import logging
import uuid

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    ChosenInlineResult,
    InlineQuery,
    InlineQueryResultCachedDocument,
    InlineQueryResultCachedPhoto,
    InlineQueryResultsButton,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiopg.sa import Engine

from oc_ref_bot.cmd_router import ChatState
from oc_ref_bot.database import get_refs, get_user, get_user_with_settings
from oc_ref_bot.database import ref_sent as db_ref_sent

router = Router()

log = logging.getLogger(__name__)


@router.inline_query(F.query.len() >= 0)
async def show_user_refs(inline_query: InlineQuery, pg: Engine):
    async with pg.acquire() as conn:
        user = await get_user(conn, inline_query.from_user.id)
        settings = await get_user_with_settings(conn, inline_query.from_user.id) or {}
        refs = [
            dict(ref)
            for ref in await get_refs(
                conn,
                inline_query.from_user.id,
                inline_query.query if settings.get('inline_input_mode', 'SEARCH') == 'SEARCH' else None,
            )
        ]

    if user and user.banned:
        await inline_query.answer(
            cache_time=600,
            results=[],
            button=InlineQueryResultsButton(start_parameter='0', text='Пользователь заблокирован'),
        )
        return

    if not user or not refs:
        await inline_query.answer(
            cache_time=60,
            results=[],
            button=InlineQueryResultsButton(start_parameter='0', text='Рефки не найдены. Добавить рефки'),
        )
        return

    def make_caption(ref) -> str | None:
        caption = ''
        if ref['verified'] and settings.get('show_verification', True):
            caption += '@OCRefBot: ✅ Verified Ref Owner\n'
        if settings.get('inline_input_mode', 'SEARCH') == 'CAPTION' and inline_query.query.strip() != '':
            caption += f'Комментарий от пользователя:\n\n{inline_query.query.replace("<", "&lt;").replace(">", "&gt;").replace("✅ Verified Ref Owner", "❌ USER TRIES TO SCAM")}'
        if not caption:
            return None
        return caption.strip()

    results = []
    for ref in refs:
        if 'PHOTO' in settings.get('inline_format', 'PHOTO+DOC'):
            results.append(
                InlineQueryResultCachedPhoto(
                    id='ph_' + str(ref['id']),
                    photo_file_id=ref['photo_file_id'],
                    caption=make_caption(ref),
                )
            )
        if ref['doc_file_id'] and 'DOC' in settings.get('inline_format', 'PHOTO+DOC'):
            results.append(
                InlineQueryResultCachedDocument(
                    id='doc_' + str(ref['id']),
                    document_file_id=ref['doc_file_id'],
                    title=ref['ref_name'],
                    caption=make_caption(ref),
                )
            )
    await inline_query.answer(cache_time=30, is_personal=True, results=results)
    log.info('User %s choosing ref in chat type %s', inline_query.from_user.full_name, inline_query.chat_type)


@router.chosen_inline_result()
async def ref_sent(inline_result: ChosenInlineResult, state: FSMContext, pg: Engine):
    sent_as_photo = inline_result.result_id.startswith('ph_')
    sent_as_doc = inline_result.result_id.startswith('doc_')
    sent_ref_id = uuid.UUID(inline_result.result_id.replace('ph_', '').replace('doc_', ''))
    async with pg.acquire() as conn:
        ref = await db_ref_sent(conn, ref_id=sent_ref_id)
    log.info(
        'User %s sent ref via bot as %s',
        inline_result.from_user.full_name,
        'document' if sent_as_doc else 'photo',
    )

    if (await state.get_state()) == ChatState.del_ref:
        if not ref:
            await state.clear()
            await inline_result.bot.send_message(
                inline_result.from_user.id,
                'Ой.. Кажется эта рефка уже удалена и была отправлена из кэша о:\nБлижайшее время она пропадёт из инлайн-меню!',
            )
            return
        await state.set_state(ChatState.del_ref_confirm)
        await state.set_data({'ref_id': sent_ref_id})
        await inline_result.bot.send_message(
            inline_result.from_user.id,
            'Ты точно хочешь удалить рефку с этим персонажем?',
        )
        await inline_result.bot.send_photo(
            inline_result.from_user.id,
            photo=ref['photo_file_id'],
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text='Да, удалить'), KeyboardButton(text='Отменить')]],
                one_time_keyboard=True,
            ),
        )

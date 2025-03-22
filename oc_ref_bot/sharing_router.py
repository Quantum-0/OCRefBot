# Sharing
# /share - спросить
# /ask
# /move - передать одну рефку
# под рефкой добавить кнопку ASK
# updated_at в бд - ориентироваться на то что пользователь уже запрашивал и ему отказали, не давать запросить заново ближайший час??
import logging
from uuid import UUID

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ChosenInlineResult, User
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiopg.sa import Engine

from database import move_ref_to_new_user

router = Router()

log = logging.getLogger(__name__)


class SharingState(StatesGroup):
    move_select_user = State()
    move_select_ref = State()
    move_confirmation = State()


@router.message(Command('move'))
async def cmd_move_1(message: Message, state: FSMContext):
    await message.answer(
        'Укажите пользователя, которому хотите передать персонажа.'
        'Для этого перешлите боту любое сообщение от этого пользователя',
    )
    await state.set_state(SharingState.move_select_user)
    log.info('User %s begin moving ref', message.from_user.full_name)


@router.message(SharingState.move_select_user, F.text or F.sticker)
async def cmd_move_2(message: Message, state: FSMContext):
    new_owner = message.forward_from
    if new_owner == message.from_user:
        await message.answer(
            'Нельзя передать реф самому себе.'
            'Выберите другого пользователя или'
            'воспользуйтесь командой отмены.'
        )
        return
    if new_owner is None:
        await message.answer(
            'Вы должны указать пользователя,'
            'которому хотите передать рефку,'
            'переслав любое сообщение от этого пользователя.'
            'Или воспользуйтесь командой отмены.'
        )
        return
    await message.answer(
        'Теперь выберите персонажа,'
        'который будет передан другому пользователю,'
        'отправив рефку в этот чат через inline-меню',
    )
    await state.set_state(SharingState.move_select_ref)
    await state.set_data({'new_owner': new_owner})
    log.info('User %s choosen destanation user', message.from_user.full_name)


# In inline router!
async def cmd_move_3(inline_result: ChosenInlineResult, state: FSMContext, sent_ref_id: UUID):
    await state.set_state(SharingState.move_confirmation)
    data = await state.get_data()
    new_owner: User = data['new_owner']
    reply_markup = ReplyKeyboardBuilder()
    reply_markup.button(text='Подтвержаю передачу персонажа')
    reply_markup.button(text='Отмена')
    await state.set_data({'ref_id': sent_ref_id, **data})
    await inline_result.bot.send_message(
        inline_result.from_user.id,
        'ВНИМАНИЕ!\n'
        'Вы хотите передать рефку с персонажем пользователю:\n'
        f'@{new_owner.username} ({new_owner.first_name} {new_owner.last_name})\n\n'
        'Данное действие поменяет владельца персонажа на данного пользователя, вам персонаж станет более недоступен.\n'
        'Если у персонажа имелась галочка верификации, она передаётся вместе с персонажем.\n'
        'Получить персонажа назад Вы сможете только если пользователь, получивший персонажа передаст вам его обратно через команду /move\n\n'
        'Иными словами, подтверждая сейчас данную операцию, Вы подтверждаете что выбранный персонаж вместе со всеми правами передаётся указанному пользователю.\n',
        reply_markup=reply_markup.as_markup(one_time_keyboard=True),
    )

@router.message(SharingState.move_confirmation, F.text)
async def cmd_move_4(message: Message, state: FSMContext, pg: Engine):
    if message.text == 'Подтвержаю передачу персонажа':
        async with pg.acquire() as conn:
            data = await state.get_data()
            old_owner: User = message.from_user
            ref_id: UUID = data['ref_id']
            new_owner: User = data['new_owner']
            success: bool = await move_ref_to_new_user(conn, ref_id, old_owner.id, new_owner.id)
        if success:
            await message.reply('Персонаж был успешно передан новому владельцу.')
            await message.bot.send_message(
                f'Пользователь  @{old_owner.username} ({old_owner.first_name} {old_owner.last_name} передал Вам персонажа.'
                f'Вы можете увидеть его через меню отправки рефок.'
            )
        else:
            await message.reply('Ошибка передачи персонажа :с')
    else:
        reply_markup = ReplyKeyboardBuilder()
        reply_markup.button(text='Подтвержаю передачу персонажа')
        reply_markup.button(text='Отмена')
        await message.reply(
            'Вы должны отменить или подтвердить передачу персонажа',
            reply_markup=reply_markup.as_markup(one_time_keyboard=True),
        )
    log.info('User %s choosen destanation user', message.from_user.full_name)
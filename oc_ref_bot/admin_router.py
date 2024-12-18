import datetime
import logging
from csv import DictWriter
from typing import Literal, Any

import sqlalchemy as sa
from aiogram import F, Router
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputFile, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiopg.sa import Engine

from oc_ref_bot.config import settings
from oc_ref_bot.database import tbl_users, tbl_refs

router = Router()

log = logging.getLogger(__name__)


class AdminFilter(BaseFilter):
    def __init__(self, *args, **kwargs) -> None:
        pass

    async def __call__(self, message: Message) -> Literal[False] | dict[str, int]:
        if message.from_user.id == settings.admin_id:
            return {'is_admin': True}
        return False


@router.message(Command('admin'))
async def cmd_adm(message: Message, state: FSMContext):
    log.info('User %s accessing admin menu', message.from_user.full_name)
    if message.from_user.id != settings.admin_id:
        await message.answer('У вас нет доступа к меню администратора :<\nЕсли у вас возникла какая-то проблема, появились вопросы или есть пожелания к боту - вы можете обратиться к нему в ЛС - @quantum0')
        return
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='Статистика')
    rkb.button(text='Режим техобслуживания')
    rkb.button(text='Дамп БД')
    rkb.button(text='Управление пользователями')  # TODO: BAN!!!
    await message.answer('Меню администратора', reply_markup=rkb.as_markup())


@router.message(AdminFilter, F.text == 'Статистика')
async def cmd_stat(message: Message):
    log.info('User %s requests statistics', message.from_user.full_name)
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='Статистика по пользователям')
    rkb.button(text='Статистика по референсам')
    rkb.button(text='Общая статистика')
    await message.answer('Выберите тип статистики', reply_markup=rkb.as_markup())


@router.message(AdminFilter, F.text == 'Статистика по пользователям')
async def cmd_stat_user(message: Message):
    log.info('User %s requests statistics for users', message.from_user.full_name)
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='Последние 10 новых пользователей бота')
    rkb.button(text='Последние 10 активных пользователей бота')
    rkb.button(text='Пользователи без референсов')
    await message.answer('Выберите тип статистики', reply_markup=rkb.as_markup())


@router.message(AdminFilter, F.text == 'Статистика по референсам')
async def cmd_stat_user(message: Message):
    log.info('User %s requests statistics for refs', message.from_user.full_name)
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='Последние отправленные референсы')
    rkb.button(text='Последние добавленные референсы')
    await message.answer('Выберите тип статистики', reply_markup=rkb.as_markup())


def user_row_to_md(user: dict[str, Any]) -> str:
    return (
        f'Пользователь <b>{user["id"]}</b> @{user["username"]}\n'
        f'Имя: <i>{user["first_name"]} {user["last_name"]}</i>\n'
        f'Статус премиум: {user["is_premium"]}\n'
        f'Язык: {user["language_code"]}\n'
        f'Добавлен {user["created_at"].strftime('%Y-%m-%d %H:%M:%S')}\n'
        f'Кол-во отправленных сообщений: {user["messages_count"]}\n'
        f'Кол-во референсов: {user["refs_count"]}\n'
        f'Последний раз отправлял реф: {user["last_send"].strftime('%Y-%m-%d %H:%M:%S') if user["last_send"] else "N/A"}.'
    )

def ref_row_to_md(ref: dict[str, Any]) -> str:
    return (
        f'Реф <code>{ref["id"]}</code>\n'
        f'Владелец:\n'
        f'- <i>{ref["first_name"]} {ref["last_name"]}</i>\n'
        f'- <b>{ref["user_id"]}</b> @{ref["username"]}\n'
        f'Название: {ref["ref_name"]}\n'
        f'Добавлен {ref["created_at"].strftime('%Y-%m-%d %H:%M:%S')}\n'
        f'Использован {ref["used_at"].strftime('%Y-%m-%d %H:%M:%S') if ref["used_at"] else "N/A"}\n'
        f'Отправлен: {ref["used_count"]} раз\n'
        f'Владелец верифицирован: {"ДА" if ref["verified"] else "НЕТ"}'
    )


@router.message(AdminFilter, F.text == 'Общая статистика')
async def cmd_stat_common(message: Message, pg: Engine):
    log.info('User %s requests common statistics', message.from_user.full_name)

    # Сколько рефов было использовано/отправлено за последнюю неделю/месяц, сколько юзеров пользовались ботом за последнюю неделю/месяц
    # TODO ^
    async with pg.acquire() as conn:
        users_count = await (await conn.execute(sa.select(sa.func.count(tbl_users.c.id)))).scalar()
        refs_count = await (await conn.execute(sa.select(sa.func.count(tbl_refs.c.id)))).scalar()
        msgs_sum = await (await conn.execute(sa.select(sa.func.sum(tbl_users.c.messages_count)))).scalar()
        total_ref_sent = await (await conn.execute(sa.select(sa.func.sum(tbl_refs.c.used_count)))).scalar()
        max_ref_sent = await (await conn.execute(sa.select(sa.func.max(tbl_refs.c.used_count)))).scalar()
        last_ref_used = await (await conn.execute(sa.select(sa.func.max(tbl_refs.c.used_at)))).scalar()
        last_ref_added = await (await conn.execute(sa.select(sa.func.max(tbl_refs.c.created_at)))).scalar()
        last_user_added = await (await conn.execute(sa.select(sa.func.max(tbl_users.c.created_at)))).scalar()
    await message.answer(f'''Общая статистика бота:\n
Всего пользователей: {users_count}
Всего референсов: {refs_count}
Суммарное число отправленных сообщений: {msgs_sum}
Всего референсов отправлено: {total_ref_sent}
Максимальное количество раз отправки одного референса: {max_ref_sent}
Дата последнего использования референса: {last_ref_used.strftime('%Y-%m-%d %H:%M:%S')}
Дата последнего добавления референса: {last_ref_added.strftime('%Y-%m-%d %H:%M:%S')}
Дала регистрации последнего пользователя: {last_user_added.strftime('%Y-%m-%d %H:%M:%S')}''')


@router.message(AdminFilter, F.text == 'Последние 10 новых пользователей бота')
async def cmd_stat_user_last_reg(message: Message, pg: Engine):
    log.info('User %s requests statistics for users', message.from_user.full_name)
    async with pg.acquire() as conn:
        q = (
            sa.select(
                tbl_users,
                sa.func.count(tbl_refs.c.id).label('refs_count'),
                sa.func.max(tbl_refs.c.used_at).label('last_send'),
            )
            .order_by(tbl_users.c.created_at.desc())
            .join(tbl_refs, tbl_users.c.id == tbl_refs.c.user_id)
            .group_by(tbl_users.c.id)
            .limit(10)
        )
        rows = await (await conn.execute(q)).fetchall()
        resp = '\n\n'.join(user_row_to_md(dict(row)) for row in rows)
    await message.answer(resp)


@router.message(AdminFilter, F.text == 'Последние 10 активных пользователей бота')
async def cmd_stat_user_last_active(message: Message, pg: Engine):
    log.info('User %s requests statistics for users', message.from_user.full_name)
    async with pg.acquire() as conn:
        q = (
            sa.select(
                tbl_users,
                sa.func.count(tbl_refs.c.id).label('refs_count'),
                sa.func.max(tbl_refs.c.used_at).label('last_send'),
            )
            .order_by(sa.func.max(tbl_refs.c.used_at).desc())
            .join(tbl_refs, tbl_users.c.id == tbl_refs.c.user_id)
            .group_by(tbl_users.c.id)
            .limit(10)
        )
        rows = await (await conn.execute(q)).fetchall()
        resp = '\n\n'.join(user_row_to_md(dict(row)) for row in rows)
    await message.answer(resp)


@router.message(AdminFilter, F.text == 'Пользователи без референсов')
async def cmd_stat_user_no_refs(message: Message, pg: Engine):
    log.info('User %s requests statistics for users', message.from_user.full_name)
    async with pg.acquire() as conn:
        q = (
            sa.select(
                tbl_users,
                sa.literal(0).label('refs_count'),
                sa.literal(None).label('last_send'),
            )
            .outerjoin(tbl_refs, tbl_users.c.id == tbl_refs.c.user_id)
            .where(tbl_refs.c.id.is_(None))
            .order_by(tbl_users.c.created_at.desc())
            .limit(10)
        )
        rows = await (await conn.execute(q)).fetchall()
        resp = '\n\n'.join(user_row_to_md(dict(row)) for row in rows)
    await message.answer(resp or 'Нет пользователей без референсов')


@router.message(AdminFilter, F.text == 'Дамп БД')
async def cmd_dump(message: Message, pg: Engine):
    log.info('User %s requests db dump', message.from_user.full_name)
    async with pg.acquire() as conn:
        fname_users = f'dump_users_{datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d_%H-%M')}.csv'
        with open(fname_users, 'w') as f:
            out = DictWriter(f, fieldnames=[c.name for c in tbl_users.c])
            rows = await (await conn.execute(sa.select(tbl_users))).fetchall()
            for row in rows:
                out.writeheader()
                out.writerow(dict(row))
        fname_refs = f'dump_refs_{datetime.datetime.now(datetime.UTC).strftime('%Y-%m-%d_%H-%M')}.csv'
        with open(fname_refs, 'w') as f:
            out = DictWriter(f, fieldnames=[c.name for c in tbl_refs.c])
            rows = await (await conn.execute(sa.select(tbl_refs))).fetchall()
            for row in rows:
                out.writeheader()
                out.writerow(dict(row))
    await message.answer_document(FSInputFile(fname_users))
    await message.answer_document(FSInputFile(fname_refs))
    log.info('Dump sent', message.from_user.full_name)


@router.message(AdminFilter, F.text == 'Последние отправленные референсы')
async def cmd_stat_ref_last_sent(message: Message, pg: Engine):
    log.info('User %s refs stats', message.from_user.full_name)
    async with pg.acquire() as conn:
        q = (
            sa.select(
                tbl_refs,
                tbl_users.c.username.label('username'),
                tbl_users.c.first_name.label('first_name'),
                tbl_users.c.last_name.label('last_name'),
            )
            .where(tbl_refs.c.used_at.is_not(None))
            .order_by(tbl_refs.c.used_at.desc())
            .outerjoin(tbl_users, tbl_users.c.id == tbl_refs.c.user_id)
            .limit(10)
        )
        rows = await (await conn.execute(q)).fetchall()
        resp = '\n\n'.join(ref_row_to_md(dict(row)) for row in rows)
    await message.bot.send_media_group(message.chat.id, media=[InputMediaPhoto(media=ref['photo_file_id']) for ref in rows])
    await message.answer(resp)


@router.message(AdminFilter, F.text == 'Последние добавленные референсы')
async def cmd_stat_ref_last_added(message: Message, pg: Engine):
    log.info('User %s refs stats', message.from_user.full_name)
    async with pg.acquire() as conn:
        q = (
            sa.select(
                tbl_refs,
                tbl_users.c.username.label('username'),
                tbl_users.c.first_name.label('first_name'),
                tbl_users.c.last_name.label('last_name'),
            )
            .order_by(tbl_refs.c.created_at.desc())
            .outerjoin(tbl_users, tbl_users.c.id == tbl_refs.c.user_id)
            .limit(10)
        )
        rows = await (await conn.execute(q)).fetchall()
        resp = '\n\n'.join(ref_row_to_md(dict(row)) for row in rows)
    await message.bot.send_media_group(message.chat.id, media=[InputMediaPhoto(media=ref['photo_file_id']) for ref in rows])
    await message.answer(resp)
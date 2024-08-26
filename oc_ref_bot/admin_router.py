import datetime
import logging
from csv import DictWriter
from typing import Literal, Any

import sqlalchemy as sa
from aiogram import F, Router
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InputFile
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiopg.sa import Engine

from oc_ref_bot.config import settings
from oc_ref_bot.database import tbl_users, tbl_refs

router = Router()

log = logging.getLogger(__name__)


class AdminFilter(BaseFilter):

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
    await message.answer('Меню администратора', reply_markup=rkb.as_markup())


@router.message(AdminFilter, F.text == 'Статистика')
async def cmd_stat(message: Message):
    log.info('User %s requests statistics', message.from_user.full_name)
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='Статистика по пользователям')
    rkb.button(text='Статистика по референсам')
    await message.answer('Выберите тип статистики', reply_markup=rkb.as_markup())


@router.message(AdminFilter, F.text == 'Статистика по пользователям')
async def cmd_stat_user(message: Message):
    log.info('User %s requests statistics for users', message.from_user.full_name)
    rkb = ReplyKeyboardBuilder()
    rkb.button(text='Последние 10 новых пользователей бота')
    rkb.button(text='Последние 10 активных пользователей бота')
    await message.answer('Выберите тип статистики', reply_markup=rkb.as_markup())


def user_row_to_md(user: dict[str, Any]) -> str:
    return (
        f'Пользователь <b>{user["id"]}</b> @{user["username"]}\n'
        f'Имя: <i>{user["first_name"]} {user["last_name"]}</i>\n'
        f'Статус премиум: {user["is_premium"]}\n'
        f'Язык: {user["language_code"]}\n'
        f'Добавлен {user["created_at"].isoformat()}\n'
        f'Кол-во отправленных сообщений: {user["messages_count"]}\n'
        f'Кол-во референсов: {user["refs_count"]}\n'
        f'Последний раз отправлял реф: {user["last_send"].isoformat()}.'
    )


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
            .groupby(tbl_users.c.id)
            .limit(10)
        )
        rows = await (await conn.execute(q)).fetchall()
        resp = '\n\n'.join(user_row_to_md(dict(row)) for row in rows)
    await message.answer(resp)


@router.message(AdminFilter, F.text == 'Дамп БД')
async def cmd_dump(message: Message, pg: Engine):
    log.info('User %s requests db dump', message.from_user.full_name)
    async with pg.acquire() as conn:
        fname_users = f'dump_users_{datetime.datetime.now(datetime.UTC)}.csv'
        with open(fname_users, 'w') as f:
            out = DictWriter(f, fieldnames=[c.name for c in tbl_users.c])
            rows = await (await conn.execute(sa.select(tbl_users))).fetchall()
            for row in rows:
                out.writeheader()
                out.writerow(dict(row))
        fname_refs = f'dump_refs_{datetime.datetime.now(datetime.UTC)}.csv'
        with open(fname_refs, 'w') as f:
            out = DictWriter(f, fieldnames=[c.name for c in tbl_refs.c])
            rows = await (await conn.execute(sa.select(tbl_refs))).fetchall()
            for row in rows:
                out.writeheader()
                out.writerow(dict(row))
    await message.answer_document(InputFile(fname_users))
    await message.answer_document(InputFile(fname_refs))
    log.info('Dump sent', message.from_user.full_name)

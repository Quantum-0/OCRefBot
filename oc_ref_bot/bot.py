import logging
from collections.abc import Callable, Awaitable
from typing import Any

from aiogram import Dispatcher, Bot, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import BotCommand, User
from aiogram.types import Message
from aiopg.sa import Engine

from oc_ref_bot import VERSION
from oc_ref_bot.cmd_router import router as cmd_router
from oc_ref_bot.config import settings
from oc_ref_bot.database import msg_from_user, create_tables, db_engine
from oc_ref_bot.inline_router import router as inline_router

log = logging.getLogger(__name__)


class SavingUsersMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        pass

    async def __call__(
            self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]
    ) -> Any:
        pg: Engine = data['pg']
        user: User = data['event_context'].user
        async with pg.acquire() as conn:
            await msg_from_user(conn, user.id, user.username, user.first_name, user.last_name, user.is_premium,
                                user.language_code)
        return await handler(event, data)


async def main_bot() -> None:
    async with db_engine() as pg_engine:
        dp = Dispatcher(fsm_strategy=FSMStrategy.USER_IN_CHAT, pg=pg_engine)
        log.info('Dispatcher created')

        @dp.startup()
        async def startup(pg, *args, **kwargs):
            async with pg.acquire() as conn:
                await create_tables(conn)

        dp.message.middleware(SavingUsersMiddleware())
        log.info('Saving users middleware registered')

        bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        log.info('Bot initialized')

        await bot.set_my_commands([
            BotCommand(command='help', description='Справка по командам'),
            # BotCommand(command='version', description='Текущая версия бота'),
            BotCommand(command='add', description='Добавление референса'),
            BotCommand(command='del', description='Удаление референса'),
        ])
        log.info('Bot command list updated')

        me = await bot.get_me()
        if me.full_name != f'{settings.bot_name} [{VERSION}]':
            await bot.set_my_name(f'{settings.bot_name} [{VERSION}]')
        log.info('Bot name was set')

        dp.include_router(cmd_router)
        log.info('Commands router registered')
        dp.include_router(inline_router)
        log.info('Inline router registered')

        log.info('Starting polling')
        await dp.start_polling(bot)

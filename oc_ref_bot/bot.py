import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp
import psutil
import sentry_sdk
from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import BotCommand, Message, Update, User
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiopg.sa import Engine

from oc_ref_bot import VERSION
from oc_ref_bot.admin_router import router as admin_router
from oc_ref_bot.cmd_router import router as cmd_router
from oc_ref_bot.config import settings
from oc_ref_bot.database import create_tables, db_engine, msg_from_user
from oc_ref_bot.inline_router import router as inline_router
from oc_ref_bot.settings_router import router as settings_router

log = logging.getLogger(__name__)


class UsersMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        pass

    async def __call__(
        self, handler: Callable[[Message, dict[str, Any]], Awaitable[Any]], event: Message, data: dict[str, Any]
    ) -> Any:
        pg: Engine = data['pg']
        user: User = data['event_context'].user
        with sentry_sdk.start_span(op='middleware.handle-user'):
            async with pg.acquire() as conn:
                user_db = await msg_from_user(
                    conn, user.id, user.username, user.first_name, user.last_name, user.is_premium, user.language_code
                )
                if user_db.banned:
                    await event.answer('Доступ к боту с данного аккаунта запрещён.')
                    return None
        return await handler(event, data)


class SentryMiddleware(BaseMiddleware):
    async def __call__(
        self, handler: Callable[[Update, dict[str, Any]], Awaitable[Any]], event: Update, data: dict[str, Any]
    ) -> Any:
        if (not event.message) and (not event.callback_query):
            return await handler(event, data)

        with sentry_sdk.start_transaction(name='handle-update') as trans:
            sentry_sdk.set_user(
                {
                    'id': (event.message or event.callback_query).from_user.id,
                    'username': (event.message or event.callback_query).from_user.username,
                }
            )
            trans.set_tag('version', VERSION)
            trans.set_measurement('used-memory', psutil.Process(os.getpid()).memory_info().rss, 'byte')
            return await handler(event, data)


async def make_bot() -> Bot:
    bot_args = {'token': settings.bot_token, 'default': DefaultBotProperties(parse_mode=ParseMode.HTML)}
    if settings.proxy_url:
        bot_args['proxy'] = settings.proxy_url
        if settings.proxy_auth:
            bot_args['proxy_auth'] = settings.proxy_auth
    bot = Bot(**bot_args)
    log.info('Bot initialized')

    await bot.set_my_commands(
        [
            BotCommand(command='help', description='Справка по командам'),
            # BotCommand(command='version', description='Текущая версия бота'),  # noqa: ERA001
            BotCommand(command='add', description='Добавление референса'),
            BotCommand(command='del', description='Удаление референса'),
            BotCommand(command='settings', description='Настройки'),
            BotCommand(command='admin', description='Меню администратора бота'),
        ]
    )
    log.info('Bot command list updated')

    me = await bot.get_me()
    bot_name = f'{settings.bot_name} [{VERSION}]'
    if me.full_name != bot_name:
        await bot.set_my_name(bot_name)
    log.info('Bot name was set')

    if settings.webhook_enabled:
        await bot.set_webhook(**settings.webhook_params, drop_pending_updates=False)
        log.info('Webhook registered')
    else:
        await bot.delete_webhook(drop_pending_updates=False)
        log.info('Webhook deleted')

    return bot


async def make_dp(pg_engine: Engine) -> Dispatcher:
    dp = Dispatcher(fsm_strategy=FSMStrategy.USER_IN_CHAT, pg=pg_engine)
    log.info('Dispatcher created')

    @dp.startup()
    async def startup(pg: Engine, *_: Any, **__: Any) -> None:
        async with pg.acquire() as conn:
            await create_tables(conn)
        log.info('Bot startup is done')

    dp.update.middleware(SentryMiddleware())
    log.info('Error handling middlewares registered')

    dp.message.middleware(UsersMiddleware())
    log.info('Saving users middleware registered')

    dp.include_router(admin_router)
    log.info('Admin router registered')
    dp.include_router(cmd_router)
    log.info('Commands router registered')
    dp.include_router(settings_router)
    log.info('Settings router registered')
    dp.include_router(inline_router)
    log.info('Inline router registered')

    return dp


async def start_bot_with_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    log.info('Starting polling')
    await dispatcher.start_polling(bot)


async def start_bot_as_server(bot: Bot, dispatcher: Dispatcher) -> None:
    log.info('Initializating web server')
    app = aiohttp.web.Application()
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret,
    )
    webhook_requests_handler.register(app, path=settings.webhook_path)
    setup_application(app, dispatcher, bot=bot)

    log.info('Starting web server')
    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, host=settings.web_server_host, port=settings.web_server_port)
    await site.start()
    await asyncio.Event().wait()


async def main_bot() -> None:
    log.info('Starting bot...')
    log.info(f'Webhook mode is {'ENABLED' if settings.webhook_enabled else 'DISABLED'}')
    async with db_engine() as pg_engine:
        bot: Bot = await make_bot()
        dp: Dispatcher = await make_dp(pg_engine)
        if not settings.webhook_enabled:
            await start_bot_with_polling(bot, dp)
        else:
            await start_bot_as_server(bot, dp)

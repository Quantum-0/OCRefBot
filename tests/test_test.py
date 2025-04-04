from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update
from bot import UsersMiddleware
from database import create_tables, db_engine, get_user
from testcontainers.postgres import PostgresContainer

from oc_ref_bot.cmd_router import router as cmd_router
from oc_ref_bot.config import settings

pytestmark = pytest.mark.asyncio  # Required for pytest-asyncio


@pytest.fixture
async def pg_conn():
    with PostgresContainer('postgres:16-alpine', driver='psycopg2') as postgres:
        # psql_url = postgres.get_connection_url(driver='psycopg2')
        settings.db_host = postgres.get_container_host_ip() + ':' + str(postgres.get_exposed_port(postgres.port))
        settings.db_user = postgres.username
        settings.db_pass = postgres.password
        settings.db_db = postgres.dbname
        async with db_engine() as engine:
            yield engine
            # async with engine.acquire() as conn:
            #     await create_tables(conn)
            #     yield conn
        # async with db_engine() as connection:
        # engine = aiopg.sa.create_engine(psql_url)
        # async with engine as connection:
        #     await create_tables(connection)
        #     yield connection


@pytest.fixture
async def bot():
    """Creates a bot instance with a mocked send_message function."""
    bot = Bot(token=settings.bot_token)
    bot.send_message = AsyncMock()  # Mock sending messages to avoid real API calls
    bot.send_sticker = AsyncMock()  # Mock sending messages to avoid real API calls

    return bot


@pytest.fixture
async def dispatcher(bot, pg_conn):
    """Creates a Dispatcher instance."""
    dp = Dispatcher(pg=pg_conn)
    dp._bot = bot  # Attach the mock bot to the dispatcher
    dp.message.middleware(UsersMiddleware())
    dp.include_router(cmd_router)
    return dp


@pytest.fixture
async def message(bot):
    """Creates a fake message object to simulate a /start command."""
    msg = Message(
        message_id=1,
        from_user={'id': 123456789, 'is_bot': False, 'first_name': 'TestUser'},
        chat={'id': 123456789, 'type': 'private'},
        text='/start',
        date=datetime.now(),
    )
    msg._bot = bot
    return msg


async def test_start_command(bot, dispatcher, message, pg_conn):
    """Test if the bot correctly handles the /start command."""
    # await cmd_start(message)  # Simulate handling the command
    async with pg_conn.acquire() as conn:
        await create_tables(conn)

    await dispatcher.feed_update(bot, Update(update_id=1234, message=message))

    # Check that bot.send_message was called once with expected arguments
    bot.send_message.assert_called_once_with(
        message.chat.id,
        'Драсти\n\nЯ бот, который помогает удобно хранить рефки на персонажей, с возможностью быстрого доступа к ним и отправки их\n\nНадеюсь я буду Вам полезен ^-^\n\nЧтоб получить подробную инструкцию по пользованию боту, используйте команду /help\n\nМеня сделал @quantum0, по всем вопросам насчёт меня можете обращаться к нему :>\n\nОн так же передаёт вам добра и желает хорошего дня ❤️\n\n',
    )
    bot.send_sticker.assert_called_once_with(
        message.chat.id,
        'CAACAgIAAxkBAT2NsWbDhsizAAFqJIcz1hZsDkrJm1UqfQACtUwAAiNsuErWfaHtCbzGbDUE',
    )
    async with pg_conn.acquire() as conn:
        user = await get_user(conn, message.from_user.id)
        assert user
        assert 1


# import json
#
# import pytest
# from aiogram.types import Update
# from aiohttp import web
# from oc_ref_bot.main import main_bot  # Import your bot startup function
#
#
# @pytest.fixture
# async def test_client(aiohttp_client):
#     """Starts the bot's webhook server and returns a test client."""
#     app = web.Application()
#
#     # Start the bot server
#     await main_bot()  # Ensure your bot registers webhook handlers
#
#     # Create a test client
#     return await aiohttp_client(app)
#
# async def test_webhook_start_command(test_client):
#     '''Sends a fake /start command via webhook and checks response.'''
#
#     # Simulated Telegram webhook payload
#     fake_update = Update(
#         update_id=1,
#         message={
#             'message_id': 1,
#             'from': {'id': 123456789, 'is_bot': False, 'first_name': 'TestUser'},
#             'chat': {'id': 123456789, 'type': 'private'},
#             'text': '/start',
#         },
#     ).model_dump_json()
#
#     # Send webhook request to your bot
#     response = await test_client.post('/your-webhook-path', data=json.dumps(fake_update))
#
#     # Assert response is 200 OK (Telegram expects this)
#     assert response.status == 200
#
#     # Optionally, check if the bot's response contains expected text
#     response_text = await response.text()
#     assert 'Hello! Welcome to the bot' in response_text

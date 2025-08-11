# curl -v -k -X POST -H "Content-Type: application/json" -H "Cache-Control: no-cache"  -d '{
# "update_id":10000,
# "callback_query":{
#   "id": "4382bfdwdsb323b2d9",
#   "from":{
#      "last_name":"Test Lastname",
#      "type": "private",
#      "id":1111111,
#      "first_name":"Test Firstname",
#      "username":"Testusername"
#   },
#   "data": "Data from button callback",
#   "inline_message_id": "1234csdbsk4839"
# }
# }' "https://YOUR.BOT.URL:YOURPORT/"


# curl -v -k -X POST -H "Content-Type: application/json" -H "Cache-Control: no-cache"  -d '{
# "update_id":10000,
# "message":{
#   "date":1441645532,
#   "chat":{
#      "last_name":"Test Lastname",
#      "id":194573162,
#      "type": "private",
#      "first_name":"Test Firstname",
#      "username":"quantum0"
#   },
#   "message_id":1365,
#   "from":{
#      "last_name":"Test Lastname",
#      "id":194573162,
#      "first_name":"Test Firstname",
#      "username":"quantum0", "is_bot":false
#   },
#   "text":"/start"
# }
# }' -H "X-Telegram-Bot-Api-Secret-Token: bnklgnbklgnfkbnkgfnbkfg" "https://ocrefbot.quantum0.ru/webhook"


from unittest.mock import AsyncMock

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import User
from aiopg.sa import Engine
from testcontainers.postgres import PostgresContainer

from oc_ref_bot.bot import make_bot, make_dp
from oc_ref_bot.config import settings
from oc_ref_bot.database import db_engine

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def pg_engine() -> Engine:
    with PostgresContainer('postgres:16-alpine', driver='psycopg2') as postgres:
        settings.db_host = postgres.get_container_host_ip() + ':' + str(postgres.get_exposed_port(postgres.port))
        settings.db_user = postgres.username
        settings.db_pass = postgres.password
        settings.db_db = postgres.dbname
        async with db_engine() as engine:
            yield engine


@pytest.fixture
async def bot() -> Bot:
    """Creates a bot instance with a mocked send_message function."""
    Bot.set_my_commands = AsyncMock()
    Bot.get_me = AsyncMock(
        return_value=User(
            id=111222333,
            is_bot=True,
            first_name='OC Reference Bot [0.0.1]',
            last_name=None,
            username='ocrefbot',
        )
    )
    Bot.set_my_name = AsyncMock()
    Bot.delete_webhook = AsyncMock()
    bot = await make_bot()
    bot.set_my_name.assert_called_once()
    bot.delete_webhook.assert_called_once()
    Bot.send_message = AsyncMock()
    Bot.send_sticker = AsyncMock()

    return bot


@pytest.fixture
async def dispatcher(pg_engine: Engine) -> Dispatcher:
    """Creates a Dispatcher instance."""
    dp = await make_dp(pg_engine)
    await dp.emit_startup(pg=pg_engine)
    return dp

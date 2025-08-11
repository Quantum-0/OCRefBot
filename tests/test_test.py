import random
from datetime import UTC, datetime
from queue import Queue
from typing import Any, Self

import pytest
from aiogram import Bot, Dispatcher
from aiogram.types import Chat, Message, Update

from oc_ref_bot.database import get_user

pytestmark = pytest.mark.asyncio


class IncomingMessageGenerator:
    def __init__(self, dp: Dispatcher, bot: Bot, user: dict[str, Any] | None = None) -> None:
        self.update_id = 123
        self.dp = dp
        self.bot = bot
        self.user = user or {'id': 123456789, 'is_bot': False, 'first_name': 'TestUser'}
        self.msgs = Queue()

    async def get_message(self, text: str) -> Self:
        msg = Message(
            message_id=random.randint(0, 10**8),
            from_user=self.user,
            chat=Chat(id=self.user.get('id'), type='private'),
            text=text,
            date=datetime.now(tz=UTC),
        )
        msg._bot = self.bot
        self.update_id += 1
        await self.dp.feed_update(self.bot, Update(update_id=self.update_id, message=msg))
        self.msgs.put(msg)
        return self

    def check_text_response(self, text: str) -> Self:
        self.bot.send_message.assert_called_once_with(self.user.get('id'), text)
        return self

    def check_sticker_response(self, sticker_id: str) -> Self:
        self.bot.send_sticker.assert_called_once_with(self.user.get('id'), sticker_id)
        return self


@pytest.fixture
async def msg_gen(dispatcher: Dispatcher, bot: Bot) -> IncomingMessageGenerator:
    return IncomingMessageGenerator(dispatcher, bot)


# @pytest.fixture
# async def message(bot):
#     """Creates a fake message object to simulate a /start command."""
#     msg = Message(
#         message_id=1,
#         from_user={'id': 123456789, 'is_bot': False, 'first_name': 'TestUser'},
#         chat={'id': 123456789, 'type': 'private'},
#         text='/start',
#         date=datetime.now(tz=UTC),
#     )
#     msg._bot = bot
#     return msg


# async def test_start_command(bot, dispatcher, message, pg_engine):
#     """Test if the bot correctly handles the /start command."""
#
#     await dispatcher.feed_update(bot, Update(update_id=1234, message=message))
#
#     # Check that bot.send_message was called once with expected arguments
#     bot.send_message.assert_called_once_with(
#         message.chat.id,
#         'Драсти\n\nЯ бот, который помогает удобно хранить рефки на персонажей, с возможностью быстрого доступа к ним и отправки их\n\nНадеюсь я буду Вам полезен ^-^\n\nЧтоб получить подробную инструкцию по пользованию боту, используйте команду /help\n\nМеня сделал @quantum0, по всем вопросам насчёт меня можете обращаться к нему :>\n\nОн так же передаёт вам добра и желает хорошего дня ❤️\n\n',
#     )
#     bot.send_sticker.assert_called_once_with(
#         message.chat.id,
#         'CAACAgIAAxkBAT2NsWbDhsizAAFqJIcz1hZsDkrJm1UqfQACtUwAAiNsuErWfaHtCbzGbDUE',
#     )
#     async with pg_engine.acquire() as conn:
#         user = await get_user(conn, message.from_user.id)
#         assert user
#         assert 1


async def test_start_command(msg_gen, pg_engine):
    """Test if the bot correctly handles the /start command."""

    start_resp = 'Драсти\n\nЯ бот, который помогает удобно хранить рефки на персонажей, с возможностью быстрого доступа к ним и отправки их\n\nНадеюсь я буду Вам полезен ^-^\n\nЧтоб получить подробную инструкцию по пользованию боту, используйте команду /help\n\nМеня сделал @quantum0, по всем вопросам насчёт меня можете обращаться к нему :>\n\nОн так же передаёт вам добра и желает хорошего дня ❤️\n\n'
    start_sticker = 'CAACAgIAAxkBAT2NsWbDhsizAAFqJIcz1hZsDkrJm1UqfQACtUwAAiNsuErWfaHtCbzGbDUE'
    (await msg_gen.get_message('/start')).check_text_response(start_resp).check_sticker_response(start_sticker)

    async with pg_engine.acquire() as conn:
        user = await get_user(conn, msg_gen.user['id'])
        assert user.id == msg_gen.user['id']
        assert user.username == msg_gen.user.get('username')
        assert user.first_name == msg_gen.user['first_name']
        assert user.last_name == msg_gen.user.get('last_name')
        assert user.banned is False
        assert user.messages_count == 1


async def test_dump_database(msg_gen, pg_engine):
    """Test bot successfully dumps and loads database from dump."""

    # TODO

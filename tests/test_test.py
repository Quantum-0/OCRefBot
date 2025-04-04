from datetime import UTC, datetime

import pytest
from aiogram.types import Message, Update

from oc_ref_bot.database import get_user

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def message(bot):
    """Creates a fake message object to simulate a /start command."""
    msg = Message(
        message_id=1,
        from_user={'id': 123456789, 'is_bot': False, 'first_name': 'TestUser'},
        chat={'id': 123456789, 'type': 'private'},
        text='/start',
        date=datetime.now(tz=UTC),
    )
    msg._bot = bot
    return msg


async def test_start_command(bot, dispatcher, message, pg_engine):
    """Test if the bot correctly handles the /start command."""

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
    async with pg_engine.acquire() as conn:
        user = await get_user(conn, message.from_user.id)
        assert user
        assert 1

import asyncio
import logging
import sys

from oc_ref_bot.bot import main_bot

logger = logging.getLogger(__name__)


async def main_async() -> None:
    async with asyncio.TaskGroup() as group:
        group.create_task(main_bot())


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    asyncio.run(main_async())


if __name__ == '__main__':
    main()

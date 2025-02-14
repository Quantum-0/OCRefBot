import aiohttp
import sentry_sdk

from oc_ref_bot.config import settings

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)


import asyncio
import logging
import sys

from oc_ref_bot.bot import main_bot

logger = logging.getLogger(__name__)


async def healthcheck() -> None:
    if not settings.healthcheck_url:
        logger.info("Ran without healthcheck")
        return
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get(settings.healthcheck_url):
                pass
            await asyncio.sleep(settings.healthcheck_period)


async def main_async() -> None:
    # loop = asyncio.get_running_loop()
    # for sig in (signal.SIGINT, signal.SIGTERM):
    #     loop.add_signal_handler(sig, handle_shutdown_signal)
    async with asyncio.TaskGroup() as group:
        group.create_task(main_bot())
        group.create_task(healthcheck())


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    asyncio.run(main_async())


if __name__ == '__main__':
    main()

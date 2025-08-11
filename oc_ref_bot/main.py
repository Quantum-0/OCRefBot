import asyncio
import logging
import sys

import aiohttp
import sentry_sdk

from oc_ref_bot.config import settings

sentry_sdk.init(
    dsn=settings.sentry_dsn,
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
    # http_proxy=
)

from oc_ref_bot.bot import main_bot  # noqa: E402

logger = logging.getLogger(__name__)


async def healthcheck() -> None:
    if not settings.healthcheck_url:
        logger.info('Ran without healthcheck')
        return
    request_params = {'url': settings.healthcheck_url}
    if settings.proxy_url:
        request_params['proxy'] = settings.proxy_url
        if settings.proxy_auth:
            request_params['proxy_auth'] = settings.proxy_auth
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.post(settings.healthcheck_url):
                    pass
            except Exception as exc:  # noqa: BLE001
                sentry_sdk.capture_exception(exc)
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

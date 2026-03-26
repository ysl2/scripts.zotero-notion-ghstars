import asyncio

import aiohttp


HTTP_TOTAL_TIMEOUT = 20
HTTP_CONNECT_TIMEOUT = 10
MAX_RETRIES = 2


class RateLimiter:
    """Serialize requests to keep a minimum interval between them."""

    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self.last_request_time = 0.0
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        loop = asyncio.get_event_loop()
        async with self.lock:
            now = loop.time()
            wait_until = max(now, self.last_request_time + self.min_interval)
            self.last_request_time = wait_until

        delay = wait_until - now
        if delay > 0:
            await asyncio.sleep(delay)


def build_timeout() -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(total=HTTP_TOTAL_TIMEOUT, connect=HTTP_CONNECT_TIMEOUT)

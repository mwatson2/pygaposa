import asyncio
from logging import Logger
from typing import Any, Callable, Coroutine, Optional, TypedDict

POLL_INTERVAL = 2  # seconds
POLL_RETRIES = 5
POLL_TIMEOUT = 10  # seconds


class PollMagagerConfig(TypedDict):
    """
    Configuration for PollManager.
    """

    """Interval between polls in seconds."""
    poll_interval: int

    """Number of times to retry a poll before giving up."""
    poll_retries: int

    """Timeout for a single poll in seconds."""
    poll_timeout: int


DefaultPollManagerConfig: PollMagagerConfig = {
    "poll_interval": POLL_INTERVAL,
    "poll_retries": POLL_RETRIES,
    "poll_timeout": POLL_TIMEOUT,
}


class PollManager:
    """
    Class for managing polling in response to a request and until a condition is met.

    The poll method should return a coroutine that polls the remote state. This class
    issues poll request in response to wait_for_update() and wait_for_condition() calls,
    ensuring that the polling is stopped when all waiters have been satisfied and that
    there is only one polling task active at a time.

    The wait_for_update() method will perform the poll once. The wait_for_condition()
    method will perform the poll until the condition is met. The condition is a callback
    that returns True when the polling should stop. The condition is checked after each
    poll.
    """

    def __init__(
        self,
        poll: Callable[[], Coroutine],
        logger: Logger,
        config: PollMagagerConfig = DefaultPollManagerConfig,
    ):
        self.poll = poll
        self.poll_interval = config["poll_interval"]
        self.poll_retries = config["poll_retries"]
        self.poll_timeout = config["poll_timeout"]
        self.logger = logger
        self.pollingTask: Optional[asyncio.Task[Any]] = None
        self.waiters: list[tuple[Optional[Callable[[], bool]], asyncio.Event]] = []

    async def wait_for_update(self):
        """
        Fetch the device document.
        """
        await self.wait_for_condition()

    async def wait_for_condition(self, condition: Optional[Callable[[], bool]] = None):
        """
        Poll the device document until the callback returns True or just once.
        """
        event = asyncio.Event()
        self.waiters.append((condition, event))
        self.retries = 0

        if self.pollingTask is None:
            self.pollingTask = asyncio.create_task(self.execute())

        await event.wait()

    async def execute(self):
        """
        Poll the device document until all callbacks return True.
        """
        while self.waiters:
            numConditions = self.numConditions()
            try:
                await asyncio.wait_for(self.poll(), self.poll_timeout)
            except asyncio.TimeoutError:
                self.logger.error("Timeout waiting for device document update")
            except Exception as e:
                self.logger.error(f"Error {e} waiting for device document update")

            sleep = numConditions == self.numConditions()

            met = [
                (condition, event)
                for condition, event in self.waiters
                if condition is None or condition()
            ]

            for condition, event in met:
                event.set()
                self.waiters.remove((condition, event))

            if self.waiters and sleep:
                self.retries += 1
                if self.retries > self.poll_retries:
                    self.logger.error("Exceeded polling retries")
                    for _, event in self.waiters:
                        event.set()
                    self.waiters = []
                else:
                    await asyncio.sleep(self.poll_interval)

        self.pollingTask = None

    def numConditions(self):
        return len([waiter for waiter in self.waiters if waiter[0] is not None])

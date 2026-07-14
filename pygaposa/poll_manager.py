import asyncio
from logging import Logger
from typing import Any, Callable, Coroutine, Optional, TypedDict

POLL_INTERVAL = 2  # seconds
POLL_RETRIES = 10
POLL_TIMEOUT = 20  # seconds


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
        self.waiters: list[
            tuple[Optional[Callable[[], bool]], "asyncio.Future[None]"]
        ] = []

    async def wait_for_update(self):
        """
        Fetch the device document.
        """
        await self.wait_for_condition()

    async def close(self):
        """Cancel any in-progress polling and fail outstanding waiters.

        Used when shutting down so that a polling task started for a
        fire-and-forget command does not keep running (and does not emit
        unhandled exceptions) after the owner has been closed.
        """
        task = self.pollingTask
        self.pollingTask = None

        for _, future in self.waiters:
            if not future.done():
                future.cancel()
        self.waiters = []

        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    def add_condition(
        self, condition: Optional[Callable[[], bool]] = None
    ) -> "asyncio.Future[None]":
        """
        Poll the device document until the callback returns True or just once.
        """
        future: "asyncio.Future[None]" = asyncio.get_event_loop().create_future()
        self.waiters.append((condition, future))
        self.retries = 0

        if self.pollingTask is None:
            self.pollingTask = asyncio.create_task(self.execute())

        return future

    async def wait_for_condition(self, condition: Optional[Callable[[], bool]] = None):
        """
        Poll the device document until the callback returns True or just once.

        If polling ultimately fails (the poll raises on every attempt until the
        retry limit is reached), the originating exception is propagated to the
        caller rather than being silently swallowed.
        """
        future = self.add_condition(condition)
        await future

    async def execute(self):
        """
        Poll the device document until all callbacks return True.
        """
        while self.waiters:
            numConditions = self.numConditions()
            error: Optional[BaseException] = None
            try:
                self.logger.debug(
                    f"Polling device document ({numConditions} conditions,"
                    f" {self.retries} retries)"
                )
                await asyncio.wait_for(self.poll(), self.poll_timeout)
            except asyncio.TimeoutError as exc:
                self.logger.error("Timeout waiting for device document update")
                error = exc
            except Exception as exc:
                self.logger.exception("Error waiting for device document update")
                error = exc

            sleep = numConditions == self.numConditions()

            # Only settle waiters when the poll succeeded; a failed poll leaves
            # the device state stale, so its conditions must not be evaluated.
            if error is None:
                met = [
                    (condition, future)
                    for condition, future in self.waiters
                    if condition is None or condition()
                ]

                for condition, future in met:
                    if not future.done():
                        future.set_result(None)
                    self.waiters.remove((condition, future))

            if self.waiters and (sleep or error is not None):
                self.retries += 1
                if self.retries > self.poll_retries:
                    # Give up. Propagate the failure to the waiters if the poll
                    # was failing, otherwise complete them (the condition simply
                    # never became true within the retry budget).
                    self.logger.error("Exceeded polling retries")
                    for _, future in self.waiters:
                        if future.done():
                            continue
                        if error is not None:
                            future.set_exception(error)
                        else:
                            future.set_result(None)
                    self.waiters = []
                else:
                    await asyncio.sleep(self.poll_interval)

        self.pollingTask = None

    def numConditions(self):
        return len([waiter for waiter in self.waiters if waiter[0] is not None])

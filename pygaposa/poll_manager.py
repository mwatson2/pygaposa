import asyncio
from logging import Logger
from typing import Callable, Coroutine

POLL_INTERVAL = 2  # seconds
POLL_RETRIES = 5
POLL_TIMEOUT = 10  # seconds


class PollManager:
    """
    Class for managing polling of the device document.

    When a command is issued, it takes a while for the system to update the device
    document. During this time other commands may be issued, necessetating continued
    polling. This class manages the polling and updates the device document when it
    changes.

    Requests for a document update may be accompanies by a callback function. This
    tests whether an expected update has occured (e.g. change in motor state).
    Polling stops when the callback returns True.
    """

    def __init__(self, poll: Callable[[], Coroutine], logger: Logger):
        self.poll = poll
        self.logger = logger
        self.pollingTask = None
        self.waiters: list[tuple[Callable[[], bool] | None, asyncio.Event]] = []

    async def wait_for_update(self):
        """
        Fetch the device document.
        """
        await self.wait_for_condition()

    async def wait_for_condition(self, condition: Callable[[], bool] | None = None):
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
                await asyncio.wait_for(self.poll(), POLL_TIMEOUT)
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
                if self.retries > POLL_RETRIES:
                    self.logger.error("Exceeded polling retries")
                    for _, event in self.waiters:
                        event.set()
                    self.waiters = []
                else:
                    await asyncio.sleep(POLL_INTERVAL)

        self.pollingTask = None

    def numConditions(self):
        return len([waiter for waiter in self.waiters if waiter[0] is not None])

import asyncio
from logging import Logger
from typing import Callable, Coroutine, Optional, Union

from typeguard import check_type

from pygaposa.api import GaposaApi
from pygaposa.api_types import DeviceDocument, DeviceInfo
from pygaposa.firebase import FirestorePath
from pygaposa.model import Motor, Named, Updatable
from pygaposa.poll_manager import PollMagagerConfig, PollManager


class DeviceBase(Updatable):
    """Base class for a device in the Gaposa API.

    A device is a physical Gaposa hub device that can be controlled by the API.
    The Gaposa hub control one or more motors, which can be controlled individually,
    or as part of a group. The device also has a list of rooms and schedules.

    The base class is needed to avoid circular references with the Motor and Group
    classes that require a Device instance to be created.
    """

    def __init__(
        self,
        api: GaposaApi,
        firestore: FirestorePath,
        logger: Logger,
        config: PollMagagerConfig,
        info: DeviceInfo,
    ):
        Named.__init__(self, info["Serial"], info["Name"])
        self.api = api.clone()
        self.logger = logger
        self.serial: str = info["Serial"]

        self.api.setSerial(self.serial)

        self.pollManager = PollManager(self.doUpdate, self.logger, config)

        self.documentRef = firestore.child("Devices").child(self.serial)
        self.scheduleRef = self.documentRef.child("Schedule")

        # Depth counter used to suppress listener notifications while a bulk
        # refresh is in progress. Notifications are suppressed whenever this is
        # greater than zero. A counter (rather than a boolean) keeps the state
        # correct if suppressed updates overlap.
        self.suppressNotifyDepth = 0

        # Fire-and-forget command-poll tasks (see Motor/Group command with
        # waitForUpdate=False). Strong references are retained so the tasks are
        # not garbage collected mid-execution, and so they can be cancelled on
        # close().
        self.backgroundTasks: set[asyncio.Task] = set()

    def createBackgroundTask(self, coro: Coroutine) -> asyncio.Task:
        """Create and track a fire-and-forget background task.

        The task is kept referenced until it completes, and its result is
        always retrieved on completion so that a failure (e.g. a poll that
        raises during an outage) is logged rather than surfacing as an
        "Task exception was never retrieved" error.
        """
        task = asyncio.create_task(coro)
        self.backgroundTasks.add(task)
        task.add_done_callback(self._onBackgroundTaskDone)
        return task

    def _onBackgroundTaskDone(self, task: asyncio.Task) -> None:
        self.backgroundTasks.discard(task)
        if task.cancelled():
            return
        exception = task.exception()
        if exception is not None:
            self.logger.error("Background command-poll task failed", exc_info=exception)

    async def close(self):
        """Cancel outstanding background tasks and stop polling for this device."""
        tasks = list(self.backgroundTasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        await self.pollManager.close()

    async def update(
        self,
        condition: Optional[Callable[[], bool]] = None,
        notifyListeners: bool = True,
    ):
        """Update the device state from the API.

        Since we have only poll access to the device state, we need to poll the API
        to get the latest state. Since state changes may take some time to occur after
        a command is sent, we need to poll the API at a regular interval to get the
        latest state and to continue until the expected state change is observed.

        We use the PollManager class to manage the polling and to wait for the
        expected state change.

        When ``notifyListeners`` is False the registered listeners are not
        called for updates produced by this poll. This is used by the bulk
        refresh path so that a scheduled refresh does not publish a redundant
        intermediate update per device.
        """
        if not notifyListeners:
            self.suppressNotifyDepth += 1
        try:
            await self.pollManager.wait_for_condition(condition)
        finally:
            if not notifyListeners:
                self.suppressNotifyDepth -= 1

    async def doUpdate(self):
        self.snapshot = await self.documentRef.get()
        if self.snapshot is None:
            raise Exception("Failed to get device document")
        self.document: DeviceDocument = self.snapshot.val()  # type: ignore

        self.documentRef.app.logger.debug(self.document)

        check_type(self.document, DeviceDocument)

        self.scheduleEvents = {}
        schedules = self.document["Schedule"] if "Schedule" in self.document else []
        for schedule in schedules:
            (scheduleUp, scheduleDown, schedulePreset) = await asyncio.gather(
                self.scheduleRef.get(schedule + ".UP"),
                self.scheduleRef.get(schedule + ".DOWN"),
                self.scheduleRef.get(schedule + ".PRESET"),
            )
            self.scheduleEvents[schedule] = [
                scheduleUp.val() if scheduleUp else None,
                scheduleDown.val() if scheduleDown else None,
                schedulePreset.val() if schedulePreset else None,
            ]

        self.onDocumentUpdated()

    def onDocumentUpdated(self):
        self.state = self.document["State"]
        self.info = self.document["Info"]
        self.assistant = self.document["Assistant"]
        self.heartbeat = self.document["HeartBeat"]
        self.uid = self.document["Uid"]

        for deletedChannel in self.document["DeletedChannels"]:
            if str(deletedChannel) in self.document["Channels"]:
                del self.document["Channels"][str(deletedChannel)]

    def setLocation(self, location: tuple[float, float], timezone: str):
        self.location = location
        self.timezone = timezone

    def findMotorsById(self, ids: list[int]) -> list[Motor]:
        return []

    def hasSchedule(self, id: Union[int, str]) -> bool:
        return False

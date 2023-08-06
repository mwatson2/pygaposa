import asyncio
from logging import Logger
from typing import Callable, Optional, Union

from typeguard import check_type

from pygaposa.api import GaposaApi
from pygaposa.api_types import DeviceDocument, DeviceInfo
from pygaposa.firebase import FirestorePath
from pygaposa.model import Motor, Named, Updatable
from pygaposa.poll_manager import PollManager


class DeviceBase(Updatable):
    def __init__(
        self, api: GaposaApi, firestore: FirestorePath, logger: Logger, info: DeviceInfo
    ):
        Named.__init__(self, info["Serial"], info["Name"])
        self.api = api.clone()
        self.logger = logger
        self.serial: str = info["Serial"]

        self.api.setSerial(self.serial)

        self.pollManager = PollManager(self.doUpdate, self.logger)

        self.documentRef = firestore.child("Devices").child(self.serial)
        self.scheduleRef = self.documentRef.child("Schedule")

    async def update(self, condition: Optional[Callable[[], bool]] = None):
        await self.pollManager.wait_for_condition(condition)

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
            del self.document["Channels"][str(deletedChannel)]

    def setLocation(self, location: tuple[float, float], timezone: str):
        self.location = location
        self.timezone = timezone

    def findMotorsById(self, ids: list[int]) -> list[Motor]:
        return []

    def hasSchedule(self, id: Union[int, str]) -> bool:
        return False

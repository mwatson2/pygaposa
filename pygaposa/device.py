import asyncio
from logging import Logger
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from pygaposa.api import GaposaApi
from pygaposa.api_types import (
    DeviceInfo,
    EventDays,
    EventRepeat,
    NamedItem,
    ScheduleUpdate,
)
from pygaposa.devicebase import DeviceBase
from pygaposa.firebase import FirestorePath
from pygaposa.group import Group
from pygaposa.model import NamedType, Updatable
from pygaposa.motor import Motor, MotorImpl
from pygaposa.poll_manager import PollMagagerConfig, PollManager
from pygaposa.room import Room
from pygaposa.schedule import Schedule

ItemType = TypeVar("ItemType", bound=Updatable)
InitializerType = TypeVar("InitializerType", bound=NamedItem)
EventDaysSpecifier = Union[EventDays, List[EventDays], EventRepeat]


class Device(DeviceBase):
    def __init__(
        self,
        api: GaposaApi,
        firestore: FirestorePath,
        logger: Logger,
        config: PollMagagerConfig,
        info: DeviceInfo,
    ):
        DeviceBase.__init__(self, api, firestore, logger, config, info)

        self.motors: list[Motor] = []
        self.rooms: list[Room] = []
        self.groups: list[Group] = []
        self.schedules: list[Schedule] = []

    def onDocumentUpdated(self, updateSchedules: bool = False):
        DeviceBase.onDocumentUpdated(self)

        self.motors = self.onListUpdated(
            self.motors, self.document["Channels"], MotorImpl
        )
        self.rooms = self.onListUpdated(self.rooms, self.document["Rooms"], Room)
        self.groups = self.onListUpdated(self.groups, self.document["Groups"], Group)
        self.schedules = (
            self.onListUpdated(self.schedules, self.document["Schedule"], Schedule)
            if "Schedule" in self.document
            else []
        )
        if updateSchedules:
            for schedule in self.schedules:
                schedule.updateEvents(self.scheduleEvents[schedule.id])

    def findMotorById(self, id: Union[int, str]) -> Optional[Motor]:
        return findById(self.motors, str(id))

    def findRoomById(self, id: Union[int, str]) -> Optional[Room]:
        return findById(self.rooms, str(id))

    def findGroupById(self, id: Union[int, str]) -> Optional[Group]:
        return findById(self.groups, str(id))

    def findScheduleById(self, id: Union[int, str]) -> Optional[Schedule]:
        return findById(self.schedules, str(id))

    def hasSchedule(self, id: Union[int, str]) -> bool:
        return self.findScheduleById(id) is not None

    def findMotorsById(self, ids: list[int]) -> list[Motor]:
        motors = [self.findMotorById(id) for id in ids]
        if any(motor is None for motor in motors):
            raise Exception("Motor not found")
        return motors  # type: ignore

    def onListUpdated(
        self,
        items: list[ItemType],
        update: Dict[str, InitializerType],
        itemType: Callable[["Device", str, InitializerType], ItemType],
    ) -> list[ItemType]:  # noqa: E501
        result: list[ItemType] = [
            item.update(update[item.id]) for item in items if item.id in update
        ]
        for key, value in update.items():
            if findById(items, key) is None:
                result.append(itemType(self, key, value))
        return result

    async def addSchedule(self, Name: str, properties: ScheduleUpdate):
        if any(s.name == Name for s in self.schedules):
            raise Exception("Schedule already exists")

        schedule: ScheduleUpdate = {
            "Name": Name,
            "Icon": "noImg",
            **properties,  # type: ignore
        }

        if "Location" not in schedule and self.location is not None:
            schedule["Location"] = {
                "_latitude": self.location[0],
                "_longitude": self.location[1],
            }

        await self.api.addSchedule(schedule)
        await asyncio.sleep(2)
        await self.update(lambda: any(s.name == Name for s in self.schedules))

    def nextScheduleId(self) -> int:
        ids = [int(s.id) for s in self.schedules]
        highestId = max(ids) if len(ids) > 0 else 0
        return highestId + 1


def findById(items: list[NamedType], id: str) -> Optional[NamedType]:
    for item in items:
        if item.id == id:
            return item
    return None

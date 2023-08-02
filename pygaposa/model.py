import asyncio
from datetime import datetime, timedelta
from logging import Logger
from typing import Any, Callable, Dict, List, Literal, Optional, TypeVar

import suncalc
from typeguard import check_type

from pygaposa.api import GaposaApi
from pygaposa.api_types import (
    Channel,
    ClientInfo,
    Command,
    DeviceDocument,
    DeviceInfo,
    EventDays,
    EventMode,
    EventRepeat,
    GroupInfo,
    NamedItem,
    RoomInfo,
    ScheduleEventInfo,
    ScheduleEventType,
    ScheduleInfo,
    ScheduleUpdate,
    UserInfo,
)
from pygaposa.firebase import FirestorePath
from pygaposa.geoapi import GeoApi
from pygaposa.poll_manager import PollManager


class Named:
    def __init__(self, id: str, name: str):
        self.id: str = id
        self.name: str = name


class Updatable(Named):
    def update(self, update):
        pass


class Controllable(Updatable):
    async def up(self):
        pass

    async def down(self):
        pass

    async def stop(self):
        pass

    async def set(self, preset: int):
        pass


class Motor(Controllable):
    def __init__(self, device: "Device", id: str, info: Channel):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.update(info)

    def update(self, info: Channel):
        self.name = info["Name"]
        self.status = info["StatusCode"]
        self.state = info["State"]
        self.running = info["HomeRunning"]
        self.percent = info["HomePercent"]
        self.paused = info["HomePaused"]
        self.location = info["Location"]
        self.icon = info["Icon"]

    async def up(self):
        await self.command(Command.UP)

    async def down(self):
        await self.command(Command.DOWN)

    async def stop(self):
        await self.command(Command.STOP)

    async def preset(self):
        await self.command(Command.PRESET)

    async def command(self, command: Command):
        await self.device.api.control(command, "channel", self.id)
        await asyncio.sleep(2)
        await self.device.update(lambda: self.state == expectedState(command))


class Room(Updatable):
    def __init__(self, device: "Device", id: str, info: RoomInfo):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.update(info)

    def update(self, info: RoomInfo):
        self.name = info["Name"]
        self.favourite = info["Favourite"]
        self.motors = self.device.findMotorsById(info["Motors"])
        self.icon = info["Icon"]


class Group(Controllable):
    def __init__(self, device: "Device", id: str, info: GroupInfo):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.update(info)

    def update(self, info: GroupInfo):
        assert info["Name"] == self.name
        self.favourite = info["Favourite"]
        self.motors = self.device.findMotorsById(info["Motors"])
        self.icon = info["Icon"]

    async def up(self):
        await self.command(Command.UP)

    async def down(self):
        await self.command(Command.DOWN)

    async def stop(self):
        await self.command(Command.STOP)

    async def preset(self):
        await self.command(Command.PRESET)

    async def command(self, command: Command):
        await self.device.api.control(command, "group", self.id)
        await asyncio.sleep(2)
        await self.device.update(lambda: self.motors[0].state == expectedState(command))


def expectedState(command: Command) -> str:
    return {
        Command.UP: "UP",
        Command.DOWN: "DOWN",
        Command.STOP: "STOP",
        Command.PRESET: "STOP",
    }[command]


class ScheduleEvent:
    def __init__(self, info: ScheduleEventInfo, device: "Device"):
        self.device = device
        self.update(info)

    def update(self, info: ScheduleEventInfo):
        self.timezone = info["TimeZone"]
        self.active = info["Active"]
        self.futureevent = info["FutureEvent"]
        self.submit = info["Submit"]
        self.eventepoch = info["EventEpoch"]
        self.location = info["Location"]
        self.motors = [self.device.findMotorById(id) for id in info["Motors"]]
        self.eventmode = info["EventMode"]
        self.eventrepeat = info["EventRepeat"]


ScheduleEventsTuple = list[Optional[ScheduleEvent]]


def modeToIndex(mode: ScheduleEventType) -> int:
    return [
        ScheduleEventType.UP,
        ScheduleEventType.DOWN,
        ScheduleEventType.PRESET,
    ].index(mode)


class Schedule(Updatable):
    def __init__(self, device: "Device", id: str, info: ScheduleInfo):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.events: ScheduleEventsTuple = [None, None, None]
        self.update(info)

    def update(self, info: ScheduleInfo):
        self.name = info["Name"]
        self.groups = info["Groups"]
        self.location = info["Location"]
        self.motors = self.device.findMotorsById(info["Motors"])
        self.icon = info["Icon"]
        self.active = info["Active"]

    def updateEvents(self, infos: list[Optional[ScheduleEventInfo]]):
        def scheduleevent(info: Optional[ScheduleEventInfo]) -> Optional[ScheduleEvent]:
            return ScheduleEvent(info, self.device) if info is not None else None

        self.events = list(map(scheduleevent, infos))

    async def updateProperties(self, update: ScheduleUpdate):
        update["Id"] = self.id
        await self.device.api.updateSchedule(update)
        await asyncio.sleep(2)
        await self.device.update()

    async def delete(self):
        await self.device.api.deleteSchedule(self.id)
        await asyncio.sleep(2)
        await self.device.update(lambda: self.device.findScheduleById(self.id) is None)

    async def setActive(self, Active: bool):
        await self.updateProperties({"Active": Active})

    async def setEvent(self, Mode: ScheduleEventType, event: ScheduleEventInfo):
        await self.device.api.addScheduleEvent(self.id, Mode, event)
        await asyncio.sleep(2)
        await self.device.update(lambda: self.events[modeToIndex(Mode)] is not None)

    async def deleteEvent(self, Mode: ScheduleEventType):
        await self.device.api.deleteScheduleEvent(self.id, Mode)
        await asyncio.sleep(2)
        await self.device.update(lambda: self.events[modeToIndex(Mode)] is None)

    async def setSunriseOpen(
        self, days: EventDays | List[EventDays] | EventRepeat = EventDays.ALL
    ):
        await self.setSuntimeCommand(ScheduleEventType.UP, "sunrise", days)

    async def setSunsetClose(
        self, days: EventDays | List[EventDays] | EventRepeat = EventDays.ALL
    ):
        await self.setSuntimeCommand(ScheduleEventType.DOWN, "sunset", days)

    async def setSuntimeCommand(
        self,
        event: ScheduleEventType,
        suntime: Literal["sunrise", "sunset"],
        days: EventDays | List[EventDays] | EventRepeat = EventDays.ALL,
    ):
        mode: EventMode = {
            "SunRise": suntime == "sunrise",
            "SunSet": suntime == "sunset",
            "TimeDay": False,
        }
        await self.setEvent(
            event,
            {
                "EventMode": mode,
                "EventRepeat": getEventRepeat(days),
                "TimeZone": self.device.timezone,
                "Location": {
                    "_latitude": self.device.location[0],
                    "_longitude": self.device.location[1],
                },
                "FutureEvent": False,
                "Active": True,
                "Submit": True,
                "Motors": [int(motor.id) for motor in self.motors],
                "EventEpoch": self.nextSuntimeEpoch("sunset"),
            },
        )

    def nextSuntimeEpoch(self, suntime: str):
        now = datetime.now()
        todaysTimes: Dict[str, datetime] = suncalc.get_times(
            now, self.device.location[0], self.device.location[1]
        )  # type: ignore
        if todaysTimes[suntime] < now:
            tomorrow = self.getDateTomorrow()
            tomorrowsTimes: Dict[str, datetime] = suncalc.get_times(
                tomorrow, self.device.location[0], self.device.location[1]
            )  # type: ignore
            return int(tomorrowsTimes[suntime].timestamp())
        else:
            return int(todaysTimes[suntime].timestamp())

    def getDateTomorrow(self):
        return datetime.now() + timedelta(days=1)


NamedType = TypeVar("NamedType", bound=Named)
ItemType = TypeVar("ItemType", bound=Updatable)
InitializerType = TypeVar("InitializerType", bound=NamedItem)


class Device(Updatable):
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
        self.motors: list[Motor] = []
        self.rooms: list[Room] = []
        self.groups: list[Group] = []
        self.schedules: list[Schedule] = []

    async def update(self, condition: Callable[[], bool] | None = None):
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

    def onDocumentUpdated(self, updateSchedules: bool = False):
        self.state = self.document["State"]
        self.info = self.document["Info"]
        self.assistant = self.document["Assistant"]
        self.heartbeat = self.document["HeartBeat"]
        self.uid = self.document["Uid"]

        for deletedChannel in self.document["DeletedChannels"]:
            del self.document["Channels"][str(deletedChannel)]
        self.motors = self.onListUpdated(self.motors, self.document["Channels"], Motor)
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

    def findMotorById(self, id: int | str) -> Motor | None:
        return findById(self.motors, str(id))

    def findRoomById(self, id: int | str) -> Room | None:
        return findById(self.rooms, str(id))

    def findGroupById(self, id: int | str) -> Group | None:
        return findById(self.groups, str(id))

    def findScheduleById(self, id: int | str) -> Schedule | None:
        return findById(self.schedules, str(id))

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
        result: list[ItemType] = []
        for key, value in update.items():
            item = findById(items, key)
            if item is None:
                item = itemType(self, key, value)
            else:
                item.update(value)
            result.append(item)
        return result

    async def addSchedule(self, Name: str, properties: ScheduleUpdate):
        if any(s.name == Name for s in self.schedules):
            raise Exception("Schedule already exists")

        schedule: ScheduleUpdate = {
            "Name": Name,
            "Icon": "noImg",
            **properties,
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

    def setLocation(self, location: tuple[float, float], timezone: str):
        self.location = location
        self.timezone = timezone


class User(Named):
    def __init__(self, geoApi: GeoApi, info: UserInfo):
        Named.__init__(self, info["Uid"], info["Name"])
        self.email: str = info["Email"]
        self.mobile: str = info["Mobile"]
        self.country: str = info["Country"]
        self.countryCode: str = info["CountryCode"]
        self.countryId: str = info["CountryID"]
        self.uid: str = info["Uid"]
        self.role: int = info["Role"]
        self.active: bool = info["Active"]
        self.compoundLocation: str = info["CompoundLocation"]
        self.joined: Dict[str, int] = info["Joined"]
        self.termsAgreed: bool = info["TermsAgreed"]
        self.emailAlert: bool = info["EmailAlert"]
        self.geoApi = geoApi

    async def resolveLocation(self):
        self.location = await self.geoApi.resolveLocation(self.compoundLocation)
        self.timezone = await self.geoApi.resolveTimezone(self.location)


class Client(Named):
    def __init__(
        self,
        api: GaposaApi,
        geoApi: GeoApi,
        firestore: FirestorePath,
        logger: Logger,
        id: str,
        info: ClientInfo,
    ):
        Named.__init__(self, id, info["Name"])
        self.id: str = id
        self.role: int = info["Role"]

        self.api: GaposaApi = api.clone()
        self.api.setClientAndRole(self.id, self.role)

        self.geoApi = geoApi
        self.logger = logger

        self.devices: List[Device] = [
            Device(self.api, firestore, logger, d) for d in info["Devices"]
        ]

    async def getUserInfo(self) -> User:
        response = await self.api.users()
        self.user = User(self.geoApi, response["result"]["Info"])
        await self.user.resolveLocation()
        for device in self.devices:
            device.setLocation(self.user.location, self.user.timezone)
        return self.user

    async def update(self):
        updates = [device.update() for device in self.devices]
        await asyncio.gather(*updates)


def findById(items: list[NamedType], id: str) -> Optional[NamedType]:
    for item in items:
        if item.id == id:
            return item
    return None


def findByName(items: list[NamedType], name: str) -> Optional[NamedType]:
    for item in items:
        if item.name == name:
            return item
    return None


def getEventRepeat(days: EventDays | List[EventDays] | EventRepeat) -> EventRepeat:
    if isinstance(days, tuple) or isinstance(days, list):
        if len(days) == 7 and all(isinstance(d, bool) for d in days):
            return tuple(days)  # type: ignore
        else:
            assert all(isinstance(d, EventDays) for d in days)
            return tuple(x in days for x in range(7))
    elif days == EventDays.ALL:
        return (True,) * len(EventDays)
    elif days == EventDays.WEEKDAYS:
        return (True, True, True, True, True, False, False)
    elif days == EventDays.WEEKENDS:
        return (False, False, False, False, False, True, True)
    else:
        return (i == days for i in range(7))  # type: ignore

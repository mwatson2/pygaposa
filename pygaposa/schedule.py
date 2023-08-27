import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional, Union

import suncalc  # type: ignore

from pygaposa.api_types import (
    EventDays,
    EventMode,
    EventRepeat,
    ScheduleEventInfo,
    ScheduleEventType,
    ScheduleInfo,
    ScheduleUpdate,
)
from pygaposa.devicebase import DeviceBase
from pygaposa.model import Named, Updatable


class ScheduleEvent:
    def __init__(self, info: ScheduleEventInfo, device: DeviceBase):
        self.device = device
        self.update(info)

    def update(self, info: ScheduleEventInfo):
        self.timezone = info["TimeZone"]
        self.active = info["Active"]
        self.futureevent = info["FutureEvent"]
        self.submit = info["Submit"]
        self.eventepoch = info["EventEpoch"]
        self.location = info["Location"]
        self.motors = self.device.findMotorsById(info["Motors"])
        self.eventmode = info["EventMode"]
        self.eventrepeat = info["EventRepeat"]
        return self


ScheduleEventsTuple = list[Optional[ScheduleEvent]]


def modeToIndex(mode: ScheduleEventType) -> int:
    return [
        ScheduleEventType.UP,
        ScheduleEventType.DOWN,
        ScheduleEventType.PRESET,
    ].index(mode)


EventDaysSpecifier = Union[EventDays, List[EventDays], EventRepeat]


class Schedule(Updatable):
    """Represents a schedule in the Gaposa API."""

    def __init__(self, device: DeviceBase, id: str, info: ScheduleInfo):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.events: ScheduleEventsTuple = [None, None, None]
        self.update(info)

    def update(self, info: ScheduleInfo) -> "Schedule":
        self.name = info["Name"]
        self.groups = info["Groups"]
        self.location = info["Location"]
        self.motors = self.device.findMotorsById(info["Motors"])
        self.icon = info["Icon"]
        self.active = info["Active"]
        return self

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
        await self.device.update(lambda: not self.device.hasSchedule(self.id))

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

    async def setSunriseOpen(self, days: EventDaysSpecifier = EventDays.ALL):
        await self.setSuntimeCommand(ScheduleEventType.UP, "sunrise", days)

    async def setSunsetClose(self, days: EventDaysSpecifier = EventDays.ALL):
        await self.setSuntimeCommand(ScheduleEventType.DOWN, "sunset", days)

    async def setSuntimeCommand(
        self,
        event: ScheduleEventType,
        suntime: Literal["sunrise", "sunset"],
        days: EventDaysSpecifier = EventDays.ALL,
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


def getEventRepeat(days: EventDaysSpecifier) -> EventRepeat:
    if isinstance(days, tuple) or isinstance(days, list):
        if len(days) == 7 and all(isinstance(d, bool) for d in days):
            return tuple(days)  # type: ignore
        else:
            assert all(isinstance(d, EventDays) for d in days)
            return tuple(x in days for x in range(7))  # type: ignore
    elif days == EventDays.ALL:
        return (True,) * len(EventDays)  # type: ignore
    elif days == EventDays.WEEKDAYS:
        return (True, True, True, True, True, False, False)
    elif days == EventDays.WEEKENDS:
        return (False, False, False, False, False, True, True)
    else:
        return tuple(i == days for i in range(7))  # type: ignore

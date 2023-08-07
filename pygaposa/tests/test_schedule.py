from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from unittest.mock import MagicMock

import pytest
import suncalc

from pygaposa.api import GaposaApi
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
from pygaposa.model import Motor, Named, Updatable
from pygaposa.schedule import Schedule, ScheduleEvent, getEventRepeat


@pytest.fixture
def motors(mocker) -> Dict[int, Motor]:
    return {
        1: mocker.Mock(spec=Motor),
        2: mocker.Mock(spec=Motor),
        3: mocker.Mock(spec=Motor),
        4: mocker.Mock(spec=Motor),
        5: mocker.Mock(spec=Motor),
        6: mocker.Mock(spec=Motor),
    }


@pytest.fixture
def mock_device(mocker, motors):
    device = mocker.Mock(spec=DeviceBase)
    device.api = mocker.Mock(spec=GaposaApi)
    device.findMotorsById.side_effect = lambda ids: [motors[id] for id in ids]
    return device


@pytest.fixture
def mock_schedule_info() -> ScheduleInfo:
    return {
        "Name": "Test Schedule",
        "Groups": [1, 2],
        "Location": {"_latitude": 0, "_longitude": 0},
        "Motors": [1, 2, 3],
        "Icon": "schedule_icon",
        "Active": True,
    }


@pytest.fixture
def mock_schedule_event_info() -> ScheduleEventInfo:
    return {
        "TimeZone": "UTC",
        "Active": True,
        "FutureEvent": False,
        "Submit": True,
        "EventEpoch": 0,
        "Location": {"_latitude": 0, "_longitude": 0},
        "Motors": [],
        "EventMode": {"SunRise": True, "SunSet": False, "TimeDay": False},
        "EventRepeat": (True, True, True, True, True, True, True),
    }


def test_schedule_init(mock_device, mock_schedule_info, motors):
    schedule = Schedule(mock_device, "schedule_id", mock_schedule_info)
    assert schedule.name == "Test Schedule"
    assert schedule.id == "schedule_id"
    assert schedule.location == {"_latitude": 0, "_longitude": 0}
    assert schedule.active is True
    assert schedule.icon == "schedule_icon"
    assert schedule.motors == [motors[1], motors[2], motors[3]]
    assert schedule.groups == [1, 2]
    assert schedule.device == mock_device
    assert schedule.events == [None, None, None]


def test_schedule_update(mock_device, mock_schedule_info, motors):
    schedule = Schedule(mock_device, "schedule_id", mock_schedule_info)
    updated_info: ScheduleInfo = {
        "Name": "Updated Schedule",
        "Groups": [3, 4],
        "Location": {"_latitude": 1, "_longitude": 1},
        "Motors": [4, 5, 6],
        "Icon": "updated_schedule_icon",
        "Active": False,
    }
    schedule.update(updated_info)
    assert schedule.name == "Updated Schedule"
    assert schedule.location == {"_latitude": 1, "_longitude": 1}
    assert schedule.active is False
    assert schedule.icon == "updated_schedule_icon"
    assert schedule.motors == [motors[4], motors[5], motors[6]]
    assert schedule.groups == [3, 4]


def test_schedule_update_events(
    mock_device, mock_schedule_info, mock_schedule_event_info
):
    schedule = Schedule(mock_device, "schedule_id", mock_schedule_info)
    event_infos = [mock_schedule_event_info] * 3
    schedule.updateEvents(event_infos)
    assert len(schedule.events) == 3
    for event in schedule.events:
        assert isinstance(event, ScheduleEvent)
        assert event.timezone == "UTC"
        assert event.active is True
        assert event.futureevent is False
        assert event.submit is True
        assert event.eventepoch == 0
        assert event.location == {"_latitude": 0, "_longitude": 0}
        assert event.motors == []
        assert event.eventmode == {"SunRise": True, "SunSet": False, "TimeDay": False}
        assert event.eventrepeat == (True, True, True, True, True, True, True)


async def test_schedule_set_active(mock_device, mock_schedule_info):
    schedule = Schedule(mock_device, "schedule_id", mock_schedule_info)
    await schedule.setActive(True)
    mock_device.api.updateSchedule.assert_awaited_with(
        {"Id": "schedule_id", "Active": True}
    )


async def test_schedule_set_inactive(mock_device, mock_schedule_info):
    schedule = Schedule(mock_device, "schedule_id", mock_schedule_info)
    await schedule.setActive(False)
    mock_device.api.updateSchedule.assert_awaited_with(
        {"Id": "schedule_id", "Active": False}
    )


async def test_schedule_set_event(
    mock_device, mock_schedule_info, mock_schedule_event_info
):
    schedule = Schedule(mock_device, "schedule_id", mock_schedule_info)
    event_info = mock_schedule_event_info
    await schedule.setEvent(ScheduleEventType.UP, event_info)
    mock_device.api.addScheduleEvent.assert_awaited_with(
        "schedule_id", ScheduleEventType.UP, event_info
    )


async def test_schedule_delete_event(mock_device, mock_schedule_info):
    schedule = Schedule(mock_device, "schedule_id", mock_schedule_info)
    await schedule.deleteEvent(ScheduleEventType.UP)
    mock_device.api.deleteScheduleEvent.assert_awaited_with(
        "schedule_id", ScheduleEventType.UP
    )


def test_get_event_repeat():
    assert getEventRepeat(EventDays.ALL) == (True,) * len(EventDays)
    assert getEventRepeat(EventDays.WEEKDAYS) == (
        True,
        True,
        True,
        True,
        True,
        False,
        False,
    )
    assert getEventRepeat(EventDays.WEEKENDS) == (
        False,
        False,
        False,
        False,
        False,
        True,
        True,
    )
    assert getEventRepeat(EventDays.MON) == (
        True,
        False,
        False,
        False,
        False,
        False,
        False,
    )
    assert getEventRepeat([EventDays.MON, EventDays.WED]) == (
        True,
        False,
        True,
        False,
        False,
        False,
        False,
    )
    assert getEventRepeat((True, False, True, False, True, False, True)) == (
        True,
        False,
        True,
        False,
        True,
        False,
        True,
    )

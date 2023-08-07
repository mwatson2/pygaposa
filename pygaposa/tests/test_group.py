from typing import Dict

import pytest

from pygaposa.api import GaposaApi
from pygaposa.api_types import Command, GroupInfo
from pygaposa.devicebase import DeviceBase
from pygaposa.group import Group
from pygaposa.model import Motor


class TestGroup:
    @pytest.fixture
    def motors(self, mocker) -> Dict[int, Motor]:
        return {
            1: mocker.Mock(spec=Motor),
            2: mocker.Mock(spec=Motor),
            3: mocker.Mock(spec=Motor),
            4: mocker.Mock(spec=Motor),
            5: mocker.Mock(spec=Motor),
            6: mocker.Mock(spec=Motor),
        }

    @pytest.fixture
    def device(self, motors, mocker):
        device = mocker.Mock(spec=DeviceBase)
        device.api = mocker.Mock(spec=GaposaApi)
        device.findMotorsById.side_effect = lambda ids: [motors[id] for id in ids]
        return device

    @pytest.fixture
    def group(self, device):
        id = "1"
        info: GroupInfo = {
            "Name": "Test Group",
            "Favourite": False,
            "Rooms": ["Living Room", "Kitchen"],
            "Motors": [4, 5, 6],
            "Icon": "group_icon",
        }
        return Group(device, id, info)

    def test_init(self, group, motors, device):
        assert group.device == device
        assert group.id == "1"
        assert group.name == "Test Group"
        assert group.favourite is False
        assert group.motors == [motors[4], motors[5], motors[6]]
        assert group.icon == "group_icon"

    def test_update(self, group, motors):
        info = {
            "Name": "Updated Group",
            "Favourite": True,
            "Rooms": ["Living Room"],
            "Motors": [1, 2],
            "Icon": "updated_icon",
        }
        group.update(info)
        assert group.name == "Updated Group"
        assert group.favourite is True
        assert group.motors == [motors[1], motors[2]]
        assert group.icon == "updated_icon"

    async def test_up(self, group, device):
        await group.up()
        device.api.control.assert_called_once_with(Command.UP, "group", "1")
        device.update.assert_called_once()

    async def test_down(self, group, device):
        await group.down()
        device.api.control.assert_called_once_with(Command.DOWN, "group", "1")
        device.update.assert_called_once()

    async def test_stop(self, group, device):
        await group.stop()
        device.api.control.assert_called_once_with(Command.STOP, "group", "1")
        device.update.assert_called_once()

    async def test_preset(self, group, device):
        await group.preset()
        device.api.control.assert_called_once_with(Command.PRESET, "group", "1")
        device.update.assert_called_once()

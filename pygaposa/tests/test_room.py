from typing import Dict

import pytest

from pygaposa.api_types import RoomInfo
from pygaposa.devicebase import DeviceBase
from pygaposa.model import Motor
from pygaposa.room import Room


class TestRoom:
    @pytest.fixture
    def motors(self, mocker) -> Dict[int, Motor]:
        return {
            1: mocker.Mock(spec=Motor),
            2: mocker.Mock(spec=Motor),
            3: mocker.Mock(spec=Motor),
            4: mocker.Mock(spec=Motor),
            5: mocker.Mock(spec=Motor),
        }

    @pytest.fixture
    def device(self, motors, mocker):
        device = mocker.Mock(spec=DeviceBase)
        device.findMotorsById.side_effect = lambda ids: [motors[id] for id in ids]
        return device

    @pytest.fixture
    def room(self, device):
        id = "123"
        info: RoomInfo = {
            "Name": "Living Room",
            "Favourite": True,
            "Motors": [1, 2, 3],
            "Icon": "room_icon",
        }
        return Room(device, id, info)

    def test_init(self, room, motors):
        assert room.device is not None
        assert room.id == "123"
        assert room.name == "Living Room"
        assert room.favourite is True
        assert room.motors == [motors[1], motors[2], motors[3]]
        assert room.icon == "room_icon"

    def test_update(self, room, motors):
        info = {
            "Name": "Updated Room",
            "Favourite": False,
            "Motors": [4, 5],
            "Icon": "updated_icon",
        }
        room.update(info)
        assert room.name == "Updated Room"
        assert room.favourite is False
        assert room.motors == [motors[4], motors[5]]
        assert room.icon == "updated_icon"

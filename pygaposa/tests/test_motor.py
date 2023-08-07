from typing import Dict

import pytest

from pygaposa.api import GaposaApi
from pygaposa.api_types import Channel, Command, GroupInfo
from pygaposa.devicebase import DeviceBase
from pygaposa.motor import MotorImpl


class TestMotor:
    @pytest.fixture
    def device(self, mocker):
        device = mocker.Mock(spec=DeviceBase)
        device.api = mocker.Mock(spec=GaposaApi)
        return device

    @pytest.fixture
    def motor(self, device):
        id = "1"
        info: Channel = {
            "Name": "Test Motor",
            "State": "UP",
            "StatusCode": 0,
            "HomeRunning": False,
            "HomePercent": 0,
            "HomePaused": False,
            "Location": "Living Room",
            "Icon": "motor_icon",
        }
        return MotorImpl(device, id, info)

    def test_init(self, motor, device):
        assert motor.device == device
        assert motor.id == "1"
        assert motor.name == "Test Motor"
        assert motor.status == 0
        assert motor.state == "UP"
        assert motor.running is False
        assert motor.percent == 0
        assert motor.paused is False
        assert motor.location == "Living Room"
        assert motor.icon == "motor_icon"

    def test_update(self, motor):
        info: Channel = {
            "Name": "Updated Motor",
            "State": "DOWN",
            "StatusCode": 1,
            "HomeRunning": True,
            "HomePercent": 100,
            "HomePaused": True,
            "Location": "Annex",
            "Icon": "updated_motor_icon",
        }
        motor.update(info)
        assert motor.name == "Updated Motor"
        assert motor.status == 1
        assert motor.state == "DOWN"
        assert motor.running is True
        assert motor.percent == 100
        assert motor.paused is True
        assert motor.location == "Annex"
        assert motor.icon == "updated_motor_icon"

    async def test_up(self, motor, device):
        await motor.up()
        device.api.control.assert_called_once_with(Command.UP, "channel", "1")
        device.update.assert_awaited_once()

    async def test_down(self, motor, device):
        await motor.down()
        device.api.control.assert_called_once_with(Command.DOWN, "channel", "1")
        device.update.assert_awaited_once()

    async def test_stop(self, motor, device):
        await motor.stop()
        device.api.control.assert_called_once_with(Command.STOP, "channel", "1")
        device.update.assert_awaited_once()

    async def test_preset(self, motor, device):
        await motor.preset()
        device.api.control.assert_called_once_with(Command.PRESET, "channel", "1")
        device.update.assert_awaited_once()

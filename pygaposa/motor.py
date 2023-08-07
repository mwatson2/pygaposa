import asyncio

from pygaposa.api_types import Channel, Command
from pygaposa.devicebase import DeviceBase
from pygaposa.model import Motor, Named, expectedState


class MotorImpl(Motor):
    """Represents a motor in the Gaposa API."""

    def __init__(self, device: DeviceBase, id: str, info: Channel):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.update(info)

    async def up(self):
        """Issue an "UP" command to the motor."""
        await self.command(Command.UP)

    async def down(self):
        """Issue a "DOWN" command to the motor."""
        await self.command(Command.DOWN)

    async def stop(self):
        """Issue a "STOP" command to the motor."""
        await self.command(Command.STOP)

    async def preset(self):
        """Issue a "PRESET" command to the motor."""
        await self.command(Command.PRESET)

    async def command(self, command: Command):
        await self.device.api.control(command, "channel", self.id)
        await asyncio.sleep(2)
        await self.device.update(lambda: self.state == expectedState(command))

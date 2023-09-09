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

    async def up(self, waitForUpdate=True):
        """Issue an "UP" command to the motor."""
        await self.command(Command.UP, waitForUpdate)

    async def down(self, waitForUpdate=True):
        """Issue a "DOWN" command to the motor."""
        await self.command(Command.DOWN, waitForUpdate)

    async def stop(self, waitForUpdate=True):
        """Issue a "STOP" command to the motor."""
        await self.command(Command.STOP, waitForUpdate)

    async def preset(self, waitForUpdate=True):
        """Issue a "PRESET" command to the motor."""
        await self.command(Command.PRESET, waitForUpdate)

    async def command(self, command: Command, waitForUpdate=True):
        await self.device.api.control(command, "channel", self.id)
        if waitForUpdate:
            await self.updateAfterCommand(command)
        else:
            asyncio.create_task(self.updateAfterCommand(command))

    async def updateAfterCommand(self, command: Command, delay=2):
        if delay:
            await asyncio.sleep(delay)
        await self.device.update(lambda: self.state == expectedState(command))

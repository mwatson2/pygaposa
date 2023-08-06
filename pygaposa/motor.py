import asyncio

from pygaposa.api_types import Channel, Command
from pygaposa.devicebase import DeviceBase
from pygaposa.model import Controllable, Motor, Named, expectedState


class MotorImpl(Motor):
    def __init__(self, device: DeviceBase, id: str, info: Channel):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.update(info)

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

import asyncio

from pygaposa.api_types import Command, GroupInfo
from pygaposa.devicebase import DeviceBase
from pygaposa.model import Controllable, Named, expectedState


class Group(Controllable):
    def __init__(self, device: DeviceBase, id: str, info: GroupInfo):
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

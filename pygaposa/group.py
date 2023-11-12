import asyncio

from pygaposa.api_types import Command, GroupInfo
from pygaposa.devicebase import DeviceBase
from pygaposa.model import Controllable, Named, expectedState


class Group(Controllable):
    """Represents a group of motors in the Gaposa API."""

    @property
    def state(self):
        # return the state if the state of all motors in self.motors is the same
        # otherwise return None
        states = {motor.state for motor in self.motors}
        if len(states) == 1:
            return states.pop()
        else:
            return None

    def __init__(self, device: DeviceBase, id: str, info: GroupInfo):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.update(info)

    def update(self, info: GroupInfo) -> "Group":
        """Update the group with new state from the API."""
        self.name = info["Name"]
        self.favourite = info["Favourite"]
        self.motors = self.device.findMotorsById(info["Motors"])
        self.icon = info["Icon"]
        return self

    async def up(self, waitForUpdate=True):
        """Issue an "UP" command to the motors in the group."""
        await self.command(Command.UP, waitForUpdate)

    async def down(self, waitForUpdate=True):
        """Issue a "DOWN" command to the motors in the group."""
        await self.command(Command.DOWN, waitForUpdate)

    async def stop(self, waitForUpdate=True):
        """Issue a "STOP" command to the motors in the group."""
        await self.command(Command.STOP, waitForUpdate)

    async def preset(self, waitForUpdate=True):
        """Issue a "PRESET" command to the motors in the group."""
        await self.command(Command.PRESET, waitForUpdate)

    async def command(self, command: Command, waitForUpdate=True):
        await self.device.api.control(command, "group", self.id)
        if waitForUpdate:
            await self.updateAfterCommand(command)
        else:
            asyncio.create_task(self.updateAfterCommand(command))

    async def updateAfterCommand(self, command: Command, delay=2):
        if delay:
            await asyncio.sleep(delay)
        await self.device.update(lambda: self.motors[0].state == expectedState(command))

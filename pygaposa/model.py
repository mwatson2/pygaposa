from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Union

from pygaposa.api_types import Channel, Command


class Named:
    """Represents an object with a name and ID."""

    def __init__(self, id: str, name: str):
        self.id: str = id
        self.name: str = name


NamedType = TypeVar("NamedType", bound=Named)


class Updatable(ABC, Named):
    """Represents an object that can be updated from the API."""

    @abstractmethod
    def update(self, update):
        pass


class Controllable(Updatable):
    """Represents an object that can be controlled by the API."""

    @abstractmethod
    async def up(self):
        pass

    @abstractmethod
    async def down(self):
        pass

    @abstractmethod
    async def stop(self):
        pass

    @abstractmethod
    async def preset(self):
        pass


class Motor(Controllable):
    """Represents a motor in the Gaposa API."""

    def update(self, info: Channel) -> "Motor":
        self.name = info["Name"]
        self.status = info["StatusCode"]
        self.state = info["State"]
        self.running = info["HomeRunning"]
        self.percent = info["HomePercent"]
        self.paused = info["HomePaused"]
        self.location = info["Location"]
        self.icon = info["Icon"]
        return self


def expectedState(command: Command) -> str:
    """Return the expected state of a motor after a command is issued."""
    return {
        Command.UP: "UP",
        Command.DOWN: "DOWN",
        Command.STOP: "STOP",
        Command.PRESET: "STOP",
    }[command]

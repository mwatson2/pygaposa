from pygaposa.api_types import RoomInfo
from pygaposa.devicebase import DeviceBase
from pygaposa.model import Named, Updatable


class Room(Updatable):
    """Represents a room in the Gaposa API."""

    def __init__(self, device: DeviceBase, id: str, info: RoomInfo):
        Named.__init__(self, id, info["Name"])
        self.device = device
        self.update(info)

    def update(self, info: RoomInfo):
        self.name = info["Name"]
        self.favourite = info["Favourite"]
        self.motors = self.device.findMotorsById(info["Motors"])
        self.icon = info["Icon"]
        return self

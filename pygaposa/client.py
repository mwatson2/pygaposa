import asyncio
from logging import Logger
from typing import Dict, List

from typeguard import check_type

from pygaposa.api import GaposaApi
from pygaposa.api_types import ClientInfo, UserInfo
from pygaposa.device import Device
from pygaposa.firebase import FirestorePath
from pygaposa.geoapi import GeoApi
from pygaposa.model import Named
from pygaposa.poll_manager import PollMagagerConfig


class User(Named):
    """Represents the "user" object in the API.

    There appears to be a one-to-one relationship between users and clients.
    The user object is the source of location and timezone information for
    all devices associated with this client
    """

    def __init__(self, geoApi: GeoApi, info: UserInfo):
        Named.__init__(self, info["Uid"], info["Name"])
        self.email: str = info["Email"]
        self.mobile: str = info["Mobile"]
        self.country: str = info["Country"]
        self.countryCode: str = info["CountryCode"]
        self.countryId: str = info["CountryID"]
        self.uid: str = info["Uid"]
        self.role: int = info["Role"]
        self.active: bool = info["Active"]
        self.compoundLocation: str = info["CompoundLocation"]
        self.joined: Dict[str, int] = info["Joined"]
        self.termsAgreed: bool = info["TermsAgreed"]
        self.emailAlert: bool = info["EmailAlert"]
        self.geoApi = geoApi

    async def resolveLocation(self):
        self.location = await self.geoApi.resolveLocation(self.compoundLocation)
        self.timezone = await self.geoApi.resolveTimezone(self.location)


class Client(Named):
    """Represents the "client" object in the API.

    The API supports multiple clients for one set of login credentials,
    but it is not clear if this capbility is used in practice.

    A client may be associated with multiple devices.
    """

    def __init__(
        self,
        api: GaposaApi,
        geoApi: GeoApi,
        firestore: FirestorePath,
        config: PollMagagerConfig,
        logger: Logger,
        id: str,
        info: ClientInfo,
    ):
        Named.__init__(self, id, info["Name"])
        self.id: str = id
        self.role: int = info["Role"]

        self.api: GaposaApi = api.clone()
        self.api.setClientAndRole(self.id, self.role)

        self.geoApi = geoApi
        self.logger = logger

        self.devices: List[Device] = [
            Device(self.api, firestore, logger, config, d) for d in info["Devices"]
        ]

    async def getUserInfo(self) -> User:
        """Get the user info for this client.

        The user info is the source of location and timezone information for
        all devices associated with this client.
        """
        response = await self.api.users()
        self.user = User(self.geoApi, response["result"]["Info"])
        await self.user.resolveLocation()
        for device in self.devices:
            device.setLocation(self.user.location, self.user.timezone)
        return self.user

    async def update(self):
        """Update the state of all devices associated with this client."""
        updates = [device.update() for device in self.devices]
        await asyncio.gather(*updates)

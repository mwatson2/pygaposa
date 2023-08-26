import asyncio
import logging
from typing import Optional

import aiohttp

from pygaposa.api import GaposaApi
from pygaposa.api_types import ApiLoginResponse
from pygaposa.client import Client, User
from pygaposa.firebase import (
    FirebaseAuth,
    FirebaseAuthException,
    FirestorePath,
    initialize_app,
)
from pygaposa.geoapi import GeoApi
from pygaposa.poll_manager import DefaultPollManagerConfig, PollMagagerConfig

logging.basicConfig(level=logging.DEBUG)


class Gaposa:
    """The main class for interacting with the Gaposa API.

    The Gaposa API is a REST API that is used to communicate with the Gaposa
    backend. The API is used to retrieve information about the user's account,
    devices, and to control the devices. The API is used by the Gaposa mobile app,
    and is not officially supported for third-party use. However, the API is fairly
    simple and easy to use.

    Arguments:
    ---------
        apiKey: The Google API key to use for the Gaopsa API.
        loop: The event loop to use for the API. If not specified, the default
            event loop will be used.
        websession: The aiohttp session to use for the API. If not specified,
            a new session will be created.

    """

    def __init__(
        self,
        apiKey: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        websession: Optional[aiohttp.ClientSession] = None,
    ):
        self.apiKey = apiKey
        self.serverUrl = "https://backend.rollapp.tech"
        self.firebase = initialize_app(
            {
                "apiKey": apiKey,
                "authDomain": "gaposa-prod.firebaseapp.com",
                "databaseURL": "https://gaposa-prod.firebaseio.com",
                "projectId": "gaposa-prod",
                "storageBucket": "gaposa-prod.appspot.com",
            }
        )
        self.firestore: Optional[FirestorePath] = None
        self.logger = logging.getLogger("GAPOSA")
        self.config = DefaultPollManagerConfig

        if loop:
            self.loop: asyncio.AbstractEventLoop = loop
        else:
            self.loop = asyncio.get_event_loop()

        if websession:
            self.session: aiohttp.ClientSession = websession
            self.ownSession: bool = False
        else:
            self.session = aiohttp.ClientSession()
            self.ownSession = True

    def setLocation(self, location: tuple[float, float], timeZoneId: str) -> "Gaposa":
        """Set the physical location and timezone for the API.

        If not provided, these will be obtained from the user information.
        This information is (presumably) use to enable schedules with sunrise / sunset
        activation times which are calculated based on geographic location and date.
        """
        self.location = location
        self.timeZoneId = timeZoneId
        return self

    def setConfig(self, config: PollMagagerConfig) -> "Gaposa":
        self.config = config
        return self

    async def login(self, email: str, password: str):
        """Open the API and authenticate with Google and Gaposa."""
        self.email = email
        self.password = password
        self.auth: FirebaseAuth = self.firebase.auth()
        await self.auth.sign_in_with_email_and_password(self.email, self.password)
        if not self.firebase.hasAuth:
            raise GaposaAuthException("Failed to authenticate with Google")

        self.firestore = self.firebase.firestore()
        self.api = GaposaApi(self.session, self.auth.getToken, self.serverUrl)
        self.geoApi = GeoApi(self.session, self.apiKey)

        authResponse: ApiLoginResponse = await self.api.login()

        if authResponse["apiStatus"] != "Success":
            raise GaposaAuthException("Failed to authenticate with Gaposa")

        self.clients: list[tuple[Client, User]] = []
        for key, value in authResponse["result"]["Clients"].items():
            client = Client(
                self.api,
                self.geoApi,
                self.firestore,
                self.config,
                self.logger,
                key,
                value,
            )
            user = await client.getUserInfo()
            self.clients.append((client, user))

        return None

    async def close(self):
        if self.ownSession:
            await self.session.close()

    async def update(self):
        """Update the state of all devices."""
        updates = [client.update() for client, _ in self.clients]
        try:
            await asyncio.gather(*updates)
        except FirebaseAuthException as exp:
            raise GaposaAuthException from exp


class GaposaAuthException(Exception):
    """Exception raised when authentication fails."""

    pass

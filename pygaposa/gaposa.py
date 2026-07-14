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
        self.firestore: Optional[FirestorePath] = None
        self.logger = logging.getLogger("gaposa")
        self.config = DefaultPollManagerConfig

        if loop:
            self.loop: Optional[asyncio.AbstractEventLoop] = loop
        else:
            # Retained for backwards compatibility but not used internally.
            # Avoid raising when constructed without a running loop.
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = None

        if websession:
            self.session: aiohttp.ClientSession = websession
            self.ownSession: bool = False
        else:
            self.session = aiohttp.ClientSession()
            self.ownSession = True

        # Share the same session with Firebase rather than letting it create its
        # own, so that a caller-supplied session (e.g. Home Assistant's shared
        # client session) is reused for every request and there is no orphaned
        # session to leak.
        self.firebase = initialize_app(
            {
                "apiKey": apiKey,
                "authDomain": "gaposa-prod.firebaseapp.com",
                "databaseURL": "https://gaposa-prod.firebaseio.com",
                "projectId": "gaposa-prod",
                "storageBucket": "gaposa-prod.appspot.com",
            },
            self.loop,
            self.session,
        )

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

    async def update(self, notifyListeners: bool = False):
        """Update the state of all devices.

        This is a bulk refresh of every device's state. By default it does not
        fire the per-device listeners, because callers driving a scheduled
        refresh (such as the Home Assistant coordinator) consume the refreshed
        state directly and firing a listener per device would publish redundant
        intermediate updates. Command-driven polls (e.g. after a motor command)
        still notify listeners so that observers see the resulting state change
        promptly.
        """
        updates = [
            client.update(notifyListeners=notifyListeners) for client, _ in self.clients
        ]
        try:
            await asyncio.gather(*updates)
        except FirebaseAuthException as exp:
            raise GaposaAuthException from exp


class GaposaAuthException(Exception):
    """Exception raised when authentication fails."""

    pass

import asyncio
import logging
from typing import Optional

import aiohttp

from pygaposa.api import GaposaApi
from pygaposa.api_types import ApiLoginResponse
from pygaposa.client import Client, User
from pygaposa.firebase import FirebaseAuth, FirestorePath, initialize_app
from pygaposa.geoapi import GeoApi
from pygaposa.poll_manager import DefaultPollManagerConfig, PollMagagerConfig

logging.basicConfig(level=logging.DEBUG)


class Gaposa:
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
        self.location = location
        self.timeZoneId = timeZoneId
        return self

    def setConfig(self, config: PollMagagerConfig) -> "Gaposa":
        self.config = config
        return self

    async def open(self, email: str, password: str):
        self.email = email
        self.password = password
        self.auth: FirebaseAuth = self.firebase.auth()
        await self.auth.sign_in_with_email_and_password(self.email, self.password)
        if not self.firebase.hasAuth:
            raise Exception("Failed to authenticate with Google")

        self.firestore = self.firebase.firestore()
        self.api = GaposaApi(self.session, self.auth.getToken, self.serverUrl)
        self.geoApi = GeoApi(self.session, self.apiKey)

        authResponse: ApiLoginResponse = await self.api.login()

        if authResponse["apiStatus"] != "Success":
            raise Exception("Failed to authenticate with Gaposa")

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

        await self.update()

        return None

    async def close(self):
        if self.ownSession:
            await self.session.close()

    async def update(self):
        updates = [client.update() for client, _ in self.clients]
        await asyncio.gather(*updates)

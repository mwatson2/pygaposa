import asyncio
from typing import Optional

import aiohttp

from pygaposa.api import GaposaApi
from pygaposa.api_types import ApiLoginResponse
from pygaposa.firebase import FirebaseAuth, initialize_app
from pygaposa.geoapi import GeoApi
from pygaposa.model import Client, User


class Gaposa:
    def __init__(
        self,
        apiKey: str,
        location: Optional[tuple[float, float]] = None,
        timeZoneId: Optional[str] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        websession: Optional[aiohttp.ClientSession] = None,
    ):
        self.apiKey = apiKey
        self.serverUrl = "https://gaposa-prod.ew.r.appspot.com"
        self.firebase = initialize_app(
            {
                "apiKey": apiKey,
                "authDomain": "gaposa-prod.firebaseapp.com",
                "databaseURL": "https://gaposa-prod.firebaseio.com",
                "projectId": "gaposa-prod",
                "storageBucket": "gaposa-prod.appspot.com",
            }
        )
        self.firestore = None

        if location:
            self.location: tuple[float, float] = location

        if timeZoneId:
            self.timeZoneId: str = timeZoneId

        if loop:
            self.loop: asyncio.AbstractEventLoop = loop
        else:
            self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        if websession:
            self.session: aiohttp.ClientSession = websession
            self.ownSession: bool = False
        else:
            self.session: aiohttp.ClientSession = aiohttp.ClientSession()
            self.ownSession: bool = True

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
            client = Client(self.api, self.geoApi, self.firestore, key, value)
            user = await client.getUserInfo()
            self.clients.append((client, user))

        await self.update()

    async def close(self):
        if self.ownSession:
            await self.session.close()

    async def update(self):
        updates = [client.update() for client, _ in self.clients]
        await asyncio.gather(*updates)

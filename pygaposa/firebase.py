from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TypedDict, Union
from urllib.parse import urljoin

import aiohttp

FirebaseConfig = TypedDict(
    "FirebaseConfig",
    {
        "apiKey": str,
        "authDomain": str,
        "databaseURL": str,
        "projectId": str,
        "storageBucket": str,
    },
)

FirebaseAuthResponse = TypedDict(
    "FirebaseAuthResponse",
    {
        "kind": str,
        "localId": str,
        "email": str,
        "displayName": str,
        "idToken": str,
        "registered": bool,
        "refreshToken": str,
        "expiresIn": str,
    },
)

SecureTokenRefreshResponse = TypedDict(
    "SecureTokenRefreshResponse",
    {
        "expires_in": str,
        "token_type": str,
        "refresh_token": str,
        "id_token": str,
        "user_id": str,
        "project_id": str,
    },
)


def flattenValue(value: Dict) -> Union[Dict, List, str, int, float, bool, None]:
    """Flatten a Firestore value to a native Python type."""
    if "mapValue" in value:
        dict: Dict = {}
        if "fields" in value["mapValue"]:
            for k, v in value["mapValue"]["fields"].items():
                dict[k] = flattenValue(v)
        return dict
    elif "arrayValue" in value:
        array: List = []
        if "values" in value["arrayValue"]:
            for v in value["arrayValue"]["values"]:
                array.append(flattenValue(v))
        return array
    elif "integerValue" in value:
        return int(value["integerValue"])
    elif "booleanValue" in value:
        return bool(value["booleanValue"])
    elif "doubleValue" in value:
        return float(value["doubleValue"])
    elif "nullValue" in value:
        return None
    else:
        # stringValue
        # timestampValue
        # geoPointValue
        # bytesValue
        # referenceValue
        return list(value.values())[0]


class FirebaseAuth:
    def __init__(self, app: FirebaseApp) -> None:
        self.app: FirebaseApp = app
        self.token_expiry: datetime = datetime.today()

    async def getToken(self) -> str:
        if self.should_refresh_id_token():
            await self.refresh_id_token()
        return self.authresponse["idToken"]

    async def sign_in_with_email_and_password(self, email: str, password: str) -> None:
        self.email: str = email
        self.password: str = password
        await self.sign_in()

    async def sign_in(self) -> None:
        async with self.app.session.post(
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword",
            params={"key": self.app.config["apiKey"]},
            json={
                "returnSecureToken": True,
                "email": self.email,
                "password": self.password,
            },
        ) as response:
            self.app.logger.debug(response)
            if response.status == 200:
                self.authresponse: FirebaseAuthResponse = await response.json()
                self.on_token_received()
            else:
                raise FirebaseAuthException("Failed to authenticate with Google")

    async def refresh_id_token(self) -> None:
        async with self.app.session.post(
            "https://securetoken.googleapis.com/v1/token",
            params={"key": self.app.config["apiKey"]},
            json={
                "grant_type": "refresh_token",
                "refresh_token": self.authresponse["refreshToken"],
            },
        ) as response:
            self.app.logger.debug(response)

            if response.status == 200:
                responseData: SecureTokenRefreshResponse = await response.json()

                self.authresponse["idToken"] = responseData["id_token"]
                self.authresponse["refreshToken"] = responseData["refresh_token"]
                self.authresponse["expiresIn"] = responseData["expires_in"]

                self.on_token_received()

            else:
                await self.sign_in()

    def on_token_received(self) -> None:
        self.token_expiry = datetime.today() + timedelta(
            seconds=int(self.authresponse["expiresIn"]) - 60
        )

    def should_refresh_id_token(self) -> bool:
        return datetime.today() > self.token_expiry


class FirebaseAuthException(Exception):
    """Raised when authentication with Google fails."""

    pass


FirestoreDocumentType = TypedDict(
    "FirestoreDocumentType",
    {"name": str, "fields": Dict, "createTime": str, "updateTime": str},
)


class FirestoreDocument:
    def __init__(self, firestore: Firestore, document: FirestoreDocumentType):
        self.firestore = firestore
        self.document: FirestoreDocumentType = document

    def val(self) -> Dict:
        result: Dict = flattenValue({"mapValue": self.document})  # type: ignore
        return result

    async def update(self) -> bool:
        document = await self.firestore._get(self.document["name"])
        if (
            document is not None
            and self.document["updateTime"] != document["updateTime"]
        ):
            self.document = document
            return True
        return False


class Firestore:
    def __init__(self, app: FirebaseApp):
        self.app: FirebaseApp = app

    async def _get(self, path: str) -> FirestoreDocumentType | None:
        headers = {}
        if self.app.hasAuth:
            token = await self.app.firebaseAuth.getToken()
            headers["Authorization"] = "Bearer " + token

        async with self.app.session.get(
            pathjoin("https://firestore.googleapis.com/v1", path),
            headers=headers,
        ) as response:
            self.app.logger.debug(response)

            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None
            else:
                response.raise_for_status()
            return None

    async def get(self, path: str) -> FirestoreDocument | None:
        document: Optional[FirestoreDocumentType] = await self._get(path)
        if document is not None:
            return FirestoreDocument(self, document)
        return None


def pathjoin(base: str, path: str) -> str:
    base = base[0:-1] if base.endswith("/") else base
    path = "/" + path if len(path) > 0 and not path.startswith("/") else path
    return base + path


class FirestorePath:
    def __init__(
        self, app: FirebaseApp, firestore: Optional[Firestore] = None, path: str = ""
    ):
        self.app = app
        if isinstance(firestore, Firestore):
            self.firestore = firestore
        else:
            self.firestore = Firestore(app)
        self.path = path

        self.sanitize_path()

    def child(self, path) -> FirestorePath:
        return FirestorePath(self.app, self.firestore, pathjoin(self.path, path))

    def sanitize_path(self):
        if self.path.endswith("/"):
            self.path = self.path[0:-1]

    async def get(self, path: str = ""):
        return await self.firestore.get(pathjoin(self.path, path))


class FirebaseApp:
    @property
    def hasAuth(self) -> bool:
        return hasattr(self, "firebaseAuth")

    def __init__(
        self,
        config: FirebaseConfig,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        websession: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.config: FirebaseConfig = config
        self.logger = logging.getLogger("firebase")
        if loop:
            self.loop: asyncio.AbstractEventLoop = loop
        else:
            self.loop = asyncio.get_event_loop()

        if websession:
            self.session: aiohttp.ClientSession = websession
        else:
            self.session = aiohttp.ClientSession()

    def auth(self) -> FirebaseAuth:
        if not self.hasAuth:
            self.firebaseAuth: FirebaseAuth = FirebaseAuth(self)
        return self.firebaseAuth

    def firestore(self, databaseId: str = "(default)") -> FirestorePath:
        return FirestorePath(
            self,
            None,
            "/projects/{projectId}/databases/{databaseId}/documents".format(
                projectId=self.config["projectId"], databaseId=databaseId
            ),
        )


def initialize_app(
    config: FirebaseConfig,
    loop: Union[None, asyncio.AbstractEventLoop] = None,
    websession: Union[None, aiohttp.ClientSession] = None,
) -> FirebaseApp:
    return FirebaseApp(config, loop, websession)

import asyncio
from typing import Dict, Optional
from unittest import mock
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
from aioresponses import CallbackResult, aioresponses

from pygaposa.firebase import FirebaseApp, Firestore, FirestoreDocumentType

mock_document: FirestoreDocumentType = {
    "name": "Mock Document",
    "fields": {
        "mapValue": {"fields": {"mock_field": {"stringValue": {"value": "mock_value"}}}}
    },
    "createTime": "yesterday",
    "updateTime": "today",
}


@pytest.fixture
def server():
    with aioresponses() as server:
        yield server


@pytest.fixture
async def websession():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest.fixture
def mock_app(websession):
    app = MagicMock(spec=FirebaseApp)()
    app.hasAuth = True
    app.firebaseAuth.getToken = AsyncMock(return_value="mock_token")
    app.session = websession
    return app


@pytest.fixture
def mock_app_bad_auth(mock_app):
    mock_app.firebaseAuth.getToken = AsyncMock(return_value="bad_mock_token")
    return mock_app


def authorize(url, **kwargs):
    if "headers" in kwargs:
        headers: Optional[Dict[str, str]] = kwargs["headers"]
        if headers and "Authorization" in headers:
            if headers["Authorization"] == "Bearer mock_token":
                return None

    return CallbackResult(status=403, reason="Forbidden")


@pytest.mark.asyncio
async def test_get_with_success_response(server, mock_app):
    server.get(
        "https://firestore.googleapis.com/v1/test/path",
        payload=mock_document,
        callback=authorize,
    )

    firestore = Firestore(app=mock_app)
    document = await firestore._get("/test/path")

    assert document == mock_document
    server.assert_called_once()


@pytest.mark.asyncio
async def test_get_with_auth_failure(server, mock_app_bad_auth):
    server.get(
        "https://firestore.googleapis.com/v1/test/path",
        payload=mock_document,
        callback=authorize,
    )

    firestore = Firestore(app=mock_app_bad_auth)
    try:
        await firestore._get("/test/path")
        raise AssertionError("Expected exception")
    except aiohttp.ClientResponseError as e:
        assert e.status == 403
        assert e.message == "Forbidden"

    server.assert_called_once()


@pytest.mark.asyncio
async def test_get_with_no_document(server, mock_app):
    server.get(
        "https://firestore.googleapis.com/v1/test/path",
        payload=None,
        callback=authorize,
    )

    firestore = Firestore(app=mock_app)
    document = await firestore._get("/test/path")

    assert document is None
    server.assert_called_once()

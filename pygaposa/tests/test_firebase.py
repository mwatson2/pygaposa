import asyncio
from unittest import mock

import aiohttp
import pytest
from yarl import URL

from pygaposa.firebase import (
    FirebaseApp,
    FirebaseAuth,
    FirebaseConfig,
    initialize_app,
    sanitizedResponse,
)


def test_sanitized_response_strips_query_and_keeps_context():
    """The API key in the query string must not appear in the log line."""
    response = mock.Mock()
    response.method = "POST"
    response.url = URL(
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
        "?key=SUPER_SECRET_KEY"
    )
    response.status = 200

    line = sanitizedResponse(response)

    assert "SUPER_SECRET_KEY" not in line
    assert "key=" not in line
    assert "POST" in line
    assert "200" in line
    assert "identitytoolkit.googleapis.com" in line


def test_has_auth():
    firebase_config: FirebaseConfig = {}  # type: ignore
    firebase_app = FirebaseApp(firebase_config, websession=mock.MagicMock())
    assert firebase_app.hasAuth is False
    firebase_app.auth()
    assert firebase_app.hasAuth is True


@mock.patch("asyncio.get_event_loop", return_value="event loop")
@mock.patch("aiohttp.ClientSession", return_value="websession")
def test_init_no_loop_or_session(mock_get_event_loop, mock_client_session):
    firebase_config: FirebaseConfig = {}  # type: ignore
    firebase_app = FirebaseApp(firebase_config)
    mock_get_event_loop.assert_called_once()
    mock_client_session.assert_called_once()
    assert firebase_app.config == firebase_config
    assert firebase_app.loop == "event loop"
    assert firebase_app.session == "websession"


def test_auth():
    firebase_config: FirebaseConfig = {}  # type: ignore
    firebase_app = FirebaseApp(firebase_config, websession=mock.MagicMock())
    firebase_auth = firebase_app.auth()
    assert isinstance(firebase_auth, FirebaseAuth)
    assert firebase_auth == firebase_app.firebaseAuth


def test_auth_again():
    firebase_config: FirebaseConfig = {}  # type: ignore
    firebase_app = FirebaseApp(firebase_config, websession=mock.MagicMock())
    firebase_auth = firebase_app.auth()
    firebase_auth_again = firebase_app.auth()
    assert firebase_auth == firebase_auth_again


def test_firestore(monkeypatch):
    dummy_path = "/projects/dummyProjectId/databases/(default)/documents"
    firebase_config: FirebaseConfig = {}  # type: ignore
    monkeypatch.setitem(firebase_config, "projectId", "dummyProjectId")
    firebase_app = FirebaseApp(firebase_config, websession=mock.MagicMock())
    firestore_path = firebase_app.firestore()
    assert firestore_path.path == dummy_path


@mock.patch("pygaposa.firebase.FirebaseApp", return_value="firebase_app")
def test_initialize_app(mock_firebase_app):
    firebase_config: FirebaseConfig = {}  # type: ignore
    loop: asyncio.AbstractEventLoop = mock.MagicMock(spec=asyncio.AbstractEventLoop)
    websession: aiohttp.ClientSession = mock.MagicMock(spec=aiohttp.ClientSession)
    firebase_app = initialize_app(firebase_config, loop, websession)

    assert firebase_app == "firebase_app"
    mock_firebase_app.assert_called_once_with(firebase_config, loop, websession)

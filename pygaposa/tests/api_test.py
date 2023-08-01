import asyncio
import json
from typing import Any, Callable, Dict, Optional

import aiohttp
import pytest
from aioresponses import CallbackResult, aioresponses
from parameterized import parameterized
from typeguard import TypeCheckError

from pygaposa.api import GaposaApi
from pygaposa.api_types import Command, ScheduleEventType

from .api_test_data import (
    add_schedule_update,
    expected_add_schedule_request,
    expected_add_schedule_response,
    expected_control_request_channel,
    expected_control_request_group,
    expected_control_response,
    expected_delete_schedule_event_request,
    expected_delete_schedule_request,
    expected_delete_schedule_response,
    expected_login_response,
    expected_schedule_event_request,
    expected_schedule_event_response,
    expected_update_schedule_request,
    expected_update_schedule_response,
    expected_users_response,
    schedule_event,
    update_schedule_update,
)


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
async def api(websession):
    async def getToken():
        return "mock_token"

    return GaposaApi(websession, getToken)


@pytest.fixture
async def api_bad_auth(api):
    async def getToken():
        return "bad_mock_token"

    api.getToken = getToken
    return api


@pytest.fixture
async def api_set_client(api):
    api.setClientAndRole("mock_client_id", 1)
    return api


@pytest.fixture
async def api_set_bad_client(api):
    api.setClientAndRole("bad_mock_client_id", 1)
    return api


@pytest.fixture
async def api_set_serial(api):
    api.setSerial("mock_serial")
    return api


def authorize(url, **kwargs):
    if "headers" in kwargs:
        headers: Optional[Dict[str, str]] = kwargs["headers"]
        if headers and "authorization" in headers:
            if headers["authorization"] == "Bearer mock_token":
                if url.path.startswith("/v1/login"):
                    return None
                else:
                    if "auth" in headers:
                        auth: Dict = json.loads(headers["auth"])
                        if "role" in auth and "client" in auth:
                            if auth["role"] == 1 and auth["client"] == "mock_client_id":
                                return None

    return CallbackResult(status=403, reason="Forbidden")


def mock_get(server: aioresponses, path: str, payload):
    url = GaposaApi.serverUrl + path
    server.get(url, payload=payload, callback=authorize)


def mock_post(server: aioresponses, path: str, payload, validate: Callable):
    url = GaposaApi.serverUrl + path
    server.post(url, payload=payload, callback=make_callback(validate))


def mock_put(server: aioresponses, path: str, payload, validate: Callable):
    url = GaposaApi.serverUrl + path
    server.put(url, payload=payload, callback=make_callback(validate))


def mock_delete(server: aioresponses, path: str, payload, validate: Callable):
    url = GaposaApi.serverUrl + path
    server.delete(url, payload=payload, callback=make_callback(validate))


def make_callback(validate: Callable):
    def callback(url, **kwargs):
        auth = authorize(url, **kwargs)
        if auth:
            return auth
        if "data" in kwargs:
            data = kwargs["data"]
            if data:
                data = json.loads(data) if isinstance(data, str) else data
                return validate(data)
        return CallbackResult(status=402, reason="Bad Request")

    return callback


def validator(expected: Dict[str, Any]):
    def validate(data: Dict[str, Any]):
        if data != expected:
            return CallbackResult(status=402, reason="Bad Request")

    return validate


async def assert_forbidden(api_function: Callable):
    await assert_http_failure(api_function, 403, "Forbidden")


async def assert_bad_request(api_function: Callable):
    await assert_http_failure(api_function, 402, "Bad Request")


async def assert_http_failure(api_function: Callable, status: int, message: str):
    try:
        await api_function()
        raise AssertionError("Expected exception")
    except aiohttp.ClientResponseError as e:
        assert e.status == status
        assert e.message == message


async def assert_bad_response(api_function: Callable, msg: str):
    try:
        await api_function()
        raise AssertionError("Expected exception")
    except TypeCheckError as e:
        assert e.args[0] == msg


async def test_login(server, api):
    mock_get(server, "/v1/login", expected_login_response)
    response = await api.login()
    assert response == expected_login_response
    server.assert_called_once()


async def test_login_auth_failure(server, api, api_bad_auth):
    mock_get(server, "/v1/login", expected_login_response)
    await assert_forbidden(api.login)
    server.assert_called_once()


async def test_login_bad_response(server, api):
    mock_get(server, "/v1/login", {"apiStatus": "Failed"})
    await assert_bad_response(api.login, 'is missing required key(s): "msg", "result"')
    server.assert_called_once()


async def test_users(server, api, api_set_client):
    mock_get(server, "/v1/users", expected_users_response)
    response = await api.users()
    assert response == expected_users_response
    server.assert_called_once()


async def test_users_auth_failure(server, api, api_set_client, api_bad_auth):
    mock_get(server, "/v1/users", expected_users_response)
    await assert_forbidden(api.users)
    server.assert_called_once()


async def test_users_client_auth_failure(server, api, api_set_bad_client):
    mock_get(server, "/v1/users", expected_users_response)
    await assert_forbidden(api.users)
    server.assert_called_once()


async def test_users_bad_response(server, api, api_set_client):
    mock_get(server, "/v1/users", {"apiStatus": "Failed"})
    await assert_bad_response(api.users, 'is missing required key(s): "msg", "result"')
    server.assert_called_once()


@pytest.mark.parametrize(
    "scope, expected_request",
    [
        ["channel", expected_control_request_channel],
        ["group", expected_control_request_group],
    ],
)
async def test_control(
    scope, expected_request, server, api, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_request})
    mock_post(server, "/control", expected_control_response, validate)
    response = await api.control(Command.DOWN, scope, "1")
    assert response == expected_control_response
    server.assert_called_once()


async def test_control_bad_request(server, api, api_set_client, api_set_serial):
    validate = validator({"payload": expected_control_request_channel})
    mock_post(server, "/control", expected_control_response, validate)

    def control():
        return api.control(Command.DOWN, "room", "1")

    await assert_bad_request(control)
    server.assert_called_once()


async def test_control_auth_failure(
    server, api, api_bad_auth, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_control_request_channel})
    mock_post(server, "/control", expected_control_response, validate)

    def control():
        return api.control(Command.DOWN, "channel", "1")

    await assert_forbidden(control)
    server.assert_called_once()


async def test_control_bad_response(server, api, api_set_client, api_set_serial):
    validate = validator({"payload": expected_control_request_channel})
    mock_post(server, "/control", {"apiCommand": "Failed"}, validate)

    def control():
        return api.control(Command.DOWN, "channel", "1")

    await assert_bad_response(control, 'is missing required key(s): "msg", "result"')
    server.assert_called_once()


async def test_add_schedule(server, api, api_set_client, api_set_serial):
    validate = validator({"payload": expected_add_schedule_request})
    mock_post(server, "/v1/schedules", expected_add_schedule_response, validate)
    response = await api.addSchedule(add_schedule_update)
    assert response == expected_add_schedule_response
    server.assert_called_once()


async def test_add_schedule_auth_failure(
    server, api, api_bad_auth, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_add_schedule_request})
    mock_post(server, "/v1/schedules", expected_add_schedule_response, validate)

    def schedule():
        return api.addSchedule(add_schedule_update)

    await assert_forbidden(schedule)
    server.assert_called_once()


async def test_add_schedule_bad_response(server, api, api_set_client, api_set_serial):
    validate = validator({"payload": expected_add_schedule_request})
    mock_post(server, "/v1/schedules", {"apiStatus": "Failed"}, validate)

    def schedule():
        return api.addSchedule(add_schedule_update)

    await assert_bad_response(schedule, 'is missing required key(s): "msg", "result"')
    server.assert_called_once()


async def test_update_schedule(server, api, api_set_client, api_set_serial):
    validate = validator({"payload": expected_update_schedule_request})
    mock_put(server, "/v1/schedules", expected_update_schedule_response, validate)
    response = await api.updateSchedule(update_schedule_update)
    assert response == expected_update_schedule_response
    server.assert_called_once()


async def test_update_schedule_auth_failure(
    server, api, api_bad_auth, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_update_schedule_request})
    mock_put(server, "/v1/schedules", expected_update_schedule_response, validate)

    def schedule():
        return api.updateSchedule(update_schedule_update)

    await assert_forbidden(schedule)
    server.assert_called_once()


async def test_update_schedule_bad_response(
    server, api, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_update_schedule_request})
    mock_put(server, "/v1/schedules", {"apiStatus": "Failed"}, validate)

    def schedule():
        return api.updateSchedule(update_schedule_update)

    await assert_bad_response(schedule, 'is missing required key(s): "msg", "result"')
    server.assert_called_once()


async def test_delete_schedule(server, api, api_set_client, api_set_serial):
    validate = validator({"payload": expected_delete_schedule_request})
    mock_delete(server, "/v1/schedules", expected_delete_schedule_response, validate)
    response = await api.deleteSchedule("1")
    assert response == expected_delete_schedule_response
    server.assert_called_once()


async def test_delete_schedule_auth_failure(
    server, api, api_bad_auth, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_delete_schedule_request})
    mock_delete(server, "/v1/schedules", expected_delete_schedule_response, validate)

    def schedule():
        return api.deleteSchedule("1")

    await assert_forbidden(schedule)
    server.assert_called_once()


async def test_delete_schedule_bad_response(
    server, api, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_delete_schedule_request})
    mock_delete(server, "/v1/schedules", {"apiStatus": "Failed"}, validate)

    def schedule():
        return api.deleteSchedule("1")

    await assert_bad_response(schedule, 'is missing required key(s): "msg", "result"')
    server.assert_called_once()


async def test_add_schedule_event(server, api, api_set_client, api_set_serial):
    validate = validator({"payload": expected_schedule_event_request})
    mock_put(server, "/v1/schedules/event", expected_schedule_event_response, validate)
    response = await api.addScheduleEvent("1", ScheduleEventType.UP, schedule_event)
    assert response == expected_schedule_event_response
    server.assert_called_once()


async def test_add_schedule_event_auth_failure(
    server, api, api_bad_auth, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_schedule_event_request})
    mock_put(server, "/v1/schedules/event", expected_schedule_event_response, validate)

    def schedule():
        return api.addScheduleEvent("1", ScheduleEventType.UP, schedule_event)

    await assert_forbidden(schedule)
    server.assert_called_once()


async def test_add_schedule_event_bad_response(
    server, api, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_schedule_event_request})
    mock_put(server, "/v1/schedules/event", {"apiStatus": "Failed"}, validate)

    def schedule():
        return api.addScheduleEvent("1", ScheduleEventType.UP, schedule_event)

    await assert_bad_response(schedule, 'is missing required key(s): "msg", "result"')
    server.assert_called_once()


async def test_delete_schedule_event(server, api, api_set_client, api_set_serial):
    validate = validator({"payload": expected_delete_schedule_event_request})
    mock_delete(
        server, "/v1/schedules/event", expected_schedule_event_response, validate
    )
    response = await api.deleteScheduleEvent("1", ScheduleEventType.UP)
    assert response == expected_schedule_event_response
    server.assert_called_once()


async def test_delete_schedule_event_auth_failure(
    server, api, api_bad_auth, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_delete_schedule_event_request})
    mock_delete(
        server, "/v1/schedules/event", expected_schedule_event_response, validate
    )

    def schedule():
        return api.deleteScheduleEvent("1", ScheduleEventType.UP)

    await assert_forbidden(schedule)
    server.assert_called_once()


async def test_delete_schedule_event_bad_response(
    server, api, api_set_client, api_set_serial
):
    validate = validator({"payload": expected_delete_schedule_event_request})
    mock_delete(server, "/v1/schedules/event", {"apiStatus": "Failed"}, validate)

    def schedule():
        return api.deleteScheduleEvent("1", ScheduleEventType.UP)

    await assert_bad_response(schedule, 'is missing required key(s): "msg", "result"')
    server.assert_called_once()

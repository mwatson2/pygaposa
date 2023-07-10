import json
import unittest
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    Union,
)
from unittest import IsolatedAsyncioTestCase, TestCase, mock

from aiohttp import ClientResponse, ClientSession
from asynctest import CoroutineMock
from parameterized import parameterized
from typeguard import TypeCheckError

from pygaposa.api import GaposaApi
from pygaposa.api_types import (
    ApiControlRequest,
    ApiControlResponse,
    ApiLoginResponse,
    ApiRequestPayload,
    ApiScheduleEventRequest,
    ApiScheduleEventResponse,
    ApiScheduleRequest,
    ApiScheduleResponse,
    ApiUsersResponse,
    Command,
    ScheduleEvent,
    ScheduleEventType,
    ScheduleUpdate,
)

expected_login_response: ApiLoginResponse = {
    "apiStatus": "Success",
    "msg": "Auth",
    "result": {
        "TermsAgreed": True,
        "UserRole": 1,
        "Clients": {
            "mock_client_id": {
                "Role": 1,
                "Name": "mock_client_name",
                "Devices": [{"Serial": "mock_serial", "Name": "mock_device_name"}],
            }
        },
    },
}

expected_users_response: ApiUsersResponse = {
    "apiStatus": "success",
    "msg": "Return user",
    "result": {
        "Info": {
            "CountryId": "mock_country_id",
            "EmailAlert": True,
            "Email": "mock_email",
            "Name": "mock_name",
            "Role": 1,
            "Uid": "mock_uid",
            "Active": True,
            "CompoundLocation": "mock_compound_location",
            "Country": "mock_country",
            "Joined": {"mock_joined": 1},
            "TermsAgreed": True,
            "CountryCode": "mock_country_code",
            "Mobile": "mock_mobile",
        }
    },
}

expected_control_request_group: ApiControlRequest = {
    "serial": "mock_serial",
    "data": {"cmd": "0xee"},
    "group": "1",
}

expected_control_request_channel: ApiControlRequest = {
    "serial": "mock_serial",
    "data": {"cmd": "0xee"},
    "channel": "1",
}

expected_control_response: ApiControlResponse = {
    "apiCommand": "Success",
    "msg": "OK",
    "result": {"Success": "OK"},
}


class TestGaposaApi(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.websession = mock.create_autospec(ClientSession)
        self.getToken = CoroutineMock(return_value="mock_token")
        self.api = GaposaApi(self.websession, self.getToken)

    def setupWebRequestMock(self, expected_response):
        mock_response = mock.create_autospec(ClientResponse)
        mock_response.ok = True
        mock_response.status = 200
        mock_response.json = CoroutineMock(return_value=expected_response)
        mock_request = CoroutineMock(return_value=mock_response)
        self.websession.request = mock_request
        return mock_request

    def setupWebRequestMockFailure(self, expected_response):
        mock_response = mock.create_autospec(ClientResponse)
        mock_response.ok = False
        mock_response.status = 400
        mock_response.json = CoroutineMock(return_value=expected_response)
        mock_request = CoroutineMock(return_value=mock_response)
        self.websession.request = mock_request
        return mock_request

    def setupWebRequestMockException(self, expected_exception):
        mock_request = CoroutineMock(side_effect=expected_exception)
        self.websession.request = mock_request
        return mock_request

    def setupWebRequestMockJsonException(self, expected_exception):
        mock_response = mock.create_autospec(ClientResponse)
        mock_response.ok = True
        mock_response.status = 200
        mock_response.json = CoroutineMock(side_effect=expected_exception)
        mock_request = CoroutineMock(return_value=mock_response)
        self.websession.request = mock_request
        return mock_request

    @parameterized.expand(
        [
            [
                "login",
                "GET",
                "/v1/login",
                False,
                False,
                [],
                expected_login_response,
                None,
            ],
            [
                "users",
                "GET",
                "/v1/users",
                True,
                False,
                [],
                expected_users_response,
                None,
            ],
            [
                "control",
                "POST",
                "/control",
                True,
                True,
                [Command.DOWN, "group", "1"],
                expected_control_response,
                expected_control_request_group,
            ],
            [
                "control",
                "POST",
                "/control",
                True,
                True,
                [Command.DOWN, "channel", "1"],
                expected_control_response,
                expected_control_request_channel,
            ],
        ]
    )
    async def test_api_call(
        self,
        fn: str,
        method: str,
        path: str,
        auth_header: bool,
        serial: bool,
        args: List,
        expected_response: Dict,
        expected_request: Optional[Dict],
    ):
        mock_request = self.setupWebRequestMock(expected_response)
        if auth_header:
            self.api.setClientAndRole("mock_client_id", 1)
        if serial:
            self.api.setSerial("mock_serial")
        if expected_request:
            expected_request = {"payload": expected_request}

        response = await getattr(self.api, fn)(*args)

        self.assertEqual(response, expected_response)
        headers = {
            "Content-Type": "application/json",
            "authorization": "Bearer mock_token",
        }
        if auth_header:
            headers["auth"] = '{"role": 1, "client": "mock_client_id"}'
        mock_request.assert_called_once_with(
            method,
            "https://20230124t120606-dot-gaposa-prod.ew.r.appspot.com" + path,
            headers=headers,
            data=json.dumps(expected_request) if expected_request is not None else None,
        )

    @parameterized.expand(
        [
            [
                "login",
                False,
                False,
                [],
                expected_login_response,
                'is missing required key(s): "Clients", "TermsAgreed", "UserRole"',
            ],
            [
                "users",
                True,
                False,
                [],
                expected_users_response,
                'is missing required key(s): "Info"',
            ],
            [
                "control",
                True,
                True,
                [Command.DOWN, "group", "1"],
                expected_control_response,
                'is missing required key(s): "Success"',
            ],
            [
                "control",
                True,
                True,
                [Command.DOWN, "channel", "1"],
                expected_control_response,
                'is missing required key(s): "Success"',
            ],
        ]
    )
    async def test_api_call_invalid_response(
        self,
        fn: str,
        auth_header: bool,
        serial: bool,
        args: List,
        expected_response: Dict,
        expected_failure: str,
    ):
        expected_response = expected_response.copy()
        expected_response["result"] = {}

        self.setupWebRequestMock(expected_response)
        if auth_header:
            self.api.setClientAndRole("mock_client_id", 1)
        if serial:
            self.api.setSerial("mock_serial")

        try:
            await getattr(self.api, fn)(*args)
            self.fail("Expected exception")
        except TypeCheckError as exception:
            self.assertIsInstance(exception, TypeCheckError)
            self.assertEqual(exception.args[0], expected_failure)

    @parameterized.expand(
        [
            ["login", False, False, []],
            ["users", True, False, []],
            ["control", True, True, [Command.DOWN, "group", "1"]],
            ["control", True, True, [Command.DOWN, "channel", "1"]],
        ]
    )
    async def test_api_call_exception(
        self, fn: str, auth_header: bool, serial: bool, args: List
    ):
        expected_exception = Exception("mock_exception")

        self.setupWebRequestMockException(expected_exception)
        if auth_header:
            self.api.setClientAndRole("mock_client_id", 1)
        if serial:
            self.api.setSerial("mock_serial")

        try:
            await getattr(self.api, fn)(*args)
            self.fail("Expected exception")
        except Exception as exception:
            self.assertIsInstance(exception, Exception)
            self.assertEqual(exception.args[0], "mock_exception")

    @parameterized.expand(
        [
            ["login", False, False, []],
            ["users", True, False, []],
            ["control", True, True, [Command.DOWN, "group", "1"]],
            ["control", True, True, [Command.DOWN, "channel", "1"]],
        ]
    )
    async def test_api_call_json_exception(
        self, fn: str, auth_header: bool, serial: bool, args: List
    ):
        expected_exception = Exception("mock_exception")

        self.setupWebRequestMockJsonException(expected_exception)
        if auth_header:
            self.api.setClientAndRole("mock_client_id", 1)
        if serial:
            self.api.setSerial("mock_serial")

        try:
            await getattr(self.api, fn)(*args)
            self.fail("Expected exception")
        except Exception as exception:
            self.assertIsInstance(exception, Exception)
            self.assertEqual(exception.args[0], "mock_exception")


if __name__ == "__main__":
    unittest.main()

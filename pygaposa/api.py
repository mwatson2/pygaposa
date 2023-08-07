import json
import logging
from typing import Awaitable, Callable, Literal, Optional, Union

from aiohttp import ClientSession
from typeguard import check_type

from pygaposa.api_types import (
    ApiControlRequest,
    ApiControlRequestChannel,
    ApiControlResponse,
    ApiLoginResponse,
    ApiRequestPayload,
    ApiScheduleEventRequest,
    ApiScheduleEventResponse,
    ApiScheduleRequest,
    ApiScheduleResponse,
    ApiUsersResponse,
    Command,
    ScheduleEventInfo,
    ScheduleEventType,
    ScheduleUpdate,
)

logging.basicConfig(level=logging.DEBUG)


class GaposaApi:
    """A class for interacting with the GAPOSA API.

    Arguments:
    ---------
        websession: An aiohttp ClientSession to use for requests.
        getToken: A callable that returns a valid Google Authentication token.
        serverUrl: The URL of the GAPOSA server to use.
    """

    # serverUrl: str = "https://20230124t120606-dot-gaposa-prod.ew.r.appspot.com"
    # serverUrl: str = "https://gaposa-prod.ew.r.appspot.com"
    serverUrl = "https://backend.rollapp.tech"

    def __init__(
        self,
        websession: ClientSession,
        getToken: Callable[[], Awaitable[str]],
        serverUrl: Optional[str] = None,
    ):
        self.serverUrl = serverUrl or GaposaApi.serverUrl
        self.websession = websession
        self.getToken = getToken
        self.logger = logging.getLogger("gaposa")

    def clone(self) -> "GaposaApi":
        """Create a new GaposaApi instance with the same configuration as this one.

        This enables us to create instances of the API with different configurations,
        for example for different clients and devices.
        """
        result = GaposaApi(self.websession, self.getToken, self.serverUrl)
        if hasattr(self, "client"):
            result.setClientAndRole(self.client, self.role)
        if hasattr(self, "serial"):
            result.setSerial(self.serial)
        return result

    def setClientAndRole(self, client: str, role: int):
        """Set the client and role for this API instance."""
        self.client = client
        self.role = role

    def setSerial(self, serial: str):
        """Set the serial number for this API instance."""
        self.serial = serial

    async def login(self) -> ApiLoginResponse:
        """Log in to the GAPOSA API."""
        response = await self.request("/v1/login")
        return check_type(response, ApiLoginResponse)

    async def users(self) -> ApiUsersResponse:
        """Get the list of users for the client set on this API instance."""
        assert hasattr(self, "client")
        response = await self.request("/v1/users")
        return check_type(response, ApiUsersResponse)

    async def control(
        self,
        command: Command,
        scope: Union[Literal["channel"], Literal["group"]],
        id: str,
    ):
        """Send a control command to a channel or group.

        This API instance must have been configured with client and device serial
        before calling this method.
        """
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        if scope == "channel":
            payload: ApiControlRequest = {
                "serial": self.serial,
                "data": {"cmd": command.value, "bank": 0, "address": int(id)},
            }
        else:
            payload = {
                "serial": self.serial,
                "group": id,
                "data": {"cmd": command.value},
            }

        response = await self.request("/v1/control", "POST", payload)
        return check_type(response, ApiControlResponse)

    async def addSchedule(self, schedule: ScheduleUpdate) -> ApiScheduleResponse:
        """Add a new schedule. This is a convenience method for addOrUpdateSchedule.

        This API instance must have been configured with client and device serial
        before calling this method.
        """
        assert "Id" not in schedule
        return await self.addOrUpdateSchedule(schedule)

    async def updateSchedule(self, schedule: ScheduleUpdate) -> ApiScheduleResponse:
        """Update an existing schedule.

        This is a convenience method for addOrUpdateSchedule.

        This API instance must have been configured with client and device serial
        before calling this method.
        """
        assert "Id" in schedule
        return await self.addOrUpdateSchedule(schedule)

    async def addOrUpdateSchedule(
        self, schedule: ScheduleUpdate
    ) -> ApiScheduleResponse:
        """Add or update a schedule.

        This API instance must have been configured with client and device serial
        before calling this method.
        """
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        method = "POST" if "Id" not in schedule else "PUT"
        payload: ApiScheduleRequest = {"serial": self.serial, "schedule": schedule}
        response = await self.request("/v1/schedules", method, payload)
        return check_type(response, ApiScheduleResponse)

    async def deleteSchedule(self, Id: str) -> ApiScheduleResponse:
        """Delete a schedule.

        This API instance must have been configured with client and device serial
        before calling this method.
        """
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        payload: ApiScheduleRequest = {"serial": self.serial, "schedule": {"Id": Id}}
        response = await self.request("/v1/schedules", "DELETE", payload)
        return check_type(response, ApiScheduleResponse)

    async def addScheduleEvent(
        self, Id: str, Mode: ScheduleEventType, event: ScheduleEventInfo
    ) -> ApiScheduleEventResponse:
        """Add a new event to a schedule.

        This is a convenience method for updateScheduleEvent.

        Schedules have three events for the three possible operations,
        UP, DONW and PRESET. This is specified in the Mode argument.

        This API instance must have been configured with client and device serial
        before calling this method.
        """
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        payload: ApiScheduleEventRequest = {
            "serial": self.serial,
            "schedule": {"Id": Id, "Mode": Mode.value},
            "event": event,
        }
        response = await self.request("/v1/schedules/event", "PUT", payload)
        return check_type(response, ApiScheduleEventResponse)

    async def updateScheduleEvent(
        self, Id: str, Mode: ScheduleEventType, event: ScheduleEventInfo
    ) -> ApiScheduleEventResponse:
        """Update an existing event in a schedule.

        This is a convenience method for addScheduleEvent.

        Schedules have three events for the three possible operations,
        UP, DONW and PRESET. This is specified in the Mode argument.

        This API instance must have been configured with client and device serial
        before calling this method.
        """
        return await self.addScheduleEvent(Id, Mode, event)

    async def deleteScheduleEvent(
        self, Id: str, Mode: ScheduleEventType
    ) -> ApiScheduleEventResponse:
        """Delete an event from a schedule.

        Schedules have three events for the three possible operations,
        UP, DONW and PRESET. This is specified in the Mode argument.

        This API instance must have been configured with client and device serial
        before calling this method.
        """
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        payload: ApiScheduleEventRequest = {
            "serial": self.serial,
            "schedule": {"Id": Id, "Mode": Mode},
        }
        response = await self.request("/v1/schedules/event", "DELETE", payload)
        return check_type(response, ApiScheduleEventResponse)

    async def request(
        self,
        endpoint: str,
        method: str = "GET",
        payload: Optional[ApiRequestPayload] = None,
    ):
        idToken = await self.getToken()
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {idToken}",
        }
        if hasattr(self, "client"):
            headers["auth"] = json.dumps({"role": self.role, "client": self.client})

        data = json.dumps({"payload": payload}) if payload else None

        response = await self.websession.request(
            method,
            self.serverUrl + endpoint,
            headers=headers,
            data=data,
            raise_for_status=True,
        )

        self.logger.debug(f"Request: {method} {endpoint}")
        self.logger.debug(f"Headers: {headers}")
        self.logger.debug(f"Payload: {data}")
        self.logger.debug(f"Response: {response}")

        responseObject = await response.json()

        self.logger.debug(f"Response object: {responseObject}")

        return responseObject

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
    # serverUrl: str = "https://20230124t120606-dot-gaposa-prod.ew.r.appspot.com"
    serverUrl: str = "https://gaposa-prod.ew.r.appspot.com"

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
        result = GaposaApi(self.websession, self.getToken, self.serverUrl)
        if hasattr(self, "client"):
            result.setClientAndRole(self.client, self.role)
        if hasattr(self, "serial"):
            result.setSerial(self.serial)
        return result

    def setClientAndRole(self, client: str, role: int):
        self.client = client
        self.role = role

    def setSerial(self, serial: str):
        self.serial = serial

    async def login(self) -> ApiLoginResponse:
        response = await self.request("/v1/login")
        return check_type(response, ApiLoginResponse)

    async def users(self) -> ApiUsersResponse:
        assert hasattr(self, "client")
        response = await self.request("/v1/users")
        return check_type(response, ApiUsersResponse)

    async def control(
        self,
        command: Command,
        scope: Union[Literal["channel"], Literal["group"]],
        id: str,
    ):
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

        response = await self.request("/control", "POST", payload)
        return check_type(response, ApiControlResponse)

    async def addSchedule(self, schedule: ScheduleUpdate) -> ApiScheduleResponse:
        assert "Id" not in schedule
        return await self.addOrUpdateSchedule(schedule)

    async def updateSchedule(self, schedule: ScheduleUpdate) -> ApiScheduleResponse:
        assert "Id" in schedule
        return await self.addOrUpdateSchedule(schedule)

    async def addOrUpdateSchedule(
        self, schedule: ScheduleUpdate
    ) -> ApiScheduleResponse:
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        method = "POST" if "Id" not in schedule else "PUT"
        payload: ApiScheduleRequest = {"serial": self.serial, "schedule": schedule}
        response = await self.request("/v1/schedules", method, payload)
        return check_type(response, ApiScheduleResponse)

    async def deleteSchedule(self, Id: str) -> ApiScheduleResponse:
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        payload: ApiScheduleRequest = {"serial": self.serial, "schedule": {"Id": Id}}
        response = await self.request("/v1/schedules", "DELETE", payload)
        return check_type(response, ApiScheduleResponse)

    async def addScheduleEvent(
        self, Id: str, Mode: ScheduleEventType, event: ScheduleEventInfo
    ) -> ApiScheduleEventResponse:
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
        return await self.addScheduleEvent(Id, Mode, event)

    async def deleteScheduleEvent(
        self, Id: str, Mode: ScheduleEventType
    ) -> ApiScheduleEventResponse:
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

import json
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

from aiohttp import ClientSession
from typeguard import check_type

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


class GaposaApi:
    def __init__(
        self,
        websession: ClientSession,
        getToken: Callable[[], Awaitable[str]],
        serverUrl: str = "https://20230124t120606-dot-gaposa-prod.ew.r.appspot.com",
    ):
        self.serverUrl = serverUrl
        self.websession = websession
        self.getToken = getToken

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
        payload: ApiControlRequest = {
            "serial": self.serial,
            "data": {"cmd": command.value},
        }  # type: ignore
        payload[scope] = id  # type: ignore
        response = await self.request("/control", "POST", payload)
        return check_type(response, ApiControlResponse)

    async def addSchedule(self, schedule: ScheduleUpdate) -> ApiScheduleResponse:
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        payload: ApiScheduleRequest = {"serial": self.serial, "schedule": schedule}
        response = await self.request("/v1/schedules", "PUT", payload)
        return check_type(response, ApiScheduleResponse)

    async def updateSchedule(self, schedule: ScheduleUpdate) -> ApiScheduleResponse:
        return await self.addSchedule(schedule)

    async def deleteSchedule(self, Id: str) -> ApiScheduleResponse:
        assert hasattr(self, "client")
        assert hasattr(self, "serial")
        payload: ApiScheduleRequest = {"serial": self.serial, "schedule": {"Id": Id}}
        response = await self.request("/v1/schedules", "DELETE", payload)
        return check_type(response, ApiScheduleResponse)

    async def addScheduleEvent(
        self, Id: str, Mode: ScheduleEventType, event: ScheduleEvent
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
        self, Id: str, Mode: ScheduleEventType, event: ScheduleEvent
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
            method, self.serverUrl + endpoint, headers=headers, data=data
        )

        responseObject = await response.json()

        return responseObject

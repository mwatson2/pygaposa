import asyncio
import json
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union

import aiohttp
import suncalc
from firebase import FirebaseAuth, FirebaseConfig, initialize_app


class DeviceInfo(TypedDict):
    Name: str
    Serial: str


class ClientInfo(TypedDict):
    Role: int
    Name: str
    Devices: List[DeviceInfo]


class AuthResult(TypedDict):
    TermsAgreed: bool
    UserRole: int
    Clients: Dict[str, ClientInfo]


# Response for /v1/login
class ApiLoginResponse(TypedDict):
    apiStatus: Literal["Success"]
    msg: Literal["Auth"]
    result: AuthResult


class UserInfo(TypedDict):
    CountryId: str
    EmailAlert: bool
    Email: str
    Name: str
    Role: int
    Uid: str
    Active: bool
    CompoundLocation: str
    Country: str
    Joined: Dict[str, int]
    TermsAgreed: bool
    CountryCode: str
    Mobile: str


class UsersResult(TypedDict):
    Info: UserInfo


# Response for /v1/users
class ApiUsersResponse(TypedDict):
    apiStatus: Literal["success"]
    msg: Literal["Return user"]
    result: UsersResult


class Command(Enum):
    DOWN = "0xee"
    UP = "0xdd"
    STOP = "0xcc"


class EventDays(IntEnum):
    MON = 0
    TUE = 1
    WED = 2
    THU = 3
    FRI = 4
    SAT = 5
    SUN = 6
    ALL = 7
    WEEKDAYS = 8
    WEEKENDS = 9


NumericIdentifier = str
Location = TypedDict("Location", {"_latitude": float, "_longitude": float})
EventRepeat = tuple[bool, bool, bool, bool, bool, bool, bool]


class State(TypedDict):
    TimeStamp: str
    OnLine: bool
    LastCmd: str


class Info(TypedDict):
    Name: str
    ClientId: str


class Assistant(TypedDict):
    Alexa: bool
    Home: bool


class HeartBeat(TypedDict):
    Subnet: str
    Channels: str
    Software: str
    Signal: str
    Mode: str
    Frequency: str
    Gateway: str
    Ip: str


class Channel(TypedDict):
    StatusCode: int
    State: str
    HomeRunning: bool
    Location: str
    HomePercent: int
    Icon: str
    Name: str
    HomePaused: bool


class Room(TypedDict):
    Favourite: bool
    Motors: list[int]
    Name: str
    Icon: str


class Group(TypedDict):
    Favourite: bool
    Icon: str
    Name: str
    Motors: list[int]


class Schedule(TypedDict):
    Id: NumericIdentifier
    Name: str
    Groups: list[int]
    Location: Location
    Motors: list[int]
    Icon: str
    Active: bool


class ScheduleUpdate(TypedDict, total=False):
    Id: NumericIdentifier  # Omit the Id field to create a new schedule
    Name: str
    Groups: list[int]
    Location: Location
    Motors: list[int]
    Icon: str
    Active: bool


class DeviceDocument(TypedDict):
    State: State
    Info: Info
    Assistant: Assistant
    Channels: Dict[str, Channel]
    Rooms: Dict[str, Room]  # key is room name
    Groups: Dict[NumericIdentifier, Group]
    Schedule: Dict[NumericIdentifier, Schedule]
    HeartBeat: HeartBeat
    DeletedChannels: List[int]
    Pending: list
    Uid: list[str]


class EventMode(TypedDict):
    Sunrise: bool
    Sunset: bool
    TimeDay: bool


class ScheduleEvent(TypedDict):
    EventRepeat: EventRepeat
    TimeZone: str
    Active: bool
    FutureEvent: bool
    Submit: bool
    EventEpoch: int
    Location: Location
    Motors: list[int]
    EventMode: EventMode


class NamedItem(TypedDict):
    Name: str


class ScheduleEventType(Enum):
    UP = "UP"
    DOWN = "DOWN"
    PRESET = "PRESET"


class ApiControlResult(TypedDict):
    Success: Literal["OK"]


# Response for /control
class ApiControlResponse(TypedDict):
    apiCommand: Literal["Success"]
    msg: Literal["OK"]
    result: ApiControlResult


# Request for /v1/schedules (in "payload" field)
class ApiScheduleRequest(TypedDict):
    serial: str
    schedule: ScheduleUpdate


class ApiScheduleDeleteResult(TypedDict):
    Schedule: bool
    Down: bool
    Up: bool
    Preset: bool


# Response for /v1/schedules
class ApiScheduleResponse(TypedDict):
    apiStatus: Literal["success"]
    msg: Union[
        Literal["Schedule Update"], Literal["Schedule deleted"], Literal["Schedule Add"]
    ]
    result: Union[Literal["ok"], ApiScheduleDeleteResult, str]


class ScheduleEventSelector(TypedDict):
    Id: NumericIdentifier
    Mode: ScheduleEventType


# Request for /v1/schedules/event (in "payload" field)
class ApiScheduleEventRequest(TypedDict):
    serial: str
    schedule: ScheduleEventSelector
    event: ScheduleEvent


# Response for /v1/schedules/event
class ApiScheduleEventResponse(TypedDict):
    apiStatus: Literal["success"]
    msg: Literal["Schedule Add"]
    result: str


class ApiTimezoneResponse(TypedDict):
    dstOffset: int
    rawOffset: int
    status: Literal["OK"]
    timeZoneId: str
    timeZoneName: str


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
        self.serverUrl = "https://20230124t120606-dot-gaposa-prod.ew.r.appspot.com"
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
        self.document = None
        self.snapshot = None
        self.scheduleRef = None

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

    async def fetch(
        self, url: str, method: str = "GET", data=None, headers=None, params=None
    ):
        return await self.session.request(
            method, url, data=data, headers=headers, params=params
        )

    async def open(self, email: str, password: str):
        self.email = email
        self.password = password
        self.auth: FirebaseAuth = self.firebase.auth()
        await self.auth.sign_in_with_email_and_password(self.email, self.password)
        if not self.firebase.hasAuth:
            raise Exception("Failed to authenticate with Google")

        self.firestore = self.firebase.firestore()

        authResponse: ApiLoginResponse = await self.request("/v1/login", "GET")

        if authResponse["apiStatus"] != "Success":
            raise Exception("Failed to authenticate with Gaposa")

        clients: List[str] = list(authResponse["result"]["Clients"].keys())
        self.client: str = clients[0]
        self.clientInfo: ClientInfo = authResponse["result"]["Clients"][self.client]

        devices: List[DeviceInfo] = self.clientInfo["Devices"]
        self.serial: str = devices[0]["Serial"]

        userResponse: ApiUsersResponse = await self.request("/v1/users", "GET")

        if userResponse["apiStatus"] != "success":
            raise Exception("Failed to get user info from Gaposa")

        self.user: UserInfo = userResponse["result"]["Info"]

        if not hasattr(self, "location"):
            await self.setLocation(self.user["CompoundLocation"])

        if hasattr(self, "location") and not hasattr(self, "timeZone"):
            await self.setTimezone()

        self.document = self.firestore.child("Devices").child(self.serial)

        await self.update()

    async def close(self):
        if self.ownSession:
            await self.session.close()

    async def update(self):
        assert self.document is not None
        self.snapshot = await self.document.get()
        if self.snapshot is None:
            raise Exception("Failed to get device document")
        self.device: DeviceDocument = self.snapshot.val()  # type: ignore

        self.scheduleRef = self.document.child("Schedule")
        self.schedules = {}
        schedules = self.device["Schedule"]
        for schedule in schedules:
            scheduleUp = await self.scheduleRef.get(schedule + ".UP")
            scheduleDown = await self.scheduleRef.get(schedule + ".DOWN")
            schedulePreset = await self.scheduleRef.get(schedule + ".PRESET")
            self.schedules[schedule] = [
                scheduleUp.val() if scheduleUp else None,
                scheduleDown.val() if scheduleDown else None,
                schedulePreset.val() if schedulePreset else None,
            ]

    async def setLocation(self, address: str):
        query = {"address": address, "ekey": self.apiKey}
        response = await self.fetch("https://plus.codes/api", params=query)
        if response.ok:
            responseText = await response.text()
            location = json.loads(responseText)
            if location["status"] == "OK":
                self.location = (
                    location["plus_code"]["geometry"]["location"]["lat"],
                    location["plus_code"]["geometry"]["location"]["lng"],
                )
                await self.setTimezone()
            else:
                raise Exception(
                    f"Failed to get location for {address}: {location['status']}"
                )
        else:
            raise Exception(
                f"Failed to get location for {address}: "
                f"{response.status} {response.reason}"
            )

    async def setTimezone(self):
        assert hasattr(self, "location")
        query = {
            "location": f"{self.location[0]},{self.location[1]}",
            "timestamp": int(datetime.now().timestamp()),
            "key": self.apiKey,
        }
        tz = await self.fetch(
            "https://maps.googleapis.com/maps/api/timezone/json", params=query
        )
        if tz.ok:
            tzresponse: ApiTimezoneResponse = await tz.json()
            if tzresponse["status"] == "OK":
                self.timeZone = tzresponse
                self.timeZoneId = tzresponse["timeZoneId"]
            else:
                raise Exception(
                    f"Failed to get timezone for {self.location}: "
                    f"{tzresponse['status']}"
                )
        else:
            raise Exception(
                f"Failed to get timezone for {self.location}: {tz.status} {tz.reason}"
            )

    async def sendCommand(self, path: str, cmd: Command):
        type, name = path.split("/", 2)
        payload = {"serial": self.serial, "data": {"cmd": cmd.value}}
        if type == "motors":
            motor = self.findMotor(name)
            if not motor:
                return
            payload["channel"] = motor
        elif type == "groups":
            group = self.findGroup(name)
            if not group:
                return
            payload["group"] = group
        else:
            return

        result: ApiControlResponse = await self.request("/control", "POST", payload)
        if result["apiCommand"] != "Success":
            raise Exception(f"Failed to send command {cmd} to {path}: {result['msg']}")

        await self.update()

        return result

    async def addSchedule(self, Name: str, properties: Dict[str, Any]):
        Id = self.findSchedule(Name)
        if Id:
            return

        Id = self.nextScheduleId()

        Location = self.location
        if not Location:
            return

        schedule = {
            "Name": Name,
            "Id": Id,
            "Location": Location,
            "Icon": "noImg",
            **properties,
        }
        payload = {"serial": self.serial, "schedule": schedule}

        return await self.request("v1/schedules", "PUT", payload)

    async def deleteSchedule(self, NameOrId: str):
        Id = NameOrId
        if self.schedules[Id] is None:
            Id = self.findSchedule(NameOrId)
            if not Id:
                return

        payload = {"serial": self.serial, "schedule": {"Id": Id}}

        return await self.request("v1/schedules", "DELETE", payload)

    async def setScheduleProperties(self, name: str, properties: Dict[str, Any]):
        Id = self.findSchedule(name)
        if not Id:
            return

        payload = {"serial": self.serial, "schedule": {**properties, "Id": Id}}

        return await self.request("v1/schedules", "PUT", payload)

    async def setScheduleActive(self, name: str, Active: bool):
        return await self.setScheduleProperties(name, {"Active": Active})

    async def setScheduleEvent(
        self, name: str, Mode: ScheduleEventType, event: Dict[str, Any]
    ):
        Id = self.findSchedule(name)
        if not Id:
            return

        payload = {
            "serial": self.serial,
            "schedule": {"Id": Id, "Mode": Mode.value},
            "event": event,
        }

        return await self.request("v1/schedules/event", "PUT", payload)

    async def deleteScheduleEvent(
        self, name: str, Mode: ScheduleEventType
    ) -> ApiScheduleDeleteResult:
        # Fix me: this is a schedule event not a schedule
        Id = self.findSchedule(name)
        if not Id:
            raise Exception(f"Schedule {name} not found")

        payload = {"serial": self.serial, "schedule": {"Id": Id, "Mode": Mode.value}}

        result: ApiScheduleResponse = await self.request(
            "v1/schedules/event", "DELETE", payload
        )

        if result["apiStatus"] != "success":
            raise Exception(f"Failed to delete schedule event: {result['msg']}")

        await self.update()

        return result["result"]  # type: ignore

    async def setSunriseOpen(
        self,
        name: str,
        days: Union[EventDays, List[EventDays], EventRepeat] = EventDays.ALL,
    ):
        Id = self.findSchedule(name)
        if not Id:
            return

        EventEpoch = self.nextSuntimeEpoch("sunrise")
        if not self.timeZone:
            return

        return await self.setScheduleEvent(
            name,
            ScheduleEventType.UP,
            {
                "EventRepeat": getEventRepeat(days),
                "TimeZone": self.timeZone["timeZoneId"],
                "EventEpoch": EventEpoch,
                "EventMode": {"SunRise": True, "SunSet": False, "TimeDay": False},
                "Location": self.location,
                "FutureEvent": False,
                "Active": True,
                "Submit": True,
                "Motors": self.device["Schedule"][Id]["Motors"],
            },
        )

    async def setSunsetClose(
        self,
        name: str,
        days: Union[EventDays, List[EventDays], EventRepeat] = EventDays.ALL,
    ):
        Id = self.findSchedule(name)
        if not Id:
            return

        EventEpoch = self.nextSuntimeEpoch("sunset")
        if not self.timeZone:
            return

        return await self.setScheduleEvent(
            name,
            ScheduleEventType.DOWN,
            {
                "EventRepeat": getEventRepeat(days),
                "TimeZone": self.timeZone["timeZoneId"],
                "EventEpoch": EventEpoch,
                "EventMode": {"SunRise": False, "SunSet": True, "TimeDay": False},
                "Location": self.location,
                "FutureEvent": False,
                "Active": True,
                "Submit": True,
                "Motors": self.device["Schedule"][Id]["Motors"],
            },
        )

    def findMotor(self, name: str):
        return self.findItemByName(self.device["Channels"], name)

    def findGroup(self, name: str):
        return self.findItemByName(self.device["Groups"], name)

    def findSchedule(self, name: str):
        return self.findItemByName(self.device["Schedule"], name)

    def findItemByName(self, collection: Dict, name: str):
        itemIds = list(collection.keys())
        itemNames = [collection[id]["Name"] for id in itemIds]
        itemIndex = itemNames.index(name) if name in itemNames else -1
        return itemIds[itemIndex] if itemIndex != -1 else None

    def nextScheduleId(self):
        ids = [int(id) for id in self.schedules.keys()]
        max_id = max(ids)
        return str(max_id + 1)

    async def request(
        self, endpoint: str, method: str, payload: Optional[Dict[str, Any]] = None
    ):
        idToken = await self.auth.getToken()
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {idToken}",
        }
        if hasattr(self, "client"):
            headers["auth"] = json.dumps(
                {"role": self.clientInfo["Role"], "client": self.client}
            )

        data = json.dumps({"payload": payload}) if payload else None

        response = await self.fetch(
            self.serverUrl + endpoint, method=method, headers=headers, data=data
        )

        responseObject = await response.json()

        return responseObject

    def nextSuntimeEpoch(self, suntime: str):
        now = datetime.now()
        todaysTimes: Dict[str, datetime] = suncalc.get_times(
            now, self.location[0], self.location[1]
        )  # type: ignore
        if todaysTimes[suntime] < now:
            tomorrow = self.getDateTomorrow()
            tomorrowsTimes: Dict[str, datetime] = suncalc.get_times(
                tomorrow, self.location[0], self.location[1]
            )  # type: ignore
            return int(tomorrowsTimes[suntime].timestamp())
        else:
            return int(todaysTimes[suntime].timestamp())

    def getDateTomorrow(self):
        return datetime.now() + timedelta(days=1)


def getEventRepeat(days: Union[EventDays, List[EventDays], EventRepeat]) -> EventRepeat:
    if isinstance(days, tuple) or isinstance(days, list):
        if len(days) == 7 and all(isinstance(d, bool) for d in days):
            return tuple(days)  # type: ignore
        else:
            assert all(isinstance(d, EventDays) for d in days)
            return tuple(x in days for x in range(7))
    elif days == EventDays.ALL:
        return (True,) * len(EventDays)
    elif days == EventDays.WEEKDAYS:
        return (True, True, True, True, True, False, False)
    elif days == EventDays.WEEKENDS:
        return (False, False, False, False, False, True, True)
    else:
        return (i == days for i in range(7))  # type: ignore

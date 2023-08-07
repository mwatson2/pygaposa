from enum import Enum, IntEnum
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union


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
    DateFormat: Any
    TimeFormat: Any
    Theme: Any


# Response for /v1/login
class ApiLoginResponse(TypedDict):
    apiStatus: Literal["Success"]
    msg: Literal["Auth"]
    result: AuthResult


class UserInfo(TypedDict):
    CountryID: str
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


class Command(str, Enum):
    DOWN = "0xee"
    UP = "0xdd"
    STOP = "0xcc"
    PRESET = "0xad"


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
    Message: str


class Info(TypedDict):
    Name: str
    ClientId: str


class Assistant(TypedDict):
    Alexa: bool
    Home: bool


class HeartBeat(TypedDict):
    Subnet: str
    Channels: int
    Software: str
    Signal: int
    Mode: str
    Frequency: int
    Gateway: str
    Ip: str
    TxID: list[int]


class Channel(TypedDict):
    StatusCode: int
    State: str
    HomeRunning: bool
    Location: str
    HomePercent: int
    Icon: str
    Name: str
    HomePaused: bool


class RoomInfo(TypedDict):
    Favourite: bool
    Motors: list[int]
    Name: str
    Icon: str


class GroupInfo(TypedDict):
    Favourite: bool
    Icon: str
    Name: str
    Motors: list[int]
    Rooms: list[str]


class ScheduleInfo(TypedDict):
    Name: str
    Groups: list[int]
    Location: Location
    Motors: list[int]
    Icon: str
    Active: bool


class ScheduleUpdate(TypedDict, total=False):
    Id: NumericIdentifier
    Name: str
    Groups: list[int]
    Location: Location
    Motors: list[int]
    Icon: str
    Active: bool


class DeviceDocumentRequired(TypedDict):
    State: State
    Info: Info
    Assistant: Assistant
    Channels: Dict[str, Channel]
    Rooms: Dict[str, RoomInfo]  # key is room name
    Groups: Dict[NumericIdentifier, GroupInfo]
    HeartBeat: HeartBeat
    DeletedChannels: List[int]
    Pending: list
    Uid: list[str]


class DeviceDocument(DeviceDocumentRequired, total=False):
    Schedule: Dict[NumericIdentifier, ScheduleInfo]


class EventMode(TypedDict):
    SunRise: bool
    SunSet: bool
    TimeDay: bool


class ScheduleEventInfo(TypedDict):
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


class ScheduleEventType(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    PRESET = "PRESET"


class ApiControlResult(TypedDict):
    Success: Literal["OK"]


class ApiGroupControlData(TypedDict):
    cmd: str


class ApiChannelControlData(TypedDict):
    cmd: str
    bank: int
    address: int


# Request for /control
class ApiControlRequestBase(TypedDict):
    serial: str


class ApiControlRequestGroup(ApiControlRequestBase):
    group: str
    data: ApiGroupControlData


class ApiControlRequestChannel(ApiControlRequestBase):
    data: ApiChannelControlData


ApiControlRequest = Union[ApiControlRequestChannel, ApiControlRequestGroup]


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
    Mode: str


# Request for /v1/schedules/event (in "payload" field)
class ApiScheduleEventRequestBase(TypedDict):
    serial: str
    schedule: ScheduleEventSelector


class ApiScheduleEventRequest(ApiScheduleEventRequestBase, total=False):
    event: ScheduleEventInfo


# Response for /v1/schedules/event
class ApiScheduleEventResponse(TypedDict):
    apiStatus: Literal["success"]
    msg: Literal["Schedule Add"]
    result: str


ApiRequestPayload = Union[
    ApiScheduleRequest, ApiScheduleEventRequest, ApiControlRequest
]

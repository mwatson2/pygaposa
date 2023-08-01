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
    ScheduleEventInfo,
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
            "CountryID": "mock_country_id",
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
    "data": {"cmd": "0xee", "bank": 0, "address": 1},
}

expected_control_response: ApiControlResponse = {
    "apiCommand": "Success",
    "msg": "OK",
    "result": {"Success": "OK"},
}

add_schedule_update: ScheduleUpdate = {
    "Name": "mock_name",
    "Groups": [1],
    "Location": {"_latitude": 1, "_longitude": 1},
    "Icon": "mock_icon",
    "Active": True,
}

expected_add_schedule_request: ApiScheduleRequest = {
    "serial": "mock_serial",
    "schedule": add_schedule_update,
}

expected_add_schedule_response: ApiScheduleResponse = {
    "apiStatus": "success",
    "msg": "Schedule Add",
    "result": "ok",
}

update_schedule_update: ScheduleUpdate = {**add_schedule_update, "Id": "1"}

expected_update_schedule_request: ApiScheduleRequest = {
    "serial": "mock_serial",
    "schedule": update_schedule_update,
}

expected_update_schedule_response: ApiScheduleResponse = {
    "apiStatus": "success",
    "msg": "Schedule Update",
    "result": "ok",
}

delete_schedule_update: ScheduleUpdate = {"Id": "1"}

expected_delete_schedule_request: ApiScheduleRequest = {
    "serial": "mock_serial",
    "schedule": delete_schedule_update,
}

expected_delete_schedule_response: ApiScheduleResponse = {
    "apiStatus": "success",
    "msg": "Schedule deleted",
    "result": {"Schedule": True, "Down": True, "Up": True, "Preset": True},
}

schedule_event: ScheduleEventInfo = {
    "EventRepeat": [True, True, True, True, True, True, True],  # type: ignore
    "TimeZone": "mock_timezone",
    "Active": True,
    "FutureEvent": True,
    "Submit": True,
    "EventEpoch": 1,
    "Location": {"_latitude": 1, "_longitude": 1},
    "Motors": [2, 3],
    "EventMode": {"Sunrise": True, "Sunset": False, "TimeDay": False},
}

expected_schedule_event_request: ApiScheduleEventRequest = {
    "serial": "mock_serial",
    "schedule": {"Id": "1", "Mode": "UP"},
    "event": schedule_event,
}

expected_schedule_event_response: ApiScheduleEventResponse = {
    "apiStatus": "success",
    "msg": "Schedule Add",
    "result": "ok",
}

expected_delete_schedule_event_request: ApiScheduleEventRequest = {
    "serial": "mock_serial",
    "schedule": {"Id": "1", "Mode": "UP"},
}

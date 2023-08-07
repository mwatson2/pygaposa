from datetime import datetime
from typing import Literal, TypedDict

import aiohttp

from pygaposa.api_types import Location


class ApiTimezoneResponse(TypedDict):
    dstOffset: int
    rawOffset: int
    status: Literal["OK"]
    timeZoneId: str
    timeZoneName: str


class GeoApi:
    """A simple class for interacting with the Google Maps API.

    This class supports resolving locations from addresses
    and timezones from locations.
    """

    def __init__(self, session: aiohttp.ClientSession, apiKey: str):
        self.session = session
        self.apiKey = apiKey

    async def fetch(
        self, url: str, method: str = "GET", data=None, headers=None, params=None
    ):
        return await self.session.request(
            method, url, data=data, headers=headers, params=params
        )

    async def resolveLocation(self, address: str) -> tuple[float, float]:
        """Resolve a location from an address using the Google Maps API."""
        response = await self.fetch(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": address, "key": self.apiKey},
        )
        data = await response.json()
        if data["status"] != "OK":
            raise Exception(f"Failed to resolve location: {data['status']}")
        location = data["results"][0]["geometry"]["location"]
        return (location["lat"], location["lng"])

    async def resolveTimezone(self, location: tuple[float, float]) -> str:
        """Resolve a timezone from a location using the Google Maps API."""
        query = {
            "location": f"{location[0]},{location[1]}",
            "timestamp": int(datetime.now().timestamp()),
            "key": self.apiKey,
        }
        tz = await self.fetch(
            "https://maps.googleapis.com/maps/api/timezone/json", params=query
        )
        if tz.ok:
            tzresponse: ApiTimezoneResponse = await tz.json()
            if tzresponse["status"] == "OK":
                return tzresponse["timeZoneId"]
            else:
                raise Exception(
                    f"Failed to get timezone for {location}: {tzresponse['status']}"
                )
        else:
            raise Exception(
                f"Failed to get timezone for {location}: {tz.status} {tz.reason}"
            )

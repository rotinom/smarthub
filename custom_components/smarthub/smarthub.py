from datetime import datetime, timedelta
import json
import time
from typing import Any
import logging

from pydantic import BaseModel, SecretStr  # , field_serializer
import requests


class SeriesData(BaseModel):
    x: datetime
    y: float
    _enableDrilldown: bool


class Series(BaseModel):
    _type: str
    _color: str
    _name: str
    _meterNumber: str
    data: list[SeriesData]
    _isNet: bool
    _stack: str
    _dataGrouping: Any
    _yAxis: int
    _zIndex: int
    _visible: bool
    _turboThreshold: int
    _channel: int


class PollData(BaseModel):
    serviceLocationNumber: str
    accountNumber: str
    startDateTime: datetime
    endDateTime: datetime
    timeFrame: str
    industry: str
    unitOfMeasure: str
    connectDate: str
    hasDaily: bool
    hasHourly: bool
    type: str
    _xToOrderedInterval: dict  # I believe these are the intervals on the chart
    series: list[Series]
    _estimatedSeries: Any


class Poll(BaseModel):
    """The root of the response from the endpoint."""

    status: str
    data: dict[str, list[PollData]] | None


class Settings(BaseModel):
    """Used to request the data from the endpoint."""

    timeFrame: str = "HOURLY"
    userId: str
    screen: str = "USAGE_EXPLORER"
    includeDemand: bool = False
    serviceLocationNumber: str
    accountNumber: str
    industries: list[str] = ["ELECTRIC"]
    startDateTime: datetime
    endDateTime: datetime

    # @field_serializer("startDateTime", "endDateTime")
    def dump_datetime(self, v: datetime):
        return int(v.timestamp() * 1000)  # seconds -> milliseconds


class Credentials(BaseModel):
    userId: str
    password: SecretStr

    # @field_serializer("password", "password")
    def dump_secret(self, v):
        return v.get_secret_value()


_LOGGER: logging.Logger = logging.getLogger(__package__)


class SmarthubCoopApi:
    def __init__(
        self,
        url: str,
        userId: str,
        password: str,
        # service_location_number: str,
        # account_number: str,
    ):
        self._url = url
        self._credentials = Credentials(userId=userId, password=password)
        # self._service_location_number = service_location_number
        # self._account_number = account_number

    def test_auth(self):
        try:
            s = self._get_session()
            return True
        except Exception as e:
            print(e)
            return False

    def _get_session(self):
        _LOGGER.info("Getting session")
        session = requests.Session()
        _LOGGER.info("Got session")

        _LOGGER.info(f"Using credentials: {self._credentials}")
        # _LOGGER.info(f"Using credentials: {self._credentials.model_dump()}")

        auth_resp = session.post(
            f"https://{self._url}/services/oauth/auth/v2" % (self._url),
            data=self._credentials.model_dump(),
        )

        if auth_resp.status_code != 200:
            raise Exception(
                f"Failed to authenticate with username: {self._credentials.userId} (HTTP Code: {auth_resp.status_code})"
            )
        token = "Bearer " + auth_resp.json()["authorizationToken"]
        # print("Using auth token: %s" % token)
        session.headers["Authorization"] = (
            "Bearer " + auth_resp.json()["authorizationToken"]
        )
        return session

    def deserialize_poll(self, json: str) -> Poll:
        return Poll.parse_raw(json)

    async def poll_for_data(
        self,
        service_location_number: str,
        account_number: str,
        start_date_time: datetime,
        end_date_time: datetime,
        timeout: timedelta = timedelta(seconds=20),
    ):
        """Poll the service for data"""

        _LOGGER.info(
            f"Polling for data for account {account_number} at location {service_location_number} between {start_date_time} and {end_date_time}"
        )

        settings = Settings(
            userId=self._credentials.userId,
            serviceLocationNumber=service_location_number,
            accountNumber=account_number,
            startDateTime=start_date_time,
            endDateTime=end_date_time,
        )
        _LOGGER.info(f"Settings: {settings}")

        session = self._get_session()
        _LOGGER.info(f"Session: {session}")

        while True:
            _LOGGER.info(f"POST'ing data {settings.model_dump_json()}")
            r = session.post(
                f"https://{self._url}/services/secured/utility-usage/poll",
                data=settings.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )

            j = json.loads(r.text)
            _LOGGER.info(f"Got results of {j}")
            if j["status"] != "PENDING":
                with open("data.json", "w") as outfile:
                    outfile.write(r.text)
                return r.text

            time.sleep(1)

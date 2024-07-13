"""Sample API Client."""

import asyncio
import logging
import socket

import aiohttp
from .smarthub import SmarthubCoopApi
from datetime import datetime, timedelta

TIMEOUT = 10


_LOGGER: logging.Logger = logging.getLogger(__package__)

HEADERS = {"Content-type": "application/json; charset=UTF-8"}


class SmarthubApiClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        url: str,
        service_location: str,
        account_number: str,
    ) -> None:
        self._username = username
        self._password = password
        self._url = url
        self._service_location = service_location
        self._account_number = account_number
        self._session = session
        self._smarthub = SmarthubCoopApi(self._url, self._username, self._password)

    async def async_get_data(self) -> dict:
        """Get data from the API."""
        try:
            return await self._smarthub.poll_for_data(
                self._service_location,
                self._account_number,
                datetime.now() - timedelta(hours=1),
                datetime.now(),
            )
        except Exception as e:
            print(e)
        # url = "https://jsonplaceholder.typicode.com/posts/1"
        # return await self.api_wrapper("get", url)

    async def async_set_title(self, value: str) -> None:
        """Get data from the API."""
        url = "https://jsonplaceholder.typicode.com/posts/1"
        await self.api_wrapper("patch", url, data={"title": value}, headers=HEADERS)

    async def api_wrapper(
        self, method: str, url: str, data: dict = {}, headers: dict = {}
    ) -> dict:
        """Get information from the API."""
        try:
            async with asyncio.timeout(TIMEOUT, loop=asyncio.get_event_loop()):
                if method == "get":
                    response = await self._session.get(url, headers=headers)
                    return await response.json()

                elif method == "put":
                    await self._session.put(url, headers=headers, json=data)

                elif method == "patch":
                    await self._session.patch(url, headers=headers, json=data)

                elif method == "post":
                    await self._session.post(url, headers=headers, json=data)

        except TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s",
                url,
                exception,
            )

        except (KeyError, TypeError) as exception:
            _LOGGER.error(
                "Error parsing information from %s - %s",
                url,
                exception,
            )
        except (aiohttp.ClientError, socket.gaierror) as exception:
            _LOGGER.error(
                "Error fetching information from %s - %s",
                url,
                exception,
            )
        except Exception as exception:  # pylint: disable=broad-except
            _LOGGER.error("Something really wrong happened! - %s", exception)

import aiohttp
import logging
from typing import Optional

from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

class KlokkuApiError(Exception):
    """Base exception for all Klokku API errors."""
    pass

class KlokkuAuthenticationError(KlokkuApiError):
    """Raised when authentication fails or user is not authenticated."""
    pass

class KlokkuNetworkError(KlokkuApiError):
    """Raised when there's a network-related error."""
    pass

class KlokkuApiResponseError(KlokkuApiError):
    """Raised when the API returns an error response."""
    def __init__(self, status_code: int, message: str = None):
        self.status_code = status_code
        self.message = message
        super().__init__(f"API returned error {status_code}: {message}")

class KlokkuDataParsingError(KlokkuApiError):
    """Raised when there's an error parsing the API response data."""
    pass

class KlokkuDataStructureError(KlokkuApiError):
    """Raised when the API response data doesn't have the expected structure."""
    pass

@dataclass(frozen=True)
class Budget:
    id: int
    name: str
    weeklyTime: int
    icon: str = ""
    status: str = "ACTIVE"

@dataclass(frozen=True)
class User:
    id: int
    username: str
    display_name: str

@dataclass(frozen=True)
class Event:
    id: int
    startTime: str
    budget: Budget

class KlokkuApi:

    url: str = ""
    username: str = ""
    user_id: int = 0
    session: Optional[aiohttp.ClientSession] = None

    def __init__(self, url):
        self.url = url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def authenticate(self, username: str) -> bool:
        """
        Authenticate with the API using a username.
        :param username: The username to authenticate with.
        :return: True if authentication was successful, False otherwise.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        :raises KlokkuDataStructureError: If the response doesn't have the expected structure.
        """
        try:
            users = await self.get_users()
            if not users:
                return False
            for user in users:
                if user.username == username:
                    self.user_id = user.id
                    return True
            return False
        except KlokkuApiError as e:
            _LOGGER.error(f"Authentication error: {e}")
            return False

    @staticmethod
    def __headers(user_id: int) -> dict:
        return {
            "X-User-Id": str(user_id)
        }

    async def get_current_event(self) -> Event | None:
        """
        Fetch the current budget from the API.
        :return: Parsed current budget data as a dictionary.
        :raises KlokkuAuthenticationError: If the user is not authenticated.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        :raises KlokkuDataStructureError: If the response doesn't have the expected structure.
        """
        if not self.user_id:
            error = KlokkuAuthenticationError("Unauthenticated - cannot fetch current budget")
            _LOGGER.warning(str(error))
            return None

        url = f"{self.url}api/event/current"
        try:
            # Create a session if one doesn't exist
            if not self.session:
                self.session = aiohttp.ClientSession()
                close_after = True
            else:
                close_after = False

            try:
                async with self.session.get(url, headers=self.__headers(self.user_id)) as response:
                    if response.status >= 400:
                        error_msg = await response.text()
                        raise KlokkuApiResponseError(response.status, error_msg)

                    try:
                        data = await response.json()
                    except aiohttp.ClientResponseError as e:
                        raise KlokkuDataParsingError(f"Failed to parse JSON response: {e}")

                    try:
                        result = Event(
                            id=data["id"],
                            startTime=data["startTime"],
                            budget=Budget(**data["budget"]),
                        )
                    except (KeyError, TypeError, ValueError) as e:
                        raise KlokkuDataStructureError(f"Unexpected data structure in response: {e}")
            except aiohttp.ClientConnectionError as e:
                raise KlokkuNetworkError(f"Connection error: {e}")

            # Close the session if we created it in this method
            if close_after:
                await self.session.close()
                self.session = None

            return result
        except KlokkuApiError as e:
            _LOGGER.error(f"Error fetching current budget: {e}")
            return None

    async def get_all_budgets(self) -> list[Budget] | None:
        """
        Fetch all budgets from the API.
        :return: Parsed list of all budgets.
        :raises KlokkuAuthenticationError: If the user is not authenticated.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        :raises KlokkuDataStructureError: If the response doesn't have the expected structure.
        """
        if not self.user_id:
            error = KlokkuAuthenticationError("Unauthenticated - cannot fetch budgets")
            _LOGGER.warning(str(error))
            return None

        url = f"{self.url}api/budget"
        try:
            # Create a session if one doesn't exist
            if not self.session:
                self.session = aiohttp.ClientSession()
                close_after = True
            else:
                close_after = False

            try:
                async with self.session.get(url, headers=self.__headers(self.user_id)) as response:
                    if response.status >= 400:
                        error_msg = await response.text()
                        raise KlokkuApiResponseError(response.status, error_msg)

                    try:
                        data = await response.json()
                    except aiohttp.ClientResponseError as e:
                        raise KlokkuDataParsingError(f"Failed to parse JSON response: {e}")

                    try:
                        result = [Budget(**budget) for budget in data]
                    except (KeyError, TypeError, ValueError) as e:
                        raise KlokkuDataStructureError(f"Unexpected data structure in response: {e}")
            except aiohttp.ClientConnectionError as e:
                raise KlokkuNetworkError(f"Connection error: {e}")

            # Close the session if we created it in this method
            if close_after:
                await self.session.close()
                self.session = None

            return result
        except KlokkuApiError as e:
            _LOGGER.error(f"Error fetching all budgets: {e}")
            return None

    async def get_users(self) -> list[User] | None:
        """
        Fetch all users from the API.
        :return: Parsed list of all users.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        :raises KlokkuDataStructureError: If the response doesn't have the expected structure.
        """
        url = f"{self.url}api/user"
        try:
            # Create a session if one doesn't exist
            if not self.session:
                self.session = aiohttp.ClientSession()
                close_after = True
            else:
                close_after = False

            try:
                async with self.session.get(url) as response:
                    if response.status >= 400:
                        error_msg = await response.text()
                        raise KlokkuApiResponseError(response.status, error_msg)

                    try:
                        data = await response.json()
                    except aiohttp.ClientResponseError as e:
                        raise KlokkuDataParsingError(f"Failed to parse JSON response: {e}")

                    try:
                        result = [User(id=user["id"], username=user["username"], display_name=user["displayName"]) for user in data]
                    except (KeyError, TypeError) as e:
                        raise KlokkuDataStructureError(f"Unexpected data structure in response: {e}")
            except aiohttp.ClientConnectionError as e:
                raise KlokkuNetworkError(f"Connection error: {e}")

            # Close the session if we created it in this method
            if close_after:
                await self.session.close()
                self.session = None

            return result
        except KlokkuApiError as e:
            _LOGGER.error(f"Error fetching all users: {e}")
            return None

    async def set_current_budget(self, budget_id: int):
        """
        Sets the currently used budget.
        :param budget_id: The ID of the budget to set as current.
        :return: The response data or None if an error occurred.
        :raises KlokkuAuthenticationError: If the user is not authenticated.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        """
        if not self.user_id:
            error = KlokkuAuthenticationError("Unauthenticated - cannot set current budget")
            _LOGGER.warning(str(error))
            return None

        url = f"{self.url}api/event"
        try:
            # Create a session if one doesn't exist
            if not self.session:
                self.session = aiohttp.ClientSession()
                close_after = True
            else:
                close_after = False

            try:
                async with self.session.post(url, headers=self.__headers(self.user_id), json={"budgetId": budget_id}) as response:
                    if response.status >= 400:
                        error_msg = await response.text()
                        raise KlokkuApiResponseError(response.status, error_msg)

                    try:
                        data = await response.json()
                    except aiohttp.ClientResponseError as e:
                        raise KlokkuDataParsingError(f"Failed to parse JSON response: {e}")
            except aiohttp.ClientConnectionError as e:
                raise KlokkuNetworkError(f"Connection error: {e}")

            # Close the session if we created it in this method
            if close_after:
                await self.session.close()
                self.session = None

            return data
        except KlokkuApiError as e:
            _LOGGER.error(f"Error setting current budget: {e}")
            return None

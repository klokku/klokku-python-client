from datetime import datetime
from enum import Enum

import aiohttp
import logging
from typing import Optional

from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)


class KlokkuApiError(Exception):
    """Base exception for all Klokku API errors."""
    pass


class KlokkuAuthenticationError(KlokkuApiError):
    """Raised when authentication fails or a user is not authenticated."""
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
class WeeklyItem:
    id: int
    budgetItemId: int
    name: str
    weeklyDuration: int
    weeklyOccurrences: int = 0
    icon: str = ""
    color: str = ""
    notes: str = ""
    position: int = 0

@dataclass(frozen=True)
class WeeklyPlan:
    budgetPlanId: int
    items: list[WeeklyItem]


@dataclass(frozen=True)
class User:
    uid: str
    username: str
    display_name: str


@dataclass(frozen=True)
class CurrentEventPlanItem:
    budgetItemId: int
    name: str
    weeklyDuration: int


@dataclass(frozen=True)
class CurrentEvent:
    planItem: CurrentEventPlanItem
    startTime: str


class AuthType(Enum):
    PERSONAL_ACCESS_TOKEN = "personal_access_token"
    USERNAME = "username"
    NONE = "none"


class KlokkuApi:
    url: str = ""
    username: str = ""
    authentication_type: AuthType = AuthType.NONE
    authenticated_user_uid: str = ""
    personal_access_token: str = ""
    session: Optional[aiohttp.ClientSession] = None

    def __init__(self, url):
        if not url.endswith("/"):
            url += "/"
        self.url = url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def authenticate(self, username_or_token: str) -> bool:
        """
        Authenticate with the API using a username.
        :param username_or_token: The username or personal access token to authenticate with.
        :return: True if authentication was successful, False otherwise.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        :raises KlokkuDataStructureError: If the response doesn't have the expected structure.
        """
        authenticate_with_pat = self.is_personal_access_token(username_or_token)
        if not authenticate_with_pat:
            try:
                username = username_or_token
                users = await self.get_users()
                if not users:
                    return False
                for user in users:
                    if user.username == username:
                        self.authenticated_user_uid = user.uid
                        self.authentication_type = AuthType.USERNAME
                        return True
                return False
            except KlokkuApiError as e:
                _LOGGER.error(f"Authentication error: {e}")
                self.authentication_type = AuthType.NONE
                self.authenticated_user_uid = ""
                return False
        else:
            try:
                self.personal_access_token = username_or_token
                self.authentication_type = AuthType.PERSONAL_ACCESS_TOKEN
                current_user = await self.get_current_user()
                if not current_user:
                    self.personal_access_token = ""
                    self.authentication_type = AuthType.NONE
                    return False
                self.authenticated_user_uid = current_user.uid
                self.authentication_type = AuthType.PERSONAL_ACCESS_TOKEN
                return True
            except KlokkuApiError as e:
                _LOGGER.error(f"Authentication error: {e}")
                self.personal_access_token = ""
                self.authentication_type = AuthType.NONE
                return False

    def __headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.authentication_type == AuthType.USERNAME:
            headers["X-User-Id"] = self.authenticated_user_uid
        elif self.authentication_type == AuthType.PERSONAL_ACCESS_TOKEN:
            headers["Authorization"] = f"Bearer {self.personal_access_token}"
        return headers

    @staticmethod
    def is_personal_access_token(username_or_token: str) -> bool:
        """
        Check if the provided username_or_token is a personal access token.
        Personal access tokens start with `pat.`
        """
        return username_or_token.startswith("pat.")

    def is_authenticated(self) -> bool:
        return self.authentication_type != AuthType.NONE

    async def get_current_user(self) -> User | None:
        """
        Fetch the current user data from the API.
        :return: Parsed current user data as a dictionary.
        :raises KlokkuAuthenticationError: If the user is not authenticated.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        :raises KlokkuDataStructureError: If the response doesn't have the expected structure.
        """
        if not self.is_authenticated():
            error = KlokkuAuthenticationError("Unauthenticated - cannot fetch current user")
            _LOGGER.warning(str(error))
            return None

        url = f"{self.url}api/user/current"

        try:
            # Create a session if one doesn't exist
            if not self.session:
                self.session = aiohttp.ClientSession()
                close_after = True
            else:
                close_after = False

            try:
                async with self.session.get(url, headers=self.__headers()) as response:
                    if response.status >= 400:
                        error_msg = await response.text()
                        raise KlokkuApiResponseError(response.status, error_msg)

                    try:
                        data = await response.json()
                    except aiohttp.ClientResponseError as e:
                        raise KlokkuDataParsingError(f"Failed to parse JSON response: {e}")

                    try:
                        result = User(
                            uid=data["uid"],
                            username=data["username"],
                            display_name=data["displayName"],
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
            _LOGGER.error(f"Error fetching current user: {e}")
            return None

    async def get_current_event(self) -> CurrentEvent | None:
        """
        Fetch the current event from the API.
        :return: Current event
        :raises KlokkuAuthenticationError: If the user is not authenticated.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        :raises KlokkuDataStructureError: If the response doesn't have the expected structure.
        """
        if not self.is_authenticated():
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
                async with self.session.get(url, headers=self.__headers()) as response:
                    if response.status >= 400:
                        error_msg = await response.text()
                        raise KlokkuApiResponseError(response.status, error_msg)

                    try:
                        data = await response.json()
                    except aiohttp.ClientResponseError as e:
                        raise KlokkuDataParsingError(f"Failed to parse JSON response: {e}")

                    try:
                        result = CurrentEvent(
                            planItem=CurrentEventPlanItem(**data["planItem"]),
                            startTime=data["startTime"],
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
            _LOGGER.error(f"Error fetching current event: {e}")
            return None

    async def get_current_week_plan(self) -> WeeklyPlan | None:
        """
        Fetch the current week plan from the API.
        :return: Parsed current week plan.
        :raises KlokkuAuthenticationError: If the user is not authenticated.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        :raises KlokkuDataStructureError: If the response doesn't have the expected structure.
        """
        if not self.is_authenticated():
            error = KlokkuAuthenticationError("Unauthenticated - cannot fetch weekly plan")
            _LOGGER.warning(str(error))
            return None

        now = datetime.now().astimezone().isoformat()
        url = f"{self.url}api/weeklyplan"
        try:
            # Create a session if one doesn't exist
            if not self.session:
                self.session = aiohttp.ClientSession()
                close_after = True
            else:
                close_after = False

            try:
                async with self.session.get(url, headers=self.__headers(), params={"date": now}) as response:
                    if response.status >= 400:
                        error_msg = await response.text()
                        raise KlokkuApiResponseError(response.status, error_msg)

                    try:
                        data = await response.json()
                    except aiohttp.ClientResponseError as e:
                        raise KlokkuDataParsingError(f"Failed to parse JSON response: {e}")

                    try:
                        result = WeeklyPlan(
                            budgetPlanId=data["budgetPlanId"],
                            items=[WeeklyItem(**item) for item in data["items"]]
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
            _LOGGER.error(f"Error fetching weekly plan: {e}")
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
                        result = [User(uid=user["uid"], username=user["username"], display_name=user["displayName"]) for user in data]
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

    async def set_current_event(self, budget_item_id: int):
        """
        Change the current event to the specified weekly item.
        :param budget_item_id: The ID of the weekly item to set as current.
        :return: The response data or None if an error occurred.
        :raises KlokkuAuthenticationError: If the user is not authenticated.
        :raises KlokkuNetworkError: If there's a network error.
        :raises KlokkuApiResponseError: If the API returns an error response.
        :raises KlokkuDataParsingError: If there's an error when parsing the response.
        """
        if not self.is_authenticated():
            error = KlokkuAuthenticationError("Unauthenticated - cannot set current event")
            _LOGGER.warning(str(error))
            return None

        weekly_plan = await self.get_current_week_plan()
        if not weekly_plan:
            return None

        # Find item on weekly plan with the specified budgetItemId
        item = next((i for i in weekly_plan.items if i.budgetItemId == budget_item_id), None)
        if not item:
            _LOGGER.warning(f"Item with budget_item_id {budget_item_id} not found in weekly plan")
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
                async with self.session.post(url,
                                             headers=self.__headers(),
                                             json={
                                                 "budgetItemId": item.budgetItemId,
                                                 "name": item.name,
                                                 "weeklyDuration": item.weeklyDuration
                                             }) as response:
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

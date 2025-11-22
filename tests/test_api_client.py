import pytest
import json
from aioresponses import aioresponses, CallbackResult
from klokku_python_client.api_client import KlokkuApi, Budget, User, Event, AuthType

# Constants for testing
TEST_URL = "http://klokku-api.example.com/"
TEST_USER_UID = "32cefa4d-87c6-43ae-b36c-83378bf1f1b4"
TEST_USERNAME = "testuser"
TEST_PAT = "pat.-7GzL3M1.lk4j53GGDF456yHFh_gdf45yhdfh"


@pytest.fixture
def mock_aioresponse():
    """Fixture to mock aiohttp responses."""
    with aioresponses() as m:
        yield m


@pytest.fixture
async def api_client():
    """Fixture to create a KlokkuApi instance."""
    client = KlokkuApi(TEST_URL)
    yield client
    # Clean up
    if client.session:
        await client.session.close()


def _mock_path_authenticated_response(token, body):
    def _callback(url, **kwargs):
        # Check if the Authorization header contains the correct Bearer token
        req_headers = kwargs.get("headers") or {}
        auth_header = req_headers.get("Authorization", "")

        if auth_header == f"Bearer {token}":
            return CallbackResult(status=200, body=body)
        else:
            return CallbackResult(status=401, body=json.dumps({"error": "Unauthorized"}))
    return _callback


async def test_authenticate_with_username_success(api_client, mock_aioresponse):
    """Test successful authentication with a username."""
    # Mock the get_users response
    users_data = [
        {"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"},
        {"uid": "cf479ef7-bbc5-413d-8b1b-bec6962d9174", "username": "otheruser", "displayName": "Other User"}
    ]
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=users_data)
    
    # Call authenticate
    result = await api_client.authenticate(TEST_USERNAME)
    
    # Verify results
    assert result is True
    assert api_client.authenticated_user_uid == TEST_USER_UID
    assert api_client.authentication_type == AuthType.USERNAME

async def test_authenticate_user_not_found(api_client, mock_aioresponse):
    """Test authentication when a user is not found."""
    # Mock the get_users response
    users_data = [
        {"uid": "cf479ef7-bbc5-413d-8b1b-bec6962d9174", "username": "otheruser", "displayName": "Other User"}
    ]
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=users_data)
    
    # Call authenticate
    result = await api_client.authenticate("nonexistentuser")
    
    # Verify results
    assert result is False
    assert api_client.authentication_type == AuthType.NONE


async def test_authenticate_api_error(api_client, mock_aioresponse):
    """Test authentication when API returns an error."""
    # Mock the get_users response with an error
    mock_aioresponse.get(f"{TEST_URL}api/user", status=500)
    
    # Call authenticate
    result = await api_client.authenticate(TEST_USERNAME)
    
    # Verify results
    assert result is False
    assert api_client.authentication_type == AuthType.NONE

async def test_authenticate_with_pat_success(api_client, mock_aioresponse):
    """Test successful authentication with a personal access token."""
    # Mock the get_current_user response
    user_data = {"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}
    mock_aioresponse.get(f"{TEST_URL}api/user/current", callback=_mock_path_authenticated_response(TEST_PAT, json.dumps(user_data)))

    # Call authenticate
    result = await api_client.authenticate(TEST_PAT)

    # Verify results
    assert result is True
    assert api_client.personal_access_token == TEST_PAT
    assert api_client.authenticated_user_uid == TEST_USER_UID
    assert api_client.authentication_type == AuthType.PERSONAL_ACCESS_TOKEN

async def test_authenticate_with_pat_failure(api_client, mock_aioresponse):
    """Test failed authentication with an incorrect personal access token."""
    # Mock the get_current_user response
    user_data = {"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}

    mock_aioresponse.get(f"{TEST_URL}api/user/current", callback=_mock_path_authenticated_response(TEST_PAT, json.dumps(user_data)))

    # Call authenticate
    result = await api_client.authenticate("invalid_token")

    # Verify results
    assert result is False
    assert api_client.authentication_type == AuthType.NONE

async def test_get_users_success(api_client, mock_aioresponse):
    """Test successful retrieval of users."""
    # Authenticate first to set user_uid
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=[{"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}])
    await api_client.authenticate(TEST_USERNAME)

    # Mock the get_users response
    users_data = [
        {"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"},
        {"uid": "cf479ef7-bbc5-413d-8b1b-bec6962d9174", "username": "otheruser", "displayName": "Other User"}
    ]
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=users_data)
    
    # Call get_users
    users = await api_client.get_users()
    
    # Verify results
    assert users is not None
    assert len(users) == 2
    assert isinstance(users[0], User)
    assert users[0].uid == TEST_USER_UID
    assert users[0].username == TEST_USERNAME
    assert users[0].display_name == "Test User"


async def test_get_users_error(api_client, mock_aioresponse):
    """Test get_users when API returns an error."""
    # Authenticate first to set user_uid
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=[{"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}])
    await api_client.authenticate(TEST_USERNAME)

    # Mock the get_users response with an error
    mock_aioresponse.get(f"{TEST_URL}api/user", status=500)
    
    # Call get_users
    users = await api_client.get_users()
    
    # Verify results
    assert users is None


async def test_get_all_budgets_success(api_client, mock_aioresponse):
    """Test successful retrieval of all budgets."""
    # Authenticate first to set user_uid
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=[{"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}])
    await api_client.authenticate(TEST_USERNAME)
    
    # Mock the get_all_budgets response
    budgets_data = [
        {"id": 1, "name": "Budget 1", "weeklyTime": 3600, "icon": "icon1", "startDate": "2024-09-08T00:00:00Z"},
        {"id": 2, "name": "Budget 2", "weeklyTime": 7200, "icon": "icon2", "startDate": "2025-09-08T00:00:00Z"},
    ]
    mock_aioresponse.get(
        f"{TEST_URL}api/budget",
        status=200,
        payload=budgets_data,
        headers={"X-User-Id": str(TEST_USER_UID)}
    )
    
    # Call get_all_budgets
    budgets = await api_client.get_all_budgets()
    
    # Verify results
    assert budgets is not None
    assert len(budgets) == 2
    assert isinstance(budgets[0], Budget)
    assert budgets[0].id == 1
    assert budgets[0].name == "Budget 1"
    assert budgets[0].weeklyTime == 3600
    assert budgets[0].icon == "icon1"
    assert budgets[0].startDate == "2024-09-08T00:00:00Z"


async def test_get_all_budgets_unauthenticated(api_client, mock_aioresponse):
    """Test get_all_budgets when not authenticated."""

    # Mock the get_all_budgets response
    budgets_data = [
        {"id": 1, "name": "Budget 1", "weeklyTime": 3600, "icon": "icon1", "startDate": "2024-09-08T00:00:00Z"},
        {"id": 2, "name": "Budget 2", "weeklyTime": 7200, "icon": "icon2", "startDate": "2025-09-08T00:00:00Z"},
    ]
    mock_aioresponse.get(
        f"{TEST_URL}api/budget",
        status=200,
        payload=budgets_data,
        headers={"X-User-Id": str(TEST_USER_UID)}
    )

    # Call get_all_budgets without setting user_uid
    budgets = await api_client.get_all_budgets()
    
    # Verify results
    assert budgets is None


async def test_get_all_budgets_error(api_client, mock_aioresponse):
    """Test get_all_budgets when API returns an error."""
    # Authenticate first to set user_uid
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=[{"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}])
    await api_client.authenticate(TEST_USERNAME)

    # Mock the get_all_budgets response with an error
    mock_aioresponse.get(
        f"{TEST_URL}api/budget",
        status=500,
        headers={"X-User-Id": str(TEST_USER_UID)}
    )
    
    # Call get_all_budgets
    budgets = await api_client.get_all_budgets()
    
    # Verify results
    assert budgets is None


async def test_get_current_event_success(api_client, mock_aioresponse):
    """Test successful retrieval of current event."""
    # Authenticate first to set user_uid
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=[{"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}])
    await api_client.authenticate(TEST_USERNAME)
    
    # Mock the get_current_event response
    event_data = {
        "id": 1,
        "startTime": "2023-01-01T12:00:00Z",
        "budget": {
            "id": 1,
            "name": "Budget 1",
            "weeklyTime": 3600,
            "icon": "icon1",
            "startDate": "2025-09-08T00:00:00Z"
        }
    }
    mock_aioresponse.get(
        f"{TEST_URL}api/event/current",
        status=200,
        payload=event_data,
        headers={"X-User-Id": str(TEST_USER_UID)}
    )
    
    # Call get_current_event
    event = await api_client.get_current_event()
    
    # Verify results
    assert event is not None
    assert isinstance(event, Event)
    assert event.id == 1
    assert event.startTime == "2023-01-01T12:00:00Z"
    assert isinstance(event.budget, Budget)
    assert event.budget.id == 1
    assert event.budget.name == "Budget 1"
    assert event.budget.weeklyTime == 3600
    assert event.budget.icon == "icon1"
    assert event.budget.startDate == "2025-09-08T00:00:00Z"


async def test_get_current_event_unauthenticated(api_client, mock_aioresponse):
    """Test get_current_event when not authenticated."""
    # Call get_current_event without setting user_uid
    event = await api_client.get_current_event()
    
    # Verify results
    assert event is None


async def test_get_current_event_error(api_client, mock_aioresponse):
    """Test get_current_event when API returns an error."""
    # Authenticate first to set user_uid
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=[{"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}])
    await api_client.authenticate(TEST_USERNAME)
    
    # Mock the get_current_event response with an error
    mock_aioresponse.get(
        f"{TEST_URL}api/event/current",
        status=500,
        headers={"X-User-Id": str(TEST_USER_UID)}
    )
    
    # Call get_current_event
    event = await api_client.get_current_event()
    
    # Verify results
    assert event is None


async def test_set_current_budget_success(api_client, mock_aioresponse):
    """Test successful setting of current budget."""
    # Authenticate first to set user_uid
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=[{"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}])
    await api_client.authenticate(TEST_USERNAME)
    budget_id = 1
    
    # Mock the set_current_budget response
    response_data = {"success": True}
    mock_aioresponse.post(
        f"{TEST_URL}api/event",
        status=200,
        payload=response_data,
        headers={"X-User-Id": str(TEST_USER_UID)}
    )
    
    # Call set_current_budget
    result = await api_client.set_current_budget(budget_id)
    
    # Verify results
    assert result is not None
    assert result["success"] is True


async def test_set_current_budget_unauthenticated(api_client, mock_aioresponse):
    """Test set_current_budget when not authenticated."""
    # Call set_current_budget without setting user_uid
    result = await api_client.set_current_budget(1)
    
    # Verify results
    assert result is None


async def test_set_current_budget_error(api_client, mock_aioresponse):
    """Test set_current_budget when API returns an error."""
    # Authenticate first to set user_uid
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=[{"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}])
    await api_client.authenticate(TEST_USERNAME)
    budget_id = 1
    
    # Mock the set_current_budget response with an error
    mock_aioresponse.post(
        f"{TEST_URL}api/event",
        status=500,
        headers={"X-User-Id": str(TEST_USER_UID)}
    )
    
    # Call set_current_budget
    result = await api_client.set_current_budget(budget_id)
    
    # Verify results
    assert result is None


async def test_context_manager(mock_aioresponse):
    """Test using KlokkuApi as a context manager."""
    async with KlokkuApi(TEST_URL) as client:
        # Verify session is created
        assert client.session is not None
        
        # Mock a simple API call
        users_data = [
            {"uid": TEST_USER_UID, "username": TEST_USERNAME, "displayName": "Test User"}
        ]
        mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=users_data)
        
        # Make the API call
        users = await client.get_users()
        
        # Verify results
        assert users is not None
        assert len(users) == 1
    
    # Verify session is closed after exiting context
    assert client.session is None
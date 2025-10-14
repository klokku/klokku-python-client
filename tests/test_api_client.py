import pytest
from aioresponses import aioresponses
from klokku_python_client.api_client import KlokkuApi, Budget, User, Event

# Constants for testing
TEST_URL = "http://klokku-api.example.com/"
TEST_USER_ID = 123
TEST_USERNAME = "testuser"


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


async def test_authenticate_success(api_client, mock_aioresponse):
    """Test successful authentication."""
    # Mock the get_users response
    users_data = [
        {"id": TEST_USER_ID, "username": TEST_USERNAME, "displayName": "Test User"},
        {"id": 456, "username": "otheruser", "displayName": "Other User"}
    ]
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=users_data)
    
    # Call authenticate
    result = await api_client.authenticate(TEST_USERNAME)
    
    # Verify results
    assert result is True
    assert api_client.user_id == TEST_USER_ID


async def test_authenticate_user_not_found(api_client, mock_aioresponse):
    """Test authentication when a user is not found."""
    # Mock the get_users response
    users_data = [
        {"id": 456, "username": "otheruser", "displayName": "Other User"}
    ]
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=users_data)
    
    # Call authenticate
    result = await api_client.authenticate("nonexistentuser")
    
    # Verify results
    assert result is False
    assert api_client.user_id == 0


async def test_authenticate_api_error(api_client, mock_aioresponse):
    """Test authentication when API returns an error."""
    # Mock the get_users response with an error
    mock_aioresponse.get(f"{TEST_URL}api/user", status=500)
    
    # Call authenticate
    result = await api_client.authenticate(TEST_USERNAME)
    
    # Verify results
    assert result is False
    assert api_client.user_id == 0


async def test_get_users_success(api_client, mock_aioresponse):
    """Test successful retrieval of users."""
    # Mock the get_users response
    users_data = [
        {"id": TEST_USER_ID, "username": TEST_USERNAME, "displayName": "Test User"},
        {"id": 456, "username": "otheruser", "displayName": "Other User"}
    ]
    mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=users_data)
    
    # Call get_users
    users = await api_client.get_users()
    
    # Verify results
    assert users is not None
    assert len(users) == 2
    assert isinstance(users[0], User)
    assert users[0].id == TEST_USER_ID
    assert users[0].username == TEST_USERNAME
    assert users[0].display_name == "Test User"


async def test_get_users_error(api_client, mock_aioresponse):
    """Test get_users when API returns an error."""
    # Mock the get_users response with an error
    mock_aioresponse.get(f"{TEST_URL}api/user", status=500)
    
    # Call get_users
    users = await api_client.get_users()
    
    # Verify results
    assert users is None


async def test_get_all_budgets_success(api_client, mock_aioresponse):
    """Test successful retrieval of all budgets."""
    # Set up user_id
    api_client.user_id = TEST_USER_ID
    
    # Mock the get_all_budgets response
    budgets_data = [
        {"id": 1, "name": "Budget 1", "weeklyTime": 3600, "icon": "icon1", "startDate": "2024-09-08T00:00:00Z"},
        {"id": 2, "name": "Budget 2", "weeklyTime": 7200, "icon": "icon2", "startDate": "2025-09-08T00:00:00Z"},
    ]
    mock_aioresponse.get(
        f"{TEST_URL}api/budget",
        status=200,
        payload=budgets_data,
        headers={"X-User-Id": str(TEST_USER_ID)}
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
    # Call get_all_budgets without setting user_id
    budgets = await api_client.get_all_budgets()
    
    # Verify results
    assert budgets is None


async def test_get_all_budgets_error(api_client, mock_aioresponse):
    """Test get_all_budgets when API returns an error."""
    # Set up user_id
    api_client.user_id = TEST_USER_ID
    
    # Mock the get_all_budgets response with an error
    mock_aioresponse.get(
        f"{TEST_URL}api/budget",
        status=500,
        headers={"X-User-Id": str(TEST_USER_ID)}
    )
    
    # Call get_all_budgets
    budgets = await api_client.get_all_budgets()
    
    # Verify results
    assert budgets is None


async def test_get_current_event_success(api_client, mock_aioresponse):
    """Test successful retrieval of current event."""
    # Set up user_id
    api_client.user_id = TEST_USER_ID
    
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
        headers={"X-User-Id": str(TEST_USER_ID)}
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
    # Call get_current_event without setting user_id
    event = await api_client.get_current_event()
    
    # Verify results
    assert event is None


async def test_get_current_event_error(api_client, mock_aioresponse):
    """Test get_current_event when API returns an error."""
    # Set up user_id
    api_client.user_id = TEST_USER_ID
    
    # Mock the get_current_event response with an error
    mock_aioresponse.get(
        f"{TEST_URL}api/event/current",
        status=500,
        headers={"X-User-Id": str(TEST_USER_ID)}
    )
    
    # Call get_current_event
    event = await api_client.get_current_event()
    
    # Verify results
    assert event is None


async def test_set_current_budget_success(api_client, mock_aioresponse):
    """Test successful setting of current budget."""
    # Set up user_id
    api_client.user_id = TEST_USER_ID
    budget_id = 1
    
    # Mock the set_current_budget response
    response_data = {"success": True}
    mock_aioresponse.post(
        f"{TEST_URL}api/event",
        status=200,
        payload=response_data,
        headers={"X-User-Id": str(TEST_USER_ID)}
    )
    
    # Call set_current_budget
    result = await api_client.set_current_budget(budget_id)
    
    # Verify results
    assert result is not None
    assert result["success"] is True


async def test_set_current_budget_unauthenticated(api_client, mock_aioresponse):
    """Test set_current_budget when not authenticated."""
    # Call set_current_budget without setting user_id
    result = await api_client.set_current_budget(1)
    
    # Verify results
    assert result is None


async def test_set_current_budget_error(api_client, mock_aioresponse):
    """Test set_current_budget when API returns an error."""
    # Set up user_id
    api_client.user_id = TEST_USER_ID
    budget_id = 1
    
    # Mock the set_current_budget response with an error
    mock_aioresponse.post(
        f"{TEST_URL}api/event",
        status=500,
        headers={"X-User-Id": str(TEST_USER_ID)}
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
            {"id": TEST_USER_ID, "username": TEST_USERNAME, "displayName": "Test User"}
        ]
        mock_aioresponse.get(f"{TEST_URL}api/user", status=200, payload=users_data)
        
        # Make the API call
        users = await client.get_users()
        
        # Verify results
        assert users is not None
        assert len(users) == 1
    
    # Verify session is closed after exiting context
    assert client.session is None
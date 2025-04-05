# Klokku Python Client Tests

This directory contains tests for the Klokku Python Client library.

## Overview

The tests use:
- `pytest` as the testing framework
- `pytest-asyncio` for testing asynchronous code
- `aioresponses` for mocking HTTP requests (similar to Wiremock)

## Running Tests

To run the tests, first install the package with test dependencies:

```bash
pip install -e ".[test]"
```

Or if you're using Poetry:

```bash
poetry install --with test
```

Then run the tests using pytest:

```bash
pytest
```

To run with verbose output:

```bash
pytest -v
```

## Test Coverage

The tests cover all methods in the `KlokkuApi` class:

- `authenticate`: Tests authentication with valid and invalid credentials
- `get_users`: Tests retrieving user information
- `get_all_budgets`: Tests retrieving all budgets
- `get_current_event`: Tests retrieving the current event
- `set_current_budget`: Tests setting the current budget

Each method is tested for:
- Success cases
- Error cases (API errors)
- Authentication requirements

The tests also verify that the context manager functionality works correctly.

## Mock HTTP Server

The tests use `aioresponses` to mock HTTP responses, which allows testing the API client without making actual HTTP requests. This is similar to Wiremock but integrated directly into Python.

Example of mocking a response:

```python
async def test_get_users(api_client, mock_aioresponse):
    # Mock the API response
    mock_aioresponse.get(
        "http://api.example.com/users",
        status=200,
        payload=[{"id": 1, "name": "User 1"}]
    )
    
    # Call the method
    users = await api_client.get_users()
    
    # Verify the result
    assert users is not None
    assert len(users) == 1
```
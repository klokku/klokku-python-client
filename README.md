# Klokku Python Client

A Python client for interacting with the Klokku REST API.

## Installation

### Using pip

```bash
pip install klokku-python-client
```

### Using Poetry

```bash
poetry add klokku-python-client
```

## Usage

The client provides an asynchronous interface to the Klokku API:

```python
import asyncio
from klokku_python_client import KlokkuApi

async def main():
    # Create a client instance
    async with KlokkuApi("https://app.klokku.com/") as client:
        # Authenticate with a username (self‑hosted) or a personal access token (cloud)
        # authenticated = await client.authenticate("your_username")
        authenticated = await client.authenticate("pat.<the-rest-of-the-token>")
        if not authenticated:
            print("Authentication failed")
            return

        # Get weekly plan
        weekly_plan = await client.get_current_week_plan()
        if not weekly_plan:
            print("Failed to fetch weekly plan")
            return

        if weekly_plan.items:
            print(f"Found {len(weekly_plan.items)} budgets:")
            for item in weekly_plan.items:
                print(f"- {item.name} (ID: {item.budgetItemId})")

        # Get current event
        current_event = await client.get_current_event()
        if current_event:
            print(f"Current item: {current_event.planItem.name}")
            print(f"Started at: {current_event.startTime}")

        # Set a different item
        if weekly_plan.items and len(weekly_plan.items) > 1:
            new_budget_id = weekly_plan.items[1].budgetItemId
            result = await client.set_current_event(new_budget_id)
            if result:
                print(f"Set current item to ID: {new_budget_id}")

# Run the async function
asyncio.run(main())
```

## Features

- Asynchronous API client using `aiohttp`
- Authentication with username
- Get list of users
- Get all budgets
- Get current event/budget
- Set current budget
- Context manager support for proper resource cleanup

## Development

### CI/CD

This project uses GitHub Actions for continuous integration and deployment:

1. **Build Workflow**: Runs on every push to the main branch, executing tests and building the package.
2. **Publish Workflow**: Automatically publishes the package to PyPI when a new GitHub Release is created.

To set up the publishing workflow:

1. Generate a PyPI API token at https://pypi.org/manage/account/token/
2. Add the token as a GitHub repository secret named `PYPI_API_TOKEN`
3. Create a new GitHub Release to trigger the publishing workflow

### Setup

1. Clone the repository
2. Install dependencies with Poetry:

```bash
poetry install
```

### Testing

The project uses pytest for testing with aioresponses for mocking HTTP requests.

To install test dependencies:

```bash
pip install -e ".[test]"
```

Or with Poetry:

```bash
poetry install --with test
```

To run the tests:

```bash
pytest
```

Or with Poetry

```bash
poetry run pytest
```

For more details about testing, see the [tests README](tests/README.md).

### Releasing

1. Upgrade the version in `pyproject.toml`
2. Create a new GitHub Release
3. The GitHub Actions build workflow will automatically publish the package to PyPI

## Requirements

- Python 3.13+
- aiohttp 3.12+

## License

[MIT](LICENSE)

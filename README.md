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
    async with KlokkuApi("https://api.klokku.example.com/") as client:
        # Authenticate with a username
        authenticated = await client.authenticate("your_username")
        if not authenticated:
            print("Authentication failed")
            return

        # Get all budgets
        budgets = await client.get_all_budgets()
        if budgets:
            print(f"Found {len(budgets)} budgets:")
            for budget in budgets:
                print(f"- {budget.name} (ID: {budget.id})")

        # Get current event
        current_event = await client.get_current_event()
        if current_event:
            print(f"Current budget: {current_event.budget.name}")
            print(f"Started at: {current_event.startTime}")

        # Set a different budget
        if budgets and len(budgets) > 1:
            new_budget_id = budgets[1].id
            result = await client.set_current_budget(new_budget_id)
            if result:
                print(f"Set current budget to ID: {new_budget_id}")

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

For more details about testing, see the [tests README](tests/README.md).

## Requirements

- Python 3.13+
- aiohttp 3.11+

## License

[MIT](LICENSE)

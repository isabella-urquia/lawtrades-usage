# Integrators API E2E Tests

This repository contains end-to-end tests for the integrators API.

## Setup

### Prerequisites

- Python 3.8.1 or higher
- [Poetry](https://python-poetry.org/docs/#installation)

### Installation

1. Navigate to the tests directory:
```bash
cd integrators-api-e2e-tests
```

2. Install Poetry if you haven't already:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. Install dependencies:
```bash
poetry install
```

### Running Tests

Make sure you're in the `integrators-api-e2e-tests` directory, then:

Run all tests with default output:
```bash
poetry run pytest
```

Run tests with detailed output (shows logs and print statements):
```bash
poetry run pytest -v
```

Run tests with maximum verbosity (shows extra test details):
```bash
poetry run pytest -vv
```

Show live logs during test execution:
```bash
poetry run pytest --log-cli-level=INFO
```

Show debug logs during test execution:
```bash
poetry run pytest --log-cli-level=DEBUG
```

Run tests with coverage:
```bash
poetry run pytest --cov=tests
```

### Development

Format code:
```bash
poetry run black .
```

Lint code:
```bash
poetry run flake8
```

## Contributing

1. Navigate to the project directory and create a virtual environment:
```bash
cd integrators-api-e2e-tests
poetry shell
```

2. Make your changes
3. Run tests
4. Submit a pull request

## Notes
- Never use sudo when activating a virtual environment
- Make sure you're in the correct directory when running commands
- If you get module not found errors, ensure you've installed the package in development mode (step 2)
- Use the -s flag with pytest to see print statements and logging output
- Use --log-cli-level=INFO to see detailed logging information



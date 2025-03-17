# Integrators API E2E Tests

This directory contains end-to-end tests for the Integrators API using Python.

## Setup

1. Create and activate a virtual environment (recommended):

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment (DO NOT use sudo)
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

2. Install the package in development mode:
```bash
# From the integrators-api-e2e-tests directory
pip install -e .
```

3. Install dependencies:
```bash
pip3 install -r requirements.txt
```

4. Run tests:
```bash
# Run all tests
pytest

# Run integration tests with verbose output
pytest -m integration -v

# Run tests with console output (shows print statements and logs)
pytest -v -s -m integration

# Run tests with console output and detailed logging
pytest -v -s -m integration --log-cli-level=INFO
```

5. Deactivate and clean up when done:
```bash
deactivate
rm -rf venv
```

## Notes
- Never use sudo when activating a virtual environment
- Make sure you're in the correct directory when running commands
- If you get module not found errors, ensure you've installed the package in development mode (step 2)
- Use the -s flag with pytest to see print statements and logging output
- Use --log-cli-level=INFO to see detailed logging information



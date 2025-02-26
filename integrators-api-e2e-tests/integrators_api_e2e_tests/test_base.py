import json
import pytest
import random
import string

class TestBase:
    # Base URL for the API endpoints (adjust if needed)
    BASE_URL = "https://integrators.dev.api.tabsplatform.com/v3"

    # Replace with your actual API key or token if authentication is required
    API_TOKEN = "test_tabs_sk_KTCeKkVVh80PB17EtSfhpY0pgZu7D7PsPmAC5kRfOCQSK84JMyJzXqqbhg0bdReP"

    @staticmethod
    def get_headers():
        """Return headers required for API requests"""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": TestBase.API_TOKEN
        }

    @staticmethod
    def validate_transaction_id(response):
        """Validate that the response contains a transaction ID header"""
        assert "X-Transaction-Id" in response.headers, "Response should contain X-Transaction-Id header"
        assert response.headers["X-Transaction-Id"], "Transaction ID should not be empty"

    @staticmethod
    def validate_paginated_response(response):
        """
        Validates the response JSON structure for expected keys and types.
        
        Expected structure:
        {
            "payload": {
                "data": [...],
                "currentPage": int,
                "limit": int,
                "totalItems": int
            },
            "success": bool,
            "message": str
        }
        """
        # If the response is a string, attempt to parse it
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON format: {e}")

        # Validate top-level keys
        for key in ["payload", "success", "message"]:
            if key not in response:
                pytest.fail(f"Missing top-level key: '{key}'")

        # Validate type for "message" and "success"
        if not isinstance(response["message"], str):
            pytest.fail("The 'message' key should be a string.")

        if not isinstance(response["success"], bool):
            pytest.fail("The 'success' key should be a boolean.")

        # Validate the payload structure
        payload = response["payload"]
        for key in ["data", "currentPage", "limit", "totalItems"]:
            if key not in payload:
                pytest.fail(f"Missing payload key: '{key}'")

        # Check types within payload
        if not isinstance(payload["data"], list):
            pytest.fail("The 'data' key in payload should be a list.")

        if not isinstance(payload["currentPage"], int):
            pytest.fail("The 'currentPage' key in payload should be an integer.")

        if not isinstance(payload["limit"], int):
            pytest.fail("The 'limit' key in payload should be an integer.")

        if not isinstance(payload["totalItems"], int):
            pytest.fail("The 'totalItems' key in payload should be an integer.")

        return True
    
    def generate_random_string(self, length=10):
        """Generate a random string of a given length"""
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for i in range(length))
        return random_string

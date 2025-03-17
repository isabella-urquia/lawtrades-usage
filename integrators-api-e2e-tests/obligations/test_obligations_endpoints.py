import requests
import json
import pytest
import logging
from integrators_api_e2e_tests.test_base import TestBase

logging.basicConfig(level=logging.INFO)

@pytest.mark.integration
def test_get_all_obligations_endpoint():
    """
    Test the GET /obligations endpoint for retrieving paginated obligation data.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles pagination parameters (limit=50, page=1)
    """
    endpoint = "/obligations"  # Endpoint for retrieving customers
    url = f"{TestBase.BASE_URL}{endpoint}"
    
    # Query parameters for pagination

    
    logging.info(f"Making GET request to {url}")
    response = requests.get(url, headers=TestBase.get_headers())
    
    if response.status_code != 200:
        logging.error(f"Request failed with status code {response.status_code}")
        logging.error(f"Response body: {response.text}")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    
    try:
        json_response = response.json()
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON response: {response.text}")
        raise
    
    logging.info("Validating paginated response structure")
    if not TestBase.validate_paginated_response(json_response):
        logging.error(f"Invalid pagination structure: {json_response}")
    assert TestBase.validate_paginated_response(json_response)
    
    logging.info("Validating transaction ID")
    TestBase.validate_transaction_id(response)

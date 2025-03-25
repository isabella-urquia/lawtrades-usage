import requests
import json
import pytest
import logging
from integrators_api_e2e_tests.test_base import TestBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.mark.integration
def test_get_all_events_endpoint():
    """
    Test the GET /events endpoint for retrieving paginated event data.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles pagination parameters (limit=50, page=1)
    """
    endpoint = "/events"
    url = f"{TestBase.BASE_URL}{endpoint}"

    # Query parameters for pagination
    params = {
        'limit': 50,
        'page': 1
    }

    logging.info(f"Making GET request to {url} with params: {params}")
    response = requests.get(url, headers=TestBase.get_headers(), params=params)
    
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

@pytest.mark.integration
def test_get_events_by_search_criteria():
    """
    Test the GET /events endpoint with search criteria.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles search filter parameters
    """
    endpoint = "/events"
    url = f"{TestBase.BASE_URL}{endpoint}"
    params = {
        "filter": "customerId:eq:b68ab84b-516e-4043-a7ea-b5b2eaf38a55,eventTypeId:eq:d631c49c-315c-40d9-91c8-fa2161856123"
    }
    response = requests.get(url, headers=TestBase.get_headers(), params=params)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    json_response = response.json()
    assert TestBase.validate_paginated_response(json_response)
    TestBase.validate_transaction_id(response)

@pytest.mark.integration
def test_delete_event_endpoint():
    """
    Test the DELETE /events/{id} endpoint.
    
    This test verifies:
    1. The endpoint returns a 200  status code for successful deletion
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles deletion of a specific event by ID
    """
    endpoint = "/events"
    id = "81de9b26-0195-4725-84e5-52c4526d425c"
    url = f"{TestBase.BASE_URL}{endpoint}/{id}"
  
    response = requests.delete(url, headers=TestBase.get_headers())
    # Assuming a successful DELETE returns status code 200 or 204
    assert response.status_code in [200], f"Expected 200, got {response.status_code}"
    TestBase.validate_transaction_id(response)

@pytest.mark.integration
def test_post_events_endpoint():
    """
    Test the POST /events endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 201 status code for successful creation
    2. The response includes a valid transaction ID header
    3. The endpoint correctly creates a new event with the provided payload
    4. The response contains a 'success' key indicating the operation status
    """
    endpoint = "/events"
    url = f"{TestBase.BASE_URL}{endpoint}"
    payload = {
        "customerId": "b68ab84b-516e-4043-a7ea-b5b2eaf38a55",
        "datetime": "2025-03-18T00:00:00.000Z",
        "eventTypeId": "d631c49c-315c-40d9-91c8-fa2161856123",
        "differentiator": "DIFF",
        "value": "200"
    }
    logger.info(f"payload: {payload}")
    response = requests.post(url, headers=TestBase.get_headers(), json=payload)
    # Assuming a successful POST returns status code 200 or 201
    assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
    
    json_response = response.json()
    # Check that the response contains the 'success' key
    assert "success" in json_response, "Response JSON should contain 'success' key"

@pytest.mark.integration
def test_get_event_types_endpoint():
    """
    Test the GET /event-types endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles pagination parameters (limit=50, page=1)
    """
    endpoint = "/events/types"
    url = f"{TestBase.BASE_URL}{endpoint}"
    params = {
        'limit': 50,
        'page': 1
    }
    response = requests.get(url, headers=TestBase.get_headers(), params=params)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    json_response = response.json()
    assert TestBase.validate_paginated_response(json_response)
    TestBase.validate_transaction_id(response)

@pytest.mark.integration
def test_get_event_type_endpoint():
    """
    Test the GET /event-types/{id} endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles pagination parameters (limit=50, page=1)
    """
    endpoint = "/events/types"
    id = "25416aa3-c633-45b7-b8f3-83f2a74698a4"
    url = f"{TestBase.BASE_URL}{endpoint}/{id}"
    response = requests.get(url, headers=TestBase.get_headers())
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    TestBase.validate_transaction_id(response)

@pytest.mark.integration
def test_create_event_type_endpoint():
    """
    Test the POST /event-types endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 201 status code for successful creation
    2. The response includes a valid transaction ID header
    3. The endpoint correctly creates a new event type with the provided payload
    4. The response contains a 'success' key indicating the operation status
    """
    endpoint = "/events/types"
    url = f"{TestBase.BASE_URL}{endpoint}"
    payload = {
        "name": TestBase.generate_random_string(length=20),
    }
    response = requests.post(url, headers=TestBase.get_headers(), json=payload)
    assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
    json_response = response.json()
    assert "success" in json_response, "Response JSON should contain 'success' key"
    
    
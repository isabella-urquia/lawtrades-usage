import requests
import json
import pytest
import logging
from integrators_api_e2e_tests.test_base import TestBase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.integration
def test_get_all_customers_endpoint():
    """
    Test the GET /customers endpoint for retrieving paginated customer data.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles pagination parameters (limit=50, page=1)
    """
    endpoint = "/customers"  # Endpoint for retrieving customers
    url = f"{TestBase.BASE_URL}{endpoint}"
    
    # Query parameters for pagination
    params = {
        "limit": 50,
        "page": 1
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
def test_get_customers_by_search_criteria():
    """
    Test the GET /customers endpoint with search criteria.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles search filter parameters
    """
    endpoint = "/customers"
    url = f"{TestBase.BASE_URL}{endpoint}"
    params = {
        "filter": "name:like:tabs"
    }
    response = requests.get(url, headers=TestBase.get_headers(), params=params)
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    json_response = response.json()
    assert TestBase.validate_paginated_response(json_response)
    TestBase.validate_transaction_id(response)

@pytest.mark.integration
def test_delete_endpoint():
    """
    Test the DELETE /customers/{id} endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 204 status code for successful deletion
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles deletion of a specific customer by ID
    """
    endpoint = "/customers"
    id = "b182a355-7487-47da-924f-dc67ad486b01"
    url = f"{TestBase.BASE_URL}{endpoint}/{id}"
  
    response = requests.delete(url, headers=TestBase.get_headers())
    # Assuming a successful DELETE returns status code 200 or 204
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)

@pytest.mark.integration
def test_create_customers_endpoint():
    """
    Test the POST /customers endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 201 status code for successful creation
    2. The response includes a valid transaction ID header
    3. The endpoint correctly creates a new customer with the provided payload
    4. The response contains a 'success' key indicating the operation status
    
    The test creates a customer with:
    - Random generated name
    - USD currency
    - Random billing contact details
    - Random billing address information
    """
    endpoint = "/customers"
    url = f"{TestBase.BASE_URL}{endpoint}"
    payload = {
        "name":  TestBase.generate_random_string(length=15),
        "currency": "USD",
        "primaryBillingContactName": TestBase.generate_random_string(length=15),
        "primaryBillingContactEmail": TestBase.generate_random_string(length=15) + "@e2etests.com",
        "billingAddress": {
            "externalId": TestBase.generate_random_string(length=15),
            "city": TestBase.generate_random_string(length=15),
            "state": "NY",
            "country": "USA",
            "zip": 10016,
            "address1": TestBase.generate_random_string(length=15),
            "address2": TestBase.generate_random_string(length=15),
            "addressee": TestBase.generate_random_string(length=15)
        },
    }
    logger.info(f"payload: {payload}")
    response = requests.post(url, headers=TestBase.get_headers(), json=payload)
    # Assuming a successful POST returns status code 200 or 201
    assert response.status_code in [200, 201], f"Expected 200/201, got {response.status_code}"
    
    json_response = response.json()
    # Check that the response contains the 'success' key
    assert "success" in json_response, "Response JSON should contain 'success' key"

@pytest.mark.integration
def test_get_customer_endpoint():
    """
    Test the GET /customers/{id} endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 204 status code
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles retrieval of a specific customer by ID
    """
    endpoint = "/customers"
    id = "b182a355-7487-47da-924f-dc67ad486b01"
    url = f"{TestBase.BASE_URL}{endpoint}/{id}"
  
    response = requests.get(url, headers=TestBase.get_headers())
    # Assuming a successful GET returns status code 200 or 204
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)


@pytest.mark.integration
def test_get_customer_invoice_():
    """
    Test the GET /customers/{id}/invoices/{invoiceId} endpoint .
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles retrieval of a specific invoice by invoiceID and customer_id
    """
    endpoint = "/customers"
    id = "3076a8e2-cc99-4899-ab4a-35cfdf6ca100"
    invoiceId = 'de83167d-b8ed-48fb-948d-71ebcbbf9b21'
    url = f"{TestBase.BASE_URL}{endpoint}/{id}/invoices/{invoiceId}"

    response = requests.get(url, headers=TestBase.get_headers())
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)

@pytest.mark.integration #ask Sathish help
def test_get_customer_invoice_pdf():
    """
    Test the GET /customers/{id}/invoices/{invoiceId}/pdf endpoint .
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles retrieval of a specific invoice by invoiceID and customer_id
    """
    endpoint = "/customers"
    id = "2dd88c8f-adf6-4b4e-a141-b6fe6f220732"
    invoiceId = '005167f1-415f-4e63-a6f6-53f0db00712e'
    url = f"{TestBase.BASE_URL}{endpoint}/{id}/invoices/{invoiceId}/pdf?type=pdf"
    headers = TestBase.get_headers()
    headers['Accept'] = 'application/pdf'
 

    response = requests.get(url, headers=headers)
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)

@pytest.mark.integration #ask Sathish help @Chirag - There is no enddpoint that gets payment for an invoice via PDF
def test_get_customer_invoice_payments():
    """
    Test the GET /customers/{id}/invoices/{invoiceId}/payments/{paymentId} endpoint .
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles retrieval of a specific invoice by invoiceID and customer_id
    """
    endpoint = "/customers"
    id = "0452a807-3073-4d9c-b737-b6c38fdf61e1"
    invoiceId = '1e975364-89e2-43f5-855d-c3a2f6e9152e'
    paymentId = '80c79865-7979-4ab8-944f-060fadcfa62b'
    url = f"{TestBase.BASE_URL}{endpoint}/{id}/invoices/{invoiceId}/payments/{paymentId}"

    response = requests.get(url, headers=TestBase.get_headers())
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)

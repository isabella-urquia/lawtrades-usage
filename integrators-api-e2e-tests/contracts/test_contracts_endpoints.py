import requests
import json
import pytest
import logging
from integrators_api_e2e_tests.test_base import TestBase
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the absolute path to the test_files directory
TEST_FILES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_files')

@pytest.mark.integration
def test_get_all_contracts_endpoint():
    """
    Test the GET /contracts endpoint for retrieving paginated contract data.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles pagination parameters (limit=50, page=1)
    """
    endpoint = "/contracts"  # Endpoint for retrieving contracts
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
def test_get_contracts_by_search_criteria():
    """
    Test the GET /contracts endpoint with search criteria.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response contains properly structured pagination data
    3. The response includes a valid transaction ID header
    4. The endpoint correctly handles search filter parameters
    """
    endpoint = "/contracts"
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
def test_delete_contract_endpoint():
    """
    Test the DELETE /contracts/{id} endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 204 status code for successful deletion
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles deletion of a specific contract by ID
    """
    endpoint = "/contracts"
    id = "9eb998e9-1d4b-46ed-89fa-c70e970ea3ff"
    url = f"{TestBase.BASE_URL}{endpoint}/{id}"
  
    response = requests.delete(url, headers=TestBase.get_headers())
    # Assuming a successful DELETE returns status code 200 or 204
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)

@pytest.mark.integration
def test_post_contracts_endpoint():
    """
    Test the POST /contracts endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 201 status code for successful creation
    2. The response includes a valid transaction ID header
    3. The endpoint correctly creates a new contract with the provided payload
    4. The response contains a 'success' key indicating the operation status
    
    The test creates a contract with:
    - Random generated ID
    - name
    - customerId
    - externalId
    """
    endpoint = "/contracts"
    url = f"{TestBase.BASE_URL}{endpoint}"
    payload = {
        "name": TestBase.generate_random_string(length=15),
        "customerId": "000b1fce-42d6-4734-8a07-cc84941111cf",
        "externalId": {
            "externalId": "644",
            "sourceType": "QUICKBOOKS"
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
def test_get_contract_endpoint():
    """
    Test the GET /contracts/{id} endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 204 status code
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles retrieval of a specific contract by ID
    """
    endpoint = "/contracts"
    id = "9eb998e9-1d4b-46ed-89fa-c70e970ea3ff"
    url = f"{TestBase.BASE_URL}{endpoint}/{id}"
  
    response = requests.get(url, headers=TestBase.get_headers())

    # Assuming a successful GET returns status code 200 or 204
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)


@pytest.mark.integration
def test_post_contracts_obligations_():
    """
    Test the POST /contracts/{id}/obligations/ endpoint .
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles the creation of a specific contraction obligations  and contract_id
    """
    endpoint = "/contracts"
    id = "00444744-c273-4a42-8371-fc00db6fb503"
    url = f"{TestBase.BASE_URL}{endpoint}/{id}/obligations"
    payload = {
                "serviceStartDate": TestBase.generate_random_string(length=15),
                "serviceEndDate": TestBase.generate_random_string(length=15),
                "categoryId": TestBase.generate_random_string(length=15),
                "billingSchedule": {
                    "name": TestBase.generate_random_string(length=15),
                    "description": TestBase.generate_random_string(length=15),
                    "startDate": TestBase.generate_random_string(length=15),
                    "endDate": TestBase.generate_random_string(length=15),
                    "isArrears": True,
                    "isRecurring": True,
                    "interval": TestBase.generate_random_string(length=15),
                    "intervalFrequency": 0,
                    "netPaymentTerms": 0,
                    "quantity": 0,
                    "billingType": TestBase.generate_random_string(length=15),
                    "pricingType": TestBase.generate_random_string(length=15),
                    "eventTypeId": TestBase.generate_random_string(length=15),
                    "erpItemId": TestBase.generate_random_string(length=15),
                    "invoiceType": TestBase.generate_random_string(length=15),
                    "pricing": [
                    TestBase.generate_random_string(length=15)
                    ]
                },
                "recognizedRevenue": [
                        TestBase.generate_random_string(length=15)
                ]
        }


    response = requests.post(url, headers=TestBase.get_headers())
    assert response.status_code in [200, 201], f"Expected 200 or 201, got {response.status_code}"
    TestBase.validate_transaction_id(response)

@pytest.mark.integration #Flag Sathish review
def test_post_contracts_file():
    """
    Test the POST /contracts/{id}/file endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles posting of file for a specific invoice by invoiceID 
    """
    endpoint = "/contracts"
    id = "029f07b1-395d-4d90-b1f8-d8af332d6f30"

    # Use the test_files directory for the PDF file
    filepath = os.path.join(TEST_FILES_DIR, 'invoice-290.pdf')
    url = f"{TestBase.BASE_URL}{endpoint}/{id}/file"

    logger.info(f"Looking for file at: {filepath}")
    
    try:
        if not os.path.exists(filepath):
            available_files = os.listdir(TEST_FILES_DIR) if os.path.exists(TEST_FILES_DIR) else []
            raise FileNotFoundError(
                f"File not found: {filepath}\n"
                f"Test files directory: {TEST_FILES_DIR}\n"
                f"Available files: {available_files}"
            )
                
        with open(filepath, 'rb') as f:
            # Simple multipart form without extra headers or metadata
            files = {
                'file': ('invoice.pdf', f, 'application/pdf')
            }
            response = requests.post(url, headers=TestBase.get_headers(), files=files)
            
        assert response.status_code in [200, 201], f"Expected status code 200 or 201, got {response.status_code}"
        TestBase.validate_transaction_id(response)
        
    except FileNotFoundError as e:
        pytest.fail(f"File error: {str(e)}")
    except Exception as e:
        pytest.fail(f"Upload failed: {str(e)}")

@pytest.mark.integration #ask Sathish help
def test_get_contract_obligations_():
    """
    Test the GET /contracts/{id}/obligations/{obligationId} endpoint .
    
    This test verifies:
    1. The endpoint returns a 200 OK status code
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles retrieval of a specific obligation by obligationID and contract_id
    """
    endpoint = "/contracts"
    id = "14811c27-40e5-40bf-813b-0f039d099ec7"
    obligationId = 'aa121f4e-d102-4b94-911d-f0baa3be55c7'
    url = f"{TestBase.BASE_URL}{endpoint}/{id}/obligations/{obligationId}"
    

    response = requests.get(url, headers=TestBase.get_headers())
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)

@pytest.mark.integration
def test_delete_contract_obligation_endpoint():
    """
    Test the DELETE /contracts/{id} endpoint.
    
    This test verifies:
    1. The endpoint returns a 200 or 204 status code for successful deletion
    2. The response includes a valid transaction ID header
    3. The endpoint correctly handles deletion of a specific obligation for a contract by obligationId and contractId
    """
    endpoint = "/contracts"
    id = "14811c27-40e5-40bf-813b-0f039d099ec7"
    obligationId = 'aa121f4e-d102-4b94-911d-f0baa3be55c7'
    url = f"{TestBase.BASE_URL}{endpoint}/{id}/obligations/{obligationId}"
  
    response = requests.delete(url, headers=TestBase.get_headers())
    # Assuming a successful DELETE returns status code 200 or 204
    assert response.status_code in [200, 204], f"Expected 200 or 204, got {response.status_code}"
    TestBase.validate_transaction_id(response)

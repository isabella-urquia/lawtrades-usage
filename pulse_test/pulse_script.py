import requests
import os
import json
import time

def convert_pdf(pdf_path,api_key):
    """
    Convert PDF using the backend API (no error handling, no API key)
    """
    start_time = time.time()
    
    url = "https://api.runpulse.com/convert"
    headers = {
        'Content-Type': 'application/pdf',
        'x-api-key': api_key
    }
    
    with open(pdf_path, 'rb') as pdf_file:
        response = requests.post(url, headers=headers, data=pdf_file)

    conversion_time = time.time() - start_time
    print(f"PDF conversion took {conversion_time:.2f} seconds")
    
    # Return whatever key you expect (here 's3_object_url', if available)
    response_data = response.json()
    return response_data.get('s3_object_url')

def upload_file(file_url, api_key, schema=None, return_table=False, chunking=None):
    """
    Upload file to backend API with chunking and schema (no error handling, no API key)
    """
    start_time = time.time()
    
    url = "https://api.runpulse.com/extract"
    data = {
        'file-url': file_url,
        'schema': schema,
        'chunking': chunking,
        'return_table': return_table
    }
    
    response = requests.post(
        url,
        headers={'x-api-key': api_key, 'Content-Type': 'application/json'},
        json=data,
    )
    
    upload_time = time.time() - start_time
    print(f"File upload and extraction took {upload_time:.2f} seconds")
    return response.json()

API_KEY = 'dePJWAyd85aSkfplIyMxt624zfofZkfK9hLRgDU7'

extraction_schema = {
  "customer_info": {
    "name": "string",
    "address": "string",
    "contact_person": "string",
    "contact_email": "string"
  },
  "payment_terms": {
    "start_date": "date",
    "billing_frequency": "string",
    "net_terms": "string",
    "contract_duration": "string"
  },
  "purchase_order": [
    {
      "description": "string",
      "quantity": "integer",
      "rate": "float",
      "amount": "string"
    }
  ],
  "billing_terms": {
    "name": "string",
    "implementation_fees": "string",
    "billing_email": "string",
    "discount": "string"
  }
}

file = "tabs-fde/pulse_test/Hardware_Software  (1) (1) (3).pdf"
converted_file_url = convert_pdf(file, API_KEY)
print("Converted file URL:", converted_file_url)

final_extraction = upload_file(converted_file_url, API_KEY, schema=extraction_schema)

# Write outputs to files (still included for demonstration)
with open('final_extraction.json', 'w') as f:
    json.dump(final_extraction, f)

with open('markdown_extraction.md', 'w') as f:
    f.write(final_extraction.get('markdown', ''))

with open('schema.json', 'w') as f:
    json.dump(final_extraction.get('schema-json', {}), f)


    
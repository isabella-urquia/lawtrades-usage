import requests
import csv
import os

# Define the API headers
headers = {
    "Authorization": "tabs_sk_V3Ko5AOG095jJsZHuDaYRitgBw6xVT2WvPTH9qUnYeoWEYkFnbNuOwBkpzgnvBvO"
}

# API Endpoint Template
API_URL_TEMPLATE = "https://integrators.prod.api.tabsplatform.com/v3/customers/{id}/invoices/{invoiceId}/attachments"

# Function to send file to API
def send_request(manufacturer_id, invoice_id, filepath, talent_name=None):
    if not os.path.exists(filepath):
        print(f"Error: File not found → {filepath}")
        return

    url = API_URL_TEMPLATE.format(id=manufacturer_id, invoiceId=invoice_id)  # Format URL with dynamic values
    
    # Create filename with talent name if provided
    filename = os.path.basename(filepath)
    if talent_name:
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{talent_name}{ext}"
        print(f"📋 Uploading split invoice: {filename}")
    
    with open(filepath, 'rb') as file:
        files = {'file': (filename, file, 'application/pdf')}  # Attach file
    
        try:
            response = requests.post(url, headers=headers, files=files, timeout=20)
            response.raise_for_status()  # Raise an error for bad responses (4xx, 5xx)
            print(f"✅ Success: {filename} → Response: {response.json()}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error processing {filename}: {e}")

# Function to process CSV file
def process_csv(file_path):
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)  # Read CSV as dictionary
        for row in reader:
            manufacturer_id = row["Manufacturer_id"]
            invoice_id = row["Invoice_id"]
            filepath = row["Filepath"]
            talent_name = row.get("Talent_name", "")  # Get talent name if it exists
            
            # Send file to API with talent name if available
            send_request(manufacturer_id, invoice_id, filepath, talent_name if talent_name else None)

# Specify CSV file location
csv_file = "/Users/isabellaurquia/Downloads/Lawtrades_invoices_7.csv"  # Update with actual file path
process_csv(csv_file)

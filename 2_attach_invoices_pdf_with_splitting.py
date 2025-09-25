import requests
import csv
import os
from PyPDF2 import PdfReader, PdfWriter
import tempfile

# Define the API headers
headers = {
    "Authorization": "tabs_sk_V3Ko5AOG095jJsZHuDaYRitgBw6xVT2WvPTH9qUnYeoWEYkFnbNuOwBkpzgnvBvO"
}

# API Endpoint Template
API_URL_TEMPLATE = "https://integrators.prod.api.tabsplatform.com/v3/customers/{id}/invoices/{invoiceId}/attachments"

# List of companies that need PDF splitting by talent
SPLIT_PDF_COMPANIES = [
    "CompanyA",  # Add your specific company names here
    "CompanyB",  # that need PDF splitting
    # Add more as needed
]

def split_pdf_by_talent(pdf_path, talent_sections):
    """
    Split a PDF into separate files based on talent sections.
    talent_sections should be a list of tuples: [(talent_name, start_page, end_page), ...]
    """
    reader = PdfReader(pdf_path)
    split_files = []
    
    for talent_name, start_page, end_page in talent_sections:
        writer = PdfWriter()
        
        # Add pages for this talent (convert to 0-based indexing)
        for page_num in range(start_page - 1, min(end_page, len(reader.pages))):
            writer.add_page(reader.pages[page_num])
        
        # Create temporary file for this talent's PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{talent_name}.pdf")
        writer.write(temp_file)
        temp_file.close()
        
        split_files.append((talent_name, temp_file.name))
    
    return split_files

def send_request(manufacturer_id, invoice_id, filepath, talent_name=None):
    if not os.path.exists(filepath):
        print(f"Error: File not found → {filepath}")
        return False

    url = API_URL_TEMPLATE.format(id=manufacturer_id, invoiceId=invoice_id)
    
    # Create filename with talent name if provided
    filename = os.path.basename(filepath)
    if talent_name:
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{talent_name}{ext}"
        print(f"📋 Uploading split invoice: {filename}")
    
    with open(filepath, 'rb') as file:
        files = {'file': (filename, file, 'application/pdf')}
    
        try:
            response = requests.post(url, headers=headers, files=files, timeout=20)
            response.raise_for_status()
            print(f"✅ Success: {filename} → Response: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Error processing {filename}: {e}")
            return False

def process_csv_with_splitting(file_path):
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            manufacturer_id = row["Manufacturer_id"]
            invoice_id = row["Invoice_id"]
            filepath = row["Filepath"]
            company_name = row["Company_name"]
            
            # Check if this company needs PDF splitting
            if company_name in SPLIT_PDF_COMPANIES:
                print(f"🔄 Splitting PDF for {company_name}...")
                
                # Define talent sections for this company
                # You'll need to customize this based on your PDF structure
                talent_sections = get_talent_sections_for_company(company_name)
                
                if talent_sections:
                    # Split the PDF
                    split_files = split_pdf_by_talent(filepath, talent_sections)
                    
                    # Upload each split file
                    for talent_name, split_file_path in split_files:
                        success = send_request(manufacturer_id, invoice_id, split_file_path, talent_name)
                        # Clean up temporary file
                        os.unlink(split_file_path)
                else:
                    print(f"⚠️ No talent sections defined for {company_name}, uploading as-is")
                    send_request(manufacturer_id, invoice_id, filepath)
            else:
                # Regular upload for non-split companies
                send_request(manufacturer_id, invoice_id, filepath)

def get_talent_sections_for_company(company_name):
    """
    Define talent sections for each company that needs PDF splitting.
    Return list of (talent_name, start_page, end_page) tuples.
    """
    # Customize this based on your specific PDFs
    talent_sections_map = {
        "CompanyA": [
            ("JohnDoe", 1, 3),      # Pages 1-3 for John Doe
            ("JaneSmith", 4, 6),    # Pages 4-6 for Jane Smith
        ],
        "CompanyB": [
            ("MikeJohnson", 1, 2),  # Pages 1-2 for Mike Johnson
            ("SarahWilson", 3, 5),  # Pages 3-5 for Sarah Wilson
        ],
        # Add more companies as needed
    }
    
    return talent_sections_map.get(company_name, [])

# Specify CSV file location
csv_file = "/Users/isabellaurquia/Downloads/Lawtrades_invoices_7.csv"
process_csv_with_splitting(csv_file)


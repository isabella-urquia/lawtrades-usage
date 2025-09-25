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

def process_csv_with_splitting(file_path, split_pdfs=False):
    """
    Process CSV file with optional PDF splitting by talent.
    
    CSV format options:
    1. Basic: Manufacturer_id, Invoice_id, Filepath
    2. With talent: Manufacturer_id, Invoice_id, Filepath, Talent_Name
    3. With splitting: Manufacturer_id, Invoice_id, Filepath, Talent_Sections
       where Talent_Sections is a JSON string like: [{"talent": "John Doe", "start": 1, "end": 3}, ...]
    """
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            manufacturer_id = row["Manufacturer_id"]
            invoice_id = row["Invoice_id"]
            filepath = row["Filepath"]
            
            # Check if we have talent information
            if "Talent_Name" in row and row["Talent_Name"]:
                # Single talent per row
                talent_name = row["Talent_Name"]
                success = send_request(manufacturer_id, invoice_id, filepath, talent_name)
                
            elif "Talent_Sections" in row and row["Talent_Sections"] and split_pdfs:
                # Split PDF by talent sections
                import json
                try:
                    talent_sections = json.loads(row["Talent_Sections"])
                    split_files = split_pdf_by_talent(filepath, 
                        [(section["talent"], section["start"], section["end"]) for section in talent_sections])
                    
                    for talent_name, split_file_path in split_files:
                        success = send_request(manufacturer_id, invoice_id, split_file_path, talent_name)
                        # Clean up temporary file
                        os.unlink(split_file_path)
                        
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"❌ Error parsing talent sections for {filepath}: {e}")
                    # Fallback to uploading original file
                    send_request(manufacturer_id, invoice_id, filepath)
                    
            else:
                # No talent information, upload as-is
                send_request(manufacturer_id, invoice_id, filepath)

def process_csv_simple(file_path):
    """Process CSV file without splitting (original functionality)"""
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            manufacturer_id = row["Manufacturer_id"]
            invoice_id = row["Invoice_id"]
            filepath = row["Filepath"]
            send_request(manufacturer_id, invoice_id, filepath)

# Example usage:
if __name__ == "__main__":
    # Choose your CSV file
    csv_file = "/Users/isabellaurquia/Downloads/Lawtrades_invoices_7.csv"
    
    # Option 1: Simple upload (original functionality)
    print("Processing CSV with simple upload...")
    process_csv_simple(csv_file)
    
    # Option 2: Upload with talent names (if CSV has Talent_Name column)
    # process_csv_with_splitting(csv_file, split_pdfs=False)
    
    # Option 3: Split PDFs by talent sections (if CSV has Talent_Sections column)
    # process_csv_with_splitting(csv_file, split_pdfs=True)


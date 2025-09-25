import os
import csv
import psycopg2
from datetime import datetime
from dateutil.parser import parse

# Database connection
conn = psycopg2.connect(
    dbname="core",
    user="read",
    password=os.getenv('SCRIPT_DB_PASSWORD'),
    port=5432,
    host="core-1.c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
    sslmode='require'
)
cursor = conn.cursor()

# Folder containing PDF files
PDF_FOLDER = r"/Users/isabellaurquia/Downloads/August_Lawtrades_Invoicing_Upfront"

# Output CSV file
CSV_FILE = "Lawtrades_invoices_7.csv"

# Fixed Merchant ID
Manufacturer_id = "7af68809-96ba-4de9-a1a0-4be7b103a491"

# Start date for invoice filtering (convert to datetime)

## Issue Date
start_date = datetime(2025, 8, 31)

# Function to extract company name from filename
def extract_company_name(filename):
    return filename.split("_")[0]  # Extract company name before " _ "

# Function to check if invoice exists in DB
def existsInvoice(company_name):
    query = """
        SELECT invoices.id
        FROM invoices
        JOIN customers ON invoices.customer_id = customers.id
        WHERE customers.name like %s
        AND invoices.issue_date = %s
        AND customers.manufacturer_id = '7af68809-96ba-4de9-a1a0-4be7b103a491'
    """
    
    cursor.execute(query, (company_name + "%", start_date))  # Correct tuple usage
    row = cursor.fetchone()  # Fetch one row

    return row[0] if row else None  # Return invoice ID if found, otherwise None

def existsCustomer(company_name):
    query = """
        SELECT invoices.id
        FROM invoices
        JOIN customers ON invoices.customer_id = customers.id
        WHERE customers.name LIKE CONCAT(%s, '%')
        AND invoices.issue_date > %s
        AND customers.manufacturer_id = '7af68809-96ba-4de9-a1a0-4be7b103a491'
    """
    
    cursor.execute(query, (company_name, start_date))  # Correct tuple usage
    row = cursor.fetchone()  # Fetch one row

    return row[0] if row else None  # Return invoice ID if found, otherwise None

# List of companies that need split invoices by talent
SPLIT_INVOICE_COMPANIES = [
    "CompanyA",  # Add your specific company names here
    "CompanyB",  # that need talent splitting
    # Add more as needed
]

# Function to extract talent name from filename (for split invoices)
def extract_talent_name(filename):
    """Extract talent name from filename like 'CompanyA_JohnDoe_Report.pdf'"""
    parts = filename.split("_")
    if len(parts) >= 3:  # Company_Talent_Report.pdf
        return parts[1]  # Return talent name
    return None

# Function to scan folder and generate CSV
def generate_csv(folder_path, output_csv):
    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]  # List all PDFs
    
    with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Manufacturer_id", "Invoice_id", "Company_name", "Filename", "Filepath", "Talent_name"])  # CSV header

        for pdf in pdf_files:
            company_name = extract_company_name(pdf)  # Extract company name
            invoice_id = existsInvoice(company_name)  # Check if invoice exists
            file_path = os.path.join(folder_path, pdf)  # Full file path
            
            # Check if this company needs talent splitting
            talent_name = None
            if company_name in SPLIT_INVOICE_COMPANIES:
                talent_name = extract_talent_name(pdf)
                if talent_name:
                    print(f"📋 Split invoice detected: {company_name} - {talent_name}")
            
            writer.writerow([Manufacturer_id, invoice_id, company_name, pdf, file_path, talent_name])

    print(f"CSV generated: {output_csv}")

# Run the function
generate_csv(PDF_FOLDER, CSV_FILE)

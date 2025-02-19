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
PDF_FOLDER = r"/Users/chiragdas/Downloads/Lawtrades_pdf_attachments_test2_feb18"

# Output CSV file
CSV_FILE = "Lawtrades_invoices_4.csv"

# Fixed Merchant ID
Manufacturer_id = "7af68809-96ba-4de9-a1a0-4be7b103a491"

# Start date for invoice filtering (convert to datetime)

## Issue Date
start_date = datetime(2025, 2, 15)

# Function to extract company name from filename
def extract_company_name(filename):
    return filename.split("_")[0]  # Extract company name before " _ "

# Function to check if invoice exists in DB
def existsInvoice(company_name):
    query = """
        SELECT invoices.id
        FROM invoices
        JOIN customers ON invoices.customer_id = customers.id
        WHERE customers.name = %s
        AND invoices.issue_date = %s
        AND customers.manufacturer_id = '7af68809-96ba-4de9-a1a0-4be7b103a491'
    """
    
    cursor.execute(query, (company_name, start_date))  # Correct tuple usage
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

# Function to scan folder and generate CSV
def generate_csv(folder_path, output_csv):
    pdf_files = [f for f in os.listdir(folder_path) if f.endswith(".pdf")]  # List all PDFs
    
    with open(output_csv, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Manufacturer_id", "Invoice_id", "Company_name", "Filename", "Filepath"])  # CSV header

        for pdf in pdf_files:
            company_name = extract_company_name(pdf)  # Extract company name
            invoice_id = existsInvoice(company_name)  # Check if invoice exists
            file_path = os.path.join(folder_path, pdf)  # Full file path
            
            writer.writerow([Manufacturer_id, invoice_id, company_name, pdf, file_path])

    print(f"CSV generated: {output_csv}")

# Run the function
generate_csv(PDF_FOLDER, CSV_FILE)

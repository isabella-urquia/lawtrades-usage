import pandas as pd
from fpdf import FPDF
import os, textwrap, zipfile
from pathlib import Path  # ✅ Added for dynamic report type parsing

def remove_non_latin1(text):
    return ''.join(c for c in text if ord(c) < 256)

# === CONFIGURATION ===
# make sure to put monthly, semimonthly, upfront.csv
csv_path = "/Users/isabellaurquia/Downloads/cision1_monthly.csv"
output_dir = "/Users/isabellaurquia/Desktop/pdf_output"

# === HELPERS ===
def normalize_text(text):
    cleaned = str(text).replace("“", '"').replace("”", '"')\
                       .replace("’", "'").replace("–", "-")\
                       .replace("—", "-").strip()
    return remove_non_latin1(cleaned)

def clean_description(desc):
    return "\n".join(line.strip() for line in str(desc).splitlines() if line.strip())

def format_date(date):
    return pd.to_datetime(date).strftime("%Y-%m-%d")

# === LOAD CSV AND CLEAN ===
df = pd.read_csv(csv_path)

# ✅ Dynamically set month and report type from filename
month_str = pd.to_datetime(df["date"]).min().strftime("%B")
report_file = Path(csv_path).stem.lower()
if "semimonth" in report_file:
    report_type = "SemiMonthly"
elif "upfront" in report_file:
    report_type = "Upfront"
elif "monthly" in report_file:
    report_type = "Monthly"
else:
    report_type = "Reports"  # fallback/default

zip_path = f"/Users/isabellaurquia/Desktop/{month_str}_Lawtrades_Invoicing_{report_type}.zip"

# ✅ Clean the currency column
df["Company_Total_No_Currency ($)"] = (
    df["Company_Total_No_Currency ($)"]
    .astype(str)
    .str.replace("$", "", regex=False)
    .str.replace(",", "", regex=False)
    .astype(float)
)

expanded_rows = []

for _, row in df.iterrows():
    base_date = format_date(row["date"])
    staffer = row["Staffer_Name"]
    company = row["Company_Name"]
    customer_id = row["tabs_customer_id"]
    base_hours = row["Hours"]
    base_amount = float(row["Company_Total_No_Currency ($)"])

    lines = clean_description(row["description"]).split("\n")
    valid_lines = [line.strip() for line in lines if line.strip()]
    per_entry_hours = base_hours / len(valid_lines)
    per_entry_amount = base_amount / len(valid_lines)

    for line in valid_lines:
        expanded_rows.append({
            "date": base_date,
            "description": normalize_text(line),
            "Hours": round(per_entry_hours, 2),
            "Company_Total_No_Currency ($)": round(per_entry_amount, 2),
            "Staffer_Name": staffer,
            "Company_Name": company,
            "tabs_customer_id": customer_id
        })

df_expanded = pd.DataFrame(expanded_rows)

# === PDF CLASS ===
class LawtradesPDF(FPDF):
    def __init__(self, company):
        super().__init__()
        self.company = company
        self.set_auto_page_break(auto=False)
        self.set_margins(15, 15, 15)
        self.headers = ["Date", "Description", "Hours", "Total ($)"]
        self.col_widths = [30, 100, 25, 30]
        self.line_height = 5 * 1.55
        self.talent_counter = 0

    def add_talent_section(self, talent):
        self.add_page()
        if self.talent_counter == 0:
            self.set_font("Arial", "B", 14)
            self.cell(0, 10, f"{self.company} - Hours Report", ln=True)
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, f"Talent: {talent}", ln=True)
        self.ln(2)
        self.print_table_header()
        self.talent_counter += 1

    def print_table_header(self):
        self.set_font("Arial", "B", 10)
        for i, h in enumerate(self.headers):
            self.cell(self.col_widths[i], 8, h, border="T")
        self.ln()

    def add_row(self, row):
        self.set_font("Arial", "", 9)
        description = clean_description(row["description"])
        desc_lines = textwrap.wrap(description, width=60)
        num_lines = max(1, len(desc_lines))
        row_height = self.line_height * num_lines

        # ✅ Page break check
        if self.get_y() + row_height > self.h - 15:
            self.add_page()
            self.print_table_header()

        x = self.get_x()
        y = self.get_y()

        # Date
        self.set_xy(x, y)
        self.set_font("Arial", "", 9)
        self.cell(self.col_widths[0], row_height, format_date(row["date"]), border="T")

        # Description
        self.set_xy(x + self.col_widths[0], y)
        self.rect(x + self.col_widths[0], y, self.col_widths[1], row_height)
        for i, line in enumerate(desc_lines):
            self.set_xy(x + self.col_widths[0], y + i * self.line_height)
            self.set_font("Arial", "", 9)
            self.cell(self.col_widths[1], self.line_height, line)

        # Hours
        self.set_xy(x + sum(self.col_widths[:2]), y)
        self.cell(self.col_widths[2], row_height, f"{row['Hours']:.2f}", border="T")

        # Total
        self.set_xy(x + sum(self.col_widths[:3]), y)
        self.cell(self.col_widths[3], row_height, f"${row['Company_Total_No_Currency ($)']:.2f}", border="T")

        self.set_y(y + row_height + 1)

    def add_totals(self, total_hours, total_amount):
        self.ln(3)
        self.set_font("Arial", "B", 10)
        self.cell(sum(self.col_widths[:2]), 8, "Total", border="T")
        self.cell(self.col_widths[2], 8, f"{total_hours:.2f}", border="T")
        self.cell(self.col_widths[3], 8, f"${total_amount:.2f}", border="T")
        self.ln()

# === GENERATE PDFs ===
os.makedirs(output_dir, exist_ok=True)
pdf_paths = []

for company, group_df in df_expanded.groupby("Company_Name"):
    customer_id = group_df["tabs_customer_id"].iloc[0]
    filename = f"{company.replace(' ', '')}_hoursReport_{month_str}_{customer_id}.pdf"
    path = os.path.join(output_dir, filename)

    pdf = LawtradesPDF(company)
    for talent, rows in group_df.groupby("Staffer_Name"):
        pdf.add_talent_section(talent)
        total_hours = rows["Hours"].sum()
        total_amount = rows["Company_Total_No_Currency ($)"].sum()
        for _, row in rows.iterrows():
            pdf.add_row(row)
        pdf.add_totals(total_hours, total_amount)

    pdf.output(path)
    pdf_paths.append(path)

# === ZIP PDFs ===
with zipfile.ZipFile(zip_path, "w") as zipf:
    for path in pdf_paths:
        zipf.write(path, os.path.basename(path))

print(f"✅ FINAL FIXED: All PDFs generated and zipped to Desktop as:\n{zip_path}")
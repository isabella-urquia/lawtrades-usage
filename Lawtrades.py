"""
Lawtrades Invoicing Pipeline - Streamlit App
===========================================
Two workflows:
1) Usage CSV Transformation (incl. dynamic step-up suffixing)
2) PDF Generation + Bulk Attach to Invoices
"""

import os
import tempfile
import textwrap
import uuid
import warnings
from pathlib import Path
from typing import List, Optional, Dict

import pandas as pd
import streamlit as st
import requests
import json
import psycopg2
from fpdf import FPDF
from datetime import datetime

# --- Global setup ---
st.set_page_config(page_title="Lawtrades Internal Tool", page_icon="📄", layout="wide")

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

API_BASE_URL = "https://integrators.prod.api.tabsplatform.com/v3"
PROD_MANUFACTURER_ID = "7af68809-96ba-4de9-a1a0-4be7b103a491"
SANDBOX_MANUFACTURER_ID = "d90b1777-0ca5-45ca-99ee-70cf51eb314a"

# --- Small helpers ---
def remove_non_latin1(text: str) -> str:
    return ''.join(c for c in str(text) if ord(c) < 256)

def normalize_text(text: str) -> str:
    if text is None:
        return ""
    s = str(text)
    # normalize smart quotes / dashes
    trans = {
        "“": '"', "”": '"', "‘": "'", "’": "'",
        "–": "-", "—": "-",
    }
    for k, v in trans.items():
        s = s.replace(k, v)
    return remove_non_latin1(s.strip())

def clean_description(desc: str) -> str:
    return "\n".join(line.strip() for line in str(desc).splitlines() if line.strip())

def format_date(date) -> str:
    return pd.to_datetime(date, errors="coerce").strftime("%Y-%m-%d")

def is_valid_uuid(val) -> bool:
    try:
        uuid.UUID(str(val))
        return True
    except Exception:
        return False

# --- DB connection ---
def get_db_connection():
    """Get read-only connection to core DB."""
    try:
        db_password = os.getenv('SCRIPT_DB_PASSWORD')
        if not db_password:
            st.error("Database password required. Set SCRIPT_DB_PASSWORD env var.")
            return None
        return psycopg2.connect(
            dbname="core",
            user="read",
            password=db_password,
            port=5432,
            host="core-1.c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
            sslmode='require'
        )
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# --- Invoice helpers ---
def extract_serial_code(filename: str) -> Optional[str]:
    """Extract UUID (customer_id) from the filename (last part before .pdf), or anywhere in the name."""
    try:
        base = os.path.splitext(filename)[0]
        parts = base.split("_")
        candidate = parts[-1] if parts else None
        if candidate and is_valid_uuid(candidate):
            return candidate
        for p in parts:
            if is_valid_uuid(p):
                return p
        return None
    except Exception:
        return None

def exists_invoice(company_id: str, fallback_invoice_id: Optional[str], issue_date=None) -> Optional[str]:
    """Check if invoice exists in DB for a company + issue_date/month; return invoice_id if found."""
    if not company_id or not is_valid_uuid(company_id):
        return fallback_invoice_id
    try:
        conn = get_db_connection()
        if not conn:
            return fallback_invoice_id
        cursor = conn.cursor()

        if issue_date is None:
            # current month (inclusive), next month (exclusive)
            current_month = datetime.now().replace(day=1)
            next_month = (pd.Timestamp(current_month) + pd.DateOffset(months=1)).to_pydatetime()
            cursor.execute(
                """
                SELECT invoices.id, invoices.issue_date
                FROM invoices
                JOIN customers ON invoices.customer_id = customers.id
                WHERE customers.id = %s
                  AND invoices.issue_date >= %s
                  AND invoices.issue_date < %s
                  AND invoices.status != 'DELETED'
                  AND customers.manufacturer_id = %s
                  AND invoices.invoice_type = 'INVOICE'
                ORDER BY invoices.issue_date DESC
                LIMIT 1
                """,
                (company_id, current_month, next_month, PROD_MANUFACTURER_ID)
            )
        else:
            cursor.execute(
                """
                SELECT invoices.id, invoices.issue_date
                FROM invoices
                JOIN customers ON invoices.customer_id = customers.id
                WHERE customers.id = %s
                  AND invoices.issue_date = %s
                  AND invoices.status != 'DELETED'
                  AND customers.manufacturer_id = %s
                  AND invoices.invoice_type = 'INVOICE'
                ORDER BY invoices.issue_date DESC
                LIMIT 1
                """,
                (company_id, issue_date, PROD_MANUFACTURER_ID)
            )
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row[0] if row else fallback_invoice_id
    except Exception:
        return fallback_invoice_id

# --- API helpers ---
def get_headers():
    api_key = st.session_state.get("api_key", "") or st.session_state.get("api_token", "")
    if not api_key:
        return None
    return {
        "Authorization": api_key,  # direct key (not Bearer)
        "Accept": "application/json"
    }

def fetch_dynamic_stepup_pricing():
    """Fetch obligations (billingSchedule) and flatten first pricing tier. Returns filtered DataFrame or None."""
    headers = get_headers()
    if not headers:
        st.error("🔑 API key required to fetch step-up pricing.")
        return None
    try:
        with st.spinner("Fetching latest step-up pricing..."):
            r = requests.get(f"{API_BASE_URL}/obligations?limit=1000", headers=headers, timeout=30)
            if r.status_code != 200:
                st.error(f"API Error {r.status_code}: {r.text[:200]}")
                return None
            data = r.json()
            payload = data.get("payload", {})
            rows = payload.get("data", [])
            if not isinstance(rows, list) or not rows:
                st.warning("No obligations returned.")
                return None

            df = pd.DataFrame(rows)

            # Flatten billingSchedule
            if "billingSchedule" in df.columns:
                bs = pd.json_normalize(df["billingSchedule"])
                bs.columns = [f"billingSchedule_{c}" for c in bs.columns]
                df = pd.concat([df.drop(columns=["billingSchedule"]), bs], axis=1)

                # pricing[0] extraction (amount, tier, amountType, tierMinimum)
                if "billingSchedule_pricing" in df.columns:
                    def first_or_none(lst, key):
                        if isinstance(lst, list) and lst:
                            return lst[0].get(key)
                        return None
                    df["pricing_amount"] = df["billingSchedule_pricing"].apply(lambda v: first_or_none(v, "amount"))
                    df["pricing_tier"] = df["billingSchedule_pricing"].apply(lambda v: first_or_none(v, "tier"))
                    df["pricing_amountType"] = df["billingSchedule_pricing"].apply(lambda v: first_or_none(v, "amountType"))
                    df["pricing_tierMinimum"] = df["billingSchedule_pricing"].apply(lambda v: first_or_none(v, "tierMinimum"))
                    df = df.drop(columns=["billingSchedule_pricing"])

            # Filter: only names with "- 1" or "- 2", non-FLAT, not expired
            if "billingSchedule_name" not in df.columns:
                st.warning("billingSchedule_name not present.")
                return None
            filtered = df[df["billingSchedule_name"].str.contains(r"-\s*[12]", na=False, regex=True)].copy()
            if "billingSchedule_billingType" in filtered.columns:
                filtered = filtered[filtered["billingSchedule_billingType"].ne("FLAT")]
            if "billingSchedule_endDate" in filtered.columns:
                filtered["_end"] = pd.to_datetime(filtered["billingSchedule_endDate"], errors="coerce", utc=True)
                now_utc = pd.Timestamp.utcnow()
                filtered = filtered[filtered["_end"].gt(now_utc)].drop(columns=["_end"], errors="ignore")

            # Keep only a few useful cols
            keep = [c for c in ["billingSchedule_name", "pricing_amount", "contractId"] if c in filtered.columns]
            return filtered[keep].reset_index(drop=True) if keep else filtered.reset_index(drop=True)
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {e}")
        return None

def map_contracts_to_customers(contract_ids):
    """Return dict {contract_id: customer_id} via contracts API. Requires API key."""
    headers = get_headers()
    mapping = {}
    if not headers:
        return mapping
    for i, cid in enumerate(set([c for c in contract_ids if isinstance(c, str) and c])):
        try:
            if i:
                import time; time.sleep(0.1)
            r = requests.get(f"{API_BASE_URL}/contracts/{cid}", headers=headers, timeout=30)
            if r.status_code == 200:
                j = r.json()
                cust = j.get("payload", {}).get("customerId")
                if cust:
                    mapping[cid] = cust
        except requests.exceptions.RequestException:
            continue
    return mapping

def upload_attachment(customer_id, invoice_id, filepath, talent_name=None) -> bool:
    """Upload PDF to invoice attachments."""
    headers = get_headers()
    if not headers:
        st.error("API key not configured.")
        return False
    url = f"{API_BASE_URL}/customers/{customer_id}/invoices/{invoice_id}/attachments"
    filename = os.path.basename(filepath)
    if talent_name:
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{talent_name}{ext}"
    try:
        with open(filepath, "rb") as f:
            files = {"file": (filename, f, "application/pdf")}
            resp = requests.post(url, headers=headers, files=files, timeout=30)
        return resp.status_code in (200, 201)
    except Exception:
        return False

# --- PDF rendering ---
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
            self.set_font("helvetica", "B", 14)
            self.cell(0, 10, f"{self.company} - Hours Report", new_x="LMARGIN", new_y="NEXT")
        self.set_font("helvetica", "B", 12)
        self.cell(0, 10, f"Talent: {talent}", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.print_table_header()
        self.talent_counter += 1

    def print_table_header(self):
        self.set_font("helvetica", "B", 10)
        for i, h in enumerate(self.headers):
            self.cell(self.col_widths[i], 8, h, border="T")
        self.ln()

    def add_row(self, row):
        self.set_font("helvetica", "", 9)
        description = clean_description(row["description"])
        desc_lines = textwrap.wrap(description, width=60)
        num_lines = max(1, len(desc_lines))
        row_height = self.line_height * num_lines

        if self.get_y() + row_height > self.h - 15:
            self.add_page()
            self.print_table_header()

        x = self.get_x()
        y = self.get_y()

        # Date
        self.set_xy(x, y)
        self.cell(self.col_widths[0], row_height, format_date(row["date"]), border="T")

        # Description
        self.set_xy(x + self.col_widths[0], y)
        self.rect(x + self.col_widths[0], y, self.col_widths[1], row_height)
        for i, line in enumerate(desc_lines):
            self.set_xy(x + self.col_widths[0], y + i * self.line_height)
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
        self.set_font("helvetica", "B", 10)
        self.cell(sum(self.col_widths[:2]), 8, "Total", border="T")
        self.cell(self.col_widths[2], 8, f"{total_hours:.2f}", border="T")
        self.cell(self.col_widths[3], 8, f"${total_amount:.2f}", border="T")
        self.ln()

# --- Usage CSV transformation (with dynamic step-up suffixing) ---
def show_csv_transformation_tab():
    st.header("CSV Transformation for Usage Upload")
    st.markdown("Transform Metabase Invoicing CSV into the format required for usage upload.")

    st.info("Upload Metabase Invoicing CSV file for usage data transformation and (optional) dynamic step-up suffixing.")

    uploaded_file = st.file_uploader(
        "Upload Metabase Invoicing CSV File",
        type=['csv'],
        help="Upload the Metabase Invoicing CSV file",
        key="transformation_upload"
    )

    # Step-up pricing settings
    st.markdown("---")
    st.subheader("Step-Up Pricing Configuration (Optional)")
    enable_stepup_pricing = st.checkbox(
        "Enable dynamic step-up suffixing based on live obligations",
        help="Looks up step-up tiers and appends ' - 1', ' - 2', etc. when name + rate match for the same customer."
    )

    if enable_stepup_pricing:
        api_token = st.text_input("🔑 Tabs API Key", type="password", placeholder="paste API key…")
        if api_token:
            st.session_state.api_key = api_token  # store once
        if st.button("Fetch Latest Step-Up Pricing"):
            step_df = fetch_dynamic_stepup_pricing()
            if step_df is not None:
                st.session_state.dynamic_stepup_data = step_df
                st.success(f"Fetched {len(step_df)} step-up rows.")
                st.dataframe(step_df, use_container_width=True)

    # Column mapping UI
    if uploaded_file is not None:
        try:
            df_original = pd.read_csv(uploaded_file)
            st.subheader("Original Data Preview")
            st.dataframe(df_original, use_container_width=True, hide_index=True)

            st.subheader("Usage Column Mapping")
            st.info(
                "**Expected Usage Columns:**\n"
                "- Event_type_name → **event_type_name**\n"
                "- Value (sum(hours)) → **value**\n"
                "- Datetime (last_worklog_date) → **datetime**\n"
                "- Customer_id (tabs_customer_id) → **customer_id**\n"
                "- Invoice (purchaseOrder) → **invoice**"
            )

            cols = [''] + list(df_original.columns)
            c1, c2 = st.columns(2)
            with c1:
                talent_col = st.selectbox("Talent / Event Type Column", cols)
                hours_col = st.selectbox("Hours / Value Column", cols)
                date_col = st.selectbox("Date Column", cols)
            with c2:
                customer_id_col = st.selectbox("Customer ID Column", cols)
                invoice_col = st.selectbox("Invoice Column (will be cleared)", cols)
                company_col = st.selectbox("Company Name Column (optional)", cols, index=0)

            # Optional split invoices
            st.markdown("---")
            st.subheader("Split Invoice Configuration (Optional)")
            enable_split_invoices = st.checkbox("Enable split invoice numbering (blank, 1, 2, …) per selected customers")
            if enable_split_invoices:
                if company_col and company_col in df_original.columns:
                    uniq = [str(x) for x in df_original[company_col].dropna().unique()]
                    selected_customers = st.multiselect("Customers (by Company Name)", uniq)
                    # resolve to IDs
                    selected_ids = []
                    if selected_customers:
                        for nm in selected_customers:
                            mask = (df_original[company_col] == nm) & df_original[customer_id_col].notna()
                            selected_ids.extend([str(x) for x in df_original.loc[mask, customer_id_col].unique() if str(x)])
                    st.session_state.split_customers = list(set(selected_ids))
                else:
                    uniq_ids = [str(x) for x in df_original[customer_id_col].dropna().unique()]
                    st.session_state.split_customers = st.multiselect("Customers (by ID)", uniq_ids)

            if st.button("Transform Data", type="primary"):
                if not all([talent_col, hours_col, date_col, customer_id_col, invoice_col]):
                    st.error("Please map all required columns.")
                    return

                with st.spinner("Transforming data..."):
                    # Rename to canonical names
                    mapping = {
                        talent_col: "event_type_name",
                        hours_col: "value",
                        date_col: "datetime",
                        customer_id_col: "customer_id",
                        invoice_col: "invoice",
                    }
                    df = df_original.rename(columns=mapping).copy()
                    if company_col and company_col in df.columns:
                        df = df.rename(columns={company_col: "company_name"})

                    # Coerce types/format
                    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce").dt.strftime("%-m/%-d/%Y")
                    df["value"] = pd.to_numeric(df["value"], errors="coerce").fillna(0)

                    # ---- Dynamic step-up suffixing ----
                    if enable_stepup_pricing:
                        step_df = st.session_state.get("dynamic_stepup_data")
                        if step_df is None or step_df.empty:
                            st.info("No step-up data loaded. Click 'Fetch Latest Step-Up Pricing' first.")
                        else:
                            # Build: (customer_id, base_name, pricing_amount) -> suffix
                            # 1) derive base_name + suffix from billingSchedule_name
                            tmp = step_df.copy()
                            name_parts = tmp["billingSchedule_name"].str.split(" - ", n=1, expand=True)
                            tmp["base_name"] = name_parts[0]
                            tmp["suffix"] = name_parts[1].apply(lambda x: f" - {x}" if isinstance(x, str) and x else "") if name_parts.shape[1] > 1 else ""
                            # 2) map contract->customer
                            contract_col = "contractId" if "contractId" in tmp.columns else None
                            contract_to_customer = map_contracts_to_customers(tmp[contract_col].dropna().unique()) if contract_col else {}
                            tmp["customer_id"] = tmp[contract_col].map(contract_to_customer) if contract_col else None
                            tmp = tmp.dropna(subset=["customer_id", "base_name", "pricing_amount"])

                            # 3) choose a rate column from the uploaded CSV to compare with pricing_amount
                            rate_col_candidates = [c for c in df.columns if c.lower() in {"rate", "unit_price", "price", "amount"}]
                            rate_col = rate_col_candidates[0] if rate_col_candidates else None
                            if not rate_col:
                                st.info("No rate column found in CSV; step-up suffixing will match by name+customer only.")
                            else:
                                df[rate_col] = pd.to_numeric(df[rate_col], errors="coerce")

                            # 4) apply suffix where (customer_id, event_type_name w/o suffix, rate) match
                            applied = 0
                            # Build quick lookup: for each (cust, base, amount) get suffix (prefer exact amount matches)
                            idx_cols = ["customer_id", "base_name"]
                            if rate_col:
                                idx_cols.append("pricing_amount")
                            lut = tmp[idx_cols + ["suffix"]].drop_duplicates()

                            # Prepare df columns
                            df["event_type_name"] = df["event_type_name"].astype(str)
                            mask_no_suffix = ~df["event_type_name"].str.contains(r"\s-\s*\d+", regex=True)
                            # create base_name extracted from CSV name
                            df["_base_from_csv"] = df["event_type_name"].str.split(" - ", n=1).str[0]

                            # join on customer + base (+ rate if available)
                            left = df.loc[mask_no_suffix, ["customer_id", "_base_from_csv"] + ([rate_col] if rate_col else [])].copy()
                            if rate_col:
                                left = left.rename(columns={rate_col: "pricing_amount"})
                            left = left.join(df.loc[mask_no_suffix, ["event_type_name"]])  # bring name back for index alignment

                            merged = left.merge(lut, how="left",
                                               left_on=["customer_id", "_base_from_csv"] + (["pricing_amount"] if rate_col else []),
                                               right_on=["customer_id", "base_name"] + (["pricing_amount"] if rate_col else []))

                            # Apply suffix where found
                            to_update = merged["suffix"].notna()
                            idxs = merged.index[to_update]
                            if len(idxs) > 0:
                                # map original df indices
                                target_idx = df.loc[mask_no_suffix].iloc[idxs].index
                                df.loc[target_idx, "event_type_name"] = df.loc[target_idx, "event_type_name"] + merged.loc[idxs, "suffix"].values
                                applied = len(idxs)

                            st.success(f"Step-up suffixes applied to {applied} rows.")

                    # ---- Split invoices (optional) ----
                    # Regardless, clear invoice values as per workflow
                    df["invoice"] = ""
                    if enable_split_invoices and st.session_state.get("split_customers"):
                        for cust_id in st.session_state.split_customers:
                            cust_idx = df.index[df["customer_id"].astype(str) == str(cust_id)].tolist()
                            for i, idx in enumerate(cust_idx):
                                df.at[idx, "invoice"] = "" if i == 0 else str(i)

                    # Ensure required columns exist
                    for col in ["event_type_name", "value", "datetime", "customer_id", "invoice"]:
                        if col not in df.columns:
                            df[col] = ""

                    # Drop missing customer_id
                    missing = df["customer_id"].isna() | (df["customer_id"].astype(str).str.strip() == "")
                    miss_count = int(missing.sum())
                    if miss_count:
                        st.warning(f"{miss_count} rows removed due to missing customer_id.")
                    df = df.loc[~missing, ["event_type_name", "value", "datetime", "customer_id", "invoice"]]

                    st.subheader("Transformed Data Preview")
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    st.download_button(
                        label="Download Transformed CSV",
                        data=df.to_csv(index=False),
                        file_name=f"usage_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
        except Exception as e:
            st.error(f"Error processing CSV: {e}")

# --- PDF workflow ---
def show_pdf_workflow_tab():
    st.header("PDF Generation & Upload Workflow")
    st.info("Upload Metabase weekly report CSV → generate PDFs → map to invoice IDs → bulk upload to Tabs.")

    # Session init
    st.session_state.setdefault("workflow_progress", {
        "csv_uploaded": False,
        "pdfs_generated": False,
        "csv_mapping_created": False,
        "ready_for_upload": False
    })
    st.session_state.setdefault("uploaded_csv", None)
    st.session_state.setdefault("generated_pdfs", [])
    st.session_state.setdefault("pdf_csv_data", None)
    st.session_state.setdefault("pdf_problematic_files", None)

    # Reset
    if any(st.session_state.workflow_progress.values()):
        if st.button("🔄 Reset Workflow", type="secondary", help="Clear all progress and start over"):
            st.session_state.workflow_progress = {
                "csv_uploaded": False, "pdfs_generated": False,
                "csv_mapping_created": False, "ready_for_upload": False
            }
            for k in ["uploaded_csv", "generated_pdfs", "pdf_csv_data", "pdf_problematic_files"]:
                st.session_state[k] = None
            st.success("Workflow reset. Refresh if UI doesn't update.")

    # Step 1: Upload CSV
    st.subheader("📁 Step 1: Upload CSV")
    if st.session_state.uploaded_csv is None:
        up = st.file_uploader("Choose weekly report CSV", type=["csv"])
        if up is not None:
            try:
                df = pd.read_csv(up)
                st.session_state.uploaded_csv = df
                st.session_state.workflow_progress["csv_uploaded"] = True
                st.success(f"CSV uploaded: {len(df)} rows.")
                st.dataframe(df.head(10), use_container_width=True)
            except Exception as e:
                st.error(f"CSV read error: {e}")
    else:
        df = st.session_state.uploaded_csv
        st.success(f"CSV ready: {len(df)} rows loaded.")

    # Step 2: Generate PDFs
    st.subheader("📄 Step 2: Generate PDFs")
    if st.session_state.uploaded_csv is None:
        st.info("Upload CSV in Step 1 first.")
        return

    enable_split = st.checkbox("Split invoices by talent for selected companies")
    split_customers_text = ""
    if enable_split:
        split_customers_text = st.text_area("Split Customer Names (one per line)", placeholder="CompanyA\nCompanyB")

    if st.button("Process Data & Generate PDFs", type="primary"):
        with st.spinner("Generating PDFs..."):
            try:
                df = st.session_state.uploaded_csv.copy()

                # Clean currency column
                if "Company_Total_No_Currency ($)" in df.columns:
                    df["Company_Total_No_Currency ($)"] = (
                        df["Company_Total_No_Currency ($)"]
                        .astype(str).str.replace("$", "", regex=False)
                        .str.replace(",", "", regex=False).astype(float)
                    )

                # Expand multi-line descriptions into rows
                rows = []
                for _, r in df.iterrows():
                    base_date = format_date(r.get("date"))
                    staffer = r.get("Staffer_Name", "")
                    company = r.get("Company_Name", "")
                    customer_id = r.get("tabs_customer_id", "")
                    base_hours = float(r.get("Hours", 0) or 0)
                    base_amount = float(r.get("Company_Total_No_Currency ($)", 0) or 0)

                    lines = clean_description(r.get("description", "")).split("\n")
                    valid = [ln for ln in lines if ln.strip()]
                    n = max(1, len(valid))
                    per_h = base_hours / n
                    per_amt = base_amount / n

                    for ln in valid or [""]:
                        rows.append({
                            "date": base_date,
                            "description": normalize_text(ln),
                            "Hours": round(per_h, 2),
                            "Company_Total_No_Currency ($)": round(per_amt, 2),
                            "Staffer_Name": staffer,
                            "Company_Name": company,
                            "tabs_customer_id": customer_id
                        })
                df_expanded = pd.DataFrame(rows)

                pdf_info_list = []
                temp_dir = tempfile.mkdtemp()
                split_list = [s.strip() for s in split_customers_text.splitlines() if s.strip()] if enable_split else []

                for company, grp in df_expanded.groupby("Company_Name"):
                    customer_id = grp["tabs_customer_id"].iloc[0]
                    month_str = pd.to_datetime(grp["date"]).min().strftime("%B")

                    def _make_pdf(fname, parts):
                        path = os.path.join(temp_dir, fname)
                        pdf = LawtradesPDF(company)
                        for talent, rows_ in parts:
                            pdf.add_talent_section(talent)
                            total_h = rows_["Hours"].sum()
                            total_amt = rows_["Company_Total_No_Currency ($)"].sum()
                            for _, rr in rows_.iterrows():
                                pdf.add_row(rr)
                            pdf.add_totals(total_h, total_amt)
                        pdf.output(path)
                        return path

                    if enable_split and company in split_list:
                        for talent, tdf in grp.groupby("Staffer_Name"):
                            tname = str(talent or "").replace(" ", "").replace(",", "").replace(".", "")
                            fname = f"{company.replace(' ', '')}_{tname}_hoursReport_{month_str}_{customer_id}.pdf"
                            p = _make_pdf(fname, [(talent, tdf)])
                            pdf_info_list.append({"path": p, "filename": fname, "company": company, "invoice_id": None, "talent_name": talent})
                    else:
                        fname = f"{company.replace(' ', '')}_hoursReport_{month_str}_{customer_id}.pdf"
                        parts = [(tal, subdf) for tal, subdf in grp.groupby("Staffer_Name")]
                        p = _make_pdf(fname, parts)
                        pdf_info_list.append({"path": p, "filename": fname, "company": company, "invoice_id": None, "talent_name": ""})

                st.session_state.generated_pdfs = pdf_info_list
                st.session_state.workflow_progress["pdfs_generated"] = True
                st.success(f"Generated {len(pdf_info_list)} PDFs.")

                st.subheader("Generated Files")
                for i, info in enumerate(pdf_info_list, 1):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.write(f"{i}. {info['filename']}")
                    with c2:
                        if os.path.exists(info["path"]):
                            with open(info["path"], "rb") as f:
                                st.download_button("View PDF", data=f.read(), file_name=info["filename"], mime="application/pdf", key=f"view_{i}")
            except Exception as e:
                st.error(f"PDF generation error: {e}")

    # Step 3: Create CSV Mapping
    st.subheader("📋 Step 3: Create CSV Mapping (Invoice IDs)")
    if not st.session_state.workflow_progress["pdfs_generated"]:
        st.info("Generate PDFs in Step 2 first.")
        return

    if "selected_issue_date" not in st.session_state:
        st.session_state.selected_issue_date = datetime.now().date().replace(day=1)
    issue_date = st.date_input("Invoice issue date used for lookup", value=st.session_state.selected_issue_date)

    if st.button("Generate CSV Mapping", type="primary"):
        with st.spinner("Looking up invoice IDs and building mapping CSV..."):
            csv_rows, problems = [], []
            for info in st.session_state.generated_pdfs:
                fname = info["filename"]
                company_id = extract_serial_code(fname)
                inv_id = exists_invoice(company_id, None, issue_date) if company_id else None
                if inv_id:
                    csv_rows.append({
                        "Manufacturer_id": PROD_MANUFACTURER_ID,
                        "Customer_id": company_id,
                        "Invoice_id": inv_id,
                        "Company_name": info["company"],
                        "Filename": fname,
                        "Filepath": info["path"],
                        "Talent_name": info["talent_name"]
                    })
                else:
                    problems.append({
                        "Filename": fname,
                        "Company": info["company"],
                        "Company_ID": company_id,
                        "Issue": "No invoice found" if company_id else "Invalid customer_id in filename",
                        "Filepath": info["path"],
                        "Talent_name": info["talent_name"]
                    })

            st.session_state.pdf_csv_data = pd.DataFrame(csv_rows)
            st.session_state.pdf_problematic_files = pd.DataFrame(problems)
            st.session_state.workflow_progress["csv_mapping_created"] = True

            st.success("CSV mapping generated.")
            st.write(f"{len(csv_rows)} mapped • {len(problems)} need attention")

            if len(csv_rows):
                st.download_button(
                    "Download PDF Mapping CSV",
                    data=st.session_state.pdf_csv_data.to_csv(index=False).encode("utf-8"),
                    file_name="pdf_mapping_successful.csv",
                    mime="text/csv"
                )
            if len(problems):
                st.download_button(
                    "Download Problematic Files CSV",
                    data=st.session_state.pdf_problematic_files.to_csv(index=False).encode("utf-8"),
                    file_name="pdf_mapping_problematic.csv",
                    mime="text/csv"
                )

    # Step 4: Bulk Upload
    st.subheader("🚀 Step 4: Bulk Upload PDFs")
    if st.session_state.pdf_csv_data is None or st.session_state.pdf_csv_data.empty:
        st.info("Create CSV mapping in Step 3 first.")
        return

    c1, c2 = st.columns(2)
    with c1:
        environment = st.selectbox("Environment", ["Production", "Sandbox"])
    with c2:
        _timeout = st.number_input("Request Timeout (s)", min_value=10, max_value=300, value=30)

    merchant_id_display = PROD_MANUFACTURER_ID if environment == "Production" else SANDBOX_MANUFACTURER_ID
    c3, c4 = st.columns(2)
    with c3:
        api_key_input = st.text_input("API Key", type="password", value=st.session_state.get("api_key", ""))
        if api_key_input:
            st.session_state.api_key = api_key_input
    with c4:
        st.text_input("Merchant ID", value=merchant_id_display, disabled=True)

    if st.button("Start Bulk Upload", type="primary"):
        if not st.session_state.get("api_key"):
            st.error("Please enter your API key.")
            return
        with st.spinner("Uploading PDFs..."):
            df_upload = st.session_state.pdf_csv_data
            progress = st.progress(0)
            status = st.empty()
            ok = err = 0
            for i, row in df_upload.iterrows():
                status.text(f"Processing {i+1}/{len(df_upload)}: {row['Filename']}")
                cust_id = row["Customer_id"]; inv_id = row["Invoice_id"]; path = row["Filepath"]
                if inv_id and os.path.exists(path):
                    if upload_attachment(cust_id, inv_id, path, row.get("Talent_name", "")):
                        ok += 1
                    else:
                        err += 1
                else:
                    err += 1
                progress.progress((i+1)/len(df_upload))
            progress.empty(); status.empty()
            if ok: st.success(f"Uploaded {ok} PDF(s).")
            if err: st.error(f"Failed {err} upload(s).")

# --- Main App ---
def main():
    with st.sidebar:
        st.header("📋 Instructions")
        st.markdown("""
        **Workflows**
        1) **Usage CSV Transformation**: Transform Metabase data and (optionally) auto-append step-up suffixes via API.
        2) **PDF Workflow**: Generate invoice PDFs and bulk attach to Tabs.
        """)
        st.markdown("---")
        st.markdown("### 🔧 API")
        st.info("Set your API key in either the Transformation (for step-up) or in PDF Step 4.")

    st.title("Lawtrades Internal Tool")
    tab1, tab2 = st.tabs(["Usage CSV Transformation", "PDF Workflow"])
    with tab1:
        show_csv_transformation_tab()
    with tab2:
        show_pdf_workflow_tab()

if __name__ == "__main__":
    main()


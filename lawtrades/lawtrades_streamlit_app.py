#!/usr/bin/env python3
"""
Lawtrades Invoicing Pipeline - Streamlit App
===========================================
A user-friendly web interface for the complete Lawtrades invoicing workflow:
1. Upload CSV data
2. Generate PDFs from data
3. Create CSV mapping for PDFs
4. Bulk attach PDFs to invoices
"""

import os
import csv
import io
import tempfile
import zipfile
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

# Suppress deprecation warnings to improve performance
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

def fetch_dynamic_stepup_pricing(api_base_url="https://integrators.prod.api.tabsplatform.com/v3", api_token=None):
    """Fetch step-up pricing data from Tabs Platform API"""
    try:
        with st.spinner("Fetching latest step-up pricing from Tabs Platform API..."):
            # Check if API token is provided
            if not api_token:
                st.error("❌ **API Token Required:** Please provide a valid API token for the Tabs Platform API")
                return None
            
            # Add authentication headers - use same method as bulk upload
            headers = {
                'Authorization': api_token,  # Direct API key (not Bearer token)
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Make API request to get all obligations
            obligations_url = f"{api_base_url}/obligations?limit=1000"
            response = requests.get(obligations_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                
                # Check if we have data in the expected format
                if isinstance(data, dict) and 'payload' in data:
                    # Extract the actual data from payload.data
                    payload = data.get('payload', {})
                    obligations_data = payload.get('data', [])
                    
                    if isinstance(obligations_data, list) and len(obligations_data) > 0:
                        st.success(f"✅ Successfully fetched {len(obligations_data)} obligations from Tabs Platform API")
                        
                        # Convert to DataFrame without any filtering
                        df = pd.DataFrame(obligations_data)
                        
                        # Flatten nested billingSchedule data to match the Object Viewer columns
                        if 'billingSchedule' in df.columns:
                            # Expand billingSchedule object into separate columns
                            billing_schedule_df = pd.json_normalize(df['billingSchedule'])
                            billing_schedule_df.columns = [f'billingSchedule_{col}' for col in billing_schedule_df.columns]
                            
                            # Handle the pricing array - extract amount from first pricing tier
                            if 'billingSchedule_pricing' in billing_schedule_df.columns:
                                # Extract pricing data from the array
                                def extract_pricing_amount(pricing_list):
                                    if isinstance(pricing_list, list) and len(pricing_list) > 0:
                                        return pricing_list[0].get('amount', None)
                                    return None
                                
                                def extract_pricing_tier(pricing_list):
                                    if isinstance(pricing_list, list) and len(pricing_list) > 0:
                                        return pricing_list[0].get('tier', None)
                                    return None
                                
                                def extract_pricing_amount_type(pricing_list):
                                    if isinstance(pricing_list, list) and len(pricing_list) > 0:
                                        return pricing_list[0].get('amountType', None)
                                    return None
                                
                                def extract_pricing_tier_minimum(pricing_list):
                                    if isinstance(pricing_list, list) and len(pricing_list) > 0:
                                        return pricing_list[0].get('tierMinimum', None)
                                    return None
                                
                                # Create columns for the first pricing tier
                                billing_schedule_df['billingSchedule_pricing_0_amount'] = billing_schedule_df['billingSchedule_pricing'].apply(extract_pricing_amount)
                                billing_schedule_df['billingSchedule_pricing_0_tier'] = billing_schedule_df['billingSchedule_pricing'].apply(extract_pricing_tier)
                                billing_schedule_df['billingSchedule_pricing_0_amountType'] = billing_schedule_df['billingSchedule_pricing'].apply(extract_pricing_amount_type)
                                billing_schedule_df['billingSchedule_pricing_0_tierMinimum'] = billing_schedule_df['billingSchedule_pricing'].apply(extract_pricing_tier_minimum)
                                
                                # Drop the original pricing column
                                billing_schedule_df = billing_schedule_df.drop('billingSchedule_pricing', axis=1)
                            
                            # Drop the original billingSchedule column and add the flattened ones
                            df = df.drop('billingSchedule', axis=1)
                            df = pd.concat([df, billing_schedule_df], axis=1)
                        
                        # Flatten nested discount data if it exists
                        if 'discount' in df.columns:
                            discount_df = pd.json_normalize(df['discount'])
                            discount_df.columns = [f'discount_{col}' for col in discount_df.columns]
                            
                            # Drop the original discount column and add the flattened ones
                            df = df.drop('discount', axis=1)
                            df = pd.concat([df, discount_df], axis=1)
                        
                        # Filter the data
                        if 'billingSchedule_name' in df.columns:
                            # Filter to only show rows where billingSchedule_name contains "- 1" or "- 2"
                            df_filtered = df[df['billingSchedule_name'].str.contains('- 1|- 2', na=False, regex=True)]
                            
                            # Filter out "FLAT" billing types
                            if 'billingSchedule_billingType' in df_filtered.columns:
                                df_filtered = df_filtered[df_filtered['billingSchedule_billingType'] != 'FLAT']
                            
                            # Filter out expired entries (endDate in the past)
                            if 'billingSchedule_endDate' in df_filtered.columns:
                                import pytz
                                
                                # Parse the end dates and ensure they're timezone-aware
                                df_filtered['billingSchedule_endDate_parsed'] = pd.to_datetime(df_filtered['billingSchedule_endDate'], errors='coerce')
                                
                                # Get current date in UTC to match the API timezone
                                current_date = datetime.now(pytz.UTC)
                                
                                # Filter out expired entries
                                df_filtered = df_filtered[df_filtered['billingSchedule_endDate_parsed'] > current_date]
                                df_filtered = df_filtered.drop('billingSchedule_endDate_parsed', axis=1)
                            
                            
                            # Select the columns you want to display - include contractId for mapping
                            columns_to_show = ['billingSchedule_name', 'billingSchedule_pricing_0_amount', 'contractId']
                            available_columns = [col for col in columns_to_show if col in df_filtered.columns]
                            
                            if available_columns:
                                df_final = df_filtered[available_columns].copy()
                                return df_final
                            else:
                                st.warning("Required columns not found in the data")
                                st.write(f"Available columns: {list(df_filtered.columns)}")
                                return df_filtered
                        else:
                            st.warning("billingSchedule_name column not found")
                        return df
                    else:
                        st.warning("No obligations data found in API payload")
                        return None
                else:
                    st.warning("API response indicates failure or unexpected format")
                    if isinstance(data, dict) and 'message' in data:
                        st.write(f"API Message: {data['message']}")
                    return None
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
    except requests.exceptions.ConnectionError:
        st.error("❌ **Connection Error:** Cannot connect to Tabs Platform API. Please check your internet connection.")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ **Timeout Error:** API request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"Error fetching step-up pricing from Tabs Platform API: {e}")
        return None

def create_stepup_mapping_from_api(df):
    """Create step-up pricing mapping from API results"""
    if df is None or len(df) == 0:
        return {}
    
    stepup_mapping = {}
    
    for _, row in df.iterrows():
        lawyer_name = row['lawyer_name']
        customer_id = row['customer_id']
        suffix = row['suffix']
        unit_price = row['unit_price']
        
        stepup_mapping[lawyer_name] = {
            'customer_id': customer_id,
            'suffix': suffix,
            'unit_price': unit_price
        }
    
    return stepup_mapping


from fpdf import FPDF
from datetime import datetime

# Page configuration
# Helper functions from original create_csv.py
def extract_serial_code(filename):
    """Extract company ID from filename (last part before .pdf)"""
    try:
        base = os.path.splitext(filename)[0]
        parts = base.split("_")
        company_id = parts[-1] if parts else None
        
        # Handle edge cases
        if not company_id or company_id.lower() in ['nan', 'none', '']:
            return None
            
        # Validate that it looks like a UUID
        if is_valid_uuid(company_id):
            return company_id
        else:
            # Try to find a UUID in the filename parts
            for part in parts:
                if is_valid_uuid(part):
                    return part
            return None
            
    except Exception:
        return None

def is_valid_uuid(val):
    """Check if value is a valid UUID"""
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


# UNUSED FUNCTION - REMOVED DUE TO CACHING SYSTEM
# def fetch_invoices_from_api(issue_date=None, api_token=None, customer_id=None):
    """Fetch invoices from Tabs Platform API using global endpoint with pagination to get ALL invoices"""
    if not api_token:
        st.warning("API token required for invoice lookup")
        return None
    
    try:
        # API configuration
        api_base_url = "https://integrators.prod.api.tabsplatform.com/v3"
        headers = {
            'Authorization': api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Use global endpoint with pagination to get ALL invoices
        url = f"{api_base_url}/invoices"
        
        # Strategy 1: Try with date filter first (but still use pagination)
        if issue_date:
            all_invoices = []
            page = 1
            limit = 1000
            
            while True:
                params = {
                    'limit': limit,
                    'page': page,
                    'issueDate': issue_date.strftime('%Y-%m-%d')
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and 'payload' in data:
                        page_invoices = data['payload'].get('data', [])
                    elif 'data' in data:
                        page_invoices = data.get('data', [])
                    else:
                        page_invoices = []
                    
                    if not page_invoices:
                        break  # No more invoices
                    
                    all_invoices.extend(page_invoices)
                    
                    # If we got less than the limit, we've reached the end
                    if len(page_invoices) < limit:
                        break
                    
                    page += 1
                    
                    # Safety check to prevent infinite loops
                    if page > 100:  # Max 100,000 invoices
                        st.warning("⚠️ Reached maximum page limit (100), stopping pagination")
                        break
                else:
                    break
            
            if all_invoices:
                st.info(f"✅ Found {len(all_invoices)} invoices with date filter ({issue_date.strftime('%Y-%m-%d')}) across {page} pages")
                return all_invoices
        
        # Strategy 2: Get ALL invoices without date filter using pagination
        st.info("🔍 No results with date filter, fetching ALL invoices with pagination...")
        
        # Check if we have cached invoices in session state (unless force refresh is enabled)
        cache_key = f"all_invoices_cache_{api_token[:10]}"  # Use first 10 chars of API key as cache key
        if not st.session_state.get('force_refresh', False) and cache_key in st.session_state:
            cached_invoices = st.session_state[cache_key]
            st.info(f"✅ Using cached invoices ({len(cached_invoices)} total)")
            return cached_invoices
        
        # Check for persistent cache file (unless force refresh is enabled)
        if not st.session_state.get('force_refresh', False):
            cache_file = f"invoice_cache_{api_token[:10]}.json"
            if os.path.exists(cache_file):
                try:
                    import json
                    with open(cache_file, 'r') as f:
                        cached_data = json.load(f)
                        # Check if cache is less than 1 hour old
                        cache_time = cached_data.get('timestamp', 0)
                        current_time = datetime.now().timestamp()
                        if current_time - cache_time < 3600:  # 1 hour
                            cached_invoices = cached_data.get('invoices', [])
                            st.info(f"✅ Using persistent cache ({len(cached_invoices)} invoices, cached {int((current_time - cache_time)/60)} minutes ago)")
                            # Also store in session state for faster access
                            st.session_state[cache_key] = cached_invoices
                            return cached_invoices
                        else:
                            st.info("🕒 Cache expired, fetching fresh data...")
                except:
                    st.info("🔄 Cache file corrupted, fetching fresh data...")
        
        # Try to get recent invoices first with date range approach
        fast_mode = st.session_state.get('fast_mode', True)
        if fast_mode:
            st.info("🚀 Fast Mode: Fetching recent invoices only (last 2 years)...")
        else:
            st.info("🐌 Full Mode: Will fetch ALL invoices (slower but comprehensive)...")
        
        # Strategy 2a: Try to get invoices for the specific date only
        from datetime import timedelta
        
        if not issue_date:
            st.error("❌ No issue date provided. Please select a specific date.")
            return None
        
        st.info(f"🎯 Ultra-Fast Mode: Fetching invoices for {issue_date.strftime('%Y-%m-%d')} only")
        
        # Ultra-fast single API call with aggressive optimizations
        params = {
            'limit': 1000,  # Start with standard limit for speed
            'issueDate': issue_date.strftime('%Y-%m-%d')  # Only get invoices for this exact date
        }
        
        st.info("⚡ Making ultra-fast API call...")
        
        # Use shorter timeout and aggressive optimizations
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'payload' in data:
                all_invoices = data['payload'].get('data', [])
            elif 'data' in data:
                all_invoices = data.get('data', [])
            else:
                all_invoices = []
            
            if all_invoices:
                st.success(f"⚡ Found {len(all_invoices)} invoices for {issue_date.strftime('%Y-%m-%d')} in {response.elapsed.total_seconds():.2f}s!")
            else:
                st.warning(f"⚠️ No invoices found for {issue_date.strftime('%Y-%m-%d')}")
        else:
            st.error(f"❌ API call failed with status {response.status_code}")
            all_invoices = []
        
        # If we got invoices, use them and skip the full pagination
        if all_invoices:
            
            # Cache the results for future use
            st.session_state[cache_key] = all_invoices
            
            # Also save to persistent cache file
            try:
                import json
                cache_data = {
                    'timestamp': datetime.now().timestamp(),
                    'invoices': all_invoices
                }
                with open(cache_file, 'w') as f:
                    json.dump(cache_data, f)
                st.info(f"💾 Saved {len(all_invoices)} invoices to persistent cache")
            except Exception as e:
                st.warning(f"⚠️ Could not save to persistent cache: {e}")
            
            # Filter by customer if we have one
            if customer_id:
                customer_invoices = [inv for inv in all_invoices if inv.get('customerId') == customer_id]
                if customer_invoices:
                    st.info(f"✅ Found {len(customer_invoices)} invoices for customer {customer_id}")
                    return customer_invoices
            
            # Return all invoices for client-side filtering
            return all_invoices
        
        # Strategy 2b: If no invoices found for the exact date, try nearby dates (±3 days) - FAST
        if fast_mode:
            st.warning(f"⚠️ No invoices found for {issue_date.strftime('%Y-%m-%d')}. Trying nearby dates (±3 days)...")
            
            # Try only the most likely nearby dates (not all 7 days)
            nearby_dates = [
                issue_date + timedelta(days=1),   # Next day
                issue_date - timedelta(days=1),   # Previous day
                issue_date + timedelta(days=2),   # Day after tomorrow
                issue_date - timedelta(days=2),   # Day before yesterday
            ]
            
            for nearby_date in nearby_dates:
                st.info(f"🔍 Trying {nearby_date.strftime('%Y-%m-%d')}...")
                
                # Ultra-fast single API call for nearby date
                params = {
                    'limit': 1000,
                    'issueDate': nearby_date.strftime('%Y-%m-%d')
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') and 'payload' in data:
                        nearby_invoices = data['payload'].get('data', [])
                    elif 'data' in data:
                        nearby_invoices = data.get('data', [])
                    else:
                        nearby_invoices = []
                    
                    if nearby_invoices:
                        st.success(f"⚡ Found {len(nearby_invoices)} invoices for {nearby_date.strftime('%Y-%m-%d')} in {response.elapsed.total_seconds():.2f}s!")
                        # Cache and return the nearby invoices
                        st.session_state[cache_key] = nearby_invoices
                        return nearby_invoices
            
            st.error(f"❌ No invoices found for {issue_date.strftime('%Y-%m-%d')} or nearby dates (±3 days).")
            return None
        else:
            st.warning(f"⚠️ No invoices found for {issue_date.strftime('%Y-%m-%d')}, falling back to full pagination (this will be slower)...")
        
        all_invoices = []
        page = 1
        
        while True:
            params = {
                'limit': limit,
                'page': page
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'payload' in data:
                    page_invoices = data['payload'].get('data', [])
                elif 'data' in data:
                    page_invoices = data.get('data', [])
                else:
                    page_invoices = []
                
                if not page_invoices:
                    break  # No more invoices
                
                all_invoices.extend(page_invoices)
                
                # If we got less than the limit, we've reached the end
                if len(page_invoices) < limit:
                    break
                
                page += 1
                
                # Safety check to prevent infinite loops
                if page > 100:  # Max 100,000 invoices
                    st.warning("⚠️ Reached maximum page limit (100), stopping pagination")
                    break
                    
                # Show progress for large datasets
                if page % 10 == 0:
                    st.info(f"📄 Fetched {len(all_invoices)} invoices so far (page {page})...")
            else:
                break
        
        if all_invoices:
            st.info(f"✅ Fetched {len(all_invoices)} total invoices")
            
            # Cache the results for future use
            st.session_state[cache_key] = all_invoices
            
            # Filter by customer if we have one
            if customer_id:
                customer_invoices = [inv for inv in all_invoices if inv.get('customerId') == customer_id]
                if customer_invoices:
                    st.info(f"✅ Found {len(customer_invoices)} invoices for customer {customer_id}")
                    return customer_invoices
            
            # Return all invoices for client-side filtering
            return all_invoices
        else:
            st.error("❌ No invoices found")
            return None
            
    except Exception as e:
        st.error(f"API lookup failed: {str(e)}")
        return None

def fetch_all_invoices_for_cache(api_token):
    """Fetch all invoices from API for caching purposes"""
    try:
        api_base_url = "https://integrators.prod.api.tabsplatform.com/v3"
        headers = {
            'Authorization': api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        url = f"{api_base_url}/invoices"
        all_invoices = []
        page = 1
        limit = 1000
        
        st.info("🚀 Starting comprehensive invoice fetch...")
        
        # Create progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while True:
            params = {
                'limit': limit,
                'page': page
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'payload' in data:
                    page_invoices = data['payload'].get('data', [])
                elif 'data' in data:
                    page_invoices = data.get('data', [])
                else:
                    page_invoices = []
                
                if not page_invoices:
                    break  # No more invoices
                
                all_invoices.extend(page_invoices)
                
                # Update progress
                progress = min(page / 50, 1.0)  # Assume max 50 pages
                progress_bar.progress(progress)
                status_text.text(f"📄 Fetched {len(all_invoices)} invoices (page {page})...")
                
                # If we got less than the limit, we've reached the end
                if len(page_invoices) < limit:
                    break
                
                page += 1
                
                # Safety check
                if page > 100:  # Max 100,000 invoices
                    st.warning("⚠️ Reached maximum page limit (100), stopping pagination")
                    break
            else:
                st.error(f"API call failed with status {response.status_code}")
                break
        
        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()
        
        if all_invoices:
            st.success(f"✅ Successfully fetched {len(all_invoices)} invoices across {page} pages")
            return all_invoices
        else:
            st.error("❌ No invoices fetched")
            return None
            
    except Exception as e:
        st.error(f"Failed to fetch invoices: {str(e)}")
        return None

def exists_invoice_database(company_id, fallback_invoice_id, issue_date=None):
    """Check if invoice exists via database, return invoice ID if found (original method)"""
    if not company_id or company_id.lower() == "nan" or not is_valid_uuid(company_id):
        st.warning(f"Invalid company ID: {company_id}")
        return fallback_invoice_id
    
    try:
        conn = get_db_connection()
        if not conn:
            st.error("Database connection failed")
            return fallback_invoice_id
        
        cursor = conn.cursor()
        
        # Build the query based on whether we have an issue date
        if issue_date:
            query = """
                SELECT id FROM invoices 
                WHERE customer_id = %s 
                AND status != 'DELETED' 
                AND invoice_type = 'INVOICE'
                AND DATE(issue_date) = %s
                ORDER BY issue_date DESC 
                LIMIT 1
            """
            cursor.execute(query, (company_id, issue_date))
        else:
            query = """
                SELECT id FROM invoices 
                WHERE customer_id = %s 
                AND status != 'DELETED' 
                AND invoice_type = 'INVOICE'
                ORDER BY issue_date DESC 
                LIMIT 1
            """
            cursor.execute(query, (company_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            invoice_id = result[0]
            st.success(f"✅ Found invoice ID {invoice_id} for company {company_id} (database)")
            return invoice_id
        else:
            date_desc = issue_date.strftime('%Y-%m-%d') if issue_date else "current period"
            st.warning(f"No invoice found for company {company_id} on {date_desc} (database)")
            return fallback_invoice_id
            
    except Exception as e:
        st.error(f"Database lookup failed for {company_id}: {str(e)}")
        return fallback_invoice_id

def exists_invoice(company_id, fallback_invoice_id, issue_date=None):
    """Check if invoice exists via API or database, return invoice ID if found"""
    if not company_id or company_id.lower() == "nan" or not is_valid_uuid(company_id):
        st.warning(f"Invalid company ID: {company_id}")
        return fallback_invoice_id
    
    # Check if user wants to use API or database
    use_api = st.session_state.get('use_api_lookup', False)
    
    if not use_api:
        # Use original database method
        return exists_invoice_database(company_id, fallback_invoice_id, issue_date)
    
    # Use API method
    api_token = st.session_state.get('api_key', '')
    if not api_token:
        st.warning("API key not configured for invoice lookup, falling back to database")
        return exists_invoice_database(company_id, fallback_invoice_id, issue_date)
    
    try:
        # Try to use cached invoices first
        cache_key = f"invoice_cache_{api_token[:10]}"
        cached_invoices = st.session_state.get(cache_key, [])
        
        if cached_invoices:
            # Use cached data for fast lookup
            invoices = cached_invoices
            
            # Filter invoices for this customer and date
            valid_invoices = []
            for invoice in invoices:
                invoice_customer_id = invoice.get('customerId', '')
                invoice_date_str = invoice.get('issueDate', '')
                
                # Check customer match and status
                if (invoice_customer_id == company_id and 
                    invoice.get('status', '').upper() != 'DELETED' and 
                    invoice.get('source', '').upper() == 'TABS'):
                    
                    # If we have a specific date, filter by date
                    if issue_date and invoice_date_str:
                        try:
                            if 'T' in invoice_date_str:
                                invoice_date = pd.to_datetime(invoice_date_str).date()
                            else:
                                invoice_date = pd.to_datetime(invoice_date_str).date()
                            
                            if invoice_date == issue_date:
                                valid_invoices.append(invoice)
                        except:
                            # If date parsing fails, include the invoice anyway
                            valid_invoices.append(invoice)
                    else:
                        # No specific date, include all valid invoices
                        valid_invoices.append(invoice)
            
            if valid_invoices:
                # Sort by issue date (most recent first) and return the first one
                valid_invoices.sort(key=lambda x: x.get('issueDate', ''), reverse=True)
                selected_invoice = valid_invoices[0]
                invoice_id = selected_invoice.get('id')
                actual_issue_date = selected_invoice.get('issueDate', 'Unknown')
                invoice_number = selected_invoice.get('invoiceNumber', 'N/A')
                
                st.success(f"✅ Found invoice ID {invoice_id} (Invoice #{invoice_number}) for company {company_id} (issued: {actual_issue_date}) (CACHED)")
                return invoice_id
        
        # If no cached data or no match found, fall back to database
        st.warning("No cached invoice found, falling back to database lookup")
        return exists_invoice_database(company_id, fallback_invoice_id, issue_date)
        
    except Exception as e:
        st.error(f"API lookup failed for {company_id}: {str(e)}")
        return fallback_invoice_id

def upload_attachment(customer_id, invoice_id, filepath, talent_name=None):
    """Upload PDF attachment to invoice via API"""
    try:
        # Get API configuration from session state
        api_key = st.session_state.get('api_key', '')
        environment = st.session_state.get('environment', 'Sandbox')
        
        if not api_key:
            st.error("API key not configured")
            return False
        
        # Determine API base URL
        api_base_url = "https://integrators.prod.api.tabsplatform.com/v3"
        
        # Construct API URL - use customer_id (company_id) not manufacturer_id
        url = f"{api_base_url}/customers/{customer_id}/invoices/{invoice_id}/attachments"
        
        # Prepare headers
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/octet-stream"
        }
        
        # Modify filename if talent name provided
        filename = os.path.basename(filepath)
        if talent_name:
            name_without_ext = os.path.splitext(filename)[0]
            ext = os.path.splitext(filename)[1]
            filename = f"{name_without_ext}_{talent_name}{ext}"
        
        # Read file and upload
        with open(filepath, 'rb') as file:
            files = {
                'file': (filename, file, 'application/pdf')
            }
            
            # Remove Content-Type header for file upload
            headers.pop('Content-Type', None)
            
            response = requests.post(url, headers=headers, files=files, timeout=30)
            
            if response.status_code in [200, 201]:
                return True
            else:
                st.error(f"❌ Upload failed: {filename}")
                return False
                
    except Exception as e:
        st.error(f"❌ Upload error: {filename}")
        return False

st.set_page_config(
    page_title="Lawtrades Internal Tool",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
if 'uploaded_csv' not in st.session_state:
    st.session_state.uploaded_csv = None
if 'generated_pdfs' not in st.session_state:
    st.session_state.generated_pdfs = []
if 'pdf_csv_data' not in st.session_state:
    st.session_state.pdf_csv_data = None

# Helper functions
def remove_non_latin1(text: str) -> str:
    return ''.join(c for c in str(text) if ord(c) < 256)

def normalize_text(text: str) -> str:
    cleaned = str(text).replace(""", '"').replace(""", '"')\
                       .replace("'", "'").replace("–", "-")\
                       .replace("—", "-").strip()
    return remove_non_latin1(cleaned)

def clean_description(desc):
    return "\n".join(line.strip() for line in str(desc).splitlines() if line.strip())

def format_date(date):
    """Format date string to YYYY-MM-DD format with error handling"""
    try:
        if pd.isna(date) or date is None:
            raise ValueError("Date is null or None")
        
        # Convert to datetime and format
        formatted_date = pd.to_datetime(date).strftime("%Y-%m-%d")
        return formatted_date
    except Exception as e:
        raise ValueError(f"Invalid date format: {date}. Error: {str(e)}")

# Database connection function
def get_db_connection():
    """Get database connection"""
    try:
        # Hardcoded database password
        db_password = "k9gxPS0UoqEbIhx0QhZEp1UeJi5F"
            
        conn = psycopg2.connect(
            dbname="core",
            user="read",
            password=db_password,
            port=5432,
            host="core-1.c1gkmwasa8f7.us-east-1.rds.amazonaws.com",
            sslmode='require'
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# PDF Generation Class
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
        self.set_font("helvetica", "", 9)
        self.cell(self.col_widths[0], row_height, format_date(row["date"]), border="T")

        # Description
        self.set_xy(x + self.col_widths[0], y)
        self.rect(x + self.col_widths[0], y, self.col_widths[1], row_height)
        for i, line in enumerate(desc_lines):
            self.set_xy(x + self.col_widths[0], y + i * self.line_height)
            self.set_font("helvetica", "", 9)
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

# CSV Transformation Functions
def transform_merchant_csv_to_tabs(df):
    """Transform merchant CSV data to Tabs platform format"""
    try:
        # Initialize transformed data
        transformed_data = []
        
        for _, row in df.iterrows():
            # Basic transformation - adjust column mappings as needed
            transformed_row = {
                'date': pd.to_datetime(row.get('date', row.get('Date', ''))).strftime('%Y-%m-%d') if pd.notna(row.get('date', row.get('Date', ''))) else '',
                'description': str(row.get('description', row.get('Description', ''))),
                'Hours': float(row.get('Hours', row.get('hours', 0))) if pd.notna(row.get('Hours', row.get('hours', 0))) else 0,
                'Company_Total_No_Currency ($)': float(row.get('amount', row.get('Amount', row.get('total', 0)))) if pd.notna(row.get('amount', row.get('Amount', row.get('total', 0)))) else 0,
                'Staffer_Name': str(row.get('staffer', row.get('Staffer', row.get('talent', row.get('Talent', ''))))),
                'Company_Name': str(row.get('company', row.get('Company', row.get('client', row.get('Client', ''))))),
                'tabs_customer_id': str(row.get('customer_id', row.get('Customer_ID', row.get('tabs_customer_id', ''))))
            }
            transformed_data.append(transformed_row)
        
        return pd.DataFrame(transformed_data)
    except Exception as e:
        st.error(f"Error transforming CSV: {e}")
        return None

def show_csv_transformation_tab():
    """Show CSV transformation tab"""
    st.header("CSV Transformation for Usage Upload")
    st.markdown("Transform Metabase Invoicing CSV into the format required for usage upload")
    
    # Note about CSV source
    st.info("📝 **Note:** Upload Metabase Invoicing CSV file for usage data transformation and upload. Add monthly, semi-monthly, and upfront CSV's separately.")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload Metabase Invoicing CSV File",
        type=['csv'],
        help="Upload the Metabase Invoicing CSV file",
        key="transformation_upload"
    )
    
    if uploaded_file is not None:
        try:
            # Load the CSV
            df_original = pd.read_csv(uploaded_file)
            
            st.subheader("Original Data Preview")
            st.dataframe(df_original, use_container_width=True, hide_index=True)
            
            # Show column mapping options
            st.subheader("Usage Column Mapping")
            st.markdown("Map Metabase columns to the required usage upload format:")
            
            # Display the expected mappings
            st.info("""
            **Expected Usage Columns:**
            - Event_type_name → maps to **Talent**
            - Value → maps to **sum(hours)**  
            - Datetime → maps to **last_worklog_date**
            - Customer_id → maps to **tabs_customer_id**
            - Invoice → maps to **purchaseOrder**
            """)
            
            col1, col2 = st.columns(2)
            
            # Get available columns
            available_cols = [''] + list(df_original.columns)
            
            with col1:
                talent_col = st.selectbox("Talent Column", available_cols, help="Select the Talent column (maps to Event_type_name)")
                hours_col = st.selectbox("Hours Column (sum(hours))", available_cols, help="Select the sum(hours) column (maps to Value)")
                date_col = st.selectbox("Date Column (last_worklog_date)", available_cols, help="Select the last_worklog_date column (maps to Datetime)")
                
            with col2:
                customer_id_col = st.selectbox("Customer ID Column (tabs_customer_id)", available_cols, help="Select the tabs_customer_id column")
                invoice_col = st.selectbox("Invoice Column (purchaseOrder)", available_cols, help="Select the purchaseOrder column (maps to Invoice)")
                
                # Required: Company name for reference
                company_col = st.selectbox("Company Name Column (Company_Name)", available_cols, help="Select the Company_Name column for reference")
            
            # Step-up pricing option
            st.markdown("---")
            st.subheader("Step-Up Pricing Configuration")
            
            # Pricing source selection
            pricing_source = "Database Query"  # Always use dynamic API data
            
            enable_stepup_pricing = st.checkbox(
                "Enable Step-Up Pricing",
                help="Automatically append '-1' to lawyer names that have step-up pricing"
            )
            
            if enable_stepup_pricing:
                
                # API configuration for dynamic pricing
                if pricing_source == "Database Query":
                    st.info("💡 **Automatic Pricing:** Fetches the latest step-up pricing data via API.")
                    
                    # API Token input
                    api_token = st.text_input(
                        "🔑 API Token", 
                        type="password",
                        help="Enter your Tabs Platform API token for authentication",
                        placeholder="Enter your API token here..."
                    )
                    
                    if st.button("🔄 Fetch Latest Step-Up Pricing"):
                        # Fetch dynamic pricing using API
                        df = fetch_dynamic_stepup_pricing(api_token=api_token)
                        if df is not None:
                            st.session_state.dynamic_stepup_data = df
                            # Don't create stepup mapping since we're showing raw data
                            # st.session_state.dynamic_stepup_mapping = create_stepup_mapping_from_api(df)
                            
                            # Display the data
                            st.subheader("📊 Step-Up Pricing Data")
                            st.write(f"**Total Rows:** {len(df)}")
                            
                            # Show the filtered data
                            st.dataframe(df, use_container_width=True)
                                
            
            # Split invoice option
            st.markdown("---")
            st.subheader("Split Invoice Configuration")
            enable_split_invoices = st.checkbox(
                "Enable Split Invoice Numbering",
                help="When enabled, replaces PO numbers with blank, 1, 2, 3... for selected customers"
            )
            
            if enable_split_invoices:
                st.info("💡 **Split Invoice Mode:** The first row will be blank (base invoice), subsequent rows will be numbered 1, 2, 3, etc.")
                
                # Get unique customer names for selection (if company column is mapped)
                if company_col and company_col != '' and company_col in df_original.columns:
                    unique_customers = df_original[company_col].dropna().unique()
                    unique_customers = [str(c) for c in unique_customers if str(c) != '' and str(c).lower() != 'nan']
                    customer_selection_type = "name"
                else:
                    # Fallback to customer IDs if no company name column
                    unique_customers = df_original[customer_id_col].dropna().unique()
                    unique_customers = [str(c) for c in unique_customers if str(c) != '']
                    customer_selection_type = "id"
                    st.info(f"📋 Using customer IDs from column: **{customer_id_col}** (no company name column selected)")
                
                if len(unique_customers) > 0:
                    st.write(f"**Select customers that need split invoice numbering:**")
                    
                    # Allow selection of multiple customers
                    selected_customers = st.multiselect(
                        f"Customers for Split Numbering ({'by Name' if customer_selection_type == 'name' else 'by ID'})",
                        options=unique_customers,
                        help="Select which customers should have split invoice numbering applied"
                    )
                    
                    if selected_customers:
                        st.success(f"✅ {len(selected_customers)} customers selected for split numbering")
                        # Store selected customers and their IDs for use in transformation
                        if customer_selection_type == "name":
                            # Get corresponding customer IDs for selected names
                            selected_customer_ids = []
                            for customer_name in selected_customers:
                                customer_mask = df_original[company_col] == customer_name
                                customer_ids = df_original[customer_mask][customer_id_col].unique()
                                selected_customer_ids.extend([str(cid) for cid in customer_ids if str(cid) != ''])
                            st.session_state.split_customers = list(set(selected_customer_ids))  # Remove duplicates
                        else:
                            st.session_state.split_customers = selected_customers
                    else:
                        st.warning("⚠️ No customers selected - split numbering will not be applied")
                        st.session_state.split_customers = []
                else:
                    st.error("No valid customer data found in the data")
                    st.session_state.split_customers = []
            
            if st.button("Transform Data", type="primary"):
                if not all([talent_col, hours_col, date_col, customer_id_col, invoice_col]):
                    st.error("Please map all required columns")
                    return
                
                with st.spinner("Transforming data..."):
                    # Create mapping for Metabase to Usage format
                    column_mapping = {
                        talent_col: 'event_type_name',      # Talent → Event_type_name
                        hours_col: 'value',                 # sum(hours) → Value
                        date_col: 'datetime',               # last_worklog_date → Datetime
                        customer_id_col: 'customer_id',     # tabs_customer_id → Customer_id
                        invoice_col: 'invoice'              # purchaseOrder → Invoice
                    }
                    
                    # Transform the data
                    df_transformed = df_original.copy()
                    
                    # Rename columns
                    df_transformed = df_transformed.rename(columns=column_mapping)
                    
                    # Add company name if selected
                    if company_col:
                        df_transformed = df_transformed.rename(columns={company_col: 'company_name'})
                    
                    # Clean and format data
                    df_transformed['datetime'] = pd.to_datetime(df_transformed['datetime'], errors='coerce').dt.strftime('%-m/%-d/%Y')
                    df_transformed['value'] = pd.to_numeric(df_transformed['value'], errors='coerce').fillna(0)
                    
                    # Handle step-up pricing if enabled
                    if enable_stepup_pricing and 'event_type_name' in df_transformed.columns:
                        # Use dynamic pricing if available, otherwise fallback to hardcoded
                        # Step-up pricing now uses dynamic API data only
                        
                        # Apply step-up pricing using dynamic API data
                        stepup_count = 0
                        
                        # Check if we have dynamic step-up data from API
                        if 'dynamic_stepup_data' in st.session_state and st.session_state.dynamic_stepup_data is not None:
                            stepup_df = st.session_state.dynamic_stepup_data
                            
                            
                            # Check for different possible contract ID column names
                            contract_id_col = None
                            for col in ['contractId', 'contract_id', 'id']:
                                if col in stepup_df.columns:
                                    contract_id_col = col
                                    break
                            
                            # Use contracts API to map contract IDs to customer IDs
                            st.info("🔍 **Fetching customer IDs from contracts API**")
                            
                            # Create contract ID to customer ID mapping using the contracts API
                            contract_to_customer = {}
                            
                            if contract_id_col:
                                # Define headers for the contracts API calls - use EXACT same method as obligations API
                                # Use the same api_token that was passed to this function (same as obligations API)
                                # api_token is already available from the function parameter
                                
                                # Use the exact same headers that work for obligations API
                                headers = {
                                    'Authorization': api_token,  # Direct API key (not Bearer token) - SAME AS OBLIGATIONS
                                    'Content-Type': 'application/json',
                                    'Accept': 'application/json'
                                }
                                
                                # Get unique contract IDs and process them
                                unique_contracts = stepup_df[contract_id_col].dropna().unique()
                                
                                # Track success/failure counts
                                success_count = 0
                                access_denied_count = 0
                                not_found_count = 0
                                other_error_count = 0
                                
                                for i, contract_id in enumerate(unique_contracts):
                                    if pd.notna(contract_id) and contract_id:
                                        try:
                                            # Add a small delay to avoid rate limiting
                                            if i > 0:
                                                import time
                                                time.sleep(0.1)  # 100ms delay between requests
                                            
                                            # Use the exact same approach as obligations API
                                            contract_url = f"https://integrators.prod.api.tabsplatform.com/v3/contracts/{contract_id}"
                                            contract_response = requests.get(contract_url, headers=headers, timeout=30)
                                            
                                            if contract_response.status_code == 200:
                                                contract_data = contract_response.json()
                                                if contract_data.get('success') and 'payload' in contract_data:
                                                    customer_id = contract_data['payload'].get('customerId')
                                                    if customer_id:
                                                        contract_to_customer[contract_id] = customer_id
                                                        st.write(f"✅ Contract {contract_id} → Customer {customer_id}")
                                                        success_count += 1
                                                    else:
                                                        st.warning(f"⚠️ No customerId in contract {contract_id}")
                                                        other_error_count += 1
                                                else:
                                                    st.warning(f"⚠️ Invalid response format for contract {contract_id}")
                                                    other_error_count += 1
                                            elif contract_response.status_code == 401:
                                                st.warning(f"🔒 Access denied for contract {contract_id} (401) - may not have permission")
                                                access_denied_count += 1
                                            elif contract_response.status_code == 404:
                                                st.warning(f"❌ Contract {contract_id} not found (404)")
                                                not_found_count += 1
                                            else:
                                                st.warning(f"⚠️ Failed to fetch contract {contract_id}: {contract_response.status_code} - {contract_response.text[:100]}")
                                                other_error_count += 1
                                        except Exception as e:
                                            st.warning(f"❌ Error fetching contract {contract_id}: {str(e)}")
                                
                                if len(contract_to_customer) == 0:
                                    st.error("❌ **No contracts could be mapped to customer IDs** - API key doesn't have permission to access contract details.")
                            else:
                                st.warning("No contract ID column found in step-up data")
                            
                            for _, row in stepup_df.iterrows():
                                lawyer_name = row['billingSchedule_name']
                                api_pricing_amount = row['billingSchedule_pricing_0_amount']
                                contract_id = row.get(contract_id_col) if contract_id_col else None
                                
                                # Extract the base name and suffix from the API data
                                if ' - ' in lawyer_name:
                                    base_name = lawyer_name.split(' - ')[0]
                                    suffix = ' - ' + lawyer_name.split(' - ')[1]
                                else:
                                    base_name = lawyer_name
                                    suffix = ''
                                
                                # Get the customer ID from the contract mapping
                                expected_customer_id = contract_to_customer.get(contract_id) if contract_id else None
                                
                                # Skip if no expected customer ID
                                if not expected_customer_id:
                                    continue
                                
                                # Skip if customer_id column doesn't exist
                                if 'customer_id' not in df_transformed.columns:
                                    continue
                                
                                # Find rows where the event_type_name exactly matches the base lawyer name (case-insensitive)
                                # and doesn't already have a suffix (to avoid double-processing)
                                lawyer_mask = (df_transformed['event_type_name'].str.lower() == base_name.lower()) & (~df_transformed['event_type_name'].str.contains(' - ', na=False))
                                
                                # Also try partial matching for names that might have slight variations
                                if not lawyer_mask.any():
                                    # Try to find names that contain the base name
                                    partial_mask = df_transformed['event_type_name'].str.contains(base_name, case=False, na=False) & (~df_transformed['event_type_name'].str.contains(' - ', na=False))
                                    if partial_mask.any():
                                        lawyer_mask = partial_mask
                                    else:
                                        # Try even more flexible matching - remove special characters
                                        import re
                                        base_name_clean = re.sub(r'[^\w\s]', '', base_name).lower()
                                        flexible_mask = df_transformed['event_type_name'].str.replace(r'[^\w\s]', '', regex=True).str.lower().str.contains(base_name_clean, na=False) & (~df_transformed['event_type_name'].str.contains(' - ', na=False))
                                        if flexible_mask.any():
                                            lawyer_mask = flexible_mask
                                
                                if lawyer_mask.any():
                                    # Require customer ID matching using the contract-to-customer mapping
                                    customer_mask = df_transformed['customer_id'] == expected_customer_id
                                    lawyer_mask = lawyer_mask & customer_mask
                                    
                                    # Check if we have a Rate column to match against (this is the rate/amount from Metabase)
                                    if 'Rate' in df_transformed.columns:
                                        # Only apply suffix if the Rate matches the API pricing amount
                                        rate_mask = df_transformed['Rate'] == api_pricing_amount
                                        final_mask = lawyer_mask & rate_mask
                                    else:
                                        # If no Rate column, just use the lawyer_mask
                                        final_mask = lawyer_mask
                                    
                                    if final_mask.any():
                                        # Update ONLY those rows that match name, contract ID, AND rate
                                        df_transformed.loc[final_mask, 'event_type_name'] = df_transformed.loc[final_mask, 'event_type_name'] + suffix
                                        stepup_count += final_mask.sum()
                        
                        if stepup_count > 0:
                            st.info(f"✅ Step-up pricing applied to {stepup_count} records")
                    else:
                        st.info("ℹ️ No dynamic step-up pricing data available. Please fetch step-up pricing data first.")
                    
                    # Handle split invoices if enabled
                    if enable_split_invoices and 'invoice' in df_transformed.columns:
                        split_customers = st.session_state.get('split_customers', [])
                        
                        if split_customers:
                            # First, clear all invoice values (disregard PO numbers)
                            df_transformed['invoice'] = ''
                            
                            # Apply split numbering to selected customers
                            for customer_id in split_customers:
                                # Get all rows for this customer
                                customer_mask = df_transformed['customer_id'] == customer_id
                                customer_data = df_transformed[customer_mask]
                                
                                if len(customer_data) > 0:
                                    # Get all row indices for this customer (don't group by date)
                                    customer_indices = customer_data.index.tolist()
                                    
                                    # Apply numbering: blank, 1, 2, 3... for all rows of this customer
                                    for i, idx in enumerate(customer_indices):
                                        if i == 0:
                                            df_transformed.loc[idx, 'invoice'] = ''  # First row blank
                                        else:
                                            df_transformed.loc[idx, 'invoice'] = str(i)  # Subsequent rows: 1, 2, 3...
                        else:
                            # No customers selected, just clear invoice column
                            df_transformed['invoice'] = ''
                            st.info("ℹ️ Invoice column cleared (no customers selected for split numbering)")
                    else:
                        # Split invoices not enabled, just clear invoice column
                        if 'invoice' in df_transformed.columns:
                            df_transformed['invoice'] = ''
                            st.info("ℹ️ Invoice column cleared (PO numbers disregarded)")
                    
                    # Ensure required columns exist
                    required_columns = ['event_type_name', 'value', 'datetime', 'customer_id', 'invoice']
                    for col in required_columns:
                        if col not in df_transformed.columns:
                            df_transformed[col] = ''
                    
                    # Check for missing customer_id before processing
                    missing_customer_ids = df_transformed['customer_id'].isna() | (df_transformed['customer_id'] == '')
                    missing_count = missing_customer_ids.sum()
                    
                    if missing_count > 0:
                        st.warning(f"⚠️ **Warning:** {missing_count} rows have missing customer_id values. These rows will be removed from the final output.")
                        
                        # Show rows with missing customer_id for review
                        st.subheader("Rows with Missing Customer ID")
                        missing_rows = df_transformed[missing_customer_ids]
                        st.dataframe(missing_rows, use_container_width=True, hide_index=True)
                    
                    # Remove any rows with missing critical data
                    df_transformed = df_transformed.dropna(subset=['customer_id', 'event_type_name'])
                    df_transformed = df_transformed[df_transformed['customer_id'] != '']
                    
                    # Keep only the required columns for usage upload
                    df_transformed = df_transformed[required_columns]
                    
                    # Store in session state for download
                    st.session_state.transformed_data = df_transformed
                    
                    if missing_count == 0:
                        st.success("Data transformed successfully!")
                    else:
                        st.success(f"Data transformed successfully! Removed {missing_count} rows with missing customer_id.")
                    
                    # Show transformed data
                    st.subheader("Transformed Data Preview")
                    
                    # Add custom CSS for dataframe headers
                    st.markdown("""
                    <style>
                    .stDataFrame thead th {
                        font-family: 'Helvetica Neue', Arial, sans-serif !important;
                        font-size: 8px !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    st.dataframe(df_transformed, use_container_width=True, hide_index=True)
                    
                    # Download button
                    csv_str = df_transformed.to_csv(index=False)
                    st.download_button(
                        label="Download Transformed CSV",
                        data=csv_str,
                        file_name=f"usage_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                    
        except Exception as e:
            st.error(f"Error processing CSV: {e}")


def run_qa_comparison(usage_df, tabs_df, tabs_source_name="Tabs Data"):
    """Run QA comparison between usage and tabs data"""
    try:
        with st.spinner("Running QA comparison..."):
            # Auto-detect column mappings for usage data
            def auto_detect_usage_columns(df):
                columns = df.columns.tolist()
                customer_id = next((col for col in columns if 'customer' in col.lower() and 'id' in col.lower()), columns[0])
                event_type = next((col for col in columns if 'event' in col.lower() and 'type' in col.lower()), columns[0])
                invoice = next((col for col in columns if 'invoice' in col.lower() and 'id' not in col.lower()), columns[0])
                differentiator = next((col for col in columns if 'differentiator' in col.lower() or 'note' in col.lower()), columns[0])
                value = next((col for col in columns if 'value' in col.lower() or 'quantity' in col.lower()), columns[0])
                return customer_id, event_type, invoice, differentiator, value
            
            # Auto-detect column mappings for tabs data
            def auto_detect_tabs_columns(df):
                columns = df.columns.tolist()
                customer_id = next((col for col in columns if 'customer' in col.lower() and 'id' in col.lower()), columns[0])
                name = next((col for col in columns if 'name' in col.lower() and 'file' not in col.lower()), columns[0])
                invoice = next((col for col in columns if 'invoice' in col.lower() and 'id' not in col.lower()), columns[0])
                note = next((col for col in columns if 'note' in col.lower()), columns[0])
                quantity = next((col for col in columns if 'quantity' in col.lower()), columns[0])
                return customer_id, name, invoice, note, quantity
            
            # Get column mappings
            usage_customer_id, usage_event_type, usage_invoice, usage_differentiator, usage_value = auto_detect_usage_columns(usage_df)
            tabs_customer_id, tabs_name, tabs_invoice, tabs_note, tabs_quantity = auto_detect_tabs_columns(tabs_df)
            
            # Rename columns for consistency
            usagedf_clean = usage_df.copy()
            tabsdf_clean = tabs_df.copy()
            
            # Rename usage columns
            usagedf_clean = usagedf_clean.rename(columns={
                usage_customer_id: 'customer_id',
                usage_event_type: 'event_type_name',
                usage_invoice: 'invoice',
                usage_differentiator: 'differentiator',
                usage_value: 'value'
            })
            
            # Rename tabs columns
            tabsdf_clean = tabsdf_clean.rename(columns={
                tabs_customer_id: 'customer_id',
                tabs_name: 'name',
                tabs_invoice: 'invoice_number',
                tabs_note: 'note',
                tabs_quantity: 'quantity'
            })
            
            # Add missing columns if they don't exist
            if 'invoiceid' not in tabsdf_clean.columns:
                tabsdf_clean['invoiceid'] = 'unknown'
            
            if 'file_name' not in tabsdf_clean.columns:
                tabsdf_clean['file_name'] = tabs_source_name
            
            # Fill missing values
            usagedf_clean = usagedf_clean.fillna({"invoice": "<missing>", "differentiator": "<missing>"})
            tabsdf_clean = tabsdf_clean.fillna({"invoice_number": "<missing>", "note": "<missing>"})
            
            # Fix invoice formatting
            tabsdf_clean['invoice_number'] = tabsdf_clean['invoice_number'].astype(str)
            tabsdf_clean['invoice'] = tabsdf_clean['invoice_number'].apply(lambda x: x.split('-')[-1] if '-' in x else '<missing>')
            usagedf_clean['invoice'] = usagedf_clean['invoice'].astype(str).str.replace(r'\.0$', '', regex=True)
            
            # Aggregate data
            usagedf_clean = usagedf_clean.groupby(["customer_id", "event_type_name", "invoice", "differentiator"]).agg({"value": "sum"}).reset_index()
            tabsdf_clean = tabsdf_clean.groupby(["customer_id", "name", "note", "invoiceid", "invoice_number", "file_name"]).agg({"quantity": "sum"}).reset_index()
            
            # Re-create the invoice column after aggregation
            tabsdf_clean['invoice'] = tabsdf_clean['invoice_number'].apply(lambda x: x.split('-')[-1] if '-' in x else '<missing>')
            
            # Clean columns
            for col in ["name", "note", "invoice_number", "customer_id", "file_name"]:
                if col in tabsdf_clean.columns:
                    tabsdf_clean[col] = tabsdf_clean[col].astype(str).str.strip().str.replace(',', '', regex=False)
                    tabsdf_clean[col] = tabsdf_clean[col].astype(str).str.strip()
            
            for col in ["event_type_name", "invoice", "differentiator"]:
                if col in usagedf_clean.columns:
                    usagedf_clean[col] = usagedf_clean[col].astype(str).str.strip().str.replace(',', '', regex=False)
            
            # Create join keys
            usagedf_clean["join_key"] = (
                usagedf_clean["customer_id"].astype(str).str.strip().str.lower() + "|" +
                usagedf_clean["event_type_name"].astype(str).str.strip().str.lower() + "|" +
                usagedf_clean["invoice"].astype(str).str.strip().str.lower() + "|" +
                usagedf_clean["differentiator"].astype(str).str.strip().str.lower()
            )
            
            tabsdf_clean["join_key"] = (
                tabsdf_clean["customer_id"].astype(str).str.strip().str.lower() + "|" +
                tabsdf_clean["name"].astype(str).str.strip().str.lower() + "|" +
                tabsdf_clean["invoice"].astype(str).str.strip().str.lower() + "|" +
                tabsdf_clean["note"].astype(str).str.strip().str.lower()
            )
            
            # Merge
            merged = pd.merge(usagedf_clean, tabsdf_clean, on="join_key", how="outer", suffixes=("_usage", "_tabs"))
            
            # Classify mismatches
            def classify_mismatch(row):
                if pd.isna(row.get("value")):
                    return "Key not found in usage"
                elif pd.isna(row.get("quantity")):
                    return "Key not found in tabs"
                elif row.get("value", 0) != row.get("quantity", 0):
                    return f"Quantity mismatch (usage={row.get('value', 0)}, tabs={row.get('quantity', 0)})"
                else:
                    return ""
            
            merged["mismatch_reason"] = merged.apply(classify_mismatch, axis=1)
            
            # Filter mismatches
            mismatches = merged[merged["mismatch_reason"] != ""]
            
            # Keep only the most relevant columns
            if len(mismatches) > 0:
                display_cols = [
                    "customer_id_usage", "customer_id_tabs",
                    "invoice_usage", "invoice_tabs", 
                    "value", "quantity",
                    "mismatch_reason", "file_name"
                ]
                mismatches_display = mismatches[display_cols].copy()
            else:
                mismatches_display = mismatches
            
            # Display results
            st.subheader("QA Analysis Results")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", len(merged))
            with col2:
                st.metric("Mismatches Found", len(mismatches))
            with col3:
                mismatch_rate = (len(mismatches) / len(merged) * 100) if len(merged) > 0 else 0
                st.metric("Mismatch Rate", f"{mismatch_rate:.1f}%")
            
            if len(mismatches) > 0:
                st.subheader("Mismatches Details")
                st.markdown("**Note:** These are records where usage data doesn't match Tabs data or where records exist in one dataset but not the other.")
                st.dataframe(mismatches_display, use_container_width=True)
                
                # Download mismatches
                csv_str = mismatches_display.to_csv(index=False)
                st.download_button(
                    label="Download Mismatches CSV",
                    data=csv_str,
                    file_name=f"usage_qa_mismatches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
                # Show summary of mismatch types
                st.subheader("Mismatch Summary")
                col1, col2 = st.columns(2)
                
                with col1:
                    mismatch_summary = mismatches_display['mismatch_reason'].value_counts()
                    st.bar_chart(mismatch_summary)
                
                with col2:
                    st.write("**Mismatches by Source:**")
                    st.write(f"- {tabs_source_name}: {len(mismatches)} mismatches")
                
            else:
                st.success("🎉 No mismatches found! Usage data matches Tabs data perfectly.")
                
    except Exception as e:
        st.error(f"Error during QA comparison: {e}")

def show_pdf_workflow_tab():
    """Show PDF generation and upload workflow tab"""
    st.header("PDF Generation & Upload Workflow")
    st.markdown("Complete workflow for generating and uploading invoice PDFs")
    
    # Note about CSV source
    st.info("📝 **Note:** Upload Metabase weekly reports CSV file for PDF generation and invoice attachment.")
    
    
    
    # Initialize session state for workflow progress
    if 'workflow_progress' not in st.session_state:
        st.session_state.workflow_progress = {
            'csv_uploaded': False,
            'pdfs_generated': False,
            'csv_mapping_created': False,
            'ready_for_upload': False
        }
    
    # Initialize other session state variables
    if 'uploaded_csv' not in st.session_state:
        st.session_state.uploaded_csv = None
    if 'generated_pdfs' not in st.session_state:
        st.session_state.generated_pdfs = []
    if 'pdf_csv_data' not in st.session_state:
        st.session_state.pdf_csv_data = None
    if 'pdf_problematic_files' not in st.session_state:
        st.session_state.pdf_problematic_files = None
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 0  # Default to first tab
    
    # Add reset button if any steps are completed
    if any(st.session_state.workflow_progress.values()):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🔄 Reset Workflow", type="secondary", help="Clear all progress and start over"):
                # Reset all progress
                st.session_state.workflow_progress = {
                    'csv_uploaded': False,
                    'pdfs_generated': False,
                    'csv_mapping_created': False,
                    'ready_for_upload': False
                }
                # Clear session state data
                if 'uploaded_csv' in st.session_state:
                    del st.session_state.uploaded_csv
                if 'generated_pdfs' in st.session_state:
                    del st.session_state.generated_pdfs
                if 'pdf_csv_data' in st.session_state:
                    del st.session_state.pdf_csv_data
                st.success("🔄 Workflow reset successfully! Please refresh the page to see changes.")
    
    # Initialize current tab in session state
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = 0
    
    # Create tabs - all unlocked for free navigation
    tab_names = [
        "📁 Step 1: Upload CSV",
        "📄 Step 2: Generate PDFs", 
        "📋 Step 3: Create CSV Mapping",
        "🚀 Step 4: Bulk Upload"
    ]
    
    # Tab selector to maintain state
    selected_tab = st.radio(
        "Select Step:",
        options=tab_names,
        index=st.session_state.current_tab,
        horizontal=True,
        key="tab_selector"
    )
    
    # Update current tab in session state
    st.session_state.current_tab = tab_names.index(selected_tab)
    
    # Show content based on selected tab
    if st.session_state.current_tab == 0:
        st.subheader("Upload CSV Data")
        if 'uploaded_csv' not in st.session_state or st.session_state.uploaded_csv is None:
            uploaded_file = st.file_uploader(
                "Choose a CSV file",
                type=['csv'],
                help="Upload the Metabase weekly reports CSV file"
            )
            
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.session_state.uploaded_csv = df
                    st.success(f"✅ CSV uploaded successfully! {len(df)} rows loaded.")
                    
                    # Show preview
                    st.subheader("Data Preview")
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    # Show column info
                    st.subheader("Column Information")
                    col_info = pd.DataFrame({
                        'Column': df.columns.tolist(),
                        'Type': df.dtypes.astype(str).tolist(),
                        'Non-Null Count': df.count().tolist(),
                        'Sample Value': df.iloc[0].astype(str).tolist() if len(df) > 0 else ['N/A'] * len(df.columns)
                    })
                    st.dataframe(col_info, use_container_width=True)
                    
                    # Show next step instructions
                    st.markdown("---")
                    st.success("🎉 **Step 1 Complete!**")
                    st.info("👉 **Next:** Click on '📄 Step 2: Generate PDFs' tab above to proceed with PDF generation.")
                        
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")
        else:
            # CSV is already uploaded
            df = st.session_state.get('uploaded_csv')
            if df is not None:
                st.success(f"✅ CSV uploaded: {len(df)} rows loaded")
                st.info("✅ Step 1 Complete! You can now proceed to Step 2 to generate PDFs.")
            else:
                st.error("CSV data is missing. Please upload a CSV file.")
    
    elif st.session_state.current_tab == 1:
        st.subheader("Generate PDFs")
        
        # Step 2 is now freely accessible
        
        # Check if CSV is uploaded
        df = st.session_state.get('uploaded_csv')
        if df is None:
            st.warning("⚠️ Please upload a CSV file in Step 1 first.")
            return
        
        st.success(f"✅ CSV ready: {len(df)} rows loaded")
        
        # Configuration options
        report_type = st.selectbox(
            "Report Type",
            ["Monthly", "SemiMonthly", "Upfront"],
            help="Select the type of report to generate"
        )
        
        # Split customers configuration
        st.subheader("Split Customers Configuration")
        col1, col2 = st.columns(2)
        with col1:
            enable_split = st.checkbox(
                "Enable Split Invoices by Talent",
                help="Generate separate PDFs for each talent within companies that need split invoices"
            )
        with col2:
            if enable_split:
                split_customers = st.text_area(
                    "Split Customer Names (one per line)",
                    placeholder="CompanyA\nCompanyB\nCompanyC",
                    help="Enter company names that need split invoices by talent. One name per line."
                )
        
        # Clean and expand data
        if st.button("Process Data & Generate PDFs", type="primary"):
            with st.spinner("Processing data and generating PDFs..."):
                try:
                    # Validate required columns exist
                    required_columns = ["date", "Staffer_Name", "Company_Name", "tabs_customer_id", "Hours", "Company_Total_No_Currency ($)", "description"]
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    
                    if missing_columns:
                        st.error(f"Missing required columns: {missing_columns}")
                        st.error(f"Available columns: {list(df.columns)}")
                        return
                    
                    # Check for empty or invalid data in critical columns
                    if df["date"].isna().any():
                        st.error("Found rows with missing dates. Please check your CSV data.")
                        st.dataframe(df[df["date"].isna()])
                        return
                    
                    # Clean currency column
                    if "Company_Total_No_Currency ($)" in df.columns:
                        df["Company_Total_No_Currency ($)"] = (
                            df["Company_Total_No_Currency ($)"]
                            .astype(str)
                            .str.replace("$", "", regex=False)
                            .str.replace(",", "", regex=False)
                            .astype(float)
                        )
                    
                    # Expand rows
                    expanded_rows = []
                    for _, row in df.iterrows():
                        try:
                            # Check if required columns exist
                            if "date" not in row or pd.isna(row["date"]):
                                st.error(f"Missing or invalid date in row: {row}")
                                continue
                            
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
                        except Exception as e:
                            st.error(f"Error processing row: {e}")
                            st.error(f"Row data: {dict(row)}")
                            continue

                    df_expanded = pd.DataFrame(expanded_rows)
                    
                    # Generate PDFs
                    pdf_info_list = []
                    temp_dir = tempfile.mkdtemp()
                    
                    # Parse split customers list
                    split_customer_list = []
                    if enable_split and split_customers:
                        split_customer_list = [name.strip() for name in split_customers.split('\n') if name.strip()]
                    
                    for company, group_df in df_expanded.groupby("Company_Name"):
                        customer_id = group_df["tabs_customer_id"].iloc[0]
                        month_str = pd.to_datetime(group_df["date"]).min().strftime("%B")
                        
                        # Check if this company needs split invoices
                        if enable_split and company in split_customer_list:
                            # Generate separate PDFs for each talent
                            for talent, talent_df in group_df.groupby("Staffer_Name"):
                                # Create filename with talent name
                                talent_name_clean = talent.replace(' ', '').replace(',', '').replace('.', '')
                                filename = f"{company.replace(' ', '')}_{talent_name_clean}_hoursReport_{month_str}_{customer_id}.pdf"
                                path = os.path.join(temp_dir, filename)

                                with warnings.catch_warnings():
                                    warnings.simplefilter("ignore")
                                    pdf = LawtradesPDF(company)
                                pdf.add_talent_section(talent)
                                total_hours = talent_df["Hours"].sum()
                                total_amount = talent_df["Company_Total_No_Currency ($)"].sum()
                                
                                for _, row in talent_df.iterrows():
                                    pdf.add_row(row)
                                pdf.add_totals(total_hours, total_amount)

                                with warnings.catch_warnings():
                                    warnings.simplefilter("ignore")
                                    pdf.output(path)
                                
                                # Store detailed PDF info
                                pdf_info_list.append({
                                    "path": path,
                                    "filename": filename,
                                    "company": company,
                                    "invoice_id": None,  # Will be looked up during CSV generation
                                    "talent_name": talent
                                })
                        else:
                            # Generate single PDF for the entire company
                            filename = f"{company.replace(' ', '')}_hoursReport_{month_str}_{customer_id}.pdf"
                            path = os.path.join(temp_dir, filename)

                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                pdf = LawtradesPDF(company)
                            for talent, rows in group_df.groupby("Staffer_Name"):
                                pdf.add_talent_section(talent)
                                total_hours = rows["Hours"].sum()
                                total_amount = rows["Company_Total_No_Currency ($)"].sum()
                                for _, row in rows.iterrows():
                                    pdf.add_row(row)
                                pdf.add_totals(total_hours, total_amount)

                            with warnings.catch_warnings():
                                warnings.simplefilter("ignore")
                                pdf.output(path)
                            
                            # Store detailed PDF info
                            pdf_info_list.append({
                                "path": path,
                                "filename": filename,
                                "company": company,
                                "invoice_id": None,  # Will be looked up during CSV generation
                                "talent_name": ""  # No talent splitting for regular PDFs
                            })
                    
                    st.session_state.generated_pdfs = pdf_info_list
                    st.session_state.workflow_progress['pdfs_generated'] = True
                    st.success(f"✅ Generated {len(pdf_info_list)} PDF files!")
                    st.info("✅ Step 2 Complete! You can now proceed to Step 3 to create CSV mapping.")
                    
                    # Show generated files
                    st.subheader("Generated Files")
                    for i, pdf_info in enumerate(pdf_info_list):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"{i+1}. {pdf_info['filename']}")
                        with col2:
                            # Add view PDF button
                            if os.path.exists(pdf_info['path']):
                                with open(pdf_info['path'], "rb") as pdf_file:
                                    pdf_bytes = pdf_file.read()
                                    st.download_button(
                                        "View PDF",
                                        data=pdf_bytes,
                                        file_name=pdf_info['filename'],
                                        mime="application/pdf",
                                        key=f"view_pdf_{i}"
                                    )
                    
                    # Show next step instructions
                    st.markdown("---")
                    st.success("🎉 **Step 2 Complete!**")
                    st.info("👉 **Next:** Click on '📋 Step 3: Create CSV Mapping' tab above to proceed with CSV generation.")
                    
                    # Step 3 will unlock automatically on next page interaction
                    
                    
                except Exception as e:
                    st.error(f"Error generating PDFs: {e}")
    
    elif st.session_state.current_tab == 2:
        st.subheader("Create PDF Mapping CSV")
        
        # Show status if CSV generation is in progress
        if st.session_state.get('csv_generation_in_progress', False):
            st.warning("🔄 **CSV generation in progress...** Please wait while the system processes your files.")
        
        # Step 3 is now freely accessible
        
        # Check if PDFs are generated
        if 'generated_pdfs' not in st.session_state or not st.session_state.generated_pdfs:
            st.warning("⚠️ Please generate PDFs in Step 2 first.")
            return
        
        st.info("Generate CSV mapping with database or API lookup for invoice IDs")
        
        # Simple API/Database toggle
        st.subheader("Invoice Lookup Method")
        
        use_api = st.checkbox(
            "🌐 Use API for Invoice Lookup", 
            help="Check to use API, uncheck to use database (original method)",
            value=st.session_state.get('use_api_lookup', False)
        )
        
        # Store the choice in session state
        st.session_state.use_api_lookup = use_api
        
        if use_api:
            st.info("🌐 Using API for invoice lookup")
            
            # Only show API key input when using API
            st.subheader("🔑 API Configuration")
            api_key_input = st.text_input(
                "API Key",
                type="password",
                help="Enter your TABS API key for invoice lookup",
                value=st.session_state.get('api_key', ''),
                key="csv_mapping_api_key"
            )
            
            # Store API key in session state
            if api_key_input:
                st.session_state.api_key = api_key_input
            
            if not api_key_input:
                st.warning("⚠️ Please enter your API key to proceed with API lookup")
                return
            
            # Smart caching system for API invoices
            st.subheader("📋 Invoice Cache Management")
            
            # Check if we have cached invoices (with better persistence)
            cache_key = f"invoice_cache_{api_key_input[:10]}"
            
            # Try to get from session state first
            cached_invoices = st.session_state.get(cache_key, [])
            cache_timestamp = st.session_state.get(f"{cache_key}_timestamp", None)
            
            # If no cache in session state, try to load from file
            if not cached_invoices:
                try:
                    import json
                    cache_file = f"invoice_cache_{api_key_input[:10]}.json"
                    if os.path.exists(cache_file):
                        with open(cache_file, 'r') as f:
                            cache_data = json.load(f)
                            cached_invoices = cache_data.get('invoices', [])
                            cache_timestamp_str = cache_data.get('timestamp')
                            if cache_timestamp_str:
                                cache_timestamp = datetime.fromisoformat(cache_timestamp_str)
                        
                        # Restore to session state
                        st.session_state[cache_key] = cached_invoices
                        st.session_state[f"{cache_key}_timestamp"] = cache_timestamp
                        st.success(f"✅ Loaded {len(cached_invoices)} invoices from persistent cache")
                except Exception as e:
                    st.warning(f"Could not load persistent cache: {e}")
                    cached_invoices = []
                    cache_timestamp = None
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                if cached_invoices:
                    cache_age = datetime.now() - cache_timestamp if cache_timestamp else None
                    if cache_age:
                        age_hours = cache_age.total_seconds() / 3600
                        st.success(f"✅ Cache: {len(cached_invoices)} invoices cached ({age_hours:.1f} hours ago)")
                    else:
                        st.success(f"✅ Cache: {len(cached_invoices)} invoices cached")
                else:
                    st.warning("⚠️ No invoice cache found")
                    st.info("💡 Click 'Refresh Cache' to fetch all invoices from API (one-time setup)")
            
            with col2:
                if st.button("🔄 Refresh Cache", help="Fetch fresh invoices from API"):
                    with st.spinner("Fetching all invoices from API (this may take a few minutes)..."):
                        all_invoices = fetch_all_invoices_for_cache(api_key_input)
                        if all_invoices:
                            # Save to session state
                            st.session_state[cache_key] = all_invoices
                            st.session_state[f"{cache_key}_timestamp"] = datetime.now()
                            
                            # Also save to file for persistence
                            try:
                                import json
                                cache_file = f"invoice_cache_{api_key_input[:10]}.json"
                                cache_data = {
                                    'invoices': all_invoices,
                                    'timestamp': datetime.now().isoformat(),
                                    'count': len(all_invoices)
                                }
                                with open(cache_file, 'w') as f:
                                    json.dump(cache_data, f)
                                st.success(f"✅ Cached {len(all_invoices)} invoices successfully! (Saved to file)")
                            except Exception as e:
                                st.success(f"✅ Cached {len(all_invoices)} invoices successfully! (File save failed: {e})")
                            
                            st.rerun()
                        else:
                            st.error("❌ Failed to fetch invoices")
            
            with col3:
                if st.button("🗑️ Clear Cache", help="Clear cached invoices"):
                    # Clear from session state
                    if cache_key in st.session_state:
                        del st.session_state[cache_key]
                    if f"{cache_key}_timestamp" in st.session_state:
                        del st.session_state[f"{cache_key}_timestamp"]
                    
                    # Also clear from file
                    try:
                        cache_file = f"invoice_cache_{api_key_input[:10]}.json"
                        if os.path.exists(cache_file):
                            os.remove(cache_file)
                        st.success("✅ Cache cleared! (Both memory and file)")
                    except Exception as e:
                        st.success(f"✅ Cache cleared! (File removal failed: {e})")
                    
                    st.rerun()
            
            # Show cache recommendations
            if cached_invoices and cache_timestamp:
                cache_age = datetime.now() - cache_timestamp
                age_hours = cache_age.total_seconds() / 3600
                if age_hours > 24:
                    st.warning("⚠️ Cache is older than 24 hours. Consider refreshing for new invoices.")
                elif age_hours > 6:
                    st.info("ℹ️ Cache is older than 6 hours. New invoices may not be included.")
                else:
                    st.info("✅ Cache is fresh and up-to-date.")
        else:
            st.info("Using database for invoice lookup")
            # Set empty API key when not using API
            api_key_input = ""
        
        # Date picker for issue date
        st.subheader("📅 Invoice Issue Date")
        
        # Store the default date in session state to persist across tab switches
        if 'selected_issue_date' not in st.session_state:
            st.session_state.selected_issue_date = datetime.now().replace(day=1).date()
        
        issue_date = st.date_input(
            "Select the issue date for invoice lookup:",
            value=st.session_state.selected_issue_date,
            help="This date will be used to find matching invoices",
            key="invoice_date_picker"
        )
        
        # Update session state when date changes
        if issue_date != st.session_state.selected_issue_date:
            st.session_state.selected_issue_date = issue_date
        
        st.markdown("---")
        
        if st.button("Generate CSV Mapping", type="primary"):
            # Set flag to indicate CSV generation is in progress
            st.session_state.csv_generation_in_progress = True
            
            with st.spinner("Generating CSV mapping..."):
                try:
                    # Generate CSV mapping with database lookup
                    csv_data = []
                    problematic_files = []
                    st.info(f"Processing {len(st.session_state.generated_pdfs)} PDF files...")
                    
                    for i, pdf_info in enumerate(st.session_state.generated_pdfs, 1):
                        filename = pdf_info["filename"]
                        
                        # Extract company ID from filename (last part before .pdf)
                        company_id = extract_serial_code(filename)
                        st.write(f"📄 Processing {i}/{len(st.session_state.generated_pdfs)}: {filename}")
                        st.write(f"   Company ID: {company_id}")
                        
                        # Check if invoice exists in database (only if we have a valid company ID)
                        if company_id:
                            invoice_id = exists_invoice(company_id, None, issue_date)
                        else:
                            st.warning(f"   ⚠️ Cannot extract valid company ID from filename: {filename}")
                            invoice_id = None
                        
                        # Only add to CSV if we have a valid invoice ID
                        if invoice_id and invoice_id != "None" and str(invoice_id).strip():
                            csv_data.append({
                                "Manufacturer_id": "7af68809-96ba-4de9-a1a0-4be7b103a491",  # Fixed merchant ID
                                "Customer_id": company_id,  # Add customer ID for API calls
                                "Invoice_id": invoice_id,
                                "Company_name": pdf_info["company"],
                                "Filename": filename,
                                "Filepath": pdf_info["path"],
                                "Talent_name": pdf_info["talent_name"]
                            })
                            st.success(f"   ✅ Invoice ID: {invoice_id}")
                        else:
                            st.warning(f"   ⚠️ No valid invoice found for company {company_id} - skipping this PDF")
                            # Add to problematic files list
                            problematic_files.append({
                                "Filename": filename,
                                "Company": pdf_info["company"],
                                "Company_ID": company_id,
                                "Issue": "No invoice ID found" if company_id else "Invalid company ID",
                                "Filepath": pdf_info["path"],
                                "Talent_name": pdf_info["talent_name"]
                            })
                            st.error(f"   ❌ No invoice ID found")
                        
                        st.write("---")
                    
                    # Create main CSV with only successful mappings
                    df_csv = pd.DataFrame(csv_data)
                    st.session_state.pdf_csv_data = df_csv
                    
                    # Create problematic files DataFrame
                    df_problematic = pd.DataFrame(problematic_files)
                    st.session_state.pdf_problematic_files = df_problematic
                    
                    st.session_state.workflow_progress['csv_mapping_created'] = True
                    
                    # Clear the in-progress flag
                    st.session_state.csv_generation_in_progress = False
                    
                    # Show results summary
                    st.success(f"✅ **CSV mapping completed!**")
                    st.info(f"📊 **Results:** {len(df_csv)} files successfully mapped, {len(problematic_files)} files need attention")
                    
                    
                except Exception as e:
                    st.error(f"Error generating CSV mapping: {e}")
                    st.error("This might be due to API connection issues. Please check your API key and network connection.")
        
        # Display results if CSV mapping was created
        if 'pdf_csv_data' in st.session_state and st.session_state.pdf_csv_data is not None:
            st.markdown("---")
            st.subheader("📋 Generated CSV Mapping")
            
            df_csv = st.session_state.pdf_csv_data
            
            if len(df_csv) > 0:
                st.success(f"✅ **{len(df_csv)} files successfully mapped**")
                st.dataframe(df_csv, use_container_width=True)
                
                # Download button for successful mappings
                csv_bytes = df_csv.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download PDF Mapping CSV",
                    data=csv_bytes,
                    file_name="pdf_mapping_successful.csv",
                    mime="text/csv"
                )
            else:
                st.warning("⚠️ No files were successfully mapped")
        
        # Display problematic files if any
        if 'pdf_problematic_files' in st.session_state and st.session_state.pdf_problematic_files is not None:
            df_problematic = st.session_state.pdf_problematic_files
            
            if len(df_problematic) > 0:
                st.markdown("---")
                st.subheader("⚠️ Files Requiring Attention")
                st.warning(f"**{len(df_problematic)} files could not be mapped**")
                st.dataframe(df_problematic, use_container_width=True)
                
                # Download button for problematic files
                problematic_csv_bytes = df_problematic.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download Problematic Files CSV",
                    data=problematic_csv_bytes,
                    file_name="pdf_mapping_problematic.csv",
                    mime="text/csv"
                )
                
        
        # Show completion message if mapping was successful
        if st.session_state.workflow_progress.get('csv_mapping_created', False):
            st.markdown("---")
            st.success("🎉 **Step 3 Complete!**")
            st.info("👉 **Next:** Click on '📤 Step 4: Bulk Upload' tab above to proceed with PDF uploads.")
        
    
    elif st.session_state.current_tab == 3:
        st.subheader("Bulk Upload PDFs")
        
        # Step 4 is now freely accessible
        
        # Check if CSV mapping is ready
        if 'pdf_csv_data' not in st.session_state or st.session_state.pdf_csv_data is None:
            st.warning("⚠️ Please create CSV mapping in Step 3 first.")
            return
        
        st.info("Ready for bulk upload! Use the CSV mapping above to upload PDFs to invoices.")
        
        # API Configuration
        st.subheader("🔧 API Configuration")
        
        col1, col2 = st.columns(2)
        with col1:
            environment = st.selectbox(
                "Environment",
                ["Production", "Sandbox"],
                help="Select the environment to use"
            )
        with col2:
            timeout = st.number_input(
                "Request Timeout (seconds)",
                min_value=10,
                max_value=300,
                value=30
            )
        
        # Set merchant ID based on environment
        if environment == "Sandbox":
            merchant_id = "d90b1777-0ca5-45ca-99ee-70cf51eb314a"
        else:
            merchant_id = "7af68809-96ba-4de9-a1a0-4be7b103a491"
        
        col3, col4 = st.columns(2)
        with col3:
            api_key_input = st.text_input(
                "API Key",
                type="password",
                help="Enter your TABS API key",
                value=st.session_state.get('api_key', '')
            )
        with col4:
            st.text_input(
                "Merchant ID",
                value=merchant_id,
                disabled=True,
                help="Merchant ID (auto-set based on environment)"
            )
        
        # Store API key in session state
        if api_key_input:
            st.session_state.api_key = api_key_input
        
        if st.button("Start Bulk Upload", type="primary"):
            if not api_key_input:
                st.error("Please enter your API key")
                return
            
            with st.spinner("Uploading PDFs..."):
                df_upload = st.session_state.pdf_csv_data
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                success_count = 0
                error_count = 0
                
                for i, row in df_upload.iterrows():
                    try:
                        # Use the customer ID from CSV data (this is the actual company ID from filename)
                        customer_id = row["Customer_id"]
                        invoice_id = row["Invoice_id"]
                        filepath = row["Filepath"]
                        
                        # Show processing status
                        status_text.text(f"Processing {i + 1}/{len(df_upload)}: {row['Filename']}")
                        
                        if invoice_id and invoice_id != "unknown" and str(invoice_id).strip() and os.path.exists(filepath):
                            # Upload attachment
                            success = upload_attachment(customer_id, invoice_id, filepath, row.get("Talent_name", ""))
                            if success:
                                success_count += 1
                        else:
                            error_count += 1
                            st.warning(f"⚠️ Skipping: {row['Filename']}")
                        
                        # Update progress
                        progress = (i + 1) / len(df_upload)
                        progress_bar.progress(progress)
                        
                    except Exception as e:
                        error_count += 1
                        st.error(f"❌ Error: {row['Filename']}")
                
                progress_bar.empty()
                status_text.empty()
                
                if success_count > 0:
                    st.success(f"Successfully uploaded {success_count} PDFs!")
                if error_count > 0:
                    st.error(f"Failed to upload {error_count} PDFs")

# Main App
def main():
    # Sidebar for instructions
    with st.sidebar:
        st.header("📋 Instructions")
        st.markdown("""
        ### Workflow Steps:
        1. **Usage CSV Transformation**: Upload Metabase data to transform into Tabs usage data
        2. **PDF Workflow**: Generate individual PDF invoices and bulk upload to Tabs
        
        """)
        
        st.markdown("---")
        st.markdown("### 🔧 API Configuration")
        st.info("API key is required for step-up pricing and bulk PDF upload functionality.")
    
    # Main content
    st.title("Lawtrades Internal Tool")
    st.markdown("Tool for CSV transformation and PDF generation/bulk attachment")
    
    # Create main tabs
    tab1, tab2 = st.tabs(["Usage CSV Transformation", "PDF Workflow"])
    
    with tab1:
        show_csv_transformation_tab()
    
    with tab2:
        show_pdf_workflow_tab()

if __name__ == "__main__":
    main()

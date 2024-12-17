import os
import pandas as pd
from datetime import datetime

# Define the folder and file paths
input_folder = "11 2024 Billing Files - Copy"
idp_data_file = "IDP report Nov2024.csv"
all_customers_file = "all_customers.csv"
output_file = "output-dec2.csv"
date = "2024-11-30"

# Load all_customers.csv
all_customers_df = pd.read_csv(all_customers_file)

# Load IDP Data Report and calculate distinct clinicianid count per clientid
idp_df = pd.read_csv(idp_data_file)
idp_counts = idp_df.groupby("clientid")["clinicianid"].nunique().reset_index()
idp_counts.columns = ["clientid", "IDP"]

# Initialize an empty list to store results
output_data = []

# Iterate over each file in the "Oct 2024 Billing Files" folder
for filename in os.listdir(input_folder):
    if filename.endswith(".csv"):
        # Load each billing CSV file
        file_path = os.path.join(input_folder, filename)
        billing_df = pd.read_csv(file_path)

        # Skip empty files
        if billing_df.empty:
            print(f"Skipping empty file: {filename}")
            continue

        # Calculate RX sum
        rx_sum = billing_df["Number of Prescriptions"].sum()

        # Calculate EPCS count
        epcs_count = billing_df[
            (billing_df["Role"] == "PrescribingClinician") & 
            (billing_df["EPCS (enabled)"] == True)
        ].shape[0]

        # Calculate Non-EPCS count
        non_epcs_count = billing_df[
            (billing_df["Role"] == "PrescribingClinician") & 
            (billing_df["EPCS (enabled)"] == False)
        ].shape[0]

        # Calculate Agents count
        agents_count = billing_df[billing_df["Role"] == "PrescribingAgentClinician"].shape[0]

        # Deduction logic
        free_deduction = 0

        if non_epcs_count >= 10:
            non_epcs_deducted = 10
            non_epcs_count -= non_epcs_deducted
            free_deduction += non_epcs_deducted
        else:
            non_epcs_deducted = non_epcs_count
            free_deduction += non_epcs_deducted
            non_epcs_count = 0

            # Deduct the remaining amount from EPCS if Non-EPCS is less than 10
            epcs_deducted = min(10 - free_deduction, epcs_count)
            epcs_count -= epcs_deducted
            free_deduction += epcs_deducted

        # Free variable is the total of the actual deductions made
        free = free_deduction

        # Get Client ID from the first row of the current billing CSV
        client_id = billing_df.iloc[0]["Client ID"]

        # Find the matching Customer ID in all_customers.csv
        customer_row = all_customers_df[all_customers_df["Client ID"] == client_id]
        if not customer_row.empty:
            customer_id = customer_row.iloc[0]["Customer ID"]

            # Find the IDP count for this client_id, if it exists
            idp_count_row = idp_counts[idp_counts["clientid"] == client_id]
            idp_count = idp_count_row["IDP"].values[0] if not idp_count_row.empty else 0

            # Prepare data to write to output
            results = [
                {"customer_id": customer_id, "event_type_name": "Rx", "datetime": date, "value": rx_sum, "differentiator": None},
                {"customer_id": customer_id, "event_type_name": "EPCS", "datetime": date, "value": epcs_count, "differentiator": None},
                {"customer_id": customer_id, "event_type_name": "Non-EPCS", "datetime": date, "value": non_epcs_count, "differentiator": None},
                {"customer_id": customer_id, "event_type_name": "Agents", "datetime": date, "value": agents_count, "differentiator": None},
                {"customer_id": customer_id, "event_type_name": "Free", "datetime": date, "value": free, "differentiator": None},
                {"customer_id": customer_id, "event_type_name": "IDP", "datetime": date, "value": idp_count, "differentiator": None}
            ]
            output_data.extend(results)

# Create a DataFrame from output_data
output_df = pd.DataFrame(output_data)

# Write output to output.csv
output_df.to_csv(output_file, index=False)
print(f"Data successfully written to {output_file}")

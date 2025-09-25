import pandas as pd

def load_file(file_path):
    return pd.read_csv(file_path)

def classify_mismatch(row):
    """
    Return a human-readable reason for mismatch.
    """
    if pd.isna(row.get("value")):
        return "Key not found in usage"
    elif pd.isna(row.get("quantity")):
        return "Key not found in tabs"
    elif row.get("value", 0) != row.get("quantity", 0):
        return f"Quantity mismatch (usage={row.get('value', 0)}, tabs={row.get('quantity', 0)})"
    else:
        return ""


def get_mismatch_columns(row, columns):
    """
    Compare *_usage and *_tabs columns for a row,
    return a pipe-separated string of column names that mismatch
    """
    mismatches = []
    for col in columns:
        if col.endswith('_usage'):
            base = col.replace('_usage', '')
            other = base + '_tabs'
            if other in columns:
                # Compare, treating NaN as 0
                val_usage = row[col] if pd.notna(row[col]) else 0
                val_tabs = row[other] if pd.notna(row[other]) else 0
                if val_usage != val_tabs:
                    mismatches.append(base)
    return '|'.join(mismatches) if mismatches else ''

def main():
    # Load files
    usagedf = load_file('/Users/colemankredich/Downloads/Revparts Batch 1 - ready 1.0.csv')
    tabsdf = load_file("/Users/colemankredich/Desktop/revparts.csv")

    # Fill missing values
    usagedf = usagedf.fillna({"invoice": "<missing>", "differentiator": "<missing>"})
    tabsdf = tabsdf.fillna({"invoice": "<missing>", "note": "<missing>"})

    # Aggregate data
    usagedf = usagedf.groupby(["customer_id", "event_type_name", "invoice", "differentiator"]).agg({"value": "sum"}).reset_index()
    tabsdf = tabsdf.groupby(["customer_id", "name", "note", "invoiceid", "invoice_number", "file_name"]).agg({"quantity": "sum"}).reset_index()

    # Fix invoice formatting
    tabsdf['invoice_number'] = tabsdf['invoice_number'].astype(str)
    tabsdf['invoice'] = tabsdf['invoice_number'].apply(lambda x: x.split('-')[-1] if '-' in x else '<missing>')
    usagedf['invoice'] = usagedf['invoice'].astype(str).str.replace(r'\.0$', '', regex=True)

    # Clean tabsdf columns used in join
    for col in ["name", "note", "invoice_number", "customer_id", "file_name"]:
        if col in tabsdf.columns:
            # Remove leading/trailing spaces and stray commas
            tabsdf[col] = tabsdf[col].astype(str).str.strip().str.replace(',', '', regex=False)
            tabsdf[col] = tabsdf[col].astype(str).str.strip()

    for col in ["event_type_name", "invoice", "differentiator"]:
        if col in usagedf.columns:
            usagedf[col] = usagedf[col].astype(str).str.strip().str.replace(',', '', regex=False)
            usagedf[col] = usagedf[col].astype(str).str.strip()


    # Create join keys
    usagedf["join_key"] = (
    usagedf["customer_id"].astype(str).str.strip().str.lower() + "|" +
    usagedf["event_type_name"].astype(str).str.strip().str.lower() + "|" +
    usagedf["invoice"].astype(str).str.strip().str.lower() + "|" +
    usagedf["differentiator"].astype(str).str.strip().str.lower()
)

    tabsdf["join_key"] = (
    tabsdf["customer_id"].astype(str).str.strip().str.lower() + "|" +
    tabsdf["name"].astype(str).str.strip().str.lower() + "|" +
    tabsdf["invoice"].astype(str).str.strip().str.lower() + "|" +
    tabsdf["note"].astype(str).str.strip().str.lower()
)

    # Merge
    merged = pd.merge(usagedf, tabsdf, on="join_key", how="outer", suffixes=("_usage", "_tabs"))

    # Compare values
    merged["mismatch_reason"] = merged.apply(classify_mismatch, axis=1)

    # Filter mismatches
    mismatches = merged[merged["mismatch_reason"] != ""]

    # Keep only the most relevant columns
    mismatches = mismatches[[
        "customer_id_usage", "customer_id_tabs",
        "invoice_usage", "invoice_tabs",
        "value", "quantity",
        "mismatch_reason", "file_name"

    ]]
    mismatches.to_csv("mismatches.csv", index=False)

    print(f"Total rows: {len(merged)}")
    print(f"Mismatches found: {len(mismatches)}")
    print("Sample mismatches:")
    print(mismatches)

if __name__ == "__main__":
    main()
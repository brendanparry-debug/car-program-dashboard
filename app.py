import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(page_title="Car Program Analytics Dashboard", layout="wide")
st.title("🚗 Automotive Finance & Lease Program Dashboard")
st.write("Upload your program files to calculate and compare dealer matrices on a single page.")

# --- Calculation Functions ---
def calculate_finance_payment(msrp, fin_discount, manual_discount, rate_pct, months):
    if months <= 0:
        return 0.0
    net_finance_amt = msrp - fin_discount - manual_discount
    if net_finance_amt <= 0:
        return 0.0
    
    monthly_rate = (rate_pct / 100) / 12
    if monthly_rate == 0:
        return net_finance_amt / months
    
    payment = net_finance_amt * (monthly_rate * (1 + monthly_rate) ** months) / (((1 + monthly_rate) ** months) - 1)
    return max(0.0, payment)

def calculate_lease_payment(msrp, lease_discount, manual_discount, rate_pct, residual_pct, months):
    if months <= 0:
        return 0.0
    
    net_cap_cost = msrp - lease_discount - manual_discount
    residual_value = msrp * (residual_pct / 100)
    
    if net_cap_cost <= residual_value:
        depreciation_charge = 0.0
    else:
        depreciation_charge = (net_cap_cost - residual_value) / months
        
    money_factor = (rate_pct / 100) / 24
    finance_charge = (net_cap_cost + residual_value) * money_factor
    
    total_lease_payment = depreciation_charge + finance_charge
    return max(0.0, total_lease_payment)

def find_column_by_keywords(columns, keywords):
    """Finds a column name that contains all the specified keywords (case-insensitive)"""
    for col in columns:
        col_lower = str(col).lower()
        if all(kw.lower() in col_lower for kw in keywords):
            return col
    return None

def clean_and_parse_file(uploaded_file):
    """Dynamically maps columns based on header text and applies safe type casting"""
    try:
        # Read the excel file normally to get headers
        df_raw = pd.read_excel(uploaded_file)
        
        # Clean up column names to prevent matching issues with spaces
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        cols = df_raw.columns
        
        # Define dynamic mapping rules using keywords
        mapping_rules = {
            'Car Model': (['model'], 'Model'),
            'Trim': (['trim'], 'Trim'),
            'MSRP': (['msrp'], 'MSRP'),
            'Cash Discount': (['cash', 'discount'], 'Cash Discount'),
            'Finance Discount': (['finance', 'discount'], 'Finance Discount'),
            'Lease Discount': (['lease', 'discount'], 'Lease Discount'),
            'Fin 24mo Rate': (['24', 'finance', 'rate'], '24 month finance rate'),
            'Fin 36mo Rate': (['36', 'finance', 'rate'], '36 month finance rate'),
            'Fin 48mo Rate': (['48', 'finance', 'rate'], '48 month finance rate'),
            'Fin 60mo Rate': (['60', 'finance', 'rate'], '60 month finance rate'),
            'Fin 72mo Rate': (['72', 'finance', 'rate'], '72 month finance rate'),
            'Fin 84mo Rate': (['84', 'finance', 'rate'], '84 month finance rate'),
            'Lease 36mo Rate': (['36', 'lease', 'rate'], '36 month lease rate'),
            'Lease 48mo Rate': (['48', 'lease', 'rate'], '48 month lease rate'),
            'Lease 60mo Rate': (['60', 'lease', 'rate'], '60 month lease rate'),
            'Lease 36mo Residual': (['36', 'lease', 'residual'], '36 month lease residual'),
            'Lease 48mo Residual': (['48', 'lease', 'residual'], '48 month lease residual'),
            'Lease 60mo Residual': (['60', 'lease', 'residual'], '60 month lease residual'),
        }
        
        df_cleaned = pd.DataFrame()
        missing_critical_cols = []
        
        # Build the new dataframe by looking up columns dynamically
        for standard_name, (keywords, fallback) in mapping_rules.items():
            matched_col = find_column_by_keywords(cols, keywords)
            if matched_col:
                df_cleaned[standard_name] = df_raw[matched_col]
            else:
                # If a rate or residual is missing entirely, we can safely fill it with zeros
                if 'Rate' in standard_name or 'Residual' in standard_name or 'Discount' in standard_name:
                    df_cleaned[standard_name] = 0.0
                else:
                    missing_critical_cols.append(fallback)
                    
        if missing_critical_cols:
            st.error(f"❌ Uploaded file is missing required headers: {', '.join(missing_critical_cols)}")
            return None
            
        # Data scrubbing (Clean up string and numeric types)
        df_cleaned['Car Model'] = df_cleaned['Car Model'].astype(str).str.strip()
        df_cleaned['Trim'] = df_cleaned['Trim'].astype(str).str.strip()
        
        numeric_cols = [col for col in df_cleaned.columns if col not in ['Car Model', 'Trim']]
        for col in numeric_cols:
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace('%', '', regex=False)
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace('$', '', regex=False)
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace(',', '', regex=False)
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce').fillna(0.0)
            
        return df_cleaned
    except Exception as e:
        st.error(f"Error reading file structure: {e}")
        return None

def process_dataframe(df, manual_discount, is_biweekly):
    processed_records = []
    factor = (12.0 / 26.0) if is_biweekly else 1.0
    
    for _, row in df.iterrows():
        msrp = row['MSRP']
        cash_discount = row['Cash Discount']
        fin_disc = row['Finance Discount']
        lease_disc = row['Lease Discount']
        
        f24 = calculate_finance_payment(msrp, fin_disc, manual_discount, row['Fin 24mo Rate'], 24)
        f36 = calculate_finance_payment(msrp, fin_disc, manual_discount, row['Fin 36mo Rate'], 36)
        f48 = calculate_finance_payment(msrp, fin_disc, manual_discount, row['Fin 48mo Rate'], 48)
        f60 = calculate_finance_payment(msrp, fin_disc, manual_discount, row['Fin 60mo Rate'], 60)
        f72 = calculate_finance_payment(msrp, fin_disc, manual_discount, row['Fin 72mo Rate'], 72)
        f84 = calculate_finance_payment(msrp, fin_disc, manual_discount, row['Fin 84mo Rate'], 84)
        
        l36 = calculate_lease_payment(msrp, lease_disc, manual_discount, row['Lease 36mo Rate'], row['Lease 36mo Residual'], 36)
        l48 = calculate_lease_payment(msrp, lease_disc, manual_discount, row['Lease 48mo Rate'], row['Lease 48mo Residual'], 48)
        l60 = calculate_lease_payment(msrp, lease_disc, manual_discount, row['Lease 60mo Rate'], row['Lease 60mo Residual'], 60)
        
        record = {
            "Car Model": row['Car Model'],
            "Trim": row['Trim'],
            "MSRP": msrp,
            "Cash Price (Net)": msrp - cash_discount,
            "Fin 24mo": f24 * factor, 
            "Fin 36mo": f36 * factor, 
            "Fin 48mo": f48 * factor, 
            "Fin 60mo": f60 * factor, 
            "Fin 72mo": f72 * factor, 
            "Fin 84mo": f84 * factor,
            "Lease 36mo": l36 * factor, 
            "Lease 48mo": l48 * factor, 
            "Lease 60mo": l60 * factor
        }
        processed_records.append(record)
        
    return pd.DataFrame(processed_records)

def compute_deltas(df_curr, df_prev, payment_cols):
    delta_df = pd.merge(df_curr, df_prev, on=["Car Model", "Trim"], suffixes=('_curr', '_prev'))
    if delta_df.empty:
        return pd.DataFrame()
        
    df_deltas = pd.DataFrame()
    df_deltas["Car Model"] = delta_df["Car Model"]
    df_deltas["Trim"] = delta_df["Trim"]
    df_deltas["Δ MSRP"] = delta_df["MSRP_curr"] - delta_df["MSRP_prev"]
    
    for col in payment_cols:
        df_deltas[f"Δ {col}"] = delta_df[f"{col}_curr"] - delta_df[f"{col}_prev"]
        
    return df_deltas

# --- Sidebar Controls ---
st.sidebar.header("🎛️ Dashboard Controls")
manual_discount = st.sidebar.number_input("Apply Additional Manual Discount ($)", min_value=0.0, value=0.0, step=100.0)

frequency = st.sidebar.radio("Payment Frequency", ["Monthly", "Bi-Weekly"])
is_biweekly = (frequency == "Bi-Weekly")

max_payment = st.sidebar.number_input(f"Filter: Maximum {frequency} Payment ($)", min_value=0.0, value=0.0, step=50.0)

st.sidebar.subheader("📂 File Uploads")
current_file = st.sidebar.file_uploader("Upload Current Program Excel File", type=["xlsx", "xls"])
previous_file = st.sidebar.file_uploader("Upload Previous Month Excel File", type=["xlsx", "xls"])

# --- Main Page Execution ---
if current_file is not None:
    df_current_cleaned = clean_and_parse_file(current_file)
    
    if df_current_cleaned is not None and not df_current_cleaned.empty:
        df_current_calculated = process_dataframe(df_current_cleaned, manual_discount, is_biweekly)
        
        unique_models = sorted(df_current_calculated["Car Model"].unique())
        dropdown_options = ["All Models"] + unique_models
        selected_model = st.selectbox("🎯 Filter by Car Model:", dropdown_options, index=0)
        
        if selected_model != "All Models":
            df_current_filtered = df_current_calculated[df_current_calculated["Car Model"] == selected_model]
        else:
            df_current_filtered = df_current_calculated.copy()
        
        payment_cols = ["Fin 24mo", "Fin 36mo", "Fin 48mo", "Fin 60mo", "Fin 72mo", "Fin 84mo", "Lease 36mo", "Lease 48mo", "Lease 60mo"]
        if max_payment > 0:
            mask = df_current_filtered[payment_cols].le(max_payment).any(axis=1)
            df_current_display = df_current_filtered[mask]
        else:
            df_current_display = df_current_filtered.copy()
            
        st.dataframe(df_current_display)

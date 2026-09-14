import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(page_title="Car Program Analytics Dashboard", layout="wide")
st.title("🚗 Automotive Finance & Lease Program Dashboard")
st.write("Upload your program files to calculate and compare dealer matrices on a single page.")

# Dynamic Mapping Definition matching your exact Excel Text Headers
HEADER_RULES = {
    'Car Model': 'Model',
    'Trim': 'Trim',
    'MSRP': 'MSRP',
    'Cash Discount': 'Cash Discount',
    'Fin 24mo Rate': '24 month finance rate',
    'Fin 36mo Rate': '36 month finance rate',
    'Fin 48mo Rate': '48 month finance rate',
    'Fin 60mo Rate': '60 month finance rate',
    'Fin 72mo Rate': '72 month finance rate',
    'Fin 84mo Rate': '84 month finance rate',
    'Finance Discount': 'Finance discount',
    'Lease 36mo Rate': '36 month lease rate',
    'Lease 48mo Rate': '48 month lease rate',
    'Lease 60mo Rate': '60 month lease rate',
    'Lease Discount': 'lease discount',
    'Lease 36mo Residual': '36 month lease residual',
    'Lease 48mo Residual': '48 month lease residual',
    'Lease 60mo Residual': '60 month lease residual'
}

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
    
    # 1. Depreciation Charge
    if net_cap_cost <= residual_value:
        depreciation_charge = 0.0
    else:
        depreciation_charge = (net_cap_cost - residual_value) / months
        
    # Standard lease interest rate percentage conversion to Money Factor
    money_factor = (rate_pct / 100) / 24
    
    # 2. Finance Rent Charge
    finance_charge = (net_cap_cost + residual_value) * money_factor
    
    total_lease_payment = depreciation_charge + finance_charge
    return max(0.0, total_lease_payment)

def clean_and_parse_file(uploaded_file):
    """Dynamically maps columns based on clean textual header matching rules with row-by-row cell normalization"""
    try:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        
        df_cleaned = pd.DataFrame()
        
        for standard_key, file_label in HEADER_RULES.items():
            if file_label in df_raw.columns:
                df_cleaned[standard_key] = df_raw[file_label]
            else:
                df_cleaned[standard_key] = 0.0
                
        df_cleaned['Car Model'] = df_cleaned['Car Model'].astype(str).str.strip()
        df_cleaned['Trim'] = df_cleaned['Trim'].astype(str).str.strip()
        
        # Sanitize financial characters cell by cell
        numeric_cols = [col for col in df_cleaned.columns if col not in ['Car Model', 'Trim']]
        for col in numeric_cols:
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace('%', '', regex=False)
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace('$', '', regex=False)
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace(',', '', regex=False)
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce').fillna(0.0)
            
            # FIXED: Row-by-row single cell validation. If an individual cell is a decimal (e.g. 0.0499), convert it to whole percentage (4.99)
            if 'Rate' in col or 'Residual' in col:
                df_cleaned[col] = df_cleaned[col].apply(lambda x: x * 100.0 if (0.0 < x <= 1.0) else x)
            
        return df_cleaned
    except Exception as e:
        st.error(f"Error validating file headers: {e}")
        return None

def process_dataframe(df, manual_discount, is_biweekly):
    if df is None or df.empty:
        return pd.DataFrame()
        
    processed_records = []
    # Retained your precise business logic calculation: (Monthly * 12) / 26
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
    if df_curr.empty or df_prev.empty:
        return pd.DataFrame()
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
payment_cols = ["Fin 24mo", "Fin 36mo", "Fin 48mo", "Fin 60mo", "Fin 72mo", "Fin 84mo", "Lease 36mo", "Lease 48mo", "Lease 60mo"]

if current_file is None:
    st.info("👋 Welcome! Please upload your program file to view calculated dealer matrices.")
    st.stop()

st.subheader("📊 Section 1: Current Program Analytics")
df_current_cleaned = clean_and_parse_file(current_file)

if df_current_cleaned is not None and not df_current_cleaned.empty:
    df_current_calculated = process_dataframe(df_current_cleaned, manual_discount, is_biweekly)
    
    if df_current_calculated is not None and not df_current_calculated.empty:
        unique_models = sorted(df_current_calculated["Car Model"].unique())
        dropdown_options = ["All Models"] + unique_models
        selected_model = st.selectbox("🎯 Filter by Car Model:", dropdown_options, index=0)
        
        if selected_model != "All Models":
            df_current_filtered = df_current_calculated[df_current_calculated["Car Model"] == selected_model]
        else:
            df_current_filtered = df_current_calculated.copy()
        
        if max_payment > 0:
            mask = df_current_filtered[payment_cols].le(max_payment).any(axis=1)
            df_current_display = df_current_filtered[mask]
        else:
            df_current_display = df_current_filtered.copy()
            
        st.dataframe(df_current_display)
        
        # --- Section 2: Delta Comparison View ---
        if previous_file is not None:
            st.markdown("---")
            st.subheader("🔄 Section 2: Program vs Prior Month Comparison Deltas")
            
            df_prev_cleaned = clean_and_parse_file(previous_file)
            if df_prev_cleaned is not None and not df_prev_cleaned.empty:
                df_prev_calculated = process_dataframe(df_prev_cleaned, manual_discount, is_biweekly)
                
                if not df_prev_calculated.empty:
                    df_deltas = compute_deltas(df_current_calculated, df_prev_calculated, payment_cols)
                    
                    if not df_deltas.empty:
                        if selected_model != "All Models":
                            df_deltas_filtered = df_deltas[df_deltas["Car Model"] == selected_model]
                        else:

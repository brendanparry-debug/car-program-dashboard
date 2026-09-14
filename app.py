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
    return float(payment)

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
    return float(total_lease_payment)

def clean_and_parse_file(uploaded_file):
    try:
        df_raw = pd.read_excel(uploaded_file)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
        
        df_cleaned = pd.DataFrame()
        
        for standard_key, file_label in HEADER_RULES.items():
            matched_col = next((c for c in df_raw.columns if c.lower() == file_label.lower()), None)
            if matched_col:
                df_cleaned[standard_key] = df_raw[matched_col]
            else:
                df_cleaned[standard_key] = 0.0
                
        df_cleaned['Car Model'] = df_cleaned['Car Model'].astype(str).str.strip()
        df_cleaned['Trim'] = df_cleaned['Trim'].astype(str).str.strip()
        
        numeric_cols = [col for col in df_cleaned.columns if col not in ['Car Model', 'Trim']]
        for col in numeric_cols:
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace('%', '', regex=False)
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace('$', '', regex=False)
            df_cleaned[col] = df_cleaned[col].astype(str).str.replace(',', '', regex=False)
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce').fillna(0.0)
            
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
            "MSRP": float(msrp),
            "Cash Price (Net)": float(msrp - cash_discount),
            "Fin 24mo": float(f24 * factor), 
            "Fin 36mo": float(f36 * factor), 
            "Fin 48mo": f48 * factor, 
            "Fin 60mo": float(f60 * factor), 
            "Fin 72mo": float(f72 * factor), 
            "Fin 84mo": float(f84 * factor),
            "Lease 36mo": float(l36 * factor), 
            "Lease 48mo": float(l48 * factor), 
            "Lease 60mo": float(l60 * factor)
        }
        processed_records.append(record)
        
    return pd.DataFrame(processed_records)

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
display_cols = ["MSRP", "Cash Price (Net)"] + payment_cols

if current_file is None:
    st.info("👋 Welcome! Please upload your program file to view calculated dealer matrices.")
    st.stop()

st.subheader("📊 Section 1: Current Program Analytics")
df_current_cleaned = clean_and_parse_file(current_file)

if df_current_cleaned is None or df_current_cleaned.empty:
    st.error("❌ Failed to parse data from your Current file.")
    st.stop()

df_current_calculated = process_dataframe(df_current_cleaned, manual_discount, is_biweekly)

unique_models = sorted(df_current_calculated["Car Model"].unique())
dropdown_options = ["All Models"] + unique_models
selected_model = st.selectbox("🎯 Filter by Car Model:", dropdown_options, index=0)

if selected_model != "All Models":
    df_current_filtered = df_current_calculated[df_current_calculated["Car Model"] == selected_model]
else:
    df_current_filtered = df_current_calculated.copy()
    
if max_payment > 0:
    mask = df_current_filtered[payment_cols].le(max_payment).any(axis=1)
    df_current_display = df_current_filtered[mask].copy()
else:
    df_current_display = df_current_filtered.copy()
    
df_s1_show = df_current_display.copy()
for col in display_cols:
    df_s1_show[col] = df_s1_show[col].round(0).astype(int)
st.dataframe(df_s1_show)

# --- Section 2: Unified Flattened Delta Comparison View ---
if previous_file is not None:
    st.markdown("---")
    st.subheader("🔄 Section 2: Program vs Prior Month Comparison Deltas")
    
    df_prev_cleaned = clean_and_parse_file(previous_file)
    df_prev_calculated = process_dataframe(df_prev_cleaned, manual_discount, is_biweekly)
    
    if df_prev_calculated.empty:
        st.error("❌ Failed to parse data from your Previous Month file.")
        st.stop()
        
    if selected_model != "All Models":
        df_prev_filtered = df_prev_calculated[df_prev_calculated["Car Model"] == selected_model]
    else:
        df_prev_filtered = df_prev_calculated.copy()
        
    # Perform clean dynamic relational dataset merge
    df_deltas = pd.merge(df_current_filtered, df_prev_filtered, on=["Car Model", "Trim"], suffixes=('_curr', '_prev'))
    
    if df_deltas.empty:
        st.warning("⚠️ No exact matching variants found between sheets to generate comparison matrices.")
    else:
        df_deltas_display = pd.DataFrame()
        df_deltas_display["Car Model"] = df_deltas["Car Model"]
        df_deltas_display["Trim"] = df_deltas["Trim"]
        df_deltas_display["Δ MSRP"] = (df_deltas["MSRP_curr"] - df_deltas["MSRP_prev"]).round(0).astype(int)
        
        for col in payment_cols:
            df_deltas_display[f"Δ {col}"] = (df_deltas[f"{col}_curr"] - df_deltas[f"{col}_prev"]).round(0).astype(int)
            
        st.write("Showing variance differences (**Current Month** minus **Previous Month**):")
        st.dataframe(df_deltas_display)

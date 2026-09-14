import streamlit as st
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(page_title="Car Program Analytics Dashboard", layout="wide")
st.title("🚗 Automotive Finance & Lease Program Dashboard")
st.write("Upload your program files to calculate and compare dealer matrices on a single page.")

# Define absolute standard letters mapping for columns A through R
COLUMN_MAPPING = {
    0: 'Car Model',
    1: 'Trim',
    2: 'MSRP',
    3: 'Cash Discount',
    4: 'Fin 24mo Rate',
    5: 'Fin 36mo Rate',
    6: 'Fin 48mo Rate',
    7: 'Fin 60mo Rate',
    8: 'Fin 72mo Rate',
    9: 'Fin 84mo Rate',
    10: 'Finance Discount',
    11: 'Lease 36mo Rate',
    12: 'Lease 48mo Rate',
    13: 'Lease 60mo Rate',
    14: 'Lease Discount',
    15: 'Lease 36mo Residual',
    16: 'Lease 48mo Residual',
    17: 'Lease 60mo Residual'
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
    
    if net_cap_cost <= residual_value:
        depreciation_charge = 0.0
    else:
        depreciation_charge = (net_cap_cost - residual_value) / months
        
    money_factor = (rate_pct / 100) / 24
    finance_charge = (net_cap_cost + residual_value) * money_factor
    
    total_lease_payment = depreciation_charge + finance_charge
    return max(0.0, total_lease_payment)

def clean_and_parse_file(uploaded_file):
    """Safely extracts columns A through R and applies safe type casting"""
    try:
        df_raw = pd.read_excel(uploaded_file, header=None)
        
        # Safe structural boundary evaluation
        if df_raw.shape[1] < 18:
            st.error(f"❌ Uploaded file must have at least 18 columns (A through R). Found only {df_raw.shape[1]} columns.")
            return None
            
        df = df_raw.iloc[:, :18].copy()
        df.columns = [COLUMN_MAPPING[i] for i in range(18)]
        
        # FIXED: Extract the actual string value from row 0, column 0
        if len(df) > 0:
            first_row_val = str(df.iloc[0, 0]).strip().lower()
            if "car" in first_row_val or "model" in first_row_val:
                df = df.iloc[1:].reset_index(drop=True)
            
        df['Car Model'] = df['Car Model'].astype(str).str.strip()
        df['Trim'] = df['Trim'].astype(str).str.strip()
        
        numeric_cols = [
            'MSRP', 'Cash Discount', 'Fin 24mo Rate', 'Fin 36mo Rate', 'Fin 48mo Rate', 
            'Fin 60mo Rate', 'Fin 72mo Rate', 'Fin 84mo Rate', 'Finance Discount', 
            'Lease 36mo Rate', 'Lease 48mo Rate', 'Lease 60mo Rate', 'Lease Discount', 
            'Lease 36mo Residual', 'Lease 48mo Residual', 'Lease 60mo Residual'
        ]
        
        for col in numeric_cols:
            df[col] = df[col].astype(str).str.replace('%', '', regex=False)
            df[col] = df[col].astype(str).str.replace('$', '', regex=False)
            df[col] = df[col].astype(str).str.replace(',', '', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            
        return df
    except Exception as e:
        st.error(f"Error reading file structure: {e}")
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

if current_file is not None:
    st.subheader("📊 Section 1: Current Program Analytics")
    df_current_cleaned = clean_and_parse_file(current_file)
    
    if df_current_cleaned is not None and not df_current_cleaned.empty:
        df_current_calculated = process_dataframe(df_current_cleaned, manual_discount, is_biweekly)
        
        # FIXED: Added fallback checking criteria around the calculation return
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
            
            # --- Section 2: Comparison View ---
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
                                df_deltas_filtered = df_deltas.copy()
                                
                            st.write("Showing differences (**Current Month** minus **Previous Month**):")
                            st.dataframe(df_deltas_filtered)
                        else:

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
        
        if df_raw.shape[1] < 18:
            st.error(f"❌ Uploaded file must have at least 18 columns (A through R). Found only {df_raw.shape[1]} columns.")
            return None
            
        df = df_raw.iloc[:, :18].copy()
        df.columns = [COLUMN_MAPPING[i] for i in range(18)]
        
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

def process_dataframe(df, manual_discount):
    processed_records = []
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
            "Fin 24mo": f24, "Fin 36mo": f36, "Fin 48mo": f48, 
            "Fin 60mo": f60, "Fin 72mo": f72, "Fin 84mo": f84,
            "Lease 36mo": l36, "Lease 48mo": l48, "Lease 60mo": l60
        }
        processed_records.append(record)
        
    return pd.DataFrame(processed_records)

# --- Sidebar Controls ---
st.sidebar.header("🎛️ Dashboard Controls")
manual_discount = st.sidebar.number_input("Apply Additional Manual Discount ($)", min_value=0.0, value=0.0, step=100.0)

st.sidebar.subheader("📂 File Uploads")
current_file = st.sidebar.file_uploader("Upload Current Program Excel File", type=["xlsx", "xls"])
previous_file = st.sidebar.file_uploader("Upload Previous Month Excel File", type=["xlsx", "xls"])

# --- Main Page Execution ---
if current_file is not None:
    df_current_cleaned = clean_and_parse_file(current_file)
    
    if df_current_cleaned is not None and not df_current_cleaned.empty:
        df_current_calculated = process_dataframe(df_current_cleaned, manual_discount)
        
        # Section 1: Active Program Calculations
        st.header("📊 Section 1: Current Program Calculations")
        
        # Use simple dynamic column configuration formatting mapping rather than custom styling syntax
        currency_config = {c: st.column_config.NumberColumn(format="$%.2f") for c in df_current_calculated.columns if c not in ["Car Model", "Trim"]}
        st.dataframe(df_current_calculated, column_config=currency_config, use_container_width=True)
        
        st.markdown("---") 
        
        # Section 2: Program Deltas
        st.header("📉 Section 2: Differences from Previous Month Program")
        if previous_file is not None:
            df_prev_cleaned = clean_and_parse_file(previous_file)
            
            if df_prev_cleaned is not None and not df_prev_cleaned.empty:
                df_prev_calculated = process_dataframe(df_prev_cleaned, manual_discount)
                
                delta_df = pd.merge(
                    df_current_calculated, 
                    df_prev_calculated, 
                    on=["Car Model", "Trim"], 
                    suffixes=('_curr', '_prev')
                )
                
                if not delta_df.empty:
                    output_delta_records = []
                    for _, row in delta_df.iterrows():
                        delta_rec = {
                            "Car Model": row["Car Model"],
                            "Trim": row["Trim"],
                            "Δ MSRP": row["MSRP_curr"] - row["MSRP_prev"],
                            "Δ Fin 24mo": row["Fin 24mo_curr"] - row["Fin 24mo_prev"],
                            "Δ Fin 36mo": row["Fin 36mo_curr"] - row["Fin 36mo_prev"],
                            "Δ Fin 48mo": row["Fin 48mo_curr"] - row["Fin 48mo_prev"],
                            "Δ Fin 60mo": row["Fin 60mo_curr"] - row["Fin 60mo_prev"],
                            "Δ Fin 72mo": row["Fin 72mo_curr"] - row["Fin 72mo_prev"],
                            "Δ Fin 84mo": row["Fin 84mo_curr"] - row["Fin 84mo_prev"],
                            "Δ Lease 36mo": row["Lease 36mo_curr"] - row["Lease 36mo_prev"],
                            "Δ Lease 48mo": row["Lease 48mo_curr"] - row["Lease 48mo_prev"],
                            "Δ Lease 60mo": row["Lease 60mo_curr"] - row["Lease 60mo_prev"],
                        }
                        output_delta_records.append(delta_rec)
                        
                    df_deltas = pd.DataFrame(output_delta_records)
                    delta_config = {col: st.column_config.NumberColumn(format="$%.2f") for col in df_deltas.columns if col not in ["Car Model", "Trim"]}
                    
                    st.caption("💡 Payments displaying positive values indicate a rate/cost increase vs last month.")
                    st.dataframe(df_deltas, column_config=delta_config, use_container_width=True)
                else:
                    st.warning("⚠️ No exact matches found for combinations of Car Model and Trim between both uploaded files.")
        else:
            st.warning("💡 Drop your older sheet into the **'Upload Previous Month Excel File'** sidebar menu item to populate the program differences down here.")
else:
    st.info("👋 System ready. Please upload your **Current Program File** to load calculations.")

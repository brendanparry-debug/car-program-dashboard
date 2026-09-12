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

def process_dataframe(df, manual_discount):
    processed_records = []
    for idx, row in df.iterrows():
        try:
            # Map columns explicitly by position to perfectly match your layout requirements
            # Column A=0, B=1, C=2, etc.
            car_model = str(row.iloc[0])
            trim = str(row.iloc[1])
            msrp = float(row.iloc[2])
            cash_discount = float(row.iloc[3])
            
            # Finance Rates (Columns E to J -> Indices 4 to 9)
            f24_r, f36_r, f48_r, f60_r, f72_r, f84_r = [float(row.iloc[i]) for i in range(4, 10)]
            
            # Finance Discount (Column K -> Index 10)
            fin_disc = float(row.iloc[10])
            
            # Lease Rates (Columns L to N -> Indices 11 to 13)
            l36_r, l48_r, l60_r = [float(row.iloc[i]) for i in range(11, 14)]
            
            # Lease Discount (Column O -> Index 14)
            lease_disc = float(row.iloc[14])
            
            # Lease Residuals (Columns P to R -> Indices 15 to 17)
            l36_res, l48_res, l60_res = [float(row.iloc[i]) for i in range(15, 18)]
            
            # Run Calculations
            f24 = calculate_finance_payment(msrp, fin_disc, manual_discount, f24_r, 24)
            f36 = calculate_finance_payment(msrp, fin_disc, manual_discount, f36_r, 36)
            f48 = calculate_finance_payment(msrp, fin_disc, manual_discount, f48_r, 48)
            f60 = calculate_finance_payment(msrp, fin_disc, manual_discount, f60_r, 60)
            f72 = calculate_finance_payment(msrp, fin_disc, manual_discount, f72_r, 72)
            f84 = calculate_finance_payment(msrp, fin_disc, manual_discount, f84_r, 84)
            
            l36 = calculate_lease_payment(msrp, lease_disc, manual_discount, l36_r, l36_res, 36)
            l48 = calculate_lease_payment(msrp, lease_disc, manual_discount, l48_r, l48_res, 48)
            l60 = calculate_lease_payment(msrp, lease_disc, manual_discount, l60_r, l60_res, 60)
            
            record = {
                "Car Model": car_model,
                "Trim": trim,
                "MSRP": msrp,
                "Cash Price (Net)": msrp - cash_discount,
                "Fin 24mo": f24, "Fin 36mo": f36, "Fin 48mo": f48, 
                "Fin 60mo": f60, "Fin 72mo": f72, "Fin 84mo": f84,
                "Lease 36mo": l36, "Lease 48mo": l48, "Lease 60mo": l60
            }
            processed_records.append(record)
        except Exception:
            continue
            
    # Always guarantee that key columns exist during creation
    if len(processed_records) == 0:
        return pd.DataFrame(columns=["Car Model", "Trim", "MSRP", "Cash Price (Net)", "Fin 24mo", "Fin 36mo", "Fin 48mo", "Fin 60mo", "Fin 72mo", "Fin 84mo", "Lease 36mo", "Lease 48mo", "Lease 60mo"])
        
    return pd.DataFrame(processed_records)

# --- Sidebar Controls ---
st.sidebar.header("🎛️ Dashboard Controls")
manual_discount = st.sidebar.number_input("Apply Additional Manual Discount ($)", min_value=0.0, value=0.0, step=100.0)

st.sidebar.subheader("📂 File Uploads")
# header=None tells pandas to read strictly by positions (0,1,2) instead of trusting header strings
current_file = st.sidebar.file_uploader("Upload Current Program Excel File", type=["xlsx", "xls"])
previous_file = st.sidebar.file_uploader("Upload Previous Month Excel File", type=["xlsx", "xls"])

# --- Main Page Layout ---
if current_file is not None:
    df_current_raw = pd.read_excel(current_file, header=None)
    
    # If file contains headers, discard the first string row so it doesn't break calculations
    if "model" in str(df_current_raw.iloc[0,0]).lower() or "car" in str(df_current_raw.iloc[0,0]).lower():
        df_current_raw = df_current_raw.iloc[1:].reset_index(drop=True)
        
    df_current_calculated = process_dataframe(df_current_raw, manual_discount)
    
    # Section 1: Active Program Calculations
    st.header("📊 Section 1: Current Program Calculations")
    currency_cols = [c for c in df_current_calculated.columns if c not in ["Car Model", "Trim"]]
    format_dict = {col: "${:,.2f}" for col in currency_cols}
    st.dataframe(df_current_calculated.style.format(format_dict), use_container_width=True)
    
    st.markdown("---") # Visual Section Divider
    
    # Section 2: Program Deltas
    st.header("📉 Section 2: Differences from Previous Month Program")
    if previous_file is not None:
        df_prev_raw = pd.read_excel(previous_file, header=None)
        
        if "model" in str(df_prev_raw.iloc[0,0]).lower() or "car" in str(df_prev_raw.iloc[0,0]).lower():
            df_prev_raw = df_prev_raw.iloc[1:].reset_index(drop=True)
            
        df_prev_calculated = process_dataframe(df_prev_raw, manual_discount)
        
        # Merge metrics on matching explicit keys
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
            delta_currency_cols = [c for c in df_deltas.columns if c not in ["Car Model", "Trim"]]
            delta_format_dict = {col: "${:,.2f}" for col in delta_currency_cols}
            
            def style_deltas(val):
                if isinstance(val, (int, float)):
                    if val > 0: return 'color: #D32F2F; font-weight: bold;' # More expensive
                    if val < 0: return 'color: #388E3C; font-weight: bold;' # Cheaper program
                return ''
                
            st.caption("🟢 Green items indicate an improved program (lower payment); 🔴 Red items mean payments went up.")
            st.dataframe(
                df_deltas.style.format(delta_format_dict).applymap(style_deltas, subset=delta_currency_cols),
                use_container_width=True
            )
        else:
            st.warning("⚠️ No exact matches found for combinations of Car Model and Trim between both uploaded files.")
    else:
        st.warning("💡 Drop your older sheet into the **'Upload Previous Month Excel File'** sidebar menu item to populate the program differences down here.")
else:
    st.info("👋 System ready. Please upload your **Current Program File** to load calculations.")

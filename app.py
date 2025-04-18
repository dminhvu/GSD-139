import streamlit as st
import pandas as pd
import io

# ── UI setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="GSD-139: Nuvo")
st.title("GSD-139: Nuvo")


# ── Core processing function ───────────────────────────────────────────────
def process_file(file):
    # 1. Read incoming file
    if file.name.lower().endswith(".csv"):
        df = pd.read_csv(file, skip_blank_lines=True)
    elif file.name.lower().endswith((".xls", ".xlsx")):
        df = pd.read_excel(file)
    else:
        st.error("Unsupported file format. Please upload a CSV or Excel file.")
        return None
    if df.empty:
        st.error("The uploaded file is empty.")
        return None

    # 2. Normalize column names if needed
    #    (e.g. sample uses "Custome" instead of "Customer")
    if "Custome" in df.columns and "Customer" not in df.columns:
        df = df.rename(columns={"Custome": "Customer"})

    # 3. Check for required columns
    required = {
        "Customer",
        "Reference Document",
        "Profit Center",
        "Amount in Company Code Currency",
        "Invoice Type",
    }
    missing = required - set(df.columns)
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return None

    # ── New ledger‑format steps ───────────────────────────────────────────────
    # Step 1: Extract numeric balance from Column G
    df["Document Balance"] = (
        df["Amount in Company Code Currency"]
        .astype(str)
        .str.extract(r"(-?[0-9,.]+)")[0]
        .str.replace(",", "", regex=False)
        .astype(float)
        .apply(lambda x: f"{x:.2f}")
    )

    # Step 2: Derive Transaction Type
    df["Transaction Type"] = df["Document Balance"].apply(
        lambda x: "INV" if float(x) > 0 else "CRD"
    )

    # Step 3: Build Document Number = RefDoc + "_" + first 4 of Profit Center
    df["ProfitCenterCode"] = df["Profit Center"].astype(str).str.extract(r"^(\d{4})")[0]
    df["Document Number"] = (
        df["Reference Document"].astype(str) + "_" + df["ProfitCenterCode"]
    )

    # Step 4: Build Debtor Reference = Customer + "_" + Invoice Type
    df["Debtor Reference"] = (
        df["Customer"].astype(str) + "_" + df["Invoice Type"].astype(str)
    )

    # 4. Select and reorder only the four ledger columns
    result_df = df[
        ["Debtor Reference", "Transaction Type", "Document Number", "Document Balance"]
    ].reset_index(drop=True)

    return result_df


# ── Download helper ────────────────────────────────────────────────────────
def get_csv_download_link(df):
    csv = df.to_csv(index=False)
    return io.BytesIO(csv.encode())


# ── Streamlit app flow ─────────────────────────────────────────────────────
st.write("Upload your Excel or CSV file:")
uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    processed_df = process_file(uploaded_file)
    if processed_df is not None:
        st.write("Processed Data:")
        st.dataframe(processed_df)
        csv_buffer = get_csv_download_link(processed_df)
        st.download_button(
            label="Download Processed File",
            data=csv_buffer,
            file_name="nuvo_ledger_upload.csv",
            mime="text/csv",
        )

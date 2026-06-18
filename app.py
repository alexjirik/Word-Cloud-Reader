import streamlit as st
import pandas as pd

# =====================================================================
# INITIAL SETUP & PAGE CONFIG
# =====================================================================
st.set_page_config(page_title="Verbatim Explorer", layout="wide")

st.title("🔍 Qualitative Verbatim Explorer")
st.markdown("Upload your raw survey data to instantly read, search, and filter open-ended respondent statements.")

# =====================================================================
# DATA LOADING ENGINE
# =====================================================================
@st.cache_data
def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

# =====================================================================
# SIDEBAR: UPLOAD
# =====================================================================
st.sidebar.header("1. Upload Data")
uploaded_file = st.sidebar.file_uploader("Upload Raw Data File (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file:
    df = load_data(uploaded_file)
    st.sidebar.success(f"Data Loaded: {len(df):,} total rows.")
    
    # =====================================================================
    # MAIN WORKSPACE
    # =====================================================================
    st.markdown("### 2. Select Question")
    # Get all columns so the user can look at any variable they want
    all_columns = df.columns.tolist()
    
    selected_col = st.selectbox("Choose a column to read the raw statements:", all_columns)
    
    # Clean the data: Drop NAs and empty strings
    raw_statements = df[selected_col].dropna().astype(str)
    # Filter out empty whitespace strings
    valid_statements = raw_statements[raw_statements.str.strip() != ""]
    
    st.markdown("---")
    
    col_search, col_stats = st.columns([3, 1])
    
    with col_search:
        search_query = st.text_input("🔎 Search these statements for a specific keyword (optional):")
    
    # Apply search filter if the user typed something
    if search_query:
        mask = valid_statements.str.contains(search_query, case=False, na=False)
        final_statements = valid_statements[mask]
    else:
        final_statements = valid_statements
        
    with col_stats:
        st.markdown("<br>", unsafe_allow_html=True) # Spacing alignment
        st.metric(label="Valid Statements Found", value=f"{len(final_statements):,}")

    # =====================================================================
    # DISPLAY ENGINE
    # =====================================================================
    if len(final_statements) == 0:
        st.warning("No statements found matching your criteria, or this column contains no valid text.")
    else:
        # Create a clean dataframe for display
        display_df = pd.DataFrame({"Respondent Statement": final_statements.values})
        
        # Use Streamlit's new column_config to ensure long text wraps beautifully
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=600,
            column_config={
                "Respondent Statement": st.column_config.TextColumn(
                    "Raw Verbatim Responses",
                    width="large"
                )
            }
        )

else:
    st.info("👉 Please upload your Raw Data File in the sidebar to begin reading statements.")

import streamlit as st
import pandas as pd
import io

# --- CONFIGURATION & STYLING ---
st.set_page_config(layout="wide", page_title="Survey Text Extractor")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .step-header { color: #1e88e5; font-weight: 600; margin-top: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- APP UI ---
st.title("📄 Survey Data Cleaner")
st.markdown("Raw survey exports often use numbers or short codes (like 'Q1' or 'Brand_5') instead of the actual question text. Upload your file here to merge and promote the real statements to the top so your data is readable!")

# 1. File Upload
uploaded_file = st.file_uploader("Upload your raw data (.csv or .xlsx)", type=['csv', 'xlsx'])

if uploaded_file:
    file_ext = uploaded_file.name.split('.')[-1]
    
    try:
        # Read the file without assuming the first row is the header
        if file_ext == 'csv':
            df = pd.read_csv(uploaded_file, header=None)
        else:
            df = pd.read_excel(uploaded_file, header=None)
            
        st.markdown('<h3 class="step-header">Step 1: Preview the Raw Mess</h3>', unsafe_allow_html=True)
        st.caption("Notice how the real questions/statements are usually trapped in Row 0, 1, or 2.")
        st.dataframe(df.head(10), use_container_width=True)
        
        st.markdown('<h3 class="step-header">Step 2: Find the Statements</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 2])
        with col1:
            # Let the user pick which row contains the good text
            row_options = {f"Row {i}": i for i in range(min(5, len(df)))}
            selected_row_label = st.selectbox(
                "Which row contains the actual Questions/Statements?", 
                list(row_options.keys()), 
                index=1 if len(df) > 1 else 0
            )
            header_idx = row_options[selected_row_label]
            
            # Optional: Ask if they want to combine the ID with the text (e.g., "Q1 - I like this")
            combine_headers = st.checkbox("Combine with the row above it? (e.g., 'Q1: Statement')", value=False)

        with col2:
            st.info("When you click the button below, we will chop off the top rows, promote your selected row to be the main column headers, and clean the dataset.")
            process_btn = st.button("✨ Convert Numbers to Statements", type="primary", use_container_width=True)

        if process_btn:
            # Clean the dataframe based on user selection
            if combine_headers and header_idx > 0:
                # Combine the row above with the statement row
                row_above = df.iloc[header_idx - 1].astype(str).replace('nan', '')
                statement_row = df.iloc[header_idx].astype(str).replace('nan', '')
                
                # Create combined header, removing empty parts
                new_header = []
                for a, b in zip(row_above, statement_row):
                    a_clean = a.strip()
                    b_clean = b.strip()
                    if a_clean and b_clean:
                        new_header.append(f"{a_clean}: {b_clean}")
                    else:
                        new_header.append(a_clean or b_clean or "Unnamed Column")
            else:
                # Just use the single selected row
                new_header = df.iloc[header_idx].fillna("Unnamed Column").astype(str)

            # Keep only the data rows (everything below the chosen header)
            df_clean = df.iloc[header_idx + 1:].copy()
            df_clean.columns = new_header
            df_clean.reset_index(drop=True, inplace=True)
            
            # Store in session state so it doesn't disappear
            st.session_state.df_clean = df_clean
            
    except Exception as e:
        st.error(f"Something went wrong while reading the file: {e}")

# --- DISPLAY CLEAN DATA AND DOWNLOAD ---
if 'df_clean' in st.session_state:
    st.markdown('<h3 class="step-header">Step 3: Your Cleaned Data</h3>', unsafe_allow_html=True)
    st.dataframe(st.session_state.df_clean, use_container_width=True)
    
    # Prepare CSV for download
    csv_buffer = io.BytesIO()
    st.session_state.df_clean.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    st.download_button(
        label="📥 Download Cleaned Data (.csv)",
        data=csv_buffer,
        file_name="cleaned_statements.csv",
        mime="text/csv",
        type="primary"
    )

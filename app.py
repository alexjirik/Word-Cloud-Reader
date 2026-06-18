import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import io

# --- CONFIGURATION & STYLING ---
st.set_page_config(layout="wide", page_title="Survey Word Cloud Studio")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .step-header { color: #1e88e5; font-weight: 600; margin-top: 20px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

# Helper function to prevent duplicate headers after translation
def rename_columns_uniquely(df, col_mapping):
    new_cols = []
    seen = {}
    for col in df.columns:
        new_name = col_mapping.get(col, col)
        if pd.isna(new_name) or str(new_name).strip() == "":
            new_name = col
        new_name = str(new_name).strip()
        if new_name in seen:
            seen[new_name] += 1
            new_cols.append(f"{new_name} ({seen[new_name]})")
        else:
            seen[new_name] = 0
            new_cols.append(new_name)
    df.columns = new_cols
    return df

# --- APP UI ---
st.title("☁️ Survey Word Cloud Studio")
st.markdown("Upload your survey files together. The app will automatically decode all response numbers into readable text, replace confusing column headers with your actual questions, and generate custom word clouds.")

# --- FILE UPLOADING ---
st.markdown('<h3 class="step-header">Step 1: Upload Your Survey Data</h3>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    raw_file = st.file_uploader("1. Upload Raw Data (.csv or .xlsx)", type=['csv', 'xlsx'])
with col2:
    info_file = st.file_uploader("2. Upload Variable Info (.csv or .xlsx) [Optional]", type=['csv', 'xlsx'])
with col3:
    values_file = st.file_uploader("3. Upload Variable Values (.csv or .xlsx) [Optional]", type=['csv', 'xlsx'])

if raw_file:
    try:
        # 1. Load Main Raw Dataset
        if raw_file.name.endswith('.csv'):
            df = pd.read_csv(raw_file, low_memory=False)
        else:
            df = pd.read_excel(raw_file)
            
        # 2. Decode Categorical Numbers (Variable Values)
        if values_file:
            if values_file.name.endswith('.csv'):
                df_values = pd.read_csv(values_file, header=None)
            else:
                df_values = pd.read_excel(values_file, header=None)
                
            # Dynamically scan to find where the header actually starts
            val_header_idx = 0
            for idx, row in df_values.iterrows():
                row_strs = [str(x).lower().strip() for x in row.dropna()]
                if 'value' in row_strs and 'label' in row_strs:
                    val_header_idx = idx
                    break
            
            df_values_clean = df_values.iloc[val_header_idx + 1:].copy()
            df_values_clean = df_values_clean.iloc[:, :3] # Keep first three columns
            df_values_clean.columns = ['Variable', 'Value', 'Label']
            df_values_clean['Variable'] = df_values_clean['Variable'].ffill() # Fill down empty variables
            
            # Construct nested dictionary mapping: { Variable: { Value_String: Label } }
            mapping_dict = {}
            for var, group in df_values_clean.groupby('Variable'):
                sub_map = {}
                for _, row in group.iterrows():
                    v = row['Value']
                    l = row['Label']
                    if pd.isna(v) or pd.isna(l): continue
                    try:
                        vf = float(v)
                        v_str = str(int(vf)) if vf.is_integer() else str(vf)
                    except ValueError:
                        v_str = str(v).strip()
                    sub_map[v_str] = str(l).strip()
                mapping_dict[str(var).strip()] = sub_map
                
            # Safely decode cells
            def decode_val(val, d):
                if pd.isna(val): return val
                try:
                    vf = float(val)
                    v_str = str(int(vf)) if vf.is_integer() else str(vf)
                except ValueError:
                    v_str = str(val).strip()
                return d.get(v_str, val)
                
            for col in df.columns:
                if col in mapping_dict:
                    df[col] = df[col].apply(lambda x: decode_val(x, mapping_dict[col]))
            st.success("🔢 Response numbers successfully decoded into text labels!")

        # 3. Decode Column Headers (Variable Info)
        if info_file:
            if info_file.name.endswith('.csv'):
                df_info = pd.read_csv(info_file, header=None)
            else:
                df_info = pd.read_excel(info_file, header=None)
                
            # Dynamically scan to find header row
            info_header_idx = 0
            for idx, row in df_info.iterrows():
                row_strs = [str(x).lower().strip() for x in row.dropna()]
                if 'variable' in row_strs and 'label' in row_strs:
                    info_header_idx = idx
                    break
                    
            df_info_clean = df_info.iloc[info_header_idx + 1:].copy()
            df_info_clean.columns = df_info.iloc[info_header_idx].astype(str).str.strip()
            
            if 'Variable' in df_info_clean.columns and 'Label' in df_info_clean.columns:
                col_mapping = dict(zip(df_info_clean['Variable'], df_info_clean['Label']))
                # Translate uniquely to avoid duplicates crash
                df = rename_columns_uniquely(df, col_mapping)
                st.success("🏷️ Column headers successfully translated to real questions!")
            else:
                st.warning("Could not find required 'Variable' and 'Label' columns in the Info file.")
        
        st.session_state.df = df
        
        with st.expander("👀 Preview Decoded Dataset"):
            st.dataframe(df.head(10), use_container_width=True)
            
    except Exception as e:
        st.error(f"Error loading files: {e}")

# --- WORD CLOUD GENERATOR ---
if 'df' in st.session_state:
    df = st.session_state.df
    
    st.markdown('<h3 class="step-header">Step 2: Configure and Generate Word Cloud</h3>', unsafe_allow_html=True)
    
    wc_col1, wc_col2 = st.columns([1, 2])
    
    with wc_col1:
        st.markdown("**1. Select the Open-Ended Question (Verbatims)**")
        text_col = st.selectbox("Which column contains the open-ended responses?", df.columns)
        
        st.markdown("**2. Filter by Demographic / Segment (Optional)**")
        filter_col = st.selectbox("Filter data using:", ["No Filter"] + list(df.columns))
        
        df_filtered = df.copy()
        if filter_col != "No Filter":
            unique_vals = [val for val in df[filter_col].dropna().unique() if str(val).strip() != ""]
            selected_val = st.selectbox(f"Only show responses where '{filter_col}' is exactly:", unique_vals)
            df_filtered = df_filtered[df_filtered[filter_col] == selected_val]
            
        st.markdown("**3. Add Custom Stopwords**")
        custom_stopwords_input = st.text_input("Words to ignore (separated by commas)", placeholder="e.g., coke, juice, good, nothing")
        
        generate_btn = st.button("☁️ Draw Word Cloud", type="primary", use_container_width=True)

    with wc_col2:
        if generate_btn:
            # Gather, filter, and normalize the text answers
            text_data = df_filtered[text_col].dropna().astype(str).tolist()
            text_data = [t for t in text_data if len(t.strip()) > 2]
            all_text = " ".join(text_data)
            
            if len(all_text.strip()) < 10:
                st.warning("Not enough text data found in this column to generate a word cloud. Verify that you selected an open-ended comment column.")
            else:
                # Add default and custom ignore-words
                stopwords = set(STOPWORDS)
                if custom_stopwords_input:
                    custom_words = [w.strip().lower() for w in custom_stopwords_input.split(",")]
                    stopwords.update(custom_words)
                
                with st.spinner("Drawing cloud..."):
                    wordcloud = WordCloud(
                        width=800, 
                        height=400, 
                        background_color='white', 
                        stopwords=stopwords,
                        colormap='viridis',
                        max_words=100
                    ).generate(all_text)
                    
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
                    
                    st.success(f"Word Cloud generated from {len(text_data)} matched responses!")
                    
                    # Provide text download
                    st.download_button(
                        label="📥 Download Extracted Text Block (.txt)",
                        data=all_text,
                        file_name="extracted_verbatims.txt",
                        mime="text/plain"
                    )

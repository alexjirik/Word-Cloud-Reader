import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import io

# --- CONFIGURATION & STYLING ---
st.set_page_config(layout="wide", page_title="Survey Word Cloud Studio")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .step-header { color: #1e88e5; font-weight: 600; margin-top: 20px; border-bottom: 2px solid #f0f2f6; padding-bottom: 10px;}
    </style>
""", unsafe_allow_html=True)

# Helper function to prevent duplicate headers
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

# --- THE SPEED OPTIMIZATION: ONE-TIME PROCESS BUTTON ---
if raw_file:
    if st.button("🚀 Load & Decode Data", type="primary", use_container_width=True):
        with st.spinner("Parsing thousands of columns... please wait a few seconds..."):
            try:
                # 1. Load Main Raw Dataset
                if raw_file.name.endswith('.csv'):
                    df = pd.read_csv(raw_file, low_memory=False)
                else:
                    df = pd.read_excel(raw_file)
                    
                # 2. Decode Categorical Numbers (Variable Values) using fast vectorized lookups
                if values_file:
                    if values_file.name.endswith('.csv'):
                        df_values = pd.read_csv(values_file, header=None)
                    else:
                        df_values = pd.read_excel(values_file, header=None)
                        
                    # Find where header starts
                    val_header_idx = 0
                    for idx, row in df_values.iterrows():
                        row_strs = [str(x).lower().strip() for x in row.dropna()]
                        if 'value' in row_strs and 'label' in row_strs:
                            val_header_idx = idx
                            break
                    
                    df_values_clean = df_values.iloc[val_header_idx + 1:].copy()
                    df_values_clean = df_values_clean.iloc[:, :3]
                    df_values_clean.columns = ['Variable', 'Value', 'Label']
                    df_values_clean['Variable'] = df_values_clean['Variable'].ffill()
                    
                    # Populate lookup dictionary
                    mapping_dict = {}
                    for var, group in df_values_clean.groupby('Variable'):
                        sub_map = {}
                        for _, row in group.iterrows():
                            v = row['Value']
                            l = row['Label']
                            if pd.isna(v) or pd.isna(l): continue
                            
                            label_str = str(l).strip()
                            sub_map[str(v).strip()] = label_str
                            try:
                                vf = float(v)
                                sub_map[vf] = label_str
                                if vf.is_integer():
                                    sub_map[int(vf)] = label_str
                            except ValueError:
                                pass
                        mapping_dict[str(var).strip()] = sub_map
                        
                    # Blazing Fast Vectorized Mapping (Only maps columns that exist)
                    cols_to_map = set(df.columns).intersection(mapping_dict.keys())
                    for col in cols_to_map:
                        df[col] = df[col].map(mapping_dict[col]).fillna(df[col])

                # 3. Decode Column Headers (Variable Info)
                if info_file:
                    if info_file.name.endswith('.csv'):
                        df_info = pd.read_csv(info_file, header=None)
                    else:
                        df_info = pd.read_excel(info_file, header=None)
                        
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
                        df = rename_columns_uniquely(df, col_mapping)
                
                # Save the processed data to RAM so we never have to load it again!
                st.session_state.df = df
                st.success("✅ Data successfully loaded and cached in memory!")
                
            except Exception as e:
                st.error(f"Error loading files: {e}")

# --- WORD CLOUD GENERATOR (INSTANT UI) ---
if 'df' in st.session_state:
    df = st.session_state.df
    
    with st.expander("👀 Preview Decoded Dataset"):
        st.dataframe(df.head(10), use_container_width=True)
    
    st.markdown('<h3 class="step-header">Step 2: Configure and Generate Word Cloud</h3>', unsafe_allow_html=True)
    
    wc_col1, wc_col2 = st.columns([1, 2])
    
    # We declare variables here so they can be accessed outside the columns for the data grid
    text_data = []
    all_text = ""
    wordcloud_generated = False
    
    with wc_col1:
        st.markdown("**1. Select the Open-Ended Question (Verbatims)**")
        text_col = st.selectbox("Which column contains the open-ended responses?", df.columns)
        
        # SMART HEURISTIC: Check if selected column is just checkbox data
        series_clean = df[text_col].dropna().astype(str).str.strip().str.lower()
        unique_check = series_clean.unique()
        if len(unique_check) <= 3 and any(x in ['checked', 'unchecked', 'selected', 'not selected', 'yes', 'no'] for x in unique_check):
            st.warning("⚠️ **Warning:** It looks like you selected a multiple-choice checkbox grid instead of a comment box! Try choosing an open-ended question (like questions starting with **Q7a**) for a better word cloud.")
        
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
            
            if len(all_text.strip()) < 1:
                st.warning("Not enough text data found in this column to generate a word cloud. Verify that you selected an open-ended comment column.")
            else:
                # Add default and custom ignore-words
                stopwords = set(STOPWORDS)
                
                # Automatically add survey checkbox artifacts to stopwords
                survey_noise = {
                    "checked", "unchecked", "selected", "not", "yes", "no", "nan", 
                    "prefer", "english", "french", "canadian", "prefer english", "prefer french",
                    "n", "a", "none", "1", "0"
                }
                stopwords.update(survey_noise)
                
                if custom_stopwords_input:
                    custom_words = [w.strip().lower() for w in custom_stopwords_input.split(",")]
                    stopwords.update(custom_words)
                
                with st.spinner("Drawing cloud..."):
                    try:
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
                        wordcloud_generated = True
                        
                        # Provide text download
                        st.download_button(
                            label="📥 Download Extracted Text Block (.txt)",
                            data=all_text,
                            file_name="extracted_verbatims.txt",
                            mime="text/plain"
                        )
                    except ValueError:
                        # Catch the exact error the user hit!
                        st.error("❌ **No valid words left to draw a cloud!** This happened because the column you chose only contains words that are currently in our 'Ignore List' (like 'Checked', 'Yes', 'No'). Try selecting a question that asks respondents to type out their answers (e.g. questions starting with Q7a).")

    # --- FULL STATEMENTS GRID ---
    # Display the grid of full statements directly beneath the word cloud
    if wordcloud_generated and len(text_data) > 0:
        st.markdown("---")
        st.markdown('<h3 class="step-header">📝 Full Responses Grid</h3>', unsafe_allow_html=True)
        st.markdown("Read the complete, uncut statements from your filtered respondents below:")
        
        # Create a clean dataframe for the grid
        df_statements = pd.DataFrame({text_col: text_data})
        
        # Display the dataframe taking up the full container width
        st.dataframe(df_statements, use_container_width=True, hide_index=True)

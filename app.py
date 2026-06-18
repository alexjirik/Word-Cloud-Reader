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

# --- APP UI ---
st.title("☁️ Survey Word Cloud Studio")
st.markdown("Upload your Raw Data and Variable Info files. We will automatically translate the column codes into real questions and generate Word Clouds from your open-ended responses.")

# --- FILE UPLOADING ---
st.markdown('<h3 class="step-header">Step 1: Upload Your Data</h3>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    raw_file = st.file_uploader("1. Upload Raw Data (.csv or .xlsx)", type=['csv', 'xlsx'])
with col2:
    info_file = st.file_uploader("2. Upload Variable Info (.csv or .xlsx)", type=['csv', 'xlsx'], help="Upload your Variable Info file here to translate codes like 'S1' into the actual question text.")

if raw_file:
    try:
        # Check if raw file is CSV or Excel and load accordingly
        if raw_file.name.endswith('.csv'):
            df = pd.read_csv(raw_file, low_memory=False)
        else:
            df = pd.read_excel(raw_file)
        
        # If the user uploaded the Variable Info file, load and rename the columns
        if info_file:
            if info_file.name.endswith('.csv'):
                # header=1 skips the blank title row
                df_info = pd.read_csv(info_file, header=1)
            else:
                df_info = pd.read_excel(info_file, header=1)
                
            # Create a dictionary mapping the "Variable" column to the "Label" column
            if 'Variable' in df_info.columns and 'Label' in df_info.columns:
                col_mapping = dict(zip(df_info['Variable'], df_info['Label']))
                df = df.rename(columns=col_mapping)
                st.success("✅ Successfully translated column names using your Variable Info file!")
            else:
                st.warning("Could not find 'Variable' and 'Label' columns in the Info file.")
        
        st.session_state.df = df
        
        with st.expander("👀 Preview your Data"):
            st.dataframe(df.head(10), use_container_width=True)
            
    except Exception as e:
        st.error(f"Error loading files: {e}")

# --- WORD CLOUD GENERATOR ---
if 'df' in st.session_state:
    df = st.session_state.df
    
    st.markdown('<h3 class="step-header">Step 2: Generate Word Cloud</h3>', unsafe_allow_html=True)
    
    wc_col1, wc_col2 = st.columns([1, 2])
    
    with wc_col1:
        st.markdown("**1. Select the Open-Ended Question**")
        # Let user pick the column with text
        text_col = st.selectbox("Which column contains the verbatims? (e.g., 'Why do you like this brand?')", df.columns)
        
        st.markdown("**2. Filter by Brand / Demographic (Optional)**")
        # Let user pick a column to filter by
        filter_col = st.selectbox("Filter data using:", ["No Filter"] + list(df.columns))
        
        df_filtered = df.copy()
        if filter_col != "No Filter":
            # Find unique answers in that column
            unique_vals = [val for val in df[filter_col].dropna().unique() if str(val).strip() != ""]
            selected_val = st.selectbox(f"Only show responses where '{filter_col}' is exactly:", unique_vals)
            df_filtered = df_filtered[df_filtered[filter_col] == selected_val]
            
        st.markdown("**3. Add Custom Stopwords**")
        custom_stopwords_input = st.text_input("Words to ignore (comma separated)", placeholder="e.g., coke, juice, good, nothing")
        
        generate_btn = st.button("☁️ Draw Word Cloud", type="primary", use_container_width=True)

    with wc_col2:
        if generate_btn:
            # Drop empty answers and combine into one giant string
            text_data = df_filtered[text_col].dropna().astype(str).tolist()
            # Filter out answers that are just numbers or single characters
            text_data = [t for t in text_data if len(t.strip()) > 2]
            all_text = " ".join(text_data)
            
            if len(all_text.strip()) < 10:
                st.warning("Not enough text data found in this column to generate a word cloud. Are you sure you selected an open-ended question?")
            else:
                # Setup words to ignore
                stopwords = set(STOPWORDS)
                if custom_stopwords_input:
                    custom_words = [w.strip().lower() for w in custom_stopwords_input.split(",")]
                    stopwords.update(custom_words)
                
                # Draw the Word Cloud
                with st.spinner("Drawing cloud..."):
                    wordcloud = WordCloud(
                        width=800, 
                        height=400, 
                        background_color='white', 
                        stopwords=stopwords,
                        colormap='viridis',
                        max_words=100
                    ).generate(all_text)
                    
                    # Display the image
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
                    
                    st.success(f"Word Cloud generated from {len(text_data)} responses!")
                    
                    # Provide text download
                    st.download_button(
                        label="📥 Download Raw Text (.txt)",
                        data=all_text,
                        file_name="extracted_verbatims.txt",
                        mime="text/plain"
                    )

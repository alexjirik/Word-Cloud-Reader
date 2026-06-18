import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import io

st.set_page_config(layout="wide", page_title="Survey Word Cloud Studio")

st.title("☁️ Survey Word Cloud Studio")
st.markdown("Upload your Raw Data and Variable Info files. We will automatically translate the column codes into real questions and generate Word Clouds from your open-ended responses.")

st.markdown("### Step 1: Upload Your Data")

col1, col2 = st.columns(2)
with col1:
    raw_file = st.file_uploader("1. Upload Raw Data (.csv)", type=['csv'])
with col2:
    info_file = st.file_uploader("2. Upload Variable Info (.csv)", type=['csv'])

if raw_file:
    try:
        df = pd.read_csv(raw_file, low_memory=False)
        
        if info_file:
            df_info = pd.read_csv(info_file, header=1)
            if 'Variable' in df_info.columns and 'Label' in df_info.columns:
                col_mapping = dict(zip(df_info['Variable'], df_info['Label']))
                df = df.rename(columns=col_mapping)
                st.success("✅ Successfully translated column names!")
        
        st.session_state.df = df
        with st.expander("👀 Preview your Data"):
            st.dataframe(df.head(10))
            
    except Exception as e:
        st.error(f"Error loading files: {e}")

if 'df' in st.session_state:
    df = st.session_state.df
    st.markdown("### Step 2: Generate Word Cloud")
    
    wc_col1, wc_col2 = st.columns([1, 2])
    
    with wc_col1:
        st.markdown("**1. Select the Open-Ended Question**")
        text_col = st.selectbox("Which column contains the verbatims?", df.columns)
        
        st.markdown("**2. Filter by Brand / Demographic (Optional)**")
        filter_col = st.selectbox("Filter data using:", ["No Filter"] + list(df.columns))
        
        df_filtered = df.copy()
        if filter_col != "No Filter":
            unique_vals = [val for val in df[filter_col].dropna().unique() if str(val).strip() != ""]
            selected_val = st.selectbox(f"Only show responses where '{filter_col}' is exactly:", unique_vals)
            df_filtered = df_filtered[df_filtered[filter_col] == selected_val]
            
        st.markdown("**3. Add Custom Stopwords**")
        custom_stopwords_input = st.text_input("Words to ignore (comma separated)", placeholder="e.g., coke, juice, good, nothing")
        
        generate_btn = st.button("☁️ Draw Word Cloud", type="primary", use_container_width=True)

    with wc_col2:
        if generate_btn:
            text_data = df_filtered[text_col].dropna().astype(str).tolist()
            text_data = [t for t in text_data if len(t.strip()) > 2]
            all_text = " ".join(text_data)
            
            if len(all_text.strip()) < 10:
                st.warning("Not enough text data found in this column.")
            else:
                stopwords = set(STOPWORDS)
                if custom_stopwords_input:
                    custom_words = [w.strip().lower() for w in custom_stopwords_input.split(",")]
                    stopwords.update(custom_words)
                
                with st.spinner("Drawing cloud..."):
                    wordcloud = WordCloud(width=800, height=400, background_color='white', stopwords=stopwords).generate(all_text)
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)

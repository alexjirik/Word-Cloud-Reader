import streamlit as st
import pandas as pd
import io
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt

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
st.markdown("Upload raw survey exports, clean the headers, and instantly generate word clouds from open-ended responses.")

# 1. File Upload
uploaded_file = st.file_uploader("Upload your raw data (.csv or .xlsx)", type=['csv', 'xlsx'])

if uploaded_file:
    file_ext = uploaded_file.name.split('.')[-1]
    
    try:
        if file_ext == 'csv':
            df = pd.read_csv(uploaded_file, header=None)
        else:
            df = pd.read_excel(uploaded_file, header=None)
            
        st.markdown('<h3 class="step-header">Step 1: Find the Statements</h3>', unsafe_allow_html=True)
        st.caption("Raw surveys usually hide the real question text in row 0, 1, or 2. Pick the correct row below to fix your table.")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            row_options = {f"Row {i}": i for i in range(min(5, len(df)))}
            selected_row_label = st.selectbox(
                "Which row contains the actual Questions/Statements?", 
                list(row_options.keys()), 
                index=1 if len(df) > 1 else 0
            )
            header_idx = row_options[selected_row_label]
            combine_headers = st.checkbox("Combine with the row above it? (e.g., 'Q1: Statement')", value=False)

        with col2:
            st.dataframe(df.head(5), use_container_width=True)
            process_btn = st.button("✨ Clean Dataset", type="primary", use_container_width=True)

        if process_btn:
            if combine_headers and header_idx > 0:
                row_above = df.iloc[header_idx - 1].astype(str).replace('nan', '')
                statement_row = df.iloc[header_idx].astype(str).replace('nan', '')
                new_header = [f"{a.strip()}: {b.strip()}" if a.strip() and b.strip() else (a.strip() or b.strip() or "Unnamed") for a, b in zip(row_above, statement_row)]
            else:
                new_header = df.iloc[header_idx].fillna("Unnamed").astype(str)

            df_clean = df.iloc[header_idx + 1:].copy()
            df_clean.columns = new_header
            df_clean.reset_index(drop=True, inplace=True)
            st.session_state.df_clean = df_clean
            
    except Exception as e:
        st.error(f"Something went wrong reading the file: {e}")

# --- WORD CLOUD GENERATOR ---
if 'df_clean' in st.session_state:
    df_clean = st.session_state.df_clean
    
    st.markdown('<h3 class="step-header">Step 2: Word Cloud Generator</h3>', unsafe_allow_html=True)
    
    wc_col1, wc_col2 = st.columns([1, 2])
    
    with wc_col1:
        st.markdown("**1. Choose your Text**")
        # Ask user which column has the open ended text
        text_col = st.selectbox("Which column has the open-ended responses? (e.g., 'Why do you like this?')", df_clean.columns)
        
        st.markdown("**2. Filter your Data (Optional)**")
        # Ask user if they want to filter by brand or sentiment
        filter_col = st.selectbox("Do you want to filter by Brand or Sentiment?", ["No Filter"] + list(df_clean.columns))
        
        df_filtered = df_clean.copy()
        if filter_col != "No Filter":
            unique_vals = [val for val in df_clean[filter_col].dropna().unique() if str(val).strip() != ""]
            selected_val = st.selectbox(f"Only show responses where {filter_col} is:", unique_vals)
            df_filtered = df_filtered[df_filtered[filter_col] == selected_val]
            
        st.markdown("**3. Add Custom Stopwords**")
        # Allow users to exclude brand names or useless words like "good" or "nothing"
        custom_stopwords_input = st.text_input("Words to ignore (comma separated)", placeholder="e.g., brandname, nothing, good")
        
        generate_btn = st.button("☁️ Draw Word Cloud", type="primary", use_container_width=True)

    with wc_col2:
        if generate_btn:
            # 1. Gather all the text into one giant paragraph
            all_text = " ".join(df_filtered[text_col].dropna().astype(str).tolist())
            
            if len(all_text.strip()) < 5:
                st.warning("Not enough text data found to generate a word cloud!")
            else:
                # 2. Setup stopwords (words to ignore)
                stopwords = set(STOPWORDS)
                if custom_stopwords_input:
                    custom_words = [w.strip().lower() for w in custom_stopwords_input.split(",")]
                    stopwords.update(custom_words)
                
                # 3. Generate the Image
                with st.spinner("Drawing cloud..."):
                    wordcloud = WordCloud(
                        width=800, 
                        height=400, 
                        background_color='white', 
                        stopwords=stopwords,
                        colormap='viridis',
                        max_words=100
                    ).generate(all_text)
                    
                    # 4. Display the Image using Matplotlib
                    fig, ax = plt.subplots(figsize=(10, 5))
                    ax.imshow(wordcloud, interpolation='bilinear')
                    ax.axis('off')
                    st.pyplot(fig)
                    
                    # 5. Provide a raw text download in case they still want to use another site
                    st.download_button(
                        label="📥 Download Raw Text (.txt)",
                        data=all_text,
                        file_name="extracted_survey_text.txt",
                        mime="text/plain"
                    )

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import io

# =====================================================================
# INITIAL SETUP & PAGE CONFIG
# =====================================================================
st.set_page_config(page_title="Dynamic Word Cloud Builder", layout="wide")

st.title("☁️ Dynamic Qualitative Insight Builder")
st.markdown("Upload your raw survey data and your codebook to translate messy variable names into readable questions. Instantly generate word clouds and search raw verbatims.")

# =====================================================================
# DATA LOADING ENGINE
# =====================================================================
@st.cache_data
def load_data(file):
    if file.name.endswith('.csv'):
        return pd.read_csv(file)
    else:
        return pd.read_excel(file)

@st.cache_data
def load_codebook(file):
    """Loads the codebook and creates a dictionary mapping variables to readable labels."""
    if file.name.endswith('.csv'):
        cb = pd.read_csv(file)
    else:
        cb = pd.read_excel(file)
        
    # Standardize column names to uppercase to catch variations
    cb.columns = [str(c).strip().upper() for c in cb.columns]
    
    # Try to find the Variable and Label columns
    var_col = next((c for c in cb.columns if 'VAR' in c or 'NAME' in c), None)
    label_col = next((c for c in cb.columns if 'LABEL' in c or 'TEXT' in c or 'QUESTION' in c), None)
    
    mapping_dict = {}
    if var_col and label_col:
        # Create a dictionary of {Variable_Name: Readable_Label}
        for _, row in cb.dropna(subset=[var_col, label_col]).iterrows():
            mapping_dict[str(row[var_col]).strip()] = str(row[label_col]).strip()
            
    return mapping_dict

# =====================================================================
# SIDEBAR: UPLOAD & CONFIGURATION
# =====================================================================
st.sidebar.header("1. Upload Data & Codebook")
data_file = st.sidebar.file_uploader("Upload Raw Survey Data (.csv/.xlsx)", type=["csv", "xlsx"], key="data")
codebook_file = st.sidebar.file_uploader("Upload Codebook (Optional) (.csv/.xlsx)", type=["csv", "xlsx"], key="codebook")

if data_file:
    df = load_data(data_file)
    st.sidebar.success(f"Data Loaded: {len(df)} rows!")
    
    # Process Codebook if provided
    var_mapping = {}
    if codebook_file:
        var_mapping = load_codebook(codebook_file)
        if var_mapping:
            st.sidebar.success(f"Codebook applied! Mapped {len(var_mapping)} variables.")
        else:
            st.sidebar.warning("Could not auto-detect 'Variable' and 'Label' columns in codebook.")
    
    st.sidebar.markdown("---")
    st.sidebar.header("2. Configure Cloud")
    
    # Automatically find text columns (open-ended responses)
    text_columns = df.select_dtypes(include=['object', 'string']).columns.tolist()
    
    if not text_columns:
        st.error("No text columns found in the uploaded data file.")
    else:
        # Create a UI-friendly list of options using the codebook mapping
        ui_options = []
        col_to_raw_map = {}
        
        for col in text_columns:
            # If the column is in the codebook, use the readable label
            readable_name = var_mapping.get(col, col)
            display_str = f"[{col}] {readable_name}"
            ui_options.append(display_str)
            col_to_raw_map[display_str] = col
            
        selected_display = st.sidebar.selectbox("Select the Open-Ended Question:", ui_options)
        selected_col = col_to_raw_map[selected_display]
        
        # Strategic feature: Custom Stop Words input
        st.sidebar.markdown("### Refine Your Insights")
        st.sidebar.markdown("Type words to exclude from the cloud, separated by commas (e.g., *juice, drink, orange*).")
        custom_stopwords_input = st.sidebar.text_area("Custom Stop Words:")
        
        # Visual customization
        st.sidebar.markdown("### Visual Settings")
        colormap = st.sidebar.selectbox("Color Theme", ["viridis", "magma", "plasma", "inferno", "cividis", "ocean", "coolwarm", "Blues"])
        bg_color = st.sidebar.selectbox("Background Color", ["white", "black"])
        max_words = st.sidebar.slider("Max Words to Display", min_value=10, max_value=200, value=75)

        # =====================================================================
        # MAIN WORKSPACE: PROCESSING & VISUALIZATION
        # =====================================================================
        st.subheader(f"Visualizing: {selected_display}")
        
        # Clean the text: Drop NAs and convert everything to a single massive string
        raw_text_series = df[selected_col].dropna().astype(str)
        # Filter out obvious non-answers like "none", "n/a", "na"
        valid_verbatims = raw_text_series[~raw_text_series.str.lower().isin(['none', 'n/a', 'na', 'nothing', 'no'])]
        all_text = " ".join(valid_verbatims)
        
        if len(all_text.strip()) == 0:
            st.warning("This column appears to be empty, contains no valid text, or only contains numeric data.")
        else:
            # Build the stop words list
            base_stopwords = set(STOPWORDS)
            if custom_stopwords_input:
                user_stops = [word.strip().lower() for word in custom_stopwords_input.split(",")]
                base_stopwords.update(user_stops)
            
            # Generate the Word Cloud
            with st.spinner("Generating visualization..."):
                wordcloud = WordCloud(
                    width=1200, 
                    height=600, 
                    background_color=bg_color, 
                    colormap=colormap, 
                    stopwords=base_stopwords,
                    max_words=max_words,
                    contour_width=3, 
                    contour_color='steelblue',
                    collocations=False # Prevents words like "orange orange" from duplicating
                ).generate(all_text)
                
                # Render using matplotlib
                fig, ax = plt.subplots(figsize=(15, 7.5))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis("off")
                
                st.pyplot(fig)
                
                # Download button for the image
                buf = io.BytesIO()
                fig.savefig(buf, format="png", bbox_inches='tight', pad_inches=0, dpi=300)
                btn = st.download_button(
                    label="⬇️ Download Word Cloud Image",
                    data=buf.getvalue(),
                    file_name=f"wordcloud_{selected_col}.png",
                    mime="image/png",
                    type="primary"
                )
                
                # =====================================================================
                # VERBATIM EXPLORER
                # =====================================================================
                st.markdown("---")
                st.markdown("### Raw Verbatim Explorer")
                st.markdown(f"**Total Valid Responses:** {len(valid_verbatims):,}")
                st.markdown("Search the raw responses below to find the context behind the big words.")
                
                search_term = st.text_input("🔍 Search verbatims for a specific word:")
                
                if search_term:
                    # Filter the dataframe to only show rows where the text contains the search term (case-insensitive)
                    mask = valid_verbatims.str.contains(search_term, case=False, na=False)
                    filtered_verbatims = valid_verbatims[mask]
                    
                    st.caption(f"Found **{len(filtered_verbatims)}** verbatims mentioning '{search_term}':")
                    for verbatim in filtered_verbatims.head(100): # Show top 100 to prevent browser lag
                        st.info(f'"{verbatim}"')

else:
    st.info("👉 Please upload your Raw Data File in the sidebar to begin. You can also upload a Codebook to map raw variables to readable questions.")

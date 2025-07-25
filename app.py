import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_excel("zip_code_demographics4.xlsx", dtype={'zip': str}, engine='openpyxl')
    numeric_cols = ['COLI', 'TRF', 'PCPI', 'PTR', 'TR', 'RSF', 'Savings']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=numeric_cols, inplace=True)
    return df

df = load_data()

# --- Normalize Utilities ---
def normalize(series):
    return 100 * (series - series.min()) / (series.max() - series.min())

def inverse_normalize(series):
    return 100 * (series.max() - series) / (series.max() - series.min())

# --- Base Score Calculator ---
def base_score_from_agi(agi, pcpi):
    ratio = agi / pcpi
    if ratio < 0.6: return 350, "🔴 Critical Financial Stress"
    elif ratio < 0.7: return 400, "🔴 Severe Stress"
    elif ratio < 0.8: return 450, "🔴 Financial Stress"
    elif ratio < 0.9: return 500, "🟠 At Risk"
    elif ratio < 1.0: return 550, "🟠 Near Average"
    elif ratio < 1.2: return 600, "🟡 Stable"
    elif ratio < 1.5: return 675, "🟢 Good"
    elif ratio < 2.0: return 750, "🟢 Very Good"
    elif ratio < 2.5: return 800, "🟢 Excellent"
    else: return 850, "🟢 Top Performer (Cap)"

# --- Layout ---
st.set_page_config(page_title="Muse Score Dashboard", layout="wide")
st.title("📊 Muse Score Dashboard")

# Input Panel
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        zip_code = st.text_input("📍 Enter ZIP Code", max_chars=10)
    with col2:
        agi = st.number_input("💰 Enter Your AGI", min_value=1000, max_value=1_000_000, step=1000, value=80000)

st.markdown("---")

# Process
if zip_code in df['zip'].values:
    row = df[df['zip'] == zip_code].iloc[0]

    # Normalize
    COLI = inverse_normalize(df['COLI']).loc[row.name]
    TRF = inverse_normalize(df['TRF']).loc[row.name]
    PTR = inverse_normalize(df['PTR']).loc[row.name]
    SITF = inverse_normalize(df['TR']).loc[row.name]
    RSF = normalize(df['RSF']).loc[row.name]
    ISF = normalize(df['Savings']).loc[row.name]

    # Score
    base_score, status = base_score_from_agi(agi, row['PCPI'])
    adjustment = (
        15 * (COLI / 100) +
        10 * (TRF / 100) +
        10 * (PTR / 100) +
        10 * (SITF / 100) +
        5 * (RSF / 100) +
        5 * (ISF / 100)
    )
    final_score = min(850, round(base_score + adjustment))

    # --- Results ---
    st.markdown("### 🧠 Muse Score Insights")
    col1, col2 = st.columns([1.5, 2])
    with col1:
        st.markdown(f"""
        <div style="font-size:18px;">
        <strong>State:</strong> <span style="color:#1f77b4">{row['state_id']}</span><br>
        <strong>City:</strong> <span style="color:#1f77b4">{row['city']}</span><br>
        <strong><span style="color:#1f77b4">Muse Score:</span></strong> {final_score}<br>
        <strong>Cost of Living Index:</strong> <span style="color:#1f77b4">{row['COLI']}</span><br>
        <strong>Per Capita Income:</strong> <span style="color:#1f77b4">{int(row['PCPI'])}</span>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=final_score,
            title={'text': f"Muse Score"},
            gauge={
                'axis': {'range': [300, 850]},
                'steps': [
                    {'range': [300, 550], 'color': "red"},
                    {'range': [550, 700], 'color': "orange"},
                    {'range': [700, 800], 'color': "yellow"},
                    {'range': [800, 850], 'color': "green"},
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': final_score
                }
            }
        ))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Maps Section ---
    st.markdown("### 🗺️ ZIP Code Maps")
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("Muse Score Category Map (Placeholder)")
        st.image("https://upload.wikimedia.org/wikipedia/commons/1/15/Blank_US_Map_%28states_only%29.svg", caption="You can embed a Tableau map here")

    with col4:
        fig_map = px.scatter_geo(
            df,
            lat="lat", lon="lng",
            color=normalize(df["PCPI"]),
            hover_name="zip",
            title="Per Capita Income by ZIP",
            color_continuous_scale="Viridis",
            projection="albers usa"
        )
        fig_map.update_layout(height=400, margin={"r":0,"t":30,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)

else:
    st.info("Please enter a valid ZIP code to view Muse Score details.")


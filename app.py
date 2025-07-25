import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- Load Data ---
@st.cache_data
def load_data():
    df = pd.read_excel("zip_code_demographics4.xlsx", dtype={'zip': str}, engine='openpyxl')
    df.columns = df.columns.str.strip()
    if 'RSF' not in df.columns:
        df['RSF'] = df['number_of_returns'] / df['population']
    numeric_cols = ['COLI', 'TRF', 'PCPI', 'PTR', 'TR', 'RSF', 'Savings']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df.dropna(subset=numeric_cols + ['lat', 'lng'], inplace=True)
    return df

df = load_data()

# --- Utility Functions ---
def normalize(series):
    return 100 * (series - series.min()) / (series.max() - series.min())

def inverse_normalize(series):
    return 100 * (series.max() - series) / (series.max() - series.min())

def base_score_from_agi(agi, pcpi):
    ratio = agi / pcpi
    if ratio < 0.6: return 350
    elif ratio < 0.7: return 400
    elif ratio < 0.8: return 450
    elif ratio < 0.9: return 500
    elif ratio < 1.0: return 550
    elif ratio < 1.2: return 600
    elif ratio < 1.5: return 675
    elif ratio < 2.0: return 750
    elif ratio < 2.5: return 800
    else: return 850

# --- Page Layout ---
st.set_page_config(page_title="Muse Score Dashboard", layout="wide")
st.title("📊 Muse Score Dashboard")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        zip_code = st.text_input("📍 Enter ZIP Code", value="10001")
    with col2:
        agi = st.number_input("💰 Enter Your AGI", min_value=1000, max_value=1_000_000, step=1000, value=80000)

calculate = st.button("📈 Calculate Muse Score")

# --- When Button is Pressed ---
if calculate and zip_code in df['zip'].values:
    row = df[df['zip'] == zip_code].iloc[0]

    # Normalize inputs
    COLI = inverse_normalize(df['COLI']).loc[row.name]
    TRF = inverse_normalize(df['TRF']).loc[row.name]
    PTR = inverse_normalize(df['PTR']).loc[row.name]
    SITF = inverse_normalize(df['TR']).loc[row.name]
    RSF = normalize(df['RSF']).loc[row.name]
    ISF = normalize(df['Savings']).loc[row.name]

    # Muse Score
    base_score = base_score_from_agi(agi, row['PCPI'])
    adjustment = (
        15 * (COLI / 100) +
        10 * (TRF / 100) +
        10 * (PTR / 100) +
        10 * (SITF / 100) +
        5 * (RSF / 100) +
        5 * (ISF / 100)
    )
    final_score = min(850, round(base_score + adjustment))

    # Compute for all ZIPs
    df_copy = df.copy()
    df_copy['base_score'] = df_copy.apply(lambda x: base_score_from_agi(agi, x['PCPI']), axis=1)
    df_copy['adjustment'] = (
        15 * (inverse_normalize(df_copy['COLI']) / 100) +
        10 * (inverse_normalize(df_copy['TRF']) / 100) +
        10 * (inverse_normalize(df_copy['PTR']) / 100) +
        10 * (inverse_normalize(df_copy['TR']) / 100) +
        5  * (normalize(df_copy['RSF']) / 100) +
        5  * (normalize(df_copy['Savings']) / 100)
    )
    df_copy['muse_score'] = (df_copy['base_score'] + df_copy['adjustment']).clip(upper=850).round()

    # --- Layout as Grid View ---
    col_top_left, col_top_right = st.columns([1.5, 2])
    with col_top_left:
        st.markdown(f"""
        <div style="font-size:18px; background-color:#f9f9f9; padding:15px; border-radius:10px;">
        <strong>State:</strong> <span style="color:#1f77b4">{row['state_id']}</span><br>
        <strong>City:</strong> <span style="color:#1f77b4">{row['city']}</span><br>
        <strong>Muse Score:</strong> <span style="color:#1f77b4">{final_score}</span><br>
        <strong>Cost of Living Index:</strong> <span style="color:#1f77b4">{row['COLI']}</span><br>
        <strong>Per Capita Income:</strong> <span style="color:#1f77b4">${int(row['PCPI']):,}</span>
        </div>
        """, unsafe_allow_html=True)

    with col_top_right:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=final_score,
            title={'text': "Muse Score"},
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

    # Middle row with 2 maps
    col_map1, col_map2 = st.columns(2)
    with col_map1:
        df_state = pd.DataFrame({'state': df['state_id'].unique()})
        df_state['highlight'] = df_state['state'].apply(lambda x: 'Selected' if x == row['state_id'] else 'Other')
        fig1 = px.choropleth(
            df_state,
            locations="state",
            locationmode="USA-states",
            color="highlight",
            color_discrete_map={"Selected": "orange", "Other": "lightgray"},
            scope="usa",
            title="Selected State Highlighted"
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_map2:
        fig2 = px.scatter_geo(
            df_copy,
            lat='lat',
            lon='lng',
            color='muse_score',
            hover_name='zip',
            color_continuous_scale=[
                [0.0, "red"],
                [0.5, "yellow"],
                [0.75, "lightgreen"],
                [1.0, "darkgreen"]
            ],
            range_color=(300, 850),
            title="Muse Score by ZIP Code",
            scope="usa"
        )
        fig2.update_layout(height=400, margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig2, use_container_width=True)

elif calculate:
    st.error("❌ ZIP code not found in the dataset. Please enter a valid ZIP code.")

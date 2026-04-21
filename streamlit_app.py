import streamlit as st
import pandas as pd
import requests
import altair as alt
from streamlit_autorefresh import st_autorefresh

API_URL = "https://tanques-dash.onrender.com/dados"

st.set_page_config(layout="wide")
st.title("💧 Monitoramento de Tanques")

def carregar_dados():
    try:
        r = requests.get(API_URL, timeout=3)

        if r.status_code != 200 or not r.text.strip():
            return pd.DataFrame()

        df = pd.DataFrame(r.json())

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        return df

    except:
        return pd.DataFrame()

df = carregar_dados()

tanques = ["TANQUEA", "TANQUEB", "TANQUEC"]
cols = st.columns(3)

for i, t in enumerate(tanques):
    df_t = df[df["tanque"] == t] if not df.empty else pd.DataFrame()
    valor = df_t.iloc[0]["nivel"] if not df_t.empty else 0

    with cols[i]:
        st.metric(t, f"{valor:.1f}%")

st.markdown("---")

if not df.empty:
    df = df.sort_values("timestamp")

    chart = alt.Chart(df).mark_line().encode(
        x="timestamp:T",
        y="nivel:Q",
        color="tanque:N"
    )

    st.altair_chart(chart, use_container_width=True)

st_autorefresh(interval=2000, key="refresh")

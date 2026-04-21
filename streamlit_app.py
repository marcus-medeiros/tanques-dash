import streamlit as st
import pandas as pd
import requests
import altair as alt
from streamlit_autorefresh import st_autorefresh

API_URL = "https://tanques-dash.onrender.com/dados"

st.set_page_config(
    page_title="TanquesCM",
    layout="wide"
)
st.title("💧 Monitoramento de Tanques")

# --- Carregar dados ---
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

# --- KPIs ---
st.subheader("📊 Nível Atual dos Tanques")

cols = st.columns(3)

if not df.empty:
    df = df.sort_values("timestamp")

    ultimos = {}
    for t in tanques:
        df_t = df[df["tanque"] == t]
        ultimos[t] = df_t.iloc[-1]["nivel"] if not df_t.empty else 0

    media = sum(ultimos.values()) / len(tanques)

    for i, t in enumerate(tanques):
        valor = ultimos[t]
        delta = valor - media

        with cols[i]:
            st.metric(
                label=t,
                value=f"{valor:.1f} %",
                delta=f"{delta:+.1f} vs média"
            )

else:
    for i, t in enumerate(tanques):
        cols[i].metric(t, "0 %")
st.markdown("---")

# --- GRÁFICO ---
st.subheader("📈 Evolução dos Tanques")

if not df.empty:
    chart = alt.Chart(df).mark_line().encode(
        x=alt.X("timestamp:T", title="Tempo"),
        y=alt.Y("nivel:Q", title="Nível (%)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("tanque:N", title="Tanque"),
        tooltip=["timestamp", "tanque", "nivel"]
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

else:
    st.warning("Sem dados ainda")

st.markdown("---")

# --- TABELA ---
st.subheader("📋 Últimas 10 Leituras")

if not df.empty:
    df_display = df.copy()

    df_display["timestamp"] = df_display["timestamp"].dt.strftime("%d/%m %H:%M:%S")

    df_display = df_display.sort_values("timestamp", ascending=False).head(10)

    st.dataframe(
        df_display[["timestamp", "tanque", "nivel"]],
        use_container_width=True
    )

else:
    st.warning("Sem dados disponíveis")

# --- Auto refresh ---
st_autorefresh(interval=2000, key="refresh")

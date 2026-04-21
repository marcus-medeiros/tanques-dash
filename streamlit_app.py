import streamlit as st
import pandas as pd
import requests
import altair as alt
from streamlit_autorefresh import st_autorefresh

API_URL = "https://tanques-dash.onrender.com/dados"

st.set_page_config(layout="wide")
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
st.subheader("📊 Indicadores")

cols = st.columns(4)

if not df.empty:
    df = df.sort_values("timestamp")

    ultimos = {}
    for t in tanques:
        df_t = df[df["tanque"] == t]
        ultimos[t] = df_t.iloc[-1]["nivel"] if not df_t.empty else 0

    media = sum(ultimos.values()) / len(tanques)
    minimo = min(ultimos.values())
    maximo = max(ultimos.values())

    with cols[0]:
        st.metric("Média (%)", f"{media:.1f}")

    with cols[1]:
        st.metric("Mínimo (%)", f"{minimo:.1f}")

    with cols[2]:
        st.metric("Máximo (%)", f"{maximo:.1f}")

    with cols[3]:
        st.metric("Δ Máx-Mín", f"{(maximo - minimo):.1f}")

else:
    for i in range(4):
        cols[i].metric("—", "0")

st.markdown("---")

# --- GRÁFICO GERAL ---
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

# --- TABELA CONSOLIDADA ---
st.subheader("📋 Últimas 10 Leituras (Todos os Tanques)")

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

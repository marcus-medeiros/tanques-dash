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

# --- Métricas no topo ---
st.subheader("📊 Nível Atual")

cols = st.columns(3)
for i, t in enumerate(tanques):
    df_t = df[df["tanque"] == t] if not df.empty else pd.DataFrame()
    valor = df_t.iloc[0]["nivel"] if not df_t.empty else 0

    with cols[i]:
        st.metric(t, f"{valor:.1f} %")

st.markdown("---")

# --- Layout por tanque ---
for t in tanques:
    st.subheader(f"🔹 {t}")

    col_grafico, col_tabela = st.columns([2, 1])

    df_t = df[df["tanque"] == t] if not df.empty else pd.DataFrame()

    if not df_t.empty:
        df_t = df_t.sort_values("timestamp")

        # --- GRÁFICO ---
        with col_grafico:
            chart = alt.Chart(df_t).mark_line().encode(
                x=alt.X("timestamp:T", title="Tempo"),
                y=alt.Y("nivel:Q", title="Nível (%)", scale=alt.Scale(domain=[0, 100])),
                tooltip=["timestamp", "nivel"]
            ).interactive()

            st.altair_chart(chart, use_container_width=True)

        # --- TABELA (últimas 10) ---
        with col_tabela:
            st.markdown("##### Últimas leituras")

            df_display = df_t.tail(10).copy()
            df_display["timestamp"] = df_display["timestamp"].dt.strftime("%H:%M:%S")

            st.dataframe(
                df_display[["timestamp", "nivel"]].iloc[::-1],
                use_container_width=True
            )

    else:
        st.warning(f"Nenhum dado para {t}")

    st.markdown("---")

# --- Auto refresh ---
st_autorefresh(interval=2000, key="refresh")

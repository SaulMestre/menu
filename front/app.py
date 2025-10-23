import streamlit as st
import requests
import os
from datetime import date as dt

st.set_page_config(page_title="Menú semanal", page_icon="🍝")

st.title("🍽️ Gestor de Comidas y Cenas")

# --- Configuración API ---
# API_URL = os.getenv("API_URL", "http://localhost:8000")
API_URL = "https://menu-api-4ev0.onrender.com"

# --- Base local temporal ---
if "db" not in st.session_state:
    st.session_state.db = {}

# --- Sidebar ---
with st.sidebar:
    mode = st.radio("Modo de uso", ["Local", "API"], index=0)
    st.caption("Cambia a 'API' si tienes FastAPI corriendo en http://localhost:8000")

# --- Selector de fecha ---
st.subheader("Selecciona la fecha")
date = st.date_input("Fecha", dt.today()).isoformat()

# --- Entrada para comida ---
st.subheader("🍝 Comida")
col1, col2 = st.columns([3, 1])
with col1:
    lunch_dish = st.text_input("Plato", key="lunch_dish")
with col2:
    lunch_frozen = st.checkbox("Congelado", key="lunch_frozen")

# --- Entrada para cena ---
st.subheader("🥗 Cena")
col3, col4 = st.columns([3, 1])
with col3:
    dinner_dish = st.text_input("Plato", key="dinner_dish")
with col4:
    dinner_frozen = st.checkbox("Congelado", key="dinner_frozen")

# --- Botones ---
colA, colB = st.columns(2)

# ---- Guardar ----
if colA.button("💾 Guardar"):
    payload = {
        "date": date,
        "lunch": {"dish": lunch_dish or None, "frozen": bool(lunch_frozen)},
        "dinner": {"dish": dinner_dish or None, "frozen": bool(dinner_frozen)},
    }

    if mode == "Local":
        st.session_state.db[date] = payload
        st.success(f"Guardado localmente para {date}")
    else:
        try:
            r = requests.post(f"{API_URL}/meals", json=payload, timeout=5)
            if r.ok:
                st.success(f"Guardado en la API para {date}")
            else:
                st.error(f"Error API ({r.status_code}): {r.text}")
        except Exception as e:
            st.error(f"Error al llamar a la API: {e}")

# ---- Ver ----
if colB.button("🔎 Ver"):
    if mode == "Local":
        rec = st.session_state.db.get(date)
        if not rec:
            st.info(f"No hay datos guardados para {date}.")
        else:
            st.json(rec)
            st.write(
                f"🍝 **Comida:** {rec['lunch']['dish'] or '—'} {'(congelada)' if rec['lunch']['frozen'] else ''}\n\n"
                f"🥗 **Cena:** {rec['dinner']['dish'] or '—'} {'(congelada)' if rec['dinner']['frozen'] else ''}"
            )
    else:
        try:
            r = requests.get(f"{API_URL}/meals/{date}", timeout=5)
            if r.status_code == 404:
                st.info(f"No hay datos guardados en la API para {date}.")
            elif r.ok:
                data = r.json()
                st.json(data)
                st.write(
                    f"🍝 **Comida:** {data['lunch']['dish'] or '—'} {'(congelada)' if data['lunch']['frozen'] else ''}\n\n"
                    f"🥗 **Cena:** {data['dinner']['dish'] or '—'} {'(congelada)' if data['dinner']['frozen'] else ''}"
                )
            else:
                st.error(f"Error API ({r.status_code}): {r.text}")
        except Exception as e:
            st.error(f"Error al llamar a la API: {e}")


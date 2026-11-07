"""Interfaz del demo (Streamlit). Ejecutar desde la raíz del repo:

    streamlit run app/main.py
"""
import streamlit as st

import datos as D
import ui

st.set_page_config(page_title="Finca El Roble · Hato lechero", page_icon="🐄", layout="wide")
ui.estilo()

PAGINAS = [
    st.Page("paginas/inicio.py", title="Inicio", icon="🏠", default=True),
    st.Page("paginas/hato.py", title="Hato", icon="🐄"),
    st.Page("paginas/leche.py", title="Leche", icon="🥛"),
    st.Page("paginas/registros.py", title="Registros", icon="📋"),
    st.Page("paginas/potreros_sanidad.py", title="Potreros y sanidad", icon="🌿"),
]
pagina = st.navigation(PAGINAS)


def _buscar():
    texto = st.session_state.get("busq_global", "").strip()
    if texto:
        st.session_state["ir_busqueda"] = texto
        st.session_state["_ir_hato"] = True
    st.session_state["busq_global"] = ""


# Encabezado fijo en todas las páginas: nombre de la finca y buscador de animales
izq, der = st.columns([3, 2], vertical_alignment="center")
izq.markdown(f"#### 🐄 Finca El Roble (demo) <span class='sub'>· datos al {D.fecha_corta(D.hoy())}</span>",
             unsafe_allow_html=True)
der.text_input("Buscar animal", key="busq_global", on_change=_buscar, label_visibility="collapsed",
               placeholder="🔍 Buscar animal: número, nombre o alias (Enter)")
if st.session_state.pop("_ir_hato", False):
    st.switch_page("paginas/hato.py")

with st.sidebar:
    st.caption("Datos de demostración: animales, nombres, precios y productos son ficticios.")

pagina.run()

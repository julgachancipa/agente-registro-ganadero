import json
from datetime import timedelta

import pandas as pd
import streamlit as st

import datos as D

h = D.hoy()
st.header("Registros")
st.caption("Historial de todo lo que se ha reportado. Los registros no se editan: una corrección anula el "
           "evento errado y crea el correcto.")

if "ir_estado" in st.session_state:
    st.session_state["reg_estado"] = st.session_state.pop("ir_estado")

ev = D.q("""SELECT e.id, e.fecha, e.tipo, e.datos, e.estado, e.motivo_anulacion, e.anulado_por,
                   p.nombre AS potrero, u.nombre AS reporto,
                   (SELECT COUNT(*) FROM eventos_animales WHERE evento_id = e.id) AS n_animales,
                   (SELECT group_concat(a.numero, ', ') FROM eventos_animales ea
                      JOIN animales a ON a.id = ea.animal_id WHERE ea.evento_id = e.id) AS animales
            FROM eventos e LEFT JOIN potreros p ON p.id = e.potrero_id
            LEFT JOIN usuarios u ON u.id = e.reportado_por
            ORDER BY e.fecha DESC, e.id DESC""")

pend = ev[ev.estado == "pendiente"]
if not pend.empty:
    st.warning(f"Hay {len(pend)} registro(s) por confirmar. Mientras no se confirmen no afectan el estado del hato.",
               icon="⏳")

c1, c2 = st.columns([3, 2])
primera = pd.Timestamp(ev.fecha.min()).date()
rango = c1.date_input("Fechas", value=(primera, h), min_value=primera, max_value=h, format="DD/MM/YYYY")
st.session_state.setdefault("reg_estado", "Todos")
estado = c2.segmented_control("Estado", ["Todos", "Confirmados", "Anulados", "Pendientes"],
                              key="reg_estado") or "Todos"
c3, c4 = st.columns([3, 2])
tipos = c3.multiselect("Tipo de registro", list(D.ICONO_TIPO), format_func=lambda t: D.ICONO_TIPO[t],
                       placeholder="Todos")
animal = c4.text_input("Animal", placeholder="Número, nombre o alias")

if len(rango) != 2:
    st.info("Elige también la fecha final del rango.")
    st.stop()
f = ev[(ev.fecha >= str(rango[0])) & (ev.fecha <= str(rango[1]))]
if tipos:
    f = f[f.tipo.isin(tipos)]
if estado != "Todos":
    f = f[f.estado == {"Confirmados": "confirmado", "Anulados": "anulado", "Pendientes": "pendiente"}[estado]]
if animal.strip():
    ids = D.buscar(D.todos_animales(), animal)["animal_id"].astype(int).tolist()
    if ids:
        marcas = ",".join("?" * len(ids))
        evs = D.q(f"SELECT DISTINCT evento_id FROM eventos_animales WHERE animal_id IN ({marcas})", tuple(ids))
        f = f[f.id.isin(evs.evento_id)]
    else:
        f = f.iloc[0:0]


def animales_txt(r) -> str:
    return f"{r.n_animales} animales" if r.n_animales > 6 else (r.animales or "—")


def detalle(r) -> str:
    txt = D.describir_evento(r.tipo, json.loads(r.datos))
    if r.estado == "anulado":
        txt += f" — {r.motivo_anulacion}" if r.motivo_anulacion else ""
        txt += f" (corregido por el registro #{int(r.anulado_por)})" if pd.notna(r.anulado_por) else ""
    return txt


ETIQUETA = {"confirmado": "✅ Confirmado", "anulado": "↩️ Anulado", "pendiente": "⏳ Por confirmar"}
st.caption(f"{len(f)} registros" + ("" if len(f) else " · prueba ampliar las fechas o quitar algún filtro"))
tabla = pd.DataFrame({
    "#": f.id.values, "Fecha": [D.fecha_corta(x) for x in f.fecha],
    "Tipo": [D.ICONO_TIPO[t] for t in f.tipo], "Animales": [animales_txt(r) for r in f.itertuples()],
    "Detalle": [detalle(r) for r in f.itertuples()],
    "Reportó": f.reporto.fillna("—").values, "Estado": [ETIQUETA[e] for e in f.estado]})
st.dataframe(tabla, hide_index=True, width="stretch", height=520,
             column_config={"Detalle": st.column_config.TextColumn(width="large")})
st.download_button("⬇️ Descargar estos registros (CSV)", tabla.to_csv(index=False).encode("utf-8"),
                   file_name="registros.csv", mime="text/csv")

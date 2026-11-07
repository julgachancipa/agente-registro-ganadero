from datetime import timedelta

import pandas as pd
import streamlit as st

import datos as D
import ui

h = D.hoy()
ayer = h - timedelta(days=1)
act = D.animales_df()

st.header("Inicio")

# ------------------------------------------------------------------ producción
fin = D.q("""SELECT fecha, litros_total, vacas_ordenadas FROM produccion_finca_diaria
             WHERE fecha BETWEEN ? AND ? ORDER BY fecha""", (str(h - timedelta(days=45)), str(ayer)))
fin["fecha"] = pd.to_datetime(fin["fecha"])
litros_ayer = float(fin.loc[fin.fecha == pd.Timestamp(ayer), "litros_total"].sum())
prev30 = fin[(fin.fecha < pd.Timestamp(ayer)) & (fin.fecha >= pd.Timestamp(ayer) - pd.Timedelta(days=30))]
prom30 = float(prev30["litros_total"].mean()) if len(prev30) else 0.0


def litros_manana(dia):
    r = D.q("SELECT SUM(litros) AS l FROM produccion_leche WHERE fecha = ? AND ordeno = 'manana'", (str(dia),))
    return float(r.iloc[0, 0] or 0)


man_hoy, man_ayer = litros_manana(h), litros_manana(ayer)
hay_tarde_hoy = int(D.q("SELECT COUNT(*) AS n FROM produccion_leche WHERE fecha = ? AND ordeno = 'tarde'",
                        (str(h),)).iloc[0, 0]) > 0

vacas = act[act.categoria == "vaca"]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Litros ayer", f"{litros_ayer:,.0f} L".replace(",", "."), border=True,
          delta=f"{(litros_ayer / prom30 - 1) * 100:+.1f}% vs. prom. 30 d" if prom30 else None)
c2.metric("Mañana de hoy", f"{man_hoy:,.0f} L".replace(",", "."), border=True,
          delta=f"{(man_hoy / man_ayer - 1) * 100:+.1f}% vs. ayer" if man_ayer else None)
c3.metric("Vacas en lactancia", int((vacas.estado_productivo == "lactando").sum()), border=True)
c4.metric("Vacas secas", int((vacas.estado_productivo == "seca").sum()), border=True)
c5.metric("Preñadas", int((act.estado_reproductivo == "prenada").sum()), border=True)
st.caption("Preñadas incluye vacas y novillas. " + ("" if hay_tarde_hoy else "El ordeño de la tarde de hoy todavía no está registrado."))

# ------------------------------------------------------------------ alertas
camp = D.campana_aftosa()
n_pend = int(D.q("SELECT COUNT(*) AS n FROM eventos WHERE estado = 'pendiente'").iloc[0, 0])
abiertas150 = D.aplicar_filtro(act, "Abiertas +150")
proximas = D.aplicar_filtro(act, "Por parir")
retiro = D.aplicar_filtro(act, "En retiro")

ALERTAS = [
    ("📅", "Vacas abiertas +150 días", len(abiertas150), "Sin preñez confirmada", "Hato", "Abiertas +150"),
    ("🍼", "Próximas a parir", len(proximas), "En los próximos 45 días", "Hato", "Por parir"),
    ("🚫", "Leche en retiro", len(retiro), "No va al tanque", "Hato", "En retiro"),
    ("💉", "Vacuna de aftosa pendiente", len(camp["pendientes"]) if camp["en_curso"] else 0,
     "Campaña en curso" if camp["en_curso"] else "Sin campaña en curso", "Sanidad", None),
    ("⏳", "Registros por confirmar", n_pend, "Esperan confirmación", "Registros", "Pendientes"),
]
st.subheader("Requiere atención")
cols = st.columns(len(ALERTAS))
for col, (icono, titulo, n, sub, destino, valor) in zip(cols, ALERTAS):
    with col.container(border=True):
        st.markdown(f"<p class='alerta-titulo'>{icono} {titulo}</p><div class='cifra'>{n}</div>"
                    f"<div class='sub'>{sub}</div>", unsafe_allow_html=True)
        if st.button("Ver", key=f"ver_{titulo}", disabled=(n == 0), width="stretch"):
            if destino == "Hato":
                st.session_state["ir_filtro"] = valor
                st.switch_page("paginas/hato.py")
            elif destino == "Sanidad":
                st.session_state["ir_vista"] = "Sanidad"
                st.switch_page("paginas/potreros_sanidad.py")
            else:
                st.session_state["ir_estado"] = valor
                st.switch_page("paginas/registros.py")

# ------------------------------------------------------------------ gráfica y próximos partos
izq, der = st.columns([3, 2])
with izq:
    st.subheader("Producción de los últimos 30 días")
    ult = fin[fin.fecha >= pd.Timestamp(ayer) - pd.Timedelta(days=29)][["fecha", "litros_total"]]
    ult = ult.rename(columns={"litros_total": "Litros de la finca"})
    ui.mostrar(ui.grafica_series(ult, "fecha", ["Litros de la finca"], [ui.AZUL], "Litros por día",
                                 alto=300, dias=30))
    with st.expander("Ver tabla"):
        st.dataframe(ult.assign(fecha=ult.fecha.dt.strftime("%d/%m/%Y")), hide_index=True, width="stretch")
with der:
    st.subheader("Próximos partos")
    if proximas.empty:
        st.info("No hay partos estimados en los próximos 45 días.")
    else:
        t = proximas.sort_values("dias_para_parto")
        st.dataframe(
            pd.DataFrame({"N°": t.numero, "Nombre": t.nombre.fillna(""),
                          "Fecha estimada": [D.fecha_corta(x) for x in t.fecha_probable_parto],
                          "En (días)": t.dias_para_parto.astype(int)}),
            hide_index=True, width="stretch", height=min(40 + 35 * len(t), 380))

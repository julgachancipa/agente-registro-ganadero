from datetime import timedelta

import pandas as pd
import streamlit as st

import datos as D
import ui

h = D.hoy()
ayer = h - timedelta(days=1)
act = D.animales_df()

st.header("Leche")
st.caption("No incluye el día de hoy, porque falta el ordeño de la tarde.")

PERIODOS = {"30 días": 30, "90 días": 90, "1 año": 365, "Todo": None}
periodo = st.segmented_control("Período", list(PERIODOS), default="90 días", key="leche_periodo") or "90 días"
dias = PERIODOS[periodo]
desde = ayer - timedelta(days=dias - 1) if dias else pd.Timestamp("2023-11-07").date()

# ------------------------------------------------------------------ finca por ordeño
pr = D.q("""SELECT fecha, ordeno, SUM(litros) AS litros, COUNT(DISTINCT animal_id) AS vacas
            FROM produccion_leche WHERE fecha BETWEEN ? AND ? GROUP BY fecha, ordeno""",
         (str(desde), str(ayer)))
if pr.empty:
    st.info("No hay producción registrada en este período.")
    st.stop()
ancho = pr.pivot(index="fecha", columns="ordeno", values="litros").rename(
    columns={"manana": "Mañana", "tarde": "Tarde"}).reset_index()
ancho["Total"] = ancho["Mañana"].fillna(0) + ancho["Tarde"].fillna(0)
ancho["Vacas"] = pr.groupby("fecha")["vacas"].max().values
ancho["fecha"] = pd.to_datetime(ancho["fecha"])

dest = D.q("""SELECT destino, SUM(litros) AS litros FROM produccion_leche
              WHERE fecha BETWEEN ? AND ? GROUP BY destino""", (str(desde), str(ayer))).set_index("destino")["litros"]
no_tanque = float(dest.get("descarte", 0) + dest.get("calostro", 0))

k = st.columns(5)
k[0].metric("Promedio diario", f"{ancho['Total'].mean():,.0f} L".replace(",", "."), border=True)
k[1].metric("Vacas ordeñadas por día", f"{ancho['Vacas'].mean():.1f}", border=True)
k[2].metric("Litros por vaca y día", f"{(ancho['Total'] / ancho['Vacas']).mean():.1f} L", border=True)
k[3].metric("Parte de la mañana", f"{ancho['Mañana'].sum() / ancho['Total'].sum() * 100:.0f}%", border=True,
            help="Qué porcentaje de los litros se saca en el ordeño de la mañana.")
k[4].metric("Fuera del tanque", f"{no_tanque:,.0f} L".replace(",", "."), border=True,
            help="Calostro y leche en retiro por tratamiento.")

serie = ancho[["fecha", "Mañana", "Tarde", "Total"]]
if len(serie) > 200:  # períodos largos: promedio semanal para que se lea
    serie = serie.set_index("fecha").resample("W").mean().reset_index()
    st.subheader("Litros por día · promedio semanal")
else:
    st.subheader("Litros por día")
ui.mostrar(ui.grafica_series(serie, "fecha", ["Mañana", "Tarde"], [ui.AZUL, ui.NARANJA], "Litros por ordeño",
                             alto=320, dias=dias, extras_tooltip=("Total",)))
with st.expander("Ver tabla"):
    st.dataframe(serie.assign(fecha=serie.fecha.dt.strftime("%d/%m/%Y")).round(1), hide_index=True, width="stretch")

# ------------------------------------------------------------------ vacas: ranking y comparación
st.subheader("Vacas en lactancia")
rec = D.q("""SELECT animal_id, fecha, litros_total FROM produccion_diaria
             WHERE fecha BETWEEN ? AND ?""", (str(ayer - timedelta(days=59)), str(ayer)))
lact = act[act.estado_productivo == "lactando"][["animal_id", "numero", "nombre", "etiqueta", "dias_en_leche"]]
cur = rec.merge(lact, on="animal_id")
r7 = cur[cur.fecha >= str(ayer - timedelta(days=6))].groupby("animal_id")["litros_total"].mean()
r30 = cur[cur.fecha >= str(ayer - timedelta(days=29))].groupby("animal_id")["litros_total"].mean()
rank = lact.set_index("animal_id").join(r7.rename("l7")).join(r30.rename("l30")).dropna(subset=["l7"])
rank = rank.sort_values("l7", ascending=False)
prom_hato = rank["l7"].mean()
rank["vs"] = (rank["l7"] / prom_hato - 1) * 100

izq, der = st.columns([6, 6], gap="large")
with izq:
    st.caption("Ordenadas por promedio de los últimos 7 días")
    st.dataframe(pd.DataFrame({
        "N°": rank.numero.values, "Nombre": rank.nombre.fillna("").values,
        "Días en leche": rank.dias_en_leche.astype(int).values,
        "L/día (7 d)": rank.l7.round(1).values, "vs. hato": rank.vs.round(0).values}),
        hide_index=True, width="stretch", height=430,
        column_config={"L/día (7 d)": st.column_config.ProgressColumn(
            "L/día (7 d)", min_value=0, max_value=float(rank.l7.max()) * 1.05, format="%.1f"),
            "vs. hato": st.column_config.NumberColumn("vs. hato", format="%+.0f%%")})
with der:
    sel = st.selectbox("Comparar una vaca con el promedio del hato (últimos 60 días)", rank.etiqueta.tolist(),
                       key="leche_vaca")
    aid = int(rank[rank.etiqueta == sel].index[0])
    mia = rec[rec.animal_id == aid][["fecha", "litros_total"]].rename(columns={"litros_total": sel})
    hato = D.q("""SELECT fecha, AVG(litros_total) AS "Promedio del hato" FROM produccion_diaria
                  WHERE fecha BETWEEN ? AND ? GROUP BY fecha""", (str(ayer - timedelta(days=59)), str(ayer)))
    comp = hato.merge(mia, on="fecha", how="left")
    comp["fecha"] = pd.to_datetime(comp["fecha"])
    ui.mostrar(ui.grafica_series(comp, "fecha", [sel, "Promedio del hato"], [ui.AZUL, ui.GRIS], "Litros por día",
                                 alto=330, dias=60, discontinuas=("Promedio del hato",)))

# ------------------------------------------------------------------ retiro y descarga
st.subheader("Leche en retiro")
ret = act[act.retiro_leche_hasta.notna()]
if ret.empty:
    st.success("Ninguna vaca tiene leche en retiro.")
else:
    st.warning("La leche de estas vacas no puede ir al tanque mientras dure el retiro.", icon="🚫")
    st.dataframe(pd.DataFrame({
        "Animal": ret.etiqueta.values, "Retiro hasta": [D.fecha_corta(x) for x in ret.retiro_leche_hasta],
        "Días restantes": [(pd.Timestamp(x).date() - h).days for x in ret.retiro_leche_hasta]}),
        hide_index=True, width="stretch")

csv = D.q("""SELECT p.fecha, a.numero AS animal, a.nombre, p.ordeno, p.litros, p.destino
             FROM produccion_leche p JOIN animales a ON a.id = p.animal_id
             WHERE p.fecha BETWEEN ? AND ? ORDER BY p.fecha, a.numero""", (str(desde), str(ayer))
         ).to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Descargar litros por vaca y ordeño (CSV)", csv, file_name="produccion_leche.csv",
                   mime="text/csv")

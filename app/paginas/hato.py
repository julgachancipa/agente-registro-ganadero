import json

import pandas as pd
import streamlit as st

import datos as D
import ui

st.header("Hato")

# Llegadas desde otras páginas (alertas del Inicio o buscador de arriba)
if "ir_busqueda" in st.session_state:
    st.session_state["hato_q"] = st.session_state.pop("ir_busqueda")
    st.session_state["hato_filtro"] = "Todos"
if "ir_filtro" in st.session_state:
    st.session_state["hato_filtro"] = st.session_state.pop("ir_filtro")
    st.session_state["hato_q"] = ""

h = D.hoy()
act = D.animales_df()

st.session_state.setdefault("hato_filtro", "Todos")
filtro = st.segmented_control("Mostrar", D.FILTROS_HATO, key="hato_filtro") or "Todos"
texto = st.session_state.get("hato_q", "")

df = D.aplicar_filtro(act, filtro)
if texto.strip():
    df = D.buscar(df, texto)
else:
    clave = {"Abiertas": ("dias_abiertos", False), "Abiertas +150": ("dias_abiertos", False),
             "Por parir": ("dias_para_parto", True), "Preñadas": ("dias_para_parto", True)}
    if filtro in clave:
        df = df.sort_values(clave[filtro][0], ascending=clave[filtro][1])
    else:
        orden = {"vaca": 0, "novilla": 2, "ternera": 3, "ternero": 3, "toro": 4}
        df = df.assign(_o=df.categoria.map(orden) + (df.estado_productivo == "seca") * 1,
                       _n=pd.to_numeric(df.numero, errors="coerce")).sort_values(["_o", "_n"])

izq, der = st.columns([5, 7], gap="large")


def detalle_lista(r) -> str:
    if filtro in ("Abiertas", "Abiertas +150") and pd.notna(r.dias_abiertos):
        return f"{int(r.dias_abiertos)} días abierta"
    if r.estado_reproductivo == "prenada" and pd.notna(r.dias_para_parto):
        return f"Parto en {int(r.dias_para_parto)} d"
    if r.estado_productivo == "lactando" and pd.notna(r.dias_en_leche):
        return f"{int(r.dias_en_leche)} d en leche"
    return D.edad_txt(r.edad_dias)


with izq:
    st.text_input("Buscar en el hato", key="hato_q", placeholder="Número, nombre, alias o descripción")
    if df.empty:
        st.info("Ningún animal coincide con ese filtro o búsqueda.")
        evento = None
    else:
        tabla = pd.DataFrame({"N°": df.numero.values, "Nombre": df.nombre.fillna("").values,
                              "Estado": df.estado_txt.values, "Detalle": [detalle_lista(r) for r in df.itertuples()]})
        st.caption(f"{len(df)} animales · marca la casilla de una fila para ver su ficha")
        evento = st.dataframe(tabla, hide_index=True, width="stretch", height=min(560, 42 + 35 * len(tabla)), key="hato_tabla",
                              on_select="rerun", selection_mode="single-row")

if evento is not None and evento.selection.rows:
    st.session_state["animal_sel"] = int(df.iloc[evento.selection.rows[0]].animal_id)

# ------------------------------------------------------------------ ficha
with der:
    sel = st.session_state.get("animal_sel")
    if sel is None and not df.empty:
        sel = int(df.iloc[0].animal_id)
    fila = act[act.animal_id == sel]
    if fila.empty:
        st.info("Selecciona un animal de la lista para ver su ficha.")
        st.stop()
    a = fila.iloc[0]
    todos = D.todos_animales().set_index("animal_id")

    st.subheader(f"#{a.numero}" + (f" · {a.nombre}" if pd.notna(a.nombre) else ""))
    chips = [ui.insignia(D.CATEGORIA.get(a.categoria, a.categoria), "azul"), ui.insignia(a.raza)]
    if a.categoria == "vaca":
        chips.append(ui.insignia("Lactando" if a.estado_productivo == "lactando" else "Seca",
                                 "verde" if a.estado_productivo == "lactando" else "neutro"))
    if pd.notna(a.estado_reproductivo):
        chips.append(ui.insignia(D.REPRO[a.estado_reproductivo].capitalize(),
                                 "verde" if a.estado_reproductivo == "prenada" else "ambar"))
    if pd.notna(a.retiro_leche_hasta):
        chips.append(ui.insignia(f"🚫 Retiro de leche hasta {D.fecha_corta(a.retiro_leche_hasta)}", "rojo"))
    if pd.notna(a.potrero):
        chips.append(ui.insignia(f"📍 {a.potrero}"))
    st.markdown("".join(chips), unsafe_allow_html=True)

    metricas = [("Edad", D.edad_txt(a.edad_dias))]
    if pd.notna(a.dias_en_leche):
        metricas.append(("Días en leche", int(a.dias_en_leche)))
    if a.estado_reproductivo == "prenada" and pd.notna(a.fecha_probable_parto):
        metricas.append(("Parto estimado", D.fecha_corta(a.fecha_probable_parto)))
    elif pd.notna(a.dias_abiertos) and a.categoria == "vaca":
        metricas.append(("Días abiertos", int(a.dias_abiertos)))
    if pd.notna(a.peso_kg):
        metricas.append(("Último peso", f"{a.peso_kg:.0f} kg"))
    ui.tarjetas(metricas)

    # Genealogía
    partes = []
    if pd.notna(a.madre_id) and int(a.madre_id) in todos.index:
        partes.append("**Madre:** " + todos.loc[int(a.madre_id), "etiqueta"])
    if pd.notna(a.pajilla):
        partes.append(f"**Padre:** pajilla {a.pajilla}")
    hijos = todos[todos.madre_id == a.animal_id].sort_values("fecha_nacimiento")
    if len(hijos):
        partes.append("**Crías:** " + ", ".join(
            f"{r.numero} ({'H' if r.sexo == 'H' else 'M'}, {D.fecha_corta(r.fecha_nacimiento)})"
            for r in hijos.itertuples()))
    if pd.notna(a.descripcion):
        partes.append(f"**Señas:** {a.descripcion}")
    if pd.notna(a.alias):
        partes.append(f"**También le dicen:** {a.alias.replace(' | ', ', ')}")
    if partes:
        st.markdown("  \n".join(partes))

    # Eventos del animal
    ev = D.q("""SELECT e.id, e.fecha, e.tipo, e.datos, e.estado, e.motivo_anulacion, p.nombre AS potrero,
                       u.nombre AS reporto
                FROM eventos e JOIN eventos_animales ea ON ea.evento_id = e.id
                LEFT JOIN potreros p ON p.id = e.potrero_id
                LEFT JOIN usuarios u ON u.id = e.reportado_por
                WHERE ea.animal_id = ? ORDER BY e.fecha DESC, e.id DESC""", (int(a.animal_id),))
    ev["detalle"] = [D.describir_evento(t, json.loads(d)) for t, d in zip(ev.tipo, ev.datos)]

    t_hist, t_prod, t_repro = st.tabs(["Historia", "Producción", "Reproducción"])

    with t_hist:
        if ev.empty:
            st.info("Sin eventos registrados.")
        else:
            vista = ev[ev.tipo != "traslado"] if st.toggle("Ocultar traslados de potrero", value=True,
                                                            key="hato_sin_traslados") else ev
            estados = {"confirmado": "", "anulado": "↩️ Anulado", "pendiente": "⏳ Por confirmar"}
            st.dataframe(pd.DataFrame({
                "Fecha": [D.fecha_corta(x) for x in vista.fecha],
                "Evento": [D.ICONO_TIPO.get(t, t) for t in vista.tipo],
                "Detalle": [d + (f" ({m})" if isinstance(m, str) and m else "")
                            for d, m in zip(vista.detalle, vista.motivo_anulacion)],
                "Estado": [estados[e] for e in vista.estado]}),
                hide_index=True, width="stretch", height=380,
                column_config={"Detalle": st.column_config.TextColumn(width="large")})

    with t_prod:
        if a.categoria not in ("vaca",) or pd.isna(a.ultimo_parto):
            st.info("Este animal todavía no está en producción.")
        else:
            prod = D.q("""SELECT fecha, ordeno, litros, destino FROM produccion_leche
                          WHERE animal_id = ? AND fecha >= ? AND fecha < ? ORDER BY fecha""",
                       (int(a.animal_id), a.ultimo_parto, str(h)))
            if prod.empty:
                st.info("Sin ordeños registrados en esta lactancia.")
            else:
                prod["fecha"] = pd.to_datetime(prod["fecha"])
                ancho = prod.pivot_table(index="fecha", columns="ordeno", values="litros", aggfunc="sum").reset_index()
                ancho = ancho.rename(columns={"manana": "Mañana", "tarde": "Tarde"}).fillna(0)
                ancho["Total"] = ancho["Mañana"] + ancho["Tarde"]
                ancho["Días en leche"] = (ancho["fecha"] - pd.Timestamp(a.ultimo_parto)).dt.days
                ui.tarjetas([("Promedio últimos 7 días", f"{ancho['Total'].tail(7).mean():.1f} L/día"),
                             ("Pico de la lactancia", f"{ancho['Total'].max():.1f} L/día"),
                             ("Total de la lactancia", f"{ancho['Total'].sum():,.0f} L".replace(",", "."))])
                st.caption(("Lactancia actual" if a.estado_productivo == "lactando" else "Última lactancia (ya secada)")
                           + f" · parto el {D.fecha_corta(a.ultimo_parto)}")
                ui.mostrar(ui.grafica_series(
                    ancho[["Días en leche", "Mañana", "Tarde", "Total"]], "Días en leche", ["Mañana", "Tarde"],
                    [ui.AZUL, ui.NARANJA], "Litros por ordeño", alto=280, x_tipo="Q", x_titulo="Días en leche",
                    extras_tooltip=("Total",)))
                desc = prod[prod.destino != "tanque"].litros.sum()
                if desc > 0:
                    st.caption(f"Litros que no fueron al tanque (calostro o retiro por tratamiento): {desc:.0f} L")

    with t_repro:
        partos = ev[(ev.tipo == "parto") & (ev.estado == "confirmado")].sort_values("fecha")
        if partos.empty:
            st.info("Sin partos registrados.")
        else:
            fechas = pd.to_datetime(partos.fecha)
            st.dataframe(pd.DataFrame({
                "Fecha": [D.fecha_corta(x) for x in partos.fecha], "Resultado": partos.detalle.values,
                "Días desde el parto anterior": fechas.diff().dt.days.astype("Int64").values}),
                hide_index=True, width="stretch")
        ciclo = ev[ev.tipo.isin(["servicio", "palpacion", "secado"]) & (ev.estado == "confirmado")]
        if pd.notna(a.ultimo_parto):
            ciclo = ciclo[ciclo.fecha >= a.ultimo_parto]
        if not ciclo.empty:
            st.markdown("**Desde el último parto**")
            st.dataframe(pd.DataFrame({
                "Fecha": [D.fecha_corta(x) for x in ciclo.fecha],
                "Evento": [D.ICONO_TIPO[t] for t in ciclo.tipo], "Detalle": ciclo.detalle.values}),
                hide_index=True, width="stretch")

import json

import pandas as pd
import streamlit as st

import datos as D
import ui

st.header("Potreros y sanidad")

SINGULAR = {"Vacas lactando": "vaca lactando", "Vacas secas": "vaca seca", "Novillas": "novilla",
            "Terneras": "ternera", "Terneros": "ternero", "Toro": "toro"}


def hace(dias) -> str:
    dias = int(dias)
    return "hoy" if dias == 0 else ("ayer" if dias == 1 else f"hace {dias} días")

if "ir_vista" in st.session_state:
    st.session_state["ps_vista"] = st.session_state.pop("ir_vista")
st.session_state.setdefault("ps_vista", "Potreros")
vista = st.segmented_control("Ver", ["Potreros", "Sanidad"], key="ps_vista") or "Potreros"

# ================================================================== POTREROS
if vista == "Potreros":
    pot = D.potreros_df()
    st.caption("Ocupación actual de cada potrero. Un potrero vacío muestra cuántos días lleva en descanso.")
    for fila in range(0, len(pot), 4):
        cols = st.columns(4)
        for col, p in zip(cols, pot.iloc[fila:fila + 4].itertuples()):
            with col.container(border=True):
                st.markdown(f"**{p.nombre}**  \n<span class='sub'>{p.area_ha:g} ha</span>", unsafe_allow_html=True)
                if p.animales == 0:
                    chips = ui.insignia("Vacío", "neutro")
                    if p.dias_descanso is not None:
                        chips += ui.insignia("En descanso desde " + hace(p.dias_descanso), "verde")
                    st.markdown(chips, unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='cifra'>{p.animales}</div><div class='sub'>animales · "
                                f"{p.carga:.1f} por ha</div>", unsafe_allow_html=True)
                    st.markdown("".join(ui.insignia(f"{n} {g.lower() if n != 1 else SINGULAR.get(g, g.lower())}")
                                        for g, n in p.composicion.items()),
                                unsafe_allow_html=True)
                    if p.dias_ingreso is not None:
                        st.caption("Último ingreso: " + hace(p.dias_ingreso))
                    with st.expander("Ver animales"):
                        d = p.detalle.sort_values("grupo")
                        st.dataframe(pd.DataFrame({"N°": d.numero.values, "Nombre": d.nombre.fillna("").values,
                                                   "Grupo": d.grupo.values}), hide_index=True, width="stretch")

# ================================================================== SANIDAD
else:
    camp = D.campana_aftosa()
    st.subheader("Vacunación contra aftosa")
    if camp["en_curso"]:
        total, hechos = camp["elegibles"], camp["aplicados"]
        st.progress(hechos / total if total else 0,
                    text=f"Campaña iniciada el {D.fecha_corta(camp['inicio'])}: {hechos} de {total} animales vacunados")
        pend = camp["pendientes"].sort_values("numero")
        if pend.empty:
            st.success("Todos los animales de la campaña ya están vacunados.")
        else:
            st.warning(f"Faltan {len(pend)} animales por vacunar (mayores de 3 meses).", icon="💉")
            st.dataframe(pd.DataFrame({"N°": pend.numero.values, "Nombre": pend.nombre.fillna("").values,
                                       "Categoría": [D.CATEGORIA[c] for c in pend.categoria],
                                       "Edad": [D.edad_txt(x) for x in pend.edad_dias],
                                       "Potrero": pend.potrero.fillna("—").values}),
                         hide_index=True, width="stretch", height=min(40 + 35 * len(pend), 420))
    else:
        st.info(f"No hay una campaña en curso. La última fue el {D.fecha_corta(camp['ultima'])}.")

    # Historial de aplicaciones: campañas (varios animales) y tratamientos individuales
    ap = D.q("""SELECT e.id, e.fecha, e.datos, COUNT(*) AS n
                FROM eventos e JOIN eventos_animales ea ON ea.evento_id = e.id
                WHERE e.estado = 'confirmado' AND e.tipo = 'tratamiento'
                GROUP BY e.id ORDER BY e.fecha DESC, e.id DESC""")
    ap["d"] = [json.loads(x) for x in ap.datos]
    ap["producto"] = [d.get("producto", "—") for d in ap.d]
    ap["diagnostico"] = [d.get("diagnostico") for d in ap.d]

    grupos = ap[ap.n >= 10].copy()
    grupos["fecha"] = pd.to_datetime(grupos["fecha"])
    grupos = grupos.sort_values(["producto", "fecha"])
    nuevo = (grupos.groupby("producto")["fecha"].diff().dt.days.fillna(99) > 3)
    grupos["campana"] = nuevo.cumsum()
    camp_df = (grupos.groupby("campana").agg(producto=("producto", "first"), desde=("fecha", "min"),
                                             hasta=("fecha", "max"), n=("n", "sum"))
               .sort_values("desde", ascending=False))
    st.subheader("Campañas anteriores")
    st.caption("Una campaña que se aplicó en varios días seguidos aparece en una sola fila.")
    st.dataframe(pd.DataFrame({
        "Fecha": [D.fecha_corta(a) if a == b else f"{D.fecha_corta(a)} – {D.fecha_corta(b)}"
                  for a, b in zip(camp_df.desde, camp_df.hasta)],
        "Producto": camp_df.producto.values, "Animales tratados": camp_df.n.values.astype(int)}),
        hide_index=True, width="stretch", height=300)

    ind = ap[ap.n < 10].head(15)
    st.subheader("Tratamientos individuales recientes")
    nombres = D.q("""SELECT ea.evento_id, group_concat(a.numero, ', ') AS animales
                     FROM eventos_animales ea JOIN animales a ON a.id = ea.animal_id GROUP BY ea.evento_id""")
    ind = ind.merge(nombres, left_on="id", right_on="evento_id", how="left")
    st.dataframe(pd.DataFrame({
        "Fecha": [D.fecha_corta(x) for x in ind.fecha], "Animal(es)": ind.animales.values,
        "Detalle": [D.describir_evento("tratamiento", d) for d in ind.d]}),
        hide_index=True, width="stretch")

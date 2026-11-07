"""Estilo y gráficas compartidas (paleta validada: azul / naranja, ver docs)."""
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

AZUL, NARANJA = "#2a78d6", "#eb6834"   # series 1 y 2 (validadas con validate_palette.js)
GRIS = "#8a8984"                        # referencia (siempre con línea discontinua)
TEXTO, TEXTO2, REJILLA, SUPERFICIE = "#0b0b0b", "#52514e", "#ececea", "#fcfcfb"

CSS = """
.block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1400px;}
h1, h2, h3 {letter-spacing: -0.01em;}
.cifra {font-size: 2.3rem; font-weight: 650; line-height: 1.1; margin: .1rem 0 .1rem 0;}
.alerta-titulo {font-size: .95rem; font-weight: 600; margin: 0;}
.sub {color: #52514e; font-size: .85rem;}
.insignia {display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .8rem;
           font-weight: 550; margin: 0 6px 6px 0;}
.i-neutro {background: #ecebe7; color: #3a3935;}
.i-azul {background: #e1edfb; color: #184f95;}
.i-verde {background: #e0f1e0; color: #0b5e0b;}
.i-ambar {background: #fdefc9; color: #7a5300;}
.i-rojo {background: #fbe1e1; color: #9c2424;}
.kpis {display: grid; grid-template-columns: repeat(auto-fit, minmax(112px, 1fr)); gap: .6rem; margin: .4rem 0 .9rem;}
.kpi {border: 1px solid rgba(49,51,63,.2); border-radius: .5rem; padding: .55rem .8rem;}
.kpi-l {font-size: .8rem; color: #52514e;}
.kpi-v {font-size: 1.4rem; font-weight: 600; line-height: 1.25;}
"""


def estilo() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def insignia(texto: str, tono: str = "neutro") -> str:
    return f"<span class='insignia i-{tono}'>{texto}</span>"


def tarjetas(items: list[tuple[str, object]]) -> None:
    """Fila de indicadores compactos que no cortan el texto."""
    html = "".join(f"<div class='kpi'><div class='kpi-l'>{e}</div><div class='kpi-v'>{v}</div></div>"
                   for e, v in items)
    st.markdown(f"<div class='kpis'>{html}</div>", unsafe_allow_html=True)


def eje_x(dias: int | None, tipo: str = "T", titulo: str | None = None) -> alt.X:
    if tipo == "Q":
        return alt.X(shorthand="x:Q", axis=alt.Axis(grid=False, title=titulo), title=titulo)
    meses = "['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']"
    if dias is not None and dias <= 150:
        expr = f"date(datum.value) + ' ' + {meses}[month(datum.value)]"
    else:
        expr = f"{meses}[month(datum.value)] + ' ' + year(datum.value)"
    return alt.X(shorthand="x:T", axis=alt.Axis(grid=False, labelExpr=expr, title=None, labelOverlap=True),
                 title=None)


def grafica_series(wide: pd.DataFrame, x: str, series: list[str], colores: list[str], y_titulo: str,
                   alto: int = 300, dias: int | None = 90, x_tipo: str = "T", x_titulo: str | None = None,
                   discontinuas: tuple[str, ...] = (), extras_tooltip: tuple[str, ...] = (),
                   cero: bool = False, formato_x: str = "%d/%m/%Y") -> alt.Chart:
    """Líneas de 2 px con leyenda (si hay >=2 series), cruz y tooltip al pasar el mouse."""
    wide = wide.rename(columns={x: "x"})
    larga = wide.melt(id_vars=["x"], value_vars=series, var_name="serie", value_name="valor")
    leyenda = alt.Legend(title=None, orient="top", symbolType="stroke", symbolStrokeWidth=3,
                         labelColor=TEXTO, labelFontSize=12) if len(series) > 1 else None
    color = alt.Color("serie:N", scale=alt.Scale(domain=series, range=colores), legend=leyenda)
    rayas = alt.StrokeDash("serie:N", legend=None, scale=alt.Scale(
        domain=series, range=[[5, 4] if s in discontinuas else [1, 0] for s in series]))
    ex = eje_x(dias, x_tipo, x_titulo)
    y = alt.Y("valor:Q", title=y_titulo, scale=alt.Scale(zero=cero, nice=True))
    base = alt.Chart(larga).encode(x=ex)
    lineas = base.mark_line(strokeWidth=2).encode(y=y, color=color, strokeDash=rayas)
    cercano = alt.selection_point(nearest=True, on="pointerover", fields=["x"], empty=False,
                                  clear="pointerout")
    selector = alt.Chart(wide).mark_point(opacity=0).encode(
        x=alt.X(shorthand=f"x:{x_tipo}")).add_params(cercano)
    puntos = base.mark_point(filled=True, size=70, stroke=SUPERFICIE, strokeWidth=2).encode(
        y="valor:Q", color=color,
        opacity=alt.condition(cercano, alt.value(1), alt.value(0)))
    tips = [alt.Tooltip(field="x", type="temporal" if x_tipo == "T" else "quantitative",
                        title="Fecha" if x_tipo == "T" else (x_titulo or "x"),
                        **({"format": formato_x} if x_tipo == "T" else {}))]
    tips += [alt.Tooltip(field=s, type="quantitative", format=".1f") for s in list(series) + list(extras_tooltip)]
    regla = alt.Chart(wide).mark_rule(color=GRIS, strokeWidth=1).encode(
        x=alt.X(shorthand=f"x:{x_tipo}"), tooltip=tips).transform_filter(cercano)
    return (alt.layer(lineas, selector, puntos, regla).properties(height=alto)
            .configure_view(stroke=None)
            .configure_axis(gridColor=REJILLA, domain=False, tickColor=REJILLA, labelColor=TEXTO2,
                            titleColor=TEXTO2, labelFontSize=12, titleFontSize=12))


def mostrar(chart: alt.Chart) -> None:
    st.altair_chart(chart, width="stretch", theme=None)

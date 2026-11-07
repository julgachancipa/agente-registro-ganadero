"""Acceso de solo lectura a db/demo.db para la interfaz (datos y utilidades)."""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / "db" / "demo.db"

MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
REPRO = {"prenada": "preñada", "vacia": "vacía", "servida": "servida"}
CATEGORIA = {"toro": "Toro", "ternera": "Ternera", "ternero": "Ternero", "novilla": "Novilla", "vaca": "Vaca"}
ICONO_TIPO = {
    "parto": "🍼 Parto", "servicio": "🧬 Servicio", "palpacion": "🔎 Palpación", "secado": "🛑 Secado",
    "destete": "✂️ Destete", "pesaje": "⚖️ Pesaje", "tratamiento": "💊 Tratamiento",
    "traslado": "➡️ Traslado", "venta": "💰 Venta", "compra": "🛒 Compra", "muerte": "✝️ Muerte",
}
FILTROS_HATO = ["Todos", "Lactando", "Secas", "Preñadas", "Por parir", "Abiertas",
                "Abiertas +150", "Novillas", "Terneras", "En retiro", "Sin vacunar"]


# --------------------------------------------------------------------------- base de datos
def asegurar_db() -> None:
    if not DB.exists():
        subprocess.run([sys.executable, str(RAIZ / "scripts" / "cargar_demo.py")], check=True,
                       capture_output=True)


@st.cache_resource
def _con() -> sqlite3.Connection:
    asegurar_db()
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)


@st.cache_data(show_spinner=False)
def _q(sql: str, params: tuple, version: float) -> pd.DataFrame:
    return pd.read_sql_query(sql, _con(), params=params)


def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Consulta de solo lectura con caché (se invalida si db/demo.db cambia)."""
    asegurar_db()
    return _q(sql, tuple(params), DB.stat().st_mtime)


def hoy() -> date:
    return pd.Timestamp(q("SELECT fecha FROM hoy").iloc[0, 0]).date()


# --------------------------------------------------------------------------- utilidades
def normalizar(texto) -> str:
    s = unicodedata.normalize("NFD", str(texto or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


def fecha_corta(d) -> str:
    if d is None or pd.isna(d):
        return "—"
    d = pd.Timestamp(d)
    return f"{d.day} {MESES[d.month - 1]} {d.year}"


def pesos(v) -> str:
    return "$ " + f"{float(v):,.0f}".replace(",", ".")


def edad_txt(dias) -> str:
    dias = int(dias)
    if dias < 60:
        return f"{dias} días"
    if dias < 730:
        return f"{dias // 30} meses"
    return f"{dias // 365} años {(dias % 365) // 30} m"


def describir_evento(tipo: str, d: dict) -> str:
    g = d.get
    if tipo == "parto":
        r = g("resultado", "vivo")
        if r == "aborto":
            return "Aborto" + (" (%s meses de gestación)" % g("meses_gestacion") if g("meses_gestacion") else "")
        if r == "muerto":
            return "Parto con cría muerta"
        sexo = {"H": "hembra", "M": "macho"}.get(g("cria_sexo"), "")
        txt = "Parto" + (" · cría %s (%s)" % (g("cria_numero"), sexo) if g("cria_numero") else "")
        return txt + (" · " + g("nota") if g("nota") else "")
    if tipo == "servicio":
        if g("tipo") == "IA":
            return "Inseminación · pajilla %s" % g("pajilla", "—")
        return "Monta natural · toro %s" % g("toro", "—")
    if tipo == "palpacion":
        txt = "Resultado: %s" % g("resultado", "—")
        if g("meses_gestacion"):
            txt += " (%s meses)" % g("meses_gestacion")
        return txt + (" · " + g("nota") if g("nota") else "")
    if tipo == "secado":
        return "Fin de la lactancia"
    if tipo == "destete":
        return "Destete" + (" · %s kg" % g("peso_kg") if g("peso_kg") else "")
    if tipo == "pesaje":
        txt = "%s kg" % g("peso_kg")
        return txt + (" · " + g("motivo") if g("motivo") else "") + (" · " + g("alerta") if g("alerta") else "")
    if tipo == "tratamiento":
        txt = g("producto", "Tratamiento")
        if g("diagnostico"):
            txt += " · %s" % g("diagnostico")
            if g("cuarto"):
                txt += " (%s)" % g("cuarto")
        if g("retiro_leche_hasta"):
            txt += " · retiro de leche hasta %s" % fecha_corta(g("retiro_leche_hasta"))
        return txt
    if tipo == "traslado":
        return "A %s" % g("potrero_destino", "—")
    if tipo == "venta":
        txt = "Vendido a %s" % g("comprador", "—")
        if g("precio_cop"):
            txt += " · " + pesos(g("precio_cop"))
        return txt + (" · " + g("motivo") if g("motivo") else "")
    if tipo == "compra":
        return "Comprado a %s · %s" % (g("proveedor", "—"), pesos(g("precio_cop", 0)))
    if tipo == "muerte":
        return "Causa: %s" % g("causa", "—")
    return ""


# --------------------------------------------------------------------------- animales
_SQL_ACTIVOS = """
SELECT e.animal_id, e.numero, e.nombre, e.sexo, e.raza, e.edad_dias, e.categoria,
       e.estado_reproductivo, e.estado_productivo, e.ultimo_parto, e.ultimo_servicio,
       e.fecha_probable_parto, e.dias_en_leche, e.dias_abiertos, e.dias_para_parto, e.potrero,
       a.descripcion, a.origen, a.madre_id, a.padre_id, a.pajilla, a.fecha_nacimiento,
       (SELECT group_concat(alias, ' | ') FROM alias_animales WHERE animal_id = e.animal_id) AS alias,
       r.retiro_leche_hasta, pe.peso_kg, pe.fecha AS peso_fecha
FROM estado_animal e
JOIN animales a ON a.id = e.animal_id
LEFT JOIN animales_en_retiro_leche r ON r.animal_id = e.animal_id
LEFT JOIN peso_actual pe ON pe.animal_id = e.animal_id
"""


def _etiqueta(numero, nombre) -> str:
    return f"{numero} · {nombre}" if pd.notna(nombre) and nombre else str(numero)


def estado_txt(r) -> str:
    if r.categoria == "vaca":
        base = "Lactando" if r.estado_productivo == "lactando" else "Seca"
        txt = f"{base} · {REPRO.get(r.estado_reproductivo, '')}"
    elif r.categoria == "novilla":
        txt = f"Novilla · {REPRO.get(r.estado_reproductivo, '')}"
    else:
        txt = CATEGORIA.get(r.categoria, r.categoria)
    return txt + (" · 🚫 retiro de leche" if pd.notna(r.retiro_leche_hasta) else "")


def animales_df() -> pd.DataFrame:
    """Animales activos con su estado calculado (vista estado_animal)."""
    df = q(_SQL_ACTIVOS)
    df["etiqueta"] = [_etiqueta(n, m) for n, m in zip(df.numero, df.nombre)]
    df["estado_txt"] = df.apply(estado_txt, axis=1)
    df["buscable"] = [normalizar(f"{a} {b} {c} {d}") for a, b, c, d in zip(
        df.numero, df.nombre.fillna(""), df.alias.fillna(""), df.descripcion.fillna(""))]
    return df


def todos_animales() -> pd.DataFrame:
    """Todos los animales (incluye vendidos y muertos), para búsquedas e historia."""
    df = q("""SELECT a.id AS animal_id, a.numero, a.nombre, a.sexo, a.raza, a.fecha_nacimiento,
                     a.descripcion, a.madre_id,
                     (SELECT group_concat(alias, ' | ') FROM alias_animales WHERE animal_id = a.id) AS alias
              FROM animales a""")
    df["etiqueta"] = [_etiqueta(n, m) for n, m in zip(df.numero, df.nombre)]
    df["buscable"] = [normalizar(f"{a} {b} {c} {d}") for a, b, c, d in zip(
        df.numero, df.nombre.fillna(""), df.alias.fillna(""), df.descripcion.fillna(""))]
    return df


def buscar(df: pd.DataFrame, texto: str) -> pd.DataFrame:
    """Coincidencia por número, nombre, alias o descripción (sin tildes ni mayúsculas)."""
    fichas = normalizar(texto).split()
    if not fichas:
        return df
    mask = pd.Series(True, index=df.index)
    for f in fichas:
        mask &= df["buscable"].str.contains(f, regex=False)
    res = df[mask].copy()
    exacto = res["numero"].astype(str).str.lower() == normalizar(texto)
    return res.assign(_p=(~exacto).astype(int)).sort_values(["_p"], kind="stable").drop(columns="_p")


def aplicar_filtro(df: pd.DataFrame, filtro: str) -> pd.DataFrame:
    vaca = df.categoria == "vaca"
    if filtro == "Lactando":
        return df[vaca & (df.estado_productivo == "lactando")]
    if filtro == "Secas":
        return df[vaca & (df.estado_productivo == "seca")]
    if filtro == "Preñadas":
        return df[df.estado_reproductivo == "prenada"]
    if filtro == "Por parir":
        return df[(df.estado_reproductivo == "prenada") & (df.dias_para_parto <= 45)]
    if filtro == "Abiertas":
        return df[vaca & df.estado_reproductivo.isin(["vacia", "servida"])]
    if filtro == "Abiertas +150":
        return df[vaca & df.estado_reproductivo.isin(["vacia", "servida"]) & (df.dias_abiertos >= 150)]
    if filtro == "Novillas":
        return df[df.categoria == "novilla"]
    if filtro == "Terneras":
        return df[df.categoria.isin(["ternera", "ternero"])]
    if filtro == "En retiro":
        return df[df.retiro_leche_hasta.notna()]
    if filtro == "Sin vacunar":
        c = campana_aftosa()
        return df[df.animal_id.isin(c["pendientes"].animal_id)] if c["en_curso"] else df.iloc[0:0]
    return df


# --------------------------------------------------------------------------- sanidad
def campana_aftosa(dias_ventana: int = 45) -> dict:
    """Campaña de aftosa en curso: aplicaciones de los últimos `dias_ventana` días."""
    h = pd.Timestamp(hoy())
    ap = q("""SELECT animal_id, fecha FROM eventos_validos
              WHERE tipo = 'tratamiento' AND json_extract(datos, '$.producto_id') = 1""")
    ap["fecha"] = pd.to_datetime(ap["fecha"])
    act = animales_df()
    elegibles = act[act.edad_dias >= 90]
    ultima = ap["fecha"].max() if not ap.empty else pd.NaT
    rec = ap[ap["fecha"] >= h - pd.Timedelta(days=dias_ventana)]
    if rec.empty:
        return dict(en_curso=False, ultima=ultima, inicio=pd.NaT, elegibles=len(elegibles),
                    aplicados=0, pendientes=elegibles.iloc[0:0])
    vac = set(rec["animal_id"])
    return dict(en_curso=True, ultima=ultima, inicio=rec["fecha"].min(), elegibles=len(elegibles),
                aplicados=int(elegibles.animal_id.isin(vac).sum()),
                pendientes=elegibles[~elegibles.animal_id.isin(vac)])


# --------------------------------------------------------------------------- potreros
def potreros_df() -> pd.DataFrame:
    """Un renglón por potrero: ocupación, composición y días desde el último ingreso/salida."""
    pot = q("SELECT id AS potrero_id, nombre, area_ha FROM potreros ORDER BY id")
    act = animales_df().merge(q("SELECT animal_id, fecha AS ingreso FROM potrero_actual"),
                              on="animal_id", how="left")
    h = pd.Timestamp(hoy())

    def grupo(r):
        if r.categoria == "vaca":
            return "Vacas lactando" if r.estado_productivo == "lactando" else "Vacas secas"
        return {"novilla": "Novillas", "ternera": "Terneras", "ternero": "Terneros",
                "toro": "Toro"}.get(r.categoria, r.categoria)

    act["grupo"] = act.apply(grupo, axis=1)
    tr = q("""SELECT ea.animal_id, e.fecha, e.potrero_id FROM eventos e
              JOIN eventos_animales ea ON ea.evento_id = e.id
              WHERE e.estado = 'confirmado' AND e.tipo = 'traslado'
              ORDER BY ea.animal_id, e.fecha, e.id""")
    tr["prev"] = tr.groupby("animal_id")["potrero_id"].shift()
    sal = tr[tr.prev.notna() & (tr.prev != tr.potrero_id)].copy()
    sal["prev"] = sal["prev"].astype(int)
    ultima_salida = pd.to_datetime(sal.groupby("prev")["fecha"].max())
    filas = []
    for r in pot.itertuples():
        a = act[act.potrero == r.nombre]
        ingreso = pd.to_datetime(a["ingreso"]).max() if len(a) else pd.NaT
        salida = ultima_salida.get(r.potrero_id, pd.NaT)
        filas.append(dict(
            potrero_id=r.potrero_id, nombre=r.nombre, area_ha=r.area_ha, animales=len(a),
            carga=len(a) / r.area_ha if r.area_ha else 0,
            composicion=a["grupo"].value_counts().to_dict(),
            dias_ingreso=(h - ingreso).days if pd.notna(ingreso) else None,
            dias_descanso=(h - salida).days if (len(a) == 0 and pd.notna(salida)) else None,
            detalle=a))
    return pd.DataFrame(filas)

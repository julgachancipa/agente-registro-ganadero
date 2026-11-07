#!/usr/bin/env python3
"""Crea db/demo.db (SQLite) a partir de db/schema_sqlite.sql y data/demo/*.csv.

Uso:  python scripts/cargar_demo.py [ruta_salida.db]
"""
import csv
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA = RAIZ / "db" / "schema_sqlite.sql"
DATOS = RAIZ / "data" / "demo"
SALIDA = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "db" / "demo.db"
FECHA_DEMO = "2026-11-07"

# Orden de carga (respeta las llaves foráneas)
TABLAS = ["fincas", "usuarios", "usuarios_fincas", "potreros", "productos_sanitarios",
          "animales", "alias_animales", "mensajes", "eventos", "eventos_animales",
          "produccion_leche"]


def main():
    if SALIDA.exists():
        SALIDA.unlink()
    con = sqlite3.connect(SALIDA)
    con.execute("PRAGMA foreign_keys = OFF")  # eventos.anulado_por apunta a un evento posterior
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    for tabla in TABLAS:
        with open(DATOS / f"{tabla}.csv", newline="", encoding="utf-8") as f:
            lector = csv.reader(f)
            columnas = next(lector)
            filas = [[v if v != "" else None for v in fila] for fila in lector]
        marcas = ",".join("?" * len(columnas))
        con.executemany(f"INSERT INTO {tabla} ({','.join(columnas)}) VALUES ({marcas})", filas)
        print(f"{tabla:22s} {len(filas):>7d} filas")
    con.execute("INSERT INTO config (clave, valor) VALUES ('fecha_demo', ?)", (FECHA_DEMO,))
    errores = con.execute("PRAGMA foreign_key_check").fetchall()
    con.commit()
    con.close()
    if errores:
        sys.exit(f"Llaves foráneas inválidas: {errores[:5]}")
    print(f"\nBase creada en {SALIDA} (fecha_demo = {FECHA_DEMO})")


if __name__ == "__main__":
    main()

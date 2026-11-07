#!/usr/bin/env python3
"""Genera datos dummy de una finca LECHERA (~3 años) como CSV en data/demo/.

- Reproducible: semilla fija.
- Simula el hato día a día: servicio -> palpación -> parto -> secado, y el ordeño
  de la mañana y de la tarde de cada vaca en lactancia.
- TODO es ficticio (nombres, teléfonos, precios, productos y tiempos de retiro).

Uso:  python scripts/generar_demo.py
"""
from __future__ import annotations

import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace as NS

SEED = 42
INICIO = date(2023, 11, 7)
FIN = date(2026, 11, 7)  # corte: ordeño de la mañana incluido; el de la tarde aún no ocurre
GESTACION = 283
SALIDA = Path(__file__).resolve().parent.parent / "data" / "demo"

rnd = random.Random(SEED)


def D(n: int) -> timedelta:
    return timedelta(days=n)


# --------------------------------------------------------------------------- catálogo
DUENO, MAYORDOMO, VAQUERO = 1, 2, 3
USUARIOS = [
    (DUENO, "570000000001", "Marta Rodríguez (dueña)"),
    (MAYORDOMO, "570000000002", "Eduardo Pardo (mayordomo)"),
    (VAQUERO, "570000000003", "Jairo Cárdenas (vaquero)"),
]
POTREROS = [
    ("Potrero 1", 3.5), ("Potrero 2", 4.0), ("Potrero 3", 3.0), ("Potrero 4", 3.5),
    ("Potrero 5", 5.0), ("Lote secas", 2.5), ("Potrero parto", 1.0), ("Lote crías", 0.8),
]
POT_ID = {n: i + 1 for i, (n, _) in enumerate(POTREROS)}
ROTACION = ["Potrero 1", "Potrero 2", "Potrero 3", "Potrero 4"]

FUENTE = "DEMO: valor ficticio, no usar como referencia"
PRODUCTOS = [  # id, nombre, principio_activo, retiro_leche, retiro_carne, fuente
    (1, "Vacuna aftosa (demo)", None, 0, 0, FUENTE),
    (2, "Vacuna brucelosis (demo)", None, 0, 0, FUENTE),
    (3, "Antibiótico intramamario (demo)", "ficticio", 4, 7, FUENTE),
    (4, "Desparasitante (demo)", "ficticio", 0, 35, FUENTE),
]

RAZAS = ["Holstein", "Normando", "Jersey", "Jersey x Holstein"]
PESO_RAZAS = [0.60, 0.20, 0.10, 0.10]
PICO = {"Holstein": 30, "Normando": 24, "Jersey": 20, "Jersey x Holstein": 25}  # L/día en el pico
PESO = {"Holstein": 600, "Normando": 560, "Jersey": 400, "Jersey x Holstein": 500}  # kg adulta
PAJILLAS = ["HOL-0412", "HOL-0877", "HOL-1203", "NOR-0215", "NOR-0330", "JER-0101", "JER-0144"]

ESPECIALES = [  # casos para probar desambiguación: números parecidos, alias, descripción
    ("24", "Canela", "Jersey", "Jersey pequeña de pelaje café"),
    ("214", "Mona", "Normando", "Normando color canela claro"),
    ("241", "Estrella", "Holstein", "Manchas negras grandes y cara blanca"),
    ("118", "Paloma", "Holstein", "Oreja derecha cortada"),
]
ALIAS = [("214", "la Mona"), ("241", "la Pintada"), ("118", "la de la oreja cortada"),
         ("118", "Oreja"), ("24", "la Jersey")]

NOMBRES = """Luna Margarita Bonita Negra Blanca Princesa Gaviota Chispa Morena Manchas Carmela
Dulce Reina Fanny Cleopatra Lola Tola Lucero Aurora Nieve Pantera Violeta Esperanza Sultana
Clavel Amapola Azucena Gardenia Camila Rubí Perla Esmeralda Topacio Diamante Zafiro Bella
Caramelo Mariposa Golondrina Alondra Sabana Neblina Aurelia Trinidad Consuelo Pastora
Rosalba Fortuna Victoria Maruja Pepita Tulipana Orquídea Margot Chola Pelusa Zarina Nube
Lluvia Brisa Cometa Estela Mireya Soledad Candela Peregrina Capuchina Tabaca Gitana Jazmín
Coqueta Chocolata Panda Vaquita Manzana Fresa Mora Guayaba Lulo Curuba""".split()
rnd.shuffle(NOMBRES)
_nombres = iter(NOMBRES)

AFTOSA = [date(2023, 11, 14), date(2024, 5, 14), date(2024, 11, 12), date(2025, 5, 13),
          date(2025, 11, 11), date(2026, 5, 12)]
AFTOSA_PARCIAL = date(2026, 11, 3)  # ciclo en curso: queda ~40% sin vacunar
DESPARASITAR = [date(2024, 3, 5), date(2024, 9, 10), date(2025, 3, 4), date(2025, 9, 9),
                date(2026, 3, 3), date(2026, 9, 8)]
KEEP_HEMBRAS = 0.45  # fracción de terneras que se queda como reemplazo; el resto se vende

# --------------------------------------------------------------------------- estado
animales: list[NS] = []
eventos: list[dict] = []
prod_rows: list[tuple] = []
usados: set[str] = set()
estado = {"rot": 0, "num": 300, "anulacion": False, "subf": 0}


def siguiente_nombre() -> str | None:
    return next(_nombres, None)


def numero_libre(lo: int, hi: int) -> str:
    while True:
        n = str(rnd.randint(lo, hi))
        if n not in usados:
            usados.add(n)
            return n


def crear_animal(**kw) -> NS:
    a = NS(
        id=len(animales) + 1, numero=None, nombre=None, sexo="H", raza="Holstein", nac=INICIO,
        madre=None, padre=None, pajilla=None, origen="nacido", desc=None, activo=True,
        cat="vaca", repro="vacia", prod="no", last_parto=None, next_service=None,
        concebida=False, sv_date=None, sv_padre=None, sv_pajilla=None, palp_date=None,
        exp_parto=None, secado_date=None, aborto_date=None, vet_check=None,
        post_traslado=None, fallos=0, peak=0.0, tp=45, parity=0, protegida=False,
        subfertil=False, potrero=None, retiro_hasta=None, dip_hasta=None, venta_plan=None,
        bruc_dia=None, destetada=False, pesada=False,
    )
    for k, v in kw.items():
        setattr(a, k, v)
    animales.append(a)
    return a


def ev(tipo, fecha, ids, potrero=None, datos=None, estado_ev="confirmado", por=VAQUERO,
       motivo=None) -> dict:
    e = dict(tmp=len(eventos) + 1, tipo=tipo, fecha=fecha, ids=list(ids), potrero=potrero,
             datos=datos or {}, estado=estado_ev, anulado_por=None, motivo=motivo, por=por)
    eventos.append(e)
    return e


def traslado(grupo, fecha, destino, por=VAQUERO):
    ev("traslado", fecha, [x.id for x in grupo], potrero=destino,
       datos={"potrero_destino": destino}, por=por)
    for x in grupo:
        x.potrero = destino


def nuevo_pico(a: NS):
    factor = [0.78, 0.90, 1.0, 1.0, 1.0, 0.95][min(max(a.parity, 1), 6) - 1]
    a.peak = PICO[a.raza] * factor * rnd.gauss(1, 0.10)
    a.tp = rnd.randint(38, 60)


# --------------------------------------------------------------------------- eventos del hato
def p_conc(a: NS, d: date) -> float:
    if a.protegida:
        return 0.80
    if a.subfertil:
        return 0.03
    if a.last_parto is None:  # novilla
        return 0.60
    return 0.50 if (d - a.last_parto).days < 150 else 0.40


def servir(a: NS, d: date, forzar: bool | None = None):
    tipo = "IA" if rnd.random() < 0.75 else "monta"
    datos, padre, paj = {"tipo": tipo}, None, None
    if tipo == "IA":
        paj = rnd.choice(PAJILLAS)
        datos["pajilla"] = paj
    else:
        padre = TORO.id
        datos.update({"toro_id": TORO.id, "toro": TORO.numero})
    ev("servicio", d, [a.id], potrero=a.potrero, datos=datos, por=MAYORDOMO)
    p = p_conc(a, d) if forzar is None else (1.0 if forzar else 0.0)
    a.repro = "servida"
    a.vet_check = None
    if rnd.random() < p:
        a.concebida, a.sv_date, a.sv_padre, a.sv_pajilla = True, d, padre, paj
        a.palp_date = d + D(rnd.randint(45, 60))
        a.exp_parto = d + D(GESTACION + rnd.randint(-4, 5))
        a.next_service, a.fallos = None, 0
        if d >= INICIO and a.prod == "lactando" and rnd.random() < 0.03:
            a.aborto_date = d + D(rnd.randint(110, 200))
    else:
        a.concebida = False
        a.fallos += 1
        a.next_service = d + D(rnd.randint(19, 23) if rnd.random() < 0.85 else rnd.randint(40, 45))
        if a.fallos % 3 == 0:  # tras 3 fallos el veterinario revisa
            a.vet_check = d + D(rnd.randint(10, 15))
            a.next_service = max(a.next_service, a.vet_check + D(5))


def palpar(a: NS, d: date, resultado: str):
    datos = {"resultado": resultado}
    if resultado == "preñada":
        datos["meses_gestacion"] = round((d - a.sv_date).days / 30.4, 1)
        datos["fecha_probable_parto"] = (a.sv_date + D(GESTACION)).isoformat()
        a.repro = "prenada"
        if a.prod == "lactando":
            a.secado_date = a.exp_parto - D(60)
    else:
        a.repro = "vacia"
    ev("palpacion", d, [a.id], potrero=a.potrero, datos=datos, por=MAYORDOMO)


def secar(a: NS, d: date):
    ev("secado", d, [a.id], potrero=a.potrero, por=MAYORDOMO)
    ev("pesaje", d, [a.id], potrero=a.potrero,
       datos={"peso_kg": float(round(rnd.gauss(PESO[a.raza], 30)))}, por=MAYORDOMO)
    a.prod, a.secado_date = "seca", None
    traslado([a], d, "Lote secas")


def vender(a: NS, d: date, precio: int, comprador: str, motivo: str | None = None):
    datos = {"precio_cop": precio, "comprador": comprador}
    if motivo:
        datos["motivo"] = motivo
    ev("venta", d, [a.id], datos=datos, por=DUENO)
    a.activo = False


def morir(a: NS, d: date, causa: str):
    ev("muerte", d, [a.id], potrero=a.potrero, datos={"causa": causa}, por=MAYORDOMO)
    a.activo = False


def abortar(a: NS, d: date):
    ev("parto", d, [a.id], potrero=a.potrero,
       datos={"resultado": "aborto", "meses_gestacion": round((d - a.sv_date).days / 30.4, 1)},
       por=MAYORDOMO)
    a.concebida, a.repro = False, "vacia"
    a.palp_date = a.exp_parto = a.secado_date = a.aborto_date = None
    a.next_service = d + D(rnd.randint(35, 55))
    traslado([a], d, ROTACION[estado["rot"]]) if a.potrero == "Potrero parto" else None


def parir(a: NS, d: date):
    resultado = "muerto" if rnd.random() < 0.03 else "vivo"
    datos = {"resultado": resultado}
    cria = None
    if resultado == "vivo":
        sexo = "H" if rnd.random() < 0.5 else "M"
        num = str(estado["num"])
        estado["num"] += 1
        usados.add(num)
        raza = a.raza if rnd.random() < 0.8 else rnd.choice(RAZAS)
        cria = crear_animal(numero=num, sexo=sexo, raza=raza, nac=d, madre=a.id, padre=a.sv_padre,
                            pajilla=a.sv_pajilla, cat="ternera" if sexo == "H" else "ternero")
        if sexo == "M":
            cria.venta_plan = d + D(rnd.randint(5, 10))
        elif rnd.random() < KEEP_HEMBRAS:
            cria.nombre = siguiente_nombre() or f"Vaca {num}"
            cria.bruc_dia = rnd.randint(100, 200)
            cria.next_service = d + D(rnd.randint(450, 520))
        else:
            cria.venta_plan = d + D(rnd.randint(15, 45))
        datos.update({"cria_id": cria.id, "cria_numero": num, "cria_sexo": sexo,
                      "peso_kg": round(rnd.gauss(38 if sexo == "M" else 35, 3), 1)})
    pot = a.potrero or "Potrero parto"
    if resultado == "vivo" and not estado["anulacion"] and d >= date(2025, 6, 1) and not a.protegida:
        # caso de prueba: se registró en la vaca equivocada y se corrigió
        otras = [x for x in animales if x.activo and x.cat == "vaca" and x.id != a.id]
        otra = rnd.choice(otras)
        malo = ev("parto", d, [otra.id], potrero=pot, datos=dict(datos), estado_ev="anulado",
                  motivo=f"Error de animal: el parto fue de la {a.numero}, no de la {otra.numero}",
                  por=VAQUERO)
        bueno = ev("parto", d, [a.id], potrero=pot, datos=datos, por=VAQUERO)
        malo["anulado_por"] = bueno["tmp"]
        estado["anulacion"] = True
    else:
        ev("parto", d, [a.id], potrero=pot, datos=datos, por=VAQUERO)
    if cria is not None:
        traslado([cria], d, "Lote crías")
    a.last_parto, a.prod, a.cat, a.repro = d, "lactando", "vaca", "vacia"
    a.parity += 1
    a.concebida, a.sv_date, a.palp_date, a.exp_parto = False, None, None, None
    a.secado_date = a.aborto_date = a.vet_check = None
    a.fallos = 0
    a.next_service = d + D(rnd.randint(55, 90))
    a.post_traslado = d + D(3)
    nuevo_pico(a)
    if (not a.subfertil and not a.protegida and estado["subf"] < 3
            and date(2026, 3, 1) <= d <= date(2026, 5, 31)):
        a.subfertil = True  # vacas abiertas largas para probar la consulta
        estado["subf"] += 1


def mastitis(a: NS, d: date):
    ev("tratamiento", d, [a.id], potrero=a.potrero, por=MAYORDOMO, datos={
        "producto_id": 3, "producto": PRODUCTOS[2][1], "diagnostico": "mastitis",
        "cuarto": rnd.choice(["anterior izquierdo", "anterior derecho",
                              "posterior izquierdo", "posterior derecho"]),
        "via": "intramamaria", "dias_tratamiento": 3,
        "retiro_leche_hasta": (d + D(6)).isoformat()})
    a.retiro_hasta, a.dip_hasta = d + D(6), d + D(7)


def grupo_tratamiento(d: date, prod_id: int, grupo: list[NS], extra: dict | None = None):
    if not grupo:
        return
    datos = {"producto_id": prod_id, "producto": PRODUCTOS[prod_id - 1][1]}
    datos.update(extra or {})
    ev("tratamiento", d, [x.id for x in grupo], datos=datos, por=MAYORDOMO)


# --------------------------------------------------------------------------- ordeño
def litros_dia(a: NS, d: date, dim: int) -> float:
    y = a.peak * (dim / a.tp) ** 0.25 * math.exp(0.25 * (1 - dim / a.tp))  # curva de Wood
    y *= 1 + 0.04 * math.sin(2 * math.pi * (d.timetuple().tm_yday - 60) / 365)
    y *= rnd.gauss(1, 0.05)
    if a.dip_hasta and d <= a.dip_hasta:
        y *= 0.65
    return max(y, 0.0)


def ordenar(a: NS, d: date):
    dim = (d - a.last_parto).days
    if dim < 1:
        return
    y = litros_dia(a, d, dim)
    share = min(max(rnd.gauss(0.54, 0.02), 0.48), 0.60)
    if dim <= 4:
        destino = "calostro"
    elif a.retiro_hasta and d <= a.retiro_hasta:
        destino = "descarte"
    else:
        destino = "tanque"
    for ordeno, parte in (("manana", share), ("tarde", 1 - share)):
        if ordeno == "tarde" and d == FIN:
            continue
        litros = round(y * parte * rnd.gauss(1, 0.03), 1)
        if litros < 0.3:
            continue
        por = VAQUERO if (ordeno == "manana" or rnd.random() < 0.9) else MAYORDOMO
        prod_rows.append((len(prod_rows) + 1, 1, a.id, d.isoformat(), ordeno, litros, destino, por))


# --------------------------------------------------------------------------- paso diario
def paso_hembra(a: NS, d: date):
    if a.concebida:
        if a.aborto_date == d:
            abortar(a, d)
            return
        if a.palp_date == d:
            palpar(a, d, "preñada")
        if a.exp_parto - D(10) == d:
            traslado([a], d, "Potrero parto")
        if a.secado_date == d and a.prod == "lactando":
            secar(a, d)
        if a.exp_parto == d:
            parir(a, d)
            return
    else:
        if a.vet_check == d:
            palpar(a, d, "vacía")
            a.vet_check = None
        if a.next_service and d >= a.next_service:
            if a.cat == "novilla" and not a.pesada:
                ev("pesaje", d, [a.id], potrero=a.potrero, por=MAYORDOMO,
                   datos={"peso_kg": float(round(rnd.gauss(PESO[a.raza] * 0.6, 20))),
                          "motivo": "previo al primer servicio"})
                a.pesada = True
            servir(a, d)
    if a.post_traslado == d:
        traslado([a], d, ROTACION[estado["rot"]])
        a.post_traslado = None


def paso(a: NS, d: date):
    edad = (d - a.nac).days
    if a.cat in ("ternero", "ternera"):
        if a.venta_plan == d:
            if a.sexo == "M":
                vender(a, d, rnd.randrange(150_000, 350_001, 10_000), "Comerciante de ganado")
            else:
                vender(a, d, rnd.randrange(400_000, 800_001, 10_000), "Comerciante de ganado")
            return
        if edad < 60 and rnd.random() < 0.0004:
            morir(a, d, rnd.choice(["diarrea", "neumonía", "desconocida"]))
            return
        if a.cat == "ternera":
            if edad == 90 and not a.destetada:
                ev("destete", d, [a.id], potrero="Potrero 5", por=MAYORDOMO,
                   datos={"peso_kg": float(round(rnd.gauss(95, 8)))})
                traslado([a], d, "Potrero 5")
                a.destetada = True
            if a.bruc_dia is not None and edad == a.bruc_dia:
                grupo_tratamiento(d, 2, [a], {"via": "subcutánea"})
            if edad >= 365:
                a.cat = "novilla"
        return
    if a.cat == "toro":
        return
    # novillas y vacas
    if a.cat == "vaca" and not a.protegida:
        if rnd.random() < 0.00008:
            morir(a, d, rnd.choice(["timpanismo", "fiebre de leche", "accidente", "desconocida"]))
            return
        if a.prod == "lactando" and not a.subfertil:
            dim = (d - a.last_parto).days
            p = 0.0004 + (0.05 if (not a.concebida and dim >= 360) else 0.0)
            if rnd.random() < p:
                vender(a, d, rnd.randrange(2_200_000, 3_600_001, 100_000), "Frigorífico (demo)",
                       motivo="descarte")
                return
    paso_hembra(a, d)
    if not a.activo or a.prod != "lactando":
        return
    dim = (d - a.last_parto).days
    if (dim >= 5 and not (a.retiro_hasta and d <= a.retiro_hasta)
            and rnd.random() < 0.0007):
        mastitis(a, d)
    ordenar(a, d)


# --------------------------------------------------------------------------- hato inicial
TORO = crear_animal(numero="901", nombre="Capitán", sexo="M", raza="Holstein",
                    nac=INICIO - D(1800), cat="toro", protegida=True)
usados.add("901")

esp_nums = {n for n, *_ in ESPECIALES}
usados |= esp_nums
specs = list(ESPECIALES)
for _ in range(24):
    specs.append((numero_libre(100, 260), siguiente_nombre(),
                  rnd.choices(RAZAS, PESO_RAZAS)[0], None))
rnd.shuffle(specs)

for num, nombre, raza, desc in specs:
    paridad = rnd.randint(1, 6)
    a = crear_animal(numero=num, nombre=nombre, raza=raza, desc=desc, parity=paridad, cat="vaca",
                     nac=INICIO - D(int(365 * (2.1 + 1.15 * (paridad - 1))) + rnd.randint(30, 300)),
                     protegida=num in esp_nums)
    nuevo_pico(a)
    tipo = rnd.choices(["abierta", "prenada", "seca"], [0.30, 0.45, 0.25])[0]
    if tipo == "abierta":
        dim = rnd.randint(25, 140)
        a.last_parto, a.prod = INICIO - D(dim), "lactando"
        a.next_service = max(INICIO, a.last_parto + D(rnd.randint(55, 90)))
    elif tipo == "prenada":
        dim = rnd.randint(110, 230)
        a.last_parto, a.prod = INICIO - D(dim), "lactando"
        sv = a.last_parto + D(rnd.randint(60, min(130, dim - 5)))
    else:
        sv = INICIO + D(rnd.randint(20, 60) - GESTACION)
        a.last_parto, a.prod = sv - D(rnd.randint(50, 110)), "seca"
    ev("parto", a.last_parto, [a.id], por=MAYORDOMO,
       datos={"resultado": "vivo", "nota": "historial previo al inicio de los datos"})
    if tipo != "abierta":
        servir(a, sv, forzar=True)  # historial previo: servicio que terminó en preñez
        if a.palp_date < INICIO:
            palpar(a, a.palp_date, "preñada")
        if tipo == "seca":
            ev("secado", a.exp_parto - D(60), [a.id], por=MAYORDOMO)

for edad in (20, 45, 75):  # terneras de reemplazo
    a = crear_animal(numero=numero_libre(270, 299), nombre=siguiente_nombre(), cat="ternera",
                     raza=rnd.choices(RAZAS, PESO_RAZAS)[0], nac=INICIO - D(edad))
    a.bruc_dia = rnd.randint(100, 200)
    a.next_service = a.nac + D(rnd.randint(450, 520))
    a.destetada = False
for edad in (380, 430, 500, 560, 620):  # novillas
    a = crear_animal(numero=numero_libre(270, 299), nombre=siguiente_nombre(), cat="novilla",
                     raza=rnd.choices(RAZAS, PESO_RAZAS)[0], nac=INICIO - D(edad), destetada=True)
    a.next_service = max(INICIO + D(rnd.randint(3, 40)), a.nac + D(rnd.randint(450, 520)))

# ubicación inicial
traslado([x for x in animales if x.prod == "lactando"], INICIO, "Potrero 1", por=MAYORDOMO)
traslado([x for x in animales if x.prod == "seca"], INICIO, "Lote secas", por=MAYORDOMO)
traslado([x for x in animales if x.cat in ("novilla", "toro")], INICIO, "Potrero 5", por=MAYORDOMO)
traslado([x for x in animales if x.cat == "ternera"], INICIO, "Lote crías", por=MAYORDOMO)

# --------------------------------------------------------------------------- simulación
aftosa_dia1: dict[date, set[int]] = {}
for dia in range((FIN - INICIO).days + 1):
    d = INICIO + D(dia)
    activos = [x for x in animales if x.activo]

    if dia > 0 and dia % 8 == 0:  # rotación de las vacas en ordeño
        estado["rot"] = (estado["rot"] + 1) % 4
        grupo = [x for x in activos if x.potrero in ROTACION]
        if grupo:
            traslado(grupo, d, ROTACION[estado["rot"]])

    elegibles = [x for x in activos if (d - x.nac).days >= 90]
    if d in AFTOSA:
        g = [x for x in elegibles if rnd.random() < 0.8]
        aftosa_dia1[d] = {x.id for x in g}
        grupo_tratamiento(d, 1, g, {"dosis": "2 ml", "via": "subcutánea"})
    elif (d - D(1)) in AFTOSA:
        g = [x for x in elegibles if x.id not in aftosa_dia1[d - D(1)]]
        grupo_tratamiento(d, 1, g, {"dosis": "2 ml", "via": "subcutánea"})
    if d == AFTOSA_PARCIAL:
        g = [x for x in elegibles if rnd.random() < 0.6]
        grupo_tratamiento(d, 1, g, {"dosis": "2 ml", "via": "subcutánea"})
    if d in DESPARASITAR:
        grupo_tratamiento(d, 4, elegibles, {"via": "oral"})

    if d == date(2024, 9, 10):  # compra de una novilla de vientre
        n = crear_animal(numero="512", nombre="Rosita", raza="Holstein", origen="comprado",
                         nac=d - D(640), cat="novilla", destetada=True, pesada=True)
        ev("compra", d, [n.id], por=DUENO,
           datos={"precio_cop": 5_800_000, "proveedor": "Finca vecina (ficticia)"})
        traslado([n], d, "Potrero 5")
        n.concebida, n.sv_date = True, d - D(183)
        n.exp_parto = n.sv_date + D(GESTACION)
        n.repro = "prenada"
        ev("palpacion", d, [n.id], potrero="Potrero 5", por=MAYORDOMO,
           datos={"resultado": "preñada", "meses_gestacion": 6.0,
                  "fecha_probable_parto": n.exp_parto.isoformat(), "nota": "al momento de la compra"})

    if d == FIN - D(2):  # mastitis reciente: leche en retiro vigente hoy
        for x in animales:
            if (x.activo and x.prod == "lactando" and not x.protegida
                    and (d - x.last_parto).days > 20 and not (x.retiro_hasta and x.retiro_hasta >= d)):
                mastitis(x, d)
                break

    for x in list(animales):
        if x.activo:
            paso(x, d)

# pesaje sospechoso pendiente de confirmar (alerta por rango)
sospechosa = next(x for x in animales if x.numero == "118")
ev("pesaje", FIN, [sospechosa.id], potrero=sospechosa.potrero, estado_ev="pendiente",
   datos={"peso_kg": 4120.0, "alerta": "fuera de rango; confirmar con el usuario"}, por=VAQUERO)

# --------------------------------------------------------------------------- salida
SALIDA.mkdir(parents=True, exist_ok=True)


def escribir(nombre: str, cabecera: list[str], filas):
    with open(SALIDA / f"{nombre}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cabecera)
        w.writerows(filas)


def js(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


escribir("fincas", ["id", "nombre", "municipio", "creada_en"],
         [(1, "Finca El Roble (demo)", "Ubaté", INICIO.isoformat())])
escribir("usuarios", ["id", "telefono", "nombre"], USUARIOS)
escribir("usuarios_fincas", ["usuario_id", "finca_id", "rol"],
         [(DUENO, 1, "dueno"), (MAYORDOMO, 1, "mayordomo"), (VAQUERO, 1, "vaquero")])
escribir("potreros", ["id", "finca_id", "nombre", "area_ha"],
         [(i + 1, 1, n, ha) for i, (n, ha) in enumerate(POTREROS)])
escribir("productos_sanitarios",
         ["id", "nombre", "principio_activo", "dias_retiro_leche", "dias_retiro_carne", "fuente"],
         PRODUCTOS)
escribir("animales",
         ["id", "finca_id", "numero", "nombre", "sexo", "raza", "fecha_nacimiento", "madre_id",
          "padre_id", "pajilla", "origen", "descripcion", "creado_en"],
         [(a.id, 1, a.numero, a.nombre, a.sexo, a.raza, a.nac.isoformat(), a.madre, a.padre,
           a.pajilla, a.origen, a.desc, a.nac.isoformat()) for a in animales])
por_num = {a.numero: a.id for a in animales}
escribir("alias_animales", ["animal_id", "alias"], [(por_num[n], al) for n, al in ALIAS])
escribir("mensajes", ["id", "finca_id", "usuario_id", "enviado_en", "recibido_en", "texto",
                      "audio_url", "transcripcion"], [])

ordenados = sorted(eventos, key=lambda e: (e["fecha"], e["tmp"]))
nuevo_id = {e["tmp"]: i + 1 for i, e in enumerate(ordenados)}
escribir("eventos",
         ["id", "finca_id", "tipo", "fecha", "potrero_id", "datos", "estado", "anulado_por",
          "motivo_anulacion", "mensaje_id", "reportado_por", "creado_en"],
         [(nuevo_id[e["tmp"]], 1, e["tipo"], e["fecha"].isoformat(),
           POT_ID[e["potrero"]] if e["potrero"] else None, js(e["datos"]), e["estado"],
           nuevo_id[e["anulado_por"]] if e["anulado_por"] else None, e["motivo"], None, e["por"],
           e["fecha"].isoformat() + "T12:00:00-05:00") for e in ordenados])
escribir("eventos_animales", ["evento_id", "animal_id"],
         [(nuevo_id[e["tmp"]], i) for e in ordenados for i in e["ids"]])
escribir("produccion_leche",
         ["id", "finca_id", "animal_id", "fecha", "ordeno", "litros", "destino", "registrado_por"],
         prod_rows)

# --------------------------------------------------------------------------- resumen
activos = [a for a in animales if a.activo]
por_cat: dict[str, int] = {}
for a in activos:
    por_cat[a.cat] = por_cat.get(a.cat, 0) + 1
por_tipo: dict[str, int] = {}
for e in eventos:
    por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
print(f"animales: {len(animales)} (activos al corte: {len(activos)} -> {por_cat})")
print(f"eventos: {len(eventos)} -> {dict(sorted(por_tipo.items()))}")
print(f"produccion_leche: {len(prod_rows)} filas")
print(f"CSV en {SALIDA}")

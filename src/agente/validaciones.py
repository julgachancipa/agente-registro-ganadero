"""Reglas de negocio. Viven en código, no en el prompt.

Cada validación devuelve errores (bloquean el registro) o alertas (se muestran
junto al resumen para que el usuario confirme).
"""
from dataclasses import dataclass, field
from datetime import date

DIAS_MIN_ENTRE_PARTOS = 270
RANGOS_PESO_KG = {  # aproximados; ajustar por raza y sistema
    "ternero": (20, 250),
    "levante": (150, 400),
    "adulto": (300, 1000),
}


@dataclass
class Resultado:
    errores: list[str] = field(default_factory=list)
    alertas: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errores


def validar_parto(madre, fecha: date, ultimo_parto: date | None, hoy: date) -> Resultado:
    r = Resultado()
    if madre.sexo != "H":
        r.errores.append(f"El animal {madre.numero} es macho; no puede registrar un parto.")
    if fecha > hoy:
        r.errores.append("La fecha del parto está en el futuro.")
    if ultimo_parto and (fecha - ultimo_parto).days < DIAS_MIN_ENTRE_PARTOS:
        r.alertas.append(
            f"El último parto de {madre.numero} fue hace {(fecha - ultimo_parto).days} días. ¿Es correcto?"
        )
    return r


def validar_servicio(animal, estado_reproductivo: str) -> Resultado:
    r = Resultado()
    if animal.sexo != "H":
        r.errores.append(f"El animal {animal.numero} es macho.")
    if estado_reproductivo == "preñada":
        r.alertas.append(f"{animal.numero} figura como preñada. ¿Seguro que se sirvió?")
    return r


def validar_pesaje(peso_kg: float, etapa: str) -> Resultado:
    r = Resultado()
    minimo, maximo = RANGOS_PESO_KG.get(etapa, (10, 1200))
    if not (minimo <= peso_kg <= maximo):
        r.alertas.append(f"{peso_kg} kg está fuera del rango usual para {etapa} ({minimo}–{maximo} kg).")
    return r

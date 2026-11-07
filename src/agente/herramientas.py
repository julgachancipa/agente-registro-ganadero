"""Definición de herramientas del agente (formato tool use de la Claude API).

Las herramientas de escritura crean eventos en estado 'pendiente'; solo pasan a
'confirmado' cuando el usuario acepta el resumen.
"""

FECHA = {"type": "string", "format": "date", "description": "Fecha del hecho (YYYY-MM-DD), resuelta contra la fecha del mensaje."}
ANIMAL = {"type": "integer", "description": "ID interno devuelto por buscar_animal. Nunca inventarlo."}

HERRAMIENTAS = [
    # --- Resolución ---
    {
        "name": "buscar_animal",
        "description": "Busca animales por número, nombre, alias o descripción. Devuelve candidatos con puntaje. Si hay más de un candidato plausible, pregunta al usuario.",
        "input_schema": {
            "type": "object",
            "properties": {"texto": {"type": "string"}},
            "required": ["texto"],
        },
    },
    {
        "name": "agregar_alias",
        "description": "Guarda un nombre alternativo cuando el usuario aclara a qué animal se refiere.",
        "input_schema": {
            "type": "object",
            "properties": {"animal_id": ANIMAL, "alias": {"type": "string"}},
            "required": ["animal_id", "alias"],
        },
    },
    # --- Escritura ---
    {
        "name": "registrar_parto",
        "description": "Registra un parto (o aborto). Crea la cría si se informa.",
        "input_schema": {
            "type": "object",
            "properties": {
                "madre_id": ANIMAL,
                "fecha": FECHA,
                "resultado": {"type": "string", "enum": ["vivo", "muerto", "aborto"]},
                "cria_sexo": {"type": "string", "enum": ["H", "M"]},
                "cria_numero": {"type": "string"},
                "potrero": {"type": "string"},
                "observaciones": {"type": "string"},
            },
            "required": ["madre_id", "fecha", "resultado"],
        },
    },
    {
        "name": "registrar_servicio",
        "description": "Registra monta natural o inseminación artificial.",
        "input_schema": {
            "type": "object",
            "properties": {
                "animal_id": ANIMAL,
                "fecha": FECHA,
                "tipo": {"type": "string", "enum": ["monta", "IA"]},
                "toro_o_pajilla": {"type": "string"},
            },
            "required": ["animal_id", "fecha", "tipo"],
        },
    },
    {
        "name": "registrar_palpacion",
        "description": "Registra un diagnóstico de preñez.",
        "input_schema": {
            "type": "object",
            "properties": {
                "animal_id": ANIMAL,
                "fecha": FECHA,
                "resultado": {"type": "string", "enum": ["preñada", "vacía"]},
                "meses_gestacion": {"type": "number"},
            },
            "required": ["animal_id", "fecha", "resultado"],
        },
    },
    {
        "name": "registrar_pesaje",
        "description": "Registra el peso de un animal.",
        "input_schema": {
            "type": "object",
            "properties": {"animal_id": ANIMAL, "fecha": FECHA, "peso_kg": {"type": "number"}},
            "required": ["animal_id", "fecha", "peso_kg"],
        },
    },
    {
        "name": "registrar_traslado",
        "description": "Mueve uno o varios animales a otro potrero.",
        "input_schema": {
            "type": "object",
            "properties": {
                "animal_ids": {"type": "array", "items": ANIMAL},
                "potrero_destino": {"type": "string"},
                "fecha": FECHA,
            },
            "required": ["animal_ids", "potrero_destino", "fecha"],
        },
    },
    {
        "name": "registrar_tratamiento",
        "description": "Registra vacunas, purgas o tratamientos. Los tiempos de retiro se toman de la tabla de productos, no del modelo.",
        "input_schema": {
            "type": "object",
            "properties": {
                "animal_ids": {"type": "array", "items": ANIMAL},
                "fecha": FECHA,
                "producto": {"type": "string"},
                "dosis": {"type": "string"},
                "via": {"type": "string"},
            },
            "required": ["animal_ids", "fecha", "producto"],
        },
    },
    {
        "name": "anular_evento",
        "description": "Anula un evento previo (corrección). Luego se registra el evento correcto.",
        "input_schema": {
            "type": "object",
            "properties": {"evento_id": {"type": "integer"}, "motivo": {"type": "string"}},
            "required": ["evento_id", "motivo"],
        },
    },
    {
        "name": "registrar_produccion_leche",
        "description": (
            "Registra los litros de uno o varios animales en un ordeño (mañana o tarde). "
            "La leche de animales en retiro por tratamiento se marca como descarte, y la de "
            "los primeros días tras el parto como calostro."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fecha": FECHA,
                "ordeno": {"type": "string", "enum": ["manana", "tarde"]},
                "registros": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"animal_id": ANIMAL, "litros": {"type": "number"}},
                        "required": ["animal_id", "litros"],
                    },
                },
            },
            "required": ["fecha", "ordeno", "registros"],
        },
    },
    # TODO: registrar_secado, registrar_venta, registrar_compra, registrar_muerte,
    #       registrar_destete
    # --- Lectura ---
    {
        "name": "estado_animal",
        "description": "Historia y estado derivado de un animal.",
        "input_schema": {"type": "object", "properties": {"animal_id": ANIMAL}, "required": ["animal_id"]},
    },
    {
        "name": "vacas_abiertas",
        "description": "Vacas con más de N días abiertos.",
        "input_schema": {"type": "object", "properties": {"dias_minimos": {"type": "integer"}}, "required": ["dias_minimos"]},
    },
    {
        "name": "inventario_por_categoria",
        "description": "Conteo de animales activos por categoría y sexo.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "produccion_animal",
        "description": "Litros de una vaca por día y por ordeño (mañana/tarde) en un rango de fechas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "animal_id": ANIMAL,
                "desde": FECHA,
                "hasta": FECHA,
            },
            "required": ["animal_id", "desde", "hasta"],
        },
    },
    {
        "name": "produccion_finca",
        "description": "Litros totales de la finca por día (y cuántos fueron al tanque) en un rango de fechas.",
        "input_schema": {
            "type": "object",
            "properties": {"desde": FECHA, "hasta": FECHA},
            "required": ["desde", "hasta"],
        },
    },
    {
        "name": "leche_en_retiro",
        "description": "Animales cuya leche debe ir a descarte por tratamiento, con la fecha hasta la que dura el retiro.",
        "input_schema": {"type": "object", "properties": {}},
    },
    # TODO: listar_animales, proximas_a_parir, pendientes_vacuna, exportar
]

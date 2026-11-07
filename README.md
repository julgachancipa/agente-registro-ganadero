# Agente de registro ganadero

Agente conversacional (WhatsApp + voz) para llevar los **registros e inventario de un hato**: partos, servicios, palpaciones, pesajes, vacunas, traslados de potrero, ventas y muertes. El productor envía un audio o un texto ("la 214 parió una hembra hoy en el potrero 3") y el agente lo convierte en un registro estructurado, lo confirma y permite consultarlo después.

## Principios

1. **La verdad vive en la base de datos, no en el modelo.** El LLM es la capa de lenguaje; los registros se guardan como eventos validados.
2. **Log de eventos.** El estado de cada animal (preñada, lactando, potrero actual) se calcula a partir de los eventos; nunca se sobrescribe.
3. **Confirmar antes de escribir.** Nada se guarda sin un resumen confirmado (explícito para ventas, muertes y tratamientos).
4. **Ante la duda, preguntar.** Si el animal es ambiguo, el agente pregunta; nunca adivina.
5. **Reglas de negocio en código.** Las validaciones (un macho no pare, intervalos entre partos, rangos de peso) viven en el backend, no en el prompt.
6. **WhatsApp primero.** Sin dashboard en el MVP: chat, audios y exportación a Excel/CSV.

## Estructura

```
.
├── docs/
│   ├── diseno-agente.md      # Arquitectura, flujo de confirmación, herramientas
│   ├── modelo-datos.md       # Entidades, eventos y estado derivado
│   ├── glosario.md           # Vocabulario ganadero colombiano para el prompt
│   └── roadmap.md            # Fases del proyecto
├── db/
│   ├── schema.sql            # Esquema Postgres (producción)
│   └── schema_sqlite.sql     # Esquema SQLite + vistas de estado (demo)
├── app/                      # Interfaz Streamlit (solo lectura), ver docs/interfaz.md
├── data/demo/                # CSV con datos dummy de una finca lechera (3 años)
├── scripts/
│   ├── generar_demo.py       # Genera los CSV (semilla fija)
│   └── cargar_demo.py        # Crea db/demo.db desde los CSV
├── src/agente/
│   ├── herramientas.py       # Definición de herramientas (tool use)
│   └── validaciones.py       # Reglas de negocio
├── evals/
│   ├── README.md             # Cómo se evalúa el agente
│   └── casos.jsonl           # Mensajes de ejemplo con el registro esperado
└── .env.example
```

## Stack del MVP

WhatsApp Cloud API → webhook (FastAPI) → transcripción de voz → agente con tool use (Claude API / Agent SDK) → Postgres → respuesta por WhatsApp.

## Estado

Fase 0: diseño y datos de demo. Ver [`docs/roadmap.md`](docs/roadmap.md).

## Interfaz web

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

Cinco secciones: Inicio, Hato, Leche, Registros y Potreros y sanidad. Ver [`docs/interfaz.md`](docs/interfaz.md).

## Probar los datos de demo

```bash
python scripts/cargar_demo.py          # crea db/demo.db a partir de data/demo/*.csv
sqlite3 db/demo.db "SELECT numero, nombre, estado_productivo, dias_en_leche FROM estado_animal LIMIT 5;"
```

Detalles de los datos y de los casos de prueba en [`docs/datos-demo.md`](docs/datos-demo.md).

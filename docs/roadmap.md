# Roadmap

## Fase 0: Diseño
- [x] Principios y flujo del agente
- [x] Modelo de datos inicial
- [x] Enfoque definido: finca **lechera** (dos ordeños al día; sin levante ni ceba de machos)
- [x] Datos dummy de una finca lechera (3 años) en CSV + SQLite, ver [`datos-demo.md`](datos-demo.md)
- [ ] Recolectar 100–200 mensajes/audios reales o realistas para evals

## Interfaz de consulta
- [x] Interfaz Streamlit de solo lectura sobre los datos de demo, ver [`interfaz.md`](interfaz.md)
- [ ] Pestaña **Chat** que simule el WhatsApp (se construye junto con el agente)

## Fase 1: Núcleo sin WhatsApp
- [ ] Postgres + esquema + vistas de estado
- [ ] Herramientas de escritura/lectura + validaciones
- [ ] Agente por CLI (texto)
- [ ] Evals de extracción por campo

## Fase 2: WhatsApp + voz
- [ ] Webhook FastAPI + WhatsApp Cloud API
- [ ] Transcripción de audios (probar con audios rurales reales)
- [ ] Flujo de confirmación en chat
- [ ] Usuarios y roles por finca

## Fase 3: Piloto
- [ ] 1–2 fincas reales
- [ ] Exportación CSV/XLSX
- [ ] Alertas: vacas abiertas, próximas a parir, vacunas pendientes
- [ ] Ajustar glosario y evals con datos reales

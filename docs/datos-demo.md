# Datos de demo

Finca **lechera** ficticia ("Finca El Roble (demo)", Ubaté) con ~3 años de historia, del 7 nov 2023 al 7 nov 2026 (fecha de corte: el ordeño de la **mañana** de hoy está registrado; el de la tarde aún no). Todo es inventado: nombres, teléfonos, precios, productos y tiempos de retiro.

## Cómo se genera

```bash
python scripts/generar_demo.py   # escribe data/demo/*.csv (semilla fija: siempre sale igual)
python scripts/cargar_demo.py    # crea db/demo.db con el esquema y las vistas
```

El generador simula el hato día a día: servicio → palpación → parto (283 días) → secado (60 días antes del parto), con descarte de vacas, ventas de crías, mastitis, vacunas y rotación de potreros. La producción sigue una curva de lactancia por vaca (pico a las 6–8 semanas), con ordeño de mañana (~54%) y de tarde (~46%).

## Qué contiene

| Tabla (CSV) | Filas | Notas |
|---|---|---|
| `animales` | 123 | 48 activos al corte: 28 vacas, 11 novillas, 8 terneras y 1 toro; el resto vendidos o muertos |
| `eventos` | 1.291 | partos, servicios, palpaciones, secados, destetes, pesajes, tratamientos, traslados, ventas, compra, muertes |
| `eventos_animales` | ~4.800 | animales de cada evento (los grupales tocan varios) |
| `produccion_leche` | ~51.400 | **una fila por vaca, día y ordeño** (`manana` / `tarde`) con litros y `destino` |
| `potreros` | 8 | 4 de ordeño en rotación, novillas, secas, parto y crías |
| `usuarios` | 3 | dueña, mayordomo y vaquero |
| `productos_sanitarios` | 4 | con tiempos de retiro **ficticios** |
| `alias_animales` | 5 | "la Mona", "la Pintada"… |

Sin levante ni ceba: los terneros machos se venden a los 5–10 días. Se mantienen las terneras y novillas de reemplazo (la mitad de las hembras nacidas), porque sin ellas el hato no se renueva.

Rendimiento: ~18,7 L por vaca en lactancia al día; la finca saca ~450 L/día con ~24 vacas ordeñadas.

## Estado calculado (vistas SQLite)

El estado nunca se guarda: se calcula desde los eventos.

- `estado_animal`: categoría, estado reproductivo (`vacia`/`servida`/`prenada`), estado productivo (`lactando`/`seca`), días en leche, días abiertos, fecha probable de parto, potrero actual.
- `vacas_abiertas`, `proximas_a_parir`
- `produccion_diaria` (por vaca) y `produccion_finca_diaria`
- `animales_en_retiro_leche`, `ultima_aplicacion`, `potrero_actual`, `peso_actual`

"Hoy" sale de `config.fecha_demo` (2026-11-07) para que los resultados no cambien con el tiempo.

## Casos difíciles a propósito

| Caso | Dónde |
|---|---|
| Números parecidos (24, 214, 241) | Canela (Jersey), Mona (Normando) y Estrella (Holstein): obligan a preguntar |
| Alias y descripciones | 214 "la Mona", 241 "la Pintada", 118 "la de la oreja cortada" |
| Vacas abiertas más de 150 días | 154, 102, 192, 208 y 311 |
| Próximas a parir | 9 vacas y novillas con parto estimado en los próximos 45 días |
| Leche en retiro vigente | La 227 (mastitis, retiro hasta el 11 nov): su leche de hoy está como `descarte` |
| Evento anulado y corregido | Parto de jun 2025 registrado en la vaca equivocada (id 673 → corregido en id 674) |
| Pesaje sospechoso | Evento `pendiente` de 4.120 kg en la vaca 118 (debe alertar) |
| Vacunación incompleta | Ciclo de aftosa de nov 2026: 25 de 45 animales vacunados, 20 pendientes |
| Ordeño de la tarde de hoy | Todavía sin registrar |

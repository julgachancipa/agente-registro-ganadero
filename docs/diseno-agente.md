# Diseño del agente

## Flujo principal

```
Mensaje (audio/texto)
   │
   ├─ audio → transcripción
   ▼
Agente (LLM + herramientas)
   ├─ separa el mensaje en uno o varios eventos
   ├─ resuelve cada animal (buscar_animal) → si es ambiguo, pregunta
   ├─ resuelve fechas relativas ("ayer", "el martes") con la FECHA DEL MENSAJE
   ▼
Validaciones de negocio (código)
   ├─ errores → se explican al usuario
   ├─ alertas → se muestran junto al resumen
   ▼
Resumen + confirmación
   ├─ "Registro: parto de la 214, cría hembra, 7 nov, potrero 3. ¿Confirmo?"
   ▼
Escritura del evento (estado: confirmado) → respuesta
```

## Niveles de confirmación

| Riesgo | Eventos | Confirmación |
|---|---|---|
| Bajo | traslado de potrero, producción de leche | Implícita (se informa y se puede deshacer) |
| Medio | parto, servicio, palpación, pesaje, secado | Explícita, puede ir en bloque |
| Alto | venta, compra, muerte, tratamiento con tiempo de retiro | Explícita e individual |

## Identificación de animales

El problema más difícil. Un mismo animal puede ser "la 214", "la Mona", "la hija de la Mona", "la de la oreja cortada".

- `buscar_animal(texto)` hace coincidencia aproximada sobre número de chapeta, nombre, alias y descripción.
- Devuelve candidatos con puntaje; si hay más de uno plausible → pregunta ("¿La 214 Normanda o la 241 Holstein?").
- `agregar_alias(animal_id, alias)` cuando el usuario aclara ("la Mona es la 214").

## Herramientas

### Escritura (requieren confirmación)
- `registrar_parto(madre, fecha, cria_sexo, cria_numero?, potrero?, observaciones?)`
- `registrar_servicio(animal, fecha, tipo: monta|IA, toro_o_pajilla?)`
- `registrar_palpacion(animal, fecha, resultado: preñada|vacía, meses_gestacion?)`
- `registrar_secado(animal, fecha)`
- `registrar_pesaje(animal, fecha, peso_kg)`
- `registrar_tratamiento(animales[], fecha, producto, dosis?, via?, dias_retiro_leche?, dias_retiro_carne?)`
- `registrar_traslado(animales[] | grupo, potrero_destino, fecha)`
- `registrar_venta(animales[], fecha, comprador?, precio?, peso?)`
- `registrar_compra(...)` / `registrar_muerte(animal, fecha, causa?)`
- `registrar_produccion_leche(fecha, ordeno: manana|tarde, registros[{animal, litros}])`: va a la tabla `produccion_leche`, no al log de eventos; se confirma en bloque ("Ordeño de la mañana: 214 → 12 L, 230 → 9 L. ¿Confirmo?")
- `anular_evento(evento_id, motivo)`: las correcciones anulan y rehacen, nunca editan en silencio.

### Lectura (consultas predefinidas, sin SQL libre)
- `estado_animal(animal)`: historia y estado derivado
- `listar_animales(filtros)`: categoría, potrero, estado reproductivo
- `vacas_abiertas(dias_minimos)`
- `proximas_a_parir(dias)`
- `pendientes_vacuna(producto)`
- `inventario_por_categoria()`: conteo para ciclos de vacunación del ICA
- `produccion_animal(animal, desde, hasta)`: litros por día y por ordeño de una vaca
- `produccion_finca(desde, hasta)`: litros diarios de la finca y cuánto fue al tanque
- `leche_en_retiro()`: animales cuya leche va a descarte y hasta cuándo
- `exportar(formato: csv|xlsx, rango?)`

## Mensajes con varios eventos

"Hoy parió la 214 y la 230, y pasé las horras al potrero 5" → 3 eventos (2 partos + 1 traslado de grupo). Se confirman en un solo resumen numerado.

## Usuarios y permisos

| Rol | Puede |
|---|---|
| Dueño | Todo, incluidas correcciones y exportación |
| Mayordomo | Registrar y consultar |
| Vaquero | Registrar |

Cada evento guarda quién lo reportó y el mensaje original (texto + referencia al audio).

## Conectividad

Los mensajes pueden llegar con horas de retraso. Las fechas relativas siempre se resuelven contra el timestamp del mensaje, no contra el momento de procesamiento.

## Seguridad sanitaria

Dosis, tiempos de retiro y calendarios sanitarios **nunca** salen de la memoria del modelo: vienen de tablas verificadas en la base de datos.

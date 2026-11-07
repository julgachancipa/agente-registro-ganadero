# Evaluación

Cada caso en `casos.jsonl` tiene un mensaje (o transcripción) y los eventos esperados. Se mide precisión **por campo**:

- Animal correcto
- Tipo de evento
- Fecha (resuelta contra `enviado_en`)
- Valores (sexo de la cría, peso, potrero…)
- Pregunta de aclaración cuando corresponde (`"espera_pregunta": true`)

Meta inicial: 100–200 casos, mezclando texto y audios reales, con varios eventos por mensaje, fechas relativas, alias y errores de transcripción.

Correr las evals ante cada cambio de prompt, modelo o herramientas.

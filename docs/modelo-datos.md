# Modelo de datos

## Entidades

- **Finca**: unidad de aislamiento de datos (multi-tenant).
- **Usuario**: teléfono de WhatsApp, rol por finca.
- **Animal**: ID interno, número de chapeta/arete, nombre, sexo, raza, fecha de nacimiento, madre, padre o pajilla, origen (nacido | comprado).
- **Alias**: nombres alternativos de un animal ("la Mona", "la pintada").
- **Potrero**: nombre, área (ha).
- **Evento**: tipo, fecha del hecho, animal(es), potrero, datos específicos (JSON), reportado_por, mensaje original, estado (pendiente | confirmado | anulado), evento que anula.

## Estado derivado (nunca se guarda a mano)

Se calcula desde los eventos confirmados y no anulados:

| Campo | Se deriva de |
|---|---|
| Categoría (ternera, novilla, vaca…) | sexo + edad + partos |
| Estado reproductivo (vacía, servida, preñada) | último servicio / palpación / parto |
| Estado productivo (lactando, seca) | último parto / secado |
| Días abiertos | último parto → servicio con preñez confirmada |
| Potrero actual | último traslado |
| Activo | ausencia de venta o muerte |
| Peso actual y ganancia diaria | pesajes |

Se implementa como vistas (o vista materializada si crece).

## Tipos de evento

parto, servicio, palpacion, secado, destete, pesaje, tratamiento, traslado, venta, compra, muerte, produccion_leche, anulacion.

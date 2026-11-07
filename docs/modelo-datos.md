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

parto, servicio, palpacion, secado, destete, pesaje, tratamiento, traslado, venta, compra, muerte.

Las correcciones no son un tipo de evento: el evento errado queda en estado `anulado` (con `motivo_anulacion`) y `anulado_por` apunta al evento que lo corrige.

## Producción de leche (tabla propia)

La leche no se guarda como evento: son decenas de miles de registros (cada vaca, dos ordeños al día), así que va en `produccion_leche`, con **una fila por vaca, día y ordeño**:

| Columna | Descripción |
|---|---|
| `animal_id`, `fecha` | Vaca y día |
| `ordeno` | `manana` o `tarde` |
| `litros` | Litros de ese ordeño |
| `destino` | `tanque`, `descarte` (en retiro por antibiótico) o `calostro` (primeros días tras el parto) |
| `registrado_por` | Usuario que reportó el ordeño |

`UNIQUE (animal_id, fecha, ordeno)`: un segundo reporte del mismo ordeño reemplaza al anterior (con confirmación). El `destino` se decide en código a partir de los eventos (`tratamiento` con `retiro_leche_hasta`, fecha del último parto), no lo decide el modelo.

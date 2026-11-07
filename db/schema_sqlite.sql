-- Esquema SQLite para el demo (equivalente al de Postgres en schema.sql).
-- Los datos se cargan desde data/demo/*.csv con scripts/cargar_demo.py.

CREATE TABLE config (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

CREATE TABLE fincas (
    id        INTEGER PRIMARY KEY,
    nombre    TEXT NOT NULL,
    municipio TEXT,
    creada_en TEXT
);

CREATE TABLE usuarios (
    id       INTEGER PRIMARY KEY,
    telefono TEXT NOT NULL UNIQUE,
    nombre   TEXT
);

CREATE TABLE usuarios_fincas (
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    finca_id   INTEGER NOT NULL REFERENCES fincas(id),
    rol        TEXT NOT NULL CHECK (rol IN ('dueno', 'mayordomo', 'vaquero')),
    PRIMARY KEY (usuario_id, finca_id)
);

CREATE TABLE potreros (
    id       INTEGER PRIMARY KEY,
    finca_id INTEGER NOT NULL REFERENCES fincas(id),
    nombre   TEXT NOT NULL,
    area_ha  REAL,
    UNIQUE (finca_id, nombre)
);

CREATE TABLE animales (
    id               INTEGER PRIMARY KEY,
    finca_id         INTEGER NOT NULL REFERENCES fincas(id),
    numero           TEXT,                 -- chapeta / arete
    nombre           TEXT,
    sexo             TEXT NOT NULL CHECK (sexo IN ('H', 'M')),
    raza             TEXT,
    fecha_nacimiento TEXT,
    madre_id         INTEGER REFERENCES animales(id),
    padre_id         INTEGER REFERENCES animales(id),
    pajilla          TEXT,
    origen           TEXT NOT NULL DEFAULT 'nacido' CHECK (origen IN ('nacido', 'comprado')),
    descripcion      TEXT,
    creado_en        TEXT,
    UNIQUE (finca_id, numero)
);

CREATE TABLE alias_animales (
    animal_id INTEGER NOT NULL REFERENCES animales(id),
    alias     TEXT NOT NULL,
    PRIMARY KEY (animal_id, alias)
);

CREATE TABLE mensajes (
    id            INTEGER PRIMARY KEY,
    finca_id      INTEGER NOT NULL REFERENCES fincas(id),
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
    enviado_en    TEXT NOT NULL,           -- base para resolver "ayer", "el martes"
    recibido_en   TEXT NOT NULL,
    texto         TEXT,
    audio_url     TEXT,
    transcripcion TEXT
);

-- Log de eventos del hato. La producción de leche NO va aquí (ver produccion_leche).
CREATE TABLE eventos (
    id               INTEGER PRIMARY KEY,
    finca_id         INTEGER NOT NULL REFERENCES fincas(id),
    tipo             TEXT NOT NULL CHECK (tipo IN (
                        'parto', 'servicio', 'palpacion', 'secado', 'destete', 'pesaje',
                        'tratamiento', 'traslado', 'venta', 'compra', 'muerte')),
    fecha            TEXT NOT NULL,        -- fecha del hecho, no del registro
    potrero_id       INTEGER REFERENCES potreros(id),
    datos            TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(datos)),
    estado           TEXT NOT NULL DEFAULT 'pendiente'
                     CHECK (estado IN ('pendiente', 'confirmado', 'anulado')),
    anulado_por      INTEGER REFERENCES eventos(id),  -- evento que corrige a este
    motivo_anulacion TEXT,
    mensaje_id       INTEGER REFERENCES mensajes(id),
    reportado_por    INTEGER NOT NULL REFERENCES usuarios(id),
    creado_en        TEXT
);

CREATE TABLE eventos_animales (
    evento_id INTEGER NOT NULL REFERENCES eventos(id),
    animal_id INTEGER NOT NULL REFERENCES animales(id),
    PRIMARY KEY (evento_id, animal_id)
);

CREATE TABLE productos_sanitarios (
    id                INTEGER PRIMARY KEY,
    nombre            TEXT NOT NULL UNIQUE,
    principio_activo  TEXT,
    dias_retiro_leche INTEGER,
    dias_retiro_carne INTEGER,
    fuente            TEXT NOT NULL
);

-- Un registro por vaca, por día y por ordeño (mañana / tarde).
CREATE TABLE produccion_leche (
    id             INTEGER PRIMARY KEY,
    finca_id       INTEGER NOT NULL REFERENCES fincas(id),
    animal_id      INTEGER NOT NULL REFERENCES animales(id),
    fecha          TEXT NOT NULL,
    ordeno         TEXT NOT NULL CHECK (ordeno IN ('manana', 'tarde')),
    litros         REAL NOT NULL CHECK (litros >= 0),
    destino        TEXT NOT NULL DEFAULT 'tanque'
                   CHECK (destino IN ('tanque', 'descarte', 'calostro')),
    registrado_por INTEGER REFERENCES usuarios(id),
    UNIQUE (animal_id, fecha, ordeno)
);

CREATE INDEX idx_eventos_finca_tipo_fecha ON eventos (finca_id, tipo, fecha);
CREATE INDEX idx_eventos_animales_animal ON eventos_animales (animal_id);
CREATE INDEX idx_produccion_fecha ON produccion_leche (fecha);
CREATE INDEX idx_alias_texto ON alias_animales (alias);

-- ---------------------------------------------------------------------------
-- Vistas: el estado de cada animal se CALCULA desde los eventos, nunca se guarda.
-- "Hoy" sale de config.fecha_demo para que el demo sea estable; en producción
-- se reemplaza por date('now').
-- ---------------------------------------------------------------------------

CREATE VIEW hoy AS
SELECT valor AS fecha FROM config WHERE clave = 'fecha_demo';

CREATE VIEW eventos_validos AS
SELECT e.*, ea.animal_id
FROM eventos e
JOIN eventos_animales ea ON ea.evento_id = e.id
WHERE e.estado = 'confirmado';

CREATE VIEW animales_activos AS
SELECT a.*
FROM animales a
WHERE NOT EXISTS (
    SELECT 1 FROM eventos_validos ev
    WHERE ev.animal_id = a.id AND ev.tipo IN ('venta', 'muerte')
);

CREATE VIEW potrero_actual AS
SELECT animal_id, potrero_id, fecha
FROM (
    SELECT animal_id, potrero_id, fecha,
           ROW_NUMBER() OVER (PARTITION BY animal_id ORDER BY fecha DESC, id DESC) AS rn
    FROM eventos_validos
    WHERE tipo = 'traslado'
)
WHERE rn = 1;

CREATE VIEW peso_actual AS
SELECT animal_id, fecha, peso_kg
FROM (
    SELECT animal_id, fecha, json_extract(datos, '$.peso_kg') AS peso_kg,
           ROW_NUMBER() OVER (PARTITION BY animal_id ORDER BY fecha DESC, id DESC) AS rn
    FROM eventos_validos
    WHERE tipo = 'pesaje'
)
WHERE rn = 1;

CREATE VIEW estado_animal AS
WITH
base AS (
    SELECT a.*, h.fecha AS hoy,
           CAST(julianday(h.fecha) - julianday(a.fecha_nacimiento) AS INTEGER) AS edad_dias
    FROM animales_activos a, hoy h
),
ult AS (  -- último evento reproductivo
    SELECT animal_id, tipo, datos,
           ROW_NUMBER() OVER (PARTITION BY animal_id ORDER BY fecha DESC, id DESC) AS rn
    FROM eventos_validos
    WHERE tipo IN ('parto', 'servicio', 'palpacion')
),
repro AS (
    SELECT animal_id,
           CASE tipo
               WHEN 'parto'   THEN 'vacia'      -- incluye aborto
               WHEN 'servicio' THEN 'servida'
               ELSE CASE json_extract(datos, '$.resultado') WHEN 'preñada' THEN 'prenada' ELSE 'vacia' END
           END AS estado_reproductivo,
           CASE WHEN tipo = 'palpacion' AND json_extract(datos, '$.resultado') = 'preñada'
                THEN json_extract(datos, '$.fecha_probable_parto') END AS fecha_probable_parto
    FROM ult WHERE rn = 1
),
lp AS (
    SELECT animal_id, MAX(fecha) AS fecha FROM eventos_validos
    WHERE tipo = 'parto' AND json_extract(datos, '$.resultado') IN ('vivo', 'muerto')
    GROUP BY animal_id
),
ls AS (SELECT animal_id, MAX(fecha) AS fecha FROM eventos_validos WHERE tipo = 'secado' GROUP BY animal_id),
sv AS (SELECT animal_id, MAX(fecha) AS fecha FROM eventos_validos WHERE tipo = 'servicio' GROUP BY animal_id),
j AS (
    SELECT b.id AS animal_id, b.numero, b.nombre, b.sexo, b.raza, b.edad_dias, b.hoy,
           CASE WHEN b.sexo = 'M' THEN CASE WHEN b.edad_dias >= 540 THEN 'toro' ELSE 'ternero' END
                WHEN lp.fecha IS NOT NULL THEN 'vaca'
                WHEN b.edad_dias < 365 THEN 'ternera'
                ELSE 'novilla' END AS categoria,
           CASE WHEN b.sexo = 'H' AND b.edad_dias >= 365
                THEN COALESCE(r.estado_reproductivo, 'vacia') END AS estado_reproductivo,
           CASE WHEN lp.fecha IS NULL THEN NULL
                WHEN ls.fecha > lp.fecha THEN 'seca'
                ELSE 'lactando' END AS estado_productivo,
           lp.fecha AS ultimo_parto, sv.fecha AS ultimo_servicio, r.fecha_probable_parto
    FROM base b
    LEFT JOIN repro r ON r.animal_id = b.id
    LEFT JOIN lp ON lp.animal_id = b.id
    LEFT JOIN ls ON ls.animal_id = b.id
    LEFT JOIN sv ON sv.animal_id = b.id
)
SELECT j.animal_id, j.numero, j.nombre, j.sexo, j.raza, j.edad_dias, j.categoria,
       j.estado_reproductivo, j.estado_productivo, j.ultimo_parto, j.ultimo_servicio,
       j.fecha_probable_parto,
       CASE WHEN j.estado_productivo = 'lactando'
            THEN CAST(julianday(j.hoy) - julianday(j.ultimo_parto) AS INTEGER) END AS dias_en_leche,
       CASE WHEN j.ultimo_parto IS NULL OR j.estado_reproductivo IS NULL THEN NULL
            WHEN j.estado_reproductivo = 'prenada'
                 THEN CAST(julianday(j.ultimo_servicio) - julianday(j.ultimo_parto) AS INTEGER)
            ELSE CAST(julianday(j.hoy) - julianday(j.ultimo_parto) AS INTEGER) END AS dias_abiertos,
       CASE WHEN j.estado_reproductivo = 'prenada'
            THEN CAST(julianday(j.fecha_probable_parto) - julianday(j.hoy) AS INTEGER) END AS dias_para_parto,
       p.nombre AS potrero
FROM j
LEFT JOIN potrero_actual pa ON pa.animal_id = j.animal_id
LEFT JOIN potreros p ON p.id = pa.potrero_id;

CREATE VIEW vacas_abiertas AS
SELECT * FROM estado_animal
WHERE categoria = 'vaca' AND estado_reproductivo IN ('vacia', 'servida');

CREATE VIEW proximas_a_parir AS
SELECT * FROM estado_animal
WHERE estado_reproductivo = 'prenada' AND dias_para_parto IS NOT NULL;

CREATE VIEW produccion_diaria AS
SELECT animal_id, fecha,
       ROUND(SUM(litros), 1) AS litros_total,
       ROUND(SUM(CASE WHEN ordeno = 'manana' THEN litros END), 1) AS litros_manana,
       ROUND(SUM(CASE WHEN ordeno = 'tarde'  THEN litros END), 1) AS litros_tarde,
       ROUND(SUM(CASE WHEN destino = 'tanque' THEN litros ELSE 0 END), 1) AS litros_tanque
FROM produccion_leche
GROUP BY animal_id, fecha;

CREATE VIEW produccion_finca_diaria AS
SELECT fecha,
       ROUND(SUM(litros), 1) AS litros_total,
       ROUND(SUM(CASE WHEN destino = 'tanque' THEN litros ELSE 0 END), 1) AS litros_tanque,
       COUNT(DISTINCT animal_id) AS vacas_ordenadas
FROM produccion_leche
GROUP BY fecha;

-- Leche que no se puede enviar al tanque por tratamiento con antibiótico
CREATE VIEW animales_en_retiro_leche AS
SELECT animal_id, MAX(json_extract(datos, '$.retiro_leche_hasta')) AS retiro_leche_hasta
FROM eventos_validos
WHERE tipo = 'tratamiento'
  AND json_extract(datos, '$.retiro_leche_hasta') >= (SELECT fecha FROM hoy)
GROUP BY animal_id;

-- Última aplicación de cada producto por animal (para "pendientes de vacuna")
CREATE VIEW ultima_aplicacion AS
SELECT animal_id, json_extract(datos, '$.producto_id') AS producto_id, MAX(fecha) AS ultima_fecha
FROM eventos_validos
WHERE tipo = 'tratamiento'
GROUP BY animal_id, 2;

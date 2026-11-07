-- Esquema inicial (Postgres)

CREATE TABLE fincas (
    id          BIGSERIAL PRIMARY KEY,
    nombre      TEXT NOT NULL,
    municipio   TEXT,
    creada_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE usuarios (
    id          BIGSERIAL PRIMARY KEY,
    telefono    TEXT NOT NULL UNIQUE,
    nombre      TEXT
);

CREATE TABLE usuarios_fincas (
    usuario_id  BIGINT NOT NULL REFERENCES usuarios(id),
    finca_id    BIGINT NOT NULL REFERENCES fincas(id),
    rol         TEXT NOT NULL CHECK (rol IN ('dueno', 'mayordomo', 'vaquero')),
    PRIMARY KEY (usuario_id, finca_id)
);

CREATE TABLE potreros (
    id          BIGSERIAL PRIMARY KEY,
    finca_id    BIGINT NOT NULL REFERENCES fincas(id),
    nombre      TEXT NOT NULL,
    area_ha     NUMERIC(8,2),
    UNIQUE (finca_id, nombre)
);

CREATE TABLE animales (
    id               BIGSERIAL PRIMARY KEY,
    finca_id         BIGINT NOT NULL REFERENCES fincas(id),
    numero           TEXT,                -- chapeta / arete
    nombre           TEXT,
    sexo             CHAR(1) NOT NULL CHECK (sexo IN ('H', 'M')),
    raza             TEXT,
    fecha_nacimiento DATE,
    madre_id         BIGINT REFERENCES animales(id),
    padre_id         BIGINT REFERENCES animales(id),
    pajilla          TEXT,
    origen           TEXT NOT NULL DEFAULT 'nacido' CHECK (origen IN ('nacido', 'comprado')),
    descripcion      TEXT,                -- "oreja cortada", "pintada"
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (finca_id, numero)
);

CREATE TABLE alias_animales (
    animal_id   BIGINT NOT NULL REFERENCES animales(id),
    alias       TEXT NOT NULL,
    PRIMARY KEY (animal_id, alias)
);

CREATE TABLE mensajes (
    id            BIGSERIAL PRIMARY KEY,
    finca_id      BIGINT NOT NULL REFERENCES fincas(id),
    usuario_id    BIGINT NOT NULL REFERENCES usuarios(id),
    enviado_en    TIMESTAMPTZ NOT NULL,   -- timestamp de WhatsApp: base para "ayer", "el martes"
    recibido_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
    texto         TEXT,
    audio_url     TEXT,
    transcripcion TEXT
);

CREATE TABLE eventos (
    id           BIGSERIAL PRIMARY KEY,
    finca_id     BIGINT NOT NULL REFERENCES fincas(id),
    tipo         TEXT NOT NULL CHECK (tipo IN (
                    'parto', 'servicio', 'palpacion', 'secado', 'destete', 'pesaje',
                    'tratamiento', 'traslado', 'venta', 'compra', 'muerte',
                    'produccion_leche')),
    fecha        DATE NOT NULL,           -- fecha del hecho, no del registro
    potrero_id   BIGINT REFERENCES potreros(id),
    datos        JSONB NOT NULL DEFAULT '{}',
    estado       TEXT NOT NULL DEFAULT 'pendiente'
                 CHECK (estado IN ('pendiente', 'confirmado', 'anulado')),
    anulado_por  BIGINT REFERENCES eventos(id),
    motivo_anulacion TEXT,
    mensaje_id   BIGINT REFERENCES mensajes(id),
    reportado_por BIGINT NOT NULL REFERENCES usuarios(id),
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un evento puede afectar a varios animales (traslados, vacunas en grupo)
CREATE TABLE eventos_animales (
    evento_id   BIGINT NOT NULL REFERENCES eventos(id),
    animal_id   BIGINT NOT NULL REFERENCES animales(id),
    PRIMARY KEY (evento_id, animal_id)
);

CREATE INDEX idx_eventos_finca_tipo_fecha ON eventos (finca_id, tipo, fecha);
CREATE INDEX idx_eventos_animales_animal ON eventos_animales (animal_id);

-- Eventos válidos = confirmados y no anulados
CREATE VIEW eventos_validos AS
SELECT e.*, ea.animal_id
FROM eventos e
JOIN eventos_animales ea ON ea.evento_id = e.id
WHERE e.estado = 'confirmado';

-- Potrero actual de cada animal
CREATE VIEW potrero_actual AS
SELECT DISTINCT ON (animal_id) animal_id, potrero_id, fecha
FROM eventos_validos
WHERE tipo = 'traslado'
ORDER BY animal_id, fecha DESC, id DESC;

-- Animales activos (sin venta ni muerte)
CREATE VIEW animales_activos AS
SELECT a.*
FROM animales a
WHERE NOT EXISTS (
    SELECT 1 FROM eventos_validos ev
    WHERE ev.animal_id = a.id AND ev.tipo IN ('venta', 'muerte')
);

-- Tablas de referencia verificadas (dosis/retiros NO salen del modelo)
CREATE TABLE productos_sanitarios (
    id                 BIGSERIAL PRIMARY KEY,
    nombre             TEXT NOT NULL UNIQUE,
    principio_activo   TEXT,
    dias_retiro_leche  INT,
    dias_retiro_carne  INT,
    fuente             TEXT NOT NULL      -- etiqueta / registro ICA
);

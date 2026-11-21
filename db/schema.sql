BEGIN;
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS fontes_dados (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome text NOT NULL,
    endereco_url text NOT NULL,
    data_coleta timestamptz NOT NULL DEFAULT now(),
    versao text NOT NULL
);

CREATE TABLE IF NOT EXISTS barragens (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_anm text NOT NULL UNIQUE,
    nome text NOT NULL,
    municipio text NOT NULL,
    uf text NOT NULL CHECK (uf ~ '^[A-Z]{2}$'),
    categoria_risco text,
    dano_potencial text,
    geometria geometry(Point,4326),
    fonte_id bigint NOT NULL REFERENCES fontes_dados(id),
    data_atualizacao date,
    CHECK (geometria IS NULL OR (NOT ST_IsEmpty(geometria) AND
        ST_X(geometria) BETWEEN -180 AND 180 AND ST_Y(geometria) BETWEEN -90 AND 90))
);

CREATE TABLE IF NOT EXISTS eventos_sismicos (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo_origem text NOT NULL UNIQUE,
    data_hora timestamptz NOT NULL,
    magnitude double precision NOT NULL CHECK (magnitude BETWEEN -10 AND 12),
    profundidade_km double precision CHECK (profundidade_km BETWEEN -100 AND 1000),
    geometria geometry(Point,4326) NOT NULL,
    fonte_id bigint NOT NULL REFERENCES fontes_dados(id),
    CHECK (NOT ST_IsEmpty(geometria) AND ST_X(geometria) BETWEEN -180 AND 180
        AND ST_Y(geometria) BETWEEN -90 AND 90)
);

CREATE TABLE IF NOT EXISTS zonas_sismogenicas (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome text NOT NULL,
    classificacao text NOT NULL,
    descricao text NOT NULL DEFAULT '',
    metodologia text NOT NULL,
    referencia_cientifica text NOT NULL,
    geometria geometry(MultiPolygon,4326) NOT NULL,
    fonte_id bigint NOT NULL REFERENCES fontes_dados(id),
    UNIQUE (referencia_cientifica, nome),
    CHECK (NOT ST_IsEmpty(geometria) AND ST_IsValid(geometria))
);

CREATE TABLE IF NOT EXISTS analises_espaciais (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    barragem_id bigint NOT NULL REFERENCES barragens(id),
    raio_km double precision NOT NULL CHECK (raio_km > 0 AND raio_km <= 1000),
    magnitude_minima double precision NOT NULL CHECK (magnitude_minima BETWEEN -10 AND 12),
    periodo_inicio date,
    periodo_fim date,
    resultado_json jsonb NOT NULL,
    data_analise timestamptz NOT NULL DEFAULT now(),
    CHECK (periodo_inicio <= periodo_fim)
);

CREATE INDEX IF NOT EXISTS barragens_geom_gist ON barragens USING gist (geometria);
CREATE INDEX IF NOT EXISTS sismos_geom_gist ON eventos_sismicos USING gist (geometria);
CREATE INDEX IF NOT EXISTS sismos_geog_gist ON eventos_sismicos USING gist ((geometria::geography));
CREATE INDEX IF NOT EXISTS zonas_geom_gist ON zonas_sismogenicas USING gist (geometria);
CREATE INDEX IF NOT EXISTS barragens_local_idx ON barragens (uf, lower(municipio));
CREATE INDEX IF NOT EXISTS sismos_data_idx ON eventos_sismicos (data_hora);
CREATE INDEX IF NOT EXISTS analises_barragem_idx ON analises_espaciais (barragem_id);
CREATE INDEX IF NOT EXISTS barragens_fonte_idx ON barragens (fonte_id);
CREATE INDEX IF NOT EXISTS sismos_fonte_idx ON eventos_sismicos (fonte_id);
CREATE INDEX IF NOT EXISTS zonas_fonte_idx ON zonas_sismogenicas (fonte_id);
COMMIT;

-- =====================================================================
-- 01_ddl_staging.sql  |  Capa de staging (stg_)
-- Proyecto: DW de Adjudicaciones DNCP  |  Motor: DuckDB 1.5
-- Regla: staging guarda el dato crudo, todo como VARCHAR, sin limpiar.
--        La tipificación y la validación ocurren en el ETL (H3).
-- =====================================================================

-- Adjudicaciones (fuente 1: awards.csv)
CREATE TABLE stg_awards (
    stg_nro_fila        BIGINT       NOT NULL,   -- n.º de fila en el CSV
    nk_proceso          VARCHAR,                 -- compiledRelease/id (ocid)
    nk_adjudicacion     VARCHAR,                 -- compiledRelease/awards/0/id
    estado              VARCHAR,                 -- .../status
    estado_detalle      VARCHAR,                 -- .../statusDetails
    fecha_adjudicacion  VARCHAR,                 -- .../date (ISO 8601 con zona)
    monto               VARCHAR,                 -- .../value/amount
    moneda              VARCHAR,                 -- .../value/currency
    invitation_id       VARCHAR,                 -- .../invitationID
    comprador_id        VARCHAR,                 -- .../buyer/id
    comprador_nombre    VARCHAR,                 -- .../buyer/name
    related_bids        VARCHAR,                 -- .../relatedBids
    stg_archivo_origen  VARCHAR      NOT NULL,
    stg_fecha_carga     TIMESTAMP    NOT NULL DEFAULT current_timestamp,
    CONSTRAINT pk_stg_awards PRIMARY KEY (stg_nro_fila)
);

-- Proveedores adjudicados (fuente 2: awa_suppliers.csv)
CREATE TABLE stg_awa_suppliers (
    stg_nro_fila        BIGINT       NOT NULL,
    nk_proceso          VARCHAR,                 -- compiledRelease/id
    nk_adjudicacion     VARCHAR,                 -- compiledRelease/awards/0/id
    nk_proveedor        VARCHAR,                 -- .../suppliers/0/id (RUC)
    proveedor_nombre    VARCHAR,                 -- .../suppliers/0/name
    stg_archivo_origen  VARCHAR      NOT NULL,
    stg_fecha_carga     TIMESTAMP    NOT NULL DEFAULT current_timestamp,
    CONSTRAINT pk_stg_awa_suppliers PRIMARY KEY (stg_nro_fila)
);

-- Etapas del proceso (fuente 3: releases.csv)
CREATE TABLE stg_releases (
    stg_nro_fila        BIGINT       NOT NULL,
    fecha_release       VARCHAR,                 -- releases/0/date
    etapas              VARCHAR,                 -- releases/0/tag (separadas por ';')
    url_release         VARCHAR,                 -- releases/0/url (termina en el ocid)
    stg_archivo_origen  VARCHAR      NOT NULL,
    stg_fecha_carga     TIMESTAMP    NOT NULL DEFAULT current_timestamp,
    CONSTRAINT pk_stg_releases PRIMARY KEY (stg_nro_fila)
);

-- Cuarentena: registros rechazados por las reglas de calidad (se llena en el ETL)
CREATE SEQUENCE seq_stg_cuarentena START 1;
CREATE TABLE stg_cuarentena (
    id_cuarentena       BIGINT       NOT NULL DEFAULT nextval('seq_stg_cuarentena'),
    tabla_origen        VARCHAR      NOT NULL,   -- p. ej. 'stg_awards'
    stg_nro_fila        BIGINT       NOT NULL,
    regla_codigo        VARCHAR      NOT NULL,   -- p. ej. 'R03_FECHA_INVALIDA'
    motivo              VARCHAR      NOT NULL,
    valor_original      VARCHAR,
    stg_fecha_registro  TIMESTAMP    NOT NULL DEFAULT current_timestamp,
    CONSTRAINT pk_stg_cuarentena PRIMARY KEY (id_cuarentena)
);
CREATE INDEX idx_stg_cuarentena_regla ON stg_cuarentena (regla_codigo);

-- Índices de apoyo para las uniones del ETL
CREATE INDEX idx_stg_awards_adjudicacion  ON stg_awards (nk_adjudicacion);
CREATE INDEX idx_stg_awards_proceso       ON stg_awards (nk_proceso);
CREATE INDEX idx_stg_suppliers_adjudic    ON stg_awa_suppliers (nk_adjudicacion);

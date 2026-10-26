-- =====================================================================
-- 02_ddl_dimensional.sql  |  Modelo dimensional en estrella (dim_ / fact_)
-- GRANO de fact_adjudicacion: UNA FILA POR ADJUDICACIÓN
--   (identificada por nk_adjudicacion = compiledRelease/awards/0/id).
-- Convenciones: dim_ / fact_ / stg_, sk_ = clave sustituta,
--   nk_ = clave natural, pk_ / fk_ / uq_ / idx_ = restricciones e índices.
-- Miembro "no definido": sk = -1 en todas las dimensiones (ver 03_*.sql).
-- =====================================================================

-- ---------- dim_tiempo (fecha de adjudicación) ----------
CREATE TABLE dim_tiempo (
    sk_tiempo           INTEGER      NOT NULL,   -- AAAAMMDD; -1 = no definido
    nk_fecha            DATE,
    anio                SMALLINT,
    semestre            SMALLINT,
    trimestre           SMALLINT,
    mes                 SMALLINT,
    nombre_mes          VARCHAR      NOT NULL,
    dia                 SMALLINT,
    dia_semana          SMALLINT,                -- 1 = lunes ... 7 = domingo
    nombre_dia_semana   VARCHAR      NOT NULL,
    es_fin_de_semana    BOOLEAN,
    CONSTRAINT pk_dim_tiempo PRIMARY KEY (sk_tiempo),
    CONSTRAINT uq_dim_tiempo_fecha UNIQUE (nk_fecha)
);

-- ---------- dim_proveedor (SCD tipo 1) ----------
-- Tipo 1: la razón social se corrige sobrescribiendo; no se conserva historia.
CREATE SEQUENCE seq_dim_proveedor START 1;
CREATE TABLE dim_proveedor (
    sk_proveedor        INTEGER      NOT NULL DEFAULT nextval('seq_dim_proveedor'),
    nk_ruc              VARCHAR      NOT NULL,   -- p. ej. 'PY-RUC-80000146-0'
    nombre_proveedor    VARCHAR      NOT NULL,
    dim_fecha_carga     TIMESTAMP    NOT NULL DEFAULT current_timestamp,
    dim_fecha_actualiz  TIMESTAMP    NOT NULL DEFAULT current_timestamp,
    CONSTRAINT pk_dim_proveedor PRIMARY KEY (sk_proveedor),
    CONSTRAINT uq_dim_proveedor_ruc UNIQUE (nk_ruc)
);

-- ---------- dim_estado ----------
CREATE SEQUENCE seq_dim_estado START 1;
CREATE TABLE dim_estado (
    sk_estado           INTEGER      NOT NULL DEFAULT nextval('seq_dim_estado'),
    nk_estado           VARCHAR      NOT NULL,   -- estado_general || '|' || estado_detalle (normalizados)
    estado_general      VARCHAR      NOT NULL,   -- active / cancelled / closed / unsuccessful
    estado_detalle      VARCHAR      NOT NULL,   -- Adjudicado, Cancelado, ... (texto normalizado)
    CONSTRAINT pk_dim_estado PRIMARY KEY (sk_estado),
    CONSTRAINT uq_dim_estado_nk UNIQUE (nk_estado)
);

-- ---------- dim_moneda ----------
CREATE SEQUENCE seq_dim_moneda START 1;
CREATE TABLE dim_moneda (
    sk_moneda           INTEGER      NOT NULL DEFAULT nextval('seq_dim_moneda'),
    nk_codigo_moneda    VARCHAR      NOT NULL,   -- PYG, USD
    nombre_moneda       VARCHAR      NOT NULL,
    CONSTRAINT pk_dim_moneda PRIMARY KEY (sk_moneda),
    CONSTRAINT uq_dim_moneda_codigo UNIQUE (nk_codigo_moneda)
);

-- ---------- dim_comprador (institución convocante) ----------
CREATE SEQUENCE seq_dim_comprador START 1;
CREATE TABLE dim_comprador (
    sk_comprador        INTEGER      NOT NULL DEFAULT nextval('seq_dim_comprador'),
    nk_comprador        VARCHAR      NOT NULL,   -- p. ej. 'DNCP-SICP-CODE-30'
    nombre_comprador    VARCHAR      NOT NULL,
    CONSTRAINT pk_dim_comprador PRIMARY KEY (sk_comprador),
    CONSTRAINT uq_dim_comprador_nk UNIQUE (nk_comprador)
);

-- ---------- dim_etapa (etapas del proceso, desde releases) ----------
CREATE SEQUENCE seq_dim_etapa START 1;
CREATE TABLE dim_etapa (
    sk_etapa                    INTEGER   NOT NULL DEFAULT nextval('seq_dim_etapa'),
    nk_etapas                   VARCHAR   NOT NULL,  -- cadena original (tag), p. ej. 'award;contract;implementation'
    tiene_planificacion         BOOLEAN   NOT NULL,
    tiene_licitacion            BOOLEAN   NOT NULL,
    tiene_adjudicacion          BOOLEAN   NOT NULL,
    tiene_contrato              BOOLEAN   NOT NULL,
    tiene_implementacion        BOOLEAN   NOT NULL,
    tiene_modificacion_contrato BOOLEAN   NOT NULL,
    tiene_terminacion_contrato  BOOLEAN   NOT NULL,
    cantidad_etapas             SMALLINT  NOT NULL,
    CONSTRAINT pk_dim_etapa PRIMARY KEY (sk_etapa),
    CONSTRAINT uq_dim_etapa_nk UNIQUE (nk_etapas)
);

-- ---------- fact_adjudicacion ----------
CREATE TABLE fact_adjudicacion (
    nk_adjudicacion         VARCHAR       NOT NULL,   -- dimensión degenerada (id de la adjudicación)
    nk_proceso              VARCHAR       NOT NULL,   -- dimensión degenerada (ocid del proceso)
    sk_tiempo               INTEGER       NOT NULL,
    sk_proveedor            INTEGER       NOT NULL,
    sk_estado               INTEGER       NOT NULL,
    sk_moneda               INTEGER       NOT NULL,
    sk_comprador            INTEGER       NOT NULL,
    sk_etapa                INTEGER       NOT NULL,
    monto_adjudicado        DECIMAL(22,2) NOT NULL,   -- en la moneda indicada por sk_moneda
    cantidad_adjudicaciones SMALLINT      NOT NULL DEFAULT 1,  -- medida aditiva (contador)
    fact_fecha_carga        TIMESTAMP     NOT NULL DEFAULT current_timestamp,
    CONSTRAINT pk_fact_adjudicacion PRIMARY KEY (nk_adjudicacion),
    CONSTRAINT ck_fact_adj_monto CHECK (monto_adjudicado > 0),
    CONSTRAINT fk_fact_adj_tiempo    FOREIGN KEY (sk_tiempo)    REFERENCES dim_tiempo (sk_tiempo),
    CONSTRAINT fk_fact_adj_proveedor FOREIGN KEY (sk_proveedor) REFERENCES dim_proveedor (sk_proveedor),
    CONSTRAINT fk_fact_adj_estado    FOREIGN KEY (sk_estado)    REFERENCES dim_estado (sk_estado),
    CONSTRAINT fk_fact_adj_moneda    FOREIGN KEY (sk_moneda)    REFERENCES dim_moneda (sk_moneda),
    CONSTRAINT fk_fact_adj_comprador FOREIGN KEY (sk_comprador) REFERENCES dim_comprador (sk_comprador),
    CONSTRAINT fk_fact_adj_etapa     FOREIGN KEY (sk_etapa)     REFERENCES dim_etapa (sk_etapa)
);

-- Índices sobre las claves foráneas (consultas OLAP)
CREATE INDEX idx_fact_adj_tiempo    ON fact_adjudicacion (sk_tiempo);
CREATE INDEX idx_fact_adj_proveedor ON fact_adjudicacion (sk_proveedor);
CREATE INDEX idx_fact_adj_estado    ON fact_adjudicacion (sk_estado);
CREATE INDEX idx_fact_adj_moneda    ON fact_adjudicacion (sk_moneda);
CREATE INDEX idx_fact_adj_comprador ON fact_adjudicacion (sk_comprador);
CREATE INDEX idx_fact_adj_etapa     ON fact_adjudicacion (sk_etapa);
CREATE INDEX idx_fact_adj_proceso   ON fact_adjudicacion (nk_proceso);

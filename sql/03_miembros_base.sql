-- =====================================================================
-- 03_miembros_base.sql  |  Miembro "no definido" (sk = -1) y calendario
-- =====================================================================
INSERT INTO dim_proveedor (sk_proveedor, nk_ruc, nombre_proveedor)
VALUES (-1, 'NO DEFINIDO', 'No definido');

INSERT INTO dim_estado (sk_estado, nk_estado, estado_general, estado_detalle)
VALUES (-1, 'NO DEFINIDO|NO DEFINIDO', 'No definido', 'No definido');

INSERT INTO dim_moneda (sk_moneda, nk_codigo_moneda, nombre_moneda)
VALUES (-1, 'N/D', 'No definido');

INSERT INTO dim_comprador (sk_comprador, nk_comprador, nombre_comprador)
VALUES (-1, 'NO DEFINIDO', 'No definido');

INSERT INTO dim_etapa (sk_etapa, nk_etapas, tiene_planificacion, tiene_licitacion,
    tiene_adjudicacion, tiene_contrato, tiene_implementacion,
    tiene_modificacion_contrato, tiene_terminacion_contrato, cantidad_etapas)
VALUES (-1, 'NO DEFINIDO', false, false, false, false, false, false, false, 0);

INSERT INTO dim_tiempo (sk_tiempo, nk_fecha, anio, semestre, trimestre, mes, nombre_mes,
    dia, dia_semana, nombre_dia_semana, es_fin_de_semana)
VALUES (-1, NULL, NULL, NULL, NULL, NULL, 'No definido', NULL, NULL, 'No definido', NULL);

-- Calendario 2015-01-01 a 2026-12-31 (las fechas fuera de rango van a cuarentena)
INSERT INTO dim_tiempo
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER),
    CAST(d AS DATE),
    CAST(year(d) AS SMALLINT),
    CAST(CASE WHEN month(d) <= 6 THEN 1 ELSE 2 END AS SMALLINT),
    CAST(quarter(d) AS SMALLINT),
    CAST(month(d) AS SMALLINT),
    CASE month(d) WHEN 1 THEN 'Enero' WHEN 2 THEN 'Febrero' WHEN 3 THEN 'Marzo'
        WHEN 4 THEN 'Abril' WHEN 5 THEN 'Mayo' WHEN 6 THEN 'Junio'
        WHEN 7 THEN 'Julio' WHEN 8 THEN 'Agosto' WHEN 9 THEN 'Septiembre'
        WHEN 10 THEN 'Octubre' WHEN 11 THEN 'Noviembre' ELSE 'Diciembre' END,
    CAST(day(d) AS SMALLINT),
    CAST(isodow(d) AS SMALLINT),
    CASE isodow(d) WHEN 1 THEN 'Lunes' WHEN 2 THEN 'Martes' WHEN 3 THEN 'Miércoles'
        WHEN 4 THEN 'Jueves' WHEN 5 THEN 'Viernes' WHEN 6 THEN 'Sábado' ELSE 'Domingo' END,
    isodow(d) >= 6
FROM generate_series(DATE '2015-01-01', DATE '2026-12-31', INTERVAL 1 DAY) AS t(d);

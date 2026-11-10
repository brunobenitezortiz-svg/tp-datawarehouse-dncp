-- 06 - Controles de integridad, rechazos, dimensiones y traza de procedencia.
SELECT 'stg_awards' AS tabla, COUNT(*) AS filas FROM stg_awards
UNION ALL SELECT 'stg_awa_suppliers', COUNT(*) FROM stg_awa_suppliers
UNION ALL SELECT 'stg_releases', COUNT(*) FROM stg_releases
UNION ALL SELECT 'fact_adjudicacion', COUNT(*) FROM fact_adjudicacion;

SELECT regla_codigo, tabla_origen, COUNT(*) AS registros
FROM stg_cuarentena GROUP BY regla_codigo, tabla_origen ORDER BY regla_codigo;

SELECT COUNT(*) AS filas_fact, COUNT(DISTINCT nk_adjudicacion) AS claves_distintas,
       COUNT(*) FILTER (WHERE sk_proveedor=-1) AS proveedor_no_definido,
       COUNT(*) FILTER (WHERE sk_comprador=-1) AS comprador_no_definido,
       COUNT(*) FILTER (WHERE sk_etapa=-1) AS etapa_no_definida
FROM fact_adjudicacion;

SELECT m.nk_codigo_moneda AS moneda, COUNT(*) AS adjudicaciones,
       SUM(f.monto_adjudicado) AS monto_en_moneda_original
FROM fact_adjudicacion f JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
GROUP BY m.nk_codigo_moneda ORDER BY moneda;

SELECT 'dim_tiempo' AS tabla, COUNT(*) AS filas FROM dim_tiempo
UNION ALL SELECT 'dim_proveedor', COUNT(*) FROM dim_proveedor
UNION ALL SELECT 'dim_estado', COUNT(*) FROM dim_estado
UNION ALL SELECT 'dim_moneda', COUNT(*) FROM dim_moneda
UNION ALL SELECT 'dim_comprador', COUNT(*) FROM dim_comprador
UNION ALL SELECT 'dim_etapa', COUNT(*) FROM dim_etapa;

-- Revisión de RUC no convencionales: hallazgos, NO errores descartados.
SELECT COUNT(*) AS filas_no_convencionales,
       COUNT(DISTINCT nk_proveedor) AS identificadores_distintos
FROM stg_awa_suppliers
WHERE NOT regexp_full_match(trim(nk_proveedor),'PY-RUC-[0-9]+-[0-9]');

-- =====================================================================
-- 04_verificacion_staging.sql  |  Controles posteriores a la carga
-- =====================================================================
SELECT 'stg_awards' AS tabla, COUNT(*) AS filas FROM stg_awards
UNION ALL SELECT 'stg_awa_suppliers', COUNT(*) FROM stg_awa_suppliers
UNION ALL SELECT 'stg_releases', COUNT(*) FROM stg_releases;

-- Unicidad de la clave de grano (adjudicación) en awards
SELECT COUNT(*) AS filas, COUNT(DISTINCT nk_adjudicacion) AS adjudicaciones_distintas
FROM stg_awards;

-- Correspondencia awards -> proveedores
SELECT COUNT(*) AS adjudicaciones_con_proveedor
FROM stg_awards a
WHERE EXISTS (SELECT 1 FROM stg_awa_suppliers s WHERE s.nk_adjudicacion = a.nk_adjudicacion);

-- Adjudicaciones con más de un proveedor
SELECT nk_adjudicacion, COUNT(*) AS filas_proveedor
FROM stg_awa_suppliers GROUP BY 1 HAVING COUNT(*) > 1 ORDER BY 2 DESC;

-- Correspondencia awards -> releases (el ocid es el último tramo de la URL)
SELECT COUNT(*) AS adjudicaciones_con_release
FROM stg_awards a
WHERE EXISTS (SELECT 1 FROM stg_releases r
              WHERE regexp_extract(r.url_release, '[^/]+$') = a.nk_proceso);

-- Completitud de campos clave en awards
SELECT COUNT(*) FILTER (WHERE fecha_adjudicacion IS NULL) AS fecha_nula,
       COUNT(*) FILTER (WHERE monto IS NULL)              AS monto_nulo,
       COUNT(*) FILTER (WHERE estado IS NULL)             AS estado_nulo,
       COUNT(*) FILTER (WHERE comprador_id IS NULL)       AS comprador_nulo
FROM stg_awards;

-- P6 | Etapas NO mutuamente excluyentes: un proceso puede contar en varias.
-- Cada porcentaje se calcula sobre el total de adjudicaciones válidas.
WITH conteos AS (
 SELECT COUNT(*) AS total,
        SUM(CAST(e.tiene_planificacion AS INTEGER)) AS planificacion,
        SUM(CAST(e.tiene_licitacion AS INTEGER)) AS licitacion,
        SUM(CAST(e.tiene_adjudicacion AS INTEGER)) AS adjudicacion,
        SUM(CAST(e.tiene_contrato AS INTEGER)) AS contrato,
        SUM(CAST(e.tiene_implementacion AS INTEGER)) AS implementacion,
        SUM(CAST(e.tiene_modificacion_contrato AS INTEGER)) AS modificacion,
        SUM(CAST(e.tiene_terminacion_contrato AS INTEGER)) AS terminacion,
        SUM(CASE WHEN e.sk_etapa=-1 THEN 1 ELSE 0 END) AS sin_etapa
 FROM fact_adjudicacion f JOIN dim_etapa e ON f.sk_etapa=e.sk_etapa
), etapas AS (
 SELECT 1 AS orden,'Planificación' AS etapa,planificacion AS adjudicaciones,total FROM conteos
 UNION ALL SELECT 2,'Licitación',licitacion,total FROM conteos
 UNION ALL SELECT 3,'Adjudicación',adjudicacion,total FROM conteos
 UNION ALL SELECT 4,'Contrato',contrato,total FROM conteos
 UNION ALL SELECT 5,'Implementación',implementacion,total FROM conteos
 UNION ALL SELECT 6,'Modificación del contrato',modificacion,total FROM conteos
 UNION ALL SELECT 7,'Terminación del contrato',terminacion,total FROM conteos
 UNION ALL SELECT 8,'No definido',sin_etapa,total FROM conteos
)
SELECT etapa, adjudicaciones, ROUND(100.0 * adjudicaciones / NULLIF(total,0),4) AS porcentaje_total
FROM etapas ORDER BY orden;

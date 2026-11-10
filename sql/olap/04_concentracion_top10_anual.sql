-- P4 | Drill-down temporal: top 10 DIFERENTE en cada año, solo PYG.
WITH por_proveedor AS (
 SELECT t.anio, p.nk_ruc, SUM(f.monto_adjudicado) AS monto
 FROM fact_adjudicacion f
 JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
 JOIN dim_proveedor p ON f.sk_proveedor=p.sk_proveedor
 JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
 WHERE m.nk_codigo_moneda='PYG'
 GROUP BY t.anio, p.nk_ruc
), ranking AS (
 SELECT anio, nk_ruc, monto,
        ROW_NUMBER() OVER (PARTITION BY anio ORDER BY monto DESC,nk_ruc) AS puesto
 FROM por_proveedor
)
SELECT anio, SUM(CASE WHEN puesto<=10 THEN monto ELSE 0 END) AS monto_top10,
       SUM(monto) AS monto_total,
       ROUND(100.0*SUM(CASE WHEN puesto<=10 THEN monto ELSE 0 END)/NULLIF(SUM(monto),0),4) AS porcentaje
FROM ranking GROUP BY anio ORDER BY anio;

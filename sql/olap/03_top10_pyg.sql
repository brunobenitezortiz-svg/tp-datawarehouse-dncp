-- P3 | Slice PYG + top 10 de proveedores sobre todo el conjunto temporal válido.
WITH por_proveedor AS (
 SELECT p.nk_ruc, p.nombre_proveedor,
        COUNT(*) AS adjudicaciones, SUM(f.monto_adjudicado) AS monto
 FROM fact_adjudicacion f
 JOIN dim_proveedor p ON f.sk_proveedor=p.sk_proveedor
 JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
 WHERE m.nk_codigo_moneda='PYG'
 GROUP BY p.nk_ruc, p.nombre_proveedor
), total AS (SELECT SUM(monto) AS importe FROM por_proveedor)
SELECT ROW_NUMBER() OVER (ORDER BY p.monto DESC, p.nk_ruc) AS puesto,
       p.nk_ruc, p.nombre_proveedor, p.adjudicaciones, p.monto,
       ROUND(p.monto * 100.0 / NULLIF(t.importe,0), 4) AS porcentaje_total_pyg
FROM por_proveedor p CROSS JOIN total t
QUALIFY ROW_NUMBER() OVER (ORDER BY p.monto DESC, p.nk_ruc) <= 10
ORDER BY puesto;

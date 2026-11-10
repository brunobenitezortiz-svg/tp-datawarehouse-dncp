-- P5 | Un proveedor es recurrente en un año cuando posee > 10 adjudicaciones ESE AÑO.
-- Se generan porcentajes independientes para PYG y USD.
WITH recuentos AS (
 SELECT t.anio, m.nk_codigo_moneda AS moneda, f.sk_proveedor,
        COUNT(*) AS adjudicaciones_proveedor, SUM(f.monto_adjudicado) AS monto
 FROM fact_adjudicacion f
 JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
 JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
 GROUP BY t.anio,m.nk_codigo_moneda,f.sk_proveedor
)
SELECT anio,moneda,
       SUM(CASE WHEN adjudicaciones_proveedor>10 THEN monto ELSE 0 END) AS monto_recurrentes,
       SUM(monto) AS monto_total,
       ROUND(100.0*SUM(CASE WHEN adjudicaciones_proveedor>10 THEN monto ELSE 0 END)/NULLIF(SUM(monto),0),4) AS porcentaje,
       COUNT(*) FILTER (WHERE adjudicaciones_proveedor>10) AS proveedores_recurrentes
FROM recuentos GROUP BY anio,moneda ORDER BY anio,moneda;

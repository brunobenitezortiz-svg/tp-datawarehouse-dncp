-- P2 | CUBE: cantidad y promedio por año/estado, con subtotales por moneda.
-- Si anio o estado salen NULL, la columna nivel aclara el subtotal correspondiente.
SELECT m.nk_codigo_moneda AS moneda, t.anio,
       e.estado_general,
       GROUPING(t.anio) AS agregado_anios,
       GROUPING(e.estado_general) AS agregado_estados,
       SUM(f.cantidad_adjudicaciones) AS adjudicaciones,
       SUM(f.monto_adjudicado) AS monto,
       ROUND(AVG(f.monto_adjudicado),2) AS promedio
FROM fact_adjudicacion f
JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
JOIN dim_estado e ON f.sk_estado=e.sk_estado
JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
GROUP BY m.nk_codigo_moneda, CUBE(t.anio, e.estado_general)
ORDER BY moneda, agregado_anios, t.anio, agregado_estados, estado_general;

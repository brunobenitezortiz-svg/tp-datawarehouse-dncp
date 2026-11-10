-- OPERADORES DE REFINAMIENTO (cinco de seis requeridos; basta con cuatro).
-- Ejecutar las cinco sentencias por separado en DBeaver.

-- 1) ROLL-UP: mes -> año, monto PYG; GROUPING SETS sin mezclar monedas.
SELECT t.anio, t.mes, GROUPING(t.mes) AS es_total_anual,
       SUM(f.monto_adjudicado) AS monto_pyg
FROM fact_adjudicacion f
JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
WHERE m.nk_codigo_moneda='PYG'
GROUP BY ROLLUP (t.anio,t.mes)
HAVING GROUPING(t.anio)=0
ORDER BY t.anio, es_total_anual,t.mes;

-- 2) DRILL-DOWN: navegar de 2024 al detalle mensual (PYG).
SELECT t.anio, t.mes, SUM(f.monto_adjudicado) AS monto_pyg
FROM fact_adjudicacion f
JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
WHERE t.anio=2024 AND m.nk_codigo_moneda='PYG'
GROUP BY t.anio,t.mes ORDER BY t.anio,t.mes;

-- 3) SLICE: recortar el cubo a una sola moneda, PYG.
SELECT e.estado_general,COUNT(*) AS adjudicaciones,SUM(f.monto_adjudicado) AS monto_pyg
FROM fact_adjudicacion f
JOIN dim_estado e ON f.sk_estado=e.sk_estado
JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
WHERE m.nk_codigo_moneda='PYG'
GROUP BY e.estado_general ORDER BY monto_pyg DESC;

-- 4) DICE: subcubo con más de una restricción (2023-24, PYG, estados activos).
SELECT t.anio,e.estado_general,COUNT(*) AS adjudicaciones,
       SUM(f.monto_adjudicado) AS monto_pyg
FROM fact_adjudicacion f
JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
JOIN dim_estado e ON f.sk_estado=e.sk_estado
JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
WHERE t.anio IN (2023,2024) AND m.nk_codigo_moneda='PYG'
      AND e.estado_general IN ('ACTIVE','CLOSED')
GROUP BY t.anio,e.estado_general ORDER BY t.anio,e.estado_general;

-- 5) PIVOT: columnas para años; salida transpuesta por estado (PYG).
SELECT e.estado_general,
       SUM(CASE WHEN t.anio=2022 THEN f.monto_adjudicado ELSE 0 END) AS pyg_2022,
       SUM(CASE WHEN t.anio=2023 THEN f.monto_adjudicado ELSE 0 END) AS pyg_2023,
       SUM(CASE WHEN t.anio=2024 THEN f.monto_adjudicado ELSE 0 END) AS pyg_2024
FROM fact_adjudicacion f
JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
JOIN dim_estado e ON f.sk_estado=e.sk_estado
JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
WHERE m.nk_codigo_moneda='PYG' AND t.anio IN (2022,2023,2024)
GROUP BY e.estado_general ORDER BY e.estado_general;

-- NO se declara drill-across, porque el modelo solo tiene una tabla de hechos.

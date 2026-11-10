-- P1 | GROUPING SETS + roll-up: suma por año/mes/moneda y subtotal anual POR MONEDA.
-- Monedas distintas nunca se suman entre sí.
SELECT t.anio, t.mes, m.nk_codigo_moneda AS moneda,
       CASE WHEN GROUPING(t.mes) = 1 THEN 'TOTAL ANUAL' ELSE 'MES' END AS nivel,
       SUM(f.cantidad_adjudicaciones) AS adjudicaciones,
       SUM(f.monto_adjudicado) AS monto
FROM fact_adjudicacion f
JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
GROUP BY GROUPING SETS ((t.anio, t.mes, m.nk_codigo_moneda),
                        (t.anio, m.nk_codigo_moneda))
ORDER BY t.anio, moneda, GROUPING(t.mes), t.mes;

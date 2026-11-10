"""Exporta vistas para actualizar Excel DESDE fact_adjudicacion y dimensiones.

Ejecutar después de cargar_h3.py: python src/exportar_dashboard.py
Usa únicamente la capa dimensional, nunca CSV crudos.
"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'db' / 'dncp_dw.duckdb'
OUT = ROOT / 'dashboard' / 'datos'
OLAP = ROOT / 'sql' / 'olap'

CONSULTAS = {
  'p1_ventas_anio_moneda': '''
    SELECT t.anio, m.nk_codigo_moneda AS moneda,
           COUNT(*) AS adjudicaciones, SUM(f.monto_adjudicado) AS monto
    FROM fact_adjudicacion f JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
    JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
    GROUP BY t.anio,m.nk_codigo_moneda ORDER BY t.anio,moneda''',
  'p1_ventas_mes_moneda': '''
    SELECT t.anio,t.mes, m.nk_codigo_moneda AS moneda,
           SUM(f.monto_adjudicado) AS monto,COUNT(*) AS adjudicaciones
    FROM fact_adjudicacion f JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
    JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
    GROUP BY t.anio,t.mes,m.nk_codigo_moneda ORDER BY t.anio,t.mes,moneda''',
  'p2_estado_anio': '''
    SELECT t.anio,m.nk_codigo_moneda AS moneda,e.estado_general,
           COUNT(*) AS adjudicaciones,SUM(f.monto_adjudicado) AS monto,
           AVG(f.monto_adjudicado) AS promedio
    FROM fact_adjudicacion f JOIN dim_tiempo t ON f.sk_tiempo=t.sk_tiempo
    JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda
    JOIN dim_estado e ON f.sk_estado=e.sk_estado
    GROUP BY t.anio,m.nk_codigo_moneda,e.estado_general
    ORDER BY t.anio,moneda,estado_general''',
  'p3_top10_proveedores': (OLAP/'03_top10_pyg.sql').read_text(encoding='utf-8').replace('p.nombre_proveedor, p.adjudicaciones','p.nombre_proveedor AS nombre, p.adjudicaciones'),
  'p4_concentracion_anual': (OLAP/'04_concentracion_top10_anual.sql').read_text(encoding='utf-8'),
  'p5_recurrentes_anual': (OLAP/'05_recurrentes_anual.sql').read_text(encoding='utf-8'),
  'p6_etapas': (OLAP/'06_etapas.sql').read_text(encoding='utf-8'),
}


def main():
    if not DB.exists():
        raise FileNotFoundError('Primero ejecutar python src/cargar_h3.py')
    OUT.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(DB), read_only=True) as con:
        for nombre, sql in CONSULTAS.items():
            # pandas se usa solo para exportar el resultado analítico del motor.
            df = con.execute(sql).df()
            df.to_csv(OUT/f'{nombre}.csv', index=False, encoding='utf-8-sig')
            print(f'[OK] dashboard/datos/{nombre}.csv: {len(df)} filas')
    print('Las tablas CSV están listas para actualizar las fuentes del archivo Excel.')


if __name__=='__main__':
    main()

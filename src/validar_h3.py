"""Pruebas de integridad de H3 contra el archivo DuckDB materializado."""
from pathlib import Path
import duckdb

BASE = Path(__file__).resolve().parents[1] / 'db' / 'dncp_dw.duckdb'
if not BASE.exists():
    raise FileNotFoundError('Falta la base. Ejecute python src/cargar_h3.py')

with duckdb.connect(str(BASE),read_only=True) as con:
    queries = {
        'Filas staging awards': 'SELECT COUNT(*) FROM stg_awards',
        'Filas staging suppliers': 'SELECT COUNT(*) FROM stg_awa_suppliers',
        'Filas staging releases (JSONL)': 'SELECT COUNT(*) FROM stg_releases',
        'Adjudicaciones aceptadas': 'SELECT COUNT(*) FROM fact_adjudicacion',
        'Adjudicaciones distintas': 'SELECT COUNT(DISTINCT nk_adjudicacion) FROM fact_adjudicacion',
        'Rechazo R01': "SELECT COUNT(*) FROM stg_cuarentena WHERE regla_codigo='R01_FECHA_INVALIDA'",
        'Rechazo R02': "SELECT COUNT(*) FROM stg_cuarentena WHERE regla_codigo='R02_MONTO_INVALIDO'",
        'Rechazo R03': "SELECT COUNT(*) FROM stg_cuarentena WHERE regla_codigo='R03_PROVEEDOR_EXCEDENTE'",
        'Sin comprador (-1)': 'SELECT COUNT(*) FROM fact_adjudicacion WHERE sk_comprador=-1',
        'Sin etapa (-1)': 'SELECT COUNT(*) FROM fact_adjudicacion WHERE sk_etapa=-1',
        'USD (no convertido)': "SELECT COUNT(*) FROM fact_adjudicacion f JOIN dim_moneda m ON f.sk_moneda=m.sk_moneda WHERE m.nk_codigo_moneda='USD'",
    }
    result = {k:con.execute(q).fetchone()[0] for k,q in queries.items()}
    for k,v in result.items(): print(f'{k}: {v}')
    expected = {
        'Filas staging awards':22491, 'Filas staging suppliers':22495,
        'Filas staging releases (JSONL)':23324, 'Adjudicaciones aceptadas':22079,
        'Adjudicaciones distintas':22079, 'Rechazo R01':349,
        'Rechazo R02':65, 'Rechazo R03':4, 'Sin comprador (-1)':14162,
        'Sin etapa (-1)':8011, 'USD (no convertido)':54,
    }
    diffs = {k:(result[k], v) for k,v in expected.items() if result[k] != v}
    if diffs:
        raise AssertionError(f'Los resultados difieren del cotejo independiente: {diffs}')
    print('\n[OK] Todas las verificaciones coinciden con el cotejo independiente.')

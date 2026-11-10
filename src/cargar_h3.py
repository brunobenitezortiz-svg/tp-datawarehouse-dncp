"""H3 DNCP: extracción CSV+JSONL, staging, calidad, dimensiones y hecho en DuckDB.

Uso: python src/cargar_h3.py                 # reconstrucción integral y repetible
     python src/cargar_h3.py --solo-etl      # reutiliza staging para probar SCD tipo 1

Nota de procedencia: releases.jsonl se obtiene SIN alterar los valores originales
mediante una conversión documentada de releases.csv (mismo portal DNCP).
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "db" / "dncp_dw.duckdb"
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
SQL = ROOT / "sql"


def preparar_jsonl() -> Path:
    """Serializa la fuente real de releases a formato JSON Lines reproducible."""
    entrada = RAW / "releases.csv"
    destino = DERIVED / "releases.jsonl"
    DERIVED.mkdir(parents=True, exist_ok=True)
    with entrada.open("r", encoding="utf-8-sig", newline="") as src, destino.open("w", encoding="utf-8", newline="") as out:
        for nro, registro in enumerate(csv.DictReader(src), 1):
            objeto = {
                "stg_nro_fila": nro,
                "fecha_release": registro["releases/0/date"],
                "etapas": registro["releases/0/tag"],
                "url_release": registro["releases/0/url"],
            }
            out.write(json.dumps(objeto, ensure_ascii=False) + "\n")
    return destino


def cargar_csv(con: duckdb.DuckDBPyConnection, tabla: str, archivo: str, columnas: str) -> None:
    ruta = (RAW / archivo).as_posix().replace("'", "''")
    # Las tres fuentes se almacenan en staging como datos sin transformar.
    con.execute(f"""
        INSERT INTO {tabla}
        SELECT row_number() OVER () AS stg_nro_fila,
               {columnas}, '{archivo}', current_timestamp
        FROM read_csv('{ruta}', header=true, all_varchar=true)
    """)
    print(f"[EXTRACCIÓN] {tabla}: {con.execute('SELECT COUNT(*) FROM ' + tabla).fetchone()[0]} registros")


def extraer_y_crear(con: duckdb.DuckDBPyConnection) -> None:
    for nombre in ("01_ddl_staging.sql", "02_ddl_dimensional.sql", "03_miembros_base.sql"):
        con.execute((SQL / nombre).read_text(encoding="utf-8"))
    cargar_csv(con, "stg_awards", "awards.csv", """
        \"compiledRelease/id\", \"compiledRelease/awards/0/id\",
        \"compiledRelease/awards/0/status\", \"compiledRelease/awards/0/statusDetails\",
        \"compiledRelease/awards/0/date\", \"compiledRelease/awards/0/value/amount\",
        \"compiledRelease/awards/0/value/currency\", \"compiledRelease/awards/0/invitationID\",
        \"compiledRelease/awards/0/buyer/id\", \"compiledRelease/awards/0/buyer/name\",
        \"compiledRelease/awards/0/relatedBids\" """)
    cargar_csv(con, "stg_awa_suppliers", "awa_suppliers.csv", """
        \"compiledRelease/id\", \"compiledRelease/awards/0/id\",
        \"compiledRelease/awards/0/suppliers/0/id\",
        \"compiledRelease/awards/0/suppliers/0/name\" """)
    ruta = preparar_jsonl().as_posix().replace("'", "''")
    con.execute(f"""
        INSERT INTO stg_releases
        SELECT stg_nro_fila, fecha_release, etapas, url_release,
               'releases.jsonl' AS stg_archivo_origen, current_timestamp
        FROM read_json_auto('{ruta}', format='newline_delimited')
    """)
    print(f"[EXTRACCIÓN] stg_releases (JSONL): {con.execute('SELECT COUNT(*) FROM stg_releases').fetchone()[0]} registros")


def transformar_y_cargar(con: duckdb.DuckDBPyConnection) -> dict:
    # Fechas: fecha civil original del portal; evita modificar el día al convertir UTC.
    # RUC: normaliza espacios/caja, pero NO inventa DV ni rechaza identificadores extranjeros.
    con.execute(r"""
        CREATE OR REPLACE TEMP TABLE h3_awards AS
        SELECT stg_nro_fila,
               COALESCE(NULLIF(TRIM(nk_adjudicacion), ''), 'NO DEFINIDO') AS nk_adjudicacion,
               COALESCE(NULLIF(TRIM(nk_proceso), ''), 'NO DEFINIDO') AS nk_proceso,
               TRY_CAST(SUBSTR(TRIM(fecha_adjudicacion), 1, 10) AS DATE) AS fecha,
               fecha_adjudicacion AS fecha_original,
               TRY_CAST(NULLIF(REPLACE(TRIM(monto), ',', '.'), '') AS DECIMAL(22,2)) AS monto_num,
               monto AS monto_original,
               COALESCE(NULLIF(UPPER(TRIM(estado)), ''), 'NO DEFINIDO') AS estado_general,
               COALESCE(NULLIF(UPPER(TRIM(estado_detalle)), ''), 'NO DEFINIDO') AS estado_detalle,
               COALESCE(NULLIF(UPPER(TRIM(moneda)), ''), 'N/D') AS moneda,
               NULLIF(TRIM(comprador_id), '') AS comprador_id,
               NULLIF(TRIM(comprador_nombre), '') AS comprador_nombre
        FROM stg_awards;
    """)
    con.execute(r"""
        CREATE OR REPLACE TEMP TABLE h3_suppliers AS
        SELECT stg_nro_fila, TRIM(nk_adjudicacion) AS nk_adjudicacion,
               NULLIF(UPPER(REGEXP_REPLACE(TRIM(nk_proveedor), '\s+', ' ', 'g')), '') AS nk_ruc,
               COALESCE(NULLIF(REGEXP_REPLACE(TRIM(proveedor_nombre), '\s+', ' ', 'g'), ''), 'No definido') AS nombre_proveedor,
               ROW_NUMBER() OVER (PARTITION BY TRIM(nk_adjudicacion) ORDER BY stg_nro_fila) AS rn
        FROM stg_awa_suppliers;
    """)
    con.execute(r"""
        CREATE OR REPLACE TEMP TABLE h3_release AS
        SELECT REGEXP_EXTRACT(TRIM(url_release), '[^/]+$') AS nk_proceso,
               COALESCE(NULLIF(LOWER(REGEXP_REPLACE(TRIM(etapas), '\s+', '', 'g')), ''), 'NO DEFINIDO') AS nk_etapas,
               ROW_NUMBER() OVER (
                   PARTITION BY REGEXP_EXTRACT(TRIM(url_release), '[^/]+$')
                   ORDER BY fecha_release DESC NULLS LAST, stg_nro_fila DESC
               ) AS rn
        FROM stg_releases;
    """)
    con.execute("DELETE FROM stg_cuarentena")
    con.execute("""
        INSERT INTO stg_cuarentena (tabla_origen, stg_nro_fila, regla_codigo, motivo, valor_original)
        SELECT 'stg_awards', stg_nro_fila, 'R01_FECHA_INVALIDA',
               'Fecha nula, no convertible o fuera de 2015-2026', fecha_original
        FROM h3_awards
        WHERE fecha IS NULL OR fecha < DATE '2015-01-01' OR fecha > DATE '2026-12-31';
    """)
    con.execute("""
        INSERT INTO stg_cuarentena (tabla_origen, stg_nro_fila, regla_codigo, motivo, valor_original)
        SELECT 'stg_awards', stg_nro_fila, 'R02_MONTO_INVALIDO',
               'Monto nulo, no convertible o no positivo', monto_original
        FROM h3_awards WHERE monto_num IS NULL OR monto_num <= 0;
    """)
    con.execute("""
        INSERT INTO stg_cuarentena (tabla_origen, stg_nro_fila, regla_codigo, motivo, valor_original)
        SELECT 'stg_awa_suppliers', stg_nro_fila, 'R03_PROVEEDOR_EXCEDENTE',
               'Proveedor adicional: se conserva la primera fila por adjudicación', nk_ruc
        FROM h3_suppliers WHERE rn > 1;
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE h3_elegibles AS
        SELECT a.*, s.nk_ruc, s.nombre_proveedor,
               COALESCE(r.nk_etapas, 'NO DEFINIDO') AS nk_etapas
        FROM h3_awards a
        LEFT JOIN h3_suppliers s ON s.nk_adjudicacion = a.nk_adjudicacion AND s.rn = 1
        LEFT JOIN h3_release r ON r.nk_proceso = a.nk_proceso AND r.rn = 1
        WHERE a.fecha BETWEEN DATE '2015-01-01' AND DATE '2026-12-31'
          AND a.monto_num > 0;
    """)
    # SCD tipo 1: razón social actual sobreescrita; ID natural estable.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE h3_proveedor_unico AS
        SELECT nk_ruc, nombre_proveedor
        FROM (
            SELECT nk_ruc, nombre_proveedor,
                   ROW_NUMBER() OVER (PARTITION BY nk_ruc ORDER BY stg_nro_fila DESC) AS rn
            FROM h3_elegibles WHERE nk_ruc IS NOT NULL
        ) t WHERE rn = 1;
    """)
    con.execute("""
        UPDATE dim_proveedor AS d
        SET nombre_proveedor = p.nombre_proveedor, dim_fecha_actualiz = current_timestamp
        FROM h3_proveedor_unico p
        WHERE d.nk_ruc = p.nk_ruc AND d.nombre_proveedor <> p.nombre_proveedor;
    """)
    con.execute("""
        INSERT INTO dim_proveedor (nk_ruc, nombre_proveedor)
        SELECT p.nk_ruc, p.nombre_proveedor FROM h3_proveedor_unico p
        WHERE NOT EXISTS (SELECT 1 FROM dim_proveedor d WHERE d.nk_ruc = p.nk_ruc);
    """)
    con.execute("""
        INSERT INTO dim_estado (nk_estado, estado_general, estado_detalle)
        SELECT DISTINCT (estado_general || '|' || estado_detalle), estado_general, estado_detalle
        FROM h3_elegibles e
        WHERE NOT EXISTS (SELECT 1 FROM dim_estado d WHERE d.nk_estado = e.estado_general || '|' || e.estado_detalle);
    """)
    con.execute("""
        INSERT INTO dim_moneda (nk_codigo_moneda, nombre_moneda)
        SELECT DISTINCT moneda,
               CASE moneda WHEN 'PYG' THEN 'Guaraní paraguayo'
                           WHEN 'USD' THEN 'Dólar estadounidense' ELSE moneda END
        FROM h3_elegibles e
        WHERE moneda <> 'N/D'
          AND NOT EXISTS (SELECT 1 FROM dim_moneda d WHERE d.nk_codigo_moneda = e.moneda);
    """)
    con.execute("""
        CREATE OR REPLACE TEMP TABLE h3_comprador_unico AS
        SELECT comprador_id, comprador_nombre
        FROM (
            SELECT comprador_id, COALESCE(comprador_nombre, 'No definido') AS comprador_nombre,
                   ROW_NUMBER() OVER (PARTITION BY comprador_id ORDER BY stg_nro_fila DESC) AS rn
            FROM h3_elegibles WHERE comprador_id IS NOT NULL
        ) t WHERE rn = 1;
    """)
    con.execute("""
        INSERT INTO dim_comprador (nk_comprador, nombre_comprador)
        SELECT p.comprador_id, p.comprador_nombre FROM h3_comprador_unico p
        WHERE NOT EXISTS (SELECT 1 FROM dim_comprador d WHERE d.nk_comprador = p.comprador_id);
    """)
    con.execute("""
        UPDATE dim_comprador AS d SET nombre_comprador = p.comprador_nombre
        FROM h3_comprador_unico p
        WHERE d.nk_comprador = p.comprador_id AND d.nombre_comprador <> p.comprador_nombre;
    """)
    con.execute("""
        INSERT INTO dim_etapa (
            nk_etapas, tiene_planificacion, tiene_licitacion, tiene_adjudicacion,
            tiene_contrato, tiene_implementacion, tiene_modificacion_contrato,
            tiene_terminacion_contrato, cantidad_etapas)
        SELECT DISTINCT e.nk_etapas,
            CONTAINS(';' || e.nk_etapas || ';', ';planning;'),
            CONTAINS(';' || e.nk_etapas || ';', ';tender;'),
            CONTAINS(';' || e.nk_etapas || ';', ';award;'),
            CONTAINS(';' || e.nk_etapas || ';', ';contract;'),
            CONTAINS(';' || e.nk_etapas || ';', ';implementation;'),
            CONTAINS(';' || e.nk_etapas || ';', ';contractamendment;'),
            CONTAINS(';' || e.nk_etapas || ';', ';contracttermination;'),
            CAST(array_length(string_split(e.nk_etapas, ';')) AS SMALLINT)
        FROM h3_elegibles e
        WHERE e.nk_etapas <> 'NO DEFINIDO'
          AND NOT EXISTS (SELECT 1 FROM dim_etapa d WHERE d.nk_etapas = e.nk_etapas);
    """)
    # Carga FULL de la tabla de hechos; la carga de dimensiones se hace por UPSERT/SCD1.
    con.execute("DELETE FROM fact_adjudicacion")
    con.execute("""
        INSERT INTO fact_adjudicacion (
            nk_adjudicacion, nk_proceso, sk_tiempo, sk_proveedor,
            sk_estado, sk_moneda, sk_comprador, sk_etapa,
            monto_adjudicado, cantidad_adjudicaciones)
        SELECT e.nk_adjudicacion, e.nk_proceso,
               t.sk_tiempo,
               COALESCE(p.sk_proveedor, -1), COALESCE(est.sk_estado, -1),
               COALESCE(m.sk_moneda, -1), COALESCE(c.sk_comprador, -1),
               COALESCE(et.sk_etapa, -1), e.monto_num, 1
        FROM h3_elegibles e
        JOIN dim_tiempo t ON t.nk_fecha = e.fecha
        LEFT JOIN dim_proveedor p ON p.nk_ruc = e.nk_ruc
        LEFT JOIN dim_estado est ON est.nk_estado = e.estado_general || '|' || e.estado_detalle
        LEFT JOIN dim_moneda m ON m.nk_codigo_moneda = e.moneda
        LEFT JOIN dim_comprador c ON c.nk_comprador = e.comprador_id
        LEFT JOIN dim_etapa et ON et.nk_etapas = e.nk_etapas;
    """)
    total = con.execute("SELECT COUNT(*) FROM stg_awards").fetchone()[0]
    buenos = con.execute("SELECT COUNT(*) FROM fact_adjudicacion").fetchone()[0]
    esperados = con.execute("SELECT COUNT(*) FROM h3_elegibles").fetchone()[0]
    assert buenos == esperados, f"El grano del hecho no coincide: {buenos} vs {esperados}"
    assert buenos >= 5000, "El hecho no alcanza el volumen mínimo exigido"
    assert buenos + con.execute("""
        SELECT COUNT(*) FROM h3_awards WHERE fecha IS NULL OR fecha < DATE '2015-01-01'
            OR fecha > DATE '2026-12-31' OR monto_num IS NULL OR monto_num <= 0
    """).fetchone()[0] == total
    assert con.execute("SELECT COUNT(*) - COUNT(DISTINCT nk_adjudicacion) FROM fact_adjudicacion").fetchone()[0] == 0
    resumen = dict(con.execute("""
        SELECT regla_codigo, COUNT(*) FROM stg_cuarentena
        GROUP BY regla_codigo ORDER BY regla_codigo
    """).fetchall())
    resumen.update({"staging_awards": total, "fact_adjudicacion": buenos,
                    "rechazadas_unicas_awards": total - buenos,
                    "miembro_comprador_no_definido": con.execute('SELECT COUNT(*) FROM fact_adjudicacion WHERE sk_comprador=-1').fetchone()[0],
                    "miembro_etapa_no_definido": con.execute('SELECT COUNT(*) FROM fact_adjudicacion WHERE sk_etapa=-1').fetchone()[0],
                    "registros_usd": con.execute("SELECT COUNT(*) FROM fact_adjudicacion f JOIN dim_moneda m USING(sk_moneda) WHERE m.nk_codigo_moneda='USD'").fetchone()[0]})
    return resumen


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--solo-etl", action="store_true", help="Conservar staging y verificar recarga/SCD1")
    cfg = args.parse_args()
    DB.parent.mkdir(parents=True, exist_ok=True)
    if not cfg.solo_etl and DB.exists():
        DB.unlink()
    if cfg.solo_etl and not DB.exists():
        raise FileNotFoundError("La base no existe; primero ejecute python src/cargar_h3.py")
    con = duckdb.connect(str(DB))
    try:
        if not cfg.solo_etl:
            extraer_y_crear(con)
        con.execute("BEGIN TRANSACTION")
        try:
            resumen = transformar_y_cargar(con)
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
        print("\n[ETL COMPLETO]", json.dumps(resumen, ensure_ascii=False, indent=2))
        print(f"[OK] Base materializada: {DB}")
    finally:
        con.close()


if __name__ == "__main__":
    main()

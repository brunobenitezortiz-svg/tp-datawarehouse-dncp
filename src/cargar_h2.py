"""
cargar_h2.py  |  Hito H2: crea el modelo (DDL) y carga el dataset fuente en staging.

Uso (desde la raíz del proyecto):
    python src/cargar_h2.py

Qué hace:
  1. Recrea el archivo DuckDB db/dncp_dw.duckdb desde cero (ejecución repetible).
  2. Ejecuta sql/01 (staging), sql/02 (modelo dimensional) y sql/03 (miembros -1 + calendario).
  3. Carga los 3 CSV de data/raw en las tablas stg_* (todo como texto, sin limpiar).
  4. Ejecuta sql/04 y muestra los controles de carga.
"""
from pathlib import Path
import duckdb

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "db" / "dncp_dw.duckdb"
SQL = RAIZ / "sql"
RAW = RAIZ / "data" / "raw"


def ejecutar_script(con, nombre):
    con.execute((SQL / nombre).read_text(encoding="utf-8"))
    print(f"[OK] {nombre}")


def cargar(con, tabla, archivo, select_cols):
    ruta = (RAW / archivo).as_posix()
    con.execute(f"""
        INSERT INTO {tabla}
        SELECT row_number() OVER () AS stg_nro_fila,
               {select_cols},
               '{archivo}' AS stg_archivo_origen,
               current_timestamp AS stg_fecha_carga
        FROM read_csv('{ruta}', header = true, all_varchar = true)
    """)
    n = con.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
    print(f"[OK] {tabla}: {n:,} filas cargadas desde {archivo}")


def main():
    DB.parent.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = duckdb.connect(str(DB))

    for script in ("01_ddl_staging.sql", "02_ddl_dimensional.sql", "03_miembros_base.sql"):
        ejecutar_script(con, script)

    cargar(con, "stg_awards", "awards.csv", """
        "compiledRelease/id", "compiledRelease/awards/0/id",
        "compiledRelease/awards/0/status", "compiledRelease/awards/0/statusDetails",
        "compiledRelease/awards/0/date", "compiledRelease/awards/0/value/amount",
        "compiledRelease/awards/0/value/currency", "compiledRelease/awards/0/invitationID",
        "compiledRelease/awards/0/buyer/id", "compiledRelease/awards/0/buyer/name",
        "compiledRelease/awards/0/relatedBids" """)

    cargar(con, "stg_awa_suppliers", "awa_suppliers.csv", """
        "compiledRelease/id", "compiledRelease/awards/0/id",
        "compiledRelease/awards/0/suppliers/0/id", "compiledRelease/awards/0/suppliers/0/name" """)

    cargar(con, "stg_releases", "releases.csv", """
        "releases/0/date", "releases/0/tag", "releases/0/url" """)

    print("\n--- Controles de carga (sql/04_verificacion_staging.sql) ---")
    for sentencia in (SQL / "04_verificacion_staging.sql").read_text(encoding="utf-8").split(";"):
        s = "\n".join(l for l in sentencia.splitlines() if not l.strip().startswith("--")).strip()
        if s:
            print(con.execute(s).fetchdf().to_string(index=False), "\n")
    con.close()


if __name__ == "__main__":
    main()

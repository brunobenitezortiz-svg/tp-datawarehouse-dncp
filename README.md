# DW de Adjudicaciones de Contrataciones Públicas (DNCP)

Trabajo Práctico individual — Datawarehouse (22891), Universidad del Norte, 2.º semestre 2026.

## Estructura
```
data/raw/   CSV originales de la DNCP (awards, awa_suppliers, releases)
sql/        Scripts SQL: 01 staging, 02 modelo dimensional, 03 miembros -1 y calendario, 04 verificación
src/        cargar_h2.py (crea el modelo y carga staging)
db/         Base DuckDB generada (no se versiona)
docs/       Diagrama del modelo e informe del hito H2
```

## Cómo ejecutar
```
pip install -r requirements.txt
python src/cargar_h2.py
```
El script recrea `db/dncp_dw.duckdb` desde cero, ejecuta los DDL y carga los 3 CSV en las tablas `stg_*`.

## Modelo
Esquema en estrella. Grano de `fact_adjudicacion`: una fila por adjudicación.
Dimensiones: `dim_tiempo`, `dim_proveedor` (SCD tipo 1), `dim_estado`, `dim_moneda`, `dim_comprador`, `dim_etapa`.
Convenciones: `dim_`, `fact_`, `stg_`, `sk_`, `nk_`; `pk_`, `fk_`, `uq_`, `ck_`, `idx_`.

## Fuente de datos
Portal de datos abiertos de la DNCP: https://www.contrataciones.gov.py/datos/adjudicaciones

## Estado
- H2: modelo (DDL) y staging cargado.
- H3: ETL completo, consultas OLAP, dashboard e informe.

# Datawarehouse de Adjudicaciones Públicas — DNCP

**Trabajo práctico individual de Datawarehouse | Universidad del Norte, Paraguay**

**Autor:** Bruno Sebastián Benítez Ortiz  
**Asignatura:** Datawarehouse (22891) — Ingeniería Informática  
**Docente:** Lic. Walter Romero  
**Entrega final (H3):** 10 de noviembre de 2026

## Descripción

Proyecto de integración y análisis de datos abiertos de adjudicaciones de la **Dirección Nacional de Contrataciones Públicas (DNCP)** de Paraguay. Implementa un Datawarehouse en esquema estrella para examinar montos adjudicados, proveedores, estados y etapas del proceso de contratación.

El repositorio reúne los hitos de definición de alcance (H1), diseño dimensional y staging (H2), y la implementación final de ETL, consultas OLAP y tablero de indicadores (H3).

## Preguntas de negocio

1. ¿Cuál es el monto adjudicado por año y mes, diferenciado por moneda?
2. ¿Cuántas adjudicaciones existen y cuál es su monto promedio por estado y año?
3. ¿Qué diez proveedores concentran el mayor monto adjudicado en PYG y qué participación representan?
4. ¿Cómo evoluciona anualmente la concentración del monto adjudicado en los diez principales proveedores?
5. ¿Qué proporción del monto anual corresponde a proveedores recurrentes (más de diez adjudicaciones)?
6. ¿Cómo se distribuyen las adjudicaciones entre las etapas del proceso de contratación?

## Arquitectura y modelo dimensional

El flujo de datos sigue estas etapas:

```text
Fuentes DNCP → Extracción (CSV / JSONL) → Staging
            → Validaciones y cuarentena → Dimensiones + hechos (DuckDB)
            → Consultas OLAP → Dashboard Excel
```

El esquema estrella contiene una tabla de hechos, `fact_adjudicacion`, y seis dimensiones:

- `dim_tiempo`
- `dim_proveedor` (SCD tipo 1)
- `dim_estado`
- `dim_moneda`
- `dim_comprador`
- `dim_etapa`

**Grano:** una fila de la tabla de hechos por adjudicación (`nk_adjudicacion`). La tabla de hechos almacena el monto adjudicado y la cantidad de adjudicaciones. Las dimensiones admiten un miembro **«NO DEFINIDO»** con clave sustituta `-1` cuando falta información asociada.

[Ver diagrama del modelo dimensional](docs/diagrama_modelo.png).

## Origen de los datos

Los archivos fuente proceden del [portal de datos abiertos de la DNCP](https://www.contrataciones.gov.py/datos/adjudicaciones), con descarga utilizada en los hitos H1 y H2:

| Archivo | Contenido | Registros fuente |
|---|---|---:|
| `data/raw/awards.csv` | Adjudicaciones | 22.491 |
| `data/raw/awa_suppliers.csv` | Proveedores adjudicados | 22.495 |
| `data/raw/releases.csv` | Publicaciones y etapas de procesos | 23.324 |

La extracción del H3 procesa `awards.csv` y `awa_suppliers.csv` en formato CSV, y `data/derived/releases.jsonl` en formato JSON Lines. Este último archivo se genera de forma reproducible a partir de `releases.csv`, preservando los datos de origen. **Los formatos son diferentes, pero todos los archivos proceden de una misma fuente institucional: la DNCP.**

## ETL y calidad de datos

El proceso implementado en `src/cargar_h3.py` realiza extracción, carga a staging, validaciones, cuarentena de registros defectuosos, construcción de dimensiones y carga de la tabla de hechos.

Las principales reglas comprenden:

- Rechazo de adjudicaciones con fecha inválida o fuera del período 2015–2026, o monto nulo/no positivo.
- Selección de un proveedor por adjudicación cuando hay múltiples asociaciones; las filas adicionales se registran en cuarentena.
- Normalización de estados, nombres e identificadores según las reglas documentadas.
- Asignación de `sk = -1` a compradores y etapas no identificados.
- Actualización SCD tipo 1 del nombre del proveedor, sin conservar historial de razones sociales.
- Análisis separado de adjudicaciones en PYG y USD, sin conversión ni suma entre monedas.

### Resultados de validación

| Indicador | Cantidad |
|---|---:|
| Adjudicaciones de origen | 22.491 |
| Adjudicaciones cargadas en `fact_adjudicacion` | **22.079** |
| Adjudicaciones rechazadas (únicas) | **412** |
| Incidencias de fecha (R01) | 349 |
| Incidencias de monto (R02) | 65 |
| Filas adicionales de proveedor en cuarentena (R03) | 4 |
| Adjudicaciones cargadas sin comprador identificado | 14.162 |
| Adjudicaciones cargadas sin etapa identificada | 8.011 |

Dos adjudicaciones incumplen simultáneamente las reglas de fecha y monto; por ese motivo el total único de rechazadas es 412, y no 414. Las cuatro asociaciones adicionales de proveedores no reducen el número de adjudicaciones cargadas.

Los resultados de la verificación están implementados en `src/validar_h3.py` y `sql/06_validaciones_h3.sql`.

## Tecnologías

- **Base de datos:** DuckDB 1.5.
- **Procesamiento ETL:** Python 3.12, pandas 2.2 y SQL.
- **Análisis:** consultas SQL OLAP (`GROUPING SETS`, `ROLLUP`, agregaciones y refinamientos).
- **Visualización:** Microsoft Excel.
- **Control de versiones:** Git / GitHub.

## Instalación y ejecución

Con Python 3.12 instalado, ejecutar desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python src/cargar_h3.py
python src/validar_h3.py
python src/exportar_dashboard.py
```

`cargar_h3.py` construye la base `db/dncp_dw.duckdb` a partir de los datos fuente. `validar_h3.py` verifica la integridad y los recuentos esperados. `exportar_dashboard.py` genera las tablas analíticas en `dashboard/datos/` a partir del modelo dimensional.

La base de datos DuckDB es **reproducible y no está versionada**. Para repetir únicamente la transformación y la carga usando el staging existente, está disponible:

```powershell
python src/cargar_h3.py --solo-etl
```

## Consultas OLAP y dashboard

Las seis consultas que responden a las preguntas de negocio están en [`sql/olap/`](sql/olap/). Los ejemplos de **roll-up, drill-down, slice, dice y pivot** están documentados en [`sql/08_operadores_refinamiento.sql`](sql/08_operadores_refinamiento.sql).

El archivo [`dashboard/Tablero_DNCP_H3.xlsx`](dashboard/Tablero_DNCP_H3.xlsx) presenta los resultados mediante seis gráficos. Sus datos provienen de agregaciones sobre `fact_adjudicacion` y las dimensiones, no de consultas directas a los CSV originales. El Excel contiene una instantánea de resultados; las tablas auxiliares pueden regenerarse con `src/exportar_dashboard.py`.

**Criterios de interpretación:** los importes en PYG y USD se reportan por separado; los diez mayores proveedores por año se calculan para cada período; la recurrencia se evalúa por proveedor, año y moneda; las etapas pueden superponerse, de modo que sus porcentajes no necesariamente suman 100 %.

## Estructura del repositorio

```text
data/
  raw/                     CSV originales de la DNCP
  derived/                 releases.jsonl generado desde releases.csv
sql/
  01_ddl_staging.sql       Definición del staging
  02_ddl_dimensional.sql   Esquema estrella
  03_miembros_base.sql     Miembros no definidos y dimensión tiempo
  04_verificacion_staging.sql
  06_validaciones_h3.sql   Controles finales
  08_operadores_refinamiento.sql
  olap/                    Seis consultas analíticas de negocio
src/
  cargar_h2.py             Carga del hito H2
  cargar_h3.py             ETL completo
  validar_h3.py            Validación automática
  exportar_dashboard.py    Exportación de resultados para el tablero
  analisis_independiente.py
dashboard/
  Tablero_DNCP_H3.xlsx     Tablero final
  datos/                   CSV analíticos auxiliares
docs/
  H2_Modelo_Dimensional_DNCP.docx
  Informe_Final_H3_DNCP.docx
  diagrama_modelo.png
  metricas_h3_cotejo_pandas.json
requirements.txt
README.md
```

## Documentación

El [informe final H3](docs/Informe_Final_H3_DNCP.docx) incluye el alcance del proyecto, el diccionario de datos, las decisiones de modelado, el proceso ETL, las consultas OLAP, el dashboard y el anexo de fuentes y calidad de datos.

Este proyecto fue desarrollado con fines académicos a partir de datos públicos de contrataciones del Paraguay.

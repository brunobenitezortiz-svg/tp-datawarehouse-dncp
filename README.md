# TP individual de Datawarehouse — DNCP (H1 + H2 + H3)

**Alumno:** Bruno Sebastián Benítez Ortiz  
**Materia:** Datawarehouse (22891), Universidad del Norte  
**Docente:** Lic. Walter Romero  
**Entrega H3:** 10/11/2026  
**Repositorio original:** https://github.com/brunobenitezortiz-svg/tp-datawarehouse-dncp

El proyecto mantiene el diseño H2 (1 hecho + 6 dimensiones), completa el ETL y documenta seis preguntas de negocio, cinco operadores OLAP y el tablero de Excel. La base DuckDB se crea localmente a partir de los archivos públicos; **no versionar `db/*.duckdb`**.

## 1. Requisitos y ejecución (Windows / PowerShell)

Instalar Python 3.12 (y opcionalmente DBeaver y Excel). Desde esta carpeta:

```powershell
python -m pip install -r requirements.txt
python src/cargar_h3.py
python src/validar_h3.py
python src/exportar_dashboard.py
```

- `cargar_h3.py` recrea la base, importa dos CSV y un JSONL, valida, envía rechazos a cuarentena, puebla dimensiones y la tabla de hechos.
- `validar_h3.py` comprueba recuentos, la clave de grano, las dimensiones desconocidas y que el balance coincida con el cotejo independiente.
- `exportar_dashboard.py` recalcula los CSV **consultando fact_adjudicacion y las dimensiones**, no los archivos originales. Los datos del Excel entregado son una instantánea; para actualizarla en Excel, sustituir los datos de las hojas auxiliares por los CSV exportados y actualizar los gráficos.
- `python src/cargar_h3.py --solo-etl` reutiliza el staging y hace recarga completa de hechos y actualizaciones SCD tipo 1 en dimensiones, sin borrar las claves de dimensión.

Si tu comando es `py` en vez de `python`, sustituirlo en los ejemplos.

### Consultas OLAP y demostración

Abre `db/dncp_dw.duckdb` en DBeaver (DuckDB) y ejecuta las consultas SQL bajo `sql/olap/`. Cada archivo responde a una pregunta del H1. El archivo `sql/08_operadores_refinamiento.sql` contiene cinco ejemplos separados: roll-up, drill-down, slice, dice y pivot. `sql/06_validaciones_h3.sql` ofrece las verificaciones.

## 2. Origen real y heterogeneidad de los archivos

Fuente publicada: https://www.contrataciones.gov.py/datos/adjudicaciones (descarga 2024 facilitada en H1/H2, con registros históricos y un registro fechado en 2025). El directorio `data/raw/` conserva intactos los tres CSV reales. Para que el ETL integre **formatos heterogéneos** sin inventar una API:

- `awards.csv` (CSV, adjudicaciones),
- `awa_suppliers.csv` (CSV, proveedores),
- `data/derived/releases.jsonl` (JSON Lines, etapas). Se deriva *sin alterar los datos* de `releases.csv` con `preparar_jsonl()`.

**Importante:** CSV y JSONL son formatos distintos pero proceden del **mismo portal y de la misma descarga**, no constituyen dos instituciones o sistemas fuente independientes. El informe lo declara explícitamente. Si el profesor interpreta la heterogeneidad como *orígenes independientes* y no como *formatos*, deberá añadirse una fuente nueva real, preferentemente un archivo/API JSON de la DNCP, previa validación.

## 3. Reglas de calidad

- **R01:** fecha no convertible o fuera de 2015-01-01 a 2026-12-31. Se descarta esa adjudicación.
- **R02:** monto no convertible, nulo o ≤ 0. Se descarta esa adjudicación.
- **R03:** proveedores adicionales de una adjudicación. Se conserva el primero en orden de origen; solo las filas adicionales se ponen en cuarentena, sin descartar la adjudicación.
- **R04:** normalización de mayúsculas y espacios en los estados.
- **R05:** estado general vacío → `NO DEFINIDO`, conservando el detalle.
- **R06/R07:** compradores o etapas faltantes → dimensión `sk = -1`, no se descarta.
- **R08:** montos denominados USD no convertidos; se analizan independientemente de PYG. Los valores atípicos se señalan como limitación y requieren auditoría de origen.
- **R09:** RUC atípicos e identificadores de proveedores extranjeros se conservan como identificadores de origen (mayúsculas y espacios normalizados), **sin inventar RUC ni dígito verificador**. Advertencia de calidad, no rechazo.

Las 349 fechas y los 65 montos deficientes tienen dos filas en común: `349 + 65 − 2 = 412` adjudicaciones rechazadas. Se aceptan `22.491 − 412 = 22.079`. Los 4 proveedores adicionales están contados aparte y no reducen la cantidad de hechos.

## 4. Reglas de interpretación

- El **grano** es UNA adjudicación por `nk_adjudicacion`.
- La fecha corresponde al día civil que consta en el archivo, sin desplazarla a UTC.
- Las medidas monetarias **NO se suman entre PYG y USD**.
- La recurrencia significa **más de diez adjudicaciones del proveedor durante el mismo año y moneda**, salvo indicación explícita contraria.
- El top 10 anual se vuelve a calcular por cada año. El top 10 global usa todo el período válido y solo PYG.
- Las etapas de `releases` son **etiquetas acumulables**; una adjudicación puede estar en varias. Por eso los porcentajes por etapa no suman 100 %.
- `dim_proveedor` implementa SCD tipo 1 actualizando la razón social sin conservar nombres históricos. La tabla de hechos usa refresco FULL documentado.

## 5. Archivos

```text
sql/01..04                  H2 intacto: DDL, miembros -1, control staging
sql/06_validaciones_h3.sql  Pruebas después del ETL
sql/08_operadores_refinamiento.sql   Cinco operadores OLAP
sql/olap/01..06             Seis consultas de las preguntas del acta
src/cargar_h2.py            Implementación original H2 (se conserva)
src/cargar_h3.py            Pipeline completo H3, CSV + JSONL → staging → DW
src/validar_h3.py           Pruebas de integridad con resultados esperados
src/exportar_dashboard.py   Agregados desde modelo dimensional a CSV
src/analisis_independiente.py Cotejo desde los archivos fuente (pandas)
data/raw/                   Fuentes originales completas
data/derived/               Fuente JSONL convertida con trazabilidad
dashboard/Tablero_DNCP_H3.xlsx  Tablero final, al menos cuatro gráficos
dashboard/datos/            Tablas auxiliares exportables
docs/Informe_Final_H3_DNCP.docx  Informe con acta, diccionario, anexo y resultados
docs/diagrama_modelo.png    Diagrama de H2
```

## 6. Presentación del 17/11/2026

Presentar en 8-10 min: contexto y seis preguntas, esquema en estrella y grano, reglas del ETL, ejecutar `sql/olap/04_concentracion_top10_anual.sql` en DBeaver, abrir dashboard y explicar PYG/USD, `sk=-1`, SCD1 y límites de las fuentes reales.

## 7. Versionado y entrega

El H3 exige **Git con historial real de commits**, no solo ZIP. Desde tu repositorio local, copia/incorpora los cambios, revisa `git status`, agrega los archivos, crea uno o varios commits descriptivos y haz `git push`. El ZIP es un respaldo para Moodle; subirlo no reemplaza el historial ni el enlace al repositorio. El archivo DuckDB se regenera y no debe incluirse en Git.

## 8. Alcance de la verificación recibida

Se cotejaron los datos públicos del ZIP con pandas para verificar las cifras. Los archivos de Python se revisaron sintácticamente. La ejecución real de DuckDB y la actualización del repositorio dependen del ambiente local del alumno y deben verificarse con los comandos de la sección 1. No declarar en la defensa que esas pruebas se ejecutaron si no se ejecutaron.

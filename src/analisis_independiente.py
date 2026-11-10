"""Cotejo independiente con pandas de los controles del H3 y datos agregados.

No reemplaza el ETL en DuckDB: verifica las cantidades desde los CSV públicos.
Las hojas del dashboard se regeneran al ejecutar el exportador DuckDB de H3.
"""
from pathlib import Path
import json
import re
import pandas as pd
import numpy as np

R = Path(__file__).resolve().parents[1]
RAW = R / 'data' / 'raw'
OUT = R / 'dashboard' / 'datos'
OUT.mkdir(parents=True, exist_ok=True)

aw = pd.read_csv(RAW/'awards.csv', dtype=str, keep_default_na=False)
su = pd.read_csv(RAW/'awa_suppliers.csv', dtype=str, keep_default_na=False)
re = pd.read_csv(RAW/'releases.csv', dtype=str, keep_default_na=False)

# Campos de las fuentes, mismos criterios que cargar_h3.py.
df = pd.DataFrame({
 'nk_adjudicacion':aw['compiledRelease/awards/0/id'].str.strip(),
 'nk_proceso':aw['compiledRelease/id'].str.strip(),
 'fecha':pd.to_datetime(aw['compiledRelease/awards/0/date'].str[:10],errors='coerce'),
 'monto':pd.to_numeric(aw['compiledRelease/awards/0/value/amount'].str.replace(',','.',regex=False),errors='coerce'),
 'moneda':aw['compiledRelease/awards/0/value/currency'].str.strip().str.upper(),
 'estado_general':aw['compiledRelease/awards/0/status'].str.strip().str.upper().replace('', 'NO DEFINIDO'),
 'estado_detalle':aw['compiledRelease/awards/0/statusDetails'].str.strip().str.upper().replace('', 'NO DEFINIDO'),
 'comprador_id':aw['compiledRelease/awards/0/buyer/id'].str.strip(),
})
bad_date=df.fecha.isna() | ~(df.fecha.dt.year.between(2015,2026))
bad_amount=df.monto.isna() | (df.monto<=0)
valid=~(bad_date | bad_amount)

s = pd.DataFrame({
 'nk_adjudicacion':su['compiledRelease/awards/0/id'].str.strip(),
 'nk_ruc':su['compiledRelease/awards/0/suppliers/0/id'].str.strip().str.upper().str.replace(r'\s+',' ',regex=True),
 'nombre':su['compiledRelease/awards/0/suppliers/0/name'].str.strip().str.replace(r'\s+',' ',regex=True),
})
s['rn']=s.groupby('nk_adjudicacion').cumcount()+1
extra=int((s.rn>1).sum()); s=s[s.rn==1].copy()
release = pd.DataFrame({
 'nk_proceso':re['releases/0/url'].str.rsplit('/', n=1).str[-1].str.strip(),
 'etapas':re['releases/0/tag'].str.strip().str.replace(r'\s+','',regex=True).str.lower(),
 'fecha_release':re['releases/0/date'],
})
release=release.sort_values('fecha_release',ascending=False).drop_duplicates('nk_proceso')
f=df[valid].merge(s.drop(columns='rn'),on='nk_adjudicacion',how='left',validate='one_to_one')
f=f.merge(release[['nk_proceso','etapas']],on='nk_proceso',how='left',validate='many_to_one')
f['etapas']=f['etapas'].fillna('NO DEFINIDO')
f['nombre']=f['nombre'].fillna('No definido')
f['nk_ruc']=f['nk_ruc'].fillna('NO DEFINIDO')
f['anio']=f.fecha.dt.year.astype(int)
f['mes']=f.fecha.dt.month.astype(int)
f['estado']=f.estado_general+'|'+f.estado_detalle

summary={
 'fuentes':{'awards':len(aw),'awa_suppliers':len(su),'releases':len(re)},
 'stg_awards':len(aw),'fact_esperada':len(f),'rechazadas_unicas':int((~valid).sum()),
 'R01_fecha':int(bad_date.sum()),'R02_monto':int(bad_amount.sum()),
 'R01_y_R02_solapadas':int((bad_date&bad_amount).sum()),'R03_proveedor_excedente':extra,
 'sin_comprador_en_fact':int((f.comprador_id=='').sum()),
 'sin_etapa_en_fact':int((f.etapas=='NO DEFINIDO').sum()),
 'usd_aceptados':int((f.moneda=='USD').sum()),
 'pyg_aceptados':int((f.moneda=='PYG').sum()),
 'ruc_no_convencional_filas_fuente':int((~su['compiledRelease/awards/0/suppliers/0/id'].str.fullmatch(r'PY-RUC-[0-9]+-[0-9]')).sum()),
 'ruc_no_convencional_identificadores':int(su.loc[~su['compiledRelease/awards/0/suppliers/0/id'].str.fullmatch(r'PY-RUC-[0-9]+-[0-9]'),'compiledRelease/awards/0/suppliers/0/id'].nunique()),
 'fact_unicidad':int(f.nk_adjudicacion.nunique()),
 'totales_por_moneda':{k:{'adjudicaciones':len(g),'monto':float(g.monto.sum())} for k,g in f.groupby('moneda')},
 'por_anio':{str(int(k)):int(v) for k,v in f.anio.value_counts().sort_index().items()},
 'proveedores_distintos_validos':int(f.nk_ruc.nunique()),
 'compradores_distintos_validos':int(f.loc[f.comprador_id!='','comprador_id'].nunique()),
 'estados_distintos_validos':int(f.estado.nunique()),
 'etapas_distintas_validas':int(f.loc[f.etapas!='NO DEFINIDO','etapas'].nunique()),
}

# Para la pregunta 1: no se agregan monedas distintas.
q1=f.groupby(['anio','mes','moneda'],as_index=False).agg(monto=('monto','sum'),adjudicaciones=('nk_adjudicacion','size'))
q2=f.groupby(['anio','moneda','estado_general'],as_index=False).agg(adjudicaciones=('nk_adjudicacion','size'),monto=('monto','sum'),promedio=('monto','mean'))
pyg=f[f.moneda=='PYG'].copy()
q3=pyg.groupby('nk_ruc',as_index=False).agg(monto=('monto','sum'),adjudicaciones=('nk_adjudicacion','size'))
# SCD1: el nombre que se expone es el último visto por RUC en el lote válido.
ultimo_nombre=f.drop_duplicates('nk_ruc',keep='last').set_index('nk_ruc')['nombre']
q3['nombre']=q3.nk_ruc.map(ultimo_nombre)
q3=q3.sort_values('monto',ascending=False).head(10).copy()
q3['porcentaje_total_pyg']=q3.monto/pyg.monto.sum()*100
q3.insert(0,'puesto',range(1,len(q3)+1))
rows=[]
for anio, g in pyg.groupby('anio'):
 t=g.groupby('nk_ruc').monto.sum().nlargest(10)
 rows.append({'anio':int(anio),'monto_top10':float(t.sum()),'monto_total':float(g.monto.sum()),'porcentaje':float(t.sum()/g.monto.sum()*100),'adjudicaciones':len(g)})
q4=pd.DataFrame(rows).sort_values('anio')
rows=[]
for (anio,moneda),g in f.groupby(['anio','moneda']):
 counts=g.groupby('nk_ruc').nk_adjudicacion.transform('size')
 rec=g[counts>10]
 rows.append({'anio':int(anio),'moneda':moneda,'monto_recurrentes':float(rec.monto.sum()),'monto_total':float(g.monto.sum()),'porcentaje':float(rec.monto.sum()/g.monto.sum()*100),'proveedores_recurrentes':int(rec.nk_ruc.nunique())})
q5=pd.DataFrame(rows).sort_values(['anio','moneda'])

stages={'Planificación':'planning', 'Licitación':'tender', 'Adjudicación':'award', 'Contrato':'contract', 'Implementación':'implementation', 'Modificación del contrato':'contractamendment','Terminación del contrato':'contracttermination'}
q6=[]
for label,token in stages.items():
 ct=int(f.etapas.map(lambda s:token in s.split(';')).sum())
 q6.append({'etapa':label,'adjudicaciones':ct,'porcentaje_total':round(ct/len(f)*100,4)})
q6.append({'etapa':'No definido','adjudicaciones':int((f.etapas=='NO DEFINIDO').sum()),'porcentaje_total':round((f.etapas=='NO DEFINIDO').mean()*100,4)})
q6=pd.DataFrame(q6)

# Dashboard (snapshot de las agregaciones hechas con criterios del modelo estrella).
# Se suministra asimismo el exportador que obtiene las mismas tablas DESDE fact/dim.
data={
 'p1_ventas_anio_moneda':f.groupby(['anio','moneda'],as_index=False).agg(adjudicaciones=('nk_adjudicacion','size'),monto=('monto','sum')),
 'p1_ventas_mes_moneda':q1,
 'p2_estado_anio':q2,
 'p3_top10_proveedores':q3,
 'p4_concentracion_anual':q4,
 'p5_recurrentes_anual':q5,
 'p6_etapas':q6,
}
for name,tbl in data.items(): tbl.to_csv(OUT/f'{name}.csv',index=False,encoding='utf-8-sig',float_format='%.6f')
(R/'docs'/'metricas_h3_cotejo_pandas.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
print('\nTOP 10:\n',q3.to_string(index=False))
print('\nQ4 CONCENTRACIÓN:\n',q4.to_string(index=False))
print('\nQ6 ETAPAS:\n',q6.to_string(index=False))

"""Construye los conjuntos de la Entrega 2 a partir de lo que guardó el notebook de la Entrega 1.

Entradas (en CORTEIDH_BASE): procesado/parrafos.parquet y procesado/caracteristicas/chunks.parquet
Salidas:
  procesado/clasificacion/articulos.parquet               tarea 1: hechos → artículos violados
  procesado/clasificacion/secciones.parquet               tarea 2: chunk → sección
  procesado/clasificacion/secciones_sin_etiqueta.parquet  chunks «Sin sección» (aplicación de la tarea 2)
  clasificacion/particiones_*.csv                         particiones fijas (van en git)

Uso: python clasificacion/construir_conjuntos.py
Las particiones se regeneran solo si no existen; para rehacerlas a propósito, bórrelas antes.
"""
import sys

import numpy as np
import pandas as pd
from iterstrat.ml_stratifiers import MultilabelStratifiedKFold
from sklearn.model_selection import StratifiedGroupKFold

from comun import (ANIO_CORTE, BASE_DIR, CLASES_SECCION, DIR_DATOS, MIN_PALABRAS_CHUNK, MIN_PALABRAS_HECHOS,
                   MIN_POSITIVOS, N_PARTICIONES, PARTICIONES_ARTICULOS, PARTICIONES_SECCIONES, SEMILLA)

sys.stdout.reconfigure(encoding="utf-8")
DIR_DATOS.mkdir(parents=True, exist_ok=True)
chunks = pd.read_parquet(BASE_DIR / "procesado/caracteristicas/chunks.parquet")
temporal = lambda anio: np.select([anio.le(ANIO_CORTE), anio.gt(ANIO_CORTE)], ["entrenamiento", "prueba"], "sin_anio")

# ── Tarea 1: artículos violados a partir de los hechos ──
docs = (chunks.groupby("doc_id")
        .agg(caso_id=("caso_id", "first"), titulo=("titulo", "first"), estado=("estado", "first"),
             anio=("anio", "first"), tipo_sentencia=("tipo_sentencia", "first"),
             articulos=("articulos_violados", "first")))
docs = docs[docs["tipo_sentencia"].eq("fondo") & docs["articulos"].map(len).gt(0)]

parr = pd.read_parquet(BASE_DIR / "procesado/parrafos.parquet",
                       columns=["doc_id", "orden", "parte", "seccion_canonica", "es_portada", "texto", "lemas"])
hechos = (parr[parr["seccion_canonica"].eq("Hechos") & parr["parte"].eq("cuerpo") & ~parr["es_portada"]
               & parr["doc_id"].isin(docs.index)]
          .sort_values(["doc_id", "orden"])
          .groupby("doc_id").agg(texto=("texto", "\n\n".join), lemas=("lemas", " ".join)))
hechos["num_palabras"] = hechos["texto"].str.split().str.len()
art = docs.join(hechos, how="inner")
sin_hechos = len(docs) - len(art)
art = art[art["num_palabras"].ge(MIN_PALABRAS_HECHOS)]
assert art["caso_id"].is_unique, "hay dos sentencias de fondo del mismo caso: use particiones por grupo"

conteo = pd.Series([a for l in art["articulos"] for a in l]).value_counts()
etiquetas = sorted(int(a) for a in conteo[conteo.ge(MIN_POSITIVOS)].index)
for a in etiquetas:
    art[f"art_{a}"] = art["articulos"].map(lambda l, a=a: int(a in l))
art = art[art[[f"art_{a}" for a in etiquetas]].sum(axis=1).gt(0)]       # sin ninguna etiqueta retenida no aporta
art["articulos"] = art["articulos"].map(lambda l: [int(a) for a in l])
art["temporal"] = temporal(art["anio"])
art = art.reset_index()
art.to_parquet(DIR_DATOS / "articulos.parquet", index=False)

if not PARTICIONES_ARTICULOS.exists():
    Y = art[[f"art_{a}" for a in etiquetas]].to_numpy()
    part = np.empty(len(art), dtype=int)
    for k, (_, prueba) in enumerate(MultilabelStratifiedKFold(N_PARTICIONES, shuffle=True, random_state=SEMILLA)
                                    .split(art, Y)):
        part[prueba] = k
    pd.DataFrame({"doc_id": art["doc_id"], "particion": part}).to_csv(PARTICIONES_ARTICULOS, index=False)

print(f"Tarea 1: {len(art)} sentencias de fondo ({sin_hechos} sin sección Hechos, "
      f"{len(docs) - sin_hechos - len(art)} con hechos muy cortos o sin etiquetas retenidas)")
print(f"  {len(etiquetas)} artículos con ≥ {MIN_POSITIVOS} sentencias: {etiquetas}")
print(f"  descartados: {sorted(int(a) for a in conteo[conteo.lt(MIN_POSITIVOS)].index)}")
print(f"  temporal: {art['temporal'].value_counts().to_dict()}")

# ── Tarea 2: sección de cada chunk ──
base = chunks[chunks["casi_duplicado_de"].isna() & chunks["num_palabras"].ge(MIN_PALABRAS_CHUNK)]
cols = ["chunk_id", "doc_id", "caso_id", "estado", "anio", "tipo_sentencia", "seccion", "seccion_canonica",
        "parte", "num_palabras", "texto", "texto_normalizado"]
sec = base[base["seccion_canonica"].isin(CLASES_SECCION)][cols].reset_index(drop=True)
sec["temporal"] = temporal(sec["anio"])
sec.to_parquet(DIR_DATOS / "secciones.parquet", index=False)
base[base["seccion_canonica"].eq("Sin sección")][cols].to_parquet(DIR_DATOS / "secciones_sin_etiqueta.parquet",
                                                                   index=False)

if not PARTICIONES_SECCIONES.exists():
    part = np.empty(len(sec), dtype=int)
    sgkf = StratifiedGroupKFold(N_PARTICIONES, shuffle=True, random_state=SEMILLA)
    for k, (_, prueba) in enumerate(sgkf.split(sec, sec["seccion_canonica"], groups=sec["caso_id"])):
        part[prueba] = k
    pd.DataFrame({"chunk_id": sec["chunk_id"], "particion": part}).to_csv(PARTICIONES_SECCIONES, index=False)

print(f"Tarea 2: {len(sec)} chunks de {sec['caso_id'].nunique()} casos "
      f"({chunks['casi_duplicado_de'].notna().sum()} casi duplicados fuera)")
print("  " + str(sec["seccion_canonica"].value_counts().to_dict()))
print(f"  sin sección (aplicación): {base['seccion_canonica'].eq('Sin sección').sum()} chunks")

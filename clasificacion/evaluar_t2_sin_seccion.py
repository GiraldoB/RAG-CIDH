"""Prueba de la Tarea 2 en los chunks «Sin sección», contra las etiquetas de secciones_romanas.py.

Uso:  python clasificacion/evaluar_t2_sin_seccion.py
Necesita t2_sin_seccion_predicciones.csv (lo escribe t2_secciones.ipynb) y secciones_romanas/chunks_etiquetados.csv.
Escribe resultados/t2_eval_sin_seccion.csv (métricas) y t2_eval_sin_seccion_confusion.csv.

«Otra» (introducción, procedimiento, competencia, resoluciones) no es una clase de la Tarea 2: esos chunks no se
evalúan, pero se cuenta cuántos de ellos acepta el umbral (falsos positivos inevitables del clasificador).
"""
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

sys.path.append(str(Path(__file__).resolve().parent))
from comun import CLASES_SECCION, DIR_DATOS, DIR_RESULTADOS  # noqa: E402

pred = pd.read_csv(DIR_RESULTADOS / "t2_sin_seccion_predicciones.csv")
ref = pd.read_csv(DIR_DATOS / "secciones_romanas" / "chunks_etiquetados.csv")
df = pred.merge(ref[["chunk_id", "etiqueta", "origen", "nota"]], on="chunk_id", how="left", validate="one_to_one")
assert len(df) == len(pred)

filas = []
for nombre, m in [("todas", df["etiqueta"].isin(CLASES_SECCION)),
                  ("aceptadas (umbral)", df["etiqueta"].isin(CLASES_SECCION) & df["acepta"]),
                  ("sin cruzar secciones", df["etiqueta"].isin(CLASES_SECCION) & df["nota"].isna())]:
    d = df[m]
    if len(d):
        filas.append(dict(subconjunto=nombre, n=len(d), exactitud=accuracy_score(d["etiqueta"], d["seccion_predicha"]),
                          f1_macro=f1_score(d["etiqueta"], d["seccion_predicha"], labels=sorted(d["etiqueta"].unique()),
                                            average="macro", zero_division=0)))
for origen, d in df[df["etiqueta"].isin(CLASES_SECCION)].groupby("origen"):
    filas.append(dict(subconjunto=f"origen: {origen}", n=len(d), exactitud=accuracy_score(d["etiqueta"], d["seccion_predicha"])))
otra = df["etiqueta"].eq("Otra")
filas.append(dict(subconjunto="«Otra» aceptada por el umbral (no evaluable)", n=int((otra & df["acepta"]).sum())))
filas.append(dict(subconjunto="sin etiqueta de referencia todavía", n=int(df["etiqueta"].isna().sum())))
res = pd.DataFrame(filas)
res.to_csv(DIR_RESULTADOS / "t2_eval_sin_seccion.csv", index=False)
d = df[df["etiqueta"].isin(CLASES_SECCION)]
conf = pd.crosstab(d["etiqueta"], d["seccion_predicha"], rownames=["referencia"], colnames=["predicha"])
conf.to_csv(DIR_RESULTADOS / "t2_eval_sin_seccion_confusion.csv")
print(res.round(3).to_string(index=False))
print(conf.to_string())

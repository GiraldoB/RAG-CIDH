"""Prueba de la Tarea 2 en los chunks «Sin sección», contra las etiquetas de referencia de secciones_romanas.py.

Uso:  python clasificacion/evaluar_t2_sin_seccion.py      (o, desde el notebook: from evaluar_t2_sin_seccion import evaluar)
Necesita t2_sin_seccion_predicciones.csv (lo escribe t2_secciones.ipynb) y secciones_romanas/chunks_etiquetados.csv.
Escribe resultados/t2_eval_sin_seccion.csv (métricas) y t2_eval_sin_seccion_confusion.csv.
"""
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

sys.path.append(str(Path(__file__).resolve().parent))
from comun import CLASES_SECCION, DIR_DATOS, DIR_RESULTADOS  # noqa: E402

RUTA_REFERENCIA = DIR_DATOS / "secciones_romanas" / "chunks_etiquetados.csv"


def _fila(nombre, d):
    return dict(subconjunto=nombre, n=len(d), exactitud=accuracy_score(d["etiqueta"], d["seccion_predicha"]),
                f1_macro=f1_score(d["etiqueta"], d["seccion_predicha"], labels=sorted(d["etiqueta"].unique()),
                                  average="macro", zero_division=0))


def evaluar(pred, guardar=True):
    """pred: columnas chunk_id, anio, seccion_predicha, acepta. Devuelve (métricas, matriz de confusión, unión)."""
    ref = pd.read_csv(RUTA_REFERENCIA)
    df = pred.merge(ref[["chunk_id", "etiqueta", "origen", "nota"]], on="chunk_id", how="left", validate="one_to_one")
    assert len(df) == len(pred)
    assert df["etiqueta"].dropna().isin(CLASES_SECCION).all(), "la referencia tiene etiquetas fuera de CLASES_SECCION"
    ev = df[df["etiqueta"].notna()]
    filas = [_fila("todas", ev), _fila("aceptadas (umbral)", ev[ev["acepta"]]),
             _fila("sin cruzar secciones", ev[ev["nota"].isna()]),
             _fila("sentencias 1987–1999", ev[ev["anio"] < 2000]), _fila("sentencias desde 2000", ev[ev["anio"] >= 2000])]
    filas += [_fila(f"origen: {o}", d) for o, d in ev.groupby("origen")]
    filas.append(dict(subconjunto="sin etiqueta de referencia", n=int(df["etiqueta"].isna().sum())))
    res = pd.DataFrame(filas)
    conf = pd.crosstab(ev["etiqueta"], ev["seccion_predicha"], rownames=["referencia"], colnames=["predicha"])
    acep = ev[ev["acepta"]]
    prec = (acep["etiqueta"] == acep["seccion_predicha"]).groupby(acep["seccion_predicha"]).agg(["size", "mean"])
    prec.columns = ["aceptados", "precisión"]
    if guardar:
        res.to_csv(DIR_RESULTADOS / "t2_eval_sin_seccion.csv", index=False)
        conf.to_csv(DIR_RESULTADOS / "t2_eval_sin_seccion_confusion.csv")
        prec.to_csv(DIR_RESULTADOS / "t2_eval_sin_seccion_precision_aceptados.csv")
    return res, conf, prec


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    res, conf, prec = evaluar(pd.read_csv(DIR_RESULTADOS / "t2_sin_seccion_predicciones.csv"))
    print(res.round(3).to_string(index=False))
    print(conf.to_string())
    print(prec.round(3).to_string())

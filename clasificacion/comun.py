"""Código común de la Entrega 2 (clasificación). Lo usan los tres notebooks para que los resultados sean comparables.

Uso:
    import sys; sys.path.append("clasificacion")          # o la ruta a esta carpeta en Colab
    from comun import *
    df, Y, etiquetas = cargar_articulos()
    for k, entrena, prueba in iterar_particiones(df): ...

Los datos se leen de CORTEIDH_BASE (la misma variable del notebook de la Entrega 1).
"""
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score, f1_score,
                             hamming_loss, precision_score, recall_score)

# ── Contrato del equipo: no cambiar sin avisar a los demás ──
SEMILLA = 42
N_PARTICIONES = 5
ANIO_CORTE = 2018            # prueba temporal: entrena con sentencias hasta 2018, evalúa con 2019 en adelante
MIN_POSITIVOS = 25           # un artículo entra como etiqueta si se declara violado en al menos 25 sentencias
MIN_PALABRAS_HECHOS = 100    # sentencias con menos palabras de hechos quedan fuera
MIN_PALABRAS_CHUNK = 20
CLASES_SECCION = ["Hechos", "Prueba", "Fondo", "Reparaciones", "Excepciones preliminares", "Puntos resolutivos", "Otra"]
# «Otra»: trámite y contexto, no la decisión. Sin esta clase, el 32 % de los chunks «Sin sección» (introducción,
# procedimiento…) recibía a la fuerza una de las otras seis (ver t2_etiquetas_sin_seccion.md).
OTRA_CANONICAS = {"Introducción de la causa", "Procedimiento ante la Corte", "Competencia", "Consideraciones previas"}
# Dentro de «Otras» del notebook hay de todo (títulos de artículos que son Fondo, costas…): solo estos títulos son «Otra»
RE_OTRA_TITULO = re.compile(r"^(?:[IVXL]+(?:[-.]\d+)?\.?\s*[-–—]?\s*)?(?:RECONOCIMIENTO|ADMISIBILIDAD|"
                            r"CONSIDERACI[OÓ]N(?:ES)? PREVIAS?|MEDIDAS PROVISIONALES)", re.IGNORECASE)


def seccion_t2(canonica, titulo):
    """Etiqueta de la tarea 2 a partir de seccion_canonica y del título original; None si el chunk no entra."""
    if canonica in OTRA_CANONICAS or (canonica == "Otras" and RE_OTRA_TITULO.match(str(titulo).strip())):
        return "Otra"
    return canonica if canonica in CLASES_SECCION else None

BASE_DIR = Path(os.environ.get("CORTEIDH_BASE", "/content/drive/MyDrive/corteidh_rag/content/corte_idh_descargas"))
AQUI = Path(__file__).resolve().parent
# En local (o en cualquier equipo sin la carpeta de Drive) se usa la raíz del repositorio.
if not (BASE_DIR / "procesado" / "clasificacion").is_dir() and (AQUI.parent / "procesado" / "clasificacion").is_dir():
    BASE_DIR = AQUI.parent
DIR_DATOS = BASE_DIR / "procesado" / "clasificacion"
DIR_RESULTADOS = DIR_DATOS / "resultados"
PARTICIONES_ARTICULOS = AQUI / "particiones_articulos.csv"     # en git: las mismas particiones para todos
PARTICIONES_SECCIONES = AQUI / "particiones_secciones.csv"


# ── Carga ──
def _con_particiones(df, ruta, clave):
    part = pd.read_csv(ruta)
    df = df.merge(part, on=clave, how="inner", validate="one_to_one")
    assert len(df) == len(part), f"{ruta.name}: faltan filas; regenere con construir_conjuntos.py"
    return df.reset_index(drop=True)


def cargar_articulos():
    """Tarea 1. Devuelve (df, Y, etiquetas).
    df: una fila por sentencia de fondo, con 'texto' y 'lemas' de la sección Hechos, 'particion' (0–4) y 'temporal'.
    Y: matriz binaria (sentencias × artículos). etiquetas: los artículos, en el orden de las columnas de Y."""
    df = _con_particiones(pd.read_parquet(DIR_DATOS / "articulos.parquet"), PARTICIONES_ARTICULOS, "doc_id")
    etiquetas = sorted(int(c.removeprefix("art_")) for c in df.columns if c.startswith("art_"))
    Y = df[[f"art_{a}" for a in etiquetas]].to_numpy(dtype=int)
    return df, Y, etiquetas


def cargar_secciones():
    """Tarea 2. Devuelve (df, y): una fila por chunk (texto sin cabecera), y = sección canónica (str)."""
    df = _con_particiones(pd.read_parquet(DIR_DATOS / "secciones.parquet"), PARTICIONES_SECCIONES, "chunk_id")
    return df, df["seccion_canonica"].to_numpy()


def cargar_sin_seccion():
    """Chunks «Sin sección»: el conjunto de aplicación de la tarea 2 (no tienen etiqueta)."""
    return pd.read_parquet(DIR_DATOS / "secciones_sin_etiqueta.parquet")


def iterar_particiones(df):
    """Validación cruzada externa: produce (k, índices de entrenamiento, índices de prueba).
    Para la validación interna (hiperparámetros, umbrales), particione solo el entrenamiento."""
    for k in range(N_PARTICIONES):
        prueba = df["particion"].to_numpy() == k
        yield k, np.flatnonzero(~prueba), np.flatnonzero(prueba)


def particion_temporal(df):
    """Prueba temporal: (índices hasta ANIO_CORTE, índices posteriores)."""
    t = df["temporal"].to_numpy()
    return np.flatnonzero(t == "entrenamiento"), np.flatnonzero(t == "prueba")


# ── Preprocesamiento opcional (para la ablación) ──
_NUM = r"\d+(?:\.\d+)*(?:\.[a-z])?"
_CITA = re.compile(
    rf"\b(art[íi]culos?|arts?\.)\s*{_NUM}(?:\s*(?:,|y|e|o|a|al)\s*{_NUM})*", re.IGNORECASE)


_CITA_LEMA = re.compile(r"\bart_\d+(?:_\d+)*\b")      # en lemas: la Entrega 1 convirtió «artículo 8.1» en «art_8_1»


def tapar_citas(texto):
    """Reemplaza las citas de artículos («artículos 8.1 y 25», «art. 5», y en lemas «art_8_1») por «ARTICULO»:
    pueden delatar la etiqueta."""
    return _CITA_LEMA.sub("ARTICULO", _CITA.sub("ARTICULO", texto))


def tapar_estados(texto, estados):
    """Reemplaza los nombres de los Estados por «ESTADO». shortcut: no tapa gentilicios («peruano») ni víctimas."""
    patron = re.compile(r"\b(" + "|".join(sorted((re.escape(e) for e in estados), key=len, reverse=True)) + r")\b",
                        re.IGNORECASE)
    return patron.sub("ESTADO", texto)


# ── Métricas ──
def metricas_multietiqueta(Y, Y_pred, Y_puntaje=None):
    """Métricas de la tarea 1. Y_puntaje (probabilidades o puntajes) habilita la precisión promedio (área PR)."""
    m = {"f1_micro": f1_score(Y, Y_pred, average="micro", zero_division=0),
         "f1_macro": f1_score(Y, Y_pred, average="macro", zero_division=0),
         "precision_micro": precision_score(Y, Y_pred, average="micro", zero_division=0),
         "exhaustividad_micro": recall_score(Y, Y_pred, average="micro", zero_division=0),
         "hamming": hamming_loss(Y, Y_pred),
         "exactitud_estricta": accuracy_score(Y, Y_pred)}
    if Y_puntaje is not None:
        m["ap_macro"] = average_precision_score(Y, Y_puntaje, average="macro")
        m["ap_micro"] = average_precision_score(Y, Y_puntaje, average="micro")
    return m


def f1_por_etiqueta(Y, Y_pred, etiquetas):
    return pd.DataFrame({"articulo": etiquetas, "positivos": Y.sum(0),
                         "f1": f1_score(Y, Y_pred, average=None, zero_division=0)})


def metricas_multiclase(y, y_pred):
    """Métricas de la tarea 2."""
    return {"exactitud": accuracy_score(y, y_pred),
            "exactitud_balanceada": balanced_accuracy_score(y, y_pred),
            "f1_macro": f1_score(y, y_pred, average="macro", zero_division=0),
            "f1_ponderado": f1_score(y, y_pred, average="weighted", zero_division=0)}


def resumir(filas):
    """filas: lista de dicts {'modelo', 'particion', métrica: valor}. Devuelve media y desviación por modelo."""
    t = pd.DataFrame(filas).drop(columns="particion")
    return t.groupby("modelo").agg(["mean", "std"]).round(4)


def guardar_tabla(tabla, nombre):
    """Guarda en procesado/clasificacion/resultados/<nombre>.csv (nombre: t1_..., t2_... según la tarea)."""
    DIR_RESULTADOS.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(DIR_RESULTADOS / f"{nombre}.csv", encoding="utf-8")
    return tabla

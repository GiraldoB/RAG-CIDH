"""Verifica los conjuntos, las particiones y las funciones de comun.py. Uso: python clasificacion/pruebas_comun.py"""
import sys

import numpy as np

from comun import (CLASES_SECCION, N_PARTICIONES, cargar_articulos, cargar_secciones, cargar_sin_seccion,
                   iterar_particiones, metricas_multietiqueta, metricas_multiclase, particion_temporal,
                   tapar_citas, tapar_estados)

sys.stdout.reconfigure(encoding="utf-8")

# Funciones de texto
assert tapar_citas("violó los artículos 8.1 y 25 de la Convención") == "violó los ARTICULO de la Convención"
assert tapar_citas("conforme al art. 5.2 y al artículo 63.1") == "conforme al ARTICULO y al ARTICULO"
assert tapar_citas("en el párrafo 8 de la sentencia") == "en el párrafo 8 de la sentencia"
assert tapar_estados("El Perú y la República Dominicana", ["Perú", "República Dominicana"]) == "El ESTADO y la ESTADO"

# Métricas
Y = np.array([[1, 0], [0, 1], [1, 1]])
m = metricas_multietiqueta(Y, Y, Y.astype(float))
assert m["f1_micro"] == m["f1_macro"] == m["exactitud_estricta"] == m["ap_macro"] == 1 and m["hamming"] == 0
assert metricas_multiclase(np.array(["a", "b"]), np.array(["a", "a"]))["exactitud"] == 0.5

# Tarea 1
df, Y, etiquetas = cargar_articulos()
assert Y.shape == (len(df), len(etiquetas)) and Y.sum(axis=1).min() >= 1
assert df["caso_id"].is_unique and set(df["particion"]) == set(range(N_PARTICIONES))
for k, entrena, prueba in iterar_particiones(df):
    assert len(set(entrena) & set(prueba)) == 0 and len(entrena) + len(prueba) == len(df)
    assert Y[prueba].sum(axis=0).min() >= 3, f"partición {k}: un artículo con menos de 3 positivos en prueba"
ent, pru = particion_temporal(df)
assert df["anio"].iloc[ent].max() < df["anio"].iloc[pru].min()
print(f"Tarea 1 ok: {len(df)} sentencias, {len(etiquetas)} artículos, particiones de "
      f"{sorted(df['particion'].value_counts().tolist())}, positivos mínimos por partición de prueba "
      f"{min(Y[p].sum(axis=0).min() for _, _, p in iterar_particiones(df))}")

# Tarea 2
sec, y = cargar_secciones()
assert set(y) == set(CLASES_SECCION)
assert sec.groupby("caso_id")["particion"].nunique().max() == 1, "un caso aparece en dos particiones"
prop = sec.groupby("particion")["seccion_canonica"].value_counts(normalize=True).unstack()
assert (prop.max() - prop.min()).max() < 0.05, "las clases quedaron muy desbalanceadas entre particiones"
assert not sec["texto"].str.startswith("Caso ").any() or sec["texto"].str.contains(" · párrs. ").sum() == 0
assert len(cargar_sin_seccion()) > 0
print(f"Tarea 2 ok: {len(sec)} chunks, particiones de {sorted(sec['particion'].value_counts().tolist())}, "
      f"diferencia máxima de proporción de clase entre particiones {(prop.max() - prop.min()).max():.3f}")

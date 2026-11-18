# Entrega 2: clasificación

Base común del equipo. Todos usan los mismos conjuntos, las mismas particiones y las mismas métricas, para que los resultados se puedan comparar y juntar en el artículo.

## Archivos

| Archivo | Qué es | ¿En git? |
|---|---|---|
| `comun.py` | Constantes del contrato, carga de datos, particiones, preprocesamiento opcional, métricas, guardado de tablas | sí |
| `construir_conjuntos.py` | Arma los conjuntos a partir de `parrafos.parquet` y `chunks.parquet` de la Entrega 1 | sí |
| `pruebas_comun.py` | Verifica conjuntos, particiones y funciones | sí |
| `particiones_articulos.csv`, `particiones_secciones.csv` | Partición (0–4) de cada sentencia y de cada chunk | sí |
| `procesado/clasificacion/*.parquet` | Los conjuntos (≈ 60 MB) | no: van por Drive |
| `procesado/clasificacion/resultados/` | Tablas de resultados (`guardar_tabla`) | no: van por Drive |

## Puesta en marcha

```bash
pip install -r requirements.txt
export CORTEIDH_BASE=/ruta/a/la/carpeta/del/proyecto   # en Colab, la carpeta de Drive
python clasificacion/construir_conjuntos.py           # solo si no tiene los .parquet de Drive
python clasificacion/pruebas_comun.py
```

En el notebook:

```python
import sys; sys.path.append("clasificacion")
from comun import *
df, Y, etiquetas = cargar_articulos()          # tarea 1
sec, y = cargar_secciones()                    # tarea 2
for k, entrena, prueba in iterar_particiones(df):
    ...
```

## Tarea 1: artículos violados a partir de los hechos (multietiqueta)

- **Entrada:** el texto de la sección Hechos de cada sentencia de fondo (`texto`, o `lemas`). Nunca el fondo ni los puntos resolutivos, que dicen la respuesta.
- **Etiquetas:** los artículos de la Convención que la sentencia declara violados y que aparecen en al menos 25 sentencias. Son 15: 3, 4, 5, 7, 8, 11, 13, 17, 19, 21, 22, 23, 24, 25, 26. `construir_conjuntos.py` las recalcula desde los puntos resolutivos con la regla de la Entrega 1 corregida (listas «7.1, 11.2, y 26»; ver `CAMBIOS.md`, sección 11).
- **Datos:** 305 sentencias, una por caso. Quedan fuera 67 sin sección Hechos detectada y 1 con hechos muy cortos.
- **Particiones:** 5, con estratificación iterativa multietiqueta. Cada artículo tiene al menos 7 positivos en cada partición de prueba.
- **Prueba temporal:** entrenar con 147 sentencias hasta 2018 y evaluar con 158 de 2019 en adelante (`particion_temporal`).
- **Cuidado:** el 79 % de los textos de hechos cita «artículo N», aunque muchas citas son de leyes nacionales. `tapar_citas` las reemplaza; reporten resultados con y sin tapar. Sirve para `texto` y para `lemas`: la normalización de la Entrega 1 convirtió «artículo 8.1» en el término `art_8_1`, así que los lemas también llevan las citas (243 de las 305 sentencias tienen alguna).

### Resultados (notebook `t1_articulos.ipynb`)

Medias de las 5 particiones externas, con validación anidada. Las cifras salen de las tablas `procesado/clasificacion/resultados/t1_*.csv`.

| Modelo | F1 macro | AP macro | F1 micro |
|---|---|---|---|
| Proporción de cada artículo (sin texto) | 0,18 | 0,33 | 0,61 |
| TF-IDF + regresión logística, umbral 0,5, sin ajustar | 0,58 | 0,68 | 0,76 |
| **TF-IDF + regresión logística, final** | **0,62** | 0,69 | 0,74 |
| TF-IDF + SVM lineal, final | 0,63 | 0,70 | 0,74 |
| e5 + regresión logística, final | 0,60 | 0,67 | 0,72 |

- **Modelo final.** Lemas con las citas tapadas. Hiperparámetros elegidos por AP macro y un umbral por artículo, todo dentro del entrenamiento de cada partición.
- **Comparaciones** (*bootstrap* pareado):
  - El modelo final supera al mismo modelo sin ajustar en +0,046 [0,018; 0,078].
  - Empata con el SVM.
  - Supera a e5 sin ajustar por poco: +0,022 [0,000; 0,045].
- **Prueba temporal** (entrenar hasta 2018 y evaluar desde 2019):
  - F1 macro de 0,62 con el modelo final, frente a 0,45 con umbral 0,5. La validación cruzada sobre las mismas sentencias da 0,665.
  - La AP casi no cambia (0,67).
  - La pérdida real se concentra en los artículos 13, 26, 17 y 24, que se volvieron frecuentes después de 2018.
- **Atajos.** Tapar las citas, los Estados o las personas y lugares no baja el rendimiento.
- **Análisis de errores.** Parte del error viene de la etiqueta:
  - El 26 cambió de criterio en 2017 (*concept drift*).
  - El 24 y el 13 son calificaciones que se deciden en el fondo.
  - La regla de extracción tenía errores; el de las listas con «, y» se corrigió.

Documentación de la tarea: `t1_bitacora.md` (decisiones y hallazgos), `t1_glosario.md` (conceptos) y `t1_seccion_articulo.md` (borrador de la sección del artículo).

## Tarea 2: sección de cada chunk (multiclase)

- **Entrada:** `texto` del chunk, sin la cabecera (`texto_con_contexto` incluye el título de la sección: no usarlo). Los embeddings guardados en la Entrega 1 se calcularon con cabecera; hay que recalcularlos.
- **Clases:** Hechos, Prueba, Fondo, Reparaciones, Excepciones preliminares, Puntos resolutivos y **Otra**. «Otra» agrupa introducción de la causa, procedimiento, competencia, consideraciones previas, reconocimiento de responsabilidad, admisibilidad y medidas provisionales (`seccion_t2()` en `comun.py`). Se agregó el 17-11-2026 porque el 32 % de los chunks «Sin sección» son trámite y, sin esa clase, recibían a la fuerza una sección equivocada.
- **Datos:** 68.093 chunks de 424 casos. Se excluyen los casi duplicados y los chunks de menos de 20 palabras. La sección original del notebook de la Entrega 1 queda en `seccion_original`.
- **Particiones:** 5, por caso (`StratifiedGroupKFold`): un caso nunca está en entrenamiento y prueba a la vez. Se regeneraron al agregar «Otra».
- **Conjunto de aplicación:** 1.718 chunks «Sin sección» (`cargar_sin_seccion`). Tienen etiquetas de referencia por sección del PDF (`secciones_romanas.py`) y se evalúan con `evaluar_t2_sin_seccion.py`; ver `t2_etiquetas_sin_seccion.md`.

## Contrato

- **Constantes:** semilla 42, 5 particiones, año de corte 2018. Están en `comun.py`; si alguien necesita cambiarlas, lo avisa al grupo.
- **Validación anidada:** los hiperparámetros y los umbrales se eligen dentro del entrenamiento de cada partición, nunca mirando la de prueba.
- **Ajustes dentro del `Pipeline`:** todo lo que se ajusta con datos (vocabulario TF-IDF, escalado, selección de características) va dentro del `Pipeline`. El `tfidf_vectorizer.joblib` de la Entrega 1 se ajustó con todo el corpus y no sirve aquí.
- **Métricas:**
  - Tarea 1: `metricas_multietiqueta`, con puntajes para la AP, y `f1_por_etiqueta`.
  - Tarea 2: `metricas_multiclase` y matriz de confusión.
- **Formato de resultados:** una fila por modelo y partición, `{"modelo", "particion", ...métricas}`. `resumir()` da media y desviación. Se guardan con `guardar_tabla(tabla, "t1_...")` o `"t2_..."`.
- **Notebooks:** uno por persona: `t1_articulos.ipynb`, `t2_secciones.ipynb`. Se integran al final.
- **Figuras:** se guardan en `procesado/figuras/` con prefijo `c` (`c01_...`). La numeración final se fija en el artículo.

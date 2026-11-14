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
- **Etiquetas:** los artículos de la Convención que la sentencia declara violados y que aparecen en al menos 25 sentencias. Son 15: 3, 4, 5, 7, 8, 11, 13, 17, 19, 21, 22, 23, 24, 25, 26.
- **Datos:** 305 sentencias, una por caso. Quedan fuera 67 sin sección Hechos detectada y 1 con hechos muy cortos.
- **Particiones:** 5, con estratificación iterativa multietiqueta. Cada artículo tiene al menos 7 positivos en cada partición de prueba.
- **Prueba temporal:** entrenar con 147 sentencias hasta 2018 y evaluar con 158 de 2019 en adelante (`particion_temporal`).
- **Cuidado:** el 79 % de los textos de hechos cita «artículo N». `tapar_citas` lo reemplaza; reporten resultados con y sin tapar.

Línea base de referencia, con regresión logística sobre TF-IDF de lemas, citas tapadas, umbral 0,5 y sin ajuste de hiperparámetros. Las cifras son medias de las 5 particiones:

| Modelo | F1 micro | F1 macro | AP macro |
|---|---|---|---|
| Proporción de cada artículo (sin texto) | 0,61 | 0,18 | 0,32 |
| TF-IDF + regresión logística | 0,76 | 0,57 | 0,68 |

El F1 micro de la línea base sin texto es alto porque los artículos 8 y 25 están en casi todas las sentencias. Por eso el F1 macro y la AP macro son las métricas principales.

## Tarea 2: sección de cada chunk (multiclase)

- **Entrada:** `texto` del chunk, sin la cabecera (`texto_con_contexto` incluye el título de la sección: no usarlo). Los embeddings guardados en la Entrega 1 se calcularon con cabecera; hay que recalcularlos.
- **Clases:** Hechos, Prueba, Fondo, Reparaciones, Excepciones preliminares, Puntos resolutivos.
- **Datos:** 59.184 chunks de 422 casos. Se excluyen los casi duplicados y los chunks de menos de 20 palabras.
- **Particiones:** 5, por caso (`StratifiedGroupKFold`): un caso nunca está en entrenamiento y prueba a la vez.
- **Conjunto de aplicación:** 1.718 chunks «Sin sección» (`cargar_sin_seccion`).

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

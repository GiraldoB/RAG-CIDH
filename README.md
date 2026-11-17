# RAG-CIDH: búsqueda y clasificación de la jurisprudencia de la Corte IDH

Proyecto del curso Procesamiento de Lenguaje Natural (Universidad Nacional de Colombia, Grupo 8) sobre las sentencias de casos contenciosos de la Corte Interamericana de Derechos Humanos. Tiene dos partes:
- **Entrega 1:** la base de un sistema RAG (generación aumentada por recuperación), es decir, un buscador que recupera los fragmentos de sentencias que responden una pregunta jurídica.
- **Entrega 2:** clasificación de textos sobre el mismo corpus.

**Integrantes:** Byron Daniel Giraldo Castro, Johan Fernando Sánchez Grajales y Javier Esteban González Vivas. **Profesora:** Elizabeth León Guzmán.

## Entrega 1: recuperación

El notebook `proyecto_corregido.ipynb` hace todo el recorrido:
1. descarga las sentencias y los resúmenes oficiales;
2. extrae el texto de los PDF, separando las notas al pie;
3. limpia el texto: aparta portada, votos individuales, puntos resolutivos y firmas;
4. detecta las secciones (Hechos, Prueba, Fondo, Reparaciones…);
5. lematiza con spaCy;
6. corta en fragmentos de 250 palabras;
7. los indexa con TF-IDF, BM25 y embeddings `e5-base` (FAISS).

La función `buscar()` combina los métodos (léxico, denso e híbrido con RRF), filtros (Estado, años, tipo de sentencia, artículo violado, sección) y diversificación por caso.

**Corpus**

| Elemento | Cantidad |
|---|---|
| Sentencias | 596 (597 descargadas; una duplicada en la fuente) |
| Casos | 437 |
| Resúmenes oficiales | 290 |
| Años | 1987 a 2026 |
| Párrafos | 146.627 |
| Fragmentos indexados | 79.799 |

**Evaluación** (nDCG@10, con consultas juzgadas):

| Conjunto | TF-IDF | BM25 | Denso | Híbrido |
|---|---|---|---|---|
| A · 290 oraciones de resúmenes oficiales (encontrar la sentencia) | 0,83 | **0,84** | 0,56 | 0,72 |
| B · 20 consultas temáticas propias | 0,66 | 0,76 | **0,86** | **0,86** |
| C · 182 subtemas de los Cuadernillos de Jurisprudencia (por sentencia) | 0,30 | 0,32 | **0,37** | 0,36 |

- **Lectura.** Los métodos léxicos ganan cuando la consulta repite las palabras de la sentencia (conjunto A). El denso y el híbrido ganan en las consultas temáticas (B y C). El híbrido es el método más robusto y es el valor por defecto.
- **Juicios del conjunto B.** Los asignó un modelo de lenguaje y una segunda revisión, también con un modelo, coincidió en el 95 % (`evaluacion/qrels_consultas_propias.csv`). Los del conjunto C vienen de los Cuadernillos de la propia Corte.
- **Dónde está el detalle.** Las decisiones, las ablaciones y el análisis exploratorio están en [`CAMBIOS.md`](CAMBIOS.md).
- **Etiqueta.** La versión entregada está marcada con la etiqueta `entrega-1`.

## Entrega 2: clasificación

Hay dos tareas, con etiquetas que salen del pipeline de la Entrega 1. Todas usan los mismos conjuntos, particiones y métricas, definidos en [`clasificacion/README.md`](clasificacion/README.md).

1. **Artículos violados desde los hechos** (multietiqueta, `t1_articulos.ipynb`). La entrada es la sección Hechos de 305 sentencias de fondo; las etiquetas son 15 artículos de la Convención Americana. El modelo final (TF-IDF con regresión logística, un umbral por artículo) alcanza un F1 macro de 0,62, frente a 0,18 de la línea base.
2. **Sección de cada fragmento** (multiclase, `t2_secciones.ipynb`). Son 59.184 fragmentos y 6 secciones. Se valida con particiones agrupadas por caso.

## Estructura

```
proyecto_corregido.ipynb     notebook de la Entrega 1 (descarga → índice → búsqueda → evaluación → análisis)
pruebas_notebook.py          pruebas de las funciones del notebook con datos sintéticos
CAMBIOS.md                   registro de decisiones y resultados de la Entrega 1
t1_articulos.ipynb           Tarea 1 de la Entrega 2
t2_secciones.ipynb           Tarea 2 de la Entrega 2
clasificacion/               base común de la Entrega 2: conjuntos, particiones fijas, métricas y documentación
evaluacion/                  consultas y juicios de relevancia (conjuntos B y C) y extractor de los Cuadernillos
articulo/                    artículo de la Entrega 1 (Articulo.pdf) y de la Entrega 2 (Articulo_entrega2.docx)
requirements.txt             versiones de las librerías
```

## Datos

Los datos no están en git, porque son pesados y se regeneran con los notebooks. El equipo los comparte en la carpeta de Drive del proyecto:

| Carpeta o archivo | Contenido | Lo genera |
|---|---|---|
| `casos/` | PDF de las sentencias y los resúmenes | scraper de `proyecto_corregido.ipynb` |
| `procesado/corpus_limpio.parquet` | texto limpio de cada documento | `proyecto_corregido.ipynb` |
| `procesado/parrafos.parquet` | 146.627 párrafos con parte, sección y lemas | `proyecto_corregido.ipynb` |
| `procesado/caracteristicas/` | `chunks.parquet`, `embeddings.npy`, `indice.faiss` y el vectorizador TF-IDF | `proyecto_corregido.ipynb` |
| `procesado/evaluacion/` | tablas de la evaluación de la recuperación y consultas del conjunto A | `proyecto_corregido.ipynb` |
| `procesado/figuras/` | figuras de los notebooks | todos los notebooks |
| `procesado/clasificacion/` | `articulos.parquet`, `secciones.parquet`, `secciones_sin_etiqueta.parquet` y `resultados/` | `clasificacion/construir_conjuntos.py` y los notebooks de la Entrega 2 |
| `cuadernillos/` | PDF de los cinco Cuadernillos de Jurisprudencia | descarga manual |

## Cómo ejecutar

1. Instalar las dependencias con Python 3.11: `pip install -r requirements.txt`. Para descargar las sentencias, además: `playwright install chromium`.
2. Definir `CORTEIDH_BASE` con la carpeta que contiene `procesado/` (en Colab, la carpeta del proyecto en Drive).
3. **Entrega 1.** Si `casos/` está vacía, poner `DESCARGAR = True` en la celda de configuración; la descarga toma unos 80 minutos. Ejecutar `proyecto_corregido.ipynb` completo: toma alrededor de una hora con GPU, la mayor parte en las ablaciones.
4. **Entrega 2.** Si no se tienen los archivos de `procesado/clasificacion/`, generarlos con `python clasificacion/construir_conjuntos.py` (un par de minutos) y verificarlos con `python clasificacion/pruebas_comun.py`. Luego ejecutar `t1_articulos.ipynb` y `t2_secciones.ipynb`.
5. Probar las funciones de la Entrega 1: `python pruebas_notebook.py proyecto_corregido.ipynb`.

## Fuente de los datos

Las sentencias, los resúmenes oficiales y los Cuadernillos de Jurisprudencia son documentos públicos de la Corte Interamericana de Derechos Humanos ([corteidh.or.cr](https://www.corteidh.or.cr)). Se usan con fines académicos.

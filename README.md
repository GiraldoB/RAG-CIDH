# RAG-CIDH: búsqueda y clasificación de la jurisprudencia de la Corte IDH

Proyecto de Procesamiento de Lenguaje Natural sobre las sentencias de la Corte Interamericana de Derechos Humanos. Tiene dos partes:
- **Entrega 1:** la base de un sistema RAG, es decir, un buscador que recupera los fragmentos de sentencias que responden una pregunta jurídica.
- **Entrega 2:** clasificación de textos sobre el mismo corpus.

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
| Sentencias | 597 |
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
- **Dónde está el detalle.** Las decisiones, las ablaciones y el análisis exploratorio están en [`CAMBIOS.md`](CAMBIOS.md).
- **Etiqueta.** La versión entregada está marcada con la etiqueta `entrega-1`.

## Entrega 2: clasificación (rama `entrega-2`)

Hay dos tareas, con etiquetas que salen del pipeline de la Entrega 1:
1. **Artículos violados desde los hechos** (multietiqueta). La entrada es la sección Hechos de 305 sentencias de fondo; las etiquetas son 15 artículos de la Convención Americana.
2. **Sección de cada fragmento** (multiclase). Son 59.184 fragmentos y 6 secciones. Se valida con particiones agrupadas por caso.

Los conjuntos, las particiones fijas, las métricas y las reglas del equipo están en [`clasificacion/README.md`](https://github.com/GiraldoB/RAG-CIDH/blob/entrega-2/clasificacion/README.md), en la rama `entrega-2`.

## Estructura

```
proyecto_corregido.ipynb   notebook de la Entrega 1 (descarga → índice → búsqueda → evaluación → análisis)
pruebas_notebook.py        pruebas de las funciones del notebook con datos sintéticos
CAMBIOS.md                 registro de decisiones y resultados de la Entrega 1
articulo/                  artículo entregado (Articulo.pdf) y versión actualizada (.docx y .pdf)
evaluacion/                consultas y juicios de relevancia (conjuntos B y C) y extractor de los Cuadernillos
clasificacion/             (rama entrega-2) base común de la Entrega 2
requirements.txt           (rama entrega-2) versiones de las librerías
```

Los datos no están en git, porque son pesados y se regeneran con el notebook:
- `casos/`: los PDF;
- `corpus/`;
- `procesado/`: párrafos, chunks, embeddings, índices, figuras y tablas;
- `cuadernillos/`.

El equipo los comparte por Drive.

## Cómo ejecutar

1. Instalar las dependencias: `pip install -r requirements.txt` (Python 3.11; el archivo está en la rama `entrega-2`).
2. Definir `CORTEIDH_BASE` con la carpeta del proyecto. En Colab, el notebook usa por defecto la ruta de Drive.
3. Si `casos/` está vacía, poner `DESCARGAR = True` en la celda de configuración del notebook. Para eso hace falta haber corrido `playwright install chromium`, y la descarga toma unos 80 minutos.
4. Ejecutar el notebook completo. Toma alrededor de una hora con GPU, la mayor parte en las ablaciones.
5. Probar las funciones: `python pruebas_notebook.py proyecto_corregido.ipynb`.

## Fuente de los datos

Las sentencias, los resúmenes oficiales y los Cuadernillos de Jurisprudencia son documentos públicos de la Corte Interamericana de Derechos Humanos ([corteidh.or.cr](https://www.corteidh.or.cr)). Se usan con fines académicos.

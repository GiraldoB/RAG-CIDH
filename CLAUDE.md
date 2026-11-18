# RAG-CIDH: guía para sesiones de trabajo

## Qué es
Proyecto de PLN (3 estudiantes) sobre las sentencias de la Corte Interamericana de Derechos Humanos.
Este repositorio solo lleva lo que pide la profesora para cada entrega.

- **Entrega 1** (`main`, etiqueta `entrega-1`): recuperación. Todo en `proyecto_corregido.ipynb`.
- **Entrega 2** (`entrega-2`, rama de trabajo actual): clasificación. Tarea 1 (artículos violados) y Tarea 2
  (sección de cada chunk, 7 clases) con sus notebooks ejecutados; el artículo está en `articulo/Articulo_entrega2.docx`.

Antes de tocar nada, lea este archivo y, si la tarea es de la Entrega 2, `clasificacion/README.md` (el contrato común:
conjuntos, particiones y métricas).

## Mapa de archivos
| Ruta | Qué es |
|---|---|
| `proyecto_corregido.ipynb` | Entrega 1 completa: scraping → PDF → párrafos → chunks → índices → `buscar()` → evaluación. **2,6 MB: no leerlo entero** |
| `pruebas_notebook.py` | Pruebas de las funciones del notebook con datos sintéticos (las extrae por marcador de celda) |
| `CAMBIOS.md` | Decisiones y cifras de la Entrega 1. Fuente de verdad de los números |
| `clasificacion/` | Entrega 2: `comun.py` (contrato), `construir_conjuntos.py`, particiones fijas, `secciones_romanas.py` (etiquetas de referencia de «Sin sección»), documentos `t1_*.md` y `t2_*.md` |
| `t1_articulos.ipynb`, `t2_secciones.ipynb` | Notebooks de las Tareas 1 y 2 |
| `articulo/` | Artículos de la Entrega 1 (`Articulo.pdf`, `Articulo_actualizado.*`) y de la Entrega 2 (`Articulo_entrega2.docx`) |
| `evaluacion/` | Conjuntos B (`consultas_propias`, juicios de LLM) y C (`*_cuadernillos`, juicios de la Corte), extractor de cuadernillos e instrucciones de DeepSeek de la Tarea 2 (`revision/`) |
| `casos/`, `corpus/`, `procesado/`, `cuadernillos/` | Datos pesados. **No están en git**; van por Drive |

Artefactos principales (en `procesado/`):
- `parrafos.parquet`: 146.627 párrafos con `doc_id`, `parte`, `num_parrafo`, `texto`, `seccion_canonica`.
- `corpus_limpio.parquet`: una fila por documento, con `titulo`, `estado`, `fecha` (texto), `anio`, `tipo_sentencia`.
- `caracteristicas/chunks.parquet`: 79.799 chunks (`chunk_id`, `doc_id`, `caso_id`, `parr_ini`, `parr_fin`, `texto`,
  `texto_normalizado`, `texto_con_contexto`, `articulos_violados`, `seccion_canonica`, `casi_duplicado_de`).
- `caracteristicas/embeddings.npy` e `indice.faiss`: e5-base, 512 tokens, mismo orden que `chunks.parquet`.
- `caracteristicas/tfidf_vectorizer.joblib`. BM25 no se guarda: se reconstruye desde `texto_normalizado`.

## Cómo correr cada cosa
Siempre con `CORTEIDH_BASE` apuntando a la carpeta del proyecto (la que contiene `procesado/`). Python 3.11.

```bash
pip install -r requirements.txt
export CORTEIDH_BASE=/ruta/al/proyecto          # PowerShell: $env:CORTEIDH_BASE = "C:\ruta\al\proyecto"
python pruebas_notebook.py proyecto_corregido.ipynb    # pruebas de la Entrega 1 (segundos)
python clasificacion/pruebas_comun.py                  # pruebas de la Entrega 2
python evaluacion/extraer_cuadernillos.py cuadernillos procesado/corpus_limpio.parquet   # solo si hay cuadernillos nuevos
```

El notebook completo tarda unos 100 minutos con GPU (52 son las ablaciones). **No lo ejecute** salvo que la
tarea lo pida de forma explícita. Si necesita una cifra, está en `CAMBIOS.md`.

## Cómo leer el notebook sin gastar contexto
Busque la función y lea solo su celda:

```bash
python - <<'EOF'
import json
nb = json.load(open("proyecto_corregido.ipynb", encoding="utf-8"))
for i, c in enumerate(nb["cells"]):
    s = "".join(c["source"])
    if "def buscar(" in s:
        print(i, s)
EOF
```

Celdas útiles (el número puede moverse; busque por el marcador): `def filtrar_tokens(doc):` (normalización),
`def construir_chunks(df):` (chunks y cabecera), `def ranking_lexico(` (TF-IDF y BM25),
`def buscar(consulta` (denso, RRF, filtros, diversificación), `def ndcg_at_k(` (métricas).

## Convenciones
- **Idioma:** todo en español: código, nombres, comentarios, documentos y mensajes de commit.
- **Decimales:** coma decimal en documentos y tablas (0,62). En el código y los CSV, punto.
- **Semilla 42** en todo lo aleatorio. Constantes del contrato en `clasificacion/comun.py`.
- **Particiones fijas:** no regenerar `particiones_*.csv`.
- **Sin fugas:**
  - hiperparámetros, umbrales y prompts se ajustan solo con entrenamiento o con la partición de desarrollo;
  - un caso nunca está en entrenamiento y prueba a la vez;
  - los ejemplos que van dentro de un prompt no pueden salir de la partición de prueba;
  - el modelo que juzga no es el modelo que genera.
- **Cifras:** toda cifra de un documento sale de una tabla guardada o de `CAMBIOS.md`. No se escriben de memoria.
- **Términos:** «sentencia» y «caso» no son lo mismo (596 sentencias, 437 casos). Un chunk es un fragmento de hasta 250 palabras.
- **Pruebas:** datos sintéticos, sin Drive ni GPU, con `check(condición, mensaje)` y la línea final `OK: N comprobaciones`,
  como en `pruebas_notebook.py`.
- **Código nuevo:** fuera del notebook, en módulos `.py` junto a la tarea. El notebook de la Entrega 1 solo se toca para corregir errores.
- **Juicios hechos por un LLM:** se dicen siempre como tales y se validan contra una muestra humana.

## Git
- Ramas: `main` (Entrega 1), `entrega-2` (clasificación). Cada tarea, en una rama corta que sale de la rama de su
  entrega, o directamente en ella si es pequeña.
- Commits pequeños, en español, un tema por commit. No reescribir la historia de ramas compartidas.
- **No hacer push ni abrir PR sin que un estudiante lo pida.**
- Nunca subir `casos/`, `corpus/`, `procesado/`, `cuadernillos/`, claves de API ni archivos `.env`.
- Los notebooks se guardan con las salidas de la ejecución que respalda las cifras.

## Tropiezos conocidos
- **Tuberías y loky:** no pasar la salida de un notebook o de un script con `joblib` por `| grep | tail`.
  Los procesos de loky dejan la tubería abierta y el comando no termina nunca. Redirija a un archivo y léalo después:
  `python guion.py > salida.log 2>&1`.
- **GPU para e5:** los embeddings se calculan con CUDA y fp16 (`batch_size=128`, 150 s para todos los chunks). En CPU
  tardan horas. Codificar una consulta suelta sí es viable en CPU.
- **Prefijos de e5:** las consultas llevan `query: ` y los chunks `passage: `. Sin el prefijo, la recuperación empeora.
- **Ventana de 512 tokens:** con 256 se truncaba el 74 % de los chunks.
- **Consulta normalizada:** TF-IDF y BM25 trabajan sobre lemas. La consulta pasa por `normalizar()`; si no, no coincide con nada.
- **`buscar()` depende de variables globales** del notebook (`df_chunks`, `bm25`, `faiss_index`, `embeddings`,
  `embedding_model`, `normalizar`). Para usarla fuera del notebook, ejecutar sus celdas por marcador, como `pruebas_notebook.py`.
- **Títulos en minúsculas:** `titulo` y `estado` están en minúsculas en los datos. Para mostrar o citar, pasarlos a mayúscula inicial.
- **`articulos_violados` de `chunks.parquet`** tiene la regla anterior a la corrección de `CAMBIOS.md` §11
  (cambian 11 sentencias) hasta que se vuelva a ejecutar el notebook.
- **Conjunto C:** cinco subtemas (C019, C020, C021, C033, C034) están mal extraídos: `extraer_cuadernillos.py` tomó
  como subtema un encabezado en negrita de la sentencia transcrita y les asignó párrafos del subtema siguiente. Las cifras
  de la Entrega 1 sobre C los incluyen; corregirlo cambia esas cifras y renumera las consultas.
- **Puntos resolutivos:** su numeración vuelve a empezar en 1 y choca con la del cuerpo; `doc_id:num_parrafo` no los
  distingue sin la columna `parte`.
- **Embeddings con cabecera:** los guardados incluyen el título de la sección. No sirven para clasificar la sección (Tarea 2).
- **Alegatos:** muchos párrafos de una sentencia resumen lo que alegaron el Estado, la Comisión o los representantes.
  No son un pronunciamiento de la Corte, aunque estén en la sentencia.
- **Votos individuales:** están fuera del índice a propósito. No expresan la decisión de la Corte.
- **Windows:** fijar `PYTHONIOENCODING=utf-8` si la consola muestra mal las tildes. Los archivos se leen con `encoding="utf-8"`.

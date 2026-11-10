# Cambios al notebook: fases 1 y 2 de la revisión

Versión entregada: commit `9dd6cc8` (rama `main`).
Versión corregida: rama `correcciones-fase-1-2` (commit `2c4c516` y siguientes).

El notebook se ejecutó **completo, de principio a fin, en local y con el corpus completo**: las 597 sentencias y los 290 resúmenes, descargados desde cero con el scraper del propio notebook (sección 6). Todas las salidas corresponden a esa ejecución.

Las funciones nuevas también se probaron con datos sintéticos (`pruebas_notebook.py`, 50 comprobaciones). Se validaron en tres etapas, y de cada una salieron cambios adicionales:
- sobre 10 sentencias reales (sección 4);
- con una primera ejecución local de 199 sentencias de 2020–2026 (sección 5);
- con el corpus completo, que incluye las sentencias de 1987–2019 con formatos más antiguos (sección 6).

---

## 1. Construcción del corpus (punto 1)

### Notas al pie separadas por tamaño de fuente
- **Qué:** se agregó la función `separar_notas`. Clasifica como nota cada renglón con fuente menor que la del cuerpo que esté debajo del último renglón del cuerpo de la página. Del cuerpo se quitan los marcadores de nota: dígitos en superíndice o en fuente menor. Quedan las columnas nuevas `texto_cuerpo`, `texto_notas` y `numero_palabras_notas`. `texto_original` no cambia.
- **Por qué:** el texto de las notas quedaba mezclado dentro de los párrafos y contaminaba los chunks y los embeddings. Por ejemplo, el primer resultado de los embeddings era casi todo texto de notas. Además, quitar los marcadores con regex dejaba casos sin cubrir. Separar las notas no exigía rehacer el corpus: los PDF ya estaban descargados.
- **Salvaguardas:**
  - Si un PDF no usa una fuente menor para las notas, todo queda en el cuerpo, igual que antes.
  - Si la separación falla, el documento se conserva con el texto crudo en lugar de perderse.

### Metadatos nuevos: `tipo_sentencia` y `caso_id`
- **Qué:** `tipo_sentencia` se toma del paréntesis que sigue a la fecha, por ejemplo «(Excepciones Preliminares, Fondo, Reparaciones y Costas)», y vale fondo, interpretación, excepciones preliminares, reparaciones, competencia u otra. `caso_id` agrupa las sentencias de un mismo caso a partir del título normalizado. La tabla de calidad ahora reporta el número de casos distintos y el porcentaje de palabras que hay en notas.
- **Por qué:** el artículo confundía «caso» y «sentencia»: hay 596 sentencias, pero un caso puede tener varias. Estos campos también sirven más adelante como filtros de búsqueda.
- **Limitación:** si el título varía entre sentencias del mismo caso, quedan como casos distintos.

---

## 2. Pipeline de preprocesamiento (punto 2)

### Puntos resolutivos y votos individuales como partes propias
- **Qué:** cada párrafo lleva ahora una columna `parte`, que vale `cuerpo`, `resolutivos` o `voto` (y `firmas`, sección 4.3). El título «PUNTOS RESOLUTIVOS» y los encabezados «VOTO CONCURRENTE / RAZONADO / DISIDENTE…» abren una parte nueva con su propia numeración. El caso «189. Por tanto,», que continúa la numeración del cuerpo, se asigna al cuerpo.
- **Por qué:** la reconstrucción de párrafos exige que la numeración sea consecutiva. Como los puntos resolutivos y los votos vuelven a empezar en 1, todo lo que venía después del último párrafo se pegaba a él. En las salidas había texto de un voto citado como «Puntos resolutivos, párr. 426» (caso Perozo). En un sistema jurídico eso significa atribuir a la Corte la opinión de un juez.
- **Límites:**
  - El cambio de parte solo se activa después del primer párrafo numerado, porque el índice de la portada también lista «PUNTOS RESOLUTIVOS».
  - Las sentencias antiguas que no tienen ese título siguen como antes.

### Regex de párrafos y notas hasta 4 dígitos
- **Qué:** `RE_NUM_PARR`, `RE_NUM_SOLO` y las regex de marcadores pasan de `\d{1,3}` a `\d{1,4}`. El marcador después de puntuación ahora acepta una coma u otro signo a continuación, como en `EXPRESIÓN)77,`.
- **Por qué:** las sentencias más largas superan los 999 párrafos o las 999 notas, y en un título de sección había quedado un marcador sin quitar.

### Una sola normalización para párrafos, chunks y consultas
- **Qué:** `normalizar_lote` y `normalizar` aplican el mismo proceso a todo. Además:
  - **Artículos:** «artículo 8.1» y «artículos 25 y 63.1» pasan a `art_8_1`, `art_25` y `art_63_1`, y se conservan.
  - **Categoría gramatical:** se descartan pronombres, determinantes, preposiciones, conjunciones y verbos auxiliares.
  - **Términos de `CONSERVAR`:** las negaciones, «estado», «parte» y «final» se conservan aunque sean cortos o estén en la lista de stopwords.
- **Por qué:**
  - El filtro alfabético borraba los números de artículo, que son de los términos más discriminativos del dominio.
  - El pronombre «él» aparecía como lema en todas las sentencias.
  - Sobre todo, la consulta TF-IDF no se normalizaba: ver el punto 3.
- **Comprobado al probar:** la hipótesis de que el lematizador convierte «Estado» en «estar» resultó falsa. Solo «ha estado» se convierte en «estar», y eso es correcto, así que no se cambió. Lo que sí se observó es que `es_core_news_sm` no lematiza palabras en MAYÚSCULAS y deja «derechos humanos» en plural. Eso queda para comparar con otros modelos en la evaluación.

### Verificaciones nuevas
- **Qué:**
  - **Marcadores residuales:** se cuentan con un patrón más amplio que el de la limpieza, y se muestran ejemplos.
  - **Partes:** cuántas sentencias tienen puntos resolutivos o votos detectados, y los percentiles de longitud de los párrafos del cuerpo.
  - **Notas:** el porcentaje de palabras que hay en notas al pie.
  - **Lemas:** qué sentencias no tienen los lemas «corte», «caso», «estado», «convención» o «sentencia».
  - **Celda nueva:** muestra las líneas candidatas a título en las sentencias sin secciones detectadas.
  - **Revisión manual:** una muestra aleatoria de 20 párrafos se guarda en `muestra_revision_manual.csv`.
  - **Validación de la numeración:** ahora considera solo el cuerpo.
- **Por qué:** la verificación anterior («1 palabra con número pegado») usaba la misma regex que la limpieza, así que no podía detectar lo que esa regex no veía. Además, el artículo afirmaba que había 30 lemas presentes en todas las sentencias, cuando el notebook mostraba 4, y no se había investigado.

### Otros cambios
- **Ejemplo «antes → después»:** ahora usa un párrafo real del cuerpo. Antes mostraba un trozo del índice como «texto limpio».
- **Secciones:** `seccion_canonica` se guarda en `parrafos.parquet`, y los votos aparecen como «Votos individuales».
- **Archivos de salida:** los parquet de salida incluyen `caso_id`, `tipo_sentencia`, `parte` y `texto_notas`.

---

## 3. Chunks y recuperación (punto 3)

### Portada, índice, votos y firmas fuera del índice
- **Qué:** se filtran `es_portada` y las partes `voto` y `firmas` (sección 4.3) antes de armar los chunks.
- **Por qué:** el artículo decía que la portada y el índice se excluían, pero el código no lo hacía. Los votos no expresan la decisión de la Corte.

### Chunks lematizados de forma consistente
- **Qué:** los trozos de párrafos largos se normalizan con la misma función que los demás chunks. Antes se guardaban con `subchunk.lower()`.
- **Por qué:** el vocabulario TF-IDF terminaba lleno de cifras y stopwords (`'0 de'`, `'0 del'`…), y una parte del índice léxico usaba texto sin procesar.

### Consulta TF-IDF normalizada
- **Qué:** `buscar_tfidf` aplica `normalizar(consulta)` antes de `transform`.
- **Por qué:** la consulta cruda no coincidía con los lemas: «periodistas» no coincidía con «periodista», y las palabras con mayúscula no coincidían con nada. TF-IDF terminaba emparejando por «de» e «y». Por eso la comparación TF-IDF vs. embeddings del artículo no es válida y hay que repetirla.

### Cabecera y `chunk_id`
- **Qué:**
  - La cabecera ya no dice «Caso caso…».
  - Los puntos resolutivos se citan como «puntos 1–2».
  - Los chunks sin número de párrafo ya no muestran «párrs. None–None».
  - Un chunk nunca mezcla secciones ni partes.
  - `chunk_id` se numera por documento.
- **Por qué:** eran errores de cita visibles. Además, el `chunk_id` global cambiaba si se modificaba cualquier sentencia anterior.
- **Reescritura:** `construir_chunks` se reescribió más compacto, sin cambiar las reglas de agrupación: hasta 250 palabras por sección, y los párrafos largos divididos por oraciones con 40 palabras de solape.

---

## 4. Validación con sentencias reales y cambios adicionales

### Qué se ejecutó
Las funciones de los puntos 1 y 2 del notebook (extracción, separación de notas, metadatos, limpieza y segmentación) se corrieron sobre 10 sentencias de 2025 descargadas localmente: 5 de excepciones preliminares (10–12 páginas) y 5 de fondo (106–136 páginas).

| Comprobación | Resultado |
|---|---|
| Palabras en notas al pie | 14–35 % por sentencia; no se encontró texto del cuerpo enviado a notas |
| Numeración de párrafos del cuerpo | completa en las 10 (0 faltantes; hasta el párrafo 318) |
| Puntos resolutivos detectados | 10/10 |
| Votos individuales detectados | todos los anunciados (2–5 por sentencia de fondo, incluido uno en portugués) |
| Bloque de firmas separado | 10/10 (tras el cambio 4.3) |
| Marcadores de nota residuales | 1 en total |
| Longitud de párrafos del cuerpo (p50 / p90 / p99) | 94 / 173 / 276 palabras |

Las notas al final de los votos, numeradas en romanos (Cuadra Bravo, págs. 118–122), también quedan en notas.

### 4.1 Rótulos «A.1.» conservados
- **Qué:** la regex de marcadores después de puntuación (`RE_MARCA_TRAS_PUNTO`) ya no acepta un punto a continuación del número.
- **Por qué:** al ampliarla en la fase 2 empezó a borrar el dígito de rótulos de sección como «D.1.», «E.3.» o «B.2.1.», que pasaban a «D..». Era una regresión introducida por la corrección anterior. Se sigue quitando «Corte.15 dijo» y «EXPRESIÓN)77,».

### 4.2 Portada e índice: todo lo anterior al párrafo 1
- **Qué:** `es_portada` se calcula con la nueva función `marcar_portada`: marca todo lo que está antes del primer párrafo 1 del cuerpo. Si una sentencia no tiene numeración detectada, se usa el criterio anterior (sección «ENCABEZADO»).
- **Por qué:** el índice de la portada contiene líneas con forma de título («A. Alegatos de las partes…»), así que el índice quedaba asignado a esas secciones y no a «ENCABEZADO». Por eso el filtro de portada no lo excluía, y entraba al índice de búsqueda. En las sentencias de fondo se marcaban 2–3 párrafos como portada; ahora se marcan 5, con el índice incluido.

### 4.3 Bloque de firmas como parte propia
- **Qué:** la nueva parte `firmas` empieza en la línea «Redactada en español…» (o «Hecha/Dada en…») o, si no la hay, en la referencia «Corte IDH. Caso … Sentencia de …» que la sustituye. Solo se busca después de los puntos resolutivos, porque en el cuerpo y en los votos esas líneas pueden ser citas. Se excluye del índice igual que los votos, y `seccion_canonica` la etiqueta «Firmas».
- **Por qué:** los nombres de los jueces y la fórmula «Comuníquese y ejecútese» quedaban pegados al último punto resolutivo (60–90 palabras por sentencia). Ese chunk se recuperaría con consultas sobre jueces que no tienen que ver con la decisión.

### Pruebas añadidas
`pruebas_notebook.py` comprueba ahora que el bloque de firmas se separa y no queda en los resolutivos, que la portada termina antes del párrafo 1 y que «A.1.» y «D.1.1.» se conservan.

---

## 5. Ejecución local del notebook

### Cómo se ejecutó
- **Datos:** los PDF en `casos/`, dentro de la carpeta del proyecto, con `CORTEIDH_BASE` apuntando a esa carpeta. Las salidas regenerables (`corpus/`, `procesado/`) y los PDF quedan fuera de git (`.gitignore`).
- **Entorno:** Python 3.11 con spaCy 3.8, PyTorch 2.11 con CUDA y una GPU RTX 4070 para los embeddings. La ejecución completa tarda unos 8 minutos con 199 sentencias y unos 19 minutos con las 597.
- **Salidas:** se quitaron las barras de progreso y los avisos de pip, que solo eran ruido.

### 5.1 Sin scraping fuera de Colab
- **Qué:** `DESCARGAR = EN_COLAB`.
- **Por qué:** con `True`, ejecutar el notebook en local habría vuelto a descargar todo el sitio de la Corte. Fuera de Colab se usan los PDF que ya están en `CASOS_DIR`.

### 5.2 Título de puntos resolutivos unido a la línea siguiente
- **Qué:** la parte `resolutivos` se activa con cualquier línea en mayúsculas que **empiece** por «[IX.] PUNTOS RESOLUTIVOS». Antes la línea tenía que ser exactamente ese título.
- **Por qué:** la unión de títulos de varias líneas producía «IX. PUNTOS RESOLUTIVOS LA CORTE DECLARA,» o «V. PUNTOS RESOLUTIVOS POR TANTO, LA CORTE», y 5 sentencias quedaban sin resolutivos. Ahora se detectan en 198 de 199. La que faltaba es una resolución de supervisión de cumplimiento, que se resolvió con el cambio 6.2.

### 5.3 Asterisco en títulos y Estados
- **Qué:** `extraer_metadata` quita el asterisco de llamada de nota del título.
- **Por qué:** «caso moya chacón y otro vs. costa rica*» dejaba «costa rica*» como Estado, y eso rompe los filtros por país. Ocurría en 6 títulos y 4 Estados.

Los resultados de esa primera ejecución (199 sentencias) quedaron reemplazados por los del corpus completo, en la sección 6.

---

## 6. Corpus completo: descarga desde cero y formatos antiguos

### Cómo se descargó
- **Scraper:** se ejecutó el del notebook (celdas de configuración y de funciones) fuera de Jupyter, con `REFRESCAR_URLS = True` y la carpeta `casos/` vacía. La copia parcial anterior se guardó aparte.
- **Lista de casos:** el buscador devolvió 597 casos en los 7 rangos de fechas. Ningún rango llegó al tope de unos 200 resultados, así que no se perdió ninguno. La lista queda en `corpus/casos_buscador.parquet`.
- **Descarga:** tardó 82 minutos (unos 8 s por caso). Falló un solo caso («no se encontró la sentencia en el menú Descargar»), y se descargó bien al reintentar.
- **Resultado:** 597 sentencias y 290 resúmenes. Dos sentencias del caso Maya Kaqchikel de Sumpango tienen texto idéntico y se conserva una, así que quedan 596 en el corpus.

### 6.1 Sentencias en inglés marcadas como «Español»
- **Qué:** el scraper prueba todas las versiones de la sentencia marcadas «Español» y descarta las que están en inglés («INTER-AMERICAN COURT» en la primera página). `detectar_idioma` reconoce ahora también el inglés, y la tabla de calidad cuenta los documentos descartados por idioma.
- **Por qué:** en el caso Girón y otro vs. Guatemala, el sitio ofrece dos PDF marcados «Español», y el primero es la traducción al inglés. Se indexaba un texto en inglés como si fuera español, sin título, fecha ni Estado. Además, la fila «sentencias en portugués» se calculaba después de filtrar por español, así que siempre daba 0.

### 6.2 Parte dispositiva sin el título «PUNTOS RESOLUTIVOS»
- **Qué:** la parte `resolutivos` también se abre con una línea sola en mayúsculas como «LA CORTE,», «DECIDE:», «RESUELVE:», «POR TANTO:» u «OPERATIVE PARAGRAPHS». El bloque de firmas acepta además «Redactada en castellano».
- **Por qué:** muchas sentencias antiguas no tienen el título «PUNTOS RESOLUTIVOS». Su parte dispositiva quedaba pegada al último párrafo del cuerpo, en 75 de las 596 sentencias; su mediana es de 1998 y solo 9 son posteriores a 2005. Ahora quedan 6.

### 6.3 El índice abría la parte resolutivos
- **Qué:** las líneas del índice (con puntos guía: «XI. PUNTOS RESOLUTIVOS ........ 85») no abren partes ni cuentan como párrafos numerados. Si aparece «PUNTOS RESOLUTIVOS» y luego el título «I. ...» sin ningún punto resolutivo numerado entre ambos, era el índice y se vuelve al cuerpo.
- **Por qué:** este error ya estaba en la versión anterior. En las sentencias con índice, una entrada numerada («1. Admisión de la prueba ..... 8») contaba como primer párrafo, y la entrada «PUNTOS RESOLUTIVOS» del índice abría la parte resolutivos. Entonces la sentencia entera quedaba en esa parte: en 15 sentencias, más del 30 % del texto, y en algunas el 97 %. Ahora queda 1, que se explica en las limitaciones.

### 6.4 Metadatos con formatos antiguos
- **Fechas:** se aceptan fechas sin «de» («19 de noviembre 1999», «6 mayo de 2008», «21 NOVIEMBRE DE 2018») y documentos que dicen «Sentencia del …» o «Resolución de la Corte …».
- **Títulos:** si el encabezado no trae «CASO» («VICKY HERNÁNDEZ Y OTRAS VS. HONDURAS»), el título se toma entre «DERECHOS HUMANOS» y la fecha. Se descartan los candidatos que contienen «la Corte Interamericana», que son del primer párrafo («En el caso X, la Corte…»).
- **Título y Estado:** terminan en el país. Antes, «caso x vs. perú (interpretación de la sentencia …)» dejaba la descripción dentro del Estado. Así las sentencias de interpretación se agrupan con su caso.
- **Estados:** se quitan las llamadas de nota pegadas («colombia1», «guatemala∗») y se unifican nombres oficiales: «estados unidos mexicanos» → «méxico», «suriname» → «surinam», «estado plurinacional de bolivia» → «bolivia» y «república federativa del brasil» → «brasil».
- **Por qué:** con el corpus completo, 12 sentencias quedaban sin título, 25 sin fecha, 27 sin tipo y 16 sin Estado. Además, varios Estados traían texto pegado, como «venezuela, la corte interamericana…». Ahora queda 1 sin título, Estado ni fecha, cuyo PDF no tiene la primera página. Los Estados distintos son 22, todos nombres de país.

### Pruebas añadidas
`pruebas_notebook.py` tiene ahora 50 comprobaciones. Las nuevas cubren:
- la parte dispositiva antigua y las firmas «en castellano»;
- el índice con y sin puntos guía;
- seis encabezados reales de formatos antiguos (fecha, título y Estado);
- el idioma inglés.

Las de la parte dispositiva y el índice fallan con la versión anterior del notebook.

### Resultados (corpus completo: 596 sentencias, 1987–2026)

| Indicador | Valor |
|---|---|
| Documentos (sentencias + resúmenes) | 886 (596 + 290) |
| Casos distintos | 437 |
| Tipos de sentencia | 394 fondo, 109 interpretación, 41 excepciones preliminares, 24 otras, 23 reparaciones, 3 competencia, 2 sin tipo |
| Sentencias sin título / Estado / fecha | 1 / 1 / 1 |
| Palabras de las sentencias en notas al pie | 27,5 % |
| Numeración de párrafos del cuerpo | cobertura completa en 560 de 596; mediana 100 %, mínimo 84 % |
| Sentencias con puntos resolutivos detectados | 590 de 596 |
| Sentencias con votos individuales separados | 279 |
| Palabras de las sentencias por parte | cuerpo 80,3 %, votos 16,4 %, resolutivos 2,4 %, firmas 0,8 % |
| Párrafos totales / que entran al RAG | 146.627 / 114.795 |
| Chunks | 79.799 (mediana 195 palabras, máximo 290) |
| Vocabulario BoW / TF-IDF (1–2-gramas) | 50.592 / 591.549 |
| Smoke test denso (5 consultas): Recall@1 / @5 / @10, MRR@10 | 0,40 / 0,80 / 0,80 / 0,55 |

**Observaciones:**
- **Votos individuales:** son el 16 % del texto de las sentencias. En la muestra 2020–2026 eran el 27 %, porque los votos de esos años son más extensos. Antes de separarlos, ese volumen se citaba como si fuera la decisión de la Corte.
- **TF-IDF:** con la consulta normalizada, para «libertad de expresión y periodistas» recupera casos pertinentes, como Palacio Urrutia, Carvajal Carvajal, Fontevecchia y D'Amico, y Moya Chacón. Los embeddings recuperan Granier (RCTV), Fontevecchia, Tristán Donoso y Moya Chacón.
- **Smoke test:** la consulta 5 («El artículo 67 de la Convención establece que…») no recupera su documento en el top 10. Ese texto se repite en las 109 sentencias de interpretación, así que no identifica un documento. El smoke test no sirve como evaluación, y por eso la evaluación con consultas juzgadas sigue pendiente.

**Limitaciones observadas:**
- **Parte dispositiva en minúsculas:** 4 sentencias de interpretación de 2008–2009 (García Prieto, Chaparro Álvarez, Ticona Estrada y Valle Jaramillo) y Saramaka (2007) la tienen dentro del último párrafo numerado («214. Por tanto, La Corte Declara, …»). El texto sigue en el índice, pero etiquetado como cuerpo. La sexta sin resolutivos es Loayza Tamayo (fondo, 1997).
- **Cita de un «RESUELVE:»:** en Cayara (excepciones preliminares, 1993), el cuerpo cita un informe de la Comisión con «RESUELVE:» en una línea sola, y desde ahí todo queda en resolutivos.
- **Firmas sin «Redactada en»:** en 65 sentencias no hay frase de cierre reconocible antes de las firmas, y los nombres de los jueces quedan pegados al último punto resolutivo.
- **Lematización:** `es_core_news_sm` produce lemas inexistentes, como «abandonarar» o «abarcarir». Queda para comparar modelos en la evaluación.
- **Anexos después de las firmas:** en algunas sentencias, las tablas de anexos que siguen a las firmas (listas de víctimas y montos) quedan en la parte `firmas` y fuera del índice.
- **Marcadores residuales:** el contador amplio marca 1.158 casos, pero la muestra son sobre todo falsos positivos (horas como «14h47», números citados entre comillas).
- **Secciones:** 43 sentencias tienen más del 20 % de sus párrafos sin sección. Son sobre todo antiguas (mediana de 1995), cuyos títulos no siguen el patrón «I. TÍTULO EN MAYÚSCULAS». Sigue pendiente (fase 3).

La celda de texto 25 (estadísticos de longitud) se actualizó con las cifras del corpus completo. La 20 sigue siendo válida.

---

## Cómo volver a ejecutar

0. **En local:** definir `CORTEIDH_BASE` con la ruta del proyecto. Si `casos/` está vacía, poner `DESCARGAR = True` en la celda de configuración para descargar los PDF con el scraper (requiere `playwright install chromium`, unos 80 minutos), y luego ejecutar todo. En Colab no hace falta cambiar nada.
1. **Punto 1:** reconstruir el corpus desde la celda de construcción. No vuelve a descargar los PDF, pero tarda más porque lee el tamaño de fuente de cada renglón.
2. **Puntos 2 y 3:** ejecutarlos en la misma sesión. El punto 3 usa la normalización del punto 2 y lo avisa con un `assert` si falta.
3. **Verificaciones:** revisar las salidas nuevas, sobre todo cuántas sentencias tienen puntos resolutivos detectados y el porcentaje de palabras en notas.
4. **Artículo:** actualizar todas las cifras del artículo con esta ejecución.

## Pendiente (fases 3 a 6)
- Truncamiento de los embeddings a 256 tokens, BM25 y búsqueda híbrida.
- Evaluación con consultas juzgadas y un smoke test con una muestra aleatoria.
- Corregir la detección de secciones en las 43 sentencias que fallan (sobre todo antiguas) y completar los metadatos desde el buscador.
- Actualizar el artículo: definición de RAG, cifras, figuras y referencias.

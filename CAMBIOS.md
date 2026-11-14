# Cambios al notebook: fases 1 a 5 de la revisión

Versión entregada: commit `9dd6cc8` (rama `main`).
Versión corregida: rama `correcciones-fase-1-2` (commit `2c4c516` y siguientes).

El notebook se ejecutó **completo, de principio a fin, en local y con el corpus completo**: las 597 sentencias y los 290 resúmenes, descargados desde cero con el scraper del propio notebook (sección 6). Todas las salidas corresponden a esa ejecución.

Las funciones nuevas también se probaron con datos sintéticos (`pruebas_notebook.py`, 67 comprobaciones). La fase 3 (características y recuperación) está en la sección 8, la fase 4 (evaluación) en la sección 9 y la fase 5 (análisis exploratorio con contenido) en la sección 10. Las fases 1 y 2 se validaron en tres etapas, y de cada una salieron cambios adicionales:
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
  - Las sentencias antiguas que no tienen ese título siguen como antes. Se resolvió después, en el cambio 6.2.

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

## 7. Artículo actualizado

`articulo/Articulo_actualizado.docx`, más su vista `articulo/Articulo_actualizado.pdf`, es el artículo con las cifras de la ejecución completa (sección 6). Además, se reescribieron las afirmaciones que las correcciones dejaron obsoletas. `articulo/Articulo.pdf` queda como la versión entregada. El .docx se generó desde cero, porque solo existía el PDF exportado de Google Docs, y mantiene la estructura, la portada y el formato (Times New Roman 12, A4). Se puede subir a Google Docs para seguir editándolo.

### Qué cambió
- **Cifras:** todas se tomaron de la ejecución completa: corpus, descriptivos (Tabla 2), diagnóstico, secciones, párrafos, efecto del preprocesamiento (Tabla 3), chunks, TF-IDF, consultas y prueba de humo. El artículo entregado mezclaba cifras de dos ejecuciones: 596 sentencias en el resumen, pero «1 de las 199 sentencias» en la sección 3.4 y «200 casos posteriores a 2020» en las limitaciones.
- **Figuras:** se regeneraron con la ejecución nueva y se numeraron en orden de aparición. Se agregó la de sentencias por año (Figura 2), ahora que el corpus va de 1987 a 2026.
- **Afirmaciones corregidas:**
  - Las notas al pie ya se separan por tamaño de fuente; la limitación decía que quedaban dentro de los párrafos.
  - Los votos individuales dentro de la sentencia se separan y quedan fuera del índice; antes se decía solo que «se excluyen».
  - La inconsistencia de los chunks de párrafos largos ya está corregida.
  - La comparación TF-IDF vs. embeddings se reescribió: con la consulta normalizada, TF-IDF ya recupera apartados de libertad de expresión.
  - La prueba de humo se reinterpretó: la consulta que falla repite el artículo 67, que aparece en las 109 sentencias de interpretación.
  - El scraper reinicia el navegador; no recarga la página.
- **Contenido nuevo:**
  - la distinción entre sentencia y caso (437 casos) y los tipos de sentencia;
  - las partes de la sentencia en el pipeline;
  - los formatos antiguos, en el diagnóstico y como limitación;
  - la separación de notas en la extracción;
  - la sección 6 «Trabajo siguiente», que el texto citaba y no existía;
  - la lista de referencias, que faltaba. Se agregó Robertson y Zaragoza (2009) por la mención de BM25.
- **Tabla 3:** la reducción de texto en la limpieza de las sentencias pasa de «menos de 1 %» a cerca del 25 %. Casi todo son las notas al pie, que se guardan aparte y no se pierden.

### Pendiente de revisar por el grupo
- **Portada:** conserva la fecha «04 de octubre de 2026» de la entrega original.
- **Referencias:** conviene verificarlas en sus fuentes antes de entregar.

---

## 8. Fase 3: características y recuperación (punto 3)

El notebook se ejecutó completo otra vez, de principio a fin, con el corpus completo: 23 minutos en una RTX 4070. Las salidas corresponden a esa ejecución. `pruebas_notebook.py` tiene ahora 59 comprobaciones.

### 8.1 Ventana del modelo de embeddings: de 256 a 512 tokens
`max_seq_length` estaba en 256, con el comentario «baja a 256 si tus chunks son cortos», y los chunks no lo son. Una celda nueva mide cuántos tokens tiene cada chunk con el tokenizador de e5:
- mediana de 318 tokens, p99 de 449 y máximo de 750, con unos 1,6 tokens por palabra;
- con 256 tokens se truncaba el **73,6 %** de los chunks: el modelo no veía el final del texto, y en los chunks de 250 palabras perdía cerca de un tercio;
- con 512 (el máximo de e5) se trunca el **0,1 %**.

El `batch_size` baja de 256 a 128 para que quepa en 12 GB. Calcular los embeddings de los 79.799 chunks tarda unos 150 s.

### 8.2 TF-IDF ajustado y BM25
- **TF-IDF:** `min_df=3` y `max_df=0.5`. Las características bajan de 591.549 a 348.689. Se descartan bigramas que aparecen en uno o dos chunks (nombres propios, errores de OCR) y términos que aparecen en más de la mitad de los chunks, que no discriminan.
- **BM25 (`rank_bm25.BM25Okapi`, k1 = 1,5, b = 0,75):** la librería estaba instalada e importada pero no se usaba. Es la línea base léxica estándar, porque satura la frecuencia del término y normaliza por la longitud del chunk. Usa los mismos lemas que TF-IDF.

### 8.3 Búsqueda híbrida, filtros y diversificación
La búsqueda queda en una sola función, `buscar(consulta, metodo, k, diversificado, **filtros)`. `buscar_tfidf` y `buscar_denso` se mantienen como atajos.
- **Métodos:** `tfidf`, `bm25`, `denso` e `hibrido`. El híbrido fusiona BM25 y denso con Reciprocal Rank Fusion (k = 60), sobre 100 candidatos de cada uno. RRF usa solo las posiciones, así que no hay que calibrar puntajes de escalas distintas.
- **Filtros:** `estado`, `anio_min`, `anio_max`, `tipo_sentencia`, `articulo` (artículo de la Convención declarado violado) y `seccion` (sección canónica). Restringen el universo antes de ordenar, en los cuatro métodos. En la búsqueda densa el filtro se aplica dentro de FAISS (`IDSelectorBatch`), así que la búsqueda sigue siendo exacta, y no un top-k filtrado después.
- **Diversificación:** por defecto se devuelve un resultado por caso y se descartan los casi duplicados de un resultado ya elegido. Sin esto, en la consulta de prueba TF-IDF y BM25 devuelven dos chunks de Carvajal Carvajal entre los cinco primeros.

### 8.4 Características de dominio
Se añadieron dos columnas a los chunks:
- **`articulos_violados`:** los artículos de la Convención Americana que la sentencia declara violados en sus puntos resolutivos. La regex busca puntos con «violó / ha violado / violación / incumplimiento» que no estén negados («no es responsable por la violación…»), y toma las listas de artículos cuyo tratado es la Convención Americana («del mismo instrumento», «de la Convención»…). Excluye otros tratados (Belém do Pará, la Convención contra la Tortura) y los artículos 1.1 y 2, que acompañan casi todas las violaciones.
  - Cubre **373 de las 394 sentencias de fondo**. De las 21 restantes, 11 no declaran ninguna violación (Rico, Galdeano Ibáñez, Fairén Garbi…). Las otras son sentencias antiguas cuya parte dispositiva no se separó completa (Cantos, El Amparo, Loayza Tamayo…) o que remiten a un reconocimiento de responsabilidad (Carpio Nicolle).
- **`seccion_canonica`:** la sección normalizada del punto 2, heredada por cada chunk (un chunk no mezcla secciones).

Una celda de análisis de contenido (figura 10, `fig10_articulos_violados.png`) muestra:
- el porcentaje de sentencias de fondo que declara violado cada artículo: el 8 (garantías judiciales) en el 85 %, el 25 (protección judicial) en el 74 %, el 5 (integridad personal) en el 63 %, el 4 (vida) en el 43 % y el 7 (libertad personal) en el 41 %;
- el mismo porcentaje para los 10 Estados con más sentencias. Por ejemplo, el artículo 4 aparece en el 86 % de las sentencias de Colombia y en el 23 % de las de Argentina.

### 8.5 Casi duplicados entre casos
La Corte repite párrafos casi literales de su jurisprudencia, como los de costas y gastos, plazo razonable o el artículo 63.1. Se calcularon los 5 vecinos más cercanos de cada chunk con FAISS (24 s). Se marcan las columnas `casi_duplicado_de` y `n_casi_duplicados` cuando un vecino de **otro caso** tiene coseno ≥ 0,97.
- **El umbral:** e5 comprime las similitudes hacia arriba, y el 0,95 del plan marcaba 8.074 chunks, muchos de ellos paráfrasis con contenido propio. Con 0,97 son **2.274 (2,8 %)**, concentrados en Competencia (20 %), Sin sección (16 %) y Reparaciones (5 %).
- **Uso:** no se eliminan del índice, porque cada uno pertenece a su caso. Se usan en la diversificación.

### 8.6 Smoke test con 100 chunks al azar
Antes eran los 5 primeros chunks, todos del mismo documento, con las 25 primeras palabras como consulta. Ahora son 100 chunks del cuerpo elegidos al azar (semilla 42), con 25 palabras seguidas desde un punto al azar. Cuenta como acierto cualquier chunk del mismo documento que comparta párrafo, porque los trozos de un párrafo largo se solapan.

| método | R@1 | R@5 | R@10 | MRR@10 |
|---|---|---|---|---|
| TF-IDF | 0,86 | 0,97 | 0,99 | 0,91 |
| BM25 | 0,85 | 0,94 | 0,99 | 0,89 |
| denso | 0,36 | 0,54 | 0,61 | 0,45 |
| híbrido | 0,61 | 0,73 | 0,85 | 0,68 |

**Cómo leerlo:** es una prueba de cordura, no una evaluación. La consulta copia el texto del chunk, así que favorece a los métodos léxicos. El denso no está hecho para recuperar un fragmento literal entre 80 mil chunks parecidos, y arrastra al híbrido. Qué método es mejor para preguntas reales lo decide la evaluación con consultas juzgadas de la fase 4. En las consultas temáticas de prueba, el híbrido diversificado da los resultados más pertinentes: Fontevecchia, Herrera Ulloa y Tristán Donoso para «libertad de expresión y periodistas».

### 8.7 Sección canónica: «Sin sección» separada de la portada
En las sentencias antiguas sin títulos, los párrafos anteriores al primer título quedaban en la sección ENCABEZADO, y `seccion_canonica` los etiquetaba como «Portada e índice» aunque no lo fueran: 2.988 párrafos de cuerpo, que sí están en el índice. Ahora la portada se toma de `es_portada` y el resto queda como **«Sin sección»**. En la figura 9, «Portada e índice» baja a 1,1 % de las palabras y aparece «Sin sección» con 2,1 %.

### Artefactos guardados
`chunks.parquet` incluye las columnas nuevas (`articulos_violados`, `seccion_canonica`, `casi_duplicado_de`, `n_casi_duplicados`). Los embeddings y el índice FAISS son los de 512 tokens. BM25 no se guarda porque se reconstruye en segundos desde `texto_normalizado`.

### Afecta al artículo
Las secciones de representación y recuperación del artículo actualizado (sección 7) usan las cifras anteriores: 256 tokens, 591.549 características TF-IDF y la prueba de humo con 5 consultas. La figura 9 también cambia. Queda para la actualización del artículo en la fase 5.

---

## 9. Fase 4: evaluación con consultas juzgadas (punto 4)

El notebook se ejecutó completo otra vez, ya con el conjunto C: 100 minutos, de los cuales 52 son las ablaciones (re-calculan embeddings de cuatro variantes del índice; con la GPU libre son unos 25). `pruebas_notebook.py` tiene ahora 67 comprobaciones (nDCG, extracción de consultas de los resúmenes, colapso de chunks a documentos, paso de párrafos citados a chunks).

### 9.1 Dos conjuntos de evaluación
- **A) Resúmenes oficiales, relevancia por documento (290 consultas).** Cada resumen oficial corresponde a una sentencia. Se toma una oración al azar del resumen (semilla 42, de 15 a 45 palabras, 28,7 en promedio) como consulta, y su sentencia es el único documento relevante. Se descartan las oraciones que nombran a las víctimas o al caso y las de trámite («la Sentencia fue notificada…»), para que la consulta no se resuelva por el nombre propio. Los rankings de chunks se colapsan a documentos en orden de aparición.
- **B) 20 consultas temáticas propias, relevancia por chunk de 0 a 2** (`evaluacion/consultas_propias.csv` y `evaluacion/qrels_consultas_propias.csv`). Ejemplos: «plazo razonable», «control de convencionalidad», «daño al proyecto de vida». Se juzgó el top 10 de los cinco sistemas (TF-IDF, BM25, denso, híbrido e híbrido diversificado): 486 pares, con 241 de relevancia 2, 195 de relevancia 1 y 50 de relevancia 0. **Los juicios los hizo Claude (un modelo de lenguaje), no un experto:** el grupo debe revisarlos, sobre todo los de relevancia 1. El CSV incluye el título, la sección y el inicio de cada chunk para revisarlos sin abrir el notebook.
- **C) Cuadernillos de Jurisprudencia, relevancia por párrafo (182 consultas, juicios de experto).** Se agregó después; ver 9.5.

### 9.2 Métricas
R@1, R@5, R@10, MRR@10 y nDCG@10 (ganancia lineal 0/1/2). En B también P@10 (fracción del top 10 con relevancia ≥ 1), el número de casos distintos en el top 10 y la fracción sin juzgar, que es 0. Los intervalos son del 95 % por bootstrap sobre las consultas (1000 remuestreos). En las ablaciones la diferencia es pareada: misma consulta, variante menos principal.

### 9.3 Resultados

**A) Resúmenes oficiales (por documento):**

| método | R@1 | R@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|
| TF-IDF | 0,74 | 0,92 | 0,80 | 0,83 [0,79–0,87] |
| BM25 | 0,74 | 0,92 | 0,81 | **0,84** [0,80–0,87] |
| denso | 0,46 | 0,67 | 0,52 | 0,56 [0,51–0,61] |
| híbrido | 0,59 | 0,86 | 0,67 | 0,72 [0,68–0,76] |

**B) Consultas propias (por chunk, juicios 0–2):**

| método | nDCG@10 | P@10 | MRR@10 | casos distintos en el top 10 |
|---|---|---|---|---|
| TF-IDF | 0,66 [0,59–0,73] | 0,90 | 0,94 | 7,0 |
| BM25 | 0,76 [0,69–0,82] | 0,93 | 0,98 | 7,0 |
| denso | 0,86 [0,81–0,90] | 0,95 | 0,98 | 6,8 |
| híbrido | **0,86** [0,81–0,91] | 0,96 | 1,00 | 7,6 |
| híbrido diversificado | 0,81 [0,72–0,89] | 0,90 | 1,00 | 10,0 |

Los resultados del conjunto C están en 9.5.

Figura 11 (`fig11_evaluacion_metodos.png`): nDCG@10 con sus intervalos en los tres conjuntos (en C, por párrafo).

**Cómo leerlo:** los dos conjuntos miden cosas distintas y ordenan los métodos al revés.
- En A la consulta describe hechos concretos de un caso (lugares, instituciones, fechas) con vocabulario que la sentencia repite, así que gana lo léxico; es una búsqueda de un documento conocido.
- En B la consulta es un tema jurídico que se expresa con otras palabras en cada sentencia, y ganan el denso y el híbrido.
- **El híbrido es el método más robusto:** empata en el primer lugar en B y queda segundo en A, lejos del denso. Es el valor por defecto de `buscar()` y se mantiene.
- **Diversificar** cuesta 0,05 de nDCG@10 en B (los intervalos se solapan) y sube de 7,6 a 10 los casos distintos en el top 10. Para un RAG que debe mostrar la jurisprudencia de varios casos es un buen intercambio, y se mantiene por defecto. Para preguntas sobre un solo caso conviene `diversificado=False`.
- Con 20 consultas los intervalos de B son anchos: denso e híbrido no se distinguen.

### 9.4 Ablaciones (conjunto A, Δ nDCG@10 pareado contra la configuración principal)

| variante | BM25 | denso | híbrido |
|---|---|---|---|
| sin cabecera de contexto | — | −0,009 [−0,042, +0,026] | **+0,030 [+0,003, +0,058]** |
| ventana de 256 tokens | — | **−0,035 [−0,062, −0,007]** | −0,020 [−0,043, +0,002] |
| con notas al pie (26.665 chunks más) | +0,001 [−0,006, +0,010] | +0,005 [−0,004, +0,015] | −0,000 [−0,007, +0,007] |
| chunks de 150 palabras (144.833 chunks) | −0,001 [−0,025, +0,021] | +0,010 [−0,022, +0,039] | +0,023 [−0,001, +0,050] |

La configuración principal usa chunks de 250 palabras, cabecera, 512 tokens y notas fuera del índice. BM25 no usa la cabecera ni la ventana del modelo, así que esas filas no aplican. TF-IDF no se re-evalúa en las variantes (su resultado principal está en 9.3).
- **512 tokens se confirma:** con 256 el denso pierde 0,035, y la diferencia es significativa.
- **Notas al pie:** no cambian nada (±0,01). Se dejan fuera del índice, que así es un 33 % más pequeño.
- **Cabecera:** en A, quitarla mejora el híbrido en 0,03 (significativo por poco). Una explicación plausible: las consultas de A evitan a propósito el nombre del caso, que es lo que más aporta la cabecera, así que A no puede premiarla. **No se cambia todavía:** falta medirla en B, donde el título y la sección sí pueden ayudar, y con los juicios revisados por el grupo.
- **Chunks de 150 palabras:** +0,023 en el híbrido, en el límite (el intervalo toca el 0), con 1,8 veces más chunks. No es concluyente.

Estas dos decisiones pendientes se resuelven con el conjunto C (9.5).

### 9.5 Conjunto C: Cuadernillos de Jurisprudencia (juicios de experto por párrafo)
Los Cuadernillos de Jurisprudencia de la Corte ordenan por temas y subtemas los párrafos de sus sentencias que la propia Corte considera representativos. El grupo descargó cinco a mano (en `cuadernillos/`, fuera de git):
- Derechos humanos de las mujeres;
- Desaparición forzada;
- Personas privadas de libertad;
- Libertad de pensamiento y de expresión;
- Pueblos indígenas y tribales.

**Extracción** (`evaluacion/extraer_cuadernillos.py`, con PyMuPDF):
- **Consultas.** Cada subtema es una consulta, con la forma «Tema: Subtema». Ejemplo: «Desaparición forzada: Obligación de investigar».
- **Grado 2.** Los párrafos transcritos bajo cada cita («Caso … Sentencia de … Serie C No. N») tienen relevancia 2.
- **Grado 1.** Las referencias «En similar sentido: Caso …, párr. M» tienen relevancia 1.
- **Lo que se descarta.** Superíndices y notas (por tamaño de fuente), encabezados de página, Opiniones Consultivas y Resoluciones (no están en el corpus).
- **Emparejamiento.** El corpus no tiene el número de Serie C, así que cada cita se empareja con su sentencia por la fecha y la similitud del título del caso (Jaccard ≥ 0,34). Si en esa fecha hay una sola sentencia candidata, se acepta directamente: así entran los casos con iniciales.

**Resultado** (`evaluacion/consultas_cuadernillos.csv`, `evaluacion/qrels_cuadernillos.csv`):
- 2.642 citas, el 97,4 % emparejadas con una sentencia del corpus;
- 182 consultas (Mujeres 35, Desaparición forzada 38, Expresión 27, Personas privadas de libertad 32, Pueblos indígenas 49);
- 2.495 juicios (2.237 de grado 2 y 258 de grado 1) sobre 191 sentencias;
- el 99,3 % de los párrafos citados cae dentro de un chunk del cuerpo, y toda consulta tiene al menos un chunk relevante (mediana 7).

Un chunk hereda el grado máximo de los párrafos citados que contiene (`ganancia_cuadernillos`). Hay dos lecturas:
- **C párrafo:** el ranking de chunks contra esos juicios.
- **C documento:** colapsado a sentencias, como en A.

**Los juicios son incompletos.** Un cuadernillo cita algunos párrafos representativos, no todos los relevantes, así que muchos chunks pertinentes cuentan como no relevantes. Las cifras absolutas son cotas inferiores y solo sirven para comparar métodos entre sí. A cambio, son juicios de la Corte y no de un modelo de lenguaje, y la cobertura temática es mucho mayor que en B.

**Resultados:**

| método | C párrafo: R@10 | C párrafo: nDCG@10 | C documento: R@10 | C documento: nDCG@10 |
|---|---|---|---|---|
| TF-IDF | 0,23 | 0,061 [0,04–0,08] | 0,67 | 0,30 [0,26–0,34] |
| BM25 | 0,31 | 0,079 [0,06–0,10] | 0,67 | 0,32 [0,28–0,37] |
| denso | **0,44** | **0,119** [0,09–0,15] | **0,80** | **0,37** [0,32–0,41] |
| híbrido | 0,36 | 0,113 [0,09–0,14] | 0,72 | 0,36 [0,31–0,40] |
| híbrido diversificado | 0,32 | 0,088 [0,06–0,11] | — | — |

- **C confirma a B con juicios independientes:** en consultas temáticas, el denso y el híbrido superan a TF-IDF y BM25, y no se distinguen entre sí. Con A el orden es el contrario, por las razones de 9.3. El híbrido sigue siendo la opción más robusta entre los tres conjuntos.
- **Diversificar** cuesta 0,025 de nDCG@10 por párrafo, un efecto parecido al de B. Es esperable: los cuadernillos citan varios párrafos de una misma sentencia, que la diversificación deja fuera.

**Ablaciones en C** (Δ nDCG@10 pareado contra la configuración principal; A se repite para comparar):

| variante | método | A | C párrafo | C documento |
|---|---|---|---|---|
| sin cabecera | denso | −0,009 | **−0,027 [−0,044, −0,011]** | **−0,054 [−0,083, −0,024]** |
| sin cabecera | híbrido | **+0,030** | −0,004 | −0,007 |
| 256 tokens | denso | **−0,035** | −0,007 | +0,002 |
| 256 tokens | híbrido | −0,020 | **+0,014 [+0,005, +0,024]** | **+0,021 [+0,003, +0,040]** |
| con notas al pie | BM25 | +0,001 | **−0,006** | **+0,018** |
| con notas al pie | denso | +0,005 | **−0,008** | **−0,020** |
| con notas al pie | híbrido | −0,000 | **−0,006** | +0,000 |
| 150 palabras | BM25 | −0,001 | (−0,026) | +0,006 |
| 150 palabras | denso | +0,010 | (−0,024) | +0,008 |
| 150 palabras | híbrido | +0,023 | (−0,017) | +0,007 |

En negrita, las diferencias cuyo intervalo no incluye el 0.

La columna «C párrafo» de 150 palabras va entre paréntesis porque no es comparable: con chunks más cortos cambia el número de chunks relevantes y el orden ideal. La comparación justa para el tamaño de chunk es «C documento».

**Decisiones:**
- **Cabecera de contexto: se mantiene.** En C quitarla hace perder al denso 0,027 por párrafo y 0,054 por documento, ambos significativos. La pequeña ganancia del híbrido en A se explica porque esas consultas evitan el nombre del caso. En el híbrido, C no muestra diferencia.
- **Chunks de 250 palabras: se mantienen.** Con 150 palabras nada mejora de forma significativa en A ni en C documento, y el índice crece 1,8 veces.
- **512 tokens: se mantiene, con una salvedad.** El denso pierde 0,035 con 256 tokens en A. En C, en cambio, el híbrido gana 0,014–0,021 con 256. Las señales se contradicen y son pequeñas, así que no se cambia. Si se quisiera afinar, la siguiente prueba es un híbrido con ponderación distinta entre BM25 y denso, no la ventana.
- **Notas al pie: siguen fuera del índice.** Sus efectos son pequeños y de signo mixto.

### Artefactos guardados
`procesado/evaluacion/` (regenerable, fuera de git):
- `tabla_metodos_resumenes.csv`, `tabla_metodos_consultas_propias.csv`, `tabla_metodos_cuadernillos.csv` y `tabla_ablaciones.csv`: las tablas de arriba;
- `evaluacion_por_consulta.csv`: las métricas por consulta, conjunto, método y variante;
- `consultas_resumenes.csv`: las 290 consultas del conjunto A.

`evaluacion/` (en git):
- las consultas propias y sus juicios;
- las consultas y juicios de los cuadernillos;
- `extraer_cuadernillos.py`.

### Afecta al artículo
La sección de evaluación del artículo debe reemplazar la prueba de humo por estas tablas y la figura 11. Queda para la fase 6.

---

## 10. Fase 5: análisis exploratorio con contenido (punto 2 y punto 3)

El análisis exploratorio describía el texto (tamaños, términos frecuentes, nubes), pero casi nada del contenido jurídico. Se agregó lo que interesa a quien consulta la jurisprudencia y lo que valida las decisiones del pipeline. Las figuras se guardan en `procesado/figuras/`. Los números de figura siguen siendo los de los archivos y se reordenan en el artículo (fase 6).

### 10.1 Sentencias en el tiempo y por Estado (figura 2, reemplaza «documentos por año»)
Tres paneles: sentencias por año apiladas por tipo, longitud de las sentencias de fondo por quinquenio y un mapa de calor Estado × década.
- **Volumen.** Desde 2018 hay más de 20 sentencias por año. De las 595 con año, 394 son de fondo y 109 de interpretación. 2026 está incompleto y se marca en la figura.
- **Estados.** Los cinco con más sentencias reúnen el 56 %: Perú 20 %, Guatemala 10 %, Ecuador 9 %, Colombia 9 % y Argentina 8 %.
- **Longitud.** La mediana de las sentencias de fondo pasa de 13.100 palabras en los noventa a 42.100 en los 2000 y 59.300 en los 2010. En los 2020 es de 46.900.

Los tipos poco frecuentes (competencia y sin tipo) se agrupan en «otra», para no pasar de cinco colores.

### 10.2 Zipf con exponente ajustado y Heaps (figura 6, reemplaza «Zipf y Jaccard»)
- **Zipf.** α = 1,08, ajustado en los rangos 10 a 10.000 con puntos espaciados en escala logarítmica, para que cada década de rangos pese lo mismo. Con todos los puntos daba 1,24, porque los rangos altos son muchos más. La curva se dobla en la cola de hápax.
- **Heaps.** V = 15,2·n^0,53 sobre 22,7 millones de tokens y 118.638 palabras distintas, leyendo las sentencias en orden cronológico.

Las dos leyes se cumplen, así que el texto extraído se comporta como lenguaje natural. El vocabulario no deja de crecer con cada sentencia nueva (nombres de víctimas, lugares, instituciones).

Se quitó el mapa de Jaccard sobre 12 sentencias al azar, que no decía nada del corpus. También se quitó la nube de palabras del texto crudo: queda solo la de lemas (figura 8).

### 10.3 Artículos de la Convención declarados violados (figura 10, ampliada)
La figura ya tenía la frecuencia de cada artículo y el mapa por Estado (sección 8). Se añadió un panel con la evolución por quinquenio, solo para quinquenios con 10 o más sentencias de fondo:

| artículo | 1995–99 | 2000–04 | 2005–09 | 2010–14 | 2015–19 | 2020–24 | 2025–26 |
|---|---|---|---|---|---|---|---|
| 8 · garantías judiciales | 56 % | 75 % | 81 % | 89 % | 92 % | 89 % | 96 % |
| 5 · integridad personal | 56 % | 61 % | 55 % | 68 % | 64 % | 61 % | 88 % |
| 4 · vida | 44 % | 46 % | 43 % | 46 % | 40 % | 42 % | 46 % |
| 13 · libertad de expresión | 0 % | 11 % | 16 % | 11 % | 12 % | 30 % | 46 % |
| 26 · DESCA | 0 % | 0 % | 2 % | 0 % | 10 % | 24 % | 38 % |

- **Lo estable.** Los artículos 8 y 25 aparecen en tres de cada cuatro sentencias de fondo o más; el 4 se mantiene alrededor del 44 %.
- **Lo que cambia.** El artículo 26 (derechos económicos, sociales, culturales y ambientales) casi no aparecía antes de 2015 y hoy está en más de un tercio de las sentencias. La libertad de expresión también crece.
- **Para el RAG.** Los temas más recientes tienen menos jurisprudencia acumulada, y conviene revisarlos al evaluar la cobertura.
- **Con cautela.** 2025–26 tiene solo 24 sentencias de fondo.

### 10.4 Términos característicos de cada sección (figura 12, nueva)
Para seis secciones canónicas se calcula el peso TF-IDF medio de cada término en los chunks de la sección, menos su peso medio en el resto. Restar el resto evita que ganen los términos comunes a todas («víctima», «derecho»). Una expresión no se repite como unigrama y bigrama.

| sección | términos más característicos |
|---|---|
| Hechos | juzgado, sala, policía, penal, fiscalía y meses del año |
| Prueba | prueba, documento, declaración, admitir, probatorio, testigo |
| Fondo | derecho, libertad, convención, autoridad, obligación |
| Reparaciones | daño, gasto, dólares, reparación, inmaterial, indemnización |
| Excepciones preliminares | excepción preliminar, recurso interno, agotamiento, admisibilidad |
| Puntos resolutivos | unanimidad, «decide», «párrafo presente», fórmulas fijas |

Cada sección tiene un vocabulario propio. Eso valida la detección de secciones del punto 2 y el filtro por sección de `buscar()`.

### 10.5 UMAP de los embeddings (figura 13, nueva)
Antes era un diagrama de dispersión sin colores que no se guardaba. Ahora tiene dos paneles:
- **Chunks por sección.** Muestra de 2.000 chunks; se colorean hechos, fondo y reparaciones, y el resto va en gris. Las reparaciones forman una región propia. Hechos y fondo se mezclan, porque el fondo vuelve a narrar los hechos.
- **Sentencias.** Cada sentencia es el embedding medio de sus chunks, coloreada por tipo, y una línea une las del mismo caso.

**Validación cuantitativa:** de las 290 sentencias que tienen otra del mismo caso, en el 95 % la sentencia más parecida (coseno) es de su mismo caso. Al azar sería el 0,2 %.

**Salvedad:** la cabecera de cada chunk lleva el título del caso, que contribuye a ese parecido. El 95 % mide sobre todo que los embeddings agrupan bien las sentencias de un caso. Que capturen el contenido jurídico lo muestran los conjuntos B y C (sección 9).

### Afecta al artículo
Las figuras 2, 6, 10, 12 y 13 y estas cifras van a la sección de análisis exploratorio del artículo. Queda para la fase 6, con la numeración de figuras definitiva.

---

## Cómo volver a ejecutar

0. **En local:** definir `CORTEIDH_BASE` con la ruta del proyecto. Si `casos/` está vacía, poner `DESCARGAR = True` en la celda de configuración para descargar los PDF con el scraper (requiere `playwright install chromium`, unos 80 minutos), y luego ejecutar todo. En Colab no hace falta cambiar nada.
1. **Punto 1:** reconstruir el corpus desde la celda de construcción. No vuelve a descargar los PDF, pero tarda más porque lee el tamaño de fuente de cada renglón.
2. **Puntos 2 y 3:** ejecutarlos en la misma sesión. El punto 3 usa la normalización del punto 2 y lo avisa con un `assert` si falta.
3. **Verificaciones:** revisar las salidas nuevas, sobre todo cuántas sentencias tienen puntos resolutivos detectados y el porcentaje de palabras en notas.
4. **Conjunto C:** solo hace falta si se añaden cuadernillos. Poner los PDF en `cuadernillos/` y ejecutar `python evaluacion/extraer_cuadernillos.py cuadernillos procesado/corpus_limpio.parquet`, que regenera los dos CSV de `evaluacion/`. Después volver a ejecutar el punto 4.
5. **Artículo:** si se vuelve a ejecutar con otros datos, revisar las cifras de `articulo/Articulo_actualizado.docx` (sección 7).

## Pendiente (fase 6)
- Revisar los juicios de `evaluacion/qrels_consultas_propias.csv` (hechos por un modelo de lenguaje).
- Opcional: más cuadernillos para el conjunto C (basta ponerlos en `cuadernillos/` y volver a correr el extractor, sección 9.5).
- Opcional de la fase 3: temas (BERTopic o LSA) y comparar e5 con bge-m3.
- Artículo: llevar las cifras de las secciones 8, 9 y 10 y las figuras nuevas, con la numeración definitiva.
- Corregir la detección de secciones en las 43 sentencias que fallan (sobre todo antiguas) y completar los metadatos desde el buscador.
- Artículo: revisar la versión actualizada y llevarla al Google Doc (sección 7).

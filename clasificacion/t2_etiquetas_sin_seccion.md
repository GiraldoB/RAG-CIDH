# Tarea 2: etiquetas de referencia para los fragmentos «Sin sección»

*17-11-2026, rama `entrega-2`*

## Para qué

El clasificador de la Tarea 2 asigna una sección a los 2.048 fragmentos «Sin sección», pero no había cómo saber si
acertaba. Aquí se construyen etiquetas de referencia para esos fragmentos. Se etiqueta **la sección completa del PDF**
(lo que va bajo cada número romano) y no párrafo por párrafo: leída entera, es mucho más fácil distinguir Hechos
(lo que se probó que pasó) de Fondo (el análisis de la Corte sobre si eso viola derechos).

## Por qué esos fragmentos quedaron sin sección

El notebook (`proyecto_corregido.ipynb`, punto 2) solo reconoce títulos con este formato:
`VI. HECHOS` (número romano, punto, título en mayúsculas). En los PDF se encontraron otros cinco formatos:

| Formato en el PDF | Ejemplo | Sentencias |
|---|---|---|
| Número romano solo, sin título | `VI` en una línea y el párrafo `31.` en la siguiente | casi todas las de 1987–1999 |
| Guion en vez de punto | `VI – HECHOS`, `I -INTRODUCCIÓN` | Norín Catrimán (2014): 412 de 421 fragmentos sin sección |
| Dos puntos seguidos | `II..` y `PROCEDIMIENTO ANTE LA CORTE` en la línea siguiente | Cuscul Pivaral (2018) |
| Título en minúsculas | `VII Puntos Resolutivos`, `II Competencia y Composición de la Corte` | interpretaciones de 2008–2009 |
| Resolución, no sentencia | `VISTOS:` / `CONSIDERANDO:` / `RESUELVE:` | 4 documentos de 1997–1999 y 2025 |

Además, en las sentencias antiguas la parte resolutiva empieza con `53. Por tanto,` en minúsculas, y el notebook solo
reconoce `POR TANTO:`. Por eso algunos puntos resolutivos también quedaron como «Sin sección».

## Qué se hizo

**1. `clasificacion/secciones_romanas.py`.** Corta cada uno de los 56 PDF en sus secciones romanas.
- Busca la secuencia I, II, III… más larga. Las entradas del índice (con `.....`) se descartan, y un `I.` citado
  dentro del texto no reinicia la secuencia.
- El primer `VOTO …` en mayúsculas cierra la sentencia.
- Para cada sección guarda su primer párrafo numerado. Los fragmentos ya tienen `parr_ini` y `parr_fin`, así que
  cada uno hereda la etiqueta de la sección donde empieza.
- Si el título dice qué es, la etiqueta es automática. Se usan las mismas reglas que `canon_seccion()` del notebook,
  más «Por tanto» → Puntos resolutivos, y Admisibilidad, Reconocimiento de responsabilidad y Medidas provisionales → Otra.
- Las secciones sin título quedan en `textos/` para que un LLM las lea completas.
- Las resoluciones (VISTOS / CONSIDERANDO) van enteras a «Otra», porque su numeración vuelve a 1 en cada bloque.

Resultado: 493 secciones en 56 sentencias. 158 se etiquetan por título y 335 las leyó un LLM. Los 2.048 fragmentos
tienen etiqueta: 1.430 vienen del LLM, 546 del título y 72 de una corrección.

**2. `evaluacion/revision/deepseek_secciones_prompt.md`.** El mensaje para DeepSeek en opencode. Incluye las
definiciones de cada etiqueta, los criterios para los casos difíciles (sobre todo Hechos frente a Fondo) y el formato
de salida: una línea JSON por sección, con una frase copiada del texto como evidencia. Se puede retomar si se corta.

**3. Revisión manual.** `revision.xlsx` tiene una fila por sección, con el inicio del texto, la etiqueta automática,
la del LLM, su confianza y su evidencia, y una columna **✎ Etiqueta correcta** con lista desplegable. Al volver a
correr el script, lo anotado a mano se conserva.

**Correcciones versionadas.** `clasificacion/secciones_correcciones.csv` está en git y tiene una línea por sección
corregida: archivo, etiqueta y motivo. Así las correcciones acordadas se reproducen en cualquier equipo.

Prioridad de las etiquetas: **manual > `secciones_correcciones.csv` > título del PDF > LLM**.

**4. `clasificacion/evaluar_t2_sin_seccion.py`.** Compara las predicciones de la Tarea 2
(`t2_sin_seccion_predicciones.csv`) con estas etiquetas y escribe `resultados/t2_eval_sin_seccion*.csv`.

## Primer resultado (solo con las etiquetas por título)

Son 392 fragmentos evaluables, casi todos de Norín Catrimán y de otras sentencias modernas:

| Subconjunto | n | Exactitud | F1 macro |
|---|---|---|---|
| Todos | 392 | 0,83 | 0,83 |
| Aceptados por el umbral (0,65) | 337 | 0,86 | 0,87 |

El error más común sigue siendo Fondo predicho como Hechos. Además, el umbral acepta 105 fragmentos que son «Otra»
(procedimiento, competencia…). Esa clase no existe en la Tarea 2, así que esos fragmentos siempre quedan mal
etiquetados. Este resultado **aún no mide las sentencias antiguas**: para eso faltan las respuestas del LLM y la
revisión.

## Cómo seguir

```bash
# 1. (Hecho el 17-11) Pegar evaluacion/revision/deepseek_secciones_prompt.md en opencode (DeepSeek), abierto en la carpeta del proyecto
# 2. Llevar las respuestas al Excel y a los fragmentos
python clasificacion/secciones_romanas.py --aplicar
# 3. Revisar procesado/clasificacion/secciones_romanas/revision.xlsx (primero confianza baja y media)
python clasificacion/secciones_romanas.py --aplicar
# 4. Evaluar la Tarea 2
python clasificacion/evaluar_t2_sin_seccion.py
```

Usa `CORTEIDH_BASE` como el resto de los scripts. Las salidas quedan en `procesado/clasificacion/secciones_romanas/`,
que no se sube a git.

## Revisión de las respuestas de DeepSeek (17-11-2026)

- **Completitud:** 330 de 330 archivos respondidos, sin repetidos ni etiquetas inválidas. Las 330 evidencias son
  frases literales del texto. Confianza: 278 alta, 51 media y 1 baja.
- **Coherencia:** la secuencia de etiquetas de cada sentencia es razonable. Por ejemplo, Velásquez Rodríguez (fondo):
  Otra → Excepciones → Prueba → Hechos → Fondo → Reparaciones. Además, el tipo de sentencia coincide: 53 de 98
  secciones de sentencias de excepciones son Excepciones preliminares, y 57 de 77 en las de reparaciones son Reparaciones.
- **Inconsistencia, ya corregida:** en las sentencias de excepciones preliminares, la sección II resume los hechos
  *según la denuncia o la demanda*, no los probados. DeepSeek marcó 8 como `Hechos` (Caballero Delgado, Genie Lacayo,
  Panel Blanca, Godínez Cruz, Castillo Páez, Loayza Tamayo, Blake, Niños de la Calle) y otras iguales como `Otra`
  (Fairén Garbi, Cayara, Maqueda). Lo mismo pasa con Loayza Tamayo (fondo) III, «la Corte resume los hechos de la
  demanda». Según la definición del equipo (Hechos = lo probado), deberían ser `Otra`, como «Introducción de la
  causa» en las sentencias modernas. Se pasaron las 9 a `Otra` en `secciones_correcciones.csv`.
- **Error del script, ya corregido:** la regla por título buscaba la palabra clave en cualquier parte del título.
  En las sentencias de interpretación, «Sobre los criterios del Tribunal para determinar hechos» quedó como Hechos y
  «…procedimiento interno de indemnización» como Otra. Ahora solo mira el comienzo del título. Las 5
  secciones que pasaron a no tener etiqueta las leyó Claude y quedaron en `secciones_correcciones.csv`. Si se prefiere
  que las lea DeepSeek, basta con borrarlas de ese archivo y volver a correr el prompt, que salta las ya respondidas.
- `clasificacion/comun.py` cambió: si no existe la carpeta de Drive, usa la raíz del repositorio. Es inofensivo, pero
  el prompt pedía no modificar archivos. Se dejó porque sirve para correr los scripts en local.

## Resultado de la Tarea 2 contra estas etiquetas

| Subconjunto | n | Exactitud | F1 macro |
|---|---|---|---|
| Todos los evaluables | 1.177 | 0,76 | 0,75 |
| Aceptados por el umbral | 900 | 0,84 | 0,83 |
| Sentencias 1987–1999 | 736 | 0,71 | – |
| Sentencias desde 2000 | 441 | 0,85 | – |

Lectura:
- Las sentencias antiguas cuestan más que las modernas, lo esperable porque el modelo se entrenó con sentencias
  modernas. En validación cruzada se obtuvo 0,87 de F1 macro.
- La confianza está bien calibrada: con confianza por encima de 0,9 acierta el 92 %; por debajo de 0,5, el 42 %.
- Los errores más frecuentes son Fondo → Hechos (56), Reparaciones → Fondo (31) y Prueba → Hechos (28).
- **El problema principal no está en la tabla:** 541 de los 1.718 fragmentos (32 %) son `Otra` (procedimiento,
  introducción, competencia, resúmenes de la denuncia). La Tarea 2 no tiene esa clase y el umbral acepta 310 de ellos
  con una sección equivocada, casi siempre Hechos o Excepciones. Por eso, de lo que el modelo etiqueta como Hechos
  y acepta, solo el 31 % es Hechos de verdad.
- Para el producto (el filtro por sección del RAG), las etiquetas de este flujo sirven directamente para los 2.048
  fragmentos y son mejores que la predicción. Si se quiere mantener el clasificador, conviene agregarle la clase
  «Otra»: en las sentencias modernas hay muchos fragmentos de introducción y procedimiento para entrenarla.

## Clase «Otra» en la Tarea 2 (17-11-2026)

Se agregó una séptima clase, **Otra**: el trámite y el contexto, no la decisión.

- **Definición:** `seccion_t2()` en `comun.py`. Entran las secciones canónicas Introducción de la causa,
  Procedimiento ante la Corte, Competencia y Consideraciones previas. También entran las secciones «Otras» del
  notebook cuyo título empieza por Reconocimiento, Admisibilidad, Consideración previa o Medidas provisionales.
- **Qué queda fuera:** el resto de «Otras» sigue excluido, porque mezcla títulos de artículos (que son Fondo),
  costas y otros contenidos.
- **Datos:** el conjunto pasa de 59.184 a **68.093 chunks**, de los que 8.909 son Otra. Las particiones
  (`particiones_secciones.csv`) se regeneraron, siguen agrupadas por caso y la diferencia máxima de proporción entre
  particiones es 0,003. La Tarea 1 no cambia: `articulos.parquet` queda idéntico.
- **Notebook:** se reemplazó la muestra de revisión manual por la evaluación contra estas etiquetas (bloque 8.1).
  `evaluar_t2_sin_seccion.py` ahora se puede importar desde el notebook.
- **Respaldo:** los resultados anteriores, con seis clases, quedaron en `resultados/antes_clase_otra/`.

**Validación cruzada.** El mejor modelo sigue siendo `tfidf_lr_texto`. Su F1 macro baja a 0,846 ± 0,006
(antes 0,872) porque ahora tiene una clase más y es difícil. El F1 de Otra es 0,83. En la prueba temporal da 0,863.

**En los 1.718 chunks «Sin sección»**, ahora todos evaluables:

| | Antes (6 clases) | Ahora (7 clases) |
|---|---|---|
| Exactitud, todos | 0,52 | **0,69** |
| F1 macro, todos | 0,50 | **0,67** |
| Exactitud, aceptados por el umbral | 0,63 (1.210 aceptados) | **0,81** (1.052 aceptados, umbral 0,75) |
| Sentencias 1987–1999 | 0,45 | **0,65** |
| Sentencias desde 2000 | 0,67 | **0,78** |

Precisión de los aceptados según la sección predicha:

| Sección predicha | Precisión |
|---|---|
| Excepciones preliminares | 0,93 |
| Fondo | 0,90 |
| Otra | 0,86 |
| Prueba | 0,85 |
| Reparaciones | 0,79 |
| Puntos resolutivos | 0,56 (solo 9 aceptados) |
| Hechos | 0,49 |

- **El punto débil sigue siendo Hechos.** 80 chunks de Otra se predicen como Hechos: son procedimiento ante la
  Comisión y resúmenes de la denuncia, que narran fechas y actuaciones igual que los hechos probados. Para el filtro
  del RAG conviene no reasignar chunks a Hechos, o exigirles un umbral más alto.
- **Efecto en `buscar()` (bloque 9):** sigue en Δ = 0. Los chunks reasignados casi no aparecen entre los relevantes
  de las consultas juzgadas.

## Limitaciones y pendientes

- **134 fragmentos cruzan dos secciones.** El notebook no vio el límite y juntó párrafos de ambas. Se les da la
  etiqueta de la sección donde empiezan, con la nota «cruza dos secciones», y el evaluador también los mide aparte.
- **Citas con números romanos.** En Poblete Vilches (2018) y Genie Lacayo (1997, fondo), una lista citada
  («I. Conclusiones», «II. Recomendaciones», o una declaración del Gobierno numerada) se confunde con la sección II
  real. Afecta pocos fragmentos y se ve en la revisión: el título de la sección es una frase, no un título.
- **Votos.** No se usan como sección de la Tarea 2: la sentencia termina en el primer voto. Para el RAG valdría la pena
  una etiqueta «Voto disidente / concurrente» con el nombre del juez. Su título es claro (`VOTO DISIDENTE DEL JUEZ…`)
  y se detecta con una regla, sin clasificador.
- **Arreglo de fondo.** Llevar estos cinco formatos a `RE_TITULO` del notebook y volver a generar los fragmentos
  dejaría etiquetadas por título las 158 secciones de arriba en todo el corpus. Eso cambia `chunks.parquet` y los
  índices del RAG, así que hay que acordarlo con el equipo.
- Se borró el Excel para marcar límites a mano (`limites_secciones.xlsx` y su script), porque este flujo lo reemplaza.

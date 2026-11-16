# Borrador para el artículo: Tarea 1, artículos violados a partir de los hechos

> Borrador de la Persona 1 para que la Persona 3 lo integre en el artículo de la Entrega 2. Todas las cifras salen de `t1_articulos.ipynb` (tablas `procesado/clasificacion/resultados/t1_*.csv`). Las figuras están en `procesado/figuras/` con nombres `c0N_t1_*.png`; la numeración definitiva se fija en el artículo. Las referencias marcadas con [ref] faltan por completar.

## X.1 Planteamiento

**Pregunta.** ¿Se puede predecir, solo a partir del relato de los hechos, qué artículos de la Convención Americana declarará violados la Corte IDH?

**Tipo de problema.** Es una clasificación multietiqueta: una sentencia puede violar varios artículos a la vez, con 4,88 en promedio.

**Uso.** La tarea tiene interés práctico como apoyo para buscar jurisprudencia. Dado un relato de hechos, sugiere qué derechos revisar.

**Entrada y etiquetas.**
- **Entrada:** el texto de la sección Hechos de cada sentencia de fondo, delimitada en la Entrega 1.
- **Etiquetas:** los artículos declarados violados en los puntos resolutivos.
- **Separación:** el modelo nunca ve el fondo ni los resolutivos, que contienen la respuesta.

## X.2 Datos

**Sentencias.** De las 373 sentencias de fondo con artículos violados detectados, 305 tienen una sección Hechos utilizable: 67 no la tienen detectada, y 1 queda fuera por hechos de menos de 100 palabras o por no tener ningún artículo retenido. Hay una sentencia por caso. Los hechos tienen una mediana de 4.562 palabras (entre 412 y 31.830).

**Artículos.** Se conservan los 15 artículos declarados violados en al menos 25 sentencias: 3, 4, 5, 7, 8, 11, 13, 17, 19, 21, 22, 23, 24, 25 y 26.
- **Desbalance.** Es fuerte: el artículo 8 está en el 93,1 % de las sentencias, el 25 en el 80,0 % y el 5 en el 67,5 %. El 23 está en solo el 11,5 % (Figura c01).
- **Bloques que se repiten** (correlación phi, Figura c02):
  - familia, niñez y circulación (17–19: φ = 0,62; 17–22: 0,47);
  - vida e integridad (4–5: 0,55);
  - desaparición forzada (3–7: 0,47).

**Desplazamiento en el tiempo.** La distribución de etiquetas cambia con los años. Entre las sentencias hasta 2018 y las posteriores:
- el artículo 26 pasa del 3,4 % al 26,6 % (5 frente a 42 sentencias);
- el 13 se multiplica por 3,0;
- el 24 se multiplica por 2,4.

**Corrección de las etiquetas.** Al analizar los errores se encontró un fallo de la regla que extrae las etiquetas de la Entrega 1. Las listas con coma antes de la «y» final («artículos 7.1, 11.2, y 26») perdían el último artículo. La corrección añadió 10 etiquetas en 10 sentencias de este conjunto, sin cambiar las sentencias ni los artículos retenidos.

## X.3 Preprocesamiento y representación

**Representación principal.** Los lemas de la Entrega 1 (texto normalizado y lematizado con spaCy), representados con TF-IDF. Los parámetros de TF-IDF son `sublinear_tf`, `max_df` = 0,9 y `min_df` y n-gramas ajustados.

**Ablación** (Figura c05). Cada decisión de preprocesamiento se probó por separado con una ablación de 5 particiones:
- **Lemas frente a texto crudo.** Los lemas dan +0,007 de F1 macro, con intervalo del 95 % [−0,006; +0,020]. No es una diferencia significativa; se mantienen por ser un vocabulario más compacto.
- **Términos raros.** Admitir términos que aparecen en una sola sentencia (`min_df` = 1) baja el F1 macro en 0,10, porque el modelo memoriza detalles de cada caso.
- **Términos frecuentes.** Exigir 10 sentencias por término (`min_df` = 10) lo sube en 0,03.

**Auditoría de atajos.** Se taparon tres posibles atajos:
- **Citas de artículos.** También en los lemas, donde la Entrega 1 las había conservado como términos `art_8_1`.
- **Nombres de los Estados.**
- **Personas y lugares,** detectados con el reconocedor de entidades de spaCy.

Ninguno cambió el F1 macro en más de 0,007. El modelo no se apoya en que los hechos citen el artículo ni en el país demandado. El modelo final usa los lemas con las citas tapadas.

**Embeddings.** Como alternativa a TF-IDF se probaron embeddings densos de `multilingual-e5-base` [ref]. Los hechos se partieron en trozos de 250 palabras y se promediaron los vectores de los trozos.

## X.4 Modelos y validación

**Modelos.** Se compararon:
- una línea base que predice la proporción de cada artículo sin mirar el texto;
- regresión logística y SVM lineal sobre TF-IDF;
- Naive Bayes complementario sobre TF-IDF;
- regresión logística sobre los embeddings e5.

Todos usan el esquema uno contra todos (un clasificador binario por artículo). Los modelos lineales usan pesos de clase balanceados.

**Validación.** Se usaron 5 particiones fijas con estratificación iterativa multietiqueta [ref: Sechidis et al., 2011], compartidas por todo el equipo. Todo lo que se ajusta se elige dentro del entrenamiento de cada partición (validación anidada):

1. Una búsqueda en rejilla, con 3 particiones internas, elige el vocabulario (`min_df`, n-gramas) y la regularización C. El criterio es la precisión promedio (AP) macro, que no depende del umbral.
2. Con los hiperparámetros elegidos, las predicciones fuera de partición del entrenamiento sirven para fijar un umbral por artículo: el que maximiza su F1 entre 19 cuantiles de los puntajes.
3. El modelo se evalúa una sola vez en la partición de prueba.

**Métricas.**
- **Principales:** el F1 macro y la AP macro, que pesan igual los 15 artículos.
- **Complementarias:** el F1 micro, la pérdida de Hamming y la exactitud estricta.

**Pruebas complementarias.**
- **Significancia:** las diferencias entre modelos se prueban con *bootstrap* pareado (1000 remuestreos) sobre las predicciones fuera de partición.
- **Prueba temporal:** se entrena con las 147 sentencias hasta 2018 y se evalúa con las 158 de 2019 en adelante.

## X.5 Resultados

**Tabla X.** Clasificación de artículos violados. Media (y desviación) de las 5 particiones externas.

| Modelo | F1 macro | AP macro | F1 micro | Exactitud estricta |
|---|---|---|---|---|
| Línea base (sin texto) | 0,18 | 0,33 | 0,61 | 0,02 |
| TF-IDF + RL, umbral 0,5, sin ajustar | 0,58 (0,05) | 0,68 | 0,76 | 0,15 |
| **TF-IDF + RL, final** | **0,62 (0,06)** | 0,69 | 0,74 | 0,10 |
| TF-IDF + SVM lineal, final | 0,63 (0,06) | 0,70 | 0,74 | 0,10 |
| e5 + RL, final | 0,60 (0,04) | 0,67 | 0,72 | 0,07 |

**Lectura de la tabla.**
- **Frente a la línea base.** El texto de los hechos permite predecir bien los artículos: el modelo final supera a la línea base en +0,45 de F1 macro (intervalo del 95 %: [0,42; 0,48]).
- **Ajuste.** Elegir los hiperparámetros por AP y fijar un umbral por artículo aporta +0,046 [0,018; 0,078] sobre el mismo modelo sin ajustar. El costo es menos precisión (de 0,79 a 0,69) a cambio de más exhaustividad (de 0,73 a 0,81). Eso conviene si el sistema sugiere artículos para que una persona los revise.
- **Entre modelos.** La regresión logística empata con el SVM (−0,005 [−0,019; 0,009]). Supera por poco a e5 sin ajustar (+0,022 [0,000; 0,045]). El SVM sí supera a e5 (+0,027 [0,006; 0,049]).
- **Hiperparámetros.** Los elegidos varían entre particiones (C entre 10 y 300, `min_df` entre 3 y 20) sin que cambie el rendimiento. Lo que más pesa es el umbral, no la configuración.

**Por artículo** (Figura c03). La correlación de Spearman entre el F1 de un artículo y su número de positivos es 0,72.
- **Frecuentes** (8, 5, 25, 4): F1 entre 0,83 y 0,94.
- **Con vocabulario propio:** el 3 (desaparición forzada, paradero) y el 21 (territorio, comunidad) alcanzan 0,66 y 0,60 con 52 y 39 ejemplos.
- **Otros ocho artículos:** quedan entre 0,43 y 0,54, con precisión de 0,35 a 0,49.

**Prueba temporal** (Figura c04).
- **Sin ajustar.** Con el modelo sin ajustar y umbral 0,5, el F1 macro cae a 0,45: los artículos 13, 24 y 26 quedan casi en cero.
- **Con el protocolo final.** Todo se elige con las sentencias hasta 2018, y el F1 macro llega a 0,62. La validación cruzada, sobre las mismas 158 sentencias, da 0,665. La AP casi no varía (0,66–0,67), así que la mayor parte de la caída se debía al umbral.
- **Pérdida que queda.** Se concentra en los artículos que se volvieron frecuentes después de 2018 y tenían entre 5 y 16 ejemplos de entrenamiento: el 13 (de 0,58 a 0,29), el 26 (de 0,61 a 0,47), el 17 (de 0,54 a 0,39) y el 24 (de 0,58 a 0,46).

## X.6 Análisis de errores

Se leyeron los errores más seguros de los artículos 13, 24 y 26. Una parte importante no se debe al modelo, sino a cómo se asigna la etiqueta:

- **Art. 26 (DESCA): el criterio cambió con el tiempo (*concept drift*).** Los falsos positivos más seguros son casos de salud o trabajo anteriores a 2017: *Chinchilla Sandoval* (2016), *I.V. vs. Bolivia* (2016), *Gonzales Lluy* (2015) y *Trabajadores cesados del Congreso* (2006). En ellos la Corte resolvió con los artículos 4, 5, 8 o 25. Solo desde *Lagos del Campo vs. Perú* (2017) declara violado el 26 de forma autónoma [ref]. Hechos parecidos reciben etiquetas distintas según la época.
- **Art. 24 (igualdad): la discriminación es una calificación jurídica.** En varios falsos negativos (*Almeida vs. Argentina*, *García Rodríguez vs. México*) los hechos no mencionan la discriminación ni la igualdad: la Corte la establece en el fondo, al comparar tratos. Varios falsos positivos (*Ramírez Escobar*, *Azul Rojas Marín*) sí describen discriminación, pero la Corte la declaró dentro de otros derechos, en relación con el artículo 1.1.
- **Art. 13: dos derechos con la misma etiqueta.** El modelo aprende el 13 como libertad de prensa (*periodista, libertad de expresión*). En los casos recientes de desaparición, en cambio, el 13 aparece como derecho a la verdad o de acceso a la información, y el modelo no lo detecta (*Núñez Naranjo*, *Deras García*). También hay casos en los que la Corte declara expresamente que el Estado **no** violó el 13, aunque los hechos traten de información (*Ascencio Rosario*).

**Ruido en las etiquetas.** Leer los errores también sirvió para revisar los datos: así se encontró el fallo de la regla de extracción descrito en X.2.

**Memorización.** Entre los términos con más peso aparecen algunos nombres propios repetidos (*silva*, *reyes*). Es una señal leve de memorización, esperable con 244 sentencias de entrenamiento por partición.

## X.7 Limitaciones

- **Tamaño del conjunto.** Con 305 sentencias, la desviación entre particiones (±0,06 de F1 macro) es del mismo orden que varias de las diferencias entre modelos.
- **Etiquetas automáticas.** Las etiquetas se extraen con reglas de los puntos resolutivos y no se revisaron a mano de forma completa. Además, dependen de la doctrina de cada época.
- **Artículos excluidos.** Se dejan fuera los artículos con menos de 25 sentencias.
- **Hechos no detectados.** Quedan fuera las 67 sentencias sin sección Hechos detectada.
- **Embeddings sin ajustar.** No se probó el ajuste fino de modelos de lenguaje ni modelos de dominio jurídico, que podrían captar mejor las calificaciones jurídicas implícitas.
- **Alcance del modelo.** No predice la decisión de la Corte: sugiere los derechos que suelen corresponder a hechos parecidos.

## Figuras propuestas

| Archivo | Contenido | Sección |
|---|---|---|
| `c01_t1_prevalencia.png` | Porcentaje de sentencias con cada artículo | X.2 |
| `c02_t1_phi.png` | Correlación phi entre artículos | X.2 |
| `c05_t1_ablacion.png` | F1 macro por partición en la ablación | X.3 |
| `c03_t1_por_articulo.png` | F1 y AP de cada artículo frente a su número de ejemplos | X.5 |
| `c04_t1_temporal.png` | F1 por artículo: validación cruzada frente a prueba temporal | X.5 |

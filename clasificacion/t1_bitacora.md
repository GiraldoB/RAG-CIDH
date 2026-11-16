# Tarea 1 · Artículos violados desde los hechos
Entrega 2 · Corte IDH · Rama `t1-articulos` · 14/11/2026

## Datos y decisiones

- 305 sentencias de fondo; 15 artículos; 4,88 artículos por sentencia.
- Etiquetas: artículos declarados violados con al menos 25 sentencias positivas.
- Las etiquetas salen de los puntos resolutivos; el texto de entrada del modelo son los Hechos.
- Cifras actualizadas el 15/11 con las etiquetas corregidas (ver «Descubrimientos»).
- Fuente: `cargar_articulos()` → `procesado/clasificacion/articulos.parquet`; notebook `t1_articulos.ipynb`.

## Prevalencia

| Artículo | Derecho | % | n |
|---:|---|---:|---:|
| 8 | Garantías judiciales | 93,1 | 284 |
| 25 | Protección judicial | 80,0 | 244 |
| 5 | Integridad personal | 67,5 | 206 |
| 4 | Vida | 44,6 | 136 |
| 7 | Libertad personal | 43,0 | 131 |
| 13 | Libertad de expresión | 20,7 | 63 |
| 19 | Derechos del niño | 20,3 | 62 |
| 11 | Honra y dignidad | 18,7 | 57 |
| 3 | Personalidad jurídica | 17,0 | 52 |
| 26 | DESCA | 15,4 | 47 |
| 17 | Protección a la familia | 15,4 | 47 |
| 24 | Igualdad ante la ley | 14,1 | 43 |
| 22 | Circulación y residencia | 13,4 | 41 |
| 21 | Propiedad privada | 12,8 | 39 |
| 23 | Derechos políticos | 11,5 | 35 |

- El 8, el 25 y el 5 son los más frecuentes. El 23 es el menos frecuente (35), pero el 21 está cerca (39).

## Interpretación

### ¿Por qué el 8 y el 25?

- Para que la Corte conozca un caso deben agotarse los recursos internos (art. 46.1.a CADH), salvo las excepciones del art. 46.2.
- Con frecuencia el caso llega porque la respuesta interna fue insuficiente: no se investigó, no se juzgó o no se reparó a tiempo.
- Por eso, buena parte de las violaciones sustantivas no resueltas internamente arrastra una falla de **debido proceso (art. 8)** y de **protección judicial (art. 25)**.
- Es un **efecto de arrastre** o denominador procesal común. No es automático: no toda sentencia viola el 8 y el 25.

### ¿Qué pares aparecen juntos?

- La co-ocurrencia cruda (`Y.T @ Y`) está dominada por el 8 y el 25 porque están en casi todas las sentencias. Phi matiza ese efecto: el par 8–25 tiene φ = 0,25.
- Las asociaciones más altas son:

| Par | φ | Lectura |
|---|---:|---|
| 17–19 | 0,62 | Familia y niñez |
| 4–5 | 0,55 | Vida e integridad personal |
| 17–22 | 0,47 | Familia y circulación/residencia |
| 3–7 | 0,47 | Personalidad jurídica y libertad personal |
| 19–22 | 0,40 | Niñez y circulación/residencia |

- **17–19–22:** consistente con el desplazamiento forzado y la movilidad humana afectando el núcleo familiar y la niñez.
- **4–5:** ejecuciones extrajudiciales, tortura y uso excesivo de la fuerza; la privación de la vida suele implicar afectación a la integridad.
- **3–7:** desaparición forzada y detención arbitraria; se niega la personalidad jurídica y la libertad.
- Son interpretaciones sobre patrones agregados; para sostenerlas hay que revisar casos concretos. Phi es descriptivo: no prueba causalidad y su valor máximo depende de la prevalencia.

### El 23, el menos frecuente

- Los casos de derechos políticos son un subconjunto específico (elecciones, participación) y no acompañan las violaciones típicas de vida, libertad e integridad.
- Es una hipótesis: conviene revisar los casos del corpus para confirmarla.

## Descubrimientos

### 15/11 · Las etiquetas tenían un error
- **Dato:** al leer los falsos positivos del art. 26 apareció *Pavez Pavez*, que la Corte sí declaró violado. La regla de la Entrega 1 no leía listas con coma antes de la «y» final («artículos 7.1, 11.2, y 26»).
- **Interpretación:** cambian 10 etiquetas de este conjunto, todas añadidas (art. 7: 3; art. 3 y 25: 2; arts. 17, 24 y 26: 1). El conjunto y las particiones no cambian.
- **Siguiente:** corregido en `construir_conjuntos.py` y en el notebook de la Entrega 1 (`CAMBIOS.md`, sección 11). Todas las cifras se recalcularon.

### 15/11 · Los lemas llevaban las citas de artículos
- **Dato:** la normalización de la Entrega 1 convierte «artículo 8.1» en `art_8_1`; 243 de 305 sentencias tienen alguna. `tapar_citas` ahora las tapa también en lemas.
- **Interpretación:** taparlas cambia el F1 macro en +0,001. El modelo no usa las citas. El modelo final usa los lemas tapados de todos modos.

### 15/11 · Modelo final y prueba temporal
- **Dato:** TF-IDF + regresión logística, con hiperparámetros elegidos por AP y un umbral por artículo dentro de la validación anidada: F1 macro 0,62 ± 0,06 y AP 0,69. Empata con el SVM (0,63) y supera por poco a e5 (0,60). En la prueba temporal da 0,62, frente a 0,45 con umbral 0,5 y 0,665 en la validación cruzada sobre las mismas sentencias.
- **Interpretación:** casi todo el colapso temporal era el umbral. La pérdida que queda está en los artículos 13, 26, 17 y 24.
- **Siguiente:** llevar las cifras y las figuras c01–c05 al artículo (`t1_seccion_articulo.md`).

### 15/11 · Errores que no son del modelo
- **Dato:** los falsos positivos más seguros del 26 son casos de salud o trabajo de 2006 a 2016 (*Chinchilla Sandoval*, *I.V.*, *Gonzales Lluy*). Los falsos negativos del 24 no mencionan la discriminación en los hechos (*Almeida*, *García Rodríguez*). Los del 13 son desapariciones donde el 13 es el derecho a la verdad.
- **Interpretación:** antes de *Lagos del Campo* (2017) la Corte no declaraba el 26: es *concept drift*. El 24 y el 13 se deciden en el fondo, a partir de calificaciones jurídicas que no están en los hechos.

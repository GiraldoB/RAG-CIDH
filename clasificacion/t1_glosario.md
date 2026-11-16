# Glosario de Conceptos Clave: Clasificación Multietiqueta (Corte IDH)

Notas de estudio sobre análisis exploratorio, desplazamiento temporal y evaluación de modelos aplicados a sentencias de la Corte Interamericana de Derechos Humanos.

---

## 1. Naturaleza de los datos

* **Clasificación multietiqueta (*Multilabel classification*):** A diferencia de la clasificación tradicional (donde se elige *una* sola categoría entre varias), aquí una misma sentencia puede tener **múltiples etiquetas activas a la vez** (en este corpus, un promedio de ~4,8 artículos violados por sentencia).
* **Desbalance de clases y prevalencia:** Ocurre cuando unas etiquetas aparecen muchísimo y otras muy poco. La **prevalencia** (`Y.mean(axis=0)`) es la proporción de sentencias en las que aparece un artículo (por ejemplo, el Art. 8 está en el 93 % de los casos, mientras que el Art. 23 está en el 11 %). Este desbalance hace que los modelos tiendan a ignorar los artículos menos frecuentes.

---

## 2. Relaciones entre etiquetas

* **Matriz de coocurrencia ($Y^T Y$):** Cuenta cuántas veces aparecen juntos dos artículos en una misma sentencia. Su limitación es el **sesgo de frecuencia marginal**: como el Art. 8 aparece en casi todas las sentencias, sumará coincidencias altas con cualquier otro artículo por pura probabilidad, ocultando relaciones jurídicas más específicas.
* **Correlación $\phi$ (*Phi*):** Mide si dos variables binarias (`0` o `1`) aparecen juntas **más o menos de lo esperado por azar** (va de `-1` a `+1`). Descuenta el efecto del volumen, silencia el ruido de los artículos transversales (Arts. 8 y 25) y revela bloques temáticos reales, como vida/integridad (`4–5`) o desplazamiento/familia (`17–19–22`).

---

## 3. El efecto del tiempo en los datos

* ***Label shift* (Desplazamiento de etiquetas):** Cambia **qué tan frecuente** es una etiqueta entre el pasado y el presente, aunque la definición del derecho sea la misma. En estos datos, el Art. 26 pasa de 3,4 % en entrenamiento a 26,6 % en prueba.
* ***Concept drift* (Desplazamiento de concepto):** Cambia **la relación entre los hechos y la etiqueta**: hechos parecidos reciben otra etiqueta en otra época. En estos datos el ejemplo claro es el Art. 26. Antes de *Lagos del Campo vs. Perú* (2017), la Corte resolvía los casos de salud o trabajo con otros artículos (vida, integridad, garantías judiciales). Después empezó a declarar violado el 26 directamente. Por eso el modelo marca el 26 en casos antiguos de salud, donde la etiqueta dice que no.
* **Cambio en la co-ocurrencia:** que el Art. 13 aparezca junto a `4–5–7` en los años recientes y no antes es un cambio en **qué artículos se combinan**, no por sí solo un *concept drift*. Además, con pocos positivos por periodo la correlación phi es muy inestable: conviene leerla junto al número de sentencias de cada periodo.
* **Evaluación temporal vs. Validación cruzada aleatoria:** Mezclar sentencias de distintos años al azar le permite al modelo "espiar" patrones del futuro. Separar los datos cronológicamente (`entrenamiento` histórico vs. `prueba` reciente) simula cómo funcionará el modelo en la vida real y mide si resiste la evolución jurisprudencial.

---

## 4. Evaluación y línea base

* **Modelo de línea base (*Dummy / Baseline*):** Un modelo "ciego" que ignora el texto de los hechos y predice usando únicamente las frecuencias históricas (`Y[ent].mean(axis=0)`). Funciona como el **piso mínimo**: si un modelo entrenado con texto no supera esta marca, significa que no está aprendiendo del contenido jurídico.
* **Micro-F1 vs. Macro-F1:**
  * **Micro-F1:** Suma todos los aciertos y errores globales sin importar de qué artículo vengan. Como los artículos 8 y 25 tienen muchísimos casos, dominan esta métrica y pueden maquillar un mal desempeño en artículos raros.
  * **Macro-F1:** Calcula el F1 de cada artículo por separado y luego saca un promedio simple donde todos pesan igual ($1/15$). Es la métrica más exigente porque penaliza fuertemente si el modelo saca `0` en los artículos menos frecuentes.
* **Ajuste de umbral (*Threshold tuning*):** Por defecto, un clasificador predice `1` cuando su probabilidad estimada supera `0.5`. Sin embargo, en artículos que eran rarísimos durante el entrenamiento (como el Art. 26), el modelo suele asignar probabilidades conservadoras (por ejemplo, `0.25`) incluso cuando sí hubo violación; reducir ese umbral permite rescatar esos aciertos (*recall*).
---

## 5. Validación y modelo final

* **Validación anidada (*nested cross-validation*):** dos niveles de particiones. Las 5 particiones externas solo sirven para medir. Dentro del entrenamiento de cada una, 3 particiones internas eligen hiperparámetros y umbrales. Así la partición de prueba nunca influye en ninguna decisión, y la cifra final no queda inflada.
* **Precisión promedio (*AP*, área bajo la curva precisión-exhaustividad):** mide qué tan bien ordena el modelo las sentencias por puntaje para un artículo, **sin depender del umbral**. Por eso se usa para elegir hiperparámetros: el umbral se elige después.
* **Umbral por artículo:** en lugar de 0,5 para todos, cada artículo usa el corte que maximiza su F1 en las particiones internas. Los artículos raros suelen necesitar cortes más bajos.
* ***Bootstrap* pareado:** se remuestrean las mismas sentencias para dos modelos y se calcula la diferencia de F1 macro muchas veces (1000). Si el intervalo del 95 % no incluye el 0, la diferencia no se explica por el azar de qué sentencias tocaron.
* **Fuga de información (*leakage*) y atajos:** que el modelo acierte por algo que no debería usar, como la cita literal del artículo en los hechos o el nombre del Estado. Se revisa tapando esas pistas (`tapar_citas`, `tapar_estados`, entidades con spaCy) y viendo si el rendimiento cae.
* **Ruido en las etiquetas:** las etiquetas salen de una regla automática sobre los puntos resolutivos, y la regla puede fallar. Al leer los falsos positivos apareció un caso así: listas como «artículos 7.1, 11.2, y 26» perdían el último artículo. Leer los errores sirve también para revisar los datos.

# Instrucciones para DeepSeek (opencode): clasificar secciones de sentencias de la Corte IDH

Copia todo este archivo como mensaje a opencode, abierto en la carpeta del proyecto.

---

Eres un abogado que conoce la estructura de las sentencias de la Corte Interamericana de Derechos Humanos.

En la carpeta `procesado/clasificacion/secciones_romanas/textos/` hay unos 330 archivos `.md`. Cada uno es **una sección
completa** de una sentencia, tal como aparece en el PDF bajo un número romano (I, II, III…). Algunas no traen título,
porque las sentencias antiguas solo ponen el número. La primera línea dice el caso, el año, el tipo de sentencia
(excepciones preliminares, fondo, reparaciones, interpretación) y el número de la sección. La sección «0» es el texto
anterior a la sección I.

**Tarea:** lee cada archivo entero y decide a qué sección corresponde. Usa exactamente una de estas etiquetas:

| Etiqueta | Qué contiene |
|---|---|
| `Excepciones preliminares` | La Corte analiza las objeciones del Estado a que el caso se juzgue: no agotamiento de recursos internos, plazos, competencia ratione temporis/materiae, caducidad. En las sentencias antiguas «(Excepciones Preliminares)» casi todo el texto es esto, salvo la introducción y el procedimiento. Tambien analiza las respuestas de las demas partes a las objeciones del estado |
| `Hechos` | Lo que la Corte da por **probado que pasó**, contado de forma objetiva: fechas, detenciones, actuaciones judiciales internas. Frases típicas: «la Corte tiene por probados los siguientes hechos», «está probado que». |
| `Prueba` | Qué pruebas se recibieron y cómo se valoran: testigos, peritos, documentos, audiencias, admisibilidad y valor de la prueba. No es el relato de los hechos. |
| `Fondo` | El **análisis jurídico** de la Corte: si esos hechos violan derechos de la Convención Americana, con interpretación de artículos y jurisprudencia. Frases típicas: «la Corte considera», «constituye una violación del artículo». |
| `Reparaciones` | Indemnizaciones, daño material e inmaterial, costas y gastos, medidas de satisfacción, obligación de investigar como reparación, beneficiarios, artículo 63.1. También la interpretación de reparaciones ya ordenadas. |
| `Puntos resolutivos` | La parte dispositiva: «Por tanto, LA CORTE, DECIDE / DECLARA / DISPONE». |
| `Otra` | Introducción de la causa, procedimiento ante la Comisión y la Corte, competencia, composición de la Corte, admisibilidad de una demanda de interpretación, reconocimiento de responsabilidad, medidas provisionales y resoluciones de trámite. |

**Criterios para los casos difíciles:**

1. La diferencia que más importa es **Hechos frente a Fondo**. Si el texto sobre todo *narra* lo ocurrido, es `Hechos`. Si sobre todo *razona* si hubo violación de un derecho, es `Fondo`, aunque mencione hechos.
   Los resúmenes de lo que *dice la denuncia o la demanda* («Según la denuncia…», «la Corte resume los hechos de la demanda») no son hechos probados: son `Otra`.
2. Las alegaciones de las partes («la Comisión alegó», «el Gobierno sostuvo») van con la sección que discuten. Las de una excepción preliminar son `Excepciones preliminares`; las del fondo, `Fondo`.
3. Si la sección mezcla dos contenidos, elige el que ocupa **la mayor parte del texto** y nombra el otro en `secundaria`.
4. El tipo de sentencia de la primera línea ayuda, pero no decide. Una sentencia de fondo también tiene secciones de procedimiento, prueba y hechos.
5. Algunas secciones muy largas vienen recortadas: se omite el centro y se marca con «[… se omite la parte central …]».

**Salida:** por cada archivo agrega **una línea** al final de `procesado/clasificacion/secciones_romanas/respuestas.jsonl`,
en JSON válido y sin texto adicional:

```json
{"archivo": "883974738_sentencia__03.md", "seccion": "Excepciones preliminares", "secundaria": null, "confianza": "alta", "evidencia": "frase copiada del texto (máx. 25 palabras) que justifica la decisión"}
```

- `confianza` puede ser `alta`, `media` o `baja`. Usa `baja` si dudas entre dos etiquetas.
- `secundaria` es otra etiqueta de la tabla o `null`.
- `evidencia` es una frase **copiada literalmente** del archivo, no un resumen.

**Proceso:**

- Antes de empezar, lee `respuestas.jsonl` si existe y salta los archivos que ya estén respondidos. Así se puede retomar.
- Procesa los archivos en orden alfabético, de uno en uno, y escribe la línea apenas decidas cada uno.
- No modifiques los archivos de `textos/` ni ningún otro archivo.
- Cada 50 archivos informa cuántos van. Al terminar, di cuántas respuestas escribiste y cuántas tienen confianza `baja`.

---

## Después de DeepSeek (para el equipo)

```bash
python clasificacion/secciones_romanas.py --aplicar
python clasificacion/evaluar_t2_sin_seccion.py
```

El primer comando lleva las respuestas a `revision.xlsx` y a `chunks_etiquetados.csv`. Avisa si quedan secciones sin
respuesta o si hay etiquetas no válidas. Después se revisa `revision.xlsx` a mano: primero las de confianza `baja`
y `media`, y luego las demás.

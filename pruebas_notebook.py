"""Prueba las funciones del notebook (notas al pie, segmentación, normalización y chunks) con datos sintéticos.

No necesita los PDF ni Drive: extrae del notebook las funciones y constantes y las ejecuta.
Requiere pymupdf, spacy, pandas y es_core_news_sm (ya instalados en el notebook de Colab).

Uso:  python pruebas_notebook.py "proyecto_(2).ipynb"      (en Colab: !python pruebas_notebook.py ...)
"""
import ast
import json
import sys

import pandas as pd
import pymupdf
import spacy

nb = json.load(open(sys.argv[1], encoding="utf-8"))
G = {"display": print}


def celda(marca):
    (s,) = ["".join(c["source"]) for c in nb["cells"] if marca in "".join(c["source"])]
    return s


def cargar(marca):
    """Ejecuta imports, funciones y constantes (nombres en MAYÚSCULA) de la celda; omite el resto."""
    arbol = ast.parse("".join(l for l in celda(marca).splitlines(keepends=True) if not l.lstrip().startswith(("%", "!"))))
    for nodo in arbol.body:
        es_const = isinstance(nodo, ast.Assign) and all(isinstance(t, ast.Name) and t.id.isupper() for t in nodo.targets)
        if isinstance(nodo, (ast.Import, ast.ImportFrom)):
            try:
                exec(compile(ast.Module([nodo], []), "nb", "exec"), G)
            except ImportError:
                pass
        elif isinstance(nodo, ast.FunctionDef) or es_const:
            exec(compile(ast.Module([nodo], []), "nb", "exec"), G)


for marca in ["def texto_limpio(v):", "import os, json, re, unicodedata, warnings", "def extraer_metadata(paginas):",
              "def diagnostico_ruido(texto, n_paginas):", "NEGACIONES = {", "def segmentar_parrafos(doc_id, bloques",
              "def filtrar_tokens(doc):", "MAX_PALABRAS = 250", "def contar_palabras(texto):",
              "def dividir_parrafo_largo(", "def construir_chunks(df):"]:
    cargar(marca)

G["nlp"] = spacy.load("es_core_news_sm", disable=["parser", "ner"])
G["nlp_sent"] = spacy.blank("es")
G["nlp_sent"].add_pipe("sentencizer")
G["tqdm"] = lambda it, **k: it
ok = 0


def check(cond, msg):
    global ok
    assert cond, msg
    ok += 1


# ── 1. Notas al pie por tamaño de fuente ──
doc = pymupdf.open()
pag = doc.new_page()
y = 80
for i in range(25):
    pag.insert_text((72, y), f"Texto del cuerpo, renglón {i}, con suficientes palabras para dominar el tamaño.", fontsize=12)
    y += 16
x = 72 + pymupdf.get_text_length("La misma", fontsize=12)
pag.insert_text((72, y), "La misma", fontsize=12)
pag.insert_text((x + 1, y - 5), "7", fontsize=7)                              # marcador de nota
pag.insert_text((x + 6, y), " palabra continúa el renglón.", fontsize=12)
y += 16
pag.insert_text((90, y), "Cita textual en fuente menor dentro del cuerpo.", fontsize=10)
y += 16
pag.insert_text((72, y), "Último renglón del cuerpo.", fontsize=12)
pag.insert_text((72, 760), "7 Cfr. Caso Velásquez Rodríguez, párr. 166.", fontsize=10)
pag.insert_text((72, 775), "8 Ibíd., párr. 170.", fontsize=10)
pag.insert_text((300, 805), "2", fontsize=12)                               # número de página
cuerpos, notas = G["separar_notas"](doc)
check("Cfr. Caso Velásquez" in notas[0] and "Ibíd" in notas[0], f"notas no separadas: {notas[0]!r}")
check("Cfr." not in cuerpos[0], "la nota quedó en el cuerpo")
check("Cita textual" in cuerpos[0], "la cita en fuente menor dentro del cuerpo se perdió")
check("misma7" not in cuerpos[0].replace(" ", "") and "7" not in cuerpos[0].split("misma")[1][:4], f"marcador no quitado: {cuerpos[0]!r}")
check("Último renglón" in cuerpos[0], "se perdió texto del cuerpo")
print("cuerpo, renglón con marcador:", [l for l in cuerpos[0].split("\n") if "misma" in l or "palabra cont" in l])

# Sin fuente menor (PDF antiguo): todo queda en el cuerpo
doc2 = pymupdf.open()
p2 = doc2.new_page()
for i in range(10):
    p2.insert_text((72, 80 + 16 * i), f"Renglón {i} todo del mismo tamaño", fontsize=12)
c2, n2 = G["separar_notas"](doc2)
check(n2 == [""] and "Renglón 9" in c2[0], "un PDF sin notas perdió texto")

# ── 2. Tipo de sentencia ──
for desc, esperado in [("Excepciones Preliminares, Fondo, Reparaciones y Costas", "fondo"),
                       ("Interpretación de la Sentencia de Fondo, Reparaciones y Costas", "interpretación"),
                       ("Excepciones Preliminares", "excepciones preliminares"), ("Reparaciones y Costas", "reparaciones")]:
    check(G["tipo_de_sentencia"](desc) == esperado, f"tipo de {desc}")
meta = G["extraer_metadata"](["CORTE INTERAMERICANA DE DERECHOS HUMANOS\nCASO PRUEBA Y OTROS VS. PERÚ\n"
                              "SENTENCIA DE 24 DE ENERO DE 2024\n(Excepciones Preliminares, Fondo, Reparaciones y Costas)\n"])
check(meta["tipo_sentencia"] == "fondo" and meta["anio"] == 2024, f"metadatos: {meta}")
meta = G["extraer_metadata"](["CASO MOYA CHACÓN Y OTRO VS. COSTA RICA*\nSENTENCIA DE 23 DE MAYO DE 2022\n"])
check(meta["titulo"] == "caso moya chacón y otro vs. costa rica" and meta["estado"] == "costa rica", f"asterisco: {meta}")
# formatos antiguos y encabezados sin "CASO"
for cab, titulo, estado, fecha in [
        ("Corte Interamericana de Derechos Humanos\nCaso Yvon Neptune vs. Haití\nSentencia de 6 mayo de 2008\n(Fondo)",
         "caso yvon neptune vs. haití", "haití", "6 de mayo de 2008"),
        ("Corte Interamericana de Derechos Humanos\nCaso del Pueblo Saramaka vs. Surinam\nSentencia del 28 de noviembre de 2007\n(Fondo)",
         "caso del pueblo saramaka vs. surinam", "surinam", "28 de noviembre de 2007"),
        ("CORTE INTERAMERICANA DE DERECHOS HUMANOS\nVICKY HERNÁNDEZ Y OTRAS VS. HONDURAS\nSENTENCIA DE 26 DE MARZO DE 2021\n"
         "(Fondo)\nEn el Caso Vicky Hernández y otras Vs. Honduras, la Corte Interamericana",
         "caso vicky hernández y otras vs. honduras", "honduras", "26 de marzo de 2021"),
        ("Corte Interamericana de Derechos Humanos\nCaso Loayza Tamayo Vs. Perú\nResolución de la Corte 8 de marzo de 1998\n"
         "(Interpretación de la Sentencia de Fondo)", "caso loayza tamayo vs. perú", "perú", "8 de marzo de 1998"),
        ("CASO RADILLA PACHECO VS. ESTADOS UNIDOS MEXICANOS\nSENTENCIA DE 23 DE NOVIEMBRE DE 2009\n(Fondo)",
         "caso radilla pacheco vs. estados unidos mexicanos", "méxico", "23 de noviembre de 2009"),
        ("CASO NEIRA ALEGRÍA Y OTROS VS.PERÚ\nSENTENCIA DE 19 DE ENERO DE 1995\n(Fondo)",
         "caso neira alegría y otros vs.perú", "perú", "19 de enero de 1995")]:
    meta = G["extraer_metadata"]([cab])
    check((meta["titulo"], meta["estado"], meta["fecha"]) == (titulo, estado, fecha), f"metadatos antiguos: {meta}")
check(G["detectar_idioma"]("INTER-AMERICAN COURT OF HUMAN RIGHTS. In the case of Girón et al. v. Guatemala, the Court "
                           "of the State of the Convention ...") == "en", "idioma inglés")
check(G["detectar_idioma"]("La Corte declara la violación del derecho a la protección judicial del Estado.") == "es", "idioma español")

# ── 3. Segmentación: cuerpo, resolutivos y votos ──
lineas = ["CORTE INTERAMERICANA DE DERECHOS HUMANOS", "CASO PRUEBA VS. PAÍS", "Tabla de Contenido",
          "I INTRODUCCIÓN DE LA CAUSA", "XII. PUNTOS RESOLUTIVOS",        # índice: no debe cambiar de parte
          "I", "INTRODUCCIÓN DE LA CAUSA", "1.", "El caso sometido a la Corte misma1 del párrafo uno.",
          "2. Segundo párrafo (LIBERTAD)77, sigue el texto."]
lineas += [f"{n}. Texto del párrafo {n} con varias palabras de relleno." for n in range(3, 1002)]
lineas += ["XII", "PUNTOS RESOLUTIVOS", "1002. Por tanto,", "LA CORTE", "DECLARA,", "Por unanimidad, que:",
           "1. El Estado es responsable por la violación del artículo 13 de la Convención.",
           "2. El Estado es responsable por la violación del artículo 8.1.",
           "Corte IDH. Caso Prueba Vs. País. Sentencia de 1 de enero de 2024.",
           "VOTO CONCURRENTE DEL JUEZ FULANO DE TAL", "1. En este voto expreso mi opinión.", "2. Segundo párrafo del voto."]
txt, stats, bloques = G["limpiar_texto"]("\n".join(lineas), 10)
filas = pd.DataFrame(G["segmentar_parrafos"]("d1_sentencia", bloques))
cu = filas[filas.parte == "cuerpo"]
check(set(range(1, 1003)) <= set(cu.num_parrafo.dropna().astype(int)), "faltan párrafos del cuerpo (≥1000 o el 'Por tanto')")
check(not cu.texto.str.contains("El Estado es responsable").any(), "los resolutivos quedaron pegados al cuerpo")
check(not cu.texto.str.contains("voto").any(), "el voto quedó pegado al cuerpo")
re_ = filas[filas.parte == "resolutivos"]
check(sorted(re_.num_parrafo.dropna().astype(int)) == [1, 2], f"puntos resolutivos: {re_[['num_parrafo', 'texto']].values}")
check((re_.seccion == "XII. PUNTOS RESOLUTIVOS").all(), "sección de resolutivos")
vo = filas[filas.parte == "voto"]
check(sorted(vo.num_parrafo.dropna().astype(int)) == [1, 2] and vo.seccion.str.startswith("VOTO CONCURRENTE").all(), "voto")
p1 = cu[cu.num_parrafo == 1].texto.iloc[0]
p2 = cu[cu.num_parrafo == 2].texto.iloc[0]
check("misma del" in p1 and "(LIBERTAD)," in p2, f"marcadores: {p1!r} {p2!r}")
check(cu[cu.num_parrafo == 1].seccion.iloc[0] == "I. INTRODUCCIÓN DE LA CAUSA", "sección del párrafo 1")
fi = filas[filas.parte == "firmas"]
check(len(fi) == 1 and fi.texto.iloc[0].startswith("Corte IDH. Caso Prueba"), f"firmas: {fi.texto.tolist()}")
check(not re_.texto.str.contains("Corte IDH").any(), "las firmas quedaron pegadas al último resolutivo")
filas["es_portada"] = G["marcar_portada"](filas)
check(filas.loc[filas.es_portada, "orden"].max() < cu[cu.num_parrafo == 1].orden.iloc[0]
      and not filas.loc[filas.texto.str.contains("Texto del párrafo"), "es_portada"].any(), "portada mal marcada")
t_rot = G["limpiar_texto"]("1. Uno.\nA.1. Derecho a la vida\nD.1.1. Subtítulo\nla Corte.15 dijo", 1)[0]
check("A.1." in t_rot and "D.1.1." in t_rot and "Corte.15" not in t_rot, f"rótulos con número: {t_rot!r}")
_, _, bl = G["limpiar_texto"]("1. Uno.\nIX\nPUNTOS RESOLUTIVOS\nLA CORTE DECLARA,\n1. El Estado es responsable.", 1)
check(any(pa == "resolutivos" and not t and "responsable" in x for pa, t, x in bl), f"título de resolutivos unido: {bl}")
# formato antiguo: sin título "PUNTOS RESOLUTIVOS"; firmas "Redactada en castellano"
_, _, bl = G["limpiar_texto"]("1. Uno.\n2. Dos.\nPor tanto,\nLA CORTE,\nDECIDE:\npor unanimidad,\n1. Desestimar la excepción.\n"
                              "Redactada en castellano y en inglés.\nHéctor Fix-Zamudio", 1)
partes = {x[:12]: pa for pa, _, x in bl}
check(partes.get("2. Dos. Por ") == "cuerpo" and any(pa == "resolutivos" and "Desestimar" in x for pa, _, x in bl)
      and any(pa == "firmas" and "castellano" in x for pa, _, x in bl), f"formato antiguo: {bl}")
# índice: sus entradas no abren la parte resolutivos, con o sin puntos guía
for indice in ("1. Admisión de la prueba ........ 8\nXI. PUNTOS RESOLUTIVOS .......... 85\n",
               "1. Restitución 2. Satisfacción\nVIII. PUNTOS RESOLUTIVOS\n"):
    _, _, bl = G["limpiar_texto"](indice + "I. INTRODUCCIÓN DE LA CAUSA\n1. El caso.\n2. Hechos.\nXI. PUNTOS RESOLUTIVOS\n1. Declara.", 1)
    check([x for pa, _, x in bl if pa == "resolutivos" and x.startswith("1.")] == ["1. Declara."]
          and any(pa == "cuerpo" and x == "2. Hechos." for pa, _, x in bl), f"índice: {bl}")
print("stats:", {k: stats[k] for k in ("inicio_resolutivos", "inicio_voto", "titulos", "parrafos_numerados")})

# ── 4. Normalización ──
norm = G["normalizar"]("El Estado violó el artículo 8.1 y los artículos 25 y 63.1 de la Convención Americana; "
                       "la Corte lo declaró sin dudas. Art. 4 también.")
print("normalizado:", norm)
for t in ("estado", "art_8_1", "art_25", "art_63_1", "art_4", "sin", "convención"):
    check(t in norm.split(), f"falta {t!r}")
check("él" not in norm.split(), "pronombre 'él' no filtrado")
lote = G["normalizar_lote"](["La Corte declaró.", "El Estado es parte."])
check(lote[1][:1] == ["estado"] and "parte" in lote[1], f"lote: {lote}")

# Hipótesis de la revisión: ¿el modelo sm convierte "Estado"/"Corte" en "estar"/"cortar"?
nlp = G["nlp"]
for frase in ["El Estado ha estado ausente.", "ESTADO DE GUATEMALA", "La Corte considera que el Estado violó.",
              "CORTE INTERAMERICANA DE DERECHOS HUMANOS", "CASO VELÁSQUEZ RODRÍGUEZ VS. HONDURAS"]:
    print(f"{frase!r:45} ->", [(t.text, t.lemma_, t.pos_) for t in nlp(frase) if t.is_alpha])

# ── 5. Chunks ──
parr = filas.assign(vid="d1", caso_id="caso prueba vs país", titulo="caso prueba vs. país", estado="país", anio=2024.0,
                    tipo_documento="sentencia", tipo_sentencia="fondo", es_portada=filas.seccion.eq("ENCABEZADO"))
parr["texto_normalizado"] = [" ".join(l) for l in G["normalizar_lote"](parr.texto)]
largo = " ".join(f"Oración número {i} del párrafo largo con contenido jurídico." for i in range(60))
parr.loc[parr.num_parrafo.eq(500) & parr.parte.eq("cuerpo"), "texto"] = largo
rag = parr[~parr.es_portada & parr.parte.ne("voto")].sort_values("orden")
ch = G["construir_chunks"](rag)
check(not ch.texto_con_contexto.str.contains("Caso caso").any(), "cabecera duplicada 'Caso caso'")
check(ch.chunk_id.iloc[0].endswith("_chunk_0000") and ch.chunk_id.is_unique, "chunk_id")
rc = ch[ch.parte == "resolutivos"]
check(len(rc) == 1 and "· puntos 1–2" in rc.texto_con_contexto.iloc[0], f"cabecera resolutivos: {rc.texto_con_contexto.tolist()}")
check(ch.parte.ne("voto").all() and not ch.texto.str.contains("Tabla de Contenido").any(), "voto o portada en el índice")
check(ch.tipo_chunk.eq("parrafo_largo").sum() >= 2 and ch.num_palabras.max() <= 290, "división de párrafos largos")
print("cabeceras:", ch.texto_con_contexto.str.split("\n").str[0].iloc[[0, -2, -1]].tolist())

# ── 6. Artículos declarados violados ──
for marca in ["def articulos_violados(textos):", "UMBRAL_CASI_DUPLICADO = ", "def rrf(*rankings"]:
    cargar(marca)
av = G["articulos_violados"]
check(av(["El Estado es responsable por la violación de los derechos reconocidos en los artículos 8.1 y 25.1 de la "
          "Convención Americana sobre Derechos Humanos, en relación con el artículo 1.1 del mismo instrumento."]) == [8, 25],
      "lista con 'y' y omisión de 1.1")
check(av(["Declara que Honduras ha violado el derecho a la libertad personal reconocido en el artículo 7 de la "
          "Convención, en conexión con el artículo 1.1 de la misma."]) == [7], "formato antiguo 'ha violado ... de la Convención'")
check(av(["El Estado es responsable por la violación del derecho a la libertad personal, reconocido en los artículos "
          "7.3, 7.4 y 7.5, en relación con el artículo 1.1 de la Convención Americana."]) == [7], "tratado nombrado tras 'en relación con'")
check(av(["El Estado no es responsable por la violación de los artículos 8 y 25 de la Convención Americana.",
          "El Estado no violó el artículo 4 de la Convención Americana."]) == [], "negaciones")
check(av(["El Estado es responsable por el incumplimiento de los artículos 1, 6 y 8 de la Convención Interamericana "
          "para Prevenir y Sancionar la Tortura."]) == [], "otro tratado")
check(av(["El Estado debe pagar las cantidades fijadas en el artículo 63.1 de la Convención Americana."]) == [],
      "punto resolutivo sin violación")

# ── 7. Fusión y diversificación ──
idx_rrf, sc_rrf = G["rrf"]([3, 1, 2], [1, 4])
check(idx_rrf[0] == 1 and set(idx_rrf) == {1, 2, 3, 4} and sc_rrf[0] > sc_rrf[1], f"rrf: {idx_rrf}")
import numpy as np
emb = np.eye(4, dtype=np.float32)
emb[1] = emb[0]                                            # 0 y 1 son idénticos (casi duplicados)
G["embeddings"] = emb
G["df_chunks"] = pd.DataFrame({"caso_id": ["a", "b", "a", "c"]})
check(G["diversificar"](np.array([0, 1, 2, 3]), k=3) == [0, 3], "diversificar: un resultado por caso y sin casi duplicados")
check(G["diversificar"](np.array([0, 2, 3]), k=3, max_por_caso=2) == [0, 1, 2], "diversificar: max_por_caso")

# ── 8. Evaluación ──
from pathlib import Path
G["BASE_DIR"] = Path(".")
for marca in ["def recall_at_k(", "def palabras_nombre(titulo):", "def ndcg_at_k(", "def a_documentos(", "def ganancia_cuadernillos("]:
    cargar(marca)
ndcg = G["ndcg_at_k"]
check(abs(ndcg(["a", "b"], {"a": 2, "b": 1}) - 1) < 1e-9, "nDCG del orden ideal = 1")
check(abs(ndcg(["b", "a"], {"a": 2, "b": 1}) - (1 + 2 / np.log2(3)) / (2 + 1 / np.log2(3))) < 1e-9, "nDCG con el orden invertido")
check(ndcg(["x", "y"], {"a": 2}) == 0 and ndcg(["x"], {}) == 0, "nDCG sin relevantes recuperados / sin juicios")
check(G["metricas"](["x", "a"], {"a": 1})["MRR@10"] == 0.5, "MRR@10 en la segunda posición")
check(G["palabras_nombre"]("caso masacres de ituango vs. colombia") == {"ituango"}, "palabras propias del caso")
check(G["oraciones_consulta"]("RESUMEN OFICIAL. " + "La Corte analizó la falta de investigación de los hechos y la "
                              "impunidad que persiste muchos años después. El caso Ituango trata de una masacre ocurrida "
                              "en el municipio y de sus consecuencias para la población.", "caso masacres de ituango vs. colombia")
      == ["La Corte analizó la falta de investigación de los hechos y la impunidad que persiste muchos años después."],
      "oraciones de consulta: sin las que nombran el caso")
check(G["a_documentos"](np.array([0, 1, 2, 3]), np.array(["d1", "d1", "d2", "d3"], dtype=object), k=2) == ["d1", "d2"],
      "colapso de chunks a documentos")
G["qrels_cuad"] = pd.DataFrame({"consulta_id": ["C1", "C1", "C1"], "doc_id": ["d1", "d1", "d2"],
                                "num_parrafo": [5, 6, 9], "relevancia": [2, 1, 1]})
ch = pd.DataFrame({"doc_id": ["d1", "d1", "d2", "d2"], "parte": ["cuerpo", "cuerpo", "resolutivos", "cuerpo"],
                   "parr_ini": [1, 5, 9, 9], "parr_fin": [4, 7, 9, 9]})
check(G["ganancia_cuadernillos"](ch) == {"C1": {1: 2, 3: 1}},
      "párrafos citados -> chunks: mayor grado del chunk y solo partes del cuerpo")
print(f"\nOK: {ok} comprobaciones")

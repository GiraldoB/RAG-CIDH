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

# ── 3. Segmentación: cuerpo, resolutivos y votos ──
lineas = ["CORTE INTERAMERICANA DE DERECHOS HUMANOS", "CASO PRUEBA VS. PAÍS", "Tabla de Contenido",
          "I INTRODUCCIÓN DE LA CAUSA", "XII. PUNTOS RESOLUTIVOS",        # índice: no debe cambiar de parte
          "I", "INTRODUCCIÓN DE LA CAUSA", "1.", "El caso sometido a la Corte misma1 del párrafo uno.",
          "2. Segundo párrafo (LIBERTAD)77, sigue el texto."]
lineas += [f"{n}. Texto del párrafo {n} con varias palabras de relleno." for n in range(3, 1002)]
lineas += ["XII", "PUNTOS RESOLUTIVOS", "1002. Por tanto,", "LA CORTE", "DECLARA,", "Por unanimidad, que:",
           "1. El Estado es responsable por la violación del artículo 13 de la Convención.",
           "2. El Estado es responsable por la violación del artículo 8.1.",
           "Redactada en español en San José, Costa Rica.",
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
print(f"\nOK: {ok} comprobaciones")

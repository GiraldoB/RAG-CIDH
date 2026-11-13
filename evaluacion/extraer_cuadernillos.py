"""Juicios de relevancia por párrafo a partir de los Cuadernillos de Jurisprudencia de la Corte IDH.

Cada cuadernillo se organiza por subtemas (títulos en negrita). Bajo cada subtema cita una sentencia
("Corte IDH. Caso X Vs. Y. ... Sentencia de 2 de julio de 2004. Serie C No. 107.") y transcribe párrafos
numerados de ella; dentro de esos párrafos remite a otros equivalentes ("En similar sentido, ver entre otros:
Caso Z ... Sentencia de ... Serie C No. 111, párr. 82"). El subtema es la consulta; los párrafos transcritos
son relevantes con grado 2 y los "en similar sentido", con grado 1. Las sentencias se emparejan con el
corpus por fecha y nombre del caso (el corpus no guarda el número de Serie C).

Uso (desde la carpeta del proyecto):
    python evaluacion/extraer_cuadernillos.py cuadernillos procesado/corpus_limpio.parquet
Escribe evaluacion/consultas_cuadernillos.csv y evaluacion/qrels_cuadernillos.csv (por párrafo:
doc_id + num_parrafo; el notebook los lleva a chunks).
"""
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import pymupdf

MESES = "enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre"
RE_CITA = re.compile(rf"Caso (?P<caso>.+?)\.\s.*?Sentencia de (?P<fecha>\d{{1,2}} de (?:{MESES}) de \d{{4}})\.?\s*"
                     rf"Serie C No\.\s*(?P<serie>\d+)", re.S)
RE_SIMILAR = re.compile(rf"Caso (?P<caso>[^;()]+?)\.\s[^;()]*?Sentencia de (?P<fecha>\d{{1,2}} de (?:{MESES}) de \d{{4}})"
                        rf"\.\s*Serie C No\.\s*(?P<serie>\d+),\s*párrs?\.\s*(?P<parrs>[\d\s,y–\-a]+)")
RE_PARRAFO = re.compile(r"^(\d{1,4})\.(?!\d)")                 # "111.Asimismo" sin espacio en algunos cuadernillos
RE_OTRA_FUENTE = re.compile(r"Resoluci[óo]n|Opini[óo]n Consultiva|Corte Interamericana|Corte IDH")
# Renglones en negrita que no son títulos: restos de citas y de referencias "en similar sentido"
RE_NO_TITULO = re.compile(r"párr|Serie [AC] No|Sentencia de|Corte IDH|Corte Interamericana|Resoluci[óo]n|Opini[óo]n Consultiva"
                          r"|\bVs\.|^[\W\d]|\d{4}\.?\s*$|Humanos\)?\s+de|^Derechos Humanos y|^Convención Americana sobre Derechos Humanos,")
BOLD = 16
MIN_CUERPO = 9.5          # texto del cuerpo: 10 pt; citas internas 9 pt; notas al pie y superíndices < 8 pt


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def palabras_caso(s):
    s = sin_tildes(s.split(" vs")[0])
    return {w for w in re.findall(r"\w+", s) if len(w) >= 3 and w not in {"caso", "otros", "otras", "del", "los", "las"}}


def lista_parrafos(s):
    """'82, 85 y 90-92' -> [82, 85, 90, 91, 92]"""
    out = []
    for a, b in re.findall(r"(\d+)(?:\s*[–\-a]\s*(\d+))?", s):
        a = int(a)
        out.extend(range(a, int(b) + 1) if b and 0 < int(b) - a <= 20 else [a])
    return out


def renglones(pdf):
    """(texto, es_negrita, tamaño) por renglón, sin superíndices, notas al pie ni encabezados de página."""
    for pagina in pymupdf.open(pdf):
        alto = pagina.rect.height
        for b in pagina.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                sp = [s for s in l["spans"] if s["text"].strip() and s["size"] >= 8.5]
                if not sp or l["bbox"][1] < 0.09 * alto:          # encabezado: número, título del cuadernillo
                    continue
                texto = sp[0]["text"]
                for a, b in zip(sp, sp[1:]):                       # algunos PDF separan palabras solo por posición
                    hueco = b["bbox"][0] - a["bbox"][2] > 1 and not (a["text"][-1:].isspace() or b["text"][:1].isspace())
                    texto += (" " if hueco else "") + b["text"]
                texto = texto.strip()
                yield texto, all(s["flags"] & BOLD for s in sp), max(s["size"] for s in sp)


def extraer(pdf):
    """Filas (subtema, capitulo, caso, fecha, serie, parrafo, grado)."""
    filas, capitulo, subtema, ultimo_titulo = [], None, None, None
    en_cita, actual, parr, texto_parr = "", None, None, ""

    def cerrar_parrafo():
        if actual and parr is not None and subtema:
            filas.append((subtema, capitulo, *actual, parr, 2))
            for m in RE_SIMILAR.finditer(re.sub(r"\s+", " ", texto_parr)):
                for p in lista_parrafos(m["parrs"]):
                    filas.append((subtema, capitulo, m["caso"], m["fecha"], int(m["serie"]), p, 1))

    for texto, negrita, tam in renglones(pdf):
        if texto.isdigit():                                      # número de página o del cuadernillo
            continue
        if en_cita:                                              # cabecera "Corte IDH. Caso ..." en curso
            en_cita += " " + texto
            m = RE_CITA.search(en_cita)
            if m or re.search(r"Serie [AC] No\.\s*\d+|Resoluci[óo]n|Opini[óo]n Consultiva", en_cita) and en_cita.rstrip().endswith("."):
                actual = (m["caso"], m["fecha"], int(m["serie"])) if m else None
                en_cita, parr, texto_parr = "", None, ""
            continue
        if tam >= 11.5:
            if negrita and re.match(r"[IVXL]+\.\s", texto):        # capítulo: "I. ASPECTOS GENERALES"
                cerrar_parrafo()
                capitulo, subtema, ultimo_titulo, actual, parr = texto.split(".", 1)[1].strip().capitalize(), None, None, None, None
            continue                                             # portada
        if negrita and tam >= MIN_CUERPO and re.match(r"(?:Corte IDH\.\s*)?Caso\s", texto):
            cerrar_parrafo()
            parr, texto_parr, ultimo_titulo, en_cita = None, "", None, texto
            m = RE_CITA.search(en_cita)
            if m:
                actual, en_cita = (m["caso"], m["fecha"], int(m["serie"])), ""
            continue
        negrita_cuerpo = negrita and tam >= MIN_CUERPO
        if negrita_cuerpo and ultimo_titulo and len(ultimo_titulo) >= 60 and not RE_NO_TITULO.search(texto):
            subtema += " " + texto                                # segundo renglón del título (puede ir en minúscula)
            ultimo_titulo = texto
            continue
        fin_frase = parr is None or re.search(r"[.)\]”\"…:]\s*$", texto_parr)
        if negrita_cuerpo and fin_frase and RE_OTRA_FUENTE.search(texto) and not texto.startswith("(") and "párr" not in texto:
            cerrar_parrafo()                                      # cita de una resolución u opinión consultiva: no es del corpus
            actual, parr, texto_parr, ultimo_titulo = None, None, "", None
            continue
        if negrita_cuerpo and fin_frase and not texto[0].islower() and not RE_NO_TITULO.search(texto):
            cerrar_parrafo()
            parr, texto_parr, actual = None, "", None
            if ultimo_titulo and len(ultimo_titulo) >= 60:        # título en dos renglones
                subtema += " " + texto
            elif ultimo_titulo:                                   # subtítulo bajo un título corto: "Vida: Deber de ..."
                subtema += ": " + texto
            else:
                subtema = texto
            ultimo_titulo = texto
            continue
        ultimo_titulo = None
        m = RE_PARRAFO.match(texto)
        if m and tam >= MIN_CUERPO and not negrita:
            cerrar_parrafo()
            parr, texto_parr = int(m[1]), texto
        elif parr is not None:
            texto_parr += " " + texto
    cerrar_parrafo()
    return filas


def emparejar(pares, corpus):
    """(caso, fecha) del cuadernillo -> doc_id del corpus: misma fecha y nombre del caso parecido."""
    sent = corpus[corpus["tipo_documento"].eq("sentencia")].copy()
    sent["fecha_n"] = sent["fecha"].fillna("").map(sin_tildes).str.replace(r"^0", "", regex=True).str.replace("setiembre", "septiembre")
    por_fecha = {f: g for f, g in sent.groupby("fecha_n")}
    cache = {}
    for caso, fecha in pares:
        f = sin_tildes(fecha).replace("setiembre", "septiembre")
        mejor, puntaje = None, 0.0
        candidatas = por_fecha.get(f, pd.DataFrame())
        if len(candidatas) == 1 and len(palabras_caso(caso)) <= 1:   # casos con iniciales ("I.V.", "J."): basta la fecha
            cache[caso, fecha] = candidatas["doc_id"].iloc[0]
            continue
        for r in candidatas.itertuples():
            a, b = palabras_caso(caso), palabras_caso(str(r.titulo))
            j = len(a & b) / max(1, len(a | b))
            if j > puntaje:
                mejor, puntaje = r.doc_id, j
        cache[caso, fecha] = mejor if puntaje >= 0.34 else None
    return cache


def tema(pdf):
    """'Cuadernillo ... No. 6 : Desaparición forzada / Corte ...' -> 'Desaparición forzada'"""
    texto = re.sub(r"\s+", " ", pymupdf.open(pdf)[1].get_text())
    t = re.search(r"No\.\s*\d+\s*:\s*(.+?)\s*/", texto)[1]
    return t[:1].upper() + t[1:].lower()


def main(dir_pdf, ruta_corpus, salida=Path(__file__).parent):
    corpus = pd.read_parquet(ruta_corpus, columns=["doc_id", "titulo", "fecha", "tipo_documento"])
    filas = []
    for pdf in sorted(Path(dir_pdf).glob("*.pdf")):
        t = tema(pdf)
        filas += [(pdf.stem, t, *f) for f in extraer(pdf)]
        print(f"{pdf.name} ({t}): {sum(1 for f in filas if f[0] == pdf.stem)} citas")
    df = pd.DataFrame(filas, columns=["cuadernillo", "tema", "subtema", "capitulo", "caso", "fecha", "serie_c", "num_parrafo", "relevancia"])
    cache = emparejar(set(zip(df["caso"], df["fecha"])), corpus)
    df["doc_id"] = [cache[c, f] for c, f in zip(df["caso"], df["fecha"])]
    print(f"Citas: {len(df)}; con sentencia en el corpus: {df['doc_id'].notna().mean():.1%}")
    df = (df.dropna(subset=["doc_id"])
            .sort_values("relevancia", ascending=False, kind="stable")
            .drop_duplicates(["tema", "subtema", "doc_id", "num_parrafo"]))

    # Una consulta por subtema con al menos un párrafo transcrito (grado 2)
    df = df[df.groupby(["tema", "subtema"])["relevancia"].transform("max").eq(2)]
    consultas = df.drop_duplicates(["tema", "subtema"])[["cuadernillo", "tema", "subtema"]].reset_index(drop=True)
    consultas.insert(0, "consulta_id", [f"C{i + 1:03d}" for i in range(len(consultas))])
    consultas["consulta"] = consultas["tema"] + ": " + consultas["subtema"]
    qrels = df.merge(consultas[["consulta_id", "tema", "subtema"]], on=["tema", "subtema"])
    qrels = qrels[["consulta_id", "doc_id", "num_parrafo", "relevancia", "caso", "serie_c"]].sort_values(["consulta_id", "doc_id", "num_parrafo"])
    consultas.to_csv(salida / "consultas_cuadernillos.csv", index=False, encoding="utf-8")
    qrels.to_csv(salida / "qrels_cuadernillos.csv", index=False, encoding="utf-8")
    print(f"{len(consultas)} consultas, {len(qrels)} juicios {qrels['relevancia'].value_counts().sort_index().to_dict()}, "
          f"{qrels['doc_id'].nunique()} sentencias")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:3])

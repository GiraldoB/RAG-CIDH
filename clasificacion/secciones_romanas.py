"""Etiquetas de referencia para los chunks «Sin sección» (prueba de la Tarea 2), a partir de las secciones romanas del PDF.

Uso:  python clasificacion/secciones_romanas.py
Lee de CORTEIDH_BASE y escribe en procesado/clasificacion/secciones_romanas/:
  secciones.csv          una fila por sección romana: título, párrafo inicial y final, etiqueta automática si el título la dice
  textos/<doc>__<n>.md   texto de cada sección sin etiqueta, para que un LLM (DeepSeek en opencode) la lea entera
  respuestas.jsonl       (lo escribe el LLM) una línea JSON por sección: {"archivo", "seccion", "confianza", "evidencia"}
  revision.xlsx          tabla para verificar a mano la etiqueta de cada sección (se regenera al correr de nuevo)
  chunks_etiquetados.csv los chunks «Sin sección» con la etiqueta de su sección (automática, LLM, corrección o manual)
Prioridad de la etiqueta: revisión manual > clasificacion/secciones_correcciones.csv > título del PDF > LLM.

Por qué: el notebook solo reconoce títulos «VI. HECHOS». Las sentencias antiguas traen el número romano solo («VI»)
y algunas modernas usan guion («VI – HECHOS», Norín Catrimán). Se etiqueta la sección entera y no el párrafo,
porque leída completa es más fácil distinguir Hechos (lo que se probó que pasó) de Fondo (el análisis de la Corte).
"""
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
import pymupdf

BASE = Path(os.environ.get("CORTEIDH_BASE", ".")).resolve()
SALIDA = BASE / "procesado/clasificacion/secciones_romanas"
CORRECCIONES = Path(__file__).resolve().parent / "secciones_correcciones.csv"   # en git: correcciones acordadas a la etiqueta del LLM
MAX_PALABRAS_LLM = 6000      # secciones más largas se recortan: inicio y final (el título y la conclusión deciden)

ROMANOS = {"I": 1, "V": 5, "X": 10, "L": 50}
RE_ROMANO_SOLO = re.compile(r"([IVXL]{1,6})\.{0,2}")      # «II..» en Cuscul Pivaral
RE_ROMANO_TITULO = re.compile(r"([IVXL]{1,6})\s*[.\-–—]\s*([A-ZÁÉÍÓÚÑ\"(].*)")   # «VI – HECHOS», «I -INTRODUCCIÓN», «IV. FONDO»
RE_INDICE = re.compile(r"\.{4,}|…{2,}|\s\d{1,3}$")
RE_PARRAFO = re.compile(r"(\d{1,4})\.(?:\s|$)")
RE_DISPOSITIVA = re.compile(r"(?:POR TANTO[,:]?\s*)?LA\s+CORTE,?(?:\s+(?:DECIDE|RESUELVE|DECLARA)[:,]?)?|PUNTOS RESOLUTIVOS.*|"
                            r"(?:DECIDE|RESUELVE|DECLARA)[:,]?|POR TANTO[,:]?")
RE_RESOLUCION = re.compile(r"VISTOS?:")    # resoluciones (interpretación, supervisión): VISTOS / CONSIDERANDO / RESUELVE
RE_VOTO = re.compile(r"VOTO\s+(?:PARCIALMENTE\s+)?(?:CONCURRENTE|RAZONADO|DISIDENTE|CONJUNTO|INDIVIDUAL|SEPARADO|SALVADO)")

# Las mismas reglas que canon_seccion() del notebook (proyecto_corregido.ipynb, punto 2), en el mismo orden
# «Otra» suma lo que el notebook deja en «Otras» y no es clase de la Tarea 2 (admisibilidad, reconocimiento de responsabilidad…)
REGLAS = [("Puntos resolutivos", "^PUNTOS RESOLUTIVOS"),
          ("Otra", "INTRODUCCI|PROCEDIMIENTO|COMPETENCIA|CONSIDERACI[OÓ]N(?:ES)? PREVIA|ADMISIBILIDAD|RECONOCIMIENTO|"
                   "MEDIDAS PROVISIONALES"), ("Excepciones preliminares", "EXCEPCI"),
          ("Prueba", "PRUEBA"), ("Hechos", "HECHOS"), ("Fondo", "FONDO|DERECHO"), ("Reparaciones", "REPARACI"),
          ("Puntos resolutivos", "PUNTOS RESOLUTIVOS|POR (?:LO )?TANTO")]
RE_POR_TANTO = re.compile(r"\S+\s+(?:\d{1,4}\.\s+)?Por (?:lo )?tanto", re.IGNORECASE)
ETIQUETAS = ["Excepciones preliminares", "Hechos", "Prueba", "Fondo", "Reparaciones", "Puntos resolutivos", "Otra"]


def romano(s):
    v = [ROMANOS[c] for c in s]
    return sum(-a if a < b else a for a, b in zip(v, v[1:] + [0]))


def etiqueta_por_titulo(t):
    # solo el comienzo: «Sobre los criterios … para determinar hechos» (interpretación) no es la sección Hechos
    t = t.upper()
    return next((n for n, p in REGLAS if re.match(p, t)), None)


def lineas_pdf(ruta):
    with pymupdf.open(ruta) as doc:
        return [l.strip() for pag in doc for l in pag.get_text().split("\n") if l.strip()]


def secciones_de(lineas):
    """Encabezados romanos de primer nivel en orden I, II, III…
    Cada «I» abre una secuencia candidata (las citas también traen «I.»); gana la más larga. El primer voto cierra."""
    candidatas, voto = [], len(lineas)
    for i, l in enumerate(lineas):
        if RE_VOTO.match(l) and l.isupper():
            voto = i; break                                                # desde el primer voto ya no es la sentencia
        m = RE_ROMANO_SOLO.fullmatch(l)
        titulo = ""
        if m and i + 1 < len(lineas):
            sig = lineas[i + 1]
            if RE_INDICE.search(sig):
                continue                                                   # entrada del índice («I» + «INTRODUCCIÓN ....»)
            if sig.isupper() or (sig[:1].isupper() and len(sig) < 100 and not RE_PARRAFO.match(sig)
                                 and not sig.endswith((".", ",", ";"))):
                titulo = sig                      # «I.» + «INTRODUCCIÓN» o «Puntos Resolutivos» en la línea siguiente
        if not m:
            m = RE_ROMANO_TITULO.fullmatch(l)
            if not m or not m.group(2).upper() == m.group(2) or RE_INDICE.search(l):
                continue
            titulo = m.group(2)
        n = romano(m.group(1))
        if n == 1:
            candidatas.append([])
        for c in candidatas:
            if len(c) == n - 1:
                c.append((i, n, m.group(1), titulo))
    cab = max(candidatas, key=len, default=[])   # en empate, la primera: un «I.» citado después hereda los II, III… reales
    if voto < len(lineas):
        cab.append((voto, None, "VOTO", lineas[voto]))
    return sorted(cab)


def primer_parrafo(lineas, ini, fin):
    for l in lineas[ini + 1:fin]:
        m = RE_PARRAFO.match(l)
        if m:
            return int(m.group(1))
    return None


def main():
    ch = pd.read_parquet(BASE / "procesado/caracteristicas/chunks.parquet",
                         columns=["doc_id", "chunk_id", "vid", "titulo", "anio", "tipo_sentencia", "parte", "parr_ini",
                                  "parr_fin", "num_palabras", "seccion_canonica", "texto"])
    sin = ch[ch["seccion_canonica"].eq("Sin sección")]
    filas = []
    (SALIDA / "textos").mkdir(parents=True, exist_ok=True)
    for f in (SALIDA / "textos").glob("*.md"):
        f.unlink()                                  # se regeneran todos: no quedan textos de una corrida anterior
    for doc_id, g in sin.groupby("doc_id"):
        vid = doc_id.split("_")[0]
        lineas = lineas_pdf(BASE / "casos" / vid / f"{vid}.pdf")
        cab = secciones_de(lineas)
        meta = g.iloc[0]
        if not [c for c in cab if c[1]]:
            if any(RE_RESOLUCION.fullmatch(l) for l in lineas[:40]):
                # cada bloque reinicia la numeración en 1: no se ubica el chunk por párrafo. Toda la resolución es «Otra».
                filas.append(dict(doc_id=doc_id, caso=meta.titulo, anio=meta.anio, tipo_sentencia=meta.tipo_sentencia,
                                  romano="RES", n=0, titulo_seccion="RESOLUCIÓN (VISTOS / CONSIDERANDO / RESUELVE)",
                                  parr_ini=0, palabras=sum(len(l.split()) for l in lineas), etiqueta_auto="Otra",
                                  archivo=f"{doc_id}__00.md", inicio=" ".join(" ".join(lineas[:30]).split()[:60])))
            continue
        primero = next(c for c in cab if c[1])
        p0, p1 = primer_parrafo(lineas, -1, primero[0]), primer_parrafo(lineas, primero[0], len(lineas))
        if p0 is not None and p1 is not None and p0 < p1:     # en las modernas, «1.» del índice no cuenta
            cab.insert(0, (-1, 0, "0", ""))      # párrafos numerados antes de la sección I (preámbulo de las antiguas)
        for k, (i, n, rom, titulo) in enumerate(cab):
            if rom in ("VOTO", "DISP"):
                continue
            fin = cab[k + 1][0] if k + 1 < len(cab) else len(lineas)
            p_ini = primer_parrafo(lineas, i, fin)
            texto = "\n".join(lineas[max(i, 0):fin])
            auto = etiqueta_por_titulo(titulo) if titulo else None
            if auto is None and RE_POR_TANTO.match(" ".join(texto.split()[:6])):
                auto = "Puntos resolutivos"         # antiguas: «VI» + «53. Por tanto,» (el notebook solo ve «POR TANTO:»)
            archivo = f"{doc_id}__{n:02d}.md"
            filas.append(dict(doc_id=doc_id, caso=meta.titulo, anio=meta.anio, tipo_sentencia=meta.tipo_sentencia,
                              romano=rom, n=n, titulo_seccion=titulo, parr_ini=p_ini, palabras=len(texto.split()),
                              etiqueta_auto=auto, archivo=archivo, inicio=" ".join(texto.split()[:60])))
            if auto is None:
                pal = texto.split()
                if len(pal) > MAX_PALABRAS_LLM:
                    mitad = MAX_PALABRAS_LLM // 2
                    texto = " ".join(pal[:mitad]) + "\n\n[… se omite la parte central de la sección …]\n\n" + " ".join(pal[-mitad:])
                (SALIDA / "textos" / archivo).write_text(
                    f"# {meta.titulo} ({int(meta.anio)}) · sentencia de {meta.tipo_sentencia} · sección {rom}\n\n{texto}\n",
                    encoding="utf-8")
    sec = pd.DataFrame(filas)
    # párrafo final = el anterior al inicio de la sección siguiente (vacío si ahí la numeración vuelve a 1)
    sig = sec.groupby("doc_id")["parr_ini"].shift(-1)
    sec["parr_fin"] = (sig - 1).where(sig > sec["parr_ini"])
    sec.to_csv(SALIDA / "secciones.csv", index=False, encoding="utf-8-sig")
    aplicar(sin, sec)


def etiqueta_final(sec):
    """Prioridad: revisión manual > secciones_correcciones.csv > título del PDF > LLM."""
    sec = sec.copy()
    sec["etiqueta_llm"] = None
    r = SALIDA / "respuestas.jsonl"
    if r.exists():
        llm = {}
        for l in r.read_text(encoding="utf-8").splitlines():
            if l.strip():
                j = json.loads(l)
                if j.get("seccion") not in ETIQUETAS:
                    print(f"respuestas.jsonl: etiqueta no válida {j.get('seccion')!r} en {j.get('archivo')}; se ignora")
                    continue
                llm[j["archivo"]] = j                    # si un archivo se respondió dos veces, vale la última
        sec["etiqueta_llm"] = sec["archivo"].map(lambda a: llm.get(a, {}).get("seccion"))
        sec["confianza_llm"] = sec["archivo"].map(lambda a: llm.get(a, {}).get("confianza"))
        sec["evidencia_llm"] = sec["archivo"].map(lambda a: llm.get(a, {}).get("evidencia"))
    sec["etiqueta_manual"] = None
    rev = SALIDA / "revision.xlsx"
    if rev.exists():
        m = pd.read_excel(rev).set_index("archivo")["✎ Etiqueta correcta"]
        sec["etiqueta_manual"] = sec["archivo"].map(m.dropna())
    cor = pd.read_csv(CORRECCIONES).set_index("archivo") if CORRECCIONES.exists() else pd.DataFrame(columns=["etiqueta", "motivo"])
    assert cor["etiqueta"].isin(ETIQUETAS).all(), f"{CORRECCIONES.name}: etiqueta no válida"
    sec["etiqueta_correccion"] = sec["archivo"].map(cor["etiqueta"])
    sec["motivo_correccion"] = sec["archivo"].map(cor["motivo"])
    sec["etiqueta"], sec["origen"] = None, None
    for col, origen in [("etiqueta_llm", "llm"), ("etiqueta_auto", "título"), ("etiqueta_correccion", "corrección"),
                        ("etiqueta_manual", "manual")]:          # de menor a mayor prioridad
        hay = sec[col].notna()
        sec.loc[hay, "etiqueta"], sec.loc[hay, "origen"] = sec.loc[hay, col], origen
    return sec


def aplicar(sin, sec):
    sec = etiqueta_final(sec)
    asign = []
    for doc_id, g in sin.sort_values("chunk_id").groupby("doc_id"):     # chunk_id sigue el orden del documento
        d = sec[(sec["doc_id"] == doc_id) & sec["parr_ini"].notna()].sort_values("n").reset_index(drop=True)
        k, previo = 0, -1
        for c in g.itertuples():
            # se avanza de sección cuando el chunk llega al primer párrafo de la siguiente, o cuando la numeración
            # vuelve a empezar (la parte resolutiva reinicia en 1) y la siguiente sección es justamente la que reinicia
            while k + 1 < len(d) and (
                    (d.at[k + 1, "parr_ini"] > d.at[k, "parr_ini"] and c.parr_ini >= d.at[k + 1, "parr_ini"])
                    or (d.at[k + 1, "parr_ini"] <= d.at[k, "parr_ini"] and c.parr_ini < previo)):
                k += 1
            previo = c.parr_ini
            s = d.iloc[k] if len(d) else None
            cruza = s is not None and pd.notna(s["parr_fin"]) and c.parr_fin > s["parr_fin"]
            antes = s is not None and k == 0 and c.parr_ini < s["parr_ini"]
            asign.append(dict(chunk_id=c.chunk_id, doc_id=doc_id, parr_ini=c.parr_ini, parr_fin=c.parr_fin,
                              num_palabras=c.num_palabras,
                              seccion_romana=None if s is None or antes else s["romano"],
                              etiqueta=None if s is None or antes else s["etiqueta"],
                              origen=None if s is None or antes else s["origen"],
                              nota="sin sección ubicada" if s is None or antes else ("cruza dos secciones" if cruza else "")))
    a = pd.DataFrame(asign)
    a.to_csv(SALIDA / "chunks_etiquetados.csv", index=False, encoding="utf-8-sig")
    escribir_revision(sec)
    print(f"Secciones romanas: {len(sec)} en {sec['doc_id'].nunique()} sentencias "
          f"(por título {sec['etiqueta_auto'].notna().sum()}, para el LLM {sec['etiqueta_auto'].isna().sum()}, "
          f"sin párrafo inicial {sec['parr_ini'].isna().sum()})")
    print(f"Secciones sin etiqueta todavía (faltan en respuestas.jsonl): {sec['etiqueta'].isna().sum()}")
    print(f"Chunks «Sin sección»: {len(a)}; con etiqueta {a['etiqueta'].notna().sum()}")
    print(a["etiqueta"].value_counts(dropna=False).to_string())
    print(a["nota"].value_counts().to_string())
    sin_cab = set(sin["doc_id"]) - set(sec["doc_id"])
    if sin_cab:
        print("Sentencias sin números romanos detectados:", sorted(sin_cab))


def escribir_revision(sec):
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    rev = SALIDA / "revision.xlsx"
    previo = pd.read_excel(rev).set_index("archivo") if rev.exists() else None
    cols = ["archivo", "caso", "anio", "tipo_sentencia", "romano", "titulo_seccion", "parr_ini", "parr_fin", "palabras",
            "inicio", "etiqueta_auto", "etiqueta_llm", "confianza_llm", "evidencia_llm", "etiqueta_correccion", "motivo_correccion"]
    t = sec.reindex(columns=cols).copy()
    t["caso"] = t["caso"].str[:1].str.upper() + t["caso"].str[1:]
    for c in ["✎ Etiqueta correcta", "✎ Notas"]:
        t[c] = t["archivo"].map(previo[c]) if previo is not None and c in previo else None
    t.to_excel(rev, index=False)
    from openpyxl import load_workbook
    wb = load_workbook(rev)
    h = wb.active
    anchos = {"archivo": 28, "caso": 32, "titulo_seccion": 30, "inicio": 70, "evidencia_llm": 50, "✎ Notas": 30,
              "✎ Etiqueta correcta": 24}
    for j, c in enumerate(t.columns, start=1):
        letra = h.cell(1, j).column_letter
        h.column_dimensions[letra].width = anchos.get(c, 12)
        h.cell(1, j).font = Font(bold=True)
        if c.startswith("✎"):
            for i in range(1, len(t) + 2):
                h.cell(i, j).fill = PatternFill("solid", fgColor="FFF2CC")
        for i in range(2, len(t) + 2):
            h.cell(i, j).alignment = Alignment(wrap_text=c in ("inicio", "evidencia_llm"), vertical="top")
    j = list(t.columns).index("✎ Etiqueta correcta") + 1
    letra = h.cell(1, j).column_letter
    dv = DataValidation(type="list", formula1='"' + ",".join(ETIQUETAS) + '"', allow_blank=True)
    h.add_data_validation(dv)
    dv.add(f"{letra}2:{letra}{len(t) + 1}")
    h.freeze_panes = "B2"
    h.auto_filter.ref = h.dimensions
    wb.save(rev)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--aplicar":      # tras el LLM o la revisión: solo recalcula etiquetas
        ch = pd.read_parquet(BASE / "procesado/caracteristicas/chunks.parquet",
                             columns=["doc_id", "chunk_id", "parr_ini", "parr_fin", "num_palabras", "seccion_canonica"])
        aplicar(ch[ch["seccion_canonica"].eq("Sin sección")], pd.read_csv(SALIDA / "secciones.csv"))
    else:
        main()

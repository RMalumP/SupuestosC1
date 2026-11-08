# -*- coding: utf-8 -*-
"""
IMPORTAR PREGUNTAS DESDE WORD (.docx)  (sin ventana)
════════════════════════════════════════════════════
Parte del editor de supuestos. Un .docx es un .zip con XML dentro: no hace falta
instalar nada. Se saca el texto de cada párrafo conservando:

  · negrita, cursiva y subrayado  → <b>, <i>, <u>
  · resaltado (rotulador)         → <mark>
  · listas numeradas o con letra  → «1) …», «a) …» (como las ve Word en pantalla)
  · viñetas                       → «•<tab>…» (el editor les pone sangría francesa)

El resultado es el mismo texto que se pegaría en «Importar preguntas», así que lo
lee importar_texto. Con marcar_correcta=True, la opción que está ENTERA en negrita
o resaltada se toma como la correcta (lo habitual en las plantillas de examen).
"""
import re
import zipfile
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
LETRAS = "abcdefghijklmnopqrstuvwxyz"


def _romano(n):
    res = ""
    for v, s in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"),
                 (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            res += s
            n -= v
    return res


def _formatos_de_numeracion(z):
    """{(numId, nivel): (formato, texto del nivel, inicio)} desde word/numbering.xml."""
    try:
        raiz = ET.fromstring(z.read("word/numbering.xml"))
    except (KeyError, ET.ParseError):
        return {}
    abstractos = {}
    for a in raiz.findall(W + "abstractNum"):
        niveles = {}
        for lvl in a.findall(W + "lvl"):
            fmt = lvl.find(W + "numFmt")
            txt = lvl.find(W + "lvlText")
            ini = lvl.find(W + "start")
            niveles[lvl.get(W + "ilvl")] = (fmt.get(W + "val") if fmt is not None else "decimal",
                                            txt.get(W + "val") if txt is not None else "%1.",
                                            int(ini.get(W + "val")) if ini is not None else 1)
        abstractos[a.get(W + "abstractNumId")] = niveles
    res = {}
    for num in raiz.findall(W + "num"):
        abs_id = num.find(W + "abstractNumId")
        if abs_id is None:
            continue
        for nivel, datos in abstractos.get(abs_id.get(W + "val"), {}).items():
            res[(num.get(W + "numId"), nivel)] = datos
    return res


def _activo(rpr, etiqueta):
    e = rpr.find(W + etiqueta) if rpr is not None else None
    if e is None:
        return False
    val = e.get(W + "val")
    return val not in ("0", "false", "none")


def _texto_parrafo(p):
    trozos = []
    for r in p.iter():
        if r.tag != W + "r":
            continue
        rpr = r.find(W + "rPr")
        texto = ""
        for hijo in r:
            if hijo.tag == W + "t":
                texto += hijo.text or ""
            elif hijo.tag == W + "tab":
                texto += "\t"
            elif hijo.tag in (W + "br", W + "cr"):
                texto += "\n"
        if not texto:
            continue
        marcas = [t for t, e in (("b", "b"), ("i", "i"), ("u", "u")) if _activo(rpr, e)]
        if rpr is not None and (rpr.find(W + "highlight") is not None or
                                (rpr.find(W + "shd") is not None and
                                 (rpr.find(W + "shd").get(W + "fill") or "auto").lower() not in ("auto", "ffffff"))):
            marcas.append("mark")
        trozos.append((texto, tuple(marcas)))
    # juntar trozos seguidos con el mismo formato (Word parte las palabras en muchos «runs»)
    juntos = []
    for texto, marcas in trozos:
        if juntos and juntos[-1][1] == marcas:
            juntos[-1] = (juntos[-1][0] + texto, marcas)
        else:
            juntos.append((texto, marcas))
    res = ""
    for texto, marcas in juntos:
        if marcas and texto.strip():
            ini = "".join("<%s>" % m for m in marcas)
            fin = "".join("</%s>" % m for m in reversed(marcas))
            sin_espacio = texto.strip()
            izq = texto[:len(texto) - len(texto.lstrip())]
            der = texto[len(texto.rstrip()):]
            res += izq + ini + sin_espacio + fin + der
        else:
            res += texto
    return res


def texto_de_docx(ruta_o_archivo):
    """Texto plano con marcas de formato, un párrafo por línea (con líneas en blanco
    donde Word las tiene). Las listas automáticas se escriben como se ven."""
    try:
        with zipfile.ZipFile(ruta_o_archivo) as z:
            doc = ET.fromstring(z.read("word/document.xml"))
            formatos = _formatos_de_numeracion(z)
    except (KeyError, zipfile.BadZipFile, ET.ParseError):
        raise ValueError("No parece un documento de Word (.docx). Si es un .doc antiguo, "
                         "ábrelo en Word y guárdalo como .docx.")
    cuerpo = doc.find(W + "body")
    contadores = {}
    lineas = []
    for p in (cuerpo.iter(W + "p") if cuerpo is not None else []):
        texto = _texto_parrafo(p)
        ppr = p.find(W + "pPr")
        num = ppr.find(W + "numPr") if ppr is not None else None
        if num is not None and texto.strip():
            num_id = num.find(W + "numId")
            ilvl = num.find(W + "ilvl")
            clave = (num_id.get(W + "val") if num_id is not None else "0",
                     ilvl.get(W + "val") if ilvl is not None else "0")
            fmt, plantilla, inicio = formatos.get(clave, ("decimal", "%1.", 1))
            if clave[0] == "0":
                pass                                     # numeración quitada a mano
            elif fmt == "bullet":
                texto = "•\t" + texto.lstrip()
            else:
                n = contadores.get(clave, inicio - 1) + 1
                contadores[clave] = n
                # al empezar un nivel, los de dentro vuelven a empezar
                for k in list(contadores):
                    if k[0] == clave[0] and int(k[1]) > int(clave[1]):
                        del contadores[k]
                valor = {"lowerLetter": LETRAS[(n - 1) % 26], "upperLetter": LETRAS[(n - 1) % 26].upper(),
                         "lowerRoman": _romano(n), "upperRoman": _romano(n).upper()}.get(fmt, str(n))
                marca = re.sub(r"%\d", valor, plantilla).strip() or (valor + ".")
                if fmt in ("lowerLetter", "upperLetter") and marca.endswith("."):
                    marca = marca[:-1] + ")"             # «a.» → «a)» para que se lea como opción
                texto = marca + " " + texto.lstrip()
        lineas.append(texto.rstrip())
    salida = "\n".join(lineas)
    return re.sub(r"\n{3,}", "\n\n", salida).strip() + "\n"


RE_OPCION = re.compile(r"^(\s*\(?[a-gA-G][\)\.\-:]\s*)(.*)$")
RE_TODO_MARCADO = re.compile(r"^\s*(?:<(b|mark)>)+(.*?)(?:</(?:b|mark)>)+\s*$")
RE_NUMERO = re.compile(r"^\s*\d+\s*[\)\.\-]\s+")
RE_VACIA = re.compile(r"<(b|i|u|mark)>\s*</\1>")
# «<b>1. ¿Pregunta?</b>» o «<b>a) opción</b>» (la letra o el número escritos a mano, con formato)
RE_MARCA_DENTRO = re.compile(r"^(\s*)((?:<(?:b|i|u|mark)>)+)(\s*\(?(?:\d+|[a-gA-G])\s*[\)\.\-:]\s+)")


def preparar(texto):
    """Deja el texto como lo espera «Importar preguntas»:
    · el número o la letra delante del formato («<b>a) x</b>» → «a) <b>x</b>»);
    · una línea en blanco antes de cada pregunta numerada que va pegada a las
      opciones de la anterior (en Word es habitual no dejar párrafo vacío)."""
    res, hay_opciones = [], False
    for linea in texto.split("\n"):
        linea = RE_VACIA.sub("", RE_MARCA_DENTRO.sub(r"\1\3\2", linea))
        if not linea.strip():
            hay_opciones = False
        elif RE_NUMERO.match(linea) and hay_opciones:
            res.append("")
            hay_opciones = False
        elif RE_OPCION.match(linea):
            hay_opciones = True
        res.append(linea)
    return "\n".join(res)


def marcar_correctas_en_negrita(texto):
    """Las opciones que están ENTERAS en negrita o resaltadas pasan a llevar «*»
    (la marca de correcta de «Importar preguntas») y pierden ese formato. Si en una
    pregunta lo están TODAS, es el estilo del documento y no se marca ninguna."""
    lineas = texto.split("\n")
    opciones, marcadas = 0, []                    # de la pregunta en curso

    def cerrar():
        if marcadas and len(marcadas) < opciones:
            for k, limpio in marcadas:
                lineas[k] = RE_OPCION.match(lineas[k]).group(1) + "*" + limpio
        marcadas.clear()

    for k, linea in enumerate(list(lineas)):
        if not linea.strip() or RE_NUMERO.match(linea):
            cerrar()
            opciones = 0
            continue
        m = RE_OPCION.match(linea)
        if not m:
            continue
        opciones += 1
        t = RE_TODO_MARCADO.match(m.group(2))
        if t and t.group(2).strip():
            marcadas.append((k, re.sub(r"</?(b|mark)>", "", m.group(2)).strip()))
    cerrar()
    return "\n".join(lineas)


def texto_para_importar(ruta_o_archivo, negrita_correcta=True):
    """Lo que se pone en la caja de «Importar preguntas» al abrir un .docx."""
    texto = preparar(texto_de_docx(ruta_o_archivo))
    return marcar_correctas_en_negrita(texto) if negrita_correcta else texto

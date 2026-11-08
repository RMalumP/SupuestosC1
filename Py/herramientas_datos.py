# -*- coding: utf-8 -*-
"""
HERRAMIENTAS SIN VENTANA DEL EDITOR
═══════════════════════════════════
Parte del editor de supuestos. No usa tkinter, así que se prueba sin pantalla.

  Historial       deshacer / rehacer con instantáneas de los datos
  buscar          encuentra texto en preguntas, opciones, motivaciones y consejos
  reemplazar      cambia ese texto en todo el supuesto
  importar_texto  convierte texto pegado («pregunta / a) b) c) d) / correcta») en preguntas
  importar_csv    lo mismo desde un CSV
  problemas_por_pregunta   qué preguntas tienen fallos (para marcarlas en la lista)
  guardar_recuperacion / leer_recuperacion   autoguardado
  errores_graves, duplicados, estadisticas, citas_sin_norma, plantillas   revisión y ayudas
"""
import difflib
import csv
import io
import json
import re
from pathlib import Path

import datos_html
import revision

LETRAS = "ABCDEFG"
CAMPOS = (("q", "pregunta"), ("a", "opción"), ("law", "motivación"), ("tip", "consejo"))


# ── deshacer / rehacer ───────────────────────────────────────────────
class Historial:
    def __init__(self, maximo=60):
        self.maximo = maximo
        self._atras = []
        self._adelante = []
        self._actual = None

    def iniciar(self, datos):
        self._atras, self._adelante = [], []
        self._actual = json.dumps(datos, sort_keys=True)

    def anotar(self, datos):
        """Guarda el estado actual si es distinto del último anotado."""
        ahora = json.dumps(datos, sort_keys=True)
        if ahora == self._actual:
            return False
        if self._actual is not None:
            self._atras.append(self._actual)
            del self._atras[:-self.maximo]
        self._actual = ahora
        self._adelante = []
        return True

    def puede_deshacer(self):
        return bool(self._atras)

    def puede_rehacer(self):
        return bool(self._adelante)

    def deshacer(self, datos):
        """Devuelve los datos anteriores (o None). `datos` es el estado actual."""
        self.anotar(datos)
        if not self._atras:
            return None
        self._adelante.append(self._actual)
        self._actual = self._atras.pop()
        return json.loads(self._actual)

    def rehacer(self):
        if not self._adelante:
            return None
        self._atras.append(self._actual)
        self._actual = self._adelante.pop()
        return json.loads(self._actual)


# ── buscar y reemplazar ──────────────────────────────────────────────
def _patron(texto, sensible):
    return re.compile(re.escape(texto), 0 if sensible else re.IGNORECASE)


LETRAS_OPCION = "ABCDEFG"
RE_TAG = re.compile(r"<[^<>]*>")
RE_PAR_VACIO = re.compile(r"<(b|i|u|s|mark|span|strong|em)\b[^<>]*></\1\s*>", re.I)


def sitios(datos):
    """Todos los textos del supuesto que se pueden buscar: (ruta, dónde, valor).
    ruta: tupla de claves para llegar al texto, p. ej. ("preguntas", 3, "a", 1)."""
    cfg = datos.get("config") or {}
    if isinstance(cfg.get("titulo"), str):
        yield ("config", "titulo"), "Título del supuesto", cfg["titulo"]
    for k, b in enumerate(datos.get("bloques") or []):
        if isinstance(b.get("titulo"), str):
            yield ("bloques", k, "titulo"), "Bloque %s · título" % b.get("id", k + 1), b["titulo"]
    for k, e in enumerate(datos.get("enunciados") or []):
        ide = e.get("id") or "E%d" % (k + 1)
        for campo, nombre in (("title", "título"), ("ambito", "materias"), ("ref", "referencia")):
            if isinstance(e.get(campo), str):
                yield ("enunciados", k, campo), "%s · %s" % (ide, nombre), e[campo]
        for j, h in enumerate(e.get("factBlocks") or []):
            idh = h.get("id") or "H%d" % (j + 1)
            if isinstance(h.get("title"), str):
                yield ("enunciados", k, "factBlocks", j, "title"), "%s · %s · título" % (ide, idh), h["title"]
            for m, par in enumerate(h.get("paragraphs") or []):
                yield ("enunciados", k, "factBlocks", j, "paragraphs", m), \
                    "%s · %s · párrafo %d" % (ide, idh, m + 1), par
        for j, h in enumerate(e.get("timeline") or []):
            for campo, nombre in (("date", "fecha"), ("text", "texto")):
                if isinstance(h.get(campo), str):
                    yield ("enunciados", k, "timeline", j, campo), "%s · hito %d · %s" % (ide, j + 1, nombre), h[campo]
    for n, p in enumerate(datos.get("preguntas") or []):
        yield ("preguntas", n, "q"), "P%d · pregunta" % (n + 1), p.get("q", "")
        for i, t in enumerate(p.get("a", [])):
            yield ("preguntas", n, "a", i), "P%d · opción %s" % (n + 1, LETRAS_OPCION[i % 7]), t
        for campo, nombre in (("law", "motivación"), ("tip", "consejo"), ("tag", "etiqueta")):
            yield ("preguntas", n, campo), "P%d · %s" % (n + 1, nombre), p.get(campo, "")


def poner_en(datos, ruta, valor):
    sitio = datos
    for clave in ruta[:-1]:
        sitio = sitio[clave]
    sitio[ruta[-1]] = valor


def _visible(texto):
    """(texto sin etiquetas HTML, posición en el original de cada letra visible)."""
    vis, pos, i = [], [], 0
    for m in RE_TAG.finditer(texto):
        for k in range(i, m.start()):
            vis.append(texto[k])
            pos.append(k)
        i = m.end()
    for k in range(i, len(texto)):
        vis.append(texto[k])
        pos.append(k)
    return "".join(vis), pos


def _coincidencias(texto, pat):
    """[(inicio, fin) en el texto original] de lo que se ve, aunque haya negritas
    u otras marcas por medio («diez <b>días</b>» se encuentra buscando «diez días»)."""
    vis, pos = _visible(texto or "")
    return [(pos[m.start()], pos[m.end() - 1] + 1) for m in pat.finditer(vis) if m.end() > m.start()]


def buscar(datos, texto, sensible=False):
    """Lista de (n.º de pregunta desde 0 o None, ruta, dónde, fragmento) en TODO el supuesto
    (preguntas, enunciados, hechos, hitos y títulos). Las marcas de formato no estorban."""
    if not texto:
        return []
    pat = _patron(texto, sensible)
    salida = []
    for ruta, donde, valor in sitios(datos):
        trozos = _coincidencias(valor or "", pat)
        if trozos:
            vis = _visible(valor)[0]
            m = pat.search(vis)
            a = max(0, m.start() - 25)
            frag = vis[a:m.end() + 25].replace("\n", " ")
            n = ruta[1] if ruta[0] == "preguntas" else None
            salida.append((n, ruta, donde + (" (×%d)" % len(trozos) if len(trozos) > 1 else ""), frag))
    return salida


def _reemplazar_en(texto, pat, nuevo):
    """Cambia lo visible; las marcas que hubiera dentro de lo cambiado se conservan
    justo detrás del texto nuevo (no se pierde ni se rompe ningún formato)."""
    trozos = _coincidencias(texto, pat)
    for ini, fin in reversed(trozos):
        marcas = "".join(RE_TAG.findall(texto[ini:fin]))
        texto = texto[:ini] + nuevo + marcas + texto[fin:]
    if trozos:
        previo = None
        while previo != texto:                       # <b></b> que se ha quedado vacío
            previo = texto
            texto = RE_PAR_VACIO.sub("", texto)
    return texto, len(trozos)


def reemplazar(datos, texto, nuevo, sensible=False, solo=None):
    """Cambia en todo el supuesto (o solo en las rutas de `solo`). Devuelve cuántas sustituciones hizo."""
    if not texto:
        return 0
    pat = _patron(texto, sensible)
    total = 0
    for ruta, _donde, valor in list(sitios(datos)):
        if solo is not None and ruta not in solo:
            continue
        cambiado, n = _reemplazar_en(valor or "", pat, nuevo)
        if n:
            poner_en(datos, ruta, cambiado)
            total += n
    return total


# ── importar ─────────────────────────────────────────────────────────
_OPC = re.compile(r"^\s*\(?([a-gA-G])[\)\.\-:]\s*(.*)$")
_CORR = re.compile(r"^\s*(?:correcta|respuesta|soluci[oó]n)s?\s*[:=\-]?\s*([a-gA-G](?:\s*[,y/ ]\s*[a-gA-G])*)\s*$",
                   re.IGNORECASE)
_NUM = re.compile(r"^\s*\d+\s*[\)\.\-]\s+")


def _pregunta(bloque_id, statement_id, q, opciones, correctas, law="", tip=""):
    p = datos_html.pregunta_vacia(statement_id, bloque_id)
    p["q"] = q
    p["a"] = opciones
    p["correctas"] = correctas or [0]
    p["c"] = p["correctas"][0]
    p["multiple"] = len(p["correctas"]) > 1
    p["law"] = law
    p["tip"] = tip
    return p


def importar_texto(texto, bloque_id="B1", statement_id=None):
    """Formato: preguntas separadas por una línea en blanco.

        1) Texto de la pregunta (puede ocupar varias líneas)
        a) opción        (la correcta se marca con * delante o con una línea «Correcta: b»)
        b) *opción
        Motivación: texto opcional
        Consejo: texto opcional

    Devuelve (preguntas, avisos)."""
    preguntas, avisos = [], []
    bloques = [b for b in re.split(r"\n\s*\n", texto.replace("\r\n", "\n").strip()) if b.strip()]
    soluciones = {}
    if bloques:
        soluciones = leer_soluciones(bloques[-1])
        if soluciones:
            bloques = bloques[:-1]
    for k, bloque in enumerate(bloques, 1):
        q, opciones, correctas, law, tip = [], [], [], "", ""
        campo = None                         # tras «Motivación:» o «Consejo:», sus líneas siguientes
        for linea in bloque.split("\n"):
            m = _OPC.match(linea)
            c = _CORR.match(linea)
            if c:
                correctas = [LETRAS.index(x.upper()) for x in re.findall(r"[a-gA-G]", c.group(1))]
                campo = None
            elif linea.lower().lstrip().startswith(("motivación:", "motivacion:")):
                law, campo = linea.split(":", 1)[1].strip(), "law"
            elif linea.lower().lstrip().startswith(("consejo:", "tip:")):
                tip, campo = linea.split(":", 1)[1].strip(), "tip"
            elif campo == "law":
                law += "\n" + linea.strip()
            elif campo == "tip":
                tip += "\n" + linea.strip()
            elif m and (opciones or q):
                t = m.group(2).strip()
                if t.startswith("*"):
                    correctas.append(len(opciones))
                    t = t.lstrip("*").strip()
                opciones.append(t)
            elif not opciones:
                q.append(_NUM.sub("", linea).strip())
            elif opciones:
                opciones[-1] += " " + linea.strip()
        enunciado = " ".join(x for x in q if x)
        if not enunciado or len(opciones) < datos_html.MIN_OPCIONES:
            avisos.append("Bloque %d de texto ignorado: hacen falta pregunta y al menos %d opciones."
                          % (k, datos_html.MIN_OPCIONES))
            continue
        if len(opciones) > datos_html.MAX_OPCIONES:
            avisos.append("Pregunta %d: se recortan a %d opciones." % (k, datos_html.MAX_OPCIONES))
            opciones = opciones[:datos_html.MAX_OPCIONES]
        correctas = sorted({i for i in correctas if i < len(opciones)})
        if not correctas:
            avisos.append("Pregunta %d: sin correcta indicada; se marca la A." % k)
        preguntas.append(_pregunta(bloque_id, statement_id, enunciado, opciones, correctas, law, tip))
        if k in soluciones and not any(_corr_marcada(bloque)):
            letras = soluciones[k]
            preguntas[-1]["correctas"] = sorted({LETRAS.index(x) for x in letras if LETRAS.index(x) < len(opciones)}) or [0]
            preguntas[-1]["c"] = preguntas[-1]["correctas"][0]
            preguntas[-1]["multiple"] = len(preguntas[-1]["correctas"]) > 1
            avisos = [a for a in avisos if not a.startswith("Pregunta %d: sin correcta" % k)]
    return preguntas, avisos


def _corr_marcada(bloque):
    """True si el bloque ya indica su correcta (con * o con «Correcta: …»)."""
    for linea in bloque.split("\n"):
        if _CORR.match(linea) or re.match(r"^\s*\(?[a-gA-G][\)\.\-:]\s*\*", linea):
            yield True


_RE_SOL = re.compile(r"(\d+)\s*[\)\.\-:=]?\s*([a-gA-G](?:\s*[,y/]\s*[a-gA-G])*)\b")


def leer_soluciones(bloque):
    """Tabla de soluciones al final de un test pegado («1-b  2-c», «1. a», una por línea…).
    {n.º de pregunta (desde 1): ['B']}. Vacío si el bloque no parece una tabla de soluciones."""
    primera = bloque.strip().split("\n")[0].lower()
    cuerpo = re.sub(r"^\s*(soluciones|respuestas|plantilla de respuestas|clave)\s*:?\s*", "", bloque.strip(),
                    flags=re.IGNORECASE)
    pares = _RE_SOL.findall(cuerpo)
    resto = _RE_SOL.sub("", cuerpo)
    if len(pares) < 2 or re.search(r"[A-Za-zÁ-ú]{3,}", resto):
        return {}
    if not (primera.startswith(("soluc", "respuesta", "plantilla", "clave")) or len(pares) >= 3):
        return {}
    return {int(n): re.findall(r"[a-gA-G]", ls.upper()) for n, ls in pares}


def importar_csv(texto, bloque_id="B1", statement_id=None):
    """Columnas: pregunta, a, b, c, d[, e, f, g], correcta (letras), motivación, consejo.
    Acepta ; o , como separador. Devuelve (preguntas, avisos)."""
    texto = texto.lstrip("\ufeff")
    try:
        sep = csv.Sniffer().sniff(texto[:2000], delimiters=";,\t").delimiter
    except csv.Error:
        sep = ";"
    preguntas, avisos = [], []
    for n, fila in enumerate(csv.reader(io.StringIO(texto), delimiter=sep), 1):
        fila = [c.strip() for c in fila]
        if not fila or not fila[0]:
            continue
        if n == 1 and fila[0].lower().startswith("preg"):
            continue
        # la correcta es la última columna que parece «letras»; el resto son opciones
        corr_i = next((i for i in range(len(fila) - 1, 0, -1)
                       if re.fullmatch(r"[a-gA-G]([\s,y/]+[a-gA-G])*", fila[i] or "")), None)
        if corr_i is None or corr_i < 3:
            avisos.append("Fila %d ignorada: faltan opciones o la columna de la correcta." % n)
            continue
        opciones = [c for c in fila[1:corr_i] if c]
        opciones = opciones[:datos_html.MAX_OPCIONES]
        correctas = sorted({LETRAS.index(x.upper()) for x in re.findall(r"[a-gA-G]", fila[corr_i])
                            if LETRAS.index(x.upper()) < len(opciones)})
        extra = fila[corr_i + 1:]
        preguntas.append(_pregunta(bloque_id, statement_id, fila[0], opciones, correctas,
                                   extra[0] if extra else "", extra[1] if len(extra) > 1 else ""))
    return preguntas, avisos


# ── fallos por pregunta ──────────────────────────────────────────────
def problemas_por_pregunta(datos):
    """{n.º de pregunta desde 0: ('error'|'aviso', texto)} — las mismas reglas que
    «Comprobar», el aviso al guardar y el validador (revision.py)."""
    return revision.por_pregunta(revision.revisar(datos))


# ── autoguardado ─────────────────────────────────────────────────────
def ruta_recuperacion(ruta_supuesto, carpeta):
    nombre = Path(ruta_supuesto).name if ruta_supuesto else "sin_guardar.html"
    return Path(carpeta) / (".recuperacion_" + nombre + ".json")


def guardar_recuperacion(destino, datos):
    try:
        Path(destino).write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        return True
    except OSError:
        return False


def leer_recuperacion(destino):
    try:
        return json.loads(Path(destino).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ── revisión: errores graves, repetidas, estadísticas, citas ───────────
def errores_graves(datos):
    """Fallos que conviene arreglar ANTES de guardar o publicar: lista de textos."""
    return revision.errores(revision.revisar(datos))


# ── identificadores de enunciado ─────────────────────────────────────
RE_ID = re.compile(r"[A-Za-z0-9_-]+")


def error_id_enunciado(datos, enunciado, nuevo):
    """Texto del problema si `nuevo` no vale como identificador de `enunciado`; None si vale."""
    nuevo = (nuevo or "").strip()
    if not nuevo:
        return "El identificador no puede quedar vacío."
    if not RE_ID.fullmatch(nuevo):
        return "Usa solo letras sin tilde, números, guion (-) y guion bajo (_)."
    if any(e is not enunciado and e.get("id") == nuevo for e in datos.get("enunciados", [])):
        return "Ya hay otro enunciado que se llama %s." % nuevo
    return None


def renombrar_enunciado(datos, enunciado, nuevo):
    """Cambia el id del enunciado y el de las preguntas que cuelgan de él. Devuelve cuántas."""
    viejo = enunciado.get("id")
    enunciado["id"] = nuevo
    cuantas = 0
    for p in datos.get("preguntas", []):
        if p.get("statementId") == viejo:
            p["statementId"] = nuevo
            cuantas += 1
    return cuantas


def _norma(texto):
    return " ".join(re.sub(r"[^\w\s]", " ", (texto or "").lower()).split())


def duplicados(datos, umbral=0.88, otras=()):
    """Parejas de preguntas muy parecidas. `otras` = [(nombre, datos)] de otros supuestos.
    Devuelve [(n.º en este supuesto, 'este' o nombre del otro, n.º allí, parecido)]."""
    mias = [_norma(p.get("q", "")) for p in datos["preguntas"]]
    res = []
    for i in range(len(mias)):
        for j in range(i + 1, len(mias)):
            r = _parecido(mias[i], mias[j], umbral)
            if r >= umbral:
                res.append((i + 1, "este", j + 1, round(r, 2)))
    for nombre, d in otras:
        for i, a in enumerate(mias):
            for j, p in enumerate(d["preguntas"]):
                r = _parecido(a, _norma(p.get("q", "")), umbral)
                if r >= umbral:
                    res.append((i + 1, nombre, j + 1, round(r, 2)))
    return res


def _parecido(a, b, umbral=0.88):
    if not a or not b:
        return 0.0
    if abs(len(a) - len(b)) > max(len(a), len(b)) * 0.4:
        return 0.0
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if m.real_quick_ratio() < umbral or m.quick_ratio() < umbral:
        return 0.0
    return m.ratio()


def estadisticas(datos):
    """Texto con el reparto de letras correctas, longitud de opciones y preguntas sin motivación."""
    ps = datos["preguntas"]
    if not ps:
        return "No hay preguntas."
    cuenta = {}
    largas = 0
    for p in ps:
        for i in p.get("correctas") or [0]:
            cuenta[LETRAS[i]] = cuenta.get(LETRAS[i], 0) + 1
        a = p.get("a", [])
        corr = (p.get("correctas") or [0])[0]
        otras = [len(x) for k, x in enumerate(a) if k != corr]
        if otras and corr < len(a) and len(a[corr]) > max(otras):
            largas += 1
    total = sum(cuenta.values())
    lineas = ["ESTADÍSTICAS DEL SUPUESTO (%d preguntas)" % len(ps), "=" * 50, "", "Letra de la respuesta correcta:"]
    for l in LETRAS:
        if l in cuenta:
            lineas.append("   %s  %-4d %5.1f%%  %s" % (l, cuenta[l], 100.0 * cuenta[l] / total, "█" * int(40 * cuenta[l] / total)))
    ideal = 100.0 / max(1, len([1 for l in LETRAS if l in cuenta]))
    sesgo = [l for l in cuenta if abs(100.0 * cuenta[l] / total - ideal) > 15]
    lineas.append("   " + ("⚠ reparto desigual (conviene equilibrar): %s" % ", ".join(sesgo) if sesgo
                           else "reparto razonable"))
    todas = [len(o) for p in ps for o in p.get("a", [])]
    lineas += ["", "Longitud de las opciones (caracteres): media %d · máxima %d" % (sum(todas) // max(1, len(todas)), max(todas or [0])),
               "Preguntas cuya correcta es la opción MÁS LARGA: %d de %d (%.0f%%)%s"
               % (largas, len(ps), 100.0 * largas / len(ps), "  ⚠ pista involuntaria" if largas / len(ps) > 0.5 else ""),
               "Preguntas sin motivación legal: %d" % sum(1 for p in ps if not p.get("law", "").strip()),
               "Preguntas sin consejo: %d" % sum(1 for p in ps if not p.get("tip", "").strip()),
               "Preguntas de respuesta múltiple: %d" % sum(1 for p in ps if p.get("multiple"))]
    return "\n".join(lineas)


_RE_CITA = re.compile(r"\b(?:art\.?|artículo|artículos|arts\.)\s*(\d+(?:\.\d+)?(?:\s*(?:bis|ter))?)(?P<cola>[^\n]{0,45})", re.IGNORECASE)


def citas_sin_norma(datos, normas):
    """Citas «art. N» en las motivaciones sin ninguna norma conocida a menos de 45 caracteres
    (la página no las enlazará). `normas` es la lista de normas_enlaces. [(n.º de pregunta, cita)]"""
    siglas = [s.lower() for n in normas for s in n.get("siglas", []) if s]
    res = []
    for i, p in enumerate(datos["preguntas"], 1):
        texto = re.sub(r"<[^>]+>", "", p.get("law", "") or "")
        for m in _RE_CITA.finditer(texto):
            cola = m.group("cola").lower()
            if not any(s in cola for s in siglas):
                res.append((i, m.group(0).strip()))
    return res


# ── plantillas de pregunta ───────────────────────────────────────────
PLANTILLAS = {
    "Verdadero o falso": dict(q="Indique si la siguiente afirmación es verdadera o falsa: …",
                              a=["Verdadera", "Falsa"], c=[0]),
    "Señale la INCORRECTA": dict(q="Señale la afirmación INCORRECTA:",
                                 a=["Afirmación incorrecta", "Afirmación correcta", "Afirmación correcta",
                                    "Afirmación correcta"], c=[0]),
    "Señale la CORRECTA": dict(q="Señale la afirmación CORRECTA:",
                               a=["Afirmación correcta", "Afirmación incorrecta", "Afirmación incorrecta",
                                  "Afirmación incorrecta"], c=[0]),
    "Plazo (días)": dict(q="¿Cuál es el plazo para …?",
                         a=["10 días hábiles", "15 días hábiles", "1 mes", "3 meses"], c=[0],
                         law="Art. … de la …"),
    "Respuesta múltiple": dict(q="Señale las afirmaciones correctas:",
                               a=["Correcta", "Correcta", "Incorrecta", "Incorrecta"], c=[0, 1], multiple=True),
}


def pregunta_de_plantilla(nombre, bloque_id="B1", statement_id=None):
    pl = PLANTILLAS[nombre]
    p = _pregunta(bloque_id, statement_id, pl["q"], list(pl["a"]), list(pl["c"]), pl.get("law", ""), "")
    p["multiple"] = bool(pl.get("multiple"))
    return p


# ── F4 · citas de la motivación que se enlazan al BOE ────────────────
def enlaces_boe(texto, normas):
    """Las mismas citas que la página convierte en enlace (js/app-uso.js):
    «art. 12 … LGSS» → [(cita, artículo, siglas, dirección del BOE)], sin repetir."""
    reglas = [(s, n.get("boe")) for n in normas or [] for s in n.get("siglas", []) if s and n.get("boe")]
    if not reglas:
        return []
    alt = "|".join(re.escape(s) for s, _b in sorted(reglas, key=lambda r: -len(r[0])))
    patron = re.compile(r"\b([Aa]rt(?:ículos?|s?\.?)?\.?\s*(\d+)[^;:]{0,45}?\b(" + alt + r")(?![\wÀ-ÿ]))")
    boe_de = dict(reglas)
    plano = re.sub(r"<[^>]+>", "", texto or "")
    res, vistos = [], set()
    for m in patron.finditer(plano):
        art, sig = m.group(2), m.group(3)
        url = "https://www.boe.es/buscar/act.php?id=%s#a%s" % (boe_de[sig], art)
        if url not in vistos:
            vistos.add(url)
            res.append(("art. %s %s" % (art, sig), art, sig, url))
    return res


# ── F7 · sugerir los hechos de los que depende una pregunta ──────────
_VACIAS = set("""a al ante bajo con contra de del desde durante e el en entre esta este esto ha han hasta la las
le les lo los mas más me mi no o os para pero por que qué se ser si sí sin sobre su sus tal te tiene tu un una uno
unos unas y ya es son fue era está están cual cuál cuales cuáles cuando cuándo como cómo debe deberá puede podrá
dicho dicha dichos dichas otro otra otros otras le señale indique correcta incorrecta respuesta pregunta caso
supuesto según art artículo ley real decreto""".split())


def _palabras(texto):
    plano = re.sub(r"<[^>]+>", " ", str(texto or "")).lower()
    return [w for w in re.findall(r"[a-záéíóúüñ0-9]{3,}", plano) if w not in _VACIAS]


def sugerir_hechos(pregunta, enunciado, maximo=2, minimo=0.12):
    """Hechos del enunciado que más se parecen a la pregunta (texto, opciones y motivación):
    [(id del hecho, parecido 0-1, palabras en común)], de más a menos parecido.
    Pesa más una palabra rara (nombres, cifras, fechas) que una que sale en todos los hechos."""
    import math
    hechos = [h for h in (enunciado or {}).get("factBlocks") or [] if h.get("id")]
    if not hechos:
        return []
    docs = [set(_palabras(" ".join([h.get("title", "")] + list(h.get("paragraphs") or [])))) for h in hechos]
    preg = set(_palabras(" ".join([pregunta.get("q", ""), pregunta.get("law", "")] + list(pregunta.get("a") or []))))
    if not preg:
        return []
    n = len(docs)
    idf = {w: math.log((n + 1) / (1 + sum(w in d for d in docs))) + 1 for w in preg}
    total = sum(idf.values())
    res = []
    for h, d in zip(hechos, docs):
        comunes = preg & d
        peso = sum(idf[w] for w in comunes) / total if total else 0
        if peso >= minimo:
            res.append((h["id"], round(peso, 2), sorted(comunes, key=lambda w: -idf[w])[:6]))
    res.sort(key=lambda x: -x[1])
    return res[:maximo]


# ── F8 · qué cambia entre dos versiones de un supuesto ───────────────
def comparar_versiones(antes, ahora):
    """Líneas legibles con lo que cambió de `antes` a `ahora` (preguntas añadidas,
    quitadas o cambiadas, enunciados, bloques y datos generales)."""
    def plano(t):
        return " ".join(re.sub(r"<[^>]+>", " ", str(t or "")).split())

    lineas = []
    ca, cb = antes.get("config") or {}, ahora.get("config") or {}
    for k in sorted(set(ca) | set(cb)):
        if isinstance(ca.get(k), (str, int, float, bool)) or isinstance(cb.get(k), (str, int, float, bool)):
            if ca.get(k) != cb.get(k):
                lineas.append("Datos generales · %s: «%s» → «%s»" % (k, plano(ca.get(k))[:60], plano(cb.get(k))[:60]))
    ids_a = [b.get("id") for b in antes.get("bloques") or []]
    ids_b = [b.get("id") for b in ahora.get("bloques") or []]
    for i in ids_b:
        if i not in ids_a:
            lineas.append("Bloque %s: nuevo" % i)
    for i in ids_a:
        if i not in ids_b:
            lineas.append("Bloque %s: quitado" % i)
    ea = {e.get("id"): e for e in antes.get("enunciados") or []}
    eb = {e.get("id"): e for e in ahora.get("enunciados") or []}
    for i in eb:
        if i not in ea:
            lineas.append("Enunciado %s: nuevo" % i)
        elif json.dumps(ea[i], sort_keys=True) != json.dumps(eb[i], sort_keys=True):
            cambios = [k for k in sorted(set(ea[i]) | set(eb[i])) if ea[i].get(k) != eb[i].get(k)]
            lineas.append("Enunciado %s: cambia %s" % (i, ", ".join(cambios)))
    for i in ea:
        if i not in eb:
            lineas.append("Enunciado %s: quitado" % i)

    pa, pb = antes.get("preguntas") or [], ahora.get("preguntas") or []
    clave_a = [plano(p.get("q")) for p in pa]
    usadas = set()
    nombres = {"q": "texto", "a": "opciones", "correctas": "correcta", "law": "motivación", "tip": "consejo",
               "bloqueId": "bloque", "statementId": "enunciado", "tag": "etiqueta", "multiple": "múltiple",
               "factIds": "modo foco", "respuestas": "nº de respuestas"}
    for n, p in enumerate(pb):
        q = plano(p.get("q"))
        # la misma pregunta: igual texto, o la que estaba en el mismo sitio
        j = next((k for k, t in enumerate(clave_a) if t == q and k not in usadas), None)
        if j is None and n < len(pa) and n not in usadas and \
                difflib.SequenceMatcher(None, clave_a[n], q).ratio() > 0.6:
            j = n
        if j is None:
            lineas.append("Pregunta %d: nueva · %s" % (n + 1, q[:70]))
            continue
        usadas.add(j)
        cambios = [nombres.get(k, k) for k in nombres if pa[j].get(k) != p.get(k)]
        if cambios:
            lineas.append("Pregunta %d%s: cambia %s · %s" % (
                n + 1, "" if j == n else " (antes %d)" % (j + 1), ", ".join(cambios), q[:60]))
        elif j != n:
            lineas.append("Pregunta %d: movida (antes %d)" % (n + 1, j + 1))
    for k, p in enumerate(pa):
        if k not in usadas:
            lineas.append("Pregunta %d (de antes): quitada · %s" % (k + 1, clave_a[k][:70]))
    return lineas


# ── F9 · exportar preguntas (lo contrario de importar) ───────────────
def exportar_texto(preguntas):
    """Texto para leer, imprimir o pasar a otro supuesto con «Importar preguntas»: pregunta,
    opciones con * en la correcta, Motivación y Consejo, separadas por una línea en blanco.
    (Los saltos de línea dentro de la pregunta se vuelven espacios; el CSV lo conserva todo.)"""
    bloques = []
    for n, p in enumerate(preguntas, 1):
        correctas = set(p.get("correctas") or [p.get("c", 0)])
        lineas = ["%d) %s" % (n, (p.get("q") or "").replace("\n", " "))]
        for i, op in enumerate(p.get("a") or []):
            lineas.append("%s) %s%s" % (LETRAS[i].lower(), "*" if i in correctas else "", op.replace("\n", " ")))
        # (una línea en blanco separaría la pregunta en dos al volver a importar)
        for campo, rotulo in (("law", "Motivación"), ("tip", "Consejo")):
            if p.get(campo):
                lineas.append(rotulo + ": " + re.sub(r"\n\s*\n+", "\n", p[campo]).replace("\n", "\n    "))
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques) + "\n"


def exportar_csv(preguntas):
    """CSV con «;» (pregunta; A…G; correcta; motivación; consejo) que se abre en Excel
    y que «Importar preguntas» también entiende."""
    salida = io.StringIO()
    w = csv.writer(salida, delimiter=";", lineterminator="\r\n")
    maximo = max([len(p.get("a") or []) for p in preguntas] + [datos_html.MIN_OPCIONES])
    w.writerow(["Pregunta"] + list(LETRAS[:maximo]) + ["Correcta", "Motivación", "Consejo"])
    for p in preguntas:
        ops = list(p.get("a") or [])
        ops += [""] * (maximo - len(ops))
        correctas = ", ".join(LETRAS[i] for i in (p.get("correctas") or [p.get("c", 0)]))
        w.writerow([p.get("q", "")] + ops + [correctas, p.get("law", ""), p.get("tip", "")])
    return "﻿" + salida.getvalue()

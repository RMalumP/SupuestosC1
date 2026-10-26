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


def _campos(p):
    yield "q", None, p.get("q", "")
    for i, t in enumerate(p.get("a", [])):
        yield "a", i, t
    yield "law", None, p.get("law", "")
    yield "tip", None, p.get("tip", "")


def buscar(datos, texto, sensible=False):
    """Lista de (n.º de pregunta desde 0, campo, índice de opción o None, fragmento)."""
    if not texto:
        return []
    pat = _patron(texto, sensible)
    salida = []
    for n, p in enumerate(datos["preguntas"]):
        for campo, i, valor in _campos(p):
            m = pat.search(valor or "")
            if m:
                a = max(0, m.start() - 25)
                salida.append((n, campo, i, (valor[a:m.end() + 25]).replace("\n", " ")))
    return salida


def reemplazar(datos, texto, nuevo, sensible=False):
    """Cambia en todo el supuesto. Devuelve cuántas sustituciones hizo."""
    if not texto:
        return 0
    pat = _patron(texto, sensible)
    total = 0
    for p in datos["preguntas"]:
        for clave in ("q", "law", "tip"):
            p[clave], n = pat.subn(lambda m: nuevo, p.get(clave, "") or "")
            total += n
        nuevas = []
        for t in p.get("a", []):
            t2, n = pat.subn(lambda m: nuevo, t or "")
            total += n
            nuevas.append(t2)
        p["a"] = nuevas
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
        for linea in bloque.split("\n"):
            m = _OPC.match(linea)
            c = _CORR.match(linea)
            if c:
                correctas = [LETRAS.index(x.upper()) for x in re.findall(r"[a-gA-G]", c.group(1))]
            elif linea.lower().lstrip().startswith(("motivación:", "motivacion:")):
                law = linea.split(":", 1)[1].strip()
            elif linea.lower().lstrip().startswith(("consejo:", "tip:")):
                tip = linea.split(":", 1)[1].strip()
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
        opciones = [c for c in fila[1:corr_i]]
        opciones = opciones[:datos_html.MAX_OPCIONES]
        correctas = sorted({LETRAS.index(x.upper()) for x in re.findall(r"[a-gA-G]", fila[corr_i])
                            if LETRAS.index(x.upper()) < len(opciones)})
        extra = fila[corr_i + 1:]
        preguntas.append(_pregunta(bloque_id, statement_id, fila[0], opciones, correctas,
                                   extra[0] if extra else "", extra[1] if len(extra) > 1 else ""))
    return preguntas, avisos


# ── fallos por pregunta ──────────────────────────────────────────────
def problemas_por_pregunta(datos):
    """{n.º de pregunta desde 0: ('error'|'aviso', texto)}"""
    res = {}
    for n, p in enumerate(datos["preguntas"]):
        opciones = p.get("a", [])
        norm = [" ".join(t.lower().split()) for t in opciones if t.strip()]
        if not p.get("q", "").strip():
            res[n] = ("error", "sin texto")
        elif any(not t.strip() for t in opciones):
            res[n] = ("error", "opción vacía")
        elif len(opciones) < datos_html.MIN_OPCIONES:
            res[n] = ("error", "pocas opciones")
        elif len(set(norm)) != len(norm):
            res[n] = ("aviso", "opciones repetidas")
        elif not p.get("law", "").strip():
            res[n] = ("aviso", "sin motivación")
        elif p.get("multiple") and len(p.get("correctas") or []) < 2:
            res[n] = ("aviso", "múltiple con una correcta")
    return res


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
    """Fallos que conviene arreglar ANTES de guardar: lista de textos."""
    salida = []
    for n, (nivel, motivo) in sorted(problemas_por_pregunta(datos).items()):
        if nivel == "error":
            salida.append("Pregunta %d: %s" % (n + 1, motivo))
    for n, p in enumerate(datos["preguntas"], 1):
        if not (p.get("correctas") or []):
            salida.append("Pregunta %d: sin respuesta correcta marcada" % n)
    return salida


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

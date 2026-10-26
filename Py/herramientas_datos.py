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
"""
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
    return preguntas, avisos


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

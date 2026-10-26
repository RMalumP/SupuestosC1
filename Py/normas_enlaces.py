# -*- coding: utf-8 -*-
"""
Lectura y escritura de datos/normas-datos.js (las normas que la plantilla enlaza al BOE).

Cada norma tiene:
  · siglas  → los «apodos» con los que se cita en las motivaciones (RIA, RD 84/1996…)
  · boe     → el identificador «BOE-A-…» de boe.es
  · nota    → comentario libre (solo para reconocerla en la lista)
"""

import re
from pathlib import Path

ARCHIVO = Path(__file__).resolve().parent.parent / "datos" / "normas-datos.js"

_CABECERA_POR_DEFECTO = """/* ════════════════════════════════════════════════════════════════
   NORMAS PARA LOS ENLACES AUTOMÁTICOS
   En la motivación de cada respuesta, las citas del tipo «art. 12 de la LGSS»
   se convierten en un enlace al artículo en el BOE (texto consolidado).
   Para añadir otra norma, añade una línea con sus siglas y su identificador
   del BOE (el «BOE-A-…» que sale en la dirección de la norma en boe.es).
   Una cita solo se enlaza si lleva «art.» o «artículo», un número y, a
   continuación (a menos de 45 caracteres), una de las siglas.
════════════════════════════════════════════════════════════════ */
"""

_RE_ENTRADA = re.compile(
    r'\{\s*siglas:\s*\[(?P<sig>[^\]]*)\]\s*,\s*boe:\s*"(?P<boe>[^"]+)"\s*\}\s*,?'
    r'(?:[ \t]*//[ \t]*(?P<nota>[^\n]*))?')
_RE_BOE = re.compile(r'BOE-[A-Z]-\d{4}-\d+', re.I)


def extraer_boe(texto):
    """Devuelve el «BOE-A-…» que haya en un texto o en una dirección web (o None)."""
    m = _RE_BOE.search(texto or "")
    return m.group(0).upper() if m else None


def partir_siglas(texto):
    """'RIA, RD 84/1996' → ['RIA', 'RD 84/1996'] (sin vacíos ni repetidos)."""
    vistas, salida = set(), []
    for s in re.split(r"[,;\n]", texto or ""):
        s = s.strip().strip('"\'')
        if s and s.lower() not in vistas:
            vistas.add(s.lower())
            salida.append(s)
    return salida


def leer(ruta=ARCHIVO):
    """→ (cabecera, [ {siglas, boe, nota}, … ]). Si el archivo no existe, lista vacía."""
    ruta = Path(ruta)
    if not ruta.is_file():
        return _CABECERA_POR_DEFECTO, []
    texto = ruta.read_text(encoding="utf-8")
    corte = texto.find("window.NORMAS")
    cabecera = texto[:corte] if corte > 0 else _CABECERA_POR_DEFECTO
    normas = []
    for m in _RE_ENTRADA.finditer(texto[max(corte, 0):]):
        normas.append({
            "siglas": re.findall(r'"([^"]*)"', m.group("sig")),
            "boe": m.group("boe"),
            "nota": (m.group("nota") or "").strip(),
        })
    return cabecera, normas


def escribir(normas, cabecera=_CABECERA_POR_DEFECTO, ruta=ARCHIVO):
    lineas = []
    for i, n in enumerate(normas):
        sig = ", ".join('"%s"' % s.replace('"', "'") for s in n["siglas"])
        cuerpo = '{ siglas: [%s], boe: "%s" }' % (sig, n["boe"])
        coma = "," if i < len(normas) - 1 else ""
        nota = ("   // " + n["nota"]) if n.get("nota") else ""
        lineas.append("    " + cuerpo + coma + nota)
    texto = "%swindow.NORMAS = [\n%s\n];\n" % (cabecera, "\n".join(lineas))
    Path(ruta).write_text(texto, encoding="utf-8")

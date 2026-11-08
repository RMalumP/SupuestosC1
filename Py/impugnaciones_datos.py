# -*- coding: utf-8 -*-
"""
IMPUGNACIONES: ESTADO Y PREGUNTA EXACTA  (sin ventana)
══════════════════════════════════════════════════════
Parte del editor de supuestos. Las impugnaciones llegan de la hoja de Google
(publicar.descargar_impugnaciones). Aquí:

  · localizar()    encuentra el supuesto y la pregunta EXACTA de cada impugnación
                   (la columna «Pregunta» trae «N. texto ‖ opción ‖ …»; el número N
                   es el del examen barajado, así que se busca por el texto).
  · el estado de cada una (pendiente, aceptada o rechazada) y una nota tuya, que se
    guardan en «.impugnaciones_estado.json» en la carpeta del proyecto. Ese archivo
    NO se sube a GitHub (la web es pública y las notas son tuyas).
"""
import difflib
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import datos_html
import publicar as pub
from archivos import escribir_seguro

ARCHIVO_ESTADO = ".impugnaciones_estado.json"
ESTADOS = ("pendiente", "aceptada", "rechazada")
RE_TAG = re.compile(r"<[^<>]*>")


def _plano(t):
    return " ".join(RE_TAG.sub("", str(t or "")).lower().split())     # como textContent en la página


def clave(fila):
    """Identificador estable de una impugnación: su ID si lo trae, si no una huella."""
    ident = pub.columna(fila, "id")
    if ident and len(ident) <= 60 and " " not in ident.strip():
        return ident.strip()
    base = "|".join(pub.columna(fila, *c) for c in (("marca", "fecha"), ("supuesto",), ("pregunta", "pegunta"),
                                                     ("texto", "impugn", "motivo")))
    return "h" + hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]


def texto_pregunta(fila):
    """De «12. ¿Cuál es…? ‖ a ‖ b» saca «¿Cuál es…?»."""
    t = pub.columna(fila, "pregunta", "pegunta")
    t = t.split("‖", 1)[0]
    return re.sub(r"^\s*\d+\s*[.)-]\s*", "", t).strip()


def leer_supuestos(raiz):
    """[(ruta, datos)] de todos los supuestos de la carpeta (los que se puedan leer)."""
    res = []
    for f in sorted((Path(raiz) / "supuestos").glob("*.html")):
        if f.name.startswith("."):
            continue
        try:
            datos, _modo, _html = datos_html.leer_html(f)
        except (OSError, ValueError):
            continue
        res.append((f, datos))
    return res


def localizar(fila, supuestos):
    """→ (ruta, n.º de pregunta desde 0, parecido 0-1) o (ruta|None, None, 0).
    Primero el supuesto por su título o nombre de archivo; luego la pregunta más parecida."""
    nombre = _plano(pub.columna(fila, "supuesto"))
    texto = _plano(texto_pregunta(fila))
    candidatos = [(r, d) for r, d in supuestos
                  if nombre and (nombre == _plano((d.get("config") or {}).get("titulo"))
                                 or nombre in (r.stem.lower(), r.name.lower()))]
    donde = candidatos or supuestos
    mejor = (candidatos[0][0] if candidatos else None, None, 0.0)
    if not texto:
        return mejor
    for ruta, datos in donde:
        for n, p in enumerate(datos.get("preguntas") or []):
            q = _plano(p.get("q"))
            if not q:
                continue
            if q == texto:
                return ruta, n, 1.0
            m = difflib.SequenceMatcher(None, texto, q, autojunk=False)
            if m.real_quick_ratio() <= mejor[2] or m.quick_ratio() <= mejor[2]:
                continue
            r = m.ratio()
            if r > mejor[2]:
                mejor = (ruta, n, r)
    return mejor if mejor[2] >= 0.6 else (mejor[0] if candidatos else None, None, mejor[2])


def leer_estados(raiz):
    try:
        datos = json.loads((Path(raiz) / ARCHIVO_ESTADO).read_text(encoding="utf-8"))
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def poner_estado(raiz, estados, k, estado=None, nota=None):
    """Cambia el estado y/o la nota de la impugnación `k` y lo guarda."""
    e = dict(estados.get(k) or {"estado": "pendiente", "nota": ""})
    if estado is not None:
        if estado not in ESTADOS:
            raise ValueError("Estado desconocido: %s" % estado)
        e["estado"] = estado
    if nota is not None:
        e["nota"] = nota
    e["fecha"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    estados[k] = e
    escribir_seguro(Path(raiz) / ARCHIVO_ESTADO, json.dumps(estados, ensure_ascii=False, indent=1, sort_keys=True))
    return e


def estado_de(estados, k):
    return (estados.get(k) or {}).get("estado", "pendiente")


def resumen(filas, estados):
    cuenta = {e: 0 for e in ESTADOS}
    for f in filas:
        cuenta[estado_de(estados, clave(f))] += 1
    return cuenta

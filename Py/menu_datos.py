# -*- coding: utf-8 -*-
"""
LISTA DEL MENÚ (supuestos-datos.js): leer y escribir
═════════════════════════════════════════════════════
Parte del editor de supuestos. No se ejecuta sola: la usan
editor_supuestos.py, validar_supuestos.py y alta_menu.py.

El archivo supuestos-datos.js guarda UNA LÍNEA POR SUPUESTO:

    { "seccion": "temas", "grupo": "iniciales", "archivo": "supuesto_4", "letra": "4",
      "ref": "S004", "titulo": "Supuesto 4 · Título", "desc": "15 preguntas · 30 minutos" },

Dentro del programa el menú se maneja como un diccionario anidado
(secciones → grupos → items, más «examenes»); aquí se convierte de
un formato al otro. También se lee el formato antiguo (todo anidado).
Sin dependencias: solo la biblioteca estándar.
"""
import json
import re
from pathlib import Path

ARCHIVO_MENU = "supuestos-datos.js"

# Valores por defecto de una instalación nueva
SECCIONES_BASE = [
    {"id": "temas", "titulo": "Supuestos por temas",
     "grupos": [{"id": "iniciales", "titulo": "Iniciales"}, {"id": "avanzados", "titulo": "Avanzados"}]},
    {"id": "generales", "titulo": "Supuestos generales",
     "grupos": [{"id": "iniciales", "titulo": "Iniciales"}, {"id": "avanzados", "titulo": "Avanzados"}]},
]

RE_SECCIONES = re.compile(r"(var SECCIONES = )(.*?)(;\s*\n\s*// <<< SECCIONES)", re.S)
RE_SUPUESTOS = re.compile(r"(var SUPUESTOS = )(.*?)(;\s*\n\s*// <<< SUPUESTOS)", re.S)
RE_VIEJO = re.compile(r"window\.SUPUESTOS_DATOS\s*=\s*(\{.*\})\s*;", re.S)

CABECERA = """/* ════════════════════════════════════════════════════════════════
   LISTA DE SUPUESTOS DEL MENÚ
   El menú principal (index.html) y el modo sin conexión se montan
   a partir de este archivo. Hay UNA LÍNEA por supuesto.

   Para añadir un supuesto a mano, copia una línea de la lista, cámbiale
   los datos y GUÁRDALA CON LA COMA FINAL (menos la última, que no la lleva):

     { "seccion": "generales", "grupo": "iniciales", "archivo": "supuesto_4", "letra": "4",
       "ref": "S004", "titulo": "Supuesto 4 · Título", "desc": "15 preguntas · 30 minutos" },

   · seccion/grupo: dónde sale (mira «SECCIONES» más abajo). «examenes» va sin grupo.
   · archivo: nombre del .html de la carpeta supuestos/ SIN «.html».
   · letra: texto del círculo (máx. 4 caracteres).
   · "oculto": true  lo quita del menú sin borrarlo (se puede abrir con su enlace).
   Para comprobar que todo está bien:  python Py/validar_supuestos.py
   El editor de Python (editor_supuestos.py) hace este alta solo al guardar.
════════════════════════════════════════════════════════════════ */
"""

COLA = """
  /* A partir de aquí no hace falta tocar nada: monta el menú. */
  function titulo(id) { return id.charAt(0).toUpperCase() + id.slice(1); }
  var datos = { secciones: [], examenes: [], lista: SUPUESTOS };
  var porId = {};
  SECCIONES.forEach(function (s) {
    var sec = { id: s.id, titulo: s.titulo, grupos: [] };
    (s.grupos || []).forEach(function (g) { sec.grupos.push({ id: g.id, titulo: g.titulo, items: [] }); });
    datos.secciones.push(sec); porId[s.id] = sec;
  });
  SUPUESTOS.forEach(function (it) {
    if (it.oculto) return;
    if (it.seccion === "examenes") { datos.examenes.push(it); return; }
    var sec = porId[it.seccion];
    if (!sec) { sec = { id: it.seccion, titulo: titulo(it.seccion), grupos: [] }; datos.secciones.push(sec); porId[it.seccion] = sec; }
    var g = null;
    sec.grupos.forEach(function (x) { if (x.id === it.grupo) g = x; });
    if (!g) { g = { id: it.grupo, titulo: titulo(it.grupo), items: [] }; sec.grupos.push(g); }
    g.items.push(it);
  });
  G.SUPUESTOS_DATOS = datos;
})(typeof window !== "undefined" ? window : self);
"""


def _json_tolerante(txt, desplazamiento_lineas, nombre):
    """json.loads que admite comas finales y líneas // comentadas, y que en caso de
    error dice la línea del archivo."""
    limpio = "\n".join("" if l.lstrip().startswith("//") else l for l in txt.split("\n"))
    limpio = re.sub(r",(\s*[}\]])", r"\1", limpio)
    try:
        return json.loads(limpio)
    except ValueError as e:
        linea = getattr(e, "lineno", 1) + desplazamiento_lineas
        raise ValueError("%s: línea %d de %s: %s. Revisa comillas y comas en esa línea y la anterior."
                         % (nombre, linea, ARCHIVO_MENU, e.msg if hasattr(e, "msg") else e))


def _linea_de(texto, pos):
    return texto.count("\n", 0, pos)


def leer(texto):
    """Texto de supuestos-datos.js → menú anidado
    {"secciones": [{"id","titulo","grupos":[{"id","titulo","items":[…]}]}], "examenes": [...]}"""
    ms, mi = RE_SECCIONES.search(texto), RE_SUPUESTOS.search(texto)
    if ms and mi:
        secciones = _json_tolerante(ms.group(2), _linea_de(texto, ms.start(2)), "SECCIONES")
        lista = _json_tolerante(mi.group(2), _linea_de(texto, mi.start(2)), "SUPUESTOS")
        menu = {"secciones": [], "examenes": []}
        por_id = {}
        for s in secciones:
            sec = {"id": s["id"], "titulo": s.get("titulo") or s["id"].title(),
                   "grupos": [{"id": g["id"], "titulo": g.get("titulo") or g["id"].title(), "items": []}
                              for g in s.get("grupos", [])]}
            menu["secciones"].append(sec)
            por_id[sec["id"]] = sec
        for it in lista:
            it = dict(it)
            sec_id = it.pop("seccion", "") or ""
            grupo_id = it.pop("grupo", "") or ""
            if sec_id == "examenes":
                menu["examenes"].append(it)
                continue
            sec = por_id.get(sec_id)
            if sec is None:
                sec = {"id": sec_id, "titulo": sec_id.title(), "grupos": []}
                menu["secciones"].append(sec)
                por_id[sec_id] = sec
            g = next((x for x in sec["grupos"] if x["id"] == grupo_id), None)
            if g is None:
                g = {"id": grupo_id, "titulo": grupo_id.title(), "items": []}
                sec["grupos"].append(g)
            g["items"].append(it)
        return menu
    mv = RE_VIEJO.search(texto)
    if mv:                                     # formato antiguo, todo anidado
        return json.loads(mv.group(1))
    raise ValueError("No reconozco el formato de %s (¿se borró alguna línea «var SECCIONES» o «var SUPUESTOS»?)."
                     % ARCHIVO_MENU)


def aplanar(menu):
    lista = []
    for sec in menu.get("secciones", []):
        for g in sec.get("grupos", []):
            for it in g.get("items", []):
                f = {"seccion": sec["id"], "grupo": g["id"]}
                f.update({k: v for k, v in it.items() if k not in ("seccion", "grupo")})
                lista.append(f)
    for it in menu.get("examenes", []):
        f = {"seccion": "examenes"}
        f.update({k: v for k, v in it.items() if k not in ("seccion", "grupo")})
        lista.append(f)
    return lista


def _bloque_secciones(menu):
    secs = [{"id": s["id"], "titulo": s.get("titulo", s["id"]),
             "grupos": [{"id": g["id"], "titulo": g.get("titulo", g["id"])} for g in s.get("grupos", [])]}
            for s in menu.get("secciones", [])]
    lineas = ["  " + json.dumps(s, ensure_ascii=False) for s in secs]
    return "[\n" + ",\n".join(lineas) + "\n  ]"


def _bloque_supuestos(menu):
    lineas = ["  " + json.dumps(it, ensure_ascii=False) for it in aplanar(menu)]
    return "[\n" + ",\n".join(lineas) + "\n  ]"


def escribir_texto(texto_antiguo, menu):
    """Devuelve el nuevo contenido de supuestos-datos.js. Si el archivo ya tiene el
    formato de una línea por supuesto solo se cambian esas dos listas (se respeta lo
    demás); si no, se crea el archivo completo."""
    ms, mi = RE_SECCIONES.search(texto_antiguo or ""), RE_SUPUESTOS.search(texto_antiguo or "")
    if ms and mi:
        t = RE_SECCIONES.sub(lambda m: m.group(1) + _bloque_secciones(menu) + m.group(3), texto_antiguo, count=1)
        return RE_SUPUESTOS.sub(lambda m: m.group(1) + _bloque_supuestos(menu) + m.group(3), t, count=1)
    return (CABECERA + "(function (G) {\n  \"use strict\";\n"
            "  // >>> SECCIONES: orden y títulos de las secciones y grupos del menú\n"
            "  var SECCIONES = " + _bloque_secciones(menu) + ";\n  // <<< SECCIONES\n\n"
            "  // >>> SUPUESTOS: una línea por supuesto\n"
            "  var SUPUESTOS = " + _bloque_supuestos(menu) + ";\n  // <<< SUPUESTOS\n" + COLA)


def leer_archivo(ruta):
    """(texto, menú) de un supuestos-datos.js."""
    texto = Path(ruta).read_text(encoding="utf-8")
    return texto, leer(texto)


def escribir_archivo(ruta, texto_antiguo, menu):
    Path(ruta).write_text(escribir_texto(texto_antiguo, menu), encoding="utf-8")


def archivos_del_menu(menu):
    """Todos los nombres de archivo del menú (incluidos los ocultos)."""
    return [it["archivo"] for it in aplanar(menu) if it.get("archivo")]


def ficha(archivo, datos, letra=None):
    """Tarjeta del menú a partir de los datos de un supuesto (bloque «datos-supuesto»)."""
    cfg = datos.get("config") or {}
    n = len(datos.get("preguntas") or [])
    partes = ["%d preguntas" % n]
    if cfg.get("minutos"):
        partes.append("%s minutos" % cfg["minutos"])
    if cfg.get("ambito"):
        partes.append(str(cfg["ambito"]))
    return {"archivo": archivo,
            "letra": letra or archivo.replace("supuesto_", "").upper()[:4],
            "ref": str(cfg.get("referencia") or archivo).strip(),
            "titulo": str(cfg.get("titulo") or archivo).strip(),
            "desc": " · ".join(partes)}


def lista_de(menu, clave):
    """Lista de supuestos de «sección/grupo» (o «examenes»); la crea si no existe."""
    if clave == "examenes":
        return menu.setdefault("examenes", [])
    sec_id, grupo_id = clave.split("/", 1)
    sec = next((x for x in menu.setdefault("secciones", []) if x["id"] == sec_id), None)
    if sec is None:
        sec = {"id": sec_id, "titulo": sec_id.title(), "grupos": []}
        menu["secciones"].append(sec)
    g = next((x for x in sec["grupos"] if x["id"] == grupo_id), None)
    if g is None:
        g = {"id": grupo_id, "titulo": grupo_id.title(), "items": []}
        sec["grupos"].append(g)
    return g["items"]


def destinos(menu):
    """[(clave, texto legible)] de todos los sitios donde puede ir un supuesto."""
    res = []
    for s in menu.get("secciones", []):
        for g in s.get("grupos", []):
            res.append(("%s/%s" % (s["id"], g["id"]), "%s · %s" % (s.get("titulo", s["id"]), g.get("titulo", g["id"]))))
    res.append(("examenes", "Exámenes y simulacros"))
    return res

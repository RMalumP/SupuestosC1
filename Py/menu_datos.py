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


# ══════════════════════════════════════════════════════════════════════
#  Edición del menú (la usa la ventana «Menú de inicio» del editor)
#  Todas estas funciones cambian el diccionario `menu` y no tocan el disco.
# ══════════════════════════════════════════════════════════════════════
CAMPOS_FICHA = ("letra", "ref", "titulo", "desc")


def _slug(texto):
    import unicodedata
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t


def _listas(menu):
    """[(clave, lista)] de todas las listas de supuestos, en orden de pantalla."""
    for s in menu.get("secciones", []):
        for g in s.get("grupos", []):
            yield "%s/%s" % (s["id"], g["id"]), g.setdefault("items", [])
    yield "examenes", menu.setdefault("examenes", [])


def buscar(menu, archivo):
    """(clave, lista, posición) del supuesto, o None."""
    for clave, lista in _listas(menu):
        for i, it in enumerate(lista):
            if it.get("archivo") == archivo:
                return clave, lista, i
    return None


def mover(menu, archivo, delta):
    """Sube (delta=-1) o baja (+1) un supuesto dentro de su lista. Devuelve True si se movió."""
    r = buscar(menu, archivo)
    if not r:
        return False
    _, lista, i = r
    j = i + delta
    if not 0 <= j < len(lista):
        return False
    lista[i], lista[j] = lista[j], lista[i]
    return True


def mover_a(menu, archivo, clave_destino, al_final=True):
    """Cambia un supuesto de sección/grupo."""
    r = buscar(menu, archivo)
    if not r:
        return False
    _, lista, i = r
    it = lista.pop(i)
    destino = lista_de(menu, clave_destino)
    destino.append(it) if al_final else destino.insert(0, it)
    return True


def editar(menu, archivo, **campos):
    """Cambia letra, ref, titulo o desc de un supuesto."""
    r = buscar(menu, archivo)
    if not r:
        return False
    it = r[1][r[2]]
    for k, v in campos.items():
        if k in CAMPOS_FICHA:
            it[k] = str(v).strip()
    return True


def ocultar(menu, archivo, oculto=True):
    r = buscar(menu, archivo)
    if not r:
        return False
    it = r[1][r[2]]
    if oculto:
        it["oculto"] = True
    else:
        it.pop("oculto", None)
    return True


def quitar(menu, archivo):
    """Saca el supuesto del menú (no borra su .html)."""
    r = buscar(menu, archivo)
    if not r:
        return False
    r[1].pop(r[2])
    return True


def anadir(menu, ficha_supuesto, clave_destino):
    """Añade una ficha (ver ficha()) al final del grupo; si ya estaba, la mueve."""
    if buscar(menu, ficha_supuesto["archivo"]):
        quitar(menu, ficha_supuesto["archivo"])
    lista_de(menu, clave_destino).append(ficha_supuesto)


def crear_seccion(menu, titulo, id_=None):
    """Crea una sección vacía. Devuelve su id."""
    id_ = _slug(id_ or titulo)
    if not id_ or id_ == "examenes":
        raise ValueError("El nombre de la sección no es válido.")
    if any(s["id"] == id_ for s in menu.setdefault("secciones", [])):
        raise ValueError("Ya existe una sección «%s»." % id_)
    menu["secciones"].append({"id": id_, "titulo": titulo.strip() or id_.title(), "grupos": []})
    return id_


def crear_grupo(menu, seccion_id, titulo, id_=None):
    """Crea un grupo vacío dentro de una sección. Devuelve la clave «sección/grupo»."""
    sec = next((s for s in menu.get("secciones", []) if s["id"] == seccion_id), None)
    if sec is None:
        raise ValueError("No existe la sección «%s»." % seccion_id)
    id_ = _slug(id_ or titulo)
    if not id_:
        raise ValueError("El nombre del grupo no es válido.")
    if any(g["id"] == id_ for g in sec["grupos"]):
        raise ValueError("Ya existe ese grupo en la sección.")
    sec["grupos"].append({"id": id_, "titulo": titulo.strip() or id_.title(), "items": []})
    return "%s/%s" % (seccion_id, id_)


def renombrar(menu, clave, titulo):
    """Cambia el título visible de una sección («temas») o de un grupo («temas/iniciales»)."""
    sec_id, _, grupo_id = clave.partition("/")
    sec = next((s for s in menu.get("secciones", []) if s["id"] == sec_id), None)
    if sec is None:
        return False
    if not grupo_id:
        sec["titulo"] = titulo.strip() or sec["titulo"]
        return True
    g = next((x for x in sec["grupos"] if x["id"] == grupo_id), None)
    if g is None:
        return False
    g["titulo"] = titulo.strip() or g["titulo"]
    return True


def mover_contenedor(menu, clave, delta):
    """Sube o baja una sección o un grupo entre sus hermanos."""
    sec_id, _, grupo_id = clave.partition("/")
    if not grupo_id:
        lista = menu.get("secciones", [])
        pos = next((i for i, s in enumerate(lista) if s["id"] == sec_id), None)
    else:
        sec = next((s for s in menu.get("secciones", []) if s["id"] == sec_id), None)
        lista = sec["grupos"] if sec else []
        pos = next((i for i, g in enumerate(lista) if g["id"] == grupo_id), None)
    if pos is None or not 0 <= pos + delta < len(lista):
        return False
    lista[pos], lista[pos + delta] = lista[pos + delta], lista[pos]
    return True


def eliminar_contenedor(menu, clave):
    """Borra una sección o grupo SOLO si está vacío."""
    sec_id, _, grupo_id = clave.partition("/")
    sec = next((s for s in menu.get("secciones", []) if s["id"] == sec_id), None)
    if sec is None:
        return False
    if not grupo_id:
        if any(g.get("items") for g in sec["grupos"]):
            raise ValueError("La sección no está vacía: mueve antes sus supuestos a otro sitio.")
        menu["secciones"].remove(sec)
        return True
    g = next((x for x in sec["grupos"] if x["id"] == grupo_id), None)
    if g is None:
        return False
    if g.get("items"):
        raise ValueError("El grupo no está vacío: mueve antes sus supuestos a otro sitio.")
    sec["grupos"].remove(g)
    return True


def sin_alta(menu, carpeta_supuestos):
    """Nombres de los .html de la carpeta que todavía no están en el menú."""
    en_menu = set(archivos_del_menu(menu))
    return sorted(p.stem for p in Path(carpeta_supuestos).glob("*.html") if p.stem not in en_menu)

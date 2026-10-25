#!/usr/bin/env python3
"""
VALIDADOR DE SUPUESTOS Y DEL MENÚ
Comprueba, sin abrir el navegador, que los supuestos de la carpeta «supuestos/» y
el menú (supuestos-datos.js) están bien. No necesita instalar nada.

    python Py/validar_supuestos.py            revisa todo el proyecto
    python Py/validar_supuestos.py T2I 0      solo esos supuestos
    python Py/validar_supuestos.py --plantillas   incluye las plantillas de Py/

Salida: ERROR = hay que arreglarlo (el programa termina con código 1)
        AVISO = conviene mirarlo, pero no impide publicar
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import menu_datos  # noqa: E402  (va junto a este archivo)
RE_JSON = re.compile(r'<script\b[^>]*\bid=["\']datos-supuesto["\'][^>]*>(.*?)</script>', re.S | re.I)
RE_MOTOR = re.compile(r'<meta\s+name=["\']motor-plantilla["\']\s+content=["\'](\d+)["\']', re.I)
RE_REFS = re.compile(r'(?:href|src)=["\']([^"\']+)["\']', re.I)
# Archivos que todo supuesto debe enlazar (en este orden relativo)
OBLIGATORIOS = ["base-supuesto.css", "tema-supuesto.css", "prefs.js", "pwa.js", "normas-datos.js",
                "telemetria-config.js", "app-supuesto.js", "app-uso.js", "app-subrayado.js", "subrayado.css", "app-telemetria.js"]

errores, avisos = [], []


def err(donde, msg):
    errores.append("ERROR  %s: %s" % (donde, msg))


def aviso(donde, msg):
    avisos.append("AVISO  %s: %s" % (donde, msg))


def norm(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(t))).strip().lower()


def validar_supuesto(ruta, motor_actual):
    nom = ruta.name
    html = ruta.read_text(encoding="utf-8")
    m = RE_JSON.search(html)
    if not m:
        err(nom, "no tiene el bloque de datos <script id=\"datos-supuesto\">")
        return None
    try:
        d = json.loads(m.group(1))
    except ValueError as e:
        err(nom, "el bloque de datos no es JSON válido (%s)" % e)
        return None

    mt = RE_MOTOR.search(html)
    motor = int(mt.group(1)) if mt else 0
    if motor < motor_actual and "noeditor" not in nom:
        aviso(nom, "usa el motor %d y la plantilla actual es la %d (ábrelo en el editor y guárdalo para ponerlo al día)" % (motor, motor_actual))

    # enlaces del <head> y del final de la página
    refs = RE_REFS.findall(html)
    for o in OBLIGATORIOS:
        if not any(r.endswith(o) for r in refs):
            err(nom, "falta enlazar %s (el diseño y las funciones nuevas no funcionarán)" % o)
    for r in refs:
        if re.match(r"^(https?:|//|#|mailto:|data:)", r) or r.startswith(("javascript:",)):
            continue
        if not (ruta.parent / r.split("?")[0].split("#")[0]).exists():
            err(nom, "el archivo enlazado «%s» no existe" % r)

    cfg = d.get("config") or {}
    if not str(cfg.get("titulo", "")).strip():
        err(nom, "config.titulo está vacío")
    try:
        if float(cfg.get("minutos", 0)) <= 0:
            err(nom, "config.minutos debe ser mayor que 0")
    except (TypeError, ValueError):
        err(nom, "config.minutos no es un número")

    bloques = d.get("bloques") or []
    ids_b = [b.get("id") for b in bloques]
    for i, n in Counter(ids_b).items():
        if n > 1:
            err(nom, "el bloque «%s» está repetido" % i)
    enun = d.get("enunciados") or []
    ids_e = [e.get("id") for e in enun]
    for i, n in Counter(ids_e).items():
        if n > 1:
            err(nom, "el enunciado «%s» está repetido" % i)
    hechos = {}
    for e in enun:
        hs = [h.get("id") for h in (e.get("factBlocks") or []) if h.get("id")]
        for i, n in Counter(hs).items():
            if n > 1:
                err(nom, "en el enunciado %s el hecho «%s» está repetido" % (e.get("id"), i))
        hechos[e.get("id")] = set(hs)

    preguntas = d.get("preguntas") or []
    if not preguntas:
        err(nom, "no tiene preguntas")
    vistos = Counter(norm(q.get("q", "")) for q in preguntas)
    for i, q in enumerate(preguntas, 1):
        p = "%s, pregunta %d" % (nom, i)
        if not norm(q.get("q", "")):
            err(p, "el enunciado de la pregunta está vacío")
        elif vistos[norm(q["q"])] > 1:
            aviso(p, "hay otra pregunta con el mismo texto")
        ops = q.get("a") or []
        if len(ops) < 2:
            err(p, "tiene menos de 2 opciones")
        for k, o in enumerate(ops):
            if not norm(o):
                err(p, "la opción %s está vacía" % "ABCDEFG"[k % 7])
        if len({norm(o) for o in ops}) < len(ops):
            err(p, "hay opciones repetidas")
        cor = q.get("correctas")
        if cor is None and isinstance(q.get("c"), int):
            cor = [q["c"]]
        if not cor:
            err(p, "no tiene ninguna respuesta correcta marcada")
        else:
            if any((not isinstance(c, int)) or c < 0 or c >= len(ops) for c in cor):
                err(p, "una respuesta correcta apunta a una opción que no existe")
            if len(set(cor)) != len(cor):
                err(p, "respuestas correctas repetidas")
            if len(cor) > 1 and not q.get("multiple"):
                err(p, "tiene varias correctas pero no está marcada como respuesta múltiple")
            if q.get("multiple") and len(cor) < 2:
                aviso(p, "está marcada como múltiple pero solo tiene una correcta")
            r = q.get("respuestas")
            if isinstance(r, int) and r:
                # (si «respuestas» supera el nº de opciones el motor usa todas: no es un problema)
                if r < len(cor) + (1 if len(ops) > len(cor) else 0):
                    err(p, "«respuestas» (%d) es demasiado pequeño para incluir las correctas" % r)
        if not norm(q.get("law", "")):
            aviso(p, "no tiene motivación legal (campo «law»)")
        if q.get("bloqueId") and q["bloqueId"] not in ids_b:
            err(p, "pertenece al bloque «%s», que no existe" % q["bloqueId"])
        sid = q.get("statementId")
        if sid and sid not in ids_e:
            err(p, "usa el enunciado «%s», que no existe" % sid)
        for f in q.get("factIds") or []:
            if sid and f not in hechos.get(sid, set()):
                err(p, "se vincula al hecho «%s», que no está en el enunciado %s" % (f, sid))

    env = d.get("envio") or {}
    if not str(env.get("url", "")).startswith("https://docs.google.com/forms/"):
        aviso(nom, "envio.url no apunta a un formulario de Google (no se enviarán resultados)")
    return d, html


def validar_menu(supuestos):
    ruta = RAIZ / "supuestos-datos.js"
    if not ruta.exists():
        err("supuestos-datos.js", "no existe")
        return
    try:
        menu = menu_datos.leer(ruta.read_text(encoding="utf-8"))
    except ValueError as e:
        err("supuestos-datos.js", str(e))
        return
    fichas = [(it, "examenes" if it["seccion"] == "examenes" else "%s/%s" % (it["seccion"], it["grupo"]))
              for it in menu_datos.aplanar(menu)]
    archivos = Counter(f["archivo"] for f, _ in fichas)
    refs = Counter(f.get("ref") for f, _ in fichas)
    for f, donde in fichas:
        a = f.get("archivo", "")
        p = "menú, %s (%s)" % (a, donde)
        for campo in ("archivo", "letra", "ref", "titulo", "desc"):
            if not str(f.get(campo, "")).strip():
                err(p, "falta «%s» (ábrelo en supuestos-datos.js, busca «%s» y rellena ese campo)" % (campo, a or "la línea sin archivo"))
        if archivos[a] > 1:
            err(p, "aparece más de una vez en el menú")
        if refs[f.get("ref")] > 1:
            aviso(p, "otra tarjeta tiene la misma referencia «%s»" % f.get("ref"))
        if len(str(f.get("letra", ""))) > 4:
            aviso(p, "el texto del círculo («%s») tiene más de 4 caracteres" % f.get("letra"))
        if not (RAIZ / "supuestos" / (a + ".html")).exists():
            err(p, "no existe supuestos/%s.html: o el nombre de «archivo» en supuestos-datos.js está mal escrito o falta subir ese .html a la carpeta supuestos/" % a)
        elif a in supuestos:
            d = supuestos[a][0]
            n = len(d.get("preguntas") or [])
            mm = re.search(r"(\d+)\s+preguntas", f.get("desc", ""))
            if mm and int(mm.group(1)) != n:
                aviso(p, "la descripción dice %s preguntas y el supuesto tiene %d" % (mm.group(1), n))
            mm = re.search(r"(\d+)\s+minutos", f.get("desc", ""))
            mi = (d.get("config") or {}).get("minutos")
            if mm and mi and float(mm.group(1)) != float(mi):
                aviso(p, "la descripción dice %s minutos y el supuesto tiene %s" % (mm.group(1), mi))
    en_menu = set(archivos)
    for a in sorted(supuestos):
        if a not in en_menu and (RAIZ / "supuestos" / (a + ".html")).exists():
            aviso(a + ".html", "no está en el menú: ejecuta «python Py/editor_supuestos.py --alta» para darlo de alta, o copia una línea en supuestos-datos.js")


def validar_sw():
    ruta = RAIZ / "sw.js"
    if not ruta.exists():
        err("sw.js", "no existe")
        return
    t = ruta.read_text(encoding="utf-8")
    m = re.search(r"const PRECACHE_BASE = \[(.*?)\];", t, re.S)
    if not m:
        err("sw.js", "no encuentro la lista PRECACHE_BASE")
        return
    lista = re.findall(r'"([^"]+)"', m.group(1))
    if "importScripts" not in t or "supuestos-datos.js" not in t:
        err("sw.js", "debe cargar supuestos-datos.js con importScripts para guardar los supuestos sin conexión")
    for r in lista:
        if r != "./" and not (RAIZ / r).exists():
            err("sw.js", "PRECACHE incluye «%s», que no existe (la app no se instalaría)" % r)
    ya = {"supuestos/" + a + ".html" for a in menu_datos.archivos_del_menu(menu_datos.leer(
        (RAIZ / "supuestos-datos.js").read_text(encoding="utf-8")))} if (RAIZ / "supuestos-datos.js").exists() else set()
    for rel in ["index.html", "mi-estudio.html", "resultados/resultados.html"]:
        if (RAIZ / rel).exists() and rel not in lista:
            aviso("sw.js", "PRECACHE no incluye %s (no estará disponible sin conexión hasta visitarlo)" % rel)
    for p in sorted((RAIZ / "supuestos").glob("*.html")):
        rel = p.relative_to(RAIZ).as_posix()
        if rel not in ya:
            aviso("sw.js", "%s no está en el menú, así que tampoco se guarda sin conexión" % rel)
    for p in ["base-supuesto.css", "tema-supuesto.css", "tema-menu.css", "tema-resultados.css", "prefs.js", "pwa.js",
              "app-supuesto.js", "app-uso.js", "app-subrayado.js", "subrayado.css", "app-menu.js", "app-estudio.js", "app-telemetria.js", "normas-datos.js",
              "telemetria-config.js", "supuestos-datos.js"]:
        if (RAIZ / p).exists() and p not in lista:
            aviso("sw.js", "PRECACHE no incluye %s" % p)
    fu = RAIZ / "fuentes" / "fuentes.css"
    if fu.exists():
        for u in re.findall(r"url\(([^)]+)\)", fu.read_text(encoding="utf-8")):
            if not (fu.parent / u.strip("'\"")).exists():
                err("fuentes/fuentes.css", "la fuente «%s» no existe" % u)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    con_plantillas = "--plantillas" in sys.argv
    plantilla = RAIZ / "Py" / "supuesto_plantilla_python.html"
    motor_actual = 0
    if plantilla.exists():
        mm = RE_MOTOR.search(plantilla.read_text(encoding="utf-8"))
        motor_actual = int(mm.group(1)) if mm else 0
    archivos = sorted((RAIZ / "supuestos").glob("*.html"))
    if args:
        quiere = {("supuesto_" + a if not a.startswith("supuesto_") else a) for a in args}
        archivos = [a for a in archivos if a.stem in quiere]
    if con_plantillas:
        archivos += sorted((RAIZ / "Py").glob("supuesto_plantilla_*.html"))
    resultados = {}
    for a in archivos:
        r = validar_supuesto(a, motor_actual)
        if r:
            resultados[a.stem] = r
    if not args:
        validar_menu(resultados)
        validar_sw()
    for linea in errores + avisos:
        print(linea)
    print("\n%d supuestos revisados · %d errores · %d avisos" % (len(archivos), len(errores), len(avisos)))
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())

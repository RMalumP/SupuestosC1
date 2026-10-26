# -*- coding: utf-8 -*-
"""
PONER TODO AL DÍA EN LOCAL Y PREPARAR LA CARPETA «PARA_SUBIR»
═════════════════════════════════════════════════════════════
Parte del editor de supuestos. Sin ventana (se puede probar sin tkinter).

Idea: te bajas el repositorio de GitHub, trabajas en local (editor, menú…) y al
final necesitas saber QUÉ archivos subir. Este módulo:

  1. Recuerda cómo estaba todo al bajarlo (huellas en «.estado_local.json»; ese
     archivo no se sube a GitHub).
  2. «Poner al día»: rehace con la plantilla actual la página de los supuestos que
     se quedaron con un motor antiguo (no se toca ni una pregunta).
  3. Copia a «PARA_SUBIR/» solo los archivos que son nuevos o distintos de lo
     descargado, con la misma estructura de carpetas, y escribe «LEEME_SUBIR.txt»
     con la lista. Basta con arrastrar el CONTENIDO de esa carpeta a GitHub.
  4. «Marcar como subido»: después de subirlo, el estado actual pasa a ser la nueva
     referencia y PARA_SUBIR se vacía.

Desde la línea de órdenes (el lanzador es editor_supuestos.py):
    python Py/editor_supuestos.py --actualizar    pone al día y prepara PARA_SUBIR
    python Py/editor_supuestos.py --para-subir    solo prepara PARA_SUBIR (con lo que haya)
    python Py/editor_supuestos.py --subido        marca todo como ya subido
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import datos_html

CARPETA = "PARA_SUBIR"
ESTADO = ".estado_local.json"
LEEME = "LEEME_SUBIR.txt"
RAIZ_DEFECTO = Path(__file__).resolve().parent.parent
CARPETAS_FUERA = {".git", ".github_cache", "node_modules", "__pycache__", CARPETA}
ARCHIVOS_FUERA = {ESTADO, ".editor_prefs.json", ".DS_Store", "Thumbs.db"}
SUFIJOS_FUERA = (".bak", ".pyc", ".tmp")


def es_proyecto(raiz):
    raiz = Path(raiz)
    return (raiz / "index.html").is_file() and (raiz / "supuestos").is_dir() and (raiz / "datos" / "supuestos-datos.js").is_file()


def raiz_de(ruta):
    """Carpeta del proyecto a la que pertenece un archivo (o None)."""
    p = Path(ruta).resolve()
    for cand in [p] + list(p.parents):
        if cand.is_dir() and es_proyecto(cand):
            return cand
    return None


_CACHE = {}      # ruta → ((fecha, tamaño), huella): no releer lo que no ha cambiado


def _huella(ruta):
    try:
        st = os.stat(ruta)
        clave = (st.st_mtime_ns, st.st_size)
    except OSError:
        clave = None
    previo = _CACHE.get(str(ruta))
    if clave and previo and previo[0] == clave:
        return previo[1]
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 16), b""):
            h.update(bloque)
    res = h.hexdigest()
    if clave:
        _CACHE[str(ruta)] = (clave, res)
    return res


def foto(raiz):
    """{ruta relativa con «/»: huella} de todos los archivos del proyecto que se suben a GitHub."""
    raiz = Path(raiz)
    res = {}
    for dirpath, dirnames, nombres in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in CARPETAS_FUERA]
        for n in nombres:
            if n in ARCHIVOS_FUERA or n.endswith(SUFIJOS_FUERA) or n.startswith(".recuperacion_"):
                continue
            p = Path(dirpath) / n
            res[p.relative_to(raiz).as_posix()] = _huella(p)
    return res


def leer_estado(raiz):
    ruta = Path(raiz) / ESTADO
    try:
        return json.loads(ruta.read_text(encoding="utf-8")).get("base")
    except (OSError, ValueError):
        return None


def _guardar_estado(raiz, base):
    (Path(raiz) / ESTADO).write_text(
        json.dumps({"version": 1, "base": base}, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def asegurar_base(raiz):
    """Si es la primera vez, el estado actual (recién descargado) pasa a ser la referencia.
    Devuelve True si la ha creado ahora."""
    if leer_estado(raiz) is not None:
        return False
    _guardar_estado(raiz, foto(raiz))
    return True


def diferencias(raiz):
    """(nuevos, modificados, borrados) respecto a la referencia, como listas de rutas."""
    base = leer_estado(raiz)
    if base is None:
        return [], [], []
    ahora = foto(raiz)
    nuevos = sorted(r for r in ahora if r not in base)
    modif = sorted(r for r in ahora if r in base and ahora[r] != base[r])
    borrados = sorted(r for r in base if r not in ahora)
    return nuevos, modif, borrados


def _motor_de(html):
    m = datos_html.RE_MOTOR.search(html or "")
    return int(m.group(1)) if m else 0


def poner_al_dia(raiz):
    """Rehace con la plantilla actual la página de cada supuesto con motor antiguo.
    Devuelve [(archivo, motor_viejo, motor_nuevo)] de los que ha tocado y [(archivo, motivo)] de los que no."""
    raiz = Path(raiz)
    plantilla_ruta = raiz / "Py" / datos_html.PLANTILLA_BASE
    if not plantilla_ruta.is_file():
        return [], [("(todos)", "falta Py/%s" % datos_html.PLANTILLA_BASE)]
    plantilla = plantilla_ruta.read_text(encoding="utf-8")
    nuevo = _motor_de(plantilla)
    hechos, saltados = [], []
    for p in sorted((raiz / "supuestos").glob("*.html")):
        try:
            datos, modo, html = datos_html.leer_html(p)
        except (OSError, ValueError) as e:
            saltados.append((p.name, "no se puede leer (%s)" % e))
            continue
        viejo = _motor_de(html)
        if viejo >= nuevo:
            continue
        if modo != "json":
            saltados.append((p.name, "es de plantilla antigua: ábrelo en el editor y usa «Pasar a plantilla nueva»"))
            continue
        datos_html.escribir_html(p, plantilla, datos, "json", copia=False)
        hechos.append((p.name, viejo, nuevo))
    return hechos, saltados


def preparar_para_subir(raiz):
    """Vacía y vuelve a llenar PARA_SUBIR con lo nuevo o modificado. Devuelve (nuevos, modificados, borrados)."""
    raiz = Path(raiz)
    nuevos, modif, borrados = diferencias(raiz)
    destino = raiz / CARPETA
    if destino.exists():
        shutil.rmtree(destino)
    if not (nuevos or modif or borrados):
        return nuevos, modif, borrados
    destino.mkdir()
    for rel in nuevos + modif:
        d = destino / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(raiz / rel, d)
    (destino / LEEME).write_text(_texto_leeme(nuevos, modif, borrados), encoding="utf-8")
    return nuevos, modif, borrados


def _texto_leeme(nuevos, modif, borrados):
    l = ["ARCHIVOS PARA SUBIR A GITHUB",
         "Preparado el %s." % datetime.now().strftime("%d/%m/%Y a las %H:%M"),
         "",
         "Cómo subirlos (en la web de GitHub):",
         "  1. Entra en el repositorio, en la rama que uses, y pulsa «Add file» > «Upload files».",
         "  2. Arrastra el CONTENIDO de esta carpeta (no la carpeta PARA_SUBIR en sí): las carpetas",
         "     «supuestos», «Py»… se arrastran enteras y GitHub las coloca donde corresponde.",
         "  3. Escribe un mensaje breve y pulsa «Commit changes».",
         "  4. Vuelve a abrir el editor y pulsa «Marcar como subido» (o ejecuta",
         "     «python Py/editor_supuestos.py --subido») para empezar de cero.",
         ""]
    for titulo, lista in (("NUEVOS (no existen todavía en GitHub)", nuevos), ("MODIFICADOS", modif)):
        if lista:
            l.append("%s: %d" % (titulo, len(lista)))
            l += ["  · " + r for r in lista]
            l.append("")
    if borrados:
        l.append("BORRADOS EN LOCAL (si quieres, bórralos también en GitHub a mano): %d" % len(borrados))
        l += ["  · " + r for r in borrados]
        l.append("")
    return "\n".join(l)


def marcar_subido(raiz):
    """El estado actual pasa a ser la referencia y PARA_SUBIR se vacía."""
    raiz = Path(raiz)
    _guardar_estado(raiz, foto(raiz))
    if (raiz / CARPETA).exists():
        shutil.rmtree(raiz / CARPETA)


def refrescar_silencioso(ruta_archivo):
    """Tras guardar algo en el editor: vuelve a preparar PARA_SUBIR. Nunca falla hacia fuera.
    Devuelve (nuevos, modificados, borrados) o None."""
    try:
        raiz = raiz_de(ruta_archivo)
        if raiz is None or leer_estado(raiz) is None:
            return None
        return preparar_para_subir(raiz)
    except OSError:
        return None


def resumen(nuevos, modif, borrados):
    n = len(nuevos) + len(modif)
    if not (n or borrados):
        return "No hay nada que subir: todo coincide con lo que descargaste."
    t = "%d archivo%s para subir (%d nuevo%s, %d modificado%s)" % (
        n, "" if n == 1 else "s", len(nuevos), "" if len(nuevos) == 1 else "s", len(modif), "" if len(modif) == 1 else "s")
    if borrados:
        t += " · %d borrado%s en local" % (len(borrados), "" if len(borrados) == 1 else "s")
    return t


def main(args=None):
    args = list(args if args is not None else sys.argv[1:])
    raiz = RAIZ_DEFECTO
    if not es_proyecto(raiz):
        print("No encuentro el proyecto (esta carpeta Py debe estar dentro de la carpeta que tiene index.html y supuestos/).")
        return 1
    if "--subido" in args:
        marcar_subido(raiz)
        print("Hecho: lo actual es ahora la referencia y PARA_SUBIR queda vacía.")
        return 0
    if asegurar_base(raiz):
        print("Primera vez en esta carpeta: lo que hay ahora cuenta como «lo descargado de GitHub».")
    if "--actualizar" in args:
        hechos, saltados = poner_al_dia(raiz)
        for a, v, n in hechos:
            print("✔ %s: motor %d → %d" % (a, v, n))
        for a, m in saltados:
            print("· %s: %s" % (a, m))
        if not hechos and not saltados:
            print("Todos los supuestos ya tienen el motor actual.")
    res = preparar_para_subir(raiz)
    print(resumen(*res))
    if res[0] or res[1]:
        print("Mira la carpeta %s (y su %s)." % (CARPETA, LEEME))
    return 0


if __name__ == "__main__":
    sys.exit(main())

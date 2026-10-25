# -*- coding: utf-8 -*-
"""
ALTA EN EL MENÚ SIN VENTANA
═══════════════════════════
Da de alta en el menú de inicio (supuestos-datos.js) los supuestos de la carpeta
supuestos/ que todavía no salen. Se lanza desde el mismo archivo de siempre:

    python Py/editor_supuestos.py --alta            pregunta dónde poner cada uno
    python Py/editor_supuestos.py --alta --auto     los pone en «Supuestos generales · Avanzados»
                                                    (luego se pueden mover desde el editor)

Lee título, número de preguntas y minutos del propio .html, así que no hay que escribir
nada a mano. Al terminar ejecuta el validador.
"""
import json
import re
import sys
from pathlib import Path

import menu_datos

RAIZ = Path(__file__).resolve().parent.parent
RE_JSON = re.compile(r'<script\b[^>]*\bid=["\']datos-supuesto["\'][^>]*>(.*?)</script>', re.S | re.I)
POR_DEFECTO = "generales/avanzados"


def _datos(ruta):
    m = RE_JSON.search(Path(ruta).read_text(encoding="utf-8"))
    return json.loads(m.group(1)) if m else None


def main(args=None, entrada=input):
    args = list(args if args is not None else sys.argv[1:])
    auto = "--auto" in args
    ruta_menu = RAIZ / menu_datos.ARCHIVO_MENU
    texto, menu = menu_datos.leer_archivo(ruta_menu)
    ya = set(menu_datos.archivos_del_menu(menu))
    nuevos = [p for p in sorted((RAIZ / "supuestos").glob("*.html")) if p.stem not in ya]
    if not nuevos:
        print("Todos los supuestos de la carpeta supuestos/ ya están en el menú. Nada que hacer.")
        return 0
    sitios = menu_datos.destinos(menu)
    for p in nuevos:
        d = _datos(p)
        if d is None:
            print("· %s: no tiene el bloque de datos del editor; lo salto." % p.name)
            continue
        ficha = menu_datos.ficha(p.stem, d)
        destino = POR_DEFECTO
        if not auto:
            print("\nNuevo: %s  (%s)" % (p.name, ficha["titulo"]))
            for i, (_, nombre) in enumerate(sitios, 1):
                print("  %d) %s" % (i, nombre))
            r = entrada("¿Dónde lo pongo? [número, Intro = %s] " % POR_DEFECTO).strip()
            if r.isdigit() and 1 <= int(r) <= len(sitios):
                destino = sitios[int(r) - 1][0]
        menu_datos.lista_de(menu, destino).append(ficha)
        print("✔ %s añadido a «%s»." % (p.name, dict(sitios).get(destino, destino)))
    menu_datos.escribir_archivo(ruta_menu, texto, menu)
    print("\nListo: supuestos-datos.js actualizado. Súbelo a GitHub junto con los supuestos nuevos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

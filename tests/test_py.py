# -*- coding: utf-8 -*-
"""Pruebas de la parte de Python (sin ventana): menú, alta, validador, lectura/escritura del HTML.
Se ejecutan con:  python3 tests/test_py.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = RAIZ / "Py"
sys.path.insert(0, str(PY))
sys.path.insert(0, str(RAIZ / "tests" / "stub_tkinter"))   # tkinter falso solo para importar el editor

import menu_datos          # noqa: E402
import datos_html          # noqa: E402


def copia_del_proyecto():
    """Copia mínima del proyecto en una carpeta temporal."""
    d = Path(tempfile.mkdtemp(prefix="supc1_"))
    shutil.copytree(PY, d / "Py", ignore=shutil.ignore_patterns("__pycache__", "*.bak"))
    shutil.copytree(RAIZ / "supuestos", d / "supuestos")
    for f in ("supuestos-datos.js", "sw.js", "index.html", "mi-estudio.html"):
        shutil.copy(RAIZ / f, d / f)
    for f in ["base-supuesto.css", "tema-supuesto.css", "tema-menu.css", "tema-resultados.css", "prefs.js", "pwa.js",
              "app-supuesto.js", "app-uso.js", "app-menu.js", "app-estudio.js", "app-telemetria.js", "app-sync.js",
              "sync-config.js", "normas-datos.js", "telemetria-config.js", "manifest.webmanifest"]:
        if (RAIZ / f).exists():
            shutil.copy(RAIZ / f, d / f)
    shutil.copytree(RAIZ / "fuentes", d / "fuentes")
    shutil.copytree(RAIZ / "icons", d / "icons")
    shutil.copytree(RAIZ / "resultados", d / "resultados")
    return d


def ejecutar(carpeta, *args):
    r = subprocess.run([sys.executable, *args], cwd=carpeta, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


class MenuDatos(unittest.TestCase):
    def test_ida_y_vuelta_sin_cambios(self):
        texto = (RAIZ / "supuestos-datos.js").read_text(encoding="utf-8")
        menu = menu_datos.leer(texto)
        self.assertEqual(menu_datos.escribir_texto(texto, menu), texto)
        self.assertEqual(len(menu_datos.archivos_del_menu(menu)), 9)

    def test_formato_antiguo_se_lee_y_se_convierte(self):
        antiguo = 'window.SUPUESTOS_DATOS = {"secciones":[{"id":"g","titulo":"G","grupos":[{"id":"i","titulo":"I","items":[' \
                  '{"archivo":"a","letra":"A","ref":"A","titulo":"T","desc":"D"}]}]}],"examenes":[]};'
        menu = menu_datos.leer(antiguo)
        nuevo = menu_datos.escribir_texto(antiguo, menu)
        self.assertIn("var SUPUESTOS", nuevo)
        self.assertEqual(menu_datos.leer(nuevo), menu)

    def test_coma_final_y_comentarios_se_toleran(self):
        t = (RAIZ / "supuestos-datos.js").read_text(encoding="utf-8")
        t = t.replace('"desc"', '"desc"', 1).replace("  ];\n  // <<< SUPUESTOS", "  // un comentario\n  ];\n  // <<< SUPUESTOS")
        t = t.replace("}\n  // un comentario", "},\n  // un comentario")
        self.assertEqual(len(menu_datos.archivos_del_menu(menu_datos.leer(t))), 9)

    def test_error_con_numero_de_linea(self):
        t = (RAIZ / "supuestos-datos.js").read_text(encoding="utf-8")
        t = t.replace('"letra": "T2I"', '"letra": T2I', 1)
        with self.assertRaises(ValueError) as cm:
            menu_datos.leer(t)
        self.assertRegex(str(cm.exception), r"línea \d+")

    def test_oculto_se_conserva(self):
        t = (RAIZ / "supuestos-datos.js").read_text(encoding="utf-8")
        menu = menu_datos.leer(t)
        menu["secciones"][0]["grupos"][0]["items"][0]["oculto"] = True
        menu2 = menu_datos.leer(menu_datos.escribir_texto(t, menu))
        self.assertTrue(menu2["secciones"][0]["grupos"][0]["items"][0]["oculto"])


class AltaYValidador(unittest.TestCase):
    def test_alta_automatica_de_un_supuesto_nuevo(self):
        d = copia_del_proyecto()
        try:
            shutil.copy(d / "supuestos" / "supuesto_2.html", d / "supuestos" / "supuesto_77.html")
            cod, _ = ejecutar(d, "Py/validar_supuestos.py")
            self.assertIn("no está en el menú", _)
            cod, sal = ejecutar(d, "Py/editor_supuestos.py", "--alta", "--auto")
            self.assertEqual(cod, 0, sal)
            self.assertIn("supuesto_77", sal)
            menu = menu_datos.leer((d / "supuestos-datos.js").read_text(encoding="utf-8"))
            self.assertIn("supuesto_77", menu_datos.archivos_del_menu(menu))
            cod, sal = ejecutar(d, "Py/validar_supuestos.py")
            self.assertEqual(cod, 0, sal)
            self.assertNotIn("no está en el menú", sal)
            cod, sal = ejecutar(d, "Py/editor_supuestos.py", "--alta", "--auto")
            self.assertIn("Nada que hacer", sal)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_el_validador_avisa_si_el_menu_apunta_a_un_archivo_inexistente(self):
        d = copia_del_proyecto()
        try:
            (d / "supuestos" / "supuesto_0.html").unlink()
            cod, sal = ejecutar(d, "Py/validar_supuestos.py")
            self.assertEqual(cod, 1)
            self.assertIn("supuesto_0", sal)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_sw_no_lleva_supuestos_a_mano(self):
        t = (RAIZ / "sw.js").read_text(encoding="utf-8")
        self.assertIn('importScripts("supuestos-datos.js")', t)
        self.assertNotIn('"supuestos/supuesto_', t)


class DatosHtml(unittest.TestCase):
    def test_leer_y_escribir_no_cambia_los_datos(self):
        for p in sorted((RAIZ / "supuestos").glob("*.html")):
            datos, modo, html = datos_html.leer_html(p)
            self.assertEqual(modo, "json", p.name)
            d = Path(tempfile.mkdtemp(prefix="supc1_"))
            try:
                destino = d / p.name
                nuevo = datos_html.escribir_html(destino, html, datos, modo)
                datos2, _, _ = datos_html.leer_html(destino)
                self.assertEqual(datos2, datos, p.name)
            finally:
                shutil.rmtree(d, ignore_errors=True)


class Editor(unittest.TestCase):
    def test_el_editor_se_importa_con_un_tkinter_falso(self):
        import editor_supuestos as e
        self.assertTrue(callable(e.leer_html) and callable(e.escribir_menu))
        self.assertEqual(e.version_motor('<meta name="motor-plantilla" content="8">'), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)

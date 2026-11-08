# -*- coding: utf-8 -*-
"""
PRUEBA DE LA VENTANA DEL EDITOR (con Tk de verdad)
══════════════════════════════════════════════════
tests/test_py.py prueba la lógica con un tkinter de mentira. Esta abre la ventana
real (en GitHub, en una pantalla virtual con xvfb-run) y comprueba que se monta,
que abre los supuestos y que lo básico responde: pestañas, formato, Ctrl+Z,
ayudas técnicas, buscar en todo, revisar y vista previa sin guardar.

    xvfb-run -a python3 tests/test_ventana.py      (Linux sin pantalla)
    python3 tests/test_ventana.py                   (con pantalla)

No guarda nada en los supuestos: trabaja sobre copias en una carpeta temporal.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "Py"))

try:
    import tkinter as tk
    tk.Tk().destroy()
    HAY_TK = True
except Exception:                 # sin tkinter o sin pantalla
    HAY_TK = False


@unittest.skipUnless(HAY_TK, "sin tkinter o sin pantalla (usa xvfb-run)")
class Ventana(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="supc1_ventana_"))
        os.environ["HOME"] = str(cls.tmp)
        import editor_comun
        editor_comun.PREFS = cls.tmp / ".editor_prefs.json"     # no tocar las preferencias de nadie
        import editor_supuestos
        cls.es = editor_supuestos
        cls.ec = editor_comun
        cls.app = editor_supuestos.EditorApp()
        cls.app.update()

    @classmethod
    def tearDownClass(cls):
        cls.app.hay_cambios = False
        cls.app._borrar_previas()
        cls.app.destroy()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _copia(self, nombre):
        """Copia del supuesto en supuestos/ con otro nombre (la vista previa necesita css/ y js/ al lado)."""
        destino = RAIZ / "supuestos" / ("_prueba_ventana_" + nombre)
        shutil.copy(RAIZ / "supuestos" / nombre, destino)
        self.addCleanup(lambda: destino.unlink() if destino.exists() else None)
        for extra in (destino.with_suffix(".html.bak"),):
            self.addCleanup(lambda e=extra: e.unlink() if e.exists() else None)
        return destino

    def test_abre_todos_los_supuestos_y_recorre_las_pestanas(self):
        app = self.app
        for ruta in sorted((RAIZ / "supuestos").glob("supuesto_*.html")):
            app._cargar_ruta(ruta)
            app.update()
            self.assertTrue(app.datos["preguntas"], ruta.name)
            for i in range(app.cuaderno.index("end")):
                app.cuaderno.select(i)
                app.update()
            app.refrescar_lista_preg(len(app.datos["preguntas"]) - 1)
            app.update()
            self.assertFalse(app.hay_cambios, "abrir y mirar no debe marcar cambios: %s" % ruta.name)

    def test_tabulador_y_deshacer_en_una_caja(self):
        ec = self.ec
        marco, t = ec.caja_texto(self.app)
        ec.poner_texto(t, "Hechos:\n<b>1)</b> uno;\n<b>2)</b> dos. <b>\n¿Cuál?</b>")
        t.mark_set("insert", "3.0")
        ec.formato_parrafos(t, "mas")
        self.app.update()
        guardado = ec.limpiar_texto(ec.sacar_texto(t))
        self.assertIn('<span class="sg-1"><b>2)</b> dos. </span>', guardado)
        self.assertTrue(guardado.endswith("<b>¿Cuál?</b>"))
        t.edit_undo()
        self.assertNotIn("sg-1", ec.sacar_texto(t))
        marco.destroy()

    def test_ayudas_tecnicas_y_revisar(self):
        app = self.app
        app._cargar_ruta(RAIZ / "supuestos" / "supuesto_T2.html")
        for ver in (True, False):
            self.ec.poner_ver_ayudas(ver)
            app.update()
        errores = app.comprobar()
        self.assertEqual(errores, [])

    def test_buscar_en_todo_y_vista_previa_sin_guardar(self):
        app = self.app
        ruta = self._copia("supuesto_T2.html")
        antes = ruta.read_text(encoding="utf-8")
        app._cargar_ruta(ruta)
        import herramientas_datos as hd
        hallazgos = hd.buscar(app.datos, "la")
        self.assertTrue(hallazgos)
        app.ir_a_sitio(hallazgos[-1][1])
        app.update()
        app.ir_a_pregunta(0)
        self.ec.poner_texto(app.txt_preg_q, "Pregunta (cambiado)")
        app.hay_cambios = True
        abiertos = []
        import webbrowser
        from urllib.parse import unquote, urlparse
        original = webbrowser.open
        webbrowser.open = lambda url, *a, **k: abiertos.append(url)
        self.addCleanup(setattr, webbrowser, "open", original)
        app.ver_navegador()
        self.assertTrue(abiertos and abiertos[-1].endswith(".htm"))
        previa = Path(unquote(urlparse(abiertos[-1]).path))
        self.assertIn("(cambiado)", previa.read_text(encoding="utf-8"))
        self.assertEqual(ruta.read_text(encoding="utf-8"), antes)     # el supuesto no se ha tocado
        app._borrar_previas()
        self.assertFalse(previa.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

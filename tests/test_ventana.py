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

    def test_imagenes_se_anaden_en_el_editor_y_se_reparten_al_guardar(self):
        app = self.app
        ruta = self._copia("supuesto_0.html")
        carpeta = RAIZ / "supuestos" / "img" / ruta.stem
        self.addCleanup(shutil.rmtree, carpeta, True)
        self.addCleanup(lambda: [(RAIZ / "supuestos" / "img").rmdir()] if (RAIZ / "supuestos" / "img").is_dir()
                        and not any((RAIZ / "supuestos" / "img").iterdir()) else None)
        menu = RAIZ / "datos" / "supuestos-datos.js"
        menu_antes = menu.read_bytes()
        self.addCleanup(menu.write_bytes, menu_antes)
        app._cargar_ruta(ruta)
        app.ir_a_pregunta(0)
        app.update()
        foto = self.tmp / "Foto de prueba.png"
        shutil.copy(RAIZ / "icons" / "icon-192.png", foto)
        self.assertEqual(app.imgs_preg.anadir_archivos([str(foto)] * 5 + [str(self.tmp / "nota.txt")]), 3)   # máximo 3
        app.imgs_preg.quitar()
        app.imgs_law.anadir_archivos([str(foto)])
        app.imgs_law.var_pie.set("Pie de prueba")
        app.imgs_law._cambio_pie()
        app.cuaderno.select(2)
        app.update()
        app.imgs_bloque.anadir_archivos([str(foto)])
        self.assertTrue(app.hay_cambios)
        app.volcar_todo()
        p = app.datos["preguntas"][0]
        self.assertEqual((len(p["imgs"]), len(p["imgsLaw"]), p["imgsLaw"][0]["pie"]), (2, 1, "Pie de prueba"))
        self.assertFalse(carpeta.exists())                     # hasta guardar no se copia nada
        from tkinter import messagebox
        original = messagebox.askyesno
        messagebox.askyesno = lambda *a, **k: True
        self.addCleanup(setattr, messagebox, "askyesno", original)
        app._pedir_grupo_menu = lambda archivo: None           # sin darlo de alta en el menú
        self.assertTrue(app._escribir(ruta))
        self.assertEqual([f.name for f in carpeta.iterdir()], ["foto-de-prueba.png"])
        import datos_html
        leido, _, _ = datos_html.leer_html(ruta)
        self.assertEqual(leido["preguntas"][0]["imgsLaw"], [{"src": "img/%s/foto-de-prueba.png" % ruta.stem, "pie": "Pie de prueba"}])
        self.assertEqual(len(leido["preguntas"][0]["imgs"]), 2)
        self.assertTrue(any(fb["imgs"] for e in leido["enunciados"] for fb in e["factBlocks"]))
        self.assertNotIn("origen", ruta.read_text(encoding="utf-8"))
        self.assertNotIn("nueva", app.imgs_law.caja.get(0))    # el recuadro ya la da por guardada

    def test_generar_simulacro_lo_abre_sin_archivo(self):
        app = self.app
        import simulacro
        import impugnaciones_datos as imp
        fuentes = [(r.stem, d) for r, d in imp.leer_supuestos(RAIZ)]
        datos, _ = simulacro.generar(fuentes, 10, 1, semilla=1, titulo="Simulacro de prueba")
        app.hay_cambios = False
        self.assertTrue(app.abrir_como_nuevo(datos))
        app.after(300, app.quit)
        app.mainloop()                          # el título se repinta con un poco de retraso
        self.assertIsNone(app.ruta)
        self.assertTrue(app.hay_cambios)
        self.assertEqual(len(app.datos["preguntas"]), len(datos["preguntas"]))
        self.assertIn("sin guardar *", app.title())
        import ventana_extra
        antes = set(app.winfo_children())
        ventana_extra.generar_simulacro(app)
        app.update()
        nuevas = [w for w in app.winfo_children() if w not in antes]
        self.assertTrue(nuevas)
        for w in nuevas:
            w.destroy()
        app.hay_cambios = False


if __name__ == "__main__":
    unittest.main(verbosity=2)

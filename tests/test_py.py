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
import sincronizar_local as sl  # noqa: E402


def copia_del_proyecto():
    """Copia mínima del proyecto en una carpeta temporal."""
    d = Path(tempfile.mkdtemp(prefix="supc1_"))
    shutil.copytree(PY, d / "Py", ignore=shutil.ignore_patterns("__pycache__", "*.bak"))
    shutil.copytree(RAIZ / "supuestos", d / "supuestos")
    for f in ("sw.js", "index.html", "mi-estudio.html", "privacidad.html", "manifest.webmanifest"):
        shutil.copy(RAIZ / f, d / f)
    for carpeta in ("js", "css", "datos", "config"):
        shutil.copytree(RAIZ / carpeta, d / carpeta)
    shutil.copytree(RAIZ / "fuentes", d / "fuentes")
    shutil.copytree(RAIZ / "icons", d / "icons")
    shutil.copytree(RAIZ / "resultados", d / "resultados")
    shutil.copytree(RAIZ / "impugnaciones", d / "impugnaciones")
    return d


def ejecutar(carpeta, *args):
    r = subprocess.run([sys.executable, *args], cwd=carpeta, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


class MenuDatos(unittest.TestCase):
    def test_ida_y_vuelta_sin_cambios(self):
        texto = (RAIZ / "datos" / "supuestos-datos.js").read_text(encoding="utf-8")
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
        t = (RAIZ / "datos" / "supuestos-datos.js").read_text(encoding="utf-8")
        t = t.replace('"desc"', '"desc"', 1).replace("  ];\n  // <<< SUPUESTOS", "  // un comentario\n  ];\n  // <<< SUPUESTOS")
        t = t.replace("}\n  // un comentario", "},\n  // un comentario")
        self.assertEqual(len(menu_datos.archivos_del_menu(menu_datos.leer(t))), 9)

    def test_error_con_numero_de_linea(self):
        t = (RAIZ / "datos" / "supuestos-datos.js").read_text(encoding="utf-8")
        t = t.replace('"letra": "T2I"', '"letra": T2I', 1)
        with self.assertRaises(ValueError) as cm:
            menu_datos.leer(t)
        self.assertRegex(str(cm.exception), r"línea \d+")

    def test_oculto_se_conserva(self):
        t = (RAIZ / "datos" / "supuestos-datos.js").read_text(encoding="utf-8")
        menu = menu_datos.leer(t)
        menu["secciones"][0]["grupos"][0]["items"][0]["oculto"] = True
        menu2 = menu_datos.leer(menu_datos.escribir_texto(t, menu))
        self.assertTrue(menu2["secciones"][0]["grupos"][0]["items"][0]["oculto"])


class EdicionDelMenu(unittest.TestCase):
    def setUp(self):
        self.t = (RAIZ / "datos" / "supuestos-datos.js").read_text(encoding="utf-8")
        self.m = menu_datos.leer(self.t)

    def orden(self, clave):
        return [i["archivo"] for c, lista in menu_datos._listas(self.m) if c == clave for i in lista]

    def test_subir_bajar_y_limites(self):
        a, b = self.orden("generales/avanzados")[:2]
        self.assertTrue(menu_datos.mover(self.m, b, -1))
        self.assertEqual(self.orden("generales/avanzados")[:2], [b, a])
        self.assertFalse(menu_datos.mover(self.m, b, -1))          # ya es el primero
        self.assertTrue(menu_datos.mover(self.m, b, 1))

    def test_mover_a_otro_grupo_y_guardar(self):
        self.assertTrue(menu_datos.mover_a(self.m, "supuesto_0", "temas/iniciales"))
        m2 = menu_datos.leer(menu_datos.escribir_texto(self.t, self.m))
        self.assertEqual(menu_datos.buscar(m2, "supuesto_0")[0], "temas/iniciales")

    def test_editar_ocultar_quitar_y_anadir(self):
        menu_datos.editar(self.m, "supuesto_1", titulo="  Nuevo título ", letra="Z9")
        it = menu_datos.buscar(self.m, "supuesto_1")
        self.assertEqual((it[1][it[2]]["titulo"], it[1][it[2]]["letra"]), ("Nuevo título", "Z9"))
        menu_datos.ocultar(self.m, "supuesto_1")
        self.assertTrue(menu_datos.buscar(self.m, "supuesto_1")[1][menu_datos.buscar(self.m, "supuesto_1")[2]]["oculto"])
        menu_datos.ocultar(self.m, "supuesto_1", False)
        self.assertTrue(menu_datos.quitar(self.m, "supuesto_1"))
        self.assertIsNone(menu_datos.buscar(self.m, "supuesto_1"))
        menu_datos.anadir(self.m, {"archivo": "supuesto_1", "letra": "1", "ref": "S1", "titulo": "t", "desc": "d"}, "examenes")
        self.assertEqual(menu_datos.buscar(self.m, "supuesto_1")[0], "examenes")

    def test_secciones_y_grupos(self):
        sid = menu_datos.crear_seccion(self.m, "Supuestos de Repaso")
        self.assertEqual(sid, "supuestos-de-repaso")
        clave = menu_datos.crear_grupo(self.m, sid, "Repaso final")
        self.assertEqual(clave, "supuestos-de-repaso/repaso-final")
        with self.assertRaises(ValueError):
            menu_datos.crear_seccion(self.m, "Supuestos de Repaso")
        menu_datos.mover_a(self.m, "supuesto_2", clave)
        with self.assertRaises(ValueError):
            menu_datos.eliminar_contenedor(self.m, clave)           # no está vacío
        menu_datos.mover_a(self.m, "supuesto_2", "generales/avanzados")
        self.assertTrue(menu_datos.eliminar_contenedor(self.m, clave))
        self.assertTrue(menu_datos.renombrar(self.m, "temas", "Por temas"))
        self.assertTrue(menu_datos.mover_contenedor(self.m, "temas", 1))
        self.assertEqual(self.m["secciones"][1]["id"], "temas")
        m2 = menu_datos.leer(menu_datos.escribir_texto(self.t, self.m))
        self.assertEqual([s["id"] for s in m2["secciones"]][:2], ["generales", "temas"])

    def test_sin_alta(self):
        menu_datos.quitar(self.m, "supuesto_3")
        self.assertEqual(menu_datos.sin_alta(self.m, RAIZ / "supuestos"), ["supuesto_3"])


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
            menu = menu_datos.leer((d / "datos" / "supuestos-datos.js").read_text(encoding="utf-8"))
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
        self.assertIn('importScripts("datos/supuestos-datos.js"', t)
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


class SincronizarLocal(unittest.TestCase):
    def test_flujo_completo_hasta_para_subir(self):
        d = copia_del_proyecto()
        try:
            self.assertTrue(sl.asegurar_base(d))
            self.assertFalse(sl.asegurar_base(d))
            self.assertEqual(sl.diferencias(d), ([], [], []))
            # un supuesto con motor antiguo (como recién bajado de GitHub)
            f = d / "supuestos" / "supuesto_2.html"
            f.write_text(f.read_text(encoding="utf-8").replace('name="motor-plantilla" content="9"', 'name="motor-plantilla" content="6"'), encoding="utf-8")
            sl.marcar_subido(d)
            antes = datos_html.leer_html(f)[0]
            hechos, saltados = sl.poner_al_dia(d)
            self.assertEqual([h[0] for h in hechos], ["supuesto_2.html"])
            self.assertEqual(datos_html.leer_html(f)[0], antes, "las preguntas no deben cambiar")
            self.assertEqual(sl.poner_al_dia(d), ([], []))
            self.assertFalse(list((d / "supuestos").glob("*.bak")))
            # un cambio más: archivo nuevo y menú
            shutil.copy(d / "supuestos" / "supuesto_0.html", d / "supuestos" / "supuesto_88.html")
            (d / "datos" / "supuestos-datos.js").write_text((d / "datos" / "supuestos-datos.js").read_text(encoding="utf-8") + "\n// x\n", encoding="utf-8")
            nuevos, modif, borrados = sl.preparar_para_subir(d)
            self.assertEqual(nuevos, ["supuestos/supuesto_88.html"])
            self.assertEqual(modif, ["datos/supuestos-datos.js", "supuestos/supuesto_2.html"])
            self.assertTrue((d / "PARA_SUBIR" / "supuestos" / "supuesto_88.html").is_file())
            self.assertIn("supuestos/supuesto_88.html", (d / "PARA_SUBIR" / "LEEME_SUBIR.txt").read_text(encoding="utf-8"))
            self.assertFalse((d / "PARA_SUBIR" / "index.html").exists())
            (d / "supuestos" / "supuesto_88.html").unlink()
            self.assertEqual(sl.diferencias(d)[2], [])
            sl.marcar_subido(d)
            self.assertFalse((d / "PARA_SUBIR").exists())
            self.assertEqual(sl.diferencias(d), ([], [], []))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_borrados_y_carpeta_no_se_cuenta_a_si_misma(self):
        d = copia_del_proyecto()
        try:
            sl.asegurar_base(d)
            (d / "supuestos" / "supuesto_1.html").unlink()
            n, m, b = sl.preparar_para_subir(d)
            self.assertEqual(b, ["supuestos/supuesto_1.html"])
            self.assertIn("BORRADOS", (d / "PARA_SUBIR" / "LEEME_SUBIR.txt").read_text(encoding="utf-8"))
            self.assertEqual(sl.diferencias(d)[2], ["supuestos/supuesto_1.html"])   # PARA_SUBIR no cuenta
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_desde_la_linea_de_ordenes(self):
        d = copia_del_proyecto()
        try:
            f = d / "supuestos" / "supuesto_3.html"
            f.write_text(f.read_text(encoding="utf-8").replace('name="motor-plantilla" content="9"', 'name="motor-plantilla" content="5"'), encoding="utf-8")
            cod, sal = ejecutar(d, "Py/editor_supuestos.py", "--actualizar")
            self.assertEqual(cod, 0, sal)
            self.assertIn("Primera vez", sal)
            self.assertIn("supuesto_3.html: motor 5 → 9", sal)
            self.assertIn("1 archivo para subir", sal)
            self.assertTrue((d / "PARA_SUBIR" / "supuestos" / "supuesto_3.html").is_file())
            cod, sal = ejecutar(d, "Py/editor_supuestos.py", "--subido")
            self.assertFalse((d / "PARA_SUBIR").exists())
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Corazon(unittest.TestCase):
    def test_config_corazon_por_defecto_y_se_respeta(self):
        self.assertIs(datos_html.normalizar({"config": {}})["config"]["corazon"], True)
        self.assertIs(datos_html.normalizar({"config": {"corazon": False}})["config"]["corazon"], False)
        self.assertIs(datos_html.datos_vacios()["config"]["corazon"], True)


class Editor(unittest.TestCase):
    def test_el_editor_se_importa_con_un_tkinter_falso(self):
        import editor_supuestos as e
        self.assertTrue(callable(e.leer_html) and callable(e.escribir_menu))
        self.assertEqual(e.version_motor('<meta name="motor-plantilla" content="9">'), 9)
        import ventana_menu, ventana_subir          # las ventanas también deben cargar
        self.assertTrue(callable(ventana_menu.abrir) and callable(ventana_subir.abrir))


import herramientas_datos as hd  # noqa: E402


class Herramientas(unittest.TestCase):
    def datos(self):
        d = datos_html.datos_vacios()
        d["preguntas"] = [datos_html.pregunta_vacia(None, "B1") for _ in range(3)]
        d["preguntas"][0]["q"] = "El plazo es de diez días"
        d["preguntas"][1]["q"] = "Otro plazo"
        return d

    def test_historial(self):
        d = self.datos()
        h = hd.Historial()
        h.iniciar(d)
        d["preguntas"].append(datos_html.pregunta_vacia(None, "B1"))
        h.anotar(d)
        previo = h.deshacer(d)
        self.assertEqual(len(previo["preguntas"]), 3)
        self.assertEqual(len(h.rehacer()["preguntas"]), 4)
        self.assertIsNone(h.rehacer())

    def test_buscar_y_reemplazar(self):
        d = self.datos()
        self.assertEqual(len(hd.buscar(d, "PLAZO")), 2)
        self.assertEqual(len(hd.buscar(d, "PLAZO", sensible=True)), 0)
        self.assertEqual(hd.reemplazar(d, "plazo", "término"), 2)
        self.assertIn("término", d["preguntas"][0]["q"])

    def test_importar_texto(self):
        t = ("1) ¿Cuál es?\na) uno\nb) *dos\nc) tres\nMotivación: art. 1\n\n"
             "2) Varias\na) x\nb) y\nc) z\nCorrecta: a, c\n\nsolo texto\n")
        p, av = hd.importar_texto(t, "B2")
        self.assertEqual(len(p), 2)
        self.assertEqual(p[0]["correctas"], [1])
        self.assertEqual(p[0]["law"], "art. 1")
        self.assertEqual(p[1]["correctas"], [0, 2])
        self.assertTrue(p[1]["multiple"])
        self.assertEqual(p[0]["bloqueId"], "B2")
        self.assertEqual(len(av), 1)

    def test_importar_csv(self):
        p, av = hd.importar_csv("pregunta;a;b;c;d;correcta;motivación\n¿Cuál?;1;2;3;4;c;art. 5\n")
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["a"], ["1", "2", "3", "4"])
        self.assertEqual(p[0]["correctas"], [2])
        self.assertEqual(p[0]["law"], "art. 5")

    def test_problemas(self):
        d = self.datos()
        d["preguntas"][1]["q"] = ""
        d["preguntas"][2]["a"] = ["igual", "igual", "x", "y"]
        f = hd.problemas_por_pregunta(d)
        self.assertEqual(f[1][0], "error")
        self.assertEqual(f[2][0], "aviso")

    def test_recuperacion(self):
        with tempfile.TemporaryDirectory() as c:
            r = hd.ruta_recuperacion("x/s.html", c)
            self.assertTrue(hd.guardar_recuperacion(r, {"a": 1}))
            self.assertEqual(hd.leer_recuperacion(r), {"a": 1})


import git_sync as gs  # noqa: E402


def _g(carpeta, *a):
    subprocess.run(["git", "-C", str(carpeta), *a], check=True, capture_output=True, text=True)


@unittest.skipUnless(gs.hay_git(), "git no instalado")
class GitSync(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix="supc1_git_"))
        _g(self.t, "init", "-q", "--bare", "-b", "main", "remoto.git")
        _g(self.t, "clone", "-q", "remoto.git", "uno")
        self.a = self.t / "uno"
        for k, v in (("user.name", "Prueba"), ("user.email", "p@p.p")):
            _g(self.a, "config", k, v)
        (self.a / "supuestos").mkdir()
        (self.a / "supuestos" / "a.html").write_text("a", encoding="utf-8")
        (self.a / ".gitignore").write_text("*.bak\n", encoding="utf-8")
        _g(self.a, "add", "-A")
        _g(self.a, "commit", "-q", "-m", "inicio")
        _g(self.a, "push", "-q", "-u", "origin", "main")
        _g(self.a, "remote", "set-head", "origin", "main")

    def test_estado_y_exclusiones(self):
        (self.a / "supuestos" / "a.html").write_text("cambiado", encoding="utf-8")
        (self.a / "supuestos" / "b.html").write_text("nuevo", encoding="utf-8")
        (self.a / ".recuperacion_x.json").write_text("{}", encoding="utf-8")
        (self.a / ".editor_prefs.json").write_text("{}", encoding="utf-8")
        (self.a / "x.html.bak").write_text("{}", encoding="utf-8")
        (self.a / "PARA_SUBIR").mkdir()
        (self.a / "PARA_SUBIR" / "z.html").write_text("z", encoding="utf-8")
        nuevos, modif, borrados = gs.estado(self.a)
        self.assertEqual(nuevos, ["supuestos/b.html"])
        self.assertEqual(modif, ["supuestos/a.html"])
        self.assertEqual(borrados, [])

    def test_subir_a_rama_del_dia_solo_lo_marcado(self):
        (self.a / "supuestos" / "a.html").write_text("cambiado", encoding="utf-8")
        (self.a / "supuestos" / "b.html").write_text("nuevo", encoding="utf-8")
        from datetime import date
        txt, _ = gs.subir(self.a, ["supuestos/a.html"], "cambio", "dia", hoy=date(2026, 10, 26))
        self.assertIn("editor-2026-10-26", txt)
        ramas = subprocess.run(["git", "-C", str(self.t / "remoto.git"), "branch"], capture_output=True,
                               text=True).stdout
        self.assertIn("editor-2026-10-26", ramas)
        self.assertEqual(gs.estado(self.a)[0], ["supuestos/b.html"])     # b no se subió

    def test_subir_a_la_principal_desde_otra_rama(self):
        _g(self.a, "checkout", "-q", "-b", "otra")
        (self.a / "supuestos" / "a.html").write_text("v2", encoding="utf-8")
        gs.subir(self.a, ["supuestos/a.html"], "directo", "principal")
        self.assertEqual(gs.rama_actual(self.a), "main")
        self.assertEqual(gs.rama_principal(self.a), "main")
        _g(self.t, "clone", "-q", "remoto.git", "dos")
        self.assertEqual((self.t / "dos" / "supuestos" / "a.html").read_text(encoding="utf-8"), "v2")

    def test_traer_y_errores(self):
        _g(self.t, "clone", "-q", "remoto.git", "dos")
        dos = self.t / "dos"
        for k, v in (("user.name", "Otro"), ("user.email", "o@o.o")):
            _g(dos, "config", k, v)
        (dos / "supuestos" / "a.html").write_text("web", encoding="utf-8")
        _g(dos, "commit", "-q", "-am", "desde la web")
        _g(dos, "push", "-q")
        self.assertIn("Traído", gs.traer(self.a))
        self.assertEqual((self.a / "supuestos" / "a.html").read_text(encoding="utf-8"), "web")
        with self.assertRaises(gs.ErrorGit):
            gs.subir(self.a, [], "x", "dia")
        with self.assertRaises(gs.ErrorGit):
            gs.subir(self.a, ["supuestos/a.html"], "  ", "dia")

    def test_sin_clon_y_traduccion(self):
        self.assertFalse(gs.es_clon(self.t))
        self.assertIn("quién eres", gs.traducir("Please tell me who you are"))
        self.assertIn("Actualizo a.html", gs.mensaje_sugerido([], ["x/a.html"], []))


if __name__ == "__main__":
    unittest.main(verbosity=2)

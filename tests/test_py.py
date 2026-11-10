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
import exportar_autonomo  # noqa: E402
import sincronizar_local as sl  # noqa: E402

MOTOR_ACTUAL = datos_html.version_motor((PY / datos_html.PLANTILLA_BASE).read_text(encoding="utf-8"))


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
        self.assertGreater(len(menu_datos.archivos_del_menu(menu)), 0)

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
        original = menu_datos.archivos_del_menu(menu_datos.leer(
            (RAIZ / "datos" / "supuestos-datos.js").read_text(encoding="utf-8")))
        self.assertEqual(len(menu_datos.archivos_del_menu(menu_datos.leer(t))), len(original))

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
        self.assertIn("supuesto_3", menu_datos.sin_alta(self.m, RAIZ / "supuestos"))


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
            f.write_text(f.read_text(encoding="utf-8").replace('name="motor-plantilla" content="%d"' % MOTOR_ACTUAL, 'name="motor-plantilla" content="6"'), encoding="utf-8")
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
            f.write_text(f.read_text(encoding="utf-8").replace('name="motor-plantilla" content="%d"' % MOTOR_ACTUAL, 'name="motor-plantilla" content="5"'), encoding="utf-8")
            cod, sal = ejecutar(d, "Py/editor_supuestos.py", "--actualizar")
            self.assertEqual(cod, 0, sal)
            self.assertIn("Primera vez", sal)
            self.assertIn("supuesto_3.html: motor 5 → %d" % MOTOR_ACTUAL, sal)
            self.assertIn("1 archivo para subir", sal)
            self.assertTrue((d / "PARA_SUBIR" / "supuestos" / "supuesto_3.html").is_file())
            cod, sal = ejecutar(d, "Py/editor_supuestos.py", "--subido")
            self.assertFalse((d / "PARA_SUBIR").exists())
        finally:
            shutil.rmtree(d, ignore_errors=True)


class JustificadoYMarcas(unittest.TestCase):
    def test_justificado_y_panel_por_defecto_y_valores_raros(self):
        cfg = datos_html.normalizar({})["config"]
        self.assertEqual(cfg["justificar"], {"enunciado": True, "pregunta": True, "motivacion": True})
        self.assertTrue(cfg["panel"]["tema"]["visible"])
        self.assertFalse(cfg["panel"]["tema"]["activa"])
        self.assertTrue(cfg["panel"]["deslizar"]["activa"])
        raro = datos_html.normalizar({"config": {"justificar": {"pregunta": False}, "panel": {"atajos": {"visible": False}, "tema": "x"}}})["config"]
        self.assertFalse(raro["justificar"]["pregunta"])
        self.assertTrue(raro["justificar"]["enunciado"])
        self.assertFalse(raro["panel"]["atajos"]["visible"])
        self.assertTrue(raro["panel"]["tema"]["visible"])

    def test_el_css_justifica_por_defecto_y_se_apaga_por_clase(self):
        css = (RAIZ / "css" / "base-supuesto.css").read_text(encoding="utf-8")
        for pieza in (".q-text", ".feedback-body p", ".fact-block p", "no-just-enun", "no-just-preg", "no-just-mot", ".al-i"):
            self.assertIn(pieza, css)
        js = (RAIZ / "js" / "app-supuesto.js").read_text(encoding="utf-8")
        self.assertIn("no-just-enun", js)

    def test_borrar_lo_visible_conserva_las_marcas(self):
        import editor_comun as ec
        self.assertEqual(ec.solo_etiquetas("b<b>cd</b>e"), "")
        self.assertEqual(ec.solo_etiquetas("b<b>cd"), "<b>")
        self.assertEqual(ec.solo_etiquetas('x<span class="al-i">y</span>'), "")
        self.assertEqual(ec.quitar_pares_vacios("a<b></b>b<i><u></u></i>"), "ab")
        self.assertEqual(ec.quitar_pares_vacios("<p></p>"), "<p></p>")        # no es de formato

    def test_izquierda_y_justificar_son_clases_de_parrafo(self):
        import editor_comun as ec
        self.assertIn("al-i", ec.CLASES_PARRAFO)
        env = ec.envoltorio_parrafo('<span class="al-i sg-1">hola</span>')
        self.assertEqual(env, ({"al-i", "sg-1"}, "hola"))


class Corazon(unittest.TestCase):
    def test_config_corazon_por_defecto_y_se_respeta(self):
        self.assertIs(datos_html.normalizar({"config": {}})["config"]["corazon"], True)
        self.assertIs(datos_html.normalizar({"config": {"corazon": False}})["config"]["corazon"], False)
        self.assertIs(datos_html.datos_vacios()["config"]["corazon"], True)


class Editor(unittest.TestCase):
    def test_el_editor_se_importa_con_un_tkinter_falso(self):
        import editor_supuestos as e
        import editor_comun as ec
        self.assertTrue(isinstance(e.EditorApp, type))
        self.assertTrue(callable(ec.leer_html) and callable(ec.escribir_menu))
        self.assertEqual(ec.version_motor('<meta name="motor-plantilla" content="9">'), 9)
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

    def test_buscar_en_todo_sin_que_estorbe_el_formato(self):
        d = self.datos()
        e = datos_html.enunciado_vacio("E1")
        e["factBlocks"] = [datos_html.bloque_hechos_vacio("H1")]
        e["factBlocks"][0]["paragraphs"] = ["Recurso en plazo de diez <b>días</b> hábiles."]
        e["timeline"] = [datos_html.hito_vacio()]
        e["timeline"][0]["text"] = "Diez días después"
        d["enunciados"] = [e]
        d["preguntas"][2]["law"] = "art. 1 · <i>diez</i> días"
        rutas = [r for _n, r, _d, _f in hd.buscar(d, "diez días")]
        self.assertIn(("enunciados", 0, "factBlocks", 0, "paragraphs", 0), rutas)
        self.assertIn(("enunciados", 0, "timeline", 0, "text"), rutas)
        self.assertIn(("preguntas", 2, "law"), rutas)
        # Solo en un sitio y sin perder la negrita.
        n = hd.reemplazar(d, "diez días", "quince días", solo={("enunciados", 0, "factBlocks", 0, "paragraphs", 0)})
        self.assertEqual(n, 1)
        self.assertEqual(e["factBlocks"][0]["paragraphs"][0], "Recurso en plazo de quince días hábiles.")
        self.assertEqual(e["timeline"][0]["text"], "Diez días después")

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
        self.assertEqual(f[2], ("error", "opciones repetidas"))   # igual que el validador
        d["preguntas"][2]["a"] = ["a", "b", "c", "d"]
        d["preguntas"][2]["law"] = ""
        self.assertEqual(hd.problemas_por_pregunta(d)[2], ("aviso", "sin motivación"))

    def test_un_solo_revisor(self):
        import revision
        d = self.datos()
        d["preguntas"][0]["a"] = ["a", "b", "c", "d"]
        d["preguntas"][0]["correctas"] = [0, 2]                 # varias sin «múltiple»
        d["preguntas"][1]["a"] = ["e", "f", "g", "h"]
        d["preguntas"][1]["correctas"] = [9]                    # apunta fuera
        h = revision.revisar(d)
        self.assertEqual(revision.por_pregunta(h)[0], ("error", "varias correctas"))
        self.assertEqual(revision.por_pregunta(h)[1], ("error", "correcta perdida"))
        # Lo que marca la lista es exactamente lo que impide publicar.
        graves = hd.errores_graves(d)
        self.assertTrue(any(g.startswith("Pregunta 1:") for g in graves))
        self.assertTrue(any(g.startswith("Pregunta 2:") for g in graves))
        # El JSON tal cual del archivo (formato antiguo con «c») también vale.
        crudo = {"config": {"titulo": "T", "minutos": 10},
                 "preguntas": [{"q": "x", "a": ["a", "b"], "c": 1, "law": "art. 1"}]}
        self.assertEqual(revision.errores(revision.revisar(crudo)), [])

    def test_recuperacion(self):
        with tempfile.TemporaryDirectory() as c:
            r = hd.ruta_recuperacion("x/s.html", c)
            self.assertTrue(hd.guardar_recuperacion(r, {"a": 1}))
            self.assertEqual(hd.leer_recuperacion(r), {"a": 1})


import publicar as pb  # noqa: E402


class Extras(unittest.TestCase):
    def datos(self):
        d = datos_html.datos_vacios()
        mk = datos_html.pregunta_vacia
        d["preguntas"] = [mk(None, "B1") for _ in range(3)]
        d["preguntas"][0].update(q="¿Cuál es el plazo para resolver el recurso de alzada?", law="Art. 15 LPAC")
        d["preguntas"][1].update(q="Cual es el plazo para resolver el recurso de alzada", law="Art. 99 de la norma rara")
        d["preguntas"][2].update(q="Otra cosa distinta", a=["x", "y", "z", "w"], correctas=[2], c=2)
        return d

    def test_soluciones_al_final(self):
        t = ("1) Primera\na) uno\nb) dos\n\n2) Segunda\na) tres\nb) cuatro\nc) cinco\n\nSoluciones: 1-b 2-c\n")
        p, av = hd.importar_texto(t)
        self.assertEqual(len(p), 2)
        self.assertEqual(p[0]["correctas"], [1])
        self.assertEqual(p[1]["correctas"], [2])
        self.assertEqual([a for a in av if "sin correcta" in a], [])

    def test_errores_graves_y_duplicados(self):
        d = self.datos()
        d["preguntas"][2]["q"] = ""
        self.assertTrue(any("Pregunta 3" in e for e in hd.errores_graves(d)))
        dup = hd.duplicados(d)
        self.assertEqual(dup[0][:3], (1, "este", 2))

    def test_estadisticas_y_citas(self):
        d = self.datos()
        self.assertIn("Letra de la respuesta correcta", hd.estadisticas(d))
        normas = [{"siglas": ["LPAC"], "boe": "BOE-A-2015-10565"}]
        citas = hd.citas_sin_norma(d, normas)
        self.assertEqual([c[0] for c in citas], [2])

    def test_plantillas(self):
        for nombre in hd.PLANTILLAS:
            p = hd.pregunta_de_plantilla(nombre, "B2")
            self.assertEqual(p["bloqueId"], "B2")
            self.assertTrue(p["correctas"])

    def test_version(self):
        with tempfile.TemporaryDirectory() as c:
            (Path(c) / "config").mkdir()
            (Path(c) / "config" / "version.js").write_text('self.SUPC1_VERSION = "v28.9";\n', encoding="utf-8")
            self.assertEqual(pb.subir_version(c), ("v28.9", "v28.10"))
            self.assertEqual(pb.version_actual(c), "v28.10")

    def test_historial_de_archivos(self):
        from datetime import datetime, timedelta
        with tempfile.TemporaryDirectory() as c:
            f = Path(c) / "s.html"
            f.write_text("a", encoding="utf-8")
            base = datetime(2026, 1, 1, 10, 0, 0)
            for k in range(14):
                pb.guardar_copia(f, c, base + timedelta(seconds=k))
            copias = pb.copias_de(f, c)
            self.assertEqual(len(copias), pb.COPIAS)
            self.assertEqual(pb.etiqueta_copia(copias[0]), "01/01/2026 10:00:13")

    def test_recientes_y_ayuda(self):
        with tempfile.TemporaryDirectory() as c:
            f = Path(c) / "a.html"
            f.write_text("x", encoding="utf-8")
            pr = {}
            pb.anotar_reciente(pr, f)
            pb.anotar_reciente(pr, Path(c) / "no_existe.html")
            self.assertEqual(pb.recientes(pr), [str(f)])
        texto = (PY / "INSTRUCCIONES.txt").read_text(encoding="utf-8")
        titulo, cuerpo = pb.ayuda_para(texto, 1)
        self.assertIn("BLOQUES", titulo.upper())
        self.assertTrue(cuerpo.strip())
        self.assertIn("NORMAS", pb.ayuda_para(texto, 6)[0].upper())

    def test_impugnaciones_csv(self):
        filas = pb.leer_impugnaciones("Marca temporal,Supuesto,Pregunta,Texto\n01/01,supuesto_1,¿Qué?,Mal\n,,,\n")
        self.assertEqual(len(filas), 1)
        self.assertEqual(pb.columna(filas[0], "supuesto"), "supuesto_1")
        self.assertTrue(pb.url_csv("ID", "Impugnaciones").startswith("https://docs.google.com/spreadsheets/d/ID/"))
        self.assertEqual(pb.config_impugnaciones(RAIZ)[1], "Impugnaciones")


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
        self.assertEqual(gs.rama_actual(self.a), "otra")              # no te cambia de rama
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

    def _otro_clon(self):
        _g(self.t, "clone", "-q", "remoto.git", "dos")
        dos = self.t / "dos"
        for k, v in (("user.name", "Otro"), ("user.email", "o@o.o")):
            _g(dos, "config", k, v)
        return dos

    def _en_remoto(self, rama, ruta):
        r = subprocess.run(["git", "-C", str(self.t / "remoto.git"), "show", "%s:%s" % (rama, ruta)],
                           capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None

    def test_rama_del_dia_sale_de_lo_ultimo_de_github_y_no_pisa(self):
        from datetime import date
        hoy = date(2026, 11, 8)
        dos = self._otro_clon()
        (dos / "supuestos" / "c.html").write_text("de otro", encoding="utf-8")
        _g(dos, "add", "-A")
        _g(dos, "commit", "-q", "-m", "otro archivo")
        _g(dos, "push", "-q")
        (self.a / "supuestos" / "a.html").write_text("mío", encoding="utf-8")
        gs.subir(self.a, ["supuestos/a.html"], "mío", "dia", hoy=hoy)
        rama = gs.nombre_rama_dia(hoy)
        self.assertEqual(self._en_remoto(rama, "supuestos/a.html"), "mío")
        self.assertEqual(self._en_remoto(rama, "supuestos/c.html"), "de otro")   # no se deshace lo de otro
        self.assertEqual(gs.rama_actual(self.a), "main")
        self.assertEqual(gs.ya_subidos(self.a, ["supuestos/a.html"], "origin/" + rama), {"supuestos/a.html"})
        # Un archivo que también cambió en GitHub: se para sin tocar nada.
        (dos / "supuestos" / "a.html").write_text("web", encoding="utf-8")
        _g(dos, "commit", "-q", "-am", "web")
        _g(dos, "push", "-q")
        with self.assertRaises(gs.ErrorGit):
            gs.subir(self.a, ["supuestos/a.html"], "otra vez", "principal")
        self.assertEqual(self._en_remoto("main", "supuestos/a.html"), "web")

    def test_traer_tras_fusionar_la_rama_del_dia(self):
        from datetime import date
        (self.a / "supuestos" / "a.html").write_text("mío", encoding="utf-8")
        (self.a / "supuestos" / "sin_subir.html").write_text("local", encoding="utf-8")
        gs.subir(self.a, ["supuestos/a.html"], "mío", "dia", hoy=date(2026, 11, 8))
        dos = self._otro_clon()                       # «fusionar en GitHub»
        _g(dos, "merge", "-q", "--ff-only", "origin/" + gs.nombre_rama_dia(date(2026, 11, 8)))
        _g(dos, "push", "-q")
        self.assertIn("Traído", gs.traer(self.a))     # antes: «your local changes would be overwritten»
        self.assertEqual(gs.estado(self.a), (["supuestos/sin_subir.html"], [], []))

    def test_volver_a_la_principal(self):
        _g(self.a, "checkout", "-q", "-b", "editor-2026-01-01")
        (self.a / "supuestos" / "a.html").write_text("sin subir", encoding="utf-8")
        self.assertIn("principal", gs.volver_a_principal(self.a))
        self.assertEqual(gs.rama_actual(self.a), "main")
        self.assertEqual((self.a / "supuestos" / "a.html").read_text(encoding="utf-8"), "sin subir")

    def test_buscar_git_dentro_de_github_desktop(self):
        with tempfile.TemporaryDirectory() as c:
            for ver in ("3.4.9", "3.4.10", "3.3.2"):
                d = Path(c) / "GitHubDesktop" / ("app-" + ver) / "resources" / "app" / "git" / "cmd"
                d.mkdir(parents=True)
                (d / "git.exe").write_text("", encoding="utf-8")
            env = {"LOCALAPPDATA": c}
            ruta = gs.buscar_git(env, "win32", cual=lambda _n: None)
            self.assertIn("app-3.4.10", ruta)                       # la versión más nueva
            self.assertIsNone(gs.buscar_git({"LOCALAPPDATA": c + "_no"}, "win32", cual=lambda _n: None))
            self.assertEqual(gs.buscar_git(env, "win32", cual=lambda _n: "C:/git.exe"), "C:/git.exe")

    def test_sin_clon_y_traduccion(self):
        self.assertFalse(gs.es_clon(self.t))
        self.assertIn("quién eres", gs.traducir("Please tell me who you are"))
        self.assertIn("Actualizo a.html", gs.mensaje_sugerido([], ["x/a.html"], []))


class ListaDePreguntas(unittest.TestCase):
    """Operaciones de la lista de preguntas sin ventana (operaciones.py)."""

    def datos(self):
        d = datos_html.datos_vacios()
        d["bloques"] = [dict(d["bloques"][0], id="B1"), dict(d["bloques"][0], id="B2")]
        d["preguntas"] = []
        for i in range(6):
            p = datos_html.pregunta_vacia(None, "B1" if i < 4 else "B2")
            p["q"] = "Pregunta %d sobre <b>plazos</b>" % i if i % 2 else "Pregunta %d" % i
            p["a"] = ["a%d" % i, "b%d" % i, "c%d" % i]
            p["law"] = "art. %d" % i
            d["preguntas"].append(p)
        return d

    def test_mover_varias_sin_salir_del_bloque(self):
        import operaciones as op
        d = self.datos()
        q = [p["q"] for p in d["preguntas"]]
        self.assertEqual(op.mover_varias(d["preguntas"], [1, 2], -1), [0, 1])
        self.assertEqual([p["q"] for p in d["preguntas"]][:3], [q[1], q[2], q[0]])
        self.assertIsNone(op.mover_varias(d["preguntas"], [0, 1], -1))          # ya arriba del todo
        self.assertIsNone(op.mover_varias(d["preguntas"], [3], 1))              # la 4 es de otro bloque
        self.assertEqual(op.mover_varias(d["preguntas"], [0, 2], 1), [1, 3])     # no seguidas

    def test_borrar_duplicar_y_filtrar(self):
        import operaciones as op
        d = self.datos()
        self.assertEqual(op.duplicar_varias(d["preguntas"], [0, 1]), [2, 3])
        self.assertEqual(len(d["preguntas"]), 8)
        self.assertEqual(op.borrar_varias(d["preguntas"], [2, 3]), 2)
        self.assertEqual(len(d["preguntas"]), 6)
        self.assertEqual(op.filtrar(d, "Todas", "plazos"), [1, 3, 5])           # sin mirar la negrita
        self.assertEqual(op.filtrar(d, "Bloque B2"), [4, 5])
        d["preguntas"][2]["law"] = ""
        self.assertEqual(op.filtrar(d, "Sin motivación"), [2])
        self.assertEqual(op.filtrar(d, "Con avisos"), [2])
        d["preguntas"][3]["q"] = ""
        self.assertEqual(op.filtrar(d, "Con errores"), [3])
        self.assertIn(4, op.filtrar(d, "Todas", "5"))                            # también por número
        self.assertIn("Bloque B1", op.opciones_de_filtro(d))


class FuncionesNuevas(unittest.TestCase):
    """F4–F9: BOE, impugnaciones, plazos, sugerir hechos, comparar versiones, exportar."""

    def test_f4_citas_al_boe_como_la_pagina(self):
        normas = [{"siglas": ["LGSS", "TRLGSS"], "boe": "BOE-A-2015-11724"}, {"siglas": ["LPAC"], "boe": "BOE-A-2015-10565"}]
        citas = hd.enlaces_boe("Según el <b>art. 12</b> de la LGSS y el artículo 21 LPAC; art. 3 sin norma.", normas)
        self.assertEqual([c[0] for c in citas], ["art. 12 LGSS", "art. 21 LPAC"])
        self.assertTrue(citas[0][3].endswith("id=BOE-A-2015-11724#a12"))

    def test_f5_impugnacion_va_a_la_pregunta_exacta_y_guarda_su_estado(self):
        import impugnaciones_datos as imp
        d = datos_html.datos_vacios()
        d["config"]["titulo"] = "Tema 3"
        d["preguntas"] = [datos_html.pregunta_vacia(None, "B1") for _ in range(3)]
        for i, t in enumerate(["¿Plazo para el alta?", "¿Quién paga la <b>cuota</b>?", "¿Cuándo prescribe?"]):
            d["preguntas"][i]["q"] = t
        sup = [(Path("supuestos/supuesto_tema3.html"), d)]
        fila = {"supuesto": "Tema 3", "pegunta": "7. ¿Quién paga la cuota? ‖ El trabajador ‖ La empresa",
                "impugnacion del usuario": "La b también vale", "id": "abc123"}
        ruta, n, parecido = imp.localizar(fila, sup)
        self.assertEqual((ruta.name, n, parecido), ("supuesto_tema3.html", 1, 1.0))
        self.assertEqual(imp.clave(fila), "abc123")
        with tempfile.TemporaryDirectory() as c:
            est = imp.leer_estados(c)
            imp.poner_estado(c, est, "abc123", estado="aceptada", nota="corregida la b")
            otra = imp.leer_estados(c)
            self.assertEqual(imp.estado_de(otra, "abc123"), "aceptada")
            self.assertEqual(otra["abc123"]["nota"], "corregida la b")
            self.assertEqual(imp.resumen([fila], otra)["aceptada"], 1)

    def test_f6_plazos(self):
        import plazos
        from datetime import date
        cal = plazos.Calendario()
        # 10 hábiles desde el lunes 30/3/2026: se saltan Viernes Santo y dos fines de semana
        self.assertEqual(plazos.calcular(date(2026, 3, 30), 10, "días hábiles", cal)[0], date(2026, 4, 14))
        # 1 mes desde el 31/1: no hay 31 de febrero → 28/2 (sábado) → lunes 2/3
        self.assertEqual(plazos.calcular(date(2026, 1, 31), 1, "meses", cal)[0], date(2026, 3, 2))
        # naturales que acaban en festivo nacional (8/12) → día siguiente hábil
        self.assertEqual(plazos.calcular(date(2026, 11, 28), 10, "días naturales", cal)[0], date(2026, 12, 9))
        local = plazos.Calendario(plazos.leer_festivos("09/12/2026 fiesta local"))
        self.assertEqual(plazos.calcular(date(2026, 11, 28), 10, "días naturales", local)[0], date(2026, 12, 10))
        self.assertEqual(plazos.pascua(2027), date(2027, 3, 28))

    def test_f7_sugerir_hechos(self):
        e = datos_html.enunciado_vacio("E1")
        e["factBlocks"] = [dict(datos_html.bloque_hechos_vacio("H1"), title="Contrato",
                                paragraphs=["Marta firma un contrato temporal con Construcciones Ruiz el 3 de marzo."]),
                           dict(datos_html.bloque_hechos_vacio("H2"), title="Baja",
                                paragraphs=["Marta sufre un accidente laboral y causa baja médica en junio."])]
        p = datos_html.pregunta_vacia("E1", "B1")
        p["q"] = "¿Qué prestación corresponde a Marta por el accidente laboral de junio?"
        self.assertEqual(hd.sugerir_hechos(p, e)[0][0], "H2")

    def test_f8_comparar_versiones(self):
        a = datos_html.datos_vacios()
        a["preguntas"] = [datos_html.pregunta_vacia(None, "B1") for _ in range(2)]
        a["preguntas"][0]["q"], a["preguntas"][1]["q"] = "Uno", "Dos"
        b = json.loads(json.dumps(a))
        b["preguntas"][1]["law"] = "art. 5"
        b["preguntas"].append(dict(b["preguntas"][0], q="Tres"))
        cambios = hd.comparar_versiones(a, b)
        self.assertTrue(any("Pregunta 2" in c and "motivación" in c for c in cambios))
        self.assertTrue(any("Pregunta 3: nueva" in c for c in cambios))
        self.assertEqual(hd.comparar_versiones(a, a), [])

    def test_f9_exportar_y_volver_a_importar(self):
        ps = [datos_html.pregunta_vacia(None, "B1") for _ in range(2)]
        ps[0].update(q="¿Plazo?", a=["10 días", "15 días", "1 mes"], correctas=[1], law="art. 21\nLPAC", tip="ojo")
        ps[1].update(q="¿Varias?", a=["x", "y", "z", "w"], correctas=[0, 2], multiple=True, law="", tip="")
        de_texto, avisos = hd.importar_texto(hd.exportar_texto(ps), "B1")
        self.assertEqual(avisos, [])
        de_csv, _ = hd.importar_csv(hd.exportar_csv(ps), "B1")
        for vuelta in (de_texto, de_csv):
            self.assertEqual([p["q"] for p in vuelta], ["¿Plazo?", "¿Varias?"])
            self.assertEqual([p["a"] for p in vuelta], [ps[0]["a"], ps[1]["a"]])
            self.assertEqual([p["correctas"] for p in vuelta], [[1], [0, 2]])
            self.assertEqual(vuelta[0]["law"], "art. 21\nLPAC")

    @staticmethod
    def _docx(parrafos, ruta):
        """.docx mínimo: [(texto, ilvl o None, negrita, resaltado)] con una lista
        de dos niveles (1. 2. … / a) b) …) como las plantillas de examen."""
        import zipfile
        from xml.sax.saxutils import escape
        cuerpo = ""
        for texto, nivel, negrita, resaltado in parrafos:
            ppr = ('<w:pPr><w:numPr><w:ilvl w:val="%d"/><w:numId w:val="1"/></w:numPr></w:pPr>' % nivel
                   if nivel is not None else "")
            rpr = ("<w:b/>" if negrita else "") + ('<w:highlight w:val="yellow"/>' if resaltado else "")
            runs = "".join('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>'
                           % ("<w:rPr>%s</w:rPr>" % rpr if rpr else "", escape(trozo))
                           for trozo in ([texto[:3], texto[3:]] if texto else []))   # Word parte los «runs»
            cuerpo += "<w:p>%s%s</w:p>" % (ppr, runs)
        ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        numeracion = ('<w:numbering %s><w:abstractNum w:abstractNumId="0">'
                      '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%%1."/></w:lvl>'
                      '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/><w:lvlText w:val="%%2."/></w:lvl>'
                      '</w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>' % ns)
        with zipfile.ZipFile(ruta, "w") as z:
            z.writestr("word/document.xml", "<w:document %s><w:body>%s</w:body></w:document>" % (ns, cuerpo))
            z.writestr("word/numbering.xml", numeracion)

    def test_f3_importar_word_con_listas_y_negrita_correcta(self):
        import importar_word as iw
        ruta = Path(tempfile.mkdtemp()) / "examen.docx"
        self.addCleanup(shutil.rmtree, ruta.parent)
        self._docx([("¿Plazo para recurrir?", 0, False, False), ("Diez días", 1, False, False),
                    ("Un mes", 1, True, False), ("Dos meses", 1, False, False),
                    ("¿Quién firma?", 0, False, False), ("El alcalde", 1, False, False),
                    ("El secretario", 1, False, True), ("Nadie", 1, False, False),
                    ("", None, False, False),
                    ("3. ¿Todas en negrita?", None, True, False), ("a) uno", None, True, False),
                    ("b) dos", None, True, False), ("c) tres", None, True, False)], ruta)
        crudo = iw.texto_de_docx(ruta)
        self.assertIn("1. ¿Plazo para recurrir?\na) Diez días\nb) <b>Un mes</b>", crudo)
        self.assertIn("2. ¿Quién firma?\na) El alcalde\nb) <mark>El secretario</mark>", crudo)
        texto = iw.texto_para_importar(ruta)
        self.assertIn("b) *Un mes", texto)
        self.assertIn("a) <b>uno</b>", texto, "si todas van en negrita no se marca ninguna")
        preguntas, _avisos = hd.importar_texto(texto, "B1")
        self.assertEqual([p["q"] for p in preguntas], ["¿Plazo para recurrir?", "¿Quién firma?", "<b>¿Todas en negrita?</b>"])
        self.assertEqual([p["a"] for p in preguntas[:2]], [["Diez días", "Un mes", "Dos meses"],
                                                            ["El alcalde", "El secretario", "Nadie"]])
        self.assertEqual([p["correctas"] for p in preguntas[:2]], [[1], [1]])
        self.assertEqual(preguntas[2]["a"], ["<b>uno</b>", "<b>dos</b>", "<b>tres</b>"])
        sin = iw.texto_para_importar(ruta, negrita_correcta=False)
        self.assertIn("b) <b>Un mes</b>", sin)
        with self.assertRaises(ValueError):
            vacio = ruta.parent / "otro.docx"
            import zipfile
            with zipfile.ZipFile(vacio, "w") as z:
                z.writestr("x.txt", "nada")
            iw.texto_de_docx(vacio)

    def test_f2_simulacro_casos_enteros_teoria_suelta_y_sin_repetidas(self):
        import revision
        import simulacro as sim

        def supuesto(nombre, n_casos, n_teoria, minutos=60):
            d = datos_html.datos_vacios()
            d["config"]["titulo"], d["config"]["minutos"] = nombre, minutos
            d["bloques"] = [datos_html.bloque_vacio("supuesto", "B1"), datos_html.bloque_vacio("test", "B2")]
            d["bloques"][1]["fallo"] = -0.33
            d["bloques"][1]["envio"] = {"url": "https://otro-formulario"}
            for k in range(1, n_casos + 1):
                e = datos_html.enunciado_vacio("E%d" % k)
                e["title"] = "%s caso %d" % (nombre, k)
                e["factBlocks"] = [datos_html.bloque_hechos_vacio("H1")]
                d["enunciados"].append(e)
                for j in range(3):
                    p = datos_html.pregunta_vacia("E%d" % k, "B1")
                    p.update(q="%s caso %d pregunta %d" % (nombre, k, j), factIds=["H1"],
                             a=["sí %d" % j, "no", "a veces"])
                    d["preguntas"].append(p)
            for j in range(n_teoria):
                p = datos_html.pregunta_vacia(None, "B2")
                p.update(q="Teoría %d" % j, a=["uno %d" % j, "dos", "tres"])    # igual en los dos: repetidas
                d["preguntas"].append(p)
            return d

        fuentes = [("Tema A", supuesto("Tema A", 2, 10)), ("Tema B", supuesto("Tema B", 1, 10, 30))]
        teoria, casos = sim.piezas(fuentes)
        self.assertEqual((len(teoria), len(casos)), (10, 3))
        d, avisos = sim.generar(fuentes, n_teoria=5, n_casos=2, semilla=3, titulo="Simulacro 1")
        self.assertEqual(avisos, [])
        self.assertEqual([b["id"] + b["tipo"] for b in d["bloques"]], ["B1supuesto", "B2test"])
        self.assertEqual(d["bloques"][1]["fallo"], -0.33, "copia la puntuación del bloque de teoría")
        self.assertNotEqual(d["bloques"][1]["envio"].get("url"), "https://otro-formulario")
        self.assertEqual([e["id"] for e in d["enunciados"]], ["E1", "E2"])
        del_caso = [p for p in d["preguntas"] if p["bloqueId"] == "B1"]
        self.assertEqual(len(del_caso), 6, "cada caso entra con todas sus preguntas")
        self.assertEqual({p["statementId"] for p in del_caso}, {"E1", "E2"})
        for e in d["enunciados"]:
            qs = [p["q"] for p in del_caso if p["statementId"] == e["id"]]
            self.assertTrue(all(q.startswith(e["title"]) for q in qs))
        self.assertEqual(len([p for p in d["preguntas"] if p["bloqueId"] == "B2"]), 5)
        self.assertEqual(d["config"]["titulo"], "Simulacro 1")
        self.assertEqual(revision.errores(revision.revisar(d)), [])
        otra, _ = sim.generar(fuentes, 5, 2, semilla=3)
        self.assertEqual([p["q"] for p in otra["preguntas"]], [p["q"] for p in d["preguntas"]], "misma semilla, mismo examen")
        self.assertEqual(fuentes[0][1]["preguntas"][0]["statementId"], "E1", "no toca los originales")
        _d, avisos = sim.generar(fuentes, 50, 9)
        self.assertEqual(len(avisos), 2)


class Fase1Fallos(unittest.TestCase):
    """Fallos que cambiaban o perdían datos sin avisar (revisión del editor, fase 1)."""

    def test_opcion_vacia_no_mueve_la_correcta(self):
        d = datos_html.datos_vacios()
        d["preguntas"] = [{"bloqueId": "B1", "q": "x", "a": ["A", "", "C buena", "D"], "correctas": [2], "c": 2}]
        p = datos_html.normalizar(d)["preguntas"][0]
        self.assertEqual(p["a"], ["A", "C buena", "D"])
        self.assertEqual(p["a"][p["correctas"][0]], "C buena")
        d["preguntas"] = [{"bloqueId": "B1", "q": "x", "a": ["", "B", "C"], "c": 2}]   # formato antiguo
        p = datos_html.normalizar(d)["preguntas"][0]
        self.assertEqual(p["a"][p["c"]], "C")

    def test_renombrar_enunciado_arrastra_sus_preguntas(self):
        d = datos_html.datos_vacios()
        d["enunciados"] = [datos_html.enunciado_vacio("E1"), datos_html.enunciado_vacio("E2")]
        d["preguntas"] = [datos_html.pregunta_vacia("E1", "B1"), datos_html.pregunta_vacia("E2", "B1")]
        e1 = d["enunciados"][0]
        self.assertIn("vacío", hd.error_id_enunciado(d, e1, " "))
        self.assertIn("Ya hay", hd.error_id_enunciado(d, e1, "E2"))
        self.assertIsNotNone(hd.error_id_enunciado(d, e1, "E 1"))
        self.assertIsNone(hd.error_id_enunciado(d, e1, "E1b"))
        self.assertEqual(hd.renombrar_enunciado(d, e1, "E1b"), 1)
        self.assertEqual(d["preguntas"][0]["statementId"], "E1b")
        self.assertFalse([g for g in hd.errores_graves(d) if "enunciado" in g.lower()])

    def test_guardar_avisa_de_enunciados_que_no_existen(self):
        d = datos_html.datos_vacios()
        d["enunciados"] = [datos_html.enunciado_vacio("E1")]
        d["preguntas"] = [datos_html.pregunta_vacia("E9", "B1")]
        self.assertTrue(any("E9" in g for g in hd.errores_graves(d)))

    def test_escritura_segura(self):
        import archivos
        with tempfile.TemporaryDirectory() as c:
            r = Path(c) / "a.html"
            r.write_text("viejo", encoding="utf-8")
            h1 = archivos.huella_disco(r)
            archivos.escribir_seguro(r, "nuevo ñ")
            self.assertEqual(r.read_text(encoding="utf-8"), "nuevo ñ")
            self.assertEqual(sorted(x.name for x in Path(c).iterdir()), ["a.html"])   # sin temporales
            self.assertNotEqual(h1, archivos.huella_disco(r))
            self.assertIsNone(archivos.huella_disco(Path(c) / "no"))

    def test_paginas_atrasadas_no_toca_nada(self):
        d = copia_del_proyecto()
        try:
            antes = sl.foto(d)
            sl.paginas_atrasadas(d)
            self.assertEqual(antes, sl.foto(d))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class ListasYSangria(unittest.TestCase):
    def setUp(self):
        import editor_comun
        self.ec = editor_comun

    def test_negrita_que_cruza_la_ultima_linea_con_sangria(self):
        eq = self.ec.equilibrar_etiquetas
        self.assertEqual(eq('<span class="sg-1"><b>3) </b>Tres. <b></span>\n¿Cuáles?</b>'),
                         '<span class="sg-1"><b>3) </b>Tres. </span>\n<b>¿Cuáles?</b>')
        self.assertEqual(eq('<b>a\n\n<span class="sg-1">b</span></b>'),
                         '<b>a</b>\n\n<span class="sg-1"><b>b</b></span>')
        self.assertEqual(eq('<b>x<i>y</b>z</i>'), '<b>x<i>y</i></b><i>z</i>')
        self.assertEqual(eq('texto </b> suelto'), 'texto  suelto')
        bien = '<span class="al-j">uno <b>dos</b></span>\n<span class="vi">•\t</span>tres'
        self.assertEqual(eq(bien), bien)
        self.assertEqual(eq(eq('<b>a\nb')), '<b>a</b>\n<b>b</b>')

    def test_lista_pegada_de_word(self):
        ec = self.ec
        self.assertEqual(ec.colgar_vineta("•\tJuan Gómez"),
                         '<span class="cg"><span class="vi">•\t</span>Juan Gómez</span>')
        self.assertEqual(ec.colgar_vineta('<span class="sg-1">2.\tSegundo</span>'),
                         '<span class="sg-1 cg"><span class="vi">2.\t</span>Segundo</span>')
        ya = ec.colgar_vineta("a)\tuno")
        self.assertEqual(ec.colgar_vineta(ya), ya)                    # no se convierte dos veces
        self.assertEqual(ec.colgar_vineta("Plazo\t10 días"), "Plazo 10 días")
        self.assertEqual(ec.colgar_vineta("sin tabulador"), "sin tabulador")

    def test_parrafos_y_textos_convierten_las_listas(self):
        ec = self.ec
        parr = ec.partir_parrafos('Intro\n<span class="sg-1">•\tuno</span>\n<span class="sg-1">•\tdos</span>')
        self.assertEqual(parr[0], "Intro")
        self.assertTrue(all('class="sg-1 cg"' in x for x in parr[1:]))
        txt = ec.limpiar_texto("Plazos:\n1.\tAlzada   un mes\n2.\tReposición")
        self.assertIn('<span class="vi">1.\t</span>Alzada un mes', txt)
        self.assertEqual(ec.limpiar_texto(txt), txt)                   # estable al volver a guardar

    def test_viñeta_siguiente(self):
        ec = self.ec
        self.assertEqual(ec.siguiente_vineta("3."), "4.")
        self.assertEqual(ec.siguiente_vineta("b)\t"), "c)\t")
        self.assertEqual(ec.siguiente_vineta("•"), "•")
        self.assertIn("cg", ec.CLASES_PARRAFO)
        self.assertEqual(ec.envolver_parrafo({"cg", "sg-1"}, "x"), '<span class="sg-1 cg">x</span>')
        self.assertEqual(ec.envolver_parrafo(set(), "x"), "x")

    def test_css_de_listas_y_sangria(self):
        css = (RAIZ / "css" / "base-supuesto.css").read_text(encoding="utf-8")
        for pieza in (".cg {", ".cg > .vi", "inline-block", ".sg-3 { width"):
            self.assertIn(pieza, css)



class ExportarAutonomo(unittest.TestCase):
    def test_no_queda_nada_enlazado(self):
        html, faltan = exportar_autonomo.exportar_html(
            (RAIZ / "supuestos" / "supuesto_1.html").read_text(encoding="utf-8"), RAIZ / "supuestos")
        self.assertEqual(faltan, [])
        import re
        self.assertEqual(re.findall(r'(?:src|href)=["\'](?:\.\./)[^"\']+', html), [])
        self.assertNotIn("url(caveat", html)
        self.assertIn('id="datos-supuesto"', html)
        self.assertIn("CARGA DE LOS DATOS DEL SUPUESTO", html)

if __name__ == "__main__":
    unittest.main(verbosity=2)

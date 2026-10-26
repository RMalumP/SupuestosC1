# -*- coding: utf-8 -*-
"""
ABRIR, GUARDAR Y CERRAR
═══════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
from editor_comun import *  # noqa: F401,F403
from editor_comun import (_guardar_prefs)  # noqa: F401


class ArchivoGuardado:

    # ═════════════════════════════════════════════════════════════
    #  ABRIR / GUARDAR
    # ═════════════════════════════════════════════════════════════
    def volcar_todo(self):
        """Pasa lo escrito en la ventana a la estructura de datos."""
        self.volcar_config()
        self.volcar_botones()
        self.volcar_seccion()
        self.volcar_enunciado()
        self.volcar_pregunta()
        self.ordenar_preguntas_por_bloque()

    def _refrescar_todo(self, reiniciar=True):
        self.i_sec = 0 if self.datos["bloques"] else None
        self.i_enun = 0 if self.datos["enunciados"] else None
        self.i_bloque = self.i_hito = None
        self.i_preg = 0 if self.datos["preguntas"] else None
        self.cargar_config()
        self.cargar_botones()
        self.refrescar_lista_sec(self.i_sec)
        self.refrescar_lista_enun(self.i_enun)
        self.refrescar_lista_preg(self.i_preg)
        self._pintar_titulo()
        if reiniciar:
            self.historial.iniciar(self.datos)

    def _recordar_carpeta(self):
        if self.ruta:
            self._prefs["carpeta"] = str(self.ruta.parent)

    def _carpeta_inicial(self):
        ultima = self._prefs.get("carpeta")
        if ultima and os.path.isdir(ultima):
            return ultima
        aqui = Path(__file__).resolve().parent
        for cand in (aqui / "supuestos", aqui.parent / "supuestos", aqui):
            if cand.is_dir():
                return str(cand)
        return str(aqui)

    def _carga_inicial(self):
        if self.ruta is not None or self.hay_cambios:
            return                       # el usuario ya ha abierto algo
        base = Path(__file__).resolve().parent / PLANTILLA_BASE
        if base.exists():
            try:
                self.datos, self.modo, self.html_base = leer_html(base)
                self.ruta = None
                self.hay_cambios = False
                self._refrescar_todo()
                self.estado("Plantilla en blanco cargada desde «%s». "
                            "Al guardar se pedirá un nombre nuevo." % PLANTILLA_BASE)
                return
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        self.estado("Pulsa «Abrir plantilla…» para empezar.")

    def _confirmar_descartar(self):
        if not self.hay_cambios:
            return True
        r = messagebox.askyesnocancel(
            "Cambios sin guardar",
            "Hay cambios sin guardar.\n\n¿Quieres guardarlos antes de continuar?",
            parent=self)
        if r is None:
            return False
        if r:
            return self.guardar()
        return True

    def nuevo(self):
        if not self._confirmar_descartar():
            return
        base = Path(__file__).resolve().parent / PLANTILLA_BASE
        if not base.exists():
            messagebox.showerror(
                "Falta la plantilla",
                "No encuentro «%s» junto a este programa.\n\n"
                "Copia el archivo de plantilla en la misma carpeta que "
                "editor_supuestos.py y vuelve a intentarlo." % PLANTILLA_BASE, parent=self)
            return
        self.datos, self.modo, self.html_base = leer_html(base)
        self.datos["preguntas"] = []
        self.datos["enunciados"] = []
        self.datos["bloques"] = [bloque_vacio("supuesto", "B1")]
        self.datos["config"] = datos_vacios()["config"]
        self.ruta = None
        self.hay_cambios = False
        self._refrescar_todo()
        self.estado("Supuesto nuevo en blanco. Empieza por la pestaña «1 · Datos generales».")

    def abrir(self):
        if not self._confirmar_descartar():
            return
        ruta = filedialog.askopenfilename(
            parent=self, title="Abrir plantilla de supuesto",
            initialdir=self._carpeta_inicial(),
            filetypes=[("Páginas HTML", "*.html *.htm"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            self.datos, self.modo, self.html_base = leer_html(ruta)
        except (OSError, ValueError, json.JSONDecodeError) as err:
            messagebox.showerror("No se ha podido abrir",
                                 "%s\n\n%s" % (Path(ruta).name, err), parent=self)
            return
        self.ruta = Path(ruta)
        self._recordar_carpeta()
        self.hay_cambios = False
        self._refrescar_todo()
        self._ofrecer_recuperacion()
        self.estado("Abierto: %s  (%d enunciados, %d preguntas)"
                    % (self.ruta.name, len(self.datos["enunciados"]),
                       len(self.datos["preguntas"])))
        if self.modo == "js-sin-config":
            messagebox.showwarning(
                "Plantilla antigua",
                "Este archivo usa la plantilla ANTIGUA: el título, la referencia, el ámbito y "
                "los minutos están escritos a mano dentro del HTML y no en un apartado de datos.\n\n"
                "Se han cargado bien los enunciados y las preguntas, y se guardarán bien, pero "
                "los cambios de la pestaña «1 · Datos generales» NO se aplicarán a este archivo.\n\n"
                "Recomendación: usa «Guardar como…» sobre una copia de %s." % PLANTILLA_BASE,
                parent=self)
        elif self.modo == "js":
            self.estado(self.lbl_estado.cget("text") + "   ·   formato JavaScript (plantilla clásica)")
        else:
            plantilla = self._plantilla_base()
            if plantilla and version_motor(self.html_base) < version_motor(plantilla):
                self.estado(self.lbl_estado.cget("text") +
                            "   ·   página de una versión anterior: al guardar se ofrecerá "
                            "ponerla al día")

    def _nombre_sugerido(self):
        texto = self.datos["config"]["titulo"].lower()
        cambios = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
        for a, b in cambios.items():
            texto = texto.replace(a, b)
        texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
        return (texto or "supuesto")[:48] + ".html"

    def guardar(self):
        self.volcar_todo()
        if self.ruta is None:
            return self.guardar_como()
        return self._escribir(self.ruta)

    def guardar_como(self):
        self.volcar_todo()
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar supuesto como…",
            initialdir=self._carpeta_inicial(),
            initialfile=self._nombre_sugerido(),
            defaultextension=".html",
            filetypes=[("Páginas HTML", "*.html"), ("Todos los archivos", "*.*")])
        if not ruta:
            return False
        return self._escribir(Path(ruta))

    def convertir_a_plantilla_nueva(self):
        """Vuelca el supuesto abierto sobre una copia de la plantilla nueva.

        Sirve para modernizar los supuestos antiguos (los que llevan el
        título escrito a mano dentro del HTML): a partir de la conversión,
        los datos generales también se editan desde el programa.

        Para los archivos que YA usan la plantilla nueva no hace falta:
        al guardar, el editor detecta solo si la página se quedó en una
        versión anterior y ofrece rehacerla."""
        self.volcar_todo()
        base = Path(__file__).resolve().parent / PLANTILLA_BASE
        if not base.exists():
            messagebox.showerror(
                "Falta la plantilla",
                "No encuentro «%s» junto a este programa." % PLANTILLA_BASE, parent=self)
            return False
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar sobre la plantilla nueva…",
            initialdir=self._carpeta_inicial(),
            initialfile=self._nombre_sugerido(),
            defaultextension=".html",
            filetypes=[("Páginas HTML", "*.html"), ("Todos los archivos", "*.*")])
        if not ruta:
            return False
        self.html_base = base.read_text(encoding="utf-8")
        self.modo = "json"
        if self._escribir(Path(ruta)):
            messagebox.showinfo(
                "Convertido",
                "Supuesto guardado con la plantilla nueva.\n\n"
                "A partir de ahora también se pueden cambiar desde el programa el "
                "título, la referencia, el ámbito y los minutos, y la página estrena "
                "el motor actual de la plantilla.", parent=self)
            return True
        return False

    def _plantilla_base(self):
        """La plantilla que viene junto al programa, si está."""
        base = Path(__file__).resolve().parent / PLANTILLA_BASE
        if not base.exists():
            return None
        try:
            return base.read_text(encoding="utf-8")
        except OSError:
            return None

    def _poner_motor_al_dia(self):
        """Si el archivo abierto se quedó con una versión anterior de la
        PÁGINA, ofrece rehacerla con la plantilla actual.

        Al guardar solo se sustituyen los datos dentro del HTML, así que un
        supuesto creado hace meses conserva su página tal cual, sin las
        mejoras posteriores de la plantilla. Aquí se detecta y se arregla,
        que es justo lo que uno espera al guardar."""
        if self.modo != "json":
            return          # las plantillas antiguas van por «⇪ Pasar a plantilla nueva…»
        plantilla = self._plantilla_base()
        if plantilla is None:
            return
        nueva = version_motor(plantilla)
        vieja = version_motor(self.html_base)
        if vieja >= nueva:
            return          # ya está al día

        if not messagebox.askyesno(
                "Poner la página al día",
                "Este supuesto se creó con una versión anterior de la plantilla, así que "
                "su página no tiene las mejoras que sí trae la plantilla que acompaña al "
                "programa.\n\n"
                "Si NO se actualiza, se guardarán los datos nuevos pero la página seguirá "
                "comportándose como el día en que se creó el archivo: es lo que hace que "
                "opciones nuevas del editor no se noten al abrir el supuesto.\n\n"
                "¿Rehacer la página con la plantilla actual?\n"
                "(No se toca ni una pregunta: solo se cambia el armazón. Del archivo "
                "anterior queda una copia .bak.)", parent=self):
            self.estado("Guardado SIN actualizar la página: las novedades de la plantilla "
                        "no se verán en este archivo.")
            return

        self.html_base = plantilla
        self.estado("Página rehecha con la plantilla actual (versión %d)." % nueva)

    def _escribir(self, destino):
        self._prefs["carpeta"] = str(Path(destino).parent)
        self._poner_motor_al_dia()
        if self.modo != "json" and bloques_se_pierden(self.datos):
            seguir = messagebox.askyesno(
                "La plantilla clásica no tiene bloques",
                "Este archivo usa la plantilla CLÁSICA, que no conoce los bloques: solo "
                "guarda una lista de preguntas seguidas.\n\n"
                "Si guardas aquí se conservan todas las preguntas y su orden, pero se "
                "PIERDEN los bloques, sus colores, su baremo, la sección de teoría, la "
                "paleta de colores y los ajustes de botones y de envío.\n\n"
                "Lo recomendable es cerrar este aviso y usar «⇪ Pasar a plantilla nueva…».\n\n"
                "¿Guardar de todas formas?", parent=self)
            if not seguir:
                return False
        try:
            self.html_base = escribir_html(destino, self.html_base, self.datos, self.modo)
        except (OSError, ValueError) as err:
            messagebox.showerror("No se ha podido guardar", str(err), parent=self)
            return False
        self.ruta = Path(destino)
        self.hay_cambios = False
        self._pintar_titulo()
        self.estado("Guardado en %s   (%d preguntas)"
                    % (self.ruta, len(self.datos["preguntas"])))
        self._borrar_recuperacion()
        self._alta_en_menu()
        self.refrescar_para_subir()
        return True

    def refrescar_para_subir(self):
        """Tras guardar: deja la carpeta PARA_SUBIR al día con lo que se ha cambiado."""
        res = sincronizar_local.refrescar_silencioso(self.ruta) if self.ruta else None
        if res:
            self.estado(self.lbl_estado.cget("text") + "   ·   " + sincronizar_local.resumen(*res))

    def _alta_en_menu(self):
        """Mantiene al día la tarjeta del supuesto en el menú principal
        (supuestos-datos.js). Si el supuesto ya estaba, solo actualiza su
        título, referencia y descripción; si es nuevo, pregunta en qué grupo
        ponerlo. No hace nada si el archivo no está en «supuestos/»."""
        try:
            ruta_menu = ruta_menu_de(self.ruta)
            if ruta_menu is None:
                return
            texto, menu = leer_menu(ruta_menu)
            archivo = self.ruta.stem
            grupo = grupo_en_menu(menu, archivo)
            if grupo:
                for it in lista_de_grupo(menu, grupo):
                    if it.get("archivo") == archivo:
                        it.update({k: v for k, v in ficha_menu(archivo, self.datos).items()
                                   if k != "letra"})
                escribir_menu(ruta_menu, texto, menu)
                self.estado(self.lbl_estado.cget("text") + "   ·   menú actualizado")
                return
            self._destinos_menu = menu_datos.destinos(menu)
            elegido = self._pedir_grupo_menu(archivo)
            if not elegido:
                self.estado(self.lbl_estado.cget("text") + "   ·   sin añadir al menú")
                return
            clave, letra = elegido
            lista_de_grupo(menu, clave).append(ficha_menu(archivo, self.datos, letra))
            escribir_menu(ruta_menu, texto, menu)
            self.estado(self.lbl_estado.cget("text") + "   ·   añadido al menú (%s)" % clave)
        except (OSError, ValueError) as err:
            messagebox.showwarning(
                "Menú principal",
                "El supuesto se ha guardado, pero no he podido tocar %s:\n\n%s\n\n"
                "Añade su tarjeta a mano (las instrucciones están al principio de ese archivo)."
                % (ARCHIVO_MENU, err), parent=self)

    def _pedir_grupo_menu(self, archivo):
        """Pequeño diálogo: ¿en qué grupo del menú va este supuesto?
        Devuelve (grupo, letra) o None si se cancela."""
        ventana = tk.Toplevel(self)
        ventana.title("Añadir al menú principal")
        ventana.transient(self)
        ventana.resizable(False, False)
        marco = ttk.Frame(ventana, padding=16)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, wraplength=380, justify="left",
                  text="«%s» todavía no está en el menú principal de la web.\n"
                       "¿En qué sección y grupo lo pongo?" % archivo).pack(anchor="w", pady=(0, 8))
        sitios = self._destinos_menu or list(GRUPOS_MENU)
        grupo = tk.StringVar(value="generales/avanzados" if any(c == "generales/avanzados" for c, _ in sitios) else sitios[0][0])
        for clave, etiqueta in sitios:
            ttk.Radiobutton(marco, text=etiqueta, value=clave, variable=grupo).pack(anchor="w")
        fila = ttk.Frame(marco)
        fila.pack(fill="x", pady=(10, 0))
        ttk.Label(fila, text="Texto del círculo (1-4 caracteres):").pack(side="left")
        letra = tk.StringVar(value=archivo.replace("supuesto_", "").upper()[:4])
        ttk.Entry(fila, textvariable=letra, width=6).pack(side="left", padx=6)
        resultado = []

        def aceptar():
            resultado.append((grupo.get(), (letra.get().strip() or "?")[:4]))
            ventana.destroy()

        botones = ttk.Frame(marco)
        botones.pack(fill="x", pady=(14, 0))
        ttk.Button(botones, text="Añadir al menú", command=aceptar).pack(side="right")
        ttk.Button(botones, text="Ahora no", command=ventana.destroy).pack(side="right", padx=(0, 6))
        ventana.grab_set()
        self.wait_window(ventana)
        return resultado[0] if resultado else None

    def ver_navegador(self):
        if self.ruta is None or self.hay_cambios:
            if not messagebox.askyesno(
                    "Guardar antes de ver",
                    "Para verlo en el navegador hay que guardar el archivo.\n\n¿Guardo ahora?",
                    parent=self):
                return
            if not self.guardar():
                return
        webbrowser.open(self.ruta.resolve().as_uri())
        self.estado("Abierto en el navegador: %s" % self.ruta.name)

    def _al_cerrar(self):
        self.volcar_todo()
        self._prefs["geometria"] = self.geometry()
        _guardar_prefs(self._prefs)
        if self.hay_cambios:
            r = messagebox.askyesnocancel(
                "Salir", "Hay cambios sin guardar.\n\n¿Guardarlos antes de salir?", parent=self)
            if r is None:
                return
            if r and not self.guardar():
                return
        if self._normas_sucio:
            r = messagebox.askyesnocancel(
                "Salir", "La lista de normas (pestaña 7) tiene cambios sin guardar.\n\n¿Guardarlas antes de salir?",
                parent=self)
            if r is None:
                return
            if r:
                self._norma_guardar_archivo()
        self.destroy()

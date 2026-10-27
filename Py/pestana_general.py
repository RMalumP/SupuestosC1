# -*- coding: utf-8 -*-
"""
PESTAÑA 1 · DATOS GENERALES
═══════════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
from editor_comun import *  # noqa: F401,F403


class PestanaGeneral:

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 1 — DATOS GENERALES
    # ═════════════════════════════════════════════════════════════
    def _pestana_general(self):
        cont = MarcoScroll(self.cuaderno)
        self.cuaderno.add(cont, text="  1 · Datos generales  ")
        m = cont.interior

        ttk.Label(m, text="Datos generales del examen", style="Titulo.TLabel").pack(
            anchor="w", padx=16, pady=(14, 2))
        ttk.Label(m, style="Ayuda.TLabel", wraplength=880, justify="left",
                  text="Estos cuatro datos rellenan solos la cabecera de la página, la pestaña del "
                       "navegador, la hoja de impresión y el cronómetro. En el archivo HTML viven en "
                       "el apartado «config».").pack(anchor="w", padx=16, pady=(0, 10))

        self.w_cfg = {}
        for clave, visible, tecnico, html, ayuda in CAMPOS_CONFIG:
            caja = ttk.LabelFrame(m, text=" %s " % visible)
            caja.pack(fill="x", padx=16, pady=6)
            rotulo(caja, visible, tecnico, html, ayuda,
                   con_titulo=False).pack(anchor="w", padx=10, pady=(8, 4))
            if clave in ("minutos", "aptoPorcentaje"):
                var = tk.StringVar(value="30" if clave == "minutos" else "50")
                tope = 600 if clave == "minutos" else 100
                sp = ttk.Spinbox(caja, from_=0 if clave == "aptoPorcentaje" else 1,
                                 to=tope, textvariable=var, width=8,
                                 font=("Consolas", 11), command=self._tocado)
                sp.pack(anchor="w", padx=10, pady=(0, 10))
                self._vigilar(sp)
                self.w_cfg[clave] = var
            elif clave == "logo":
                var = tk.StringVar()
                linea = ttk.Frame(caja, style="Panel.TFrame")
                linea.pack(fill="x", padx=10, pady=(0, 10))
                ent = ttk.Entry(linea, textvariable=var, font=("Consolas", 9))
                ent.pack(side="left", fill="x", expand=True)
                self._vigilar(ent)
                ttk.Button(linea, text="📁 Elegir imagen…", command=self.elegir_logo
                           ).pack(side="left", padx=(6, 0))
                ttk.Button(linea, text="↺ La de la plantilla",
                           command=lambda v=var: (v.set(LOGO_POR_DEFECTO), self._tocado())
                           ).pack(side="left", padx=(6, 0))
                self.w_cfg[clave] = var
            else:
                var = tk.StringVar()
                ent = ttk.Entry(caja, textvariable=var, font=("Georgia", 11))
                ent.pack(fill="x", padx=10, pady=(0, 10))
                self._vigilar(ent)
                self.w_cfg[clave] = var

        caja = ttk.LabelFrame(m, text=" Cuántas respuestas salen en cada pregunta ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Respuestas que se muestran", "config.respuestas",
               '<div class="options-grid"> → nº de <div class="option">', con_titulo=False,
               ayuda=
                    "Lo normal son cuatro. Si eliges 3, 4 o 5, todas las preguntas saldrán con "
                    "ese número de respuestas: se muestran siempre la correcta (o las correctas) "
                    "y se sortean los distractores que falten. Eso permite escribir hasta SIETE "
                    "opciones en una pregunta y que cada intento enseñe unas cuantas distintas. "
                    "Una pregunta que tenga menos opciones escritas sale con las que tenga, y en "
                    "la pestaña 4 se puede dar a una pregunta suelta un número propio."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_cfg_respuestas = tk.StringVar()
        self._etiquetas_respuestas = [texto for _valor, texto in RESPUESTAS_EXAMEN]
        combo = ttk.Combobox(caja, textvariable=self.var_cfg_respuestas, state="readonly",
                             font=("Georgia", 10), values=self._etiquetas_respuestas)
        combo.pack(anchor="w", fill="x", padx=10, pady=(0, 10))
        combo.bind("<<ComboboxSelected>>", lambda e: self._tocado())

        caja = ttk.LabelFrame(m, text=" Corazón de favoritas ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Corazón de favoritas ♥", "config.corazon",
               '<button class="btn-corazon"> en la esquina de cada pregunta', con_titulo=False,
               ayuda=
                    "Un corazón pequeño en la esquina de cada pregunta con el que la persona guarda "
                    "sus favoritas (aparecen en «Mi estudio»). Si lo desmarcas, este supuesto no "
                    "lo muestra. Cada persona también puede ocultarlo desde el panel ⚙."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_cfg_corazon = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(caja, text="Mostrar el corazón de favoritas en este supuesto",
                              variable=self.var_cfg_corazon, command=self._tocado)
        chk.pack(anchor="w", padx=10, pady=(0, 10))

        caja = ttk.LabelFrame(m, text=" Subrayar con colores ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Subrayar texto", "config.subrayar",
               '<mark class="subr"> sobre enunciado, pregunta y respuestas', con_titulo=False,
               ayuda=
                    "Permite a la persona seleccionar un trozo del enunciado, de la pregunta o de una "
                    "respuesta y subrayarlo con el color que elija en una ventanita. Los subrayados se "
                    "guardan en su navegador y se ven también en «Mi estudio». Si lo desmarcas, este "
                    "supuesto no deja subrayar. Cada persona también puede apagarlo desde el panel ⚙."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_cfg_subrayar = tk.BooleanVar(value=True)
        chk2 = ttk.Checkbutton(caja, text="Permitir subrayar en este supuesto",
                               variable=self.var_cfg_subrayar, command=self._tocado)
        chk2.pack(anchor="w", padx=10, pady=(0, 10))

        caja = ttk.LabelFrame(m, text=" Texto justificado ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Justificado por defecto", "config.justificar",
               'text-align: justify en .fact-block, .q-text y .feedback-body', con_titulo=False,
               ayuda=
                    "Por defecto el texto sale justificado (alineado a los dos márgenes) en el "
                    "enunciado, en las preguntas con sus respuestas y en las justificaciones. "
                    "Desmarca una parte si en este supuesto la quieres alineada a la izquierda. "
                    "Un párrafo suelto puede quedar a la izquierda con el botón «Izq.» del "
                    "editor de texto."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_just = {}
        for clave, texto in (("enunciado", "Justificar el enunciado"),
                             ("pregunta", "Justificar las preguntas y sus respuestas"),
                             ("motivacion", "Justificar las justificaciones (motivación y consejo)")):
            self.var_just[clave] = tk.BooleanVar(value=True)
            ttk.Checkbutton(caja, text=texto, variable=self.var_just[clave],
                            command=self._tocado).pack(anchor="w", padx=10, pady=(0, 4))
        ttk.Frame(caja, height=6).pack()

        caja = ttk.LabelFrame(m, text=" Número de preguntas (automático) ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Nº de preguntas",
               "(no se edita: se cuenta solo)",
               '<span class="meta-pill" id="meta-preguntas">', con_titulo=False,
               ayuda=
                    "La píldora «N PREGUNTAS» de la cabecera la calcula la propia página contando "
                    "las preguntas cargadas, así que nunca puede quedar desactualizada."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.lbl_num_preg = ttk.Label(caja, text="0 PREGUNTAS", font=("Consolas", 11, "bold"),
                                      foreground=C_VERDE)
        self.lbl_num_preg.pack(anchor="w", padx=10, pady=(0, 10))

        # ---------- paleta de colores de la página ----------
        caja = ttk.LabelFrame(m, text=" Colores de la página ")
        caja.pack(fill="x", padx=16, pady=(14, 18))
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=880, justify="left",
                  text="Cambia toda la apariencia del examen: fondos, textos, acentos y "
                       "hasta las transparencias derivadas de cada color. No afecta al color "
                       "de cada bloque de preguntas, que se elige en la pestaña «2 · Bloques». "
                       "En el archivo HTML viven en el apartado «tema» y sustituyen a las "
                       "variables de :root."
                  ).pack(anchor="w", padx=10, pady=(8, 8))

        rejilla = ttk.Frame(caja, style="Panel.TFrame")
        rejilla.pack(fill="x", padx=10)
        rejilla.columnconfigure(3, weight=1)

        self.w_tema = {}
        self.muestras_tema = {}
        for fila, (clave, visible, variable, ayuda) in enumerate(CAMPOS_TEMA):
            muestra = tk.Label(rejilla, text="      ", relief="solid", borderwidth=1)
            muestra.grid(row=fila, column=0, sticky="w", pady=3)
            self.muestras_tema[clave] = muestra

            var = tk.StringVar(value=TEMA_DEFECTO[clave])
            ent = ttk.Entry(rejilla, textvariable=var, font=("Consolas", 10), width=10)
            ent.grid(row=fila, column=1, sticky="w", padx=6)
            ent.bind("<KeyRelease>",
                     lambda e, c=clave: (self._tocado(), self._pintar_tema()), add="+")
            self.w_tema[clave] = var

            ttk.Button(rejilla, text="🎨", width=3,
                       command=lambda c=clave, v=visible: self.elegir_color_tema(c, v)
                       ).grid(row=fila, column=2, sticky="w")

            texto = ttk.Frame(rejilla, style="Panel.TFrame")
            texto.grid(row=fila, column=3, sticky="we", padx=(10, 0))
            ttk.Label(texto, text=visible, style="Campo.TLabel").pack(anchor="w")
            ttk.Label(texto, text="tema.%s   →   CSS: %s   ·   %s" % (clave, variable, ayuda),
                      style="Tec.TLabel").pack(anchor="w")

        pie = ttk.Frame(caja, style="Panel.TFrame")
        pie.pack(fill="x", padx=10, pady=(10, 12))
        ttk.Button(pie, text="↺  Restaurar los colores originales",
                   command=self.restaurar_tema).pack(side="left")
        ttk.Label(pie, style="Ayuda.TLabel",
                  text="   Vista previa aproximada →").pack(side="left")

        # Vista previa en miniatura
        self.previa = tk.Frame(caja, height=96, relief="solid", borderwidth=1)
        self.previa.pack(fill="x", padx=10, pady=(0, 12))
        self.previa_barra = tk.Frame(self.previa, height=26)
        self.previa_barra.pack(fill="x")
        self.previa_casilla = tk.Label(self.previa_barra, text=" 1 ", font=("Consolas", 9, "bold"))
        self.previa_casilla.pack(side="left", padx=8, pady=4)
        self.previa_rotulo = tk.Label(self.previa_barra, text="TIEMPO 30:00",
                                      font=("Consolas", 9, "bold"))
        self.previa_rotulo.pack(side="right", padx=8)
        self.previa_tarjeta = tk.Label(self.previa, text="  Texto de una pregunta de ejemplo",
                                       anchor="w", font=("Georgia", 10), padx=8, pady=6)
        self.previa_tarjeta.pack(fill="x", padx=10, pady=(8, 2))
        self.previa_hechos = tk.Label(self.previa, text="  Bloque de hechos del enunciado",
                                      anchor="w", font=("Georgia", 9), padx=8, pady=4)
        self.previa_hechos.pack(fill="x", padx=10, pady=(0, 10))

    # ---------- paleta ----------
    def _pintar_tema(self):
        """Refresca las muestras de color y la vista previa en miniatura."""
        col = {c: color_valido(self.w_tema[c].get(), TEMA_DEFECTO[c]) for c in TEMA_DEFECTO}
        for clave, muestra in self.muestras_tema.items():
            muestra.config(background=col[clave])
        self.previa.config(background=col["fondo"])
        self.previa_barra.config(background=col["barra"])
        self.previa_casilla.config(background=col["acento"], foreground=col["fondo"])
        self.previa_rotulo.config(background=col["barra"], foreground=col["acento"])
        self.previa_tarjeta.config(background=col["tarjeta"], foreground=col["texto"])
        self.previa_hechos.config(background=col["fondoHechos"], foreground=col["gris"])

    def elegir_color_tema(self, clave, visible):
        actual = color_valido(self.w_tema[clave].get(), TEMA_DEFECTO[clave])
        elegido = colorchooser.askcolor(color=actual, parent=self, title=visible)
        if elegido and elegido[1]:
            self.w_tema[clave].set(elegido[1])
            self._pintar_tema()
            self._tocado()

    def restaurar_tema(self):
        for clave, valor in TEMA_DEFECTO.items():
            self.w_tema[clave].set(valor)
        self._pintar_tema()
        self._tocado()
        self.estado("Paleta restaurada a los colores originales de la plantilla.")

    def elegir_logo(self):
        """Elige una imagen del disco y la guarda como ruta relativa al .html."""
        ruta = filedialog.askopenfilename(
            parent=self, title="Imagen del encabezado",
            initialdir=str(self.ruta.parent) if self.ruta else self._carpeta_inicial(),
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.webp *.svg"),
                       ("Todos los archivos", "*.*")])
        if not ruta:
            return
        elegida = Path(ruta)
        if self.ruta:
            try:
                relativa = os.path.relpath(elegida, self.ruta.parent).replace("\\", "/")
                self.w_cfg["logo"].set(relativa)
                self._tocado()
                self.estado("Imagen del encabezado: %s (ruta relativa al supuesto)" % relativa)
                return
            except ValueError:
                pass          # en otra unidad de disco: se usa la ruta completa
        else:
            messagebox.showinfo(
                "Guarda primero el supuesto",
                "Como el supuesto todavía no está guardado, se usará la ruta completa "
                "de la imagen. Al guardar el archivo conviene volver a elegirla para "
                "que quede una ruta relativa y el supuesto siga siendo portátil.",
                parent=self)
        self.w_cfg["logo"].set(elegida.as_uri())
        self._tocado()

    def cargar_config(self):
        cfg = self.datos["config"]
        for clave, *_ in CAMPOS_CONFIG:
            valor = cfg.get(clave, "")
            self.w_cfg[clave].set(nUm(valor) if clave == "aptoPorcentaje" else str(valor))
        valores = [v for v, _t in RESPUESTAS_EXAMEN]
        actual = cfg.get("respuestas", 0)
        pos = valores.index(actual) if actual in valores else 0
        self.var_cfg_respuestas.set(self._etiquetas_respuestas[pos])
        self.var_cfg_corazon.set(cfg.get("corazon", True) is not False)
        self.var_cfg_subrayar.set(cfg.get("subrayar", True) is not False)
        just = cfg.get("justificar") if isinstance(cfg.get("justificar"), dict) else {}
        for clave, var in self.var_just.items():
            var.set(just.get(clave, True) is not False)
        self.cargar_panel_opciones(cfg)
        tema = self.datos.get("tema") or TEMA_DEFECTO
        for clave in TEMA_DEFECTO:
            self.w_tema[clave].set(tema.get(clave, TEMA_DEFECTO[clave]))
        self._pintar_tema()
        self.lbl_num_preg.config(text="%d PREGUNTAS" % len(self.datos["preguntas"]))

    def volcar_config(self):
        cfg = self.datos["config"]
        for clave, *_ in CAMPOS_CONFIG:
            valor = self.w_cfg[clave].get()
            if clave == "minutos":
                valor = max(1, int(numero(valor, 30)))
            elif clave == "aptoPorcentaje":
                valor = min(100.0, max(0.0, numero(valor, 50.0)))
            cfg[clave] = valor
        etiqueta = self.var_cfg_respuestas.get()
        cfg["respuestas"] = next((v for v, t in RESPUESTAS_EXAMEN if t == etiqueta), 0)
        cfg["corazon"] = bool(self.var_cfg_corazon.get())
        cfg["subrayar"] = bool(self.var_cfg_subrayar.get())
        cfg["justificar"] = {k: bool(v.get()) for k, v in self.var_just.items()}
        cfg["panel"] = self.volcar_panel_opciones()
        self.datos["tema"] = {
            clave: color_valido(self.w_tema[clave].get(), TEMA_DEFECTO[clave])
            for clave in TEMA_DEFECTO}

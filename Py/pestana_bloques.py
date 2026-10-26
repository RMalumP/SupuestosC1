# -*- coding: utf-8 -*-
"""
PESTAÑA 2 · BLOQUES DEL EXAMEN
══════════════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
from editor_comun import *  # noqa: F401,F403


class PestanaBloques:

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 2 — BLOQUES DEL EXAMEN (supuesto / teoría)
    # ═════════════════════════════════════════════════════════════
    def _pestana_bloques(self):
        panel = ttk.Frame(self.cuaderno)
        self.cuaderno.add(panel, text="  2 · Bloques  ")

        divisor = ttk.PanedWindow(panel, orient="horizontal")
        divisor.pack(fill="both", expand=True, padx=8, pady=8)

        izq = ttk.Frame(divisor, width=300)
        izq.pack_propagate(False)
        divisor.add(izq, weight=0)

        ttk.Label(izq, text="Bloques del examen", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(izq, style="Tec.TLabel", text="bloques[]").pack(anchor="w")
        ttk.Label(izq, style="Ayuda.TLabel", wraplength=280, justify="left",
                  text="Secciones del examen, EN EL ORDEN EN QUE SALEN. Con ▲▼ eliges "
                       "cuál va primero. Puede haber solo un bloque, o tres, o los que "
                       "necesites, de cualquiera de los dos tipos."
                  ).pack(anchor="w", pady=(0, 6))

        self.lst_sec = tk.Listbox(izq, font=("Consolas", 9), height=10,
                                  activestyle="none", exportselection=False)
        self.lst_sec.pack(fill="both", expand=True)
        self.lst_sec.bind("<<ListboxSelect>>", self._sel_seccion)

        bot = ttk.Frame(izq)
        bot.pack(fill="x", pady=6)
        ttk.Button(bot, text="＋ Bloque de supuesto", style="Accion.TButton", width=22,
                   command=lambda: self.anadir_seccion("supuesto")
                   ).grid(row=0, column=0, columnspan=2, padx=1, pady=1)
        ttk.Button(bot, text="＋ Bloque de teoría", style="Accion.TButton", width=22,
                   command=lambda: self.anadir_seccion("test")
                   ).grid(row=1, column=0, columnspan=2, padx=1, pady=1)
        ttk.Button(bot, text="🗑 Borrar", width=10,
                   command=self.borrar_seccion).grid(row=2, column=0, padx=1, pady=1)
        ttk.Button(bot, text="⧉ Duplicar", width=10,
                   command=self.duplicar_seccion).grid(row=2, column=1, padx=1, pady=1)
        ttk.Button(bot, text="▲ Subir", width=10,
                   command=lambda: self.mover_seccion(-1)).grid(row=3, column=0, padx=1, pady=1)
        ttk.Button(bot, text="▼ Bajar", width=10,
                   command=lambda: self.mover_seccion(1)).grid(row=3, column=1, padx=1, pady=1)

        cont = MarcoScroll(divisor)
        divisor.add(cont, weight=1)
        m = cont.interior

        # ---------- identificación ----------
        self.w_sec = {}
        caja = ttk.LabelFrame(m, text=" Identificación ")
        caja.pack(fill="x", padx=10, pady=(8, 6))
        for clave, visible, tecnico, html, ayuda in CAMPOS_BLOQUE:
            rotulo(caja, visible, tecnico, html, ayuda).pack(anchor="w", padx=10, pady=(8, 2))
            var = tk.StringVar()
            ent = ttk.Entry(caja, textvariable=var, font=("Georgia", 10))
            ent.pack(fill="x", padx=10, pady=(0, 2))
            self._vigilar(ent)
            self.w_sec[clave] = var
        ttk.Frame(caja, height=8).pack()

        # ---------- tipo ----------
        caja = ttk.LabelFrame(m, text=" Tipo de bloque ")
        caja.pack(fill="x", padx=10, pady=6)
        rotulo(caja, "Qué clase de preguntas lleva", "bloques[].tipo",
               '<span class="bh-tipo"> → «Supuesto práctico» / «Teoría · test»',
               "Un bloque de SUPUESTO enlaza sus preguntas con un enunciado (los hechos "
               "aparecen encima). Un bloque de TEORÍA son preguntas de test sueltas, sin "
               "enunciado: al elegir este tipo, sus preguntas se desenganchan del enunciado."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_sec_tipo = tk.StringVar(value="supuesto")
        for valor, texto in (("supuesto", "Supuesto práctico (preguntas con enunciado)"),
                             ("test", "Teoría (preguntas de test sueltas)")):
            ttk.Radiobutton(caja, text=texto, value=valor, variable=self.var_sec_tipo,
                            command=self._cambio_tipo_seccion).pack(anchor="w", padx=18, pady=1)
        ttk.Frame(caja, height=8).pack()

        # ---------- aspecto ----------
        caja = ttk.LabelFrame(m, text=" Aspecto en la página ")
        caja.pack(fill="x", padx=10, pady=6)

        rotulo(caja, "Color del bloque", "bloques[].color",
               '.nav-box.blq-XX  ·  .block-header  ·  banda lateral de las tarjetas',
               "Color de las casillas numeradas de la cabecera, del rótulo del bloque y de "
               "la barra que encabeza sus preguntas. Sirve para distinguir de un vistazo la "
               "teoría del supuesto."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        fila = ttk.Frame(caja, style="Panel.TFrame")
        fila.pack(fill="x", padx=10, pady=(0, 4))
        self.var_sec_color = tk.StringVar(value=COLOR_SUPUESTO)
        ent = ttk.Entry(fila, textvariable=self.var_sec_color, font=("Consolas", 10), width=12)
        ent.pack(side="left")
        ent.bind("<KeyRelease>", lambda e: (self._tocado(), self._pintar_muestra_color()), add="+")
        self.muestra_color = tk.Label(fila, text="        ", relief="solid", borderwidth=1)
        self.muestra_color.pack(side="left", padx=8)
        ttk.Button(fila, text="🎨 Elegir color…", command=self.elegir_color).pack(side="left")
        for nombre, valor in (("Azul supuesto", COLOR_SUPUESTO), ("Ámbar teoría", COLOR_TEST),
                              ("Verde", "#7fbf8f"), ("Lavanda", "#b9a6e0")):
            ttk.Button(fila, text=nombre, width=13,
                       command=lambda v=valor: self.poner_color(v)).pack(side="left", padx=(6, 0))

        rotulo(caja, "Cómo EMPIEZAN viéndose las preguntas de este bloque", "bloques[].modo",
               '.question-card.visible  ·  .question-card.encadenada',
               "«En cadena» muestra todas las preguntas del bloque seguidas, una debajo de "
               "otra (lo habitual en la teoría, y también en un supuesto que se lea de "
               "corrido). «De una en una» muestra solo la pregunta actual. Esto es solo el "
               "estado de PARTIDA: en la página, cada bloque tiene su propia casilla en el "
               "panel ⚙ y el alumno puede cambiarlo sin tocar los demás bloques."
               ).pack(anchor="w", padx=10, pady=(10, 4))
        self.var_sec_modo = tk.StringVar(value="individual")
        for valor, texto in (("cadena", "En cadena — todas las preguntas del bloque seguidas"),
                             ("individual", "De una en una — solo la pregunta actual")):
            ttk.Radiobutton(caja, text=texto, value=valor, variable=self.var_sec_modo,
                            command=self._tocado).pack(anchor="w", padx=18, pady=1)

        rotulo(caja, "¿Puede el alumno cambiarlo en este bloque?", "bloques[].opcionUnaEnUna",
               '<div id="una-por-bloque"> → una casilla por bloque',
               "Marcada (lo normal): el panel ⚙ de la página enseña una casilla para ESTE "
               "bloque, con su nombre y su color, y el alumno decide si lo ve en cadena o de "
               "una en una. Desmarcada: ese bloque no sale en el panel y se queda siempre "
               "como lo hayas dejado aquí arriba. Si desmarcas todos, la opción entera "
               "desaparece del panel."
               ).pack(anchor="w", padx=10, pady=(10, 4))
        self.var_sec_opcion_una = tk.BooleanVar(value=True)
        ttk.Checkbutton(caja, variable=self.var_sec_opcion_una, command=self._tocado,
                        text="Sacar la casilla de este bloque en el panel ⚙"
                        ).pack(anchor="w", padx=18, pady=1)

        ttk.Label(caja, style="Ayuda.TLabel", wraplength=820, justify="left",
                  text="EN CADENA, un bloque de supuesto se lee de corrido y en su orden "
                       "natural: enunciado 1 completo (con todas sus secciones) → todas las "
                       "preguntas de ese enunciado → enunciado 2 → sus preguntas, y así "
                       "sucesivamente."
                  ).pack(anchor="w", padx=18, pady=(6, 2))

        rotulo(caja, "Dónde va la barra con el nombre del bloque",
               "bloques[].cabeceraSobreEnunciado",
               '<div class="block-header"> antes o después de <section class="statement">',
               "Marcada (lo normal): la barra del bloque —nombre, nº de preguntas y "
               "baremo— sale ENCIMA del enunciado, encabezando toda la sección. "
               "Desmarcada: baja hasta justo delante de la primera pregunta, debajo de "
               "los hechos (como en las versiones anteriores de la plantilla). En los "
               "bloques de teoría da igual: no llevan enunciado."
               ).pack(anchor="w", padx=10, pady=(10, 4))
        self.var_sec_cabecera = tk.BooleanVar(value=True)
        ttk.Checkbutton(caja, variable=self.var_sec_cabecera, command=self._tocado,
                        text="La barra del bloque va encima del enunciado"
                        ).pack(anchor="w", padx=18, pady=1)
        ttk.Frame(caja, height=8).pack()

        # ---------- puntuación ----------
        caja = ttk.LabelFrame(m, text=" Puntuación de este bloque ")
        caja.pack(fill="x", padx=10, pady=6)
        rotulo(caja, "Cuánto suma y cuánto descuenta cada pregunta",
               "bloques[].acierto · bloques[].fallo · bloques[].blanco",
               '<div class="score-bloques"> → puntos del bloque',
               "Cada bloque se corrige por separado con su propio baremo y luego se suman "
               "los bloques. Se admiten decimales con coma: 0,33 descuenta un tercio."
               ).pack(anchor="w", padx=10, pady=(8, 6))

        rejilla = ttk.Frame(caja, style="Panel.TFrame")
        rejilla.pack(fill="x", padx=10, pady=(0, 4))
        self.var_sec_ac = tk.StringVar(value="1")
        self.var_sec_fa = tk.StringVar(value="0")
        self.var_sec_bl = tk.StringVar(value="0")
        for col, (texto, var, ayuda) in enumerate((
                ("Suma por acierto", self.var_sec_ac, "puntos que suma cada acierto"),
                ("Descuenta por fallo", self.var_sec_fa, "puntos que resta cada fallo"),
                ("Descuenta en blanco", self.var_sec_bl, "puntos que resta dejarla sin contestar"))):
            col_marco = ttk.Frame(rejilla, style="Panel.TFrame")
            col_marco.grid(row=0, column=col, padx=(0, 18), sticky="w")
            ttk.Label(col_marco, text=texto, style="Campo.TLabel").pack(anchor="w")
            ent = ttk.Entry(col_marco, textvariable=var, font=("Consolas", 11), width=8)
            ent.pack(anchor="w", pady=2)
            ent.bind("<KeyRelease>", lambda e: (self._tocado(), self._pintar_resumen_seccion()), add="+")
            ttk.Label(col_marco, text=ayuda, style="Ayuda.TLabel").pack(anchor="w")

        self.lbl_sec_resumen = ttk.Label(caja, text="", font=("Consolas", 10, "bold"),
                                         foreground=C_VERDE, background=C_FONDO)
        self.lbl_sec_resumen.pack(anchor="w", padx=10, pady=(8, 10))

        # ---------- aleatorio ----------
        caja = ttk.LabelFrame(m, text=" Intento aleatorio ")
        caja.pack(fill="x", padx=10, pady=(6, 14))
        rotulo(caja, "Cuántas preguntas de este bloque salen al azar",
               "bloques[].porIntento",
               'botón 🔀 «Nuevo Intento (Aleatorio)» → opción 🎲',
               "0 = salen todas. Si pones un número, en el intento aleatorio total saldrán "
               "solo esas preguntas del bloque, elegidas al azar. El orden de los bloques "
               "nunca cambia: el que pongas primero aquí sale siempre primero."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_sec_por = tk.StringVar(value="0")
        sp = ttk.Spinbox(caja, from_=0, to=500, textvariable=self.var_sec_por, width=8,
                         font=("Consolas", 11), command=self._tocado)
        sp.pack(anchor="w", padx=10, pady=(0, 10))
        self._vigilar(sp)

    # ---------- color ----------
    def _pintar_muestra_color(self):
        color = color_valido(self.var_sec_color.get(), None)
        self.muestra_color.config(background=color or C_FONDO)

    def poner_color(self, valor):
        self.var_sec_color.set(valor)
        self._pintar_muestra_color()
        self._tocado()

    def elegir_color(self):
        actual = color_valido(self.var_sec_color.get(), COLOR_SUPUESTO)
        elegido = colorchooser.askcolor(color=actual, parent=self,
                                        title="Color del bloque")
        if elegido and elegido[1]:
            self.poner_color(elegido[1])

    # ---------- lista de bloques ----------
    def refrescar_lista_sec(self, seleccionar=None):
        self._silencio = True
        self.lst_sec.delete(0, "end")
        for i, b in enumerate(self.datos["bloques"]):
            cuantas = sum(1 for q in self.datos["preguntas"] if q["bloqueId"] == b["id"])
            marca = "📝" if b["tipo"] == "test" else "📁"
            self.lst_sec.insert("end", "%d. %s %-4s %-16s %2d preg."
                                % (i + 1, marca, b["id"], resumen(b["titulo"], 16), cuantas))
        if seleccionar is None:
            seleccionar = self.i_sec
        if self.datos["bloques"]:
            if seleccionar is None or seleccionar >= len(self.datos["bloques"]):
                seleccionar = 0
            self.lst_sec.selection_clear(0, "end")
            self.lst_sec.selection_set(seleccionar)
            self.lst_sec.see(seleccionar)
        else:
            seleccionar = None
        self._silencio = False
        self.i_sec = seleccionar
        self.cargar_seccion()
        self.refrescar_combo_bloques()
        self.refrescar_envio_bloques()
        self._pintar_titulo()

    def _sel_seccion(self, _e=None):
        if self._silencio:
            return
        sel = self.lst_sec.curselection()
        if not sel or sel[0] == self.i_sec:
            return
        self.volcar_seccion()
        self.i_sec = sel[0]
        self.cargar_seccion()

    def seccion_actual(self):
        if self.i_sec is None or self.i_sec >= len(self.datos["bloques"]):
            return None
        return self.datos["bloques"][self.i_sec]

    def cargar_seccion(self):
        b = self.seccion_actual()
        for clave, *_ in CAMPOS_BLOQUE:
            self.w_sec[clave].set("" if b is None else str(b.get(clave, "")))
        self.var_sec_tipo.set("supuesto" if b is None else b["tipo"])
        self.var_sec_modo.set("individual" if b is None else b["modo"])
        self.var_sec_cabecera.set(True if b is None
                                  else b.get("cabeceraSobreEnunciado", True) is not False)
        self.var_sec_opcion_una.set(True if b is None
                                    else b.get("opcionUnaEnUna", True) is not False)
        self.var_sec_color.set(COLOR_SUPUESTO if b is None else b["color"])
        self.var_sec_por.set("0" if b is None else str(b["porIntento"]))
        self.var_sec_ac.set("1" if b is None else nUm(b["acierto"]))
        self.var_sec_fa.set("0" if b is None else nUm(b["fallo"]))
        self.var_sec_bl.set("0" if b is None else nUm(b["blanco"]))
        self._pintar_muestra_color()
        self._pintar_resumen_seccion()

    def volcar_seccion(self):
        b = self.seccion_actual()
        if b is None:
            return
        antiguo = b["id"]
        nuevo = re.sub(r"[^A-Za-z0-9_-]", "", self.w_sec["id"].get().strip()) or antiguo
        otros = {x["id"] for x in self.datos["bloques"] if x is not b}
        while nuevo in otros:
            nuevo += "x"
        if nuevo != antiguo:
            for q in self.datos["preguntas"]:
                if q["bloqueId"] == antiguo:
                    q["bloqueId"] = nuevo
        b["id"] = nuevo
        b["titulo"] = self.w_sec["titulo"].get().strip() or ("Teoría" if b["tipo"] == "test"
                                                             else "Supuesto práctico")
        b["tipo"] = self.var_sec_tipo.get()
        b["modo"] = self.var_sec_modo.get()
        b["cabeceraSobreEnunciado"] = bool(self.var_sec_cabecera.get())
        b["opcionUnaEnUna"] = bool(self.var_sec_opcion_una.get())
        b["color"] = color_valido(self.var_sec_color.get(),
                                  COLOR_TEST if b["tipo"] == "test" else COLOR_SUPUESTO)
        try:
            b["porIntento"] = max(0, int(float(self.var_sec_por.get().replace(",", "."))))
        except ValueError:
            b["porIntento"] = 0
        b["acierto"] = numero(self.var_sec_ac.get(), 1.0)
        b["fallo"] = abs(numero(self.var_sec_fa.get(), 0.0))
        b["blanco"] = abs(numero(self.var_sec_bl.get(), 0.0))
        if b["tipo"] == "test":
            for q in self.datos["preguntas"]:
                if q["bloqueId"] == b["id"]:
                    q["statementId"] = None

    def _cambio_tipo_seccion(self):
        b = self.seccion_actual()
        if b is None:
            return
        nuevo = self.var_sec_tipo.get()
        if nuevo == "test":
            enganchadas = [q for q in self.datos["preguntas"]
                           if q["bloqueId"] == b["id"] and q["statementId"]]
            if enganchadas and not messagebox.askyesno(
                    "Cambiar a bloque de teoría",
                    "Este bloque tiene %d pregunta(s) enlazadas a un enunciado.\n\n"
                    "Al convertirlo en bloque de teoría dejarán de mostrar los hechos "
                    "(el enunciado no se borra).\n\n¿Continuar?" % len(enganchadas),
                    parent=self):
                self.var_sec_tipo.set(b["tipo"])
                return
        # Colores y modo por defecto del nuevo tipo, si estaban en los del anterior
        if self.var_sec_color.get() in (COLOR_SUPUESTO, COLOR_TEST):
            self.var_sec_color.set(COLOR_TEST if nuevo == "test" else COLOR_SUPUESTO)
        self.var_sec_modo.set("cadena" if nuevo == "test" else "individual")
        self.volcar_seccion()
        self._pintar_muestra_color()
        self.refrescar_lista_sec(self.i_sec)
        self.refrescar_lista_preg()
        self._tocado()

    def _pintar_resumen_seccion(self):
        b = self.seccion_actual()
        if b is None:
            self.lbl_sec_resumen.config(text="")
            return
        cuantas = sum(1 for q in self.datos["preguntas"] if q["bloqueId"] == b["id"])
        maximo = cuantas * numero(self.var_sec_ac.get(), 1.0)
        self.lbl_sec_resumen.config(
            text="%d preguntas en este bloque  ·  puntuación máxima: %s puntos"
                 % (cuantas, nUm(maximo)))

    # ---------- añadir / borrar / mover bloques ----------
    def _nuevo_id_bloque(self):
        usados = {b["id"] for b in self.datos["bloques"]}
        n = 1
        while ("B%d" % n) in usados:
            n += 1
        return "B%d" % n

    def anadir_seccion(self, tipo):
        self.volcar_seccion()
        self.datos["bloques"].append(bloque_vacio(tipo, self._nuevo_id_bloque()))
        self.refrescar_lista_sec(len(self.datos["bloques"]) - 1)
        self.refrescar_lista_preg()
        self._tocado()
        self.estado("Bloque de %s añadido. Ahora añade sus preguntas en la pestaña 4."
                    % ("teoría" if tipo == "test" else "supuesto"))

    def duplicar_seccion(self):
        b = self.seccion_actual()
        if b is None:
            return
        self.volcar_seccion()
        copia = json.loads(json.dumps(b))
        copia["id"] = self._nuevo_id_bloque()
        copia["titulo"] = b["titulo"] + " (copia)"
        self.datos["bloques"].insert(self.i_sec + 1, copia)
        self.refrescar_lista_sec(self.i_sec + 1)
        self._tocado()

    def borrar_seccion(self):
        b = self.seccion_actual()
        if b is None:
            return
        if len(self.datos["bloques"]) == 1:
            messagebox.showinfo("Un bloque como mínimo",
                                "El examen necesita al menos un bloque.", parent=self)
            return
        suyas = [q for q in self.datos["preguntas"] if q["bloqueId"] == b["id"]]
        aviso = "¿Borrar el bloque «%s»?" % b["titulo"]
        if suyas:
            aviso += ("\n\nATENCIÓN: se borrarán también sus %d preguntas."
                      % len(suyas))
        if not messagebox.askyesno("Borrar bloque", aviso, parent=self):
            return
        self.volcar_pregunta()
        self.datos["preguntas"] = [q for q in self.datos["preguntas"]
                                   if q["bloqueId"] != b["id"]]
        del self.datos["bloques"][self.i_sec]
        self.i_preg = 0 if self.datos["preguntas"] else None
        self.refrescar_lista_sec(max(0, self.i_sec - 1))
        self.refrescar_lista_preg(self.i_preg)
        self._tocado()

    def mover_seccion(self, paso):
        if self.i_sec is None:
            return
        destino = self.i_sec + paso
        lista = self.datos["bloques"]
        if destino < 0 or destino >= len(lista):
            return
        self.volcar_seccion()
        lista[self.i_sec], lista[destino] = lista[destino], lista[self.i_sec]
        self.ordenar_preguntas_por_bloque()
        self.refrescar_lista_sec(destino)
        self.refrescar_lista_preg()
        self._tocado()
        self.estado("Orden de los bloques: %s"
                    % " → ".join(b["titulo"] for b in self.datos["bloques"]))

    def ordenar_preguntas_por_bloque(self):
        """Las preguntas se guardan en el orden del examen: bloque a bloque."""
        orden = {b["id"]: i for i, b in enumerate(self.datos["bloques"])}
        self.datos["preguntas"].sort(key=lambda q: orden.get(q["bloqueId"], 0))

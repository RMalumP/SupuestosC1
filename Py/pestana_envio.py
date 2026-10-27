# -*- coding: utf-8 -*-
"""
PESTAÑA 5 · BOTONES, OPCIONES Y ENVÍO
═════════════════════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
from editor_comun import *  # noqa: F401,F403


class PestanaEnvio:

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 5 — BOTONES, OPCIONES Y ENVÍO DE RESULTADOS
    # ═════════════════════════════════════════════════════════════
    def _pestana_botones(self):
        cont = MarcoScroll(self.cuaderno)
        self.cuaderno.add(cont, text="  5 · Botones y envío  ")
        m = cont.interior
        self.w_ui = {}

        ttk.Label(m, text="Botones, opciones y envío de resultados",
                  style="Titulo.TLabel").pack(anchor="w", padx=16, pady=(14, 2))
        ttk.Label(m, style="Ayuda.TLabel", wraplength=880, justify="left",
                  text="Decide qué botones ve el alumno, cómo se llaman y a dónde se mandan "
                       "los resultados. En el archivo HTML viven en los apartados «interfaz» "
                       "y «envio»."
                  ).pack(anchor="w", padx=16, pady=(0, 10))

        # ---------- 0. interruptor general de todas las opciones ----------
        caja = ttk.LabelFrame(m, text=" Opciones de la página: activar o desactivar ")
        caja.pack(fill="x", padx=16, pady=6)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Aquí están TODAS las opciones del panel ⚙ y de la lectura. Marca las que "
                       "quieres que tenga este supuesto; las que desmarques no se ven en la "
                       "página. Más abajo (A y B) puedes además cambiar sus textos. Los botones "
                       "de abajo marcan o desmarcan todo de una vez."
                  ).pack(anchor="w", padx=10, pady=(8, 6))
        self.var_panel = {}
        for clave, texto, activa in (
                ("fuente", "Tamaño de letra (A, A+, A++)", None),
                ("tema", "Tema oscuro", "Empieza en oscuro"),
                ("deslizar", "Deslizar para cambiar de pregunta (móvil)", "Empieza activado"),
                ("atajos", "Atajos de teclado (?)", None)):
            marco = ttk.Frame(caja, style="Panel.TFrame")
            marco.pack(fill="x", padx=10, pady=1)
            v = tk.BooleanVar(value=True)
            ttk.Checkbutton(marco, text=texto, variable=v, command=self._tocado).pack(side="left")
            self.var_panel[clave] = {"visible": v}
            if activa:
                va = tk.BooleanVar(value=PANEL_DEFECTO[clave]["activa"])
                ttk.Checkbutton(marco, text=activa, variable=va,
                                command=self._tocado).pack(side="left", padx=(18, 0))
                self.var_panel[clave]["activa"] = va
        for texto, var in (("Corazón de favoritas ♥", self.var_cfg_corazon),
                           ("Subrayar con colores", self.var_cfg_subrayar),
                           ("Justificar el enunciado", self.var_just["enunciado"]),
                           ("Justificar las preguntas y respuestas", self.var_just["pregunta"]),
                           ("Justificar las justificaciones", self.var_just["motivacion"])):
            ttk.Checkbutton(caja, text=texto, variable=var,
                            command=self._tocado).pack(anchor="w", padx=10, pady=1)
        botones = ttk.Frame(caja, style="Panel.TFrame")
        botones.pack(fill="x", padx=10, pady=(8, 10))
        ttk.Button(botones, text="Activar todas", command=lambda: self.poner_todas_opciones(True)
                   ).pack(side="left")
        ttk.Button(botones, text="Desactivar todas", command=lambda: self.poner_todas_opciones(False)
                   ).pack(side="left", padx=6)
        ttk.Button(botones, text="Restablecer", command=self.restablecer_opciones
                   ).pack(side="left")

        # ---------- A. cabecera y panel ⚙ ----------
        caja = ttk.LabelFrame(m, text=" Cabecera y panel de opciones (⚙) ")
        caja.pack(fill="x", padx=16, pady=6)
        for clave, visible, html, rotulo_texto, ayuda in CAMPOS_CABECERA:
            self._fila_interfaz(caja, clave, visible, html, ayuda, rotulo_texto)
        ttk.Frame(caja, height=6).pack()

        # ---------- B. botonera ----------
        caja = ttk.LabelFrame(m, text=" Botones de abajo y de la pantalla de resultados ")
        caja.pack(fill="x", padx=16, pady=6)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Desmarca los que no quieras que aparezcan. Los cuatro últimos son "
                       "los que salen al terminar el examen, tanto en la botonera de abajo "
                       "como en la ventana de resultados."
                  ).pack(anchor="w", padx=10, pady=(8, 6))
        for clave, visible, html, ayuda in CAMPOS_BOTONERA:
            self._fila_interfaz(caja, clave, visible, html, ayuda, "Texto del botón",
                                compacto=True)
        ttk.Frame(caja, height=6).pack()

        # ---------- C. envío de resultados ----------
        caja = ttk.LabelFrame(m, text=" Envío de resultados (formulario de Google) ")
        caja.pack(fill="x", padx=16, pady=(6, 18))

        rotulo(caja, "Dirección a la que se envían los resultados", "envio.url",
               'formulario destino del botón 📤',
               "Es la dirección del formulario terminada en /formResponse. Se obtiene "
               "abriendo el formulario, copiando su enlace y cambiando el final "
               "«/viewform» por «/formResponse». Si se deja vacía, el botón de enviar "
               "no aparece."
               ).pack(anchor="w", padx=10, pady=(10, 2))
        self.var_envio_url = tk.StringVar()
        ent = ttk.Entry(caja, textvariable=self.var_envio_url, font=("Consolas", 9))
        ent.pack(fill="x", padx=10, pady=(0, 8))
        self._vigilar(ent)

        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="CÓMO SE AVERIGUA LA CASILLA DE CADA PREGUNTA: en el formulario, menú "
                       "⋮ → «Obtener enlace autorrellenado», rellena cada campo con un valor "
                       "cualquiera y copia el enlace: dentro verás trozos como "
                       "«entry.1234567=lo-que-escribiste». Ese «entry.1234567» es lo que hay "
                       "que pegar aquí. Las casillas que dejes vacías simplemente no se envían."
                  ).pack(anchor="w", padx=10, pady=(0, 8))

        rejilla = ttk.Frame(caja, style="Panel.TFrame")
        rejilla.pack(fill="x", padx=10)
        self.w_envio = {}
        for fila, (clave, visible, que) in enumerate(CAMPOS_ENVIO):
            ttk.Label(rejilla, text=visible, style="Campo.TLabel"
                      ).grid(row=fila, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            e = ttk.Entry(rejilla, textvariable=var, font=("Consolas", 9), width=22)
            e.grid(row=fila, column=1, sticky="w", padx=10)
            self._vigilar(e)
            self.w_envio[clave] = var
            ttk.Label(rejilla, text="envio.%s   ·   %s" % (clave, que), style="Tec.TLabel"
                      ).grid(row=fila, column=2, sticky="w")

        # ── Total absoluto: todos los bloques sumados como uno solo ──
        self.var_enviar_total = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            caja, variable=self.var_enviar_total, command=self._tocado,
            text="Enviar el TOTAL de todos los bloques (recuento absoluto)"
            ).pack(anchor="w", padx=10, pady=(14, 0))
        ttk.Label(caja, style="Tec.TLabel",
                  text="envio.enviarTotal  ·  envio.total{}   ·   suma las preguntas, "
                       "aciertos, fallos, en blanco y puntos de TODOS los bloques del "
                       "intento").pack(anchor="w", padx=10)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Es lo normal cuando el examen tiene varios bloques pero un solo "
                       "formulario: se manda una única cifra para todo el examen. Si una "
                       "casilla de aquí coincidiera con la de algún bloque, manda el total."
                  ).pack(anchor="w", padx=10, pady=(0, 4))
        rejilla_total = ttk.Frame(caja, style="Panel.TFrame")
        rejilla_total.pack(fill="x", padx=10, pady=(0, 6))
        self.w_envio_total = {}
        for col, (clave, etiqueta) in enumerate(CAMPOS_ENVIO_BLOQUE):
            ttk.Label(rejilla_total, text=etiqueta, style="Tec.TLabel"
                      ).grid(row=0, column=col, sticky="w", padx=(0 if col == 0 else 6, 0))
            var = tk.StringVar()
            ent = ttk.Entry(rejilla_total, textvariable=var, font=("Consolas", 9), width=16)
            ent.grid(row=1, column=col, sticky="w", padx=(0 if col == 0 else 6, 0), pady=2)
            self._vigilar(ent)
            self.w_envio_total[clave] = var

        ttk.Label(caja, text="Casillas de cada bloque (opcional)", style="Campo.TLabel"
                  ).pack(anchor="w", padx=10, pady=(14, 0))
        ttk.Label(caja, style="Tec.TLabel",
                  text="bloques[].envio   ·   se envían solo los bloques que hayan salido "
                       "en ese intento").pack(anchor="w", padx=10)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Un juego de casillas por bloque, para llevar al formulario cuántas "
                       "preguntas tuvo cada sección y cómo fue en ella. Vienen en blanco: "
                       "úsalas solo si el formulario tiene casillas para cada bloque."
                  ).pack(anchor="w", padx=10, pady=(0, 6))
        self.marco_envio_bloques = ttk.Frame(caja, style="Panel.TFrame")
        self.marco_envio_bloques.pack(fill="x", padx=10, pady=(0, 14))
        self.w_envio_bloque = {}

        # ---------- D. segundo formulario: detalle pregunta a pregunta ----------
        caja = ttk.LabelFrame(m, text=" Envío automático del detalle pregunta a pregunta ")
        caja.pack(fill="x", padx=16, pady=(6, 18))

        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Este segundo formulario NO sustituye al de arriba: es un complemento "
                       "y se manda solo, sin que el alumno tenga que pulsar nada, en cuanto "
                       "corrige el examen (o se le agota el tiempo). Lleva el nombre del "
                       "supuesto, la fecha y hora del envío, los aciertos y los fallos en "
                       "bruto (sin baremo) y, de cada pregunta, si la acertó y qué opción "
                       "marcó: «Correcta: …» o «Incorrecta: …», y «En blanco» si no la "
                       "contestó.\n\n"
                       "Cada pregunta va SIEMPRE a la casilla de su número de orden en la "
                       "pestaña «4 · Preguntas» (la 1ª a «Pregunta 1», y así hasta 80), "
                       "aunque el intento salga aleatorizado o solo con parte de ellas. Las "
                       "preguntas que no salgan en el intento dejan su casilla vacía.\n\n"
                       "Viene ya configurado con el formulario del proyecto: no hace falta "
                       "tocar nada."
                  ).pack(anchor="w", padx=10, pady=(10, 8))

        rotulo(caja, "Dirección del formulario del detalle", "envioDetalle.url",
               "formulario que se manda solo al corregir",
               "Igual que la de arriba: la del formulario, terminada en /formResponse. "
               "Si se deja vacía, no se manda nada."
               ).pack(anchor="w", padx=10, pady=(0, 2))
        self.var_detalle_url = tk.StringVar()
        ent = ttk.Entry(caja, textvariable=self.var_detalle_url, font=("Consolas", 9))
        ent.pack(fill="x", padx=10, pady=(0, 8))
        self._vigilar(ent)

        rejilla = ttk.Frame(caja, style="Panel.TFrame")
        rejilla.pack(fill="x", padx=10)
        self.w_detalle = {}
        for fila, (clave, visible, que) in enumerate(CAMPOS_ENVIO_DETALLE):
            ttk.Label(rejilla, text=visible, style="Campo.TLabel"
                      ).grid(row=fila, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            e = ttk.Entry(rejilla, textvariable=var, font=("Consolas", 9), width=22)
            e.grid(row=fila, column=1, sticky="w", padx=10)
            self._vigilar(e)
            self.w_detalle[clave] = var
            ttk.Label(rejilla, text="envioDetalle.%s   ·   %s" % (clave, que),
                      style="Tec.TLabel").grid(row=fila, column=2, sticky="w")

        ttk.Label(caja, text="Casillas de las %d preguntas" % len(ENTRADAS_PREGUNTA_DETALLE), style="Campo.TLabel"
                  ).pack(anchor="w", padx=10, pady=(14, 0))
        ttk.Label(caja, style="Tec.TLabel",
                  text="envioDetalle.preguntas   ·   una casilla por línea, en orden: "
                       "Pregunta 1, Pregunta 2 …").pack(anchor="w", padx=10)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Solo hay que tocarlas si algún día cambia el formulario. Si se "
                       "borran todas, se vuelven a poner las del proyecto."
                  ).pack(anchor="w", padx=10, pady=(0, 6))
        marco_cas = ttk.Frame(caja, style="Panel.TFrame")
        marco_cas.pack(fill="x", padx=10, pady=(0, 6))
        self.txt_detalle_preguntas = tk.Text(
            marco_cas, height=8, wrap="none", font=("Consolas", 9), relief="solid",
            borderwidth=1, background="white", foreground="#111827",
            insertbackground="#111827", padx=6, pady=4)
        barra_cas = ttk.Scrollbar(marco_cas, orient="vertical",
                                  command=self.txt_detalle_preguntas.yview)
        self.txt_detalle_preguntas.configure(yscrollcommand=barra_cas.set)
        self.txt_detalle_preguntas.pack(side="left", fill="both", expand=True)
        barra_cas.pack(side="right", fill="y")
        self._vigilar(self.txt_detalle_preguntas)
        ttk.Button(caja, text="↺  Restaurar las casillas del proyecto",
                   command=self.restaurar_casillas_detalle).pack(anchor="w", padx=10, pady=(0, 14))

    def _fila_interfaz(self, padre, clave, visible, html, ayuda, rotulo_texto,
                       compacto=False):
        """Una línea de configuración: casilla «se ve» + campos de texto."""
        base = INTERFAZ_DEFECTO[clave]
        marco = ttk.Frame(padre, style="Panel.TFrame")
        marco.pack(fill="x", padx=10, pady=(8, 2))

        campos = {}
        var_visible = tk.BooleanVar(value=True)
        cabecera = ttk.Frame(marco, style="Panel.TFrame")
        cabecera.pack(fill="x")
        ttk.Checkbutton(cabecera, text=visible, variable=var_visible,
                        command=self._tocado).pack(side="left")
        campos["visible"] = var_visible

        # Estado con el que arranca el examen (solo algunas opciones lo tienen)
        for campo, etiqueta in CAMPOS_ESTADO.items():
            if campo not in base:
                continue
            var_estado = tk.BooleanVar(value=bool(base[campo]))
            ttk.Checkbutton(cabecera, text=etiqueta, variable=var_estado,
                            command=self._tocado).pack(side="left", padx=(18, 0))
            campos[campo] = var_estado

        if compacto and "texto" in base:
            var = tk.StringVar()
            ent = ttk.Entry(cabecera, textvariable=var, font=("Georgia", 10), width=34)
            ent.pack(side="right")
            self._vigilar(ent)
            campos["texto"] = var

        ttk.Label(marco, text="interfaz.%s   →   HTML: %s" % (clave, html),
                  style="Tec.TLabel").pack(anchor="w", padx=(22, 0))
        if ayuda:
            ttk.Label(marco, text=ayuda, style="Ayuda.TLabel", wraplength=820,
                      justify="left").pack(anchor="w", padx=(22, 0))

        if not compacto:
            for campo, etiqueta in (("texto", rotulo_texto or "Texto"),
                                    ("titulo", "Título (al pasar el ratón)"),
                                    ("url", "Página de destino")):
                if campo not in base:
                    continue
                linea = ttk.Frame(marco, style="Panel.TFrame")
                linea.pack(fill="x", padx=(22, 0), pady=1)
                ttk.Label(linea, text=etiqueta + ":", style="Ayuda.TLabel", width=24
                          ).pack(side="left")
                var = tk.StringVar()
                ancho = 12 if campo == "texto" and clave == "botonCasa" else 60
                ent = ttk.Entry(linea, textvariable=var, font=("Georgia", 10), width=ancho)
                ent.pack(side="left", fill="x", expand=(ancho > 12))
                self._vigilar(ent)
                campos[campo] = var

        self.w_ui[clave] = campos

    # ---------- casillas de envío por bloque ----------
    def refrescar_envio_bloques(self):
        if not hasattr(self, "marco_envio_bloques"):
            return
        self.volcar_envio_bloques()
        for hijo in self.marco_envio_bloques.winfo_children():
            hijo.destroy()
        self.w_envio_bloque = {}

        # Cabecera de columnas
        ttk.Label(self.marco_envio_bloques, text="Bloque", style="Tec.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        for col, (_clave, etiqueta) in enumerate(CAMPOS_ENVIO_BLOQUE):
            ttk.Label(self.marco_envio_bloques, text=etiqueta, style="Tec.TLabel"
                      ).grid(row=0, column=col + 1, sticky="w", padx=(6, 0))

        for fila, b in enumerate(self.datos["bloques"], start=1):
            ttk.Label(self.marco_envio_bloques,
                      text="%s · %s" % (b["id"], resumen(b["titulo"], 18)),
                      style="Campo.TLabel").grid(row=fila, column=0, sticky="w", pady=2)
            vars_bloque = {}
            for col, (clave, _etiqueta) in enumerate(CAMPOS_ENVIO_BLOQUE):
                var = tk.StringVar(value=b["envio"].get(clave, ""))
                ent = ttk.Entry(self.marco_envio_bloques, textvariable=var,
                                font=("Consolas", 9), width=16)
                ent.grid(row=fila, column=col + 1, sticky="w", padx=(6, 0), pady=2)
                self._vigilar(ent)
                vars_bloque[clave] = var
            self.w_envio_bloque[b["id"]] = vars_bloque

    def volcar_envio_bloques(self):
        if not getattr(self, "w_envio_bloque", None):
            return
        por_id = {b["id"]: b for b in self.datos["bloques"]}
        for ident, campos in self.w_envio_bloque.items():
            bloque = por_id.get(ident)
            if not bloque:
                continue
            bloque["envio"] = {c: v.get().strip() for c, v in campos.items()}

    # ---------- interruptor general de opciones ----------
    def _todas_las_casillas_se_ve(self):
        """Casillas «se ve» de la cabecera y la botonera + las opciones extra."""
        variables = [campos["visible"] for campos in self.w_ui.values() if "visible" in campos]
        variables += [c["visible"] for c in self.var_panel.values()]
        variables += [self.var_cfg_corazon, self.var_cfg_subrayar]
        variables += list(self.var_just.values())
        return variables

    def poner_todas_opciones(self, valor):
        for var in self._todas_las_casillas_se_ve():
            var.set(bool(valor))
        self._tocado()

    def restablecer_opciones(self):
        for clave, campos in self.w_ui.items():
            for campo, var in campos.items():
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(INTERFAZ_DEFECTO[clave].get(campo, True)))
        for clave, campos in self.var_panel.items():
            for campo, var in campos.items():
                var.set(PANEL_DEFECTO[clave][campo])
        self.var_cfg_corazon.set(True)
        self.var_cfg_subrayar.set(True)
        for var in self.var_just.values():
            var.set(True)
        self._tocado()

    def cargar_panel_opciones(self, cfg):
        panel = cfg.get("panel") if isinstance(cfg.get("panel"), dict) else {}
        for clave, campos in getattr(self, "var_panel", {}).items():
            dado = panel.get(clave) if isinstance(panel.get(clave), dict) else {}
            for campo, var in campos.items():
                var.set(dado.get(campo, PANEL_DEFECTO[clave][campo]) is not False)

    def volcar_panel_opciones(self):
        return {clave: {campo: bool(var.get()) for campo, var in campos.items()}
                for clave, campos in getattr(self, "var_panel", {}).items()}

    # ---------- cargar / volcar la pestaña ----------
    def cargar_botones(self):
        interfaz = self.datos.get("interfaz") or INTERFAZ_DEFECTO
        for clave, campos in self.w_ui.items():
            ajuste = interfaz.get(clave, INTERFAZ_DEFECTO[clave])
            for campo, var in campos.items():
                por_defecto = INTERFAZ_DEFECTO[clave].get(campo, "")
                valor = ajuste.get(campo, por_defecto)
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(valor))
                else:
                    var.set(str(valor))
        envio = self.datos.get("envio") or ENVIO_DEFECTO
        self.var_envio_url.set(envio.get("url", ""))
        for clave, var in self.w_envio.items():
            var.set(envio.get(clave, ""))
        self.var_enviar_total.set(bool(envio.get("enviarTotal", True)))
        total = envio.get("total") if isinstance(envio.get("total"), dict) else {}
        for clave, var in self.w_envio_total.items():
            var.set(total.get(clave, ""))
        self.refrescar_envio_bloques()

        detalle = self.datos.get("envioDetalle") or envio_detalle_por_defecto()
        self.var_detalle_url.set(detalle.get("url", ""))
        for clave, var in self.w_detalle.items():
            var.set(detalle.get(clave, ""))
        self._poner_casillas_detalle(detalle.get("preguntas")
                                     or ENTRADAS_PREGUNTA_DETALLE)

    def volcar_botones(self):
        if not getattr(self, "w_ui", None):
            return
        interfaz = {}
        for clave, base in INTERFAZ_DEFECTO.items():
            ajuste = dict(base)
            campos = self.w_ui.get(clave, {})
            for campo, var in campos.items():
                if isinstance(var, tk.BooleanVar):
                    ajuste[campo] = bool(var.get())
                else:
                    valor = var.get().strip()
                    ajuste[campo] = valor if valor else base.get(campo, "")
            interfaz[clave] = ajuste
        self.datos["interfaz"] = interfaz

        envio = {"url": self.var_envio_url.get().strip()}
        for clave, var in self.w_envio.items():
            envio[clave] = var.get().strip()
        envio["enviarTotal"] = bool(self.var_enviar_total.get())
        envio["total"] = {clave: var.get().strip()
                          for clave, var in self.w_envio_total.items()}
        self.datos["envio"] = envio
        self.volcar_envio_bloques()

        detalle = {"url": self.var_detalle_url.get().strip()}
        for clave, var in self.w_detalle.items():
            detalle[clave] = var.get().strip()
        casillas = [l.strip() for l in
                    self.txt_detalle_preguntas.get("1.0", "end").splitlines()]
        casillas = [c for c in casillas if c]
        detalle["preguntas"] = (normalizar_casillas_detalle(casillas) if casillas
                                else list(ENTRADAS_PREGUNTA_DETALLE))
        self.datos["envioDetalle"] = detalle

    # ---------- casillas del segundo formulario ----------
    def _poner_casillas_detalle(self, casillas):
        self.txt_detalle_preguntas.delete("1.0", "end")
        self.txt_detalle_preguntas.insert("1.0", "\n".join(casillas))

    def restaurar_casillas_detalle(self):
        self._poner_casillas_detalle(ENTRADAS_PREGUNTA_DETALLE)
        self._tocado()

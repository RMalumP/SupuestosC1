# -*- coding: utf-8 -*-
"""
PESTAÑA 4 · PREGUNTAS Y RESPUESTAS
══════════════════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
import herramientas_datos as herr
import normas_enlaces
import operaciones
import revision
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk
from editor_comun import (  # noqa: F401
    C_FONDO, C_VERDE, LETRAS, MAX_OPCIONES, MIN_OPCIONES, MarcoScroll, OPCIONES_POR_DEFECTO,
    _consejo, caja_texto, limpiar_texto, poner_texto, pregunta_vacia, registrar_ayuda, resumen,
    rotulo, sacar_texto)


class PestanaPreguntas:

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 4 — PREGUNTAS, RESPUESTAS Y SOLUCIONES
    # ═════════════════════════════════════════════════════════════
    def _pestana_preguntas(self):
        panel = ttk.Frame(self.cuaderno)
        self.cuaderno.add(panel, text="  4 · Preguntas y respuestas  ")

        divisor = ttk.PanedWindow(panel, orient="horizontal")
        divisor.pack(fill="both", expand=True, padx=8, pady=8)

        izq = ttk.Frame(divisor, width=380)
        izq.pack_propagate(False)
        divisor.add(izq, weight=0)

        ttk.Label(izq, text="Preguntas del examen", style="Titulo.TLabel").pack(anchor="w")
        ay = ttk.Frame(ttk.Frame(izq))
        ay.master.pack(anchor="w", fill="x")
        ay.pack(anchor="w", fill="x")
        ttk.Label(ay, style="Tec.TLabel",
                  text='preguntas[]  →  <div class="question-card">').pack(anchor="w")
        ttk.Label(ay, style="Ayuda.TLabel", wraplength=310, justify="left",
                  text="Este es el orden por defecto del examen. Las preguntas de un mismo "
                       "enunciado deben ir seguidas."
                  ).pack(anchor="w", pady=(0, 6))
        registrar_ayuda(ay)

        # Filtro: desplegable (todas, con errores, de un bloque…) y texto a buscar.
        filtro = ttk.Frame(izq)
        filtro.pack(fill="x", pady=(0, 4))
        self.var_filtro_preg = tk.StringVar(value="Todas")
        self.combo_filtro_preg = ttk.Combobox(filtro, textvariable=self.var_filtro_preg, state="readonly",
                                              width=16, values=operaciones.FILTROS_FIJOS)
        self.combo_filtro_preg.pack(side="left")
        self.combo_filtro_preg.bind("<<ComboboxSelected>>", lambda e: self.refrescar_lista_preg())
        self.var_buscar_preg = tk.StringVar()
        ent_f = ttk.Entry(filtro, textvariable=self.var_buscar_preg)
        ent_f.pack(side="left", fill="x", expand=True, padx=(4, 0))
        _consejo(ent_f, "Escribe para ver solo las preguntas que lo contienen (texto, opciones, "
                        "motivación o etiqueta) o su número.")
        self.var_buscar_preg.trace_add("write", lambda *_: self._filtro_luego())

        marco_lista = ttk.Frame(izq)
        marco_lista.pack(fill="both", expand=True)
        cols = ("num", "bloque", "enun", "texto", "estado")
        self.arbol_preg = ttk.Treeview(marco_lista, columns=cols, show="headings",
                                       selectmode="extended", height=20)
        for col, titulo, ancho, estira in (("num", "Nº", 30, False), ("bloque", "Bl.", 34, False),
                                           ("enun", "En.", 34, False), ("texto", "Pregunta", 160, True),
                                           ("estado", "", 48, False)):
            self.arbol_preg.heading(col, text=titulo, anchor="w")
            self.arbol_preg.column(col, width=ancho, minwidth=24, stretch=estira, anchor="w")
        self.arbol_preg.tag_configure("error", foreground="#b91c1c")
        self.arbol_preg.tag_configure("aviso", foreground="#b45309")
        barra_l = ttk.Scrollbar(marco_lista, orient="vertical", command=self.arbol_preg.yview)
        self.arbol_preg.configure(yscrollcommand=barra_l.set)
        self.arbol_preg.pack(side="left", fill="both", expand=True)
        barra_l.pack(side="left", fill="y")
        self.arbol_preg.bind("<<TreeviewSelect>>", self._sel_pregunta)
        self.arbol_preg.bind("<Delete>", lambda e: self.borrar_pregunta())
        self.lbl_filtro_preg = ttk.Label(izq, text="", style="Tec.TLabel")
        self.lbl_filtro_preg.pack(anchor="w")

        # Botones de la lista, como en las demás pestañas. Duplicar, Borrar, Subir y
        # Bajar actúan sobre todas las preguntas marcadas.
        bot = ttk.Frame(izq)
        bot.pack(fill="x", pady=(6, 2))
        ttk.Button(bot, text="＋ Añadir", command=self.anadir_pregunta,
                   style="Accion.TButton", width=10).grid(row=0, column=0, padx=1, pady=1)
        ttk.Button(bot, text="⧉ Duplicar", command=self.duplicar_pregunta,
                   width=10).grid(row=0, column=1, padx=1, pady=1)
        ttk.Button(bot, text="🗑 Borrar", command=self.borrar_pregunta,
                   width=10).grid(row=0, column=2, padx=1, pady=1)
        ttk.Button(bot, text="▲ Subir", command=lambda: self.mover_pregunta(-1),
                   width=10).grid(row=1, column=0, padx=1, pady=1)
        ttk.Button(bot, text="▼ Bajar", command=lambda: self.mover_pregunta(1),
                   width=10).grid(row=1, column=1, padx=1, pady=1)

        # Crear varias preguntas de golpe, ya con su número de respuestas.
        varias = ttk.Frame(izq)
        varias.pack(fill="x", pady=(2, 4))
        ttk.Label(varias, text="Crear").pack(side="left")
        self.var_crear_cuantas = tk.StringVar(value="5")
        sp_c = ttk.Spinbox(varias, from_=1, to=operaciones.MAX_CREAR, width=4,
                           textvariable=self.var_crear_cuantas)
        sp_c.pack(side="left", padx=4)
        ttk.Label(varias, text="preg. con").pack(side="left")
        self.var_crear_respuestas = tk.StringVar(value=str(OPCIONES_POR_DEFECTO))
        sp_r = ttk.Spinbox(varias, from_=MIN_OPCIONES, to=MAX_OPCIONES, width=3,
                           textvariable=self.var_crear_respuestas)
        sp_r.pack(side="left", padx=4)
        ttk.Label(varias, text="resp.").pack(side="left")
        b_crear = ttk.Button(varias, text="＋ Crear", width=9, style="Accion.TButton",
                             command=self.crear_varias_preguntas)
        b_crear.pack(side="left", padx=(6, 0))
        _consejo(b_crear, "Añade de una vez ese número de preguntas vacías, cada una con "
                          "ese número de respuestas, detrás de la pregunta seleccionada y "
                          "en su mismo bloque y enunciado.")

        cont = MarcoScroll(divisor)
        divisor.add(cont, weight=1)
        m = cont.interior

        # --- dónde va la pregunta: bloque, enunciado y etiqueta en una sola fila ---
        caja = ttk.LabelFrame(m, text=" Pregunta ")
        caja.pack(fill="x", padx=10, pady=(8, 6))
        fila = ttk.Frame(caja, style="Panel.TFrame")
        fila.pack(fill="x", padx=10, pady=(8, 2))
        for col, peso in ((0, 3), (1, 4), (2, 3)):
            fila.columnconfigure(col, weight=peso, uniform="ubic")

        def titulo_corto(col, texto, globo):
            et = ttk.Label(fila, text=texto, style="Campo.TLabel")
            et.grid(row=0, column=col, sticky="w", padx=(0 if col == 0 else 8, 0))
            _consejo(et, globo)

        titulo_corto(0, "Bloque",
                     "Bloque del examen en el que va esta pregunta  ·  preguntas[].bloqueId\n"
                     "Decide en qué sección sale (supuesto o teoría), de qué color es su casilla "
                     "y con qué baremo se corrige. Los bloques se crean en la pestaña «2 · Bloques».")
        titulo_corto(1, "Enunciado (hechos)",
                     "Enunciado al que pertenece  ·  preguntas[].statementId\n"
                     "Al llegar a esta pregunta, la página muestra arriba los hechos de ese "
                     "enunciado. «(pregunta suelta)» si no depende de ningún caso práctico. "
                     "En los bloques de teoría está desactivado.")
        titulo_corto(2, "Etiqueta de materia",
                     "Etiqueta de materia  ·  preguntas[].tag  →  <span class=\"q-tag\">\n"
                     "Línea pequeña en mayúsculas encima de la pregunta (p. ej. «LPACAP · Art. 21»). "
                     "Déjala VACÍA si el documento de origen no la pide.")
        self.var_preg_bloque = tk.StringVar()
        self.combo_bloque = ttk.Combobox(fila, textvariable=self.var_preg_bloque,
                                         state="readonly", font=("Consolas", 9))
        self.combo_bloque.grid(row=1, column=0, sticky="ew")
        self.combo_bloque.bind("<<ComboboxSelected>>", self._cambio_bloque_pregunta)
        self.var_preg_stmt = tk.StringVar()
        self.combo_stmt = ttk.Combobox(fila, textvariable=self.var_preg_stmt, state="readonly",
                                       font=("Consolas", 9))
        self.combo_stmt.grid(row=1, column=1, sticky="ew", padx=(8, 0))
        self.combo_stmt.bind("<<ComboboxSelected>>", self._cambio_stmt)
        self.var_preg_tag = tk.StringVar()
        ent = ttk.Entry(fila, textvariable=self.var_preg_tag, font=("Consolas", 10))
        ent.grid(row=1, column=2, sticky="ew", padx=(8, 0))
        self._vigilar(ent)

        # Modo foco: solo se enseña si el enunciado de la pregunta tiene bloques de hechos.
        self.marco_foco = ttk.Frame(caja, style="Panel.TFrame")
        self.marco_foco.pack(fill="x")
        rotulo(self.marco_foco, "Partes del enunciado de las que depende (modo foco)",
               "preguntas[].factIds",
               'factBlocks[].id  →  <div class="fact-block"> que se muestran en modo foco',
               "Marca aquí el hecho (o los hechos) desencadenantes concretos de los que "
               "depende esta pregunta. Con el MODO FOCO encendido en el panel ⚙ —y las "
               "preguntas de una en una—, esta pregunta mostrará SOLO esos bloques de "
               "hechos en vez del enunciado entero, con un botón para desplegarlo completo. "
               "Si no marcas ninguno, la pregunta enseña siempre el enunciado entero. "
               "Con Ctrl+clic se marcan y desmarcan varios."
               ).pack(anchor="w", padx=10, pady=(8, 2))
        marco_fl = ttk.Frame(self.marco_foco, style="Panel.TFrame")
        marco_fl.pack(fill="x", padx=10, pady=(0, 2))
        self.lst_factlink = tk.Listbox(marco_fl, font=("Consolas", 9), height=4,
                                       selectmode="extended", activestyle="none",
                                       exportselection=False)
        self.lst_factlink.pack(side="left", fill="both", expand=True)
        self.lst_factlink.bind("<<ListboxSelect>>", self._sel_factlink)
        colf = ttk.Frame(marco_fl, style="Panel.TFrame")
        colf.pack(side="left", padx=(6, 0))
        ttk.Button(colf, text="Ninguno", width=11,
                   command=self.limpiar_factlink).pack(pady=1)
        b_sug = ttk.Button(colf, text="✨ Sugerir", width=11, command=self.sugerir_factlink)
        b_sug.pack(pady=1)
        _consejo(b_sug, "Marca los hechos que más palabras raras (nombres, cifras, fechas…) comparten "
                        "con la pregunta, sus opciones y su motivación. Revísalo: es una sugerencia.")
        self.lbl_factlink = ttk.Label(caja, text="", style="Tec.TLabel")
        self.lbl_factlink.pack(anchor="w", padx=10, pady=(2, 2))

        rotulo(caja, "Texto de la pregunta", "preguntas[].q", '<div class="q-text">',
               "Lo que se lee en negrita dentro de la tarjeta de la pregunta."
               ).pack(anchor="w", padx=10, pady=(6, 2))
        marco, self.txt_preg_q = caja_texto(caja, alto=4)
        marco.pack(fill="x", padx=10, pady=(0, 10))
        self._vigilar(self.txt_preg_q)

        # --- respuestas ---
        caja = ttk.LabelFrame(m, text=" Respuestas — marca cuál (o cuáles) es la correcta ")
        caja.pack(fill="x", padx=10, pady=6)
        rotulo(caja, "Las opciones de esta pregunta", "preguntas[].a[]",
               '<div class="option"> → <span class="opt-letter">A…G</span>',
               "De 2 a 7 opciones; lo normal son cuatro. La casilla de la izquierda marca "
               "la correcta (preguntas[].correctas). OJO: la página baraja las opciones en "
               "cada intento, así que la correcta no saldrá siempre en la letra que ocupa aquí."
               ).pack(anchor="w", padx=10, pady=(8, 6))

        # Respuesta múltiple
        self.var_preg_multiple = tk.BooleanVar(value=False)
        ttk.Checkbutton(caja, variable=self.var_preg_multiple, command=self._cambio_multiple,
                        text="Respuesta múltiple  ·  preguntas[].multiple  →  hay que marcar "
                             "TODAS las que procedan (solo cuenta si se aciertan todas)"
                        ).pack(anchor="w", padx=10, pady=(0, 8))

        # Filas de opciones: se crean las siete y se enseñan las que tenga
        # la pregunta. Así añadir o quitar una es solo mostrar u ocultar.
        self.var_preg_ok = []
        self.filas_opcion = []
        self.txt_opciones = []
        for i in range(MAX_OPCIONES):
            fila = ttk.Frame(caja, style="Panel.TFrame")
            var = tk.BooleanVar(value=(i == 0))
            ttk.Checkbutton(fila, text="  %s  " % LETRAS[i], variable=var,
                            command=lambda n=i: self._marcar_correcta(n)
                            ).pack(side="left", anchor="n", pady=4)
            marco, txt = caja_texto(fila, alto=3, ancho=70)
            marco.pack(side="left", fill="x", expand=True)
            self._vigilar(txt)
            self.var_preg_ok.append(var)
            self.filas_opcion.append(fila)
            self.txt_opciones.append(txt)

        linea = ttk.Frame(caja, style="Panel.TFrame")
        linea.pack(fill="x", padx=10, pady=(6, 2))
        ttk.Button(linea, text="＋ Añadir respuesta", width=20, style="Accion.TButton",
                   command=self.anadir_opcion).pack(side="left")
        ttk.Button(linea, text="🗑 Quitar la última", width=20,
                   command=self.quitar_opcion).pack(side="left", padx=(6, 0))
        self.lbl_correcta = ttk.Label(linea, text="", font=("Consolas", 10, "bold"),
                                      foreground=C_VERDE, background=C_FONDO)
        self.lbl_correcta.pack(side="left", padx=(16, 0))

        rotulo(caja, "Cuántas de estas respuestas salen en el examen",
               "preguntas[].respuestas",
               'nº de <div class="option"> de ESTA pregunta',
               "Normalmente, lo que hayas puesto en la pestaña 1 para todo el examen. Aquí "
               "se le puede dar un número propio a una pregunta suelta: por ejemplo, escribir "
               "siete opciones y que salgan solo cuatro (la correcta y tres distractores "
               "sorteados en cada intento). Nunca se recorta por debajo de las correctas."
               ).pack(anchor="w", padx=10, pady=(10, 2))
        self.var_preg_respuestas = tk.StringVar()
        self._etiquetas_preg_resp = ["Las que diga la pestaña 1 (todo el examen)"] + \
                                    ["%d respuestas" % n for n in range(MIN_OPCIONES, MAX_OPCIONES + 1)]
        self._valores_preg_resp = [0] + list(range(MIN_OPCIONES, MAX_OPCIONES + 1))
        combo = ttk.Combobox(caja, textvariable=self.var_preg_respuestas, state="readonly",
                             font=("Georgia", 10), values=self._etiquetas_preg_resp)
        combo.pack(fill="x", padx=10, pady=(0, 4))
        combo.bind("<<ComboboxSelected>>", lambda e: self._tocado())
        self.lbl_aviso_resp = ttk.Label(caja, text="", style="Tec.TLabel")
        self.lbl_aviso_resp.pack(anchor="w", padx=10, pady=(0, 10))

        # --- corrección ---
        caja = ttk.LabelFrame(m, text=" Solución y motivación ")
        caja.pack(fill="both", expand=True, padx=10, pady=(6, 12))

        rotulo(caja, "Motivación legal (normativa aplicable)", "preguntas[].law",
               '<div class="feedback-body"> → <p>   ·   <div class="ci-law">',
               "Texto que aparece tras corregir, bajo el rótulo «⚖️ MOTIVACIÓN LEGAL Y NORMATIVA "
               "APLICABLE», y también en la corrección completa y en el PDF."
               ).pack(anchor="w", padx=10, pady=(8, 2))
        marco, self.txt_preg_law = caja_texto(caja, alto=7)
        marco.pack(fill="both", expand=True, padx=10, pady=(0, 2))
        self._vigilar(self.txt_preg_law)
        # Las citas que la página enlazará al BOE, para abrirlas y comprobarlas desde aquí.
        self.marco_boe = ttk.Frame(caja, style="Panel.TFrame")
        self.marco_boe.pack(fill="x", padx=10, pady=(0, 6))
        for evento in ("<KeyRelease>", "<<TextoTocado>>"):
            self.txt_preg_law.bind(evento, lambda e: self._boe_luego(), add="+")

        rotulo(caja, "Consejo o matiz práctico", "preguntas[].tip",
               '<div class="tip">  ·  <div class="ci-tip">',
               "Recuadro verde con 💡 debajo de la motivación legal. Déjalo vacío si no procede."
               ).pack(anchor="w", padx=10, pady=(4, 2))
        marco, self.txt_preg_tip = caja_texto(caja, alto=4)
        marco.pack(fill="x", padx=10, pady=(0, 12))
        self._vigilar(self.txt_preg_tip)

    # ---------- citas al BOE de la motivación ----------
    def _boe_luego(self):
        if getattr(self, "_espera_boe", None):
            self.after_cancel(self._espera_boe)
        self._espera_boe = self.after(600, self._pintar_boe)

    def _pintar_boe(self):
        self._espera_boe = None
        for w in self.marco_boe.winfo_children():
            w.destroy()
        try:
            normas = normas_enlaces.leer()[1]
        except OSError:
            normas = []
        citas = herr.enlaces_boe(sacar_texto(self.txt_preg_law), normas)
        if not citas:
            return
        ttk.Label(self.marco_boe, text="⚖ Abrir en el BOE:", style="Tec.TLabel").pack(side="left")
        for cita, _art, _sig, url in citas[:8]:
            b = ttk.Button(self.marco_boe, text=cita, command=lambda u=url: webbrowser.open(u))
            b.pack(side="left", padx=(4, 0))
            _consejo(b, url)

    # ---------- desplegable de bloques ----------
    def refrescar_combo_bloques(self):
        if not hasattr(self, "combo_bloque"):
            return
        self._ids_bloque = [b["id"] for b in self.datos["bloques"]]
        self.combo_bloque["values"] = [
            "%s · %s  (%s)" % (b["id"], resumen(b["titulo"], 34),
                               "teoría" if b["tipo"] == "test" else "supuesto")
            for b in self.datos["bloques"]]
        self._sincronizar_combo_bloque()

    def _sincronizar_combo_bloque(self):
        if not self.combo_bloque["values"]:
            return
        p = self.pregunta_actual()
        try:
            pos = self._ids_bloque.index(p["bloqueId"]) if p else 0
        except (ValueError, AttributeError, TypeError):
            pos = 0
        self.combo_bloque.current(pos)
        # En los bloques de teoría el enunciado no aplica
        es_test = bool(p) and self.tipo_de_bloque(p["bloqueId"]) == "test"
        self.combo_stmt.configure(state="disabled" if es_test else "readonly")

    def tipo_de_bloque(self, bloque_id):
        for b in self.datos["bloques"]:
            if b["id"] == bloque_id:
                return b["tipo"]
        return "supuesto"

    def _cambio_bloque_pregunta(self, _e=None):
        p = self.pregunta_actual()
        if p is None:
            return
        self.volcar_pregunta()
        self.ordenar_preguntas_por_bloque()
        nuevo = next((i for i, x in enumerate(self.datos["preguntas"]) if x is p), 0)
        self.refrescar_lista_preg(nuevo)
        self.refrescar_lista_sec(self.i_sec)
        self._tocado()

    # ---------- desplegable de enunciados ----------
    def refrescar_combo_enunciados(self):
        if not hasattr(self, "combo_stmt"):
            return
        self._ids_combo = [None] + [e["id"] for e in self.datos["enunciados"]]
        etiquetas = ["(pregunta suelta — sin bloque de hechos)"]
        etiquetas += ["%s · %s" % (e["id"], resumen(e["title"], 40))
                      for e in self.datos["enunciados"]]
        self.combo_stmt["values"] = etiquetas
        self._sincronizar_combo()

    def _sincronizar_combo(self):
        if not self.combo_stmt["values"]:
            self.refrescar_combo_enunciados()
            return
        p = self.pregunta_actual()
        sid = p["statementId"] if p else None
        try:
            pos = self._ids_combo.index(sid)
        except (ValueError, AttributeError):
            pos = 0
        self.combo_stmt.current(pos)

    def _cambio_stmt(self, _e=None):
        if self.pregunta_actual() is None:
            return
        self.volcar_pregunta()          # incluye el nuevo statementId
        self.refrescar_lista_preg(self.i_preg)
        self._tocado()

    # ---------- vínculo con los bloques de hechos (modo foco) ----------
    def refrescar_lista_factlink(self):
        """Rellena la lista de bloques de hechos del enunciado de la pregunta
        actual y marca los que tenga vinculados."""
        if not hasattr(self, "lst_factlink"):
            return
        self._silencio_fact = True
        self.lst_factlink.delete(0, "end")
        p = self.pregunta_actual()
        enun = None
        if p and p.get("statementId"):
            enun = next((e for e in self.datos["enunciados"]
                         if e["id"] == p["statementId"]), None)
        hechos = enun["factBlocks"] if enun else []
        self._ids_factlink = [h["id"] for h in hechos]
        for h in hechos:
            marca = "⚠" if h["red"] else "📋"
            if h["hidden"]:
                marca = "👁"
            self.lst_factlink.insert("end", "%-4s %s %s" % (h["id"], marca,
                                                            resumen(h["title"], 44)))
        if p is not None:
            # Se descartan los vínculos que ya no existan en ese enunciado
            p["factIds"] = [x for x in p.get("factIds", []) if x in self._ids_factlink]
            for i, ident in enumerate(self._ids_factlink):
                if ident in p["factIds"]:
                    self.lst_factlink.selection_set(i)
        self._silencio_fact = False

        try:
            if hechos:
                if not self.marco_foco.winfo_manager():
                    self.marco_foco.pack(fill="x", before=self.lbl_factlink)
            elif self.marco_foco.winfo_manager():
                self.marco_foco.pack_forget()
        except (tk.TclError, AttributeError):
            pass
        if p is None:
            texto = ""
        elif not p.get("statementId"):
            texto = "Esta pregunta no depende de ningún enunciado: el modo foco no le afecta."
        elif not hechos:
            texto = ("El enunciado %s todavía no tiene bloques de hechos (pestaña 3)."
                     % p["statementId"])
        elif not p["factIds"]:
            texto = "Sin vincular: en modo foco esta pregunta muestra el enunciado entero."
        else:
            texto = ("En modo foco se mostrarán solo: %s." % ", ".join(p["factIds"]))
        self.lbl_factlink.config(text=texto)

    def _sel_factlink(self, _e=None):
        if getattr(self, "_silencio_fact", False) or self._silencio:
            return
        p = self.pregunta_actual()
        if p is None or not getattr(self, "_ids_factlink", None):
            return
        p["factIds"] = [self._ids_factlink[i] for i in self.lst_factlink.curselection()
                        if i < len(self._ids_factlink)]
        self.lbl_factlink.config(
            text="Sin vincular: en modo foco esta pregunta muestra el enunciado entero."
                 if not p["factIds"]
                 else "En modo foco se mostrarán solo: %s." % ", ".join(p["factIds"]))
        self._pintar_vinculos_bloque()
        self._tocado()

    def sugerir_factlink(self):
        """Marca los hechos que más se parecen a la pregunta (se puede corregir a mano)."""
        p = self.pregunta_actual()
        if p is None or not getattr(self, "_ids_factlink", None):
            return
        self.volcar_pregunta()
        enun = next((e for e in self.datos["enunciados"] if e["id"] == p.get("statementId")), None)
        sugeridos = herr.sugerir_hechos(p, enun)
        if not sugeridos:
            self.estado("No veo ningún hecho claramente relacionado con esta pregunta.")
            return
        p["factIds"] = [ident for ident, _peso, _pal in sugeridos]
        self.refrescar_lista_factlink()
        self._pintar_vinculos_bloque()
        self._tocado()
        self.estado("Sugeridos: " + "; ".join("%s (por «%s»)" % (i, ", ".join(pal[:3]))
                                               for i, _peso, pal in sugeridos))

    def limpiar_factlink(self):
        """Quita todos los vínculos de la pregunta actual."""
        p = self.pregunta_actual()
        if p is None:
            return
        p["factIds"] = []
        self.refrescar_lista_factlink()
        self._pintar_vinculos_bloque()
        self._tocado()

    def _marcar_correcta(self, n=None):
        """Al marcar una casilla: si la pregunta NO es de respuesta múltiple,
        marcar una desmarca las demás (se comporta como un botón de radio)."""
        if n is not None and not self.var_preg_multiple.get() and self.var_preg_ok[n].get():
            for i, var in enumerate(self.var_preg_ok):
                if i != n:
                    var.set(False)
        if n is not None and not any(v.get() for v in self.var_preg_ok):
            # Siempre tiene que haber al menos una correcta
            self.var_preg_ok[n].set(True)
        self._pintar_correctas()
        self._tocado()

    def _cambio_multiple(self):
        """Al dejar de ser múltiple, se queda solo la primera correcta."""
        if not self.var_preg_multiple.get():
            visto = False
            for var in self.var_preg_ok:
                if var.get():
                    if visto:
                        var.set(False)
                    visto = True
        self._pintar_correctas()
        self._tocado()

    def _n_opciones(self):
        """Cuántas filas de respuesta hay a la vista."""
        return sum(1 for f in self.filas_opcion if f.winfo_manager())

    def _pintar_filas_opciones(self, cuantas):
        cuantas = max(MIN_OPCIONES, min(MAX_OPCIONES, cuantas))
        for i, fila in enumerate(self.filas_opcion):
            if i < cuantas:
                fila.pack(fill="x", padx=10, pady=2)
            else:
                fila.pack_forget()
                self.var_preg_ok[i].set(False)
        return cuantas

    def _pintar_correctas(self):
        marcadas = [LETRAS[i] for i, v in enumerate(self.var_preg_ok)
                    if v.get() and self.filas_opcion[i].winfo_manager()]
        if not marcadas:
            texto = "⚠ sin respuesta correcta marcada"
        elif len(marcadas) == 1:
            texto = "Correcta: %s" % marcadas[0]
        else:
            texto = "Correctas: %s" % ", ".join(marcadas)
        self.lbl_correcta.config(text=texto)
        self._pintar_aviso_respuestas()

    def _pintar_aviso_respuestas(self):
        """Explica, en cristiano, cuántas respuestas verá el alumno."""
        if not hasattr(self, "lbl_aviso_resp"):
            return
        escritas = self._n_opciones()
        propio = next((v for v, t in zip(self._valores_preg_resp, self._etiquetas_preg_resp)
                       if t == self.var_preg_respuestas.get()), 0)
        general = self.datos["config"].get("respuestas", 0)
        cuantas = propio or general or escritas
        correctas = sum(1 for i, v in enumerate(self.var_preg_ok)
                        if v.get() and i < escritas)
        minimo = correctas + (1 if escritas > correctas else 0)
        cuantas = min(escritas, max(cuantas, minimo))
        if cuantas >= escritas:
            texto = "Salen las %d opciones escritas." % escritas
        else:
            texto = ("De las %d escritas saldrán %d: la(s) correcta(s) y %d distractor(es) "
                     "sorteados en cada intento." % (escritas, cuantas, cuantas - correctas))
        self.lbl_aviso_resp.config(text=texto)

    def anadir_opcion(self):
        cuantas = self._n_opciones()
        if cuantas >= MAX_OPCIONES:
            self.estado("Una pregunta admite como mucho %d respuestas." % MAX_OPCIONES)
            return
        self._pintar_filas_opciones(cuantas + 1)
        poner_texto(self.txt_opciones[cuantas], "")
        self._pintar_correctas()
        self.txt_opciones[cuantas].focus_set()
        self._tocado()

    def quitar_opcion(self):
        cuantas = self._n_opciones()
        if cuantas <= MIN_OPCIONES:
            self.estado("Una pregunta necesita al menos %d respuestas." % MIN_OPCIONES)
            return
        if sacar_texto(self.txt_opciones[cuantas - 1]).strip() and not messagebox.askyesno(
                "Quitar respuesta",
                "La respuesta %s tiene texto escrito. ¿Quitarla igualmente?" % LETRAS[cuantas - 1],
                parent=self):
            return
        self._pintar_filas_opciones(cuantas - 1)
        if not any(v.get() for v in self.var_preg_ok):
            self.var_preg_ok[0].set(True)
        self._pintar_correctas()
        self._tocado()

    # ---------- lista de preguntas ----------
    def refrescar_lista_preg(self, seleccionar=None, marcadas=None):
        """Vuelve a pintar la lista (con el filtro puesto) y selecciona `seleccionar`
        (y, si se dan, también `marcadas`, para seguir con varias elegidas)."""
        self._silencio = True
        arbol = self.arbol_preg
        arbol.delete(*arbol.get_children())
        hallazgos = revision.revisar(self.datos)
        filtro = self.var_filtro_preg.get() or "Todas"
        valores = operaciones.opciones_de_filtro(self.datos)
        self.combo_filtro_preg["values"] = valores
        if filtro not in valores:
            filtro = "Todas"
            self.var_filtro_preg.set(filtro)
        visibles = set(operaciones.filtrar(self.datos, filtro, self.var_buscar_preg.get(), hallazgos))
        for f in operaciones.filas(self.datos, hallazgos):
            if f["n"] not in visibles:
                continue
            estado = f["marcas"]
            if f["nivel"]:
                estado += (" ✗ " if f["nivel"] == "error" else " ! ") + f["motivo"]
            arbol.insert("", "end", iid=str(f["n"]), tags=(f["nivel"],) if f["nivel"] else (),
                         values=("%02d" % f["num"], f["bloque"], f["enunciado"],
                                 resumen(f["texto"], 60), estado.strip()))
        total = len(self.datos["preguntas"])
        self.lbl_filtro_preg.config(text="" if len(visibles) == total else
                                    "Se ven %d de %d preguntas (filtro: %s)." % (len(visibles), total, filtro))
        if seleccionar is None:
            seleccionar = self.i_preg
        if self.datos["preguntas"]:
            if seleccionar is None or seleccionar >= total:
                seleccionar = 0
            elegir = [str(i) for i in sorted(set(marcadas or []) | {seleccionar}) if str(i) in arbol.get_children()]
            if elegir:
                arbol.selection_set(elegir)
                arbol.focus(str(seleccionar) if str(seleccionar) in elegir else elegir[0])
                arbol.see(str(seleccionar) if str(seleccionar) in elegir else elegir[0])
        else:
            seleccionar = None
        self._silencio = False
        self.i_preg = seleccionar
        self.cargar_pregunta()
        if hasattr(self, "lbl_sec_resumen"):
            self._pintar_resumen_seccion()
        if hasattr(self, "lbl_num_preg"):
            self.lbl_num_preg.config(text="%d PREGUNTAS" % len(self.datos["preguntas"]))
        self._pintar_titulo()

    def _filtro_luego(self):
        """Al escribir en el filtro se espera un momento (no se repinta en cada letra)."""
        if getattr(self, "_espera_filtro", None):
            self.after_cancel(self._espera_filtro)
        self._espera_filtro = self.after(250, self._aplicar_filtro)

    def _aplicar_filtro(self):
        self._espera_filtro = None
        self.volcar_pregunta()
        self.refrescar_lista_preg()

    def preguntas_marcadas(self):
        """Índices de las preguntas elegidas en la lista (una o varias)."""
        sel = sorted(int(x) for x in self.arbol_preg.selection())
        if not sel and self.i_preg is not None:
            sel = [self.i_preg]
        return sel

    def _sel_pregunta(self, _e=None):
        if self._silencio:
            return
        sel = self.arbol_preg.selection()
        if not sel:
            return
        foco = self.arbol_preg.focus()
        nuevo = int(foco) if foco in sel else int(sel[0])
        if nuevo == self.i_preg:
            return
        self.volcar_pregunta()
        self.i_preg = nuevo
        self.cargar_pregunta()

    def pregunta_actual(self):
        if self.i_preg is None or self.i_preg >= len(self.datos["preguntas"]):
            return None
        return self.datos["preguntas"][self.i_preg]

    def cargar_pregunta(self):
        p = self.pregunta_actual()
        self.var_preg_tag.set("" if p is None else p["tag"])
        poner_texto(self.txt_preg_q, "" if p is None else p["q"])

        opciones = (p["a"] if p else [])[:MAX_OPCIONES]
        cuantas = self._pintar_filas_opciones(len(opciones) or OPCIONES_POR_DEFECTO)
        correctas = set(p["correctas"]) if p else {0}
        for i in range(MAX_OPCIONES):
            poner_texto(self.txt_opciones[i], opciones[i] if i < len(opciones) else "")
            self.var_preg_ok[i].set(i in correctas and i < cuantas)
        self.var_preg_multiple.set(bool(p and p.get("multiple")))
        propio = p.get("respuestas", 0) if p else 0
        pos = self._valores_preg_resp.index(propio) if propio in self._valores_preg_resp else 0
        self.var_preg_respuestas.set(self._etiquetas_preg_resp[pos])

        poner_texto(self.txt_preg_law, "" if p is None else p["law"])
        self._pintar_boe()
        poner_texto(self.txt_preg_tip, "" if p is None else p["tip"])
        self._pintar_correctas()
        self._sincronizar_combo_bloque()
        self._sincronizar_combo()
        self.refrescar_lista_factlink()

    def volcar_pregunta(self):
        p = self.pregunta_actual()
        if p is None:
            return
        p["tag"] = self.var_preg_tag.get().strip()
        p["q"] = limpiar_texto(sacar_texto(self.txt_preg_q))

        # Solo cuentan las filas de respuesta que estén a la vista
        cuantas = self._n_opciones()
        p["a"] = [limpiar_texto(sacar_texto(self.txt_opciones[i])) for i in range(cuantas)]
        correctas = [i for i in range(cuantas) if self.var_preg_ok[i].get()]
        p["correctas"] = correctas or [0]
        p["c"] = p["correctas"][0]
        p["multiple"] = bool(self.var_preg_multiple.get())
        etiqueta = self.var_preg_respuestas.get()
        p["respuestas"] = next((v for v, t in zip(self._valores_preg_resp,
                                                  self._etiquetas_preg_resp) if t == etiqueta), 0)

        p["law"] = limpiar_texto(sacar_texto(self.txt_preg_law))
        p["tip"] = limpiar_texto(sacar_texto(self.txt_preg_tip))
        if getattr(self, "_ids_bloque", None) and self.combo_bloque["values"]:
            p["bloqueId"] = self._ids_bloque[self.combo_bloque.current()]
        if hasattr(self, "_ids_combo") and self.combo_stmt["values"]:
            p["statementId"] = self._ids_combo[self.combo_stmt.current()]
        if self.tipo_de_bloque(p["bloqueId"]) == "test":
            p["statementId"] = None
        # Vínculos con partes del enunciado (modo foco): solo se conservan
        # mientras la pregunta siga colgando de ese enunciado.
        if not p["statementId"]:
            p["factIds"] = []
        else:
            propios = next((set(h["id"] for h in e["factBlocks"])
                            for e in self.datos["enunciados"]
                            if e["id"] == p["statementId"]), set())
            p["factIds"] = [x for x in p.get("factIds", []) if x in propios]

    def anadir_pregunta(self, cuantas=1, respuestas=None):
        self.volcar_pregunta()
        # Las nuevas heredan el bloque y el enunciado de la pregunta seleccionada
        anterior = self.pregunta_actual()
        if anterior:
            bid = anterior["bloqueId"]
            sid = anterior["statementId"]
        else:
            bid = self.datos["bloques"][0]["id"]
            sid = self.datos["enunciados"][0]["id"] if self.datos["enunciados"] else None
        if self.tipo_de_bloque(bid) == "test":
            sid = None
        destino = (self.i_preg + 1) if self.i_preg is not None else len(self.datos["preguntas"])
        nuevas = operaciones.preguntas_nuevas(sid, bid, cuantas, respuestas)
        self.datos["preguntas"][destino:destino] = nuevas
        self.ordenar_preguntas_por_bloque()
        # Tras ordenar por bloque pueden no estar donde se insertaron: se buscan.
        donde = [i for i, p in enumerate(self.datos["preguntas"]) if any(p is n for n in nuevas)]
        self.refrescar_lista_preg(donde[0], marcadas=donde if len(donde) > 1 else None)
        self.refrescar_lista_sec(self.i_sec)
        self.cuaderno.select(3)
        self.txt_preg_q.focus_set()
        self._tocado()
        if len(nuevas) == 1:
            self.estado("Pregunta nº %d añadida al bloque %s." % (donde[0] + 1, bid))
        else:
            self.estado("%d preguntas (nº %d a %d) añadidas al bloque %s, con %d respuestas cada una."
                        % (len(nuevas), donde[0] + 1, donde[-1] + 1, bid, len(nuevas[0]["a"])))

    def crear_varias_preguntas(self):
        try:
            cuantas = int(self.var_crear_cuantas.get())
            respuestas = int(self.var_crear_respuestas.get())
        except ValueError:
            self.estado("Escribe números en «Crear … preguntas con … respuestas».")
            return
        if not 1 <= cuantas <= operaciones.MAX_CREAR:
            self.estado("Se pueden crear de 1 a %d preguntas de una vez." % operaciones.MAX_CREAR)
            return
        if not MIN_OPCIONES <= respuestas <= MAX_OPCIONES:
            self.estado("Una pregunta lleva de %d a %d respuestas." % (MIN_OPCIONES, MAX_OPCIONES))
            return
        self.anadir_pregunta(cuantas, respuestas)

    def duplicar_pregunta(self):
        marcadas = self.preguntas_marcadas()
        if not marcadas:
            return
        self.volcar_pregunta()
        copias = operaciones.duplicar_varias(self.datos["preguntas"], marcadas)
        self.refrescar_lista_preg(copias[0], marcadas=copias)
        self.refrescar_lista_sec(self.i_sec)
        self._tocado()
        if len(copias) > 1:
            self.estado("%d preguntas duplicadas." % len(copias))

    def borrar_pregunta(self):
        marcadas = self.preguntas_marcadas()
        if not marcadas:
            return
        if len(marcadas) == 1:
            p = self.datos["preguntas"][marcadas[0]]
            pregunta = "¿Borrar la pregunta nº %d?\n\n%s" % (marcadas[0] + 1, resumen(p["q"], 70))
        else:
            pregunta = "¿Borrar las %d preguntas marcadas (%s)?" % (
                len(marcadas), ", ".join(str(i + 1) for i in marcadas[:12]) + ("…" if len(marcadas) > 12 else ""))
        if not messagebox.askyesno("Borrar", pregunta + "\n\n(Se puede deshacer con Ctrl+Z fuera de los cuadros de texto.)",
                                   parent=self):
            return
        self.volcar_pregunta()
        operaciones.borrar_varias(self.datos["preguntas"], marcadas)
        self.i_preg = None
        self.refrescar_lista_preg(max(0, marcadas[0] - 1))
        self.refrescar_lista_sec(self.i_sec)
        self._tocado()

    def mover_pregunta(self, paso):
        """Mueve la pregunta (o las marcadas) dentro de SU bloque. Para cambiarla de
        bloque se usa el desplegable «Bloque»."""
        marcadas = self.preguntas_marcadas()
        if not marcadas:
            return
        self.volcar_pregunta()
        actual = self.i_preg
        nuevos = operaciones.mover_varias(self.datos["preguntas"], marcadas, paso)
        if nuevos is None:
            self.estado("Ya está en el borde de su bloque. Para cambiarla de bloque usa el "
                        "desplegable «Bloque».")
            return
        foco = actual + paso if actual in marcadas else nuevos[0]
        self.refrescar_lista_preg(foco, marcadas=nuevos)
        self._tocado()

# -*- coding: utf-8 -*-
"""
PESTAÑA 3 · ENUNCIADOS (hechos y línea de tiempo)
═════════════════════════════════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
from editor_comun import *  # noqa: F401,F403


class PestanaEnunciados:

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 3 — ENUNCIADOS (bloques de hechos + línea de tiempo)
    # ═════════════════════════════════════════════════════════════
    def _pestana_enunciados(self):
        panel = ttk.Frame(self.cuaderno)
        self.cuaderno.add(panel, text="  3 · Enunciados y hechos  ")

        divisor = ttk.PanedWindow(panel, orient="horizontal")
        divisor.pack(fill="both", expand=True, padx=8, pady=8)

        # ---------- columna izquierda: lista de enunciados ----------
        izq = ttk.Frame(divisor, width=300)
        izq.pack_propagate(False)
        divisor.add(izq, weight=0)

        ttk.Label(izq, text="Enunciados del supuesto", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(izq, style="Tec.TLabel",
                  text='enunciados[]  →  <section class="statement">').pack(anchor="w")
        ttk.Label(izq, style="Ayuda.TLabel", wraplength=280, justify="left",
                  text="Cada enunciado es el bloque de hechos común a un grupo de preguntas. "
                       "Si el supuesto no tiene caso práctico, deja la lista vacía."
                  ).pack(anchor="w", pady=(0, 6))

        self.lst_enun = tk.Listbox(izq, font=("Consolas", 9), height=12,
                                   activestyle="none", exportselection=False)
        self.lst_enun.pack(fill="both", expand=True)
        self.lst_enun.bind("<<ListboxSelect>>", self._sel_enunciado)

        bot = ttk.Frame(izq)
        bot.pack(fill="x", pady=6)
        ttk.Button(bot, text="＋ Añadir", command=self.anadir_enunciado,
                   style="Accion.TButton", width=10).grid(row=0, column=0, padx=1, pady=1)
        ttk.Button(bot, text="⧉ Duplicar", command=self.duplicar_enunciado,
                   width=10).grid(row=0, column=1, padx=1, pady=1)
        ttk.Button(bot, text="🗑 Borrar", command=self.borrar_enunciado,
                   width=10).grid(row=0, column=2, padx=1, pady=1)
        ttk.Button(bot, text="▲ Subir", command=lambda: self.mover_enunciado(-1),
                   width=10).grid(row=1, column=0, padx=1, pady=1)
        ttk.Button(bot, text="▼ Bajar", command=lambda: self.mover_enunciado(1),
                   width=10).grid(row=1, column=1, padx=1, pady=1)

        # ---------- columna derecha: editor del enunciado ----------
        cont = MarcoScroll(divisor)
        divisor.add(cont, weight=1)
        m = cont.interior

        self.w_enun = {}
        caja = ttk.LabelFrame(m, text=" Datos del enunciado ")
        caja.pack(fill="x", padx=10, pady=(8, 6))
        for clave, visible, tecnico, html, ayuda in CAMPOS_ENUNCIADO:
            rotulo(caja, visible, tecnico, html, ayuda).pack(anchor="w", padx=10, pady=(8, 2))
            var = tk.StringVar()
            ent = ttk.Entry(caja, textvariable=var, font=("Georgia", 10))
            ent.pack(fill="x", padx=10, pady=(0, 2))
            self._vigilar(ent)
            self.w_enun[clave] = var
        ttk.Frame(caja, height=8).pack()

        interno = ttk.Notebook(m)
        interno.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        # ---------- bloques de hechos ----------
        pb = ttk.Frame(interno)
        interno.add(pb, text="  Bloques de hechos  ")

        ttk.Label(pb, style="Tec.TLabel",
                  text='enunciados[].factBlocks[]  →  <div class="fact-block">'
                  ).pack(anchor="w", padx=8, pady=(8, 0))
        ttk.Label(pb, style="Ayuda.TLabel", wraplength=780, justify="left",
                  text="Trozos de narración de los hechos, en el orden en que se leen. "
                       "Marca «hecho desencadenante» el bloque crítico: sale con borde rojo y ⚠️. "
                       "Cada bloque lleva delante su código (H1, H2…): es el que se usa en la "
                       "pestaña «4 · Preguntas» para vincular una pregunta a este hecho concreto "
                       "y que el modo foco recorte el enunciado a esta parte."
                  ).pack(anchor="w", padx=8)

        fila = ttk.Frame(pb)
        fila.pack(fill="x", padx=8, pady=6)
        self.lst_bloques = tk.Listbox(fila, font=("Consolas", 9), height=5,
                                      activestyle="none", exportselection=False)
        self.lst_bloques.pack(side="left", fill="both", expand=True)
        self.lst_bloques.bind("<<ListboxSelect>>", self._sel_bloque)
        colb = ttk.Frame(fila)
        colb.pack(side="left", padx=(6, 0))
        ttk.Button(colb, text="＋ Añadir", width=11, style="Accion.TButton",
                   command=self.anadir_bloque).pack(pady=1)
        ttk.Button(colb, text="🗑 Borrar", width=11, command=self.borrar_bloque).pack(pady=1)
        ttk.Button(colb, text="▲ Subir", width=11, command=lambda: self.mover_bloque(-1)).pack(pady=1)
        ttk.Button(colb, text="▼ Bajar", width=11, command=lambda: self.mover_bloque(1)).pack(pady=1)

        rotulo(pb, "Título del bloque de hechos", "factBlocks[].title",
               '<div class="fact-title">',
               "Sale en negrita con el icono 📋 (o ⚠️ si el bloque es el hecho desencadenante)."
               ).pack(anchor="w", padx=8, pady=(6, 2))
        self.var_bloque_titulo = tk.StringVar()
        ent = ttk.Entry(pb, textvariable=self.var_bloque_titulo, font=("Georgia", 10))
        ent.pack(fill="x", padx=8)
        self._vigilar(ent)

        rotulo(pb, "Narración de los hechos", "factBlocks[].paragraphs[]",
               '<div class="fact-block"> → <p>',
               "Cada vez que pulsas ENTER empieza un párrafo nuevo en la página (la línea en blanco "
               "entre párrafos es opcional). Con los botones de arriba (o con Ctrl+B, Ctrl+I, "
               "Ctrl+U, Ctrl+T y Ctrl+R) se pone en negrita, cursiva, subrayado, tachado, "
               "resaltado y otro tamaño de letra lo que esté seleccionado; el formato se ve directamente "
               "(las marcas <b>…</b> están ocultas: el botón ‹› o Ctrl+Mayús+M las enseña). "
               "El texto sale JUSTIFICADO por defecto en la página; «Izq.» (Ctrl+L) deja a la "
               "izquierda el párrafo donde esté el cursor o los seleccionados y «Just.» (Ctrl+J) "
               "lo vuelve a justificar. «Sang+» (tecla Tab) mete "
               "el párrafo más hacia dentro que el anterior, hasta tres niveles, y «Sang-» "
               "(Mayús+Tab) lo saca. El menú «Fuente» cambia la tipografía de lo seleccionado. "
               "El cuadro crece solo al escribir; arrastra la franja de abajo para ampliarlo o "
               "pulsa ⤢ (Ctrl+Mayús+E) para escribir en una ventana grande. "
               "Las tipografías se ven aquí de forma aproximada."
               ).pack(anchor="w", padx=8, pady=(8, 2))
        marco, self.txt_bloque_parr = caja_texto(pb, alto=9)
        marco.pack(fill="both", expand=True, padx=8)
        self._vigilar(self.txt_bloque_parr)

        filac = ttk.Frame(pb)
        filac.pack(fill="x", padx=8, pady=8)
        self.var_bloque_red = tk.BooleanVar()
        self.var_bloque_hidden = tk.BooleanVar()
        ttk.Checkbutton(filac, variable=self.var_bloque_red, command=self._tocado,
                        text="Hecho desencadenante  ·  factBlocks[].red  →  "
                             'class="fact-block red"  (borde rojo y ⚠️)').pack(anchor="w")
        ttk.Checkbutton(filac, variable=self.var_bloque_hidden, command=self._tocado,
                        text="No mostrar este bloque  ·  factBlocks[].hidden  →  "
                             "(se guarda en el archivo pero la página no lo pinta)").pack(anchor="w")
        self.lbl_bloque_vinculos = ttk.Label(filac, text="", style="Tec.TLabel")
        self.lbl_bloque_vinculos.pack(anchor="w", pady=(6, 0))

        # ---------- línea de tiempo ----------
        pt = ttk.Frame(interno)
        interno.add(pt, text="  Línea de tiempo  ")

        ttk.Label(pt, style="Tec.TLabel",
                  text='enunciados[].timeline[]  →  <div class="timeline"> → <div class="tl-item">'
                  ).pack(anchor="w", padx=8, pady=(8, 0))
        ttk.Label(pt, style="Ayuda.TLabel", wraplength=780, justify="left",
                  text="Hitos con fecha que se pintan como cronología bajo los hechos. "
                       "Si el supuesto no lleva cronología, deja la lista vacía."
                  ).pack(anchor="w", padx=8)

        fila = ttk.Frame(pt)
        fila.pack(fill="x", padx=8, pady=6)
        self.lst_hitos = tk.Listbox(fila, font=("Consolas", 9), height=8,
                                    activestyle="none", exportselection=False)
        self.lst_hitos.pack(side="left", fill="both", expand=True)
        self.lst_hitos.bind("<<ListboxSelect>>", self._sel_hito)
        colt = ttk.Frame(fila)
        colt.pack(side="left", padx=(6, 0))
        ttk.Button(colt, text="＋ Añadir", width=11, style="Accion.TButton",
                   command=self.anadir_hito).pack(pady=1)
        ttk.Button(colt, text="🗑 Borrar", width=11, command=self.borrar_hito).pack(pady=1)
        ttk.Button(colt, text="▲ Subir", width=11, command=lambda: self.mover_hito(-1)).pack(pady=1)
        ttk.Button(colt, text="▼ Bajar", width=11, command=lambda: self.mover_hito(1)).pack(pady=1)

        rotulo(pt, "Fecha del hito", "timeline[].date", '<span class="tl-date">',
               "Recuadro de la izquierda del hito (por ejemplo: 14/03/2025)."
               ).pack(anchor="w", padx=8, pady=(6, 2))
        self.var_hito_fecha = tk.StringVar()
        ent = ttk.Entry(pt, textvariable=self.var_hito_fecha, font=("Consolas", 10), width=24)
        ent.pack(anchor="w", padx=8)
        self._vigilar(ent)

        rotulo(pt, "Texto del hito", "timeline[].text", '<div class="tl-item">',
               "Qué ocurrió en esa fecha.").pack(anchor="w", padx=8, pady=(8, 2))
        marco, self.txt_hito_texto = caja_texto(pt, alto=4)
        marco.pack(fill="x", padx=8)
        self._vigilar(self.txt_hito_texto)

        filac = ttk.Frame(pt)
        filac.pack(fill="x", padx=8, pady=8)
        self.var_hito_red = tk.BooleanVar()
        self.var_hito_hidden = tk.BooleanVar()
        ttk.Checkbutton(filac, variable=self.var_hito_red, command=self._tocado,
                        text="Hito crítico  ·  timeline[].red  →  "
                             'class="tl-item red-event"  (se resalta en rojo)').pack(anchor="w")
        ttk.Checkbutton(filac, variable=self.var_hito_hidden, command=self._tocado,
                        text="No mostrar este hito  ·  timeline[].hidden").pack(anchor="w")

    # ---------- lista de enunciados ----------
    def refrescar_lista_enun(self, seleccionar=None):
        self._silencio = True
        self.lst_enun.delete(0, "end")
        for e in self.datos["enunciados"]:
            self.lst_enun.insert("end", "%-4s %s" % (e["id"], resumen(e["title"], 30)))
        if seleccionar is None:
            seleccionar = self.i_enun
        if self.datos["enunciados"]:
            if seleccionar is None or seleccionar >= len(self.datos["enunciados"]):
                seleccionar = 0
            self.lst_enun.selection_clear(0, "end")
            self.lst_enun.selection_set(seleccionar)
            self.lst_enun.see(seleccionar)
        else:
            seleccionar = None
        self._silencio = False
        self.i_enun = seleccionar
        self.cargar_enunciado()
        self.refrescar_combo_enunciados()
        self._pintar_titulo()

    def _sel_enunciado(self, _e=None):
        if self._silencio:
            return
        sel = self.lst_enun.curselection()
        if not sel or sel[0] == self.i_enun:
            return
        self.volcar_enunciado()
        self.i_enun = sel[0]
        self.i_bloque = None
        self.i_hito = None
        self.cargar_enunciado()

    def enunciado_actual(self):
        if self.i_enun is None or self.i_enun >= len(self.datos["enunciados"]):
            return None
        return self.datos["enunciados"][self.i_enun]

    def cargar_enunciado(self):
        e = self.enunciado_actual()
        for clave, *_ in CAMPOS_ENUNCIADO:
            self.w_enun[clave].set("" if e is None else str(e.get(clave, "")))
        self.refrescar_lista_bloques()
        self.refrescar_lista_hitos()

    def volcar_enunciado(self):
        e = self.enunciado_actual()
        if e is None:
            return
        for clave, *_ in CAMPOS_ENUNCIADO:
            e[clave] = self.w_enun[clave].get().strip()
        self.volcar_bloque()
        self.volcar_hito()

    def anadir_enunciado(self):
        self.volcar_enunciado()
        usados = {e["id"] for e in self.datos["enunciados"]}
        n = 1
        while ("E%d" % n) in usados:
            n += 1
        self.datos["enunciados"].append(enunciado_vacio("E%d" % n))
        self.i_bloque = self.i_hito = None
        self.refrescar_lista_enun(len(self.datos["enunciados"]) - 1)
        self._tocado()
        self.estado("Enunciado E%d añadido." % n)

    def duplicar_enunciado(self):
        e = self.enunciado_actual()
        if e is None:
            return
        self.volcar_enunciado()
        copia = json.loads(json.dumps(e))
        usados = {x["id"] for x in self.datos["enunciados"]}
        n = 1
        while ("E%d" % n) in usados:
            n += 1
        copia["id"] = "E%d" % n
        self.datos["enunciados"].insert(self.i_enun + 1, copia)
        self.i_bloque = self.i_hito = None
        self.refrescar_lista_enun(self.i_enun + 1)
        self._tocado()

    def borrar_enunciado(self):
        e = self.enunciado_actual()
        if e is None:
            return
        enganchadas = [i + 1 for i, p in enumerate(self.datos["preguntas"])
                       if p["statementId"] == e["id"]]
        aviso = "¿Borrar el enunciado «%s»?" % resumen(e["title"], 40)
        if enganchadas:
            aviso += ("\n\nATENCIÓN: las preguntas nº %s están enganchadas a este enunciado y "
                      "se quedarán como preguntas sueltas (sin hechos)."
                      % ", ".join(str(x) for x in enganchadas))
        if not messagebox.askyesno("Borrar enunciado", aviso, parent=self):
            return
        self.volcar_pregunta()
        for p in self.datos["preguntas"]:
            if p["statementId"] == e["id"]:
                p["statementId"] = None
        del self.datos["enunciados"][self.i_enun]
        self.i_bloque = self.i_hito = None
        self.refrescar_lista_enun(max(0, self.i_enun - 1))
        self.refrescar_lista_preg()
        self._tocado()

    def mover_enunciado(self, paso):
        if self.i_enun is None:
            return
        destino = self.i_enun + paso
        lista = self.datos["enunciados"]
        if destino < 0 or destino >= len(lista):
            return
        self.volcar_enunciado()
        lista[self.i_enun], lista[destino] = lista[destino], lista[self.i_enun]
        self.refrescar_lista_enun(destino)
        self._tocado()

    # ---------- bloques de hechos ----------
    def refrescar_lista_bloques(self, seleccionar=None):
        self._silencio = True
        self.lst_bloques.delete(0, "end")
        e = self.enunciado_actual()
        bloques = e["factBlocks"] if e else []
        for b in bloques:
            marca = "⚠ " if b["red"] else "📋 "
            if b["hidden"]:
                marca = "👁 "
            self.lst_bloques.insert("end", "%-4s %s%s" % (b.get("id", ""), marca,
                                                          resumen(b["title"], 40)))
        if seleccionar is None:
            seleccionar = self.i_bloque
        if bloques:
            if seleccionar is None or seleccionar >= len(bloques):
                seleccionar = 0
            self.lst_bloques.selection_clear(0, "end")
            self.lst_bloques.selection_set(seleccionar)
            self.lst_bloques.see(seleccionar)
        else:
            seleccionar = None
        self._silencio = False
        self.i_bloque = seleccionar
        self.cargar_bloque()

    def _sel_bloque(self, _e=None):
        if self._silencio:
            return
        sel = self.lst_bloques.curselection()
        if not sel or sel[0] == self.i_bloque:
            return
        self.volcar_bloque()
        self.i_bloque = sel[0]
        self.cargar_bloque()

    def bloque_actual(self):
        e = self.enunciado_actual()
        if e is None or self.i_bloque is None or self.i_bloque >= len(e["factBlocks"]):
            return None
        return e["factBlocks"][self.i_bloque]

    def cargar_bloque(self):
        b = self.bloque_actual()
        self.var_bloque_titulo.set("" if b is None else b["title"])
        poner_texto(self.txt_bloque_parr, "" if b is None else "\n\n".join(b["paragraphs"]))
        self.var_bloque_red.set(bool(b and b["red"]))
        self.var_bloque_hidden.set(bool(b and b["hidden"]))
        self._pintar_vinculos_bloque()

    def _pintar_vinculos_bloque(self):
        """Cuántas preguntas se apoyan en este hecho concreto (modo foco)."""
        if not hasattr(self, "lbl_bloque_vinculos"):
            return
        e = self.enunciado_actual()
        b = self.bloque_actual()
        if e is None or b is None:
            self.lbl_bloque_vinculos.config(text="")
            return
        cuantas = sum(1 for q in self.datos["preguntas"]
                      if q["statementId"] == e["id"] and b["id"] in q.get("factIds", []))
        self.lbl_bloque_vinculos.config(
            text="factBlocks[].id = %s   ·   %s (modo foco; se vincula en la pestaña "
                 "«4 · Preguntas»)"
                 % (b["id"], "sin preguntas vinculadas" if not cuantas
                    else "%d pregunta(s) vinculada(s)" % cuantas))

    def volcar_bloque(self):
        b = self.bloque_actual()
        if b is None:
            return
        if not b.get("id"):
            b["id"] = nuevo_id_hecho(self.enunciado_actual() or {})
        b["title"] = self.var_bloque_titulo.get().strip()
        crudo = sacar_texto(self.txt_bloque_parr)
        b["paragraphs"] = partir_parrafos(crudo)
        b["red"] = bool(self.var_bloque_red.get())
        b["hidden"] = bool(self.var_bloque_hidden.get())

    def anadir_bloque(self):
        e = self.enunciado_actual()
        if e is None:
            messagebox.showinfo("Sin enunciado", "Primero añade un enunciado.", parent=self)
            return
        self.volcar_bloque()
        e["factBlocks"].append(bloque_hechos_vacio(nuevo_id_hecho(e)))
        self.refrescar_lista_bloques(len(e["factBlocks"]) - 1)
        self._tocado()

    def borrar_bloque(self):
        e = self.enunciado_actual()
        b = self.bloque_actual()
        if b is None:
            return
        vinculadas = [q for q in self.datos["preguntas"]
                      if q["statementId"] == e["id"] and b["id"] in q.get("factIds", [])]
        aviso = ("" if not vinculadas else
                 "\n\n%d pregunta(s) están vinculadas a este hecho para el modo foco: "
                 "perderán el vínculo y volverán a mostrar el enunciado entero."
                 % len(vinculadas))
        if not messagebox.askyesno("Borrar bloque",
                                   "¿Borrar el bloque «%s»?%s"
                                   % (resumen(b["title"], 40), aviso),
                                   parent=self):
            return
        for q in vinculadas:
            q["factIds"] = [x for x in q["factIds"] if x != b["id"]]
        del e["factBlocks"][self.i_bloque]
        self.refrescar_lista_bloques(max(0, self.i_bloque - 1))
        if hasattr(self, "lst_factlink"):
            self.refrescar_lista_factlink()
        self._tocado()

    def mover_bloque(self, paso):
        e = self.enunciado_actual()
        if e is None or self.i_bloque is None:
            return
        destino = self.i_bloque + paso
        if destino < 0 or destino >= len(e["factBlocks"]):
            return
        self.volcar_bloque()
        e["factBlocks"][self.i_bloque], e["factBlocks"][destino] = \
            e["factBlocks"][destino], e["factBlocks"][self.i_bloque]
        self.refrescar_lista_bloques(destino)
        self._tocado()

    # ---------- hitos de la línea de tiempo ----------
    def refrescar_lista_hitos(self, seleccionar=None):
        self._silencio = True
        self.lst_hitos.delete(0, "end")
        e = self.enunciado_actual()
        hitos = e["timeline"] if e else []
        for h in hitos:
            marca = "🔴 " if h["red"] else "• "
            if h["hidden"]:
                marca = "👁 "
            self.lst_hitos.insert("end", "%s%-12s %s" % (marca, h["date"], resumen(h["text"], 40)))
        if seleccionar is None:
            seleccionar = self.i_hito
        if hitos:
            if seleccionar is None or seleccionar >= len(hitos):
                seleccionar = 0
            self.lst_hitos.selection_clear(0, "end")
            self.lst_hitos.selection_set(seleccionar)
            self.lst_hitos.see(seleccionar)
        else:
            seleccionar = None
        self._silencio = False
        self.i_hito = seleccionar
        self.cargar_hito()

    def _sel_hito(self, _e=None):
        if self._silencio:
            return
        sel = self.lst_hitos.curselection()
        if not sel or sel[0] == self.i_hito:
            return
        self.volcar_hito()
        self.i_hito = sel[0]
        self.cargar_hito()

    def hito_actual(self):
        e = self.enunciado_actual()
        if e is None or self.i_hito is None or self.i_hito >= len(e["timeline"]):
            return None
        return e["timeline"][self.i_hito]

    def cargar_hito(self):
        h = self.hito_actual()
        self.var_hito_fecha.set("" if h is None else h["date"])
        poner_texto(self.txt_hito_texto, "" if h is None else h["text"])
        self.var_hito_red.set(bool(h and h["red"]))
        self.var_hito_hidden.set(bool(h and h["hidden"]))

    def volcar_hito(self):
        h = self.hito_actual()
        if h is None:
            return
        h["date"] = self.var_hito_fecha.get().strip()
        h["text"] = limpiar_texto(sacar_texto(self.txt_hito_texto))
        h["red"] = bool(self.var_hito_red.get())
        h["hidden"] = bool(self.var_hito_hidden.get())

    def anadir_hito(self):
        e = self.enunciado_actual()
        if e is None:
            messagebox.showinfo("Sin enunciado", "Primero añade un enunciado.", parent=self)
            return
        self.volcar_hito()
        e["timeline"].append(hito_vacio())
        self.refrescar_lista_hitos(len(e["timeline"]) - 1)
        self._tocado()

    def borrar_hito(self):
        e = self.enunciado_actual()
        h = self.hito_actual()
        if h is None:
            return
        if not messagebox.askyesno("Borrar hito",
                                   "¿Borrar el hito «%s»?" % resumen(h["text"], 40), parent=self):
            return
        del e["timeline"][self.i_hito]
        self.refrescar_lista_hitos(max(0, self.i_hito - 1))
        self._tocado()

    def mover_hito(self, paso):
        e = self.enunciado_actual()
        if e is None or self.i_hito is None:
            return
        destino = self.i_hito + paso
        if destino < 0 or destino >= len(e["timeline"]):
            return
        self.volcar_hito()
        e["timeline"][self.i_hito], e["timeline"][destino] = \
            e["timeline"][destino], e["timeline"][self.i_hito]
        self.refrescar_lista_hitos(destino)
        self._tocado()

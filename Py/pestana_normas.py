# -*- coding: utf-8 -*-
"""
PESTAÑA 7 · NORMAS (ENLACES AL BOE)
═══════════════════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
from editor_comun import *  # noqa: F401,F403


class PestanaNormas:

    # ─────────────────────────────────────────────────────────────
    #  Pestaña 7 · Normas (enlaces al BOE)
    # ─────────────────────────────────────────────────────────────
    def _pestana_normas(self):
        panel = ttk.Frame(self.cuaderno)
        self.cuaderno.add(panel, text="  7 · Normas (enlaces BOE)  ")
        self._normas_cabecera, self._normas = normas_enlaces.leer()
        self._normas_sucio = False
        self._norma_sel = None

        ttk.Label(panel, style="Ayuda.TLabel", wraplength=1000, justify="left",
                  text="Cuando la motivación legal de una respuesta dice «artículo 15.1 … RD 84/1996», la "
                       "página lo convierte en un enlace al BOE. Aquí se apuntan las normas que se enlazan: "
                       "cada una con todos los «apodos» con que la citas (separados por comas) y su "
                       "dirección del BOE. Regla de la cita: «art.» o «artículo», un número y, a menos de "
                       "45 caracteres, uno de los apodos."
                  ).pack(anchor="w", padx=10, pady=(10, 6))

        cuerpo = ttk.Frame(panel)
        cuerpo.pack(fill="both", expand=True, padx=10)
        self.arbol_normas = ttk.Treeview(cuerpo, columns=("siglas", "boe", "nota"), show="headings",
                                         selectmode="browse", height=12)
        for col, texto, ancho in (("siglas", "Apodos", 330), ("boe", "BOE", 140), ("nota", "Nota", 420)):
            self.arbol_normas.heading(col, text=texto)
            self.arbol_normas.column(col, width=ancho, anchor="w")
        barra = ttk.Scrollbar(cuerpo, orient="vertical", command=self.arbol_normas.yview)
        self.arbol_normas.configure(yscrollcommand=barra.set)
        self.arbol_normas.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        self.arbol_normas.bind("<<TreeviewSelect>>", lambda e: self._norma_elegida())

        form = ttk.Frame(panel)
        form.pack(fill="x", padx=10, pady=(10, 0))
        self.var_norma_siglas = tk.StringVar()
        self.var_norma_boe = tk.StringVar()
        self.var_norma_nota = tk.StringVar()
        for i, (et, var) in enumerate((
                ("Apodos (separados por comas):", self.var_norma_siglas),
                ("Dirección del BOE o «BOE-A-…»:", self.var_norma_boe),
                ("Nota (solo para reconocerla):", self.var_norma_nota))):
            ttk.Label(form, text=et).grid(row=i, column=0, sticky="w", pady=3)
            ttk.Entry(form, textvariable=var, width=90).grid(row=i, column=1, sticky="we", padx=(8, 0), pady=3)
        form.columnconfigure(1, weight=1)

        botones = ttk.Frame(panel)
        botones.pack(fill="x", padx=10, pady=8)
        ttk.Button(botones, text="➕ Añadir / actualizar", command=self._norma_guardar_fila,
                   style="Accion.TButton").pack(side="left")
        ttk.Button(botones, text="Nueva (vaciar cuadros)", command=self._norma_nueva).pack(side="left", padx=6)
        ttk.Button(botones, text="✖ Quitar de la lista", command=self._norma_quitar).pack(side="left")
        ttk.Button(botones, text="🌐 Abrir en el BOE", command=self._norma_abrir).pack(side="left", padx=6)
        ttk.Button(botones, text="↻ Recargar del archivo", command=self._norma_recargar).pack(side="right")
        ttk.Button(botones, text="💾 Guardar normas", command=self._norma_guardar_archivo,
                   style="Accion.TButton").pack(side="right", padx=6)
        self.lbl_normas = ttk.Label(panel, style="Ayuda.TLabel", text="")
        self.lbl_normas.pack(anchor="w", padx=10, pady=(0, 8))
        self._norma_pintar()

    def _norma_pintar(self, seleccionar=None):
        self.arbol_normas.delete(*self.arbol_normas.get_children())
        for i, n in enumerate(self._normas):
            self.arbol_normas.insert("", "end", iid=str(i),
                                     values=(", ".join(n["siglas"]), n["boe"], n.get("nota", "")))
        if seleccionar is not None and self.arbol_normas.exists(str(seleccionar)):
            self.arbol_normas.selection_set(str(seleccionar))
        estado = "SIN GUARDAR · " if self._normas_sucio else ""
        self.lbl_normas.config(text="%s%d norma(s) · archivo: %s" % (estado, len(self._normas), normas_enlaces.ARCHIVO))

    def _norma_elegida(self):
        sel = self.arbol_normas.selection()
        if not sel:
            return
        self._norma_sel = int(sel[0])
        n = self._normas[self._norma_sel]
        self.var_norma_siglas.set(", ".join(n["siglas"]))
        self.var_norma_boe.set(n["boe"])
        self.var_norma_nota.set(n.get("nota", ""))

    def _norma_nueva(self):
        self._norma_sel = None
        self.arbol_normas.selection_remove(*self.arbol_normas.selection())
        for v in (self.var_norma_siglas, self.var_norma_boe, self.var_norma_nota):
            v.set("")

    def _norma_guardar_fila(self):
        siglas = normas_enlaces.partir_siglas(self.var_norma_siglas.get())
        boe = normas_enlaces.extraer_boe(self.var_norma_boe.get())
        if not siglas:
            messagebox.showwarning("Normas", "Escribe al menos un apodo (p. ej. RD 84/1996).", parent=self)
            return
        if not boe:
            messagebox.showwarning("Normas", "No encuentro un código «BOE-A-…» en lo que has pegado.\n"
                                   "Pega la dirección de la norma en boe.es o el código.", parent=self)
            return
        usados = {}
        for i, n in enumerate(self._normas):
            if i != self._norma_sel:
                for sg in n["siglas"]:
                    usados[sg.lower()] = i
        repetidos = [sg for sg in siglas if sg.lower() in usados]
        if repetidos:
            messagebox.showwarning("Normas", "Estos apodos ya los usa otra norma: %s" % ", ".join(repetidos), parent=self)
            return
        ficha = {"siglas": siglas, "boe": boe, "nota": self.var_norma_nota.get().strip()}
        if self._norma_sel is None:
            self._normas.append(ficha)
            self._norma_sel = len(self._normas) - 1
        else:
            self._normas[self._norma_sel] = ficha
        self._normas_sucio = True
        self.var_norma_boe.set(boe)
        self._norma_pintar(self._norma_sel)

    def _norma_quitar(self):
        if self._norma_sel is None or self._norma_sel >= len(self._normas):
            return
        n = self._normas[self._norma_sel]
        if messagebox.askyesno("Normas", "¿Quito «%s» de la lista?" % ", ".join(n["siglas"]), parent=self):
            self._normas.pop(self._norma_sel)
            self._normas_sucio = True
            self._norma_nueva()
            self._norma_pintar()

    def _norma_abrir(self):
        boe = normas_enlaces.extraer_boe(self.var_norma_boe.get())
        if boe:
            webbrowser.open("https://www.boe.es/buscar/act.php?id=" + boe)

    def _norma_recargar(self):
        if self._normas_sucio and not messagebox.askyesno(
                "Normas", "Hay cambios sin guardar. ¿Los descarto y recargo el archivo?", parent=self):
            return
        self._normas_cabecera, self._normas = normas_enlaces.leer()
        self._normas_sucio = False
        self._norma_nueva()
        self._norma_pintar()

    def _norma_guardar_archivo(self):
        try:
            normas_enlaces.escribir(self._normas, self._normas_cabecera)
        except OSError as e:
            messagebox.showerror("Normas", "No se pudo guardar:\n\n%s" % e, parent=self)
            return
        self._normas_sucio = False
        self._norma_pintar(self._norma_sel)
        res = sincronizar_local.refrescar_silencioso(normas_enlaces.ARCHIVO)
        self.estado("Normas guardadas en datos/normas-datos.js"
                    + (" · " + sincronizar_local.resumen(*res) if res else ""))

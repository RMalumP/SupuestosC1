# -*- coding: utf-8 -*-
"""
VENTANA «MENÚ DE INICIO»  (parte del editor; la lógica está en menu_datos.py)
═══════════════════════════════════════════════════════════════════════════
Edita la lista del menú principal (supuestos-datos.js): ordenar, mover de sección
o grupo, cambiar títulos, ocultar, quitar, añadir supuestos que falten y crear
secciones o grupos nuevos. Nada se escribe hasta pulsar «Guardar».
"""
import copy
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

import datos_html
import menu_datos as md
import sincronizar_local as sl


def abrir(app):
    raiz = sl.raiz_de(app.ruta) if getattr(app, "ruta", None) else None
    raiz = raiz or (sl.RAIZ_DEFECTO if sl.es_proyecto(sl.RAIZ_DEFECTO) else None)
    if raiz is None:
        messagebox.showinfo("Menú de inicio", "No encuentro el proyecto (la carpeta con index.html y «supuestos»).", parent=app)
        return
    ruta_menu = raiz / md.ARCHIVO_MENU
    try:
        texto, menu = md.leer_archivo(ruta_menu)
    except (OSError, ValueError) as e:
        messagebox.showerror("Menú de inicio", "No puedo leer %s:\n\n%s" % (md.ARCHIVO_MENU, e), parent=app)
        return
    Ventana(app, raiz, ruta_menu, texto, menu)


class Ventana:
    def __init__(self, app, raiz, ruta_menu, texto, menu):
        self.app, self.raiz, self.ruta_menu, self.texto, self.menu = app, raiz, ruta_menu, texto, menu
        self.sucio = False
        self.historial = []                 # estados anteriores del menú (para «Deshacer»)
        self._base = copy.deepcopy(menu)
        v = self.v = tk.Toplevel(app)
        v.title("Menú de inicio — orden y contenido de index.html")
        v.geometry("980x720")
        v.transient(app)
        v.protocol("WM_DELETE_WINDOW", self.cerrar)

        marco = ttk.Frame(v, padding=10)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, wraplength=860, justify="left",
                  text="Así se ordena el menú de la web. Elige un supuesto, un grupo o una sección y usa los botones. "
                       "Doble clic para editar, Supr para quitar, Ctrl+Z para deshacer, Ctrl+S para guardar. "
                       "Los cambios no se guardan hasta pulsar «Guardar menú».").pack(anchor="w", pady=(0, 8))
        cuerpo = ttk.Frame(marco)
        cuerpo.pack(fill="both", expand=True)

        self.arbol = ttk.Treeview(cuerpo, columns=("ref", "estado"), selectmode="browse")
        self.arbol.heading("#0", text="Sección › grupo › supuesto")
        self.arbol.heading("ref", text="Ref.")
        self.arbol.heading("estado", text="Estado")
        self.arbol.column("#0", width=520)
        self.arbol.column("ref", width=80, anchor="center")
        self.arbol.column("estado", width=90, anchor="center")
        barra = ttk.Scrollbar(cuerpo, orient="vertical", command=self.arbol.yview)
        self.arbol.configure(yscrollcommand=barra.set)
        self.arbol.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")

        col = ttk.Frame(cuerpo, padding=(10, 0, 0, 0))
        col.pack(side="left", fill="y")
        for texto_btn, orden in (
                ("▲ Subir", lambda: self.mover(-1)), ("▼ Bajar", lambda: self.mover(1)),
                ("⤒ Al principio", lambda: self.extremo(True)), ("⤓ Al final", lambda: self.extremo(False)),
                ("↔ Mover a otro grupo…", self.mover_a), ("✎ Editar datos…", self.editar),
                ("👁 Ocultar / mostrar", self.ocultar), ("✖ Quitar del menú", self.quitar),
                ("🌐 Ver en el navegador", self.ver),
                (None, None),
                ("➕ Añadir supuesto que falta…", self.anadir),
                ("➕ Añadir todos los que faltan…", self.anadir_todos),
                ("➕ Nueva sección…", self.nueva_seccion), ("➕ Nuevo grupo…", self.nuevo_grupo),
                ("✎ Cambiar nombre de sección/grupo…", self.renombrar),
                ("🗑 Borrar sección/grupo vacío", self.borrar_contenedor),
                (None, None),
                ("🔤 Ordenar el grupo…", self.ordenar),
                ("🔎 Buscar…", self.buscar),
                ("⇕ Abrir / cerrar todo", self.plegar),
                ("↶ Deshacer", self.deshacer)):
            if texto_btn is None:
                ttk.Separator(col, orient="horizontal").pack(fill="x", pady=6)
                continue
            ttk.Button(col, text=texto_btn, command=orden).pack(fill="x", pady=1)

        self.arbol.bind("<Double-1>", self._doble_clic)
        v.bind("<Delete>", lambda e: self.quitar())
        v.bind("<Control-z>", lambda e: self.deshacer())
        v.bind("<Control-s>", lambda e: self.guardar())
        self._plegado = False
        self._ultima_busqueda = ""

        pie = ttk.Frame(marco)
        pie.pack(fill="x", pady=(10, 0))
        self.lbl = ttk.Label(pie, text="")
        self.lbl.pack(side="left")
        ttk.Button(pie, text="Cerrar", command=self.cerrar).pack(side="right")
        ttk.Button(pie, text="💾 Guardar menú", command=self.guardar, style="Accion.TButton").pack(side="right", padx=6)
        self.pintar()

    # ── árbol ──
    def pintar(self, seleccionar=None):
        sel = seleccionar or (self.arbol.selection() or [None])[0]
        self.arbol.delete(*self.arbol.get_children())
        for s in self.menu.get("secciones", []):
            sid = "s:" + s["id"]
            self.arbol.insert("", "end", iid=sid, text="■ " + s.get("titulo", s["id"]), open=True)
            for g in s.get("grupos", []):
                gid = "g:%s/%s" % (s["id"], g["id"])
                self.arbol.insert(sid, "end", iid=gid, text="▸ " + g.get("titulo", g["id"]), open=True)
                self._items(gid, g.get("items", []))
        self.arbol.insert("", "end", iid="x:examenes", text="■ Exámenes y simulacros", open=True)
        self._items("x:examenes", self.menu.get("examenes", []))
        if sel and self.arbol.exists(sel):
            self.arbol.selection_set(sel)
            self.arbol.see(sel)
        falta = md.sin_alta(self.menu, self.raiz / "supuestos")
        total, ocultos = md.contar(self.menu)
        resumen = "%d en el menú (%d ocultos). " % (total, ocultos)
        self.lbl.configure(text=resumen + (("Sin alta: %s" % ", ".join(falta)) if falta else "Todos los de la carpeta están en el menú."))

    def _items(self, padre, lista):
        for it in lista:
            self.arbol.insert(padre, "end", iid="i:" + it["archivo"], text="%s   %s" % (it.get("letra", ""), it.get("titulo", it["archivo"])),
                              values=(it.get("ref", ""), "oculto" if it.get("oculto") else ""))

    def _sel(self):
        s = self.arbol.selection()
        if not s:
            messagebox.showinfo("Menú de inicio", "Primero elige algo de la lista.", parent=self.v)
            return None, None
        return s[0][0], s[0][2:]

    def _cambio(self, sel=None):
        self.sucio = True
        if self.menu != self._base:
            self.historial.append(self._base)
            self._base = copy.deepcopy(self.menu)
        self.pintar(sel)

    def deshacer(self):
        if not self.historial:
            self.lbl.configure(text="No hay nada que deshacer.")
            return
        self.menu = self.historial.pop()
        self._base = copy.deepcopy(self.menu)
        self.sucio = True
        self.pintar()

    def _doble_clic(self, e):
        if not self.arbol.identify_row(e.y):
            return
        tipo, _ = self._sel()
        if tipo == "i":
            self.editar()
        elif tipo in ("s", "g"):
            self.renombrar()

    def _titulo_de(self, tipo, ident):
        if tipo == "s":
            return next((s.get("titulo", "") for s in self.menu["secciones"] if s["id"] == ident), "")
        sec, grp = ident.split("/", 1)
        for s in self.menu["secciones"]:
            if s["id"] == sec:
                return next((g.get("titulo", "") for g in s.get("grupos", []) if g["id"] == grp), "")
        return ""

    # ── acciones sobre supuestos ──
    def mover(self, delta):
        tipo, ident = self._sel()
        if tipo == "i":
            if md.mover(self.menu, ident, delta) or md.mover_vecino(self.menu, ident, delta):
                self._cambio("i:" + ident)
        elif tipo in "sg":
            if md.mover_contenedor(self.menu, ident, delta):
                self._cambio("%s:%s" % (tipo, ident))

    def mover_a(self):
        tipo, ident = self._sel()
        if tipo != "i":
            if tipo:
                messagebox.showinfo("Menú de inicio", "Elige un supuesto para moverlo.", parent=self.v)
            return
        clave = self._elegir_destino("¿A qué grupo lo muevo?")
        if clave and md.mover_a(self.menu, ident, clave):
            self._cambio("i:" + ident)

    def editar(self):
        tipo, ident = self._sel()
        if tipo != "i":
            if tipo:
                messagebox.showinfo("Menú de inicio", "Elige un supuesto para editar sus datos.", parent=self.v)
            return
        it = md.buscar(self.menu, ident)[1][md.buscar(self.menu, ident)[2]]
        npreg, minutos, otros = md.partir_desc(it.get("desc", ""))
        d = tk.Toplevel(self.v)
        d.title("Editar «%s»" % ident)
        d.transient(self.v)
        d.resizable(False, False)
        marco = ttk.Frame(d, padding=14)
        marco.pack()
        vars_ = {k: tk.StringVar(value=it.get(k, "")) for k in ("letra", "ref", "titulo", "desc")}
        v_preg, v_min, v_otros = tk.StringVar(value=npreg), tk.StringVar(value=minutos), tk.StringVar(value=otros)
        v_oculto = tk.BooleanVar(value=bool(it.get("oculto")))
        v_html = tk.BooleanVar(value=False)

        def fila(r, etiqueta, var, ancho=70, ayuda=""):
            ttk.Label(marco, text=etiqueta).grid(row=r, column=0, sticky="w", pady=3)
            ttk.Entry(marco, textvariable=var, width=ancho).grid(row=r, column=1, pady=3, padx=(8, 0), sticky="w")
            if ayuda:
                ttk.Label(marco, text=ayuda, foreground="#666").grid(row=r, column=2, sticky="w", padx=(8, 0))

        fila(0, "Texto del círculo (máx. 4):", vars_["letra"], 10)
        fila(1, "Referencia:", vars_["ref"], 30)
        fila(2, "Título:", vars_["titulo"])
        ttk.Separator(marco, orient="horizontal").grid(row=3, column=0, columnspan=3, sticky="we", pady=6)
        fila(4, "Nº de preguntas:", v_preg, 8, "el «15 preguntas» de la tarjeta")
        fila(5, "Minutos:", v_min, 8, "el «30 minutos» de la tarjeta")
        fila(6, "Otro texto (ámbito, etc.):", v_otros)
        fila(7, "Descripción completa:", vars_["desc"], 70, "se compone sola; puedes retocarla")

        def recomponer(*_):
            vars_["desc"].set(md.componer_desc(v_preg.get(), v_min.get(), v_otros.get()))
        for v in (v_preg, v_min, v_otros):
            v.trace_add("write", recomponer)

        def leer_del_supuesto():
            try:
                datos = datos_html.leer_html(self.raiz / "supuestos" / (ident + ".html"))[0]
            except (OSError, ValueError) as e:
                messagebox.showerror("Editar", "No puedo leer ese supuesto:\n\n%s" % e, parent=d)
                return
            f = md.ficha(ident, datos, letra=vars_["letra"].get().strip() or None)
            vars_["ref"].set(f["ref"])
            vars_["titulo"].set(f["titulo"])
            p_, m_, o_ = md.partir_desc(f["desc"])
            v_preg.set(p_); v_min.set(m_); v_otros.set(o_)

        ttk.Button(marco, text="↻ Leer preguntas, minutos, referencia y título del supuesto",
                   command=leer_del_supuesto).grid(row=8, column=0, columnspan=3, sticky="w", pady=(6, 2))
        ttk.Checkbutton(marco, text="Ocultar en el menú (se puede abrir con su enlace)",
                        variable=v_oculto).grid(row=9, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Checkbutton(marco, text="Guardar también los minutos, la referencia y el título DENTRO del supuesto "
                                    "(cambia el tiempo real del examen; deja copia .bak)",
                        variable=v_html).grid(row=10, column=0, columnspan=3, sticky="w", pady=2)

        def aceptar():
            if len(vars_["letra"].get().strip()) > 4:
                messagebox.showwarning("Editar", "El texto del círculo no puede pasar de 4 caracteres.", parent=d)
                return
            minutos_txt = v_min.get().strip()
            if v_html.get():
                if not minutos_txt.isdigit() or int(minutos_txt) < 1:
                    messagebox.showwarning("Editar", "Para guardarlo en el supuesto, los minutos deben ser un número "
                                           "de 1 o más.", parent=d)
                    return
                if not self._escribir_en_supuesto(ident, int(minutos_txt), vars_["ref"].get().strip(),
                                                  vars_["titulo"].get().strip(), d):
                    return
            md.editar(self.menu, ident, **{k: v.get() for k, v in vars_.items()})
            md.ocultar(self.menu, ident, bool(v_oculto.get()))
            d.destroy()
            self._cambio("i:" + ident)
        fila_btn = ttk.Frame(marco)
        fila_btn.grid(row=11, column=0, columnspan=3, sticky="e", pady=(10, 0))
        ttk.Button(fila_btn, text="Cancelar", command=d.destroy).pack(side="right")
        ttk.Button(fila_btn, text="Aceptar", command=aceptar).pack(side="right", padx=6)
        d.grab_set()

    def _escribir_en_supuesto(self, ident, minutos, ref, titulo, parent):
        """Cambia minutos, referencia y título en el HTML del supuesto. True si se guardó."""
        ruta = self.raiz / "supuestos" / (ident + ".html")
        try:
            datos, modo, html = datos_html.leer_html(ruta)
            cfg = datos.setdefault("config", {})
            cfg["minutos"] = minutos
            if ref:
                cfg["referencia"] = ref
            if titulo:
                cfg["titulo"] = titulo
            datos_html.escribir_html(ruta, html, datos, modo)
        except (OSError, ValueError) as e:
            messagebox.showerror("Editar", "No he podido guardar en %s:\n\n%s" % (ruta.name, e), parent=parent)
            return False
        sl.refrescar_silencioso(ruta)
        return True

    def ocultar(self):
        tipo, ident = self._sel()
        if tipo == "i":
            it = md.buscar(self.menu, ident)
            md.ocultar(self.menu, ident, not it[1][it[2]].get("oculto"))
            self._cambio("i:" + ident)

    def quitar(self):
        tipo, ident = self._sel()
        if tipo == "i" and messagebox.askyesno(
                "Quitar del menú", "¿Quito «%s» del menú?\n\nEl archivo del supuesto NO se borra: sigue en la "
                "carpeta supuestos/ y se puede volver a añadir." % ident, parent=self.v):
            md.quitar(self.menu, ident)
            self._cambio()

    def anadir(self):
        falta = md.sin_alta(self.menu, self.raiz / "supuestos")
        if not falta:
            messagebox.showinfo("Menú de inicio", "Todos los supuestos de la carpeta ya están en el menú.", parent=self.v)
            return
        nombre = self._elegir_de_lista("Supuestos que faltan en el menú", falta)
        if not nombre:
            return
        try:
            datos = datos_html.leer_html(self.raiz / "supuestos" / (nombre + ".html"))[0]
        except (OSError, ValueError) as e:
            messagebox.showerror("Menú de inicio", "No puedo leer ese supuesto:\n\n%s" % e, parent=self.v)
            return
        clave = self._elegir_destino("¿En qué grupo lo pongo?")
        if clave:
            md.anadir(self.menu, md.ficha(nombre, datos), clave)
            self._cambio("i:" + nombre)

    # ── más opciones ──
    def extremo(self, al_principio):
        tipo, ident = self._sel()
        if tipo == "i" and md.mover_extremo(self.menu, ident, al_principio):
            self._cambio("i:" + ident)

    def ver(self):
        tipo, ident = self._sel()
        if tipo != "i":
            if tipo:
                messagebox.showinfo("Menú de inicio", "Elige un supuesto para verlo.", parent=self.v)
            return
        archivo = self.raiz / "supuestos" / (ident + ".html")
        if not archivo.is_file():
            messagebox.showwarning("Menú de inicio", "No encuentro %s en la carpeta supuestos/." % archivo.name, parent=self.v)
            return
        webbrowser.open(archivo.resolve().as_uri())

    def anadir_todos(self):
        falta = md.sin_alta(self.menu, self.raiz / "supuestos")
        if not falta:
            messagebox.showinfo("Menú de inicio", "Todos los supuestos de la carpeta ya están en el menú.", parent=self.v)
            return
        clave = self._elegir_destino("¿En qué grupo pongo los %d que faltan?" % len(falta))
        if not clave:
            return
        fallos = []
        for nombre in falta:
            try:
                datos = datos_html.leer_html(self.raiz / "supuestos" / (nombre + ".html"))[0]
            except (OSError, ValueError) as e:
                fallos.append("%s (%s)" % (nombre, e))
                continue
            md.anadir(self.menu, md.ficha(nombre, datos), clave)
        self._cambio()
        if fallos:
            messagebox.showwarning("Menú de inicio", "No he podido leer:\n\n" + "\n".join(fallos), parent=self.v)

    def ordenar(self):
        tipo, ident = self._sel()
        if tipo == "i":
            clave = md.buscar(self.menu, ident)[0]
        elif tipo == "g":
            clave = ident
        elif tipo == "x":
            clave = "examenes"
        else:
            if tipo:
                messagebox.showinfo("Menú de inicio", "Elige un grupo o un supuesto del grupo que quieres ordenar.", parent=self.v)
            return
        criterios = ["Por título (A→Z)", "Por referencia", "Por nombre de archivo"]
        i = self._elegir_de_lista("¿Cómo ordeno ese grupo?", criterios, indice=True)
        if i is not None and md.ordenar(self.menu, clave, ("titulo", "ref", "archivo")[i]):
            self._cambio(self.arbol.selection()[0] if self.arbol.selection() else None)

    def buscar(self):
        texto = simpledialog.askstring("Buscar", "Texto a buscar (título, referencia o archivo):",
                                       parent=self.v, initialvalue=self._ultima_busqueda)
        if not texto or not texto.strip():
            return
        self._ultima_busqueda = texto
        clave = texto.strip().lower()
        todos = []
        for _, lista in md._listas(self.menu):
            todos.extend(lista)
        aciertos = [it["archivo"] for it in todos
                    if clave in " ".join(str(it.get(k, "")) for k in ("titulo", "ref", "archivo", "desc")).lower()]
        if not aciertos:
            messagebox.showinfo("Buscar", "No encuentro «%s»." % texto, parent=self.v)
            return
        sel = self.arbol.selection()
        actual = sel[0][2:] if sel and sel[0].startswith("i:") else None
        siguiente = aciertos[(aciertos.index(actual) + 1) % len(aciertos)] if actual in aciertos else aciertos[0]
        self.arbol.selection_set("i:" + siguiente)
        self.arbol.see("i:" + siguiente)
        self.lbl.configure(text="%d resultado(s). Vuelve a pulsar «Buscar…» para pasar al siguiente." % len(aciertos))

    def plegar(self):
        self._plegado = not self._plegado
        def recorre(nodo):
            for h in self.arbol.get_children(nodo):
                self.arbol.item(h, open=not self._plegado)
                recorre(h)
        recorre("")

    # ── secciones y grupos ──
    def nueva_seccion(self):
        t = simpledialog.askstring("Nueva sección", "Título de la sección (p. ej. «Supuestos de repaso»):", parent=self.v)
        if t and t.strip():
            try:
                self._cambio("s:" + md.crear_seccion(self.menu, t))
            except ValueError as e:
                messagebox.showwarning("Nueva sección", str(e), parent=self.v)

    def nuevo_grupo(self):
        tipo, ident = self._sel()
        if not tipo or tipo == "x":
            return
        sec = ident.split("/")[0] if tipo in "sg" else None
        if sec is None:
            messagebox.showinfo("Menú de inicio", "Elige la sección donde va el grupo nuevo.", parent=self.v)
            return
        t = simpledialog.askstring("Nuevo grupo", "Título del grupo (p. ej. «Repaso final»):", parent=self.v)
        if t and t.strip():
            try:
                self._cambio("g:" + md.crear_grupo(self.menu, sec, t))
            except ValueError as e:
                messagebox.showwarning("Nuevo grupo", str(e), parent=self.v)

    def renombrar(self):
        tipo, ident = self._sel()
        if tipo in ("s", "g"):
            t = simpledialog.askstring("Cambiar nombre", "Nuevo título:", parent=self.v,
                                       initialvalue=self._titulo_de(tipo, ident))
            if t and md.renombrar(self.menu, ident, t):
                self._cambio("%s:%s" % (tipo, ident))

    def borrar_contenedor(self):
        tipo, ident = self._sel()
        if tipo in ("s", "g"):
            try:
                if md.eliminar_contenedor(self.menu, ident):
                    self._cambio()
            except ValueError as e:
                messagebox.showwarning("Borrar", str(e), parent=self.v)

    # ── diálogos auxiliares ──
    def _elegir_destino(self, pregunta):
        sitios = md.destinos(self.menu)
        i = self._elegir_de_lista(pregunta, [n for _, n in sitios], indice=True)
        return sitios[i][0] if i is not None else None

    def _elegir_de_lista(self, titulo, opciones, indice=False):
        d = tk.Toplevel(self.v)
        d.title(titulo)
        d.transient(self.v)
        marco = ttk.Frame(d, padding=14)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text=titulo).pack(anchor="w", pady=(0, 6))
        lb = tk.Listbox(marco, height=min(12, max(4, len(opciones))), width=60, exportselection=False)
        for o in opciones:
            lb.insert("end", o)
        lb.selection_set(0)
        lb.pack(fill="both", expand=True)
        res = []

        def ok():
            if lb.curselection():
                res.append(lb.curselection()[0])
            d.destroy()
        fila = ttk.Frame(marco)
        fila.pack(fill="x", pady=(10, 0))
        ttk.Button(fila, text="Cancelar", command=d.destroy).pack(side="right")
        ttk.Button(fila, text="Aceptar", command=ok).pack(side="right", padx=6)
        d.grab_set()
        self.v.wait_window(d)
        if not res:
            return None
        return res[0] if indice else opciones[res[0]]

    # ── guardar / cerrar ──
    def guardar(self):
        try:
            md.escribir_archivo(self.ruta_menu, self.texto, self.menu)
            self.texto = self.ruta_menu.read_text(encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Guardar menú", "No se pudo guardar:\n\n%s" % e, parent=self.v)
            return False
        self.sucio = False
        res = sl.refrescar_silencioso(self.ruta_menu)
        messagebox.showinfo("Menú guardado", "Guardado en %s.\n\n%s" % (md.ARCHIVO_MENU, sl.resumen(*res) if res else ""), parent=self.v)
        return True

    def cerrar(self):
        if self.sucio:
            r = messagebox.askyesnocancel("Menú de inicio", "Hay cambios sin guardar.\n\n¿Guardarlos antes de cerrar?", parent=self.v)
            if r is None or (r and not self.guardar()):
                return
        self.v.destroy()

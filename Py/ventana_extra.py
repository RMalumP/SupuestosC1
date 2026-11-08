# -*- coding: utf-8 -*-
"""
VENTANAS AUXILIARES DEL EDITOR
══════════════════════════════
Parte del editor de supuestos. La lógica está en herramientas_datos.py y publicar.py (sin ventana).

  estadisticas      reparto de letras, longitudes, preguntas sin motivación
  repetidas         preguntas parecidas dentro del supuesto y en los demás de supuestos/
  vista_previa      cómo se verá la pregunta seleccionada (se actualiza sola)
  nueva_de_plantilla  preguntas tipo (verdadero/falso, señale la incorrecta…)
  copiar_de_otro    copiar preguntas de otro supuesto
  restaurar_version volver a una copia anterior del archivo abierto
  ayuda             la parte de INSTRUCCIONES.txt de la pestaña actual (F1)
  impugnaciones     las impugnaciones de la hoja de Google, con salto al supuesto
  publicar_todo     comprobar, poner al día, subir la versión y sincronizar
  calculadora_plazos  en qué fecha vence un plazo (hábiles, naturales, meses)
  exportar_preguntas  a CSV o a texto (lo contrario de importar)
"""
import json
import webbrowser
from datetime import date
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, simpledialog

import herramientas_datos as hd
import publicar as pub
import sincronizar_local as sl
import datos_html
import git_sync as gs
import impugnaciones_datos as imp
import plazos
import segundo_plano as sp
import simulacro as sim
import ventana_subir
import ventana_sync

LETRAS = "ABCDEFG"


def _ventana(app, titulo, ancho=720, alto=520):
    v = tk.Toplevel(app)
    v.title(titulo)
    v.transient(app)
    v.geometry("%dx%d" % (ancho, alto))
    return v


def _texto(v, contenido, fuente=("Consolas", 10)):
    marco = ttk.Frame(v, padding=8)
    marco.pack(fill="both", expand=True)
    caja = tk.Text(marco, wrap="word", font=fuente)
    barra = ttk.Scrollbar(marco, orient="vertical", command=caja.yview)
    caja.configure(yscrollcommand=barra.set)
    barra.pack(side="right", fill="y")
    caja.pack(side="left", fill="both", expand=True)
    caja.insert("1.0", contenido)
    caja.configure(state="disabled")
    return caja


def estadisticas(app):
    app.volcar_todo()
    v = _ventana(app, "Estadísticas del supuesto", 640, 480)
    _texto(v, hd.estadisticas(app.datos))


def _otros_supuestos(app):
    carpeta = Path(sl.RAIZ_DEFECTO) / "supuestos"
    actual = app.ruta.resolve() if app.ruta else None
    otros = []
    for f in sorted(carpeta.glob("*.html")) if carpeta.is_dir() else []:
        if actual and f.resolve() == actual:
            continue
        try:
            d, _, _ = datos_html.leer_html(f)
            otros.append((f.name, d))
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    return otros


def repetidas(app):
    app.volcar_todo()
    v = _ventana(app, "Preguntas repetidas o muy parecidas", 760, 520)
    marco = ttk.Frame(v, padding=8)
    marco.pack(fill="both", expand=True)
    var = tk.BooleanVar(value=True)
    ttk.Checkbutton(marco, text="Buscar también en los demás supuestos de la carpeta supuestos/",
                    variable=var).pack(anchor="w")
    lista = tk.Listbox(marco, font=("Consolas", 9), activestyle="none")
    lista.pack(fill="both", expand=True, pady=6)
    res = []

    def buscar():
        otras = _otros_supuestos(app) if var.get() else []
        res[:] = hd.duplicados(app.datos, otras=otras)
        lista.delete(0, "end")
        for n, donde, m, r in res:
            q = app.datos["preguntas"][n - 1]["q"].replace("\n", " ")[:60]
            lista.insert("end", "P%-3d ≈ %s P%-3d  (%d%%)  %s" % (n, "esta" if donde == "este" else donde, m, r * 100, q))
        if not res:
            lista.insert("end", "No hay preguntas repetidas.")

    def ir(*_):
        s = lista.curselection()
        if s and s[0] < len(res):
            app.ir_a_pregunta(res[s[0]][0] - 1)

    lista.bind("<Double-Button-1>", ir)
    ttk.Button(marco, text="Buscar", command=buscar).pack(anchor="e")
    buscar()


def _texto_pregunta(p, n):
    lineas = ["PREGUNTA %d   [%s]" % (n, p.get("bloqueId", "")), "", p.get("q", ""), ""]
    for i, o in enumerate(p.get("a", [])):
        marca = "✔" if i in (p.get("correctas") or []) else " "
        lineas.append(" %s %s) %s" % (marca, LETRAS[i], o))
    if p.get("multiple"):
        lineas += ["", "(respuesta múltiple: hay que marcar todas las correctas)"]
    if p.get("law"):
        lineas += ["", "MOTIVACIÓN LEGAL", p["law"]]
    if p.get("tip"):
        lineas += ["", "💡 " + p["tip"]]
    return "\n".join(lineas)


def vista_previa(app):
    v = _ventana(app, "Vista previa de la pregunta", 640, 520)
    caja = tk.Text(v, wrap="word", font=("Segoe UI", 11), padx=12, pady=10)
    caja.pack(fill="both", expand=True)
    estado = {"ultimo": None, "vivo": True}

    def pintar():
        if not estado["vivo"]:
            return
        try:
            app._instantanea()
            p = app.pregunta_actual()
            t = _texto_pregunta(p, app.i_preg + 1) if p else "No hay ninguna pregunta seleccionada."
            if t != estado["ultimo"]:
                estado["ultimo"] = t
                caja.configure(state="normal")
                caja.delete("1.0", "end")
                caja.insert("1.0", t)
                caja.configure(state="disabled")
            v.after(1000, pintar)
        except tk.TclError:
            pass

    v.bind("<Destroy>", lambda e: estado.update(vivo=False) if e.widget is v else None)
    pintar()


def nueva_de_plantilla(app):
    v = _ventana(app, "Nueva pregunta desde plantilla", 380, 300)
    ttk.Label(v, text="Elige la plantilla:", padding=8).pack(anchor="w")
    lista = tk.Listbox(v, activestyle="none")
    nombres = list(hd.PLANTILLAS)
    for n in nombres:
        lista.insert("end", n)
    lista.selection_set(0)
    lista.pack(fill="both", expand=True, padx=8)

    def crear():
        s = lista.curselection()
        if not s:
            return
        app.anotar_historial()
        anterior = app.pregunta_actual()
        bid = anterior["bloqueId"] if anterior else app.datos["bloques"][0]["id"]
        sid = anterior["statementId"] if anterior else None
        if app.tipo_de_bloque(bid) == "test":
            sid = None
        destino = (app.i_preg + 1) if app.i_preg is not None else len(app.datos["preguntas"])
        app.datos["preguntas"].insert(destino, hd.pregunta_de_plantilla(nombres[s[0]], bid, sid))
        app.recargar_tras_cambio()
        app.ir_a_pregunta(destino)
        v.destroy()

    ttk.Button(v, text="Crear", command=crear, style="Accion.TButton").pack(pady=8)


def copiar_de_otro(app):
    ruta = filedialog.askopenfilename(parent=app, title="Copiar preguntas de…", initialdir=str(Path(sl.RAIZ_DEFECTO) / "supuestos"),
                                      filetypes=[("Páginas HTML", "*.html")])
    if not ruta:
        return
    try:
        datos, _, _ = datos_html.leer_html(ruta)
    except (OSError, ValueError, json.JSONDecodeError) as err:
        messagebox.showerror("Copiar preguntas", str(err), parent=app)
        return
    app.volcar_todo()
    v = _ventana(app, "Copiar preguntas de %s" % Path(ruta).name, 760, 560)
    marco = ttk.Frame(v, padding=8)
    marco.pack(fill="both", expand=True)
    ttk.Label(marco, text="Marca las preguntas (Ctrl+clic) y elige el bloque de destino.").pack(anchor="w")
    lista = tk.Listbox(marco, selectmode="extended", activestyle="none", font=("Consolas", 9), exportselection=False)
    lista.pack(fill="both", expand=True, pady=6)
    for i, p in enumerate(datos["preguntas"], 1):
        lista.insert("end", "%03d  %s" % (i, p["q"].replace("\n", " ")[:90]))
    fila = ttk.Frame(marco)
    fila.pack(fill="x")
    ttk.Label(fila, text="Al bloque:").pack(side="left")
    nombres = ["%s · %s" % (b["id"], b["titulo"]) for b in app.datos["bloques"]]
    combo = ttk.Combobox(fila, values=nombres, state="readonly", width=40)
    combo.current(0)
    combo.pack(side="left", padx=6)

    def copiar():
        sel = lista.curselection()
        if not sel:
            return
        bloque = app.datos["bloques"][combo.current()]
        sid = app.datos["enunciados"][0]["id"] if bloque["tipo"] != "test" and app.datos["enunciados"] else None
        app.anotar_historial()
        for i in sel:
            p = json.loads(json.dumps(datos["preguntas"][i]))
            p.update(bloqueId=bloque["id"], statementId=sid, factIds=[])
            app.datos["preguntas"].append(p)
        app.ordenar_preguntas_por_bloque()
        app.recargar_tras_cambio()
        app.estado("Copiadas %d preguntas de %s." % (len(sel), Path(ruta).name))
        v.destroy()

    ttk.Button(fila, text="Copiar", command=copiar, style="Accion.TButton").pack(side="right")
    ttk.Button(fila, text="Todas", command=lambda: lista.selection_set(0, "end")).pack(side="right", padx=6)


def restaurar_version(app):
    if not app.ruta:
        messagebox.showinfo("Restaurar", "Guarda primero el supuesto: aún no tiene historial.", parent=app)
        return
    copias = pub.copias_de(app.ruta, sl.RAIZ_DEFECTO)
    if not copias:
        messagebox.showinfo("Restaurar", "Todavía no hay copias anteriores de este archivo.", parent=app)
        return
    app.volcar_todo()
    v = _ventana(app, "Versiones anteriores de %s" % app.ruta.name, 900, 520)
    ttk.Label(v, text="Se guardan las últimas %d versiones (cada vez que guardas). Elige una para ver qué "
                      "cambiaría respecto a lo que tienes ahora." % pub.COPIAS, padding=8).pack(anchor="w")
    cuerpo = ttk.PanedWindow(v, orient="horizontal")
    cuerpo.pack(fill="both", expand=True, padx=8)
    lista = tk.Listbox(cuerpo, activestyle="none", width=24, exportselection=False)
    for c in copias:
        lista.insert("end", pub.etiqueta_copia(c))
    cuerpo.add(lista, weight=0)
    der = ttk.Frame(cuerpo)
    cuerpo.add(der, weight=1)
    caja = _texto(der, "", fuente=("Consolas", 9))
    cache = {}

    def leer(i):
        if i not in cache:
            cache[i] = datos_html.leer_html(copias[i])
        return cache[i]

    def comparar(*_):
        s = lista.curselection()
        if not s:
            return
        try:
            datos, _m, _h = leer(s[0])
        except (OSError, ValueError, json.JSONDecodeError) as err:
            texto = "No se puede leer esa versión: %s" % err
        else:
            cambios = hd.comparar_versiones(app.datos, datos)
            texto = ("Si cargas la versión del %s, respecto a lo que tienes ahora:\n\n" % pub.etiqueta_copia(copias[s[0]])
                     + ("\n".join("  · " + c for c in cambios) if cambios else "  (es igual que lo que tienes ahora)"))
        caja.configure(state="normal")
        caja.delete("1.0", "end")
        caja.insert("1.0", texto)
        caja.configure(state="disabled")

    def restaurar():
        s = lista.curselection()
        if not s:
            return
        if not messagebox.askyesno("Restaurar", "Se cargará esa versión en el editor (sin tocar el archivo hasta "
                                   "que guardes). ¿Seguir?", parent=v):
            return
        try:
            datos, modo, _html = leer(s[0])
        except (OSError, ValueError, json.JSONDecodeError) as err:
            messagebox.showerror("Restaurar", str(err), parent=v)
            return
        app.anotar_historial()
        app.datos, app.modo = json.loads(json.dumps(datos)), modo
        app._poner_datos(app.datos)
        app.estado("Versión del %s cargada. Pulsa Guardar si es la que quieres." % pub.etiqueta_copia(copias[s[0]]))
        v.destroy()

    lista.bind("<<ListboxSelect>>", comparar)
    lista.selection_set(0)
    comparar()
    ttk.Button(v, text="Cargar esta versión", command=restaurar, style="Accion.TButton").pack(pady=8)


# ── F6 · calculadora de plazos ───────────────────────────────────────
def calculadora_plazos(app):
    v = _ventana(app, "Calculadora de plazos (art. 30 LPAC)", 720, 600)
    m = ttk.Frame(v, padding=12)
    m.pack(fill="both", expand=True)
    fecha = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
    cantidad = tk.StringVar(value="10")
    unidad = tk.StringVar(value=plazos.UNIDADES[0])
    sabados = tk.BooleanVar(value=False)
    ttk.Label(m, text="Notificación o publicación (dd/mm/aaaa)").grid(row=0, column=0, sticky="w")
    ttk.Entry(m, textvariable=fecha, width=14).grid(row=0, column=1, sticky="w", padx=6)
    ttk.Label(m, text="Plazo").grid(row=1, column=0, sticky="w", pady=4)
    fila = ttk.Frame(m)
    fila.grid(row=1, column=1, sticky="w", padx=6)
    ttk.Spinbox(fila, from_=1, to=999, textvariable=cantidad, width=5).pack(side="left")
    ttk.Combobox(fila, textvariable=unidad, values=plazos.UNIDADES, state="readonly", width=16).pack(side="left", padx=4)
    ttk.Checkbutton(m, text="Los sábados cuentan como hábiles (no en la LPAC)", variable=sabados
                    ).grid(row=2, column=1, sticky="w", padx=6)
    ttk.Label(m, text="Festivos de tu comunidad o localidad (uno por línea: 19/03/2026 San José).\n"
                      "Los nacionales y el Viernes Santo ya están.", style="Ayuda.TLabel"
              ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 2))
    festivos = tk.Text(m, height=5, width=60, font=("Consolas", 9))
    festivos.grid(row=4, column=0, columnspan=2, sticky="nsew")
    festivos.insert("1.0", app._prefs.get("festivos", ""))
    resultado = ttk.Label(m, text="", font=("Georgia", 12, "bold"), foreground="#7a1f1f")
    resultado.grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 2))
    contenedor = ttk.Frame(m)
    contenedor.grid(row=7, column=0, columnspan=2, sticky="nsew")
    pasos = _texto(contenedor, "", fuente=("Segoe UI", 10))
    m.columnconfigure(1, weight=1)
    m.rowconfigure(7, weight=1)
    ultimo = {"texto": ""}

    def calcular(*_):
        app._prefs["festivos"] = festivos.get("1.0", "end-1c")
        inicio = plazos.leer_fecha(fecha.get())
        try:
            n = int(cantidad.get())
            if inicio is None:
                raise ValueError("Escribe la fecha como dd/mm/aaaa.")
            cal = plazos.Calendario(plazos.leer_festivos(festivos.get("1.0", "end")), sabados.get())
            fin, explicacion = plazos.calcular(inicio, n, unidad.get(), cal)
        except ValueError as err:
            resultado.configure(text=str(err))
            return
        resultado.configure(text="Vence el %s" % plazos.fecha_larga(fin))
        ultimo["texto"] = " ".join(explicacion)
        pasos.configure(state="normal")
        pasos.delete("1.0", "end")
        pasos.insert("1.0", "\n".join("%d. %s" % (i, t) for i, t in enumerate(explicacion, 1)))
        pasos.configure(state="disabled")

    def copiar():
        if ultimo["texto"]:
            v.clipboard_clear()
            v.clipboard_append(ultimo["texto"])
            app.estado("Explicación del plazo copiada: pégala en la motivación.")

    botones = ttk.Frame(m)
    botones.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
    ttk.Button(botones, text="Calcular", command=calcular, style="Accion.TButton").pack(side="left")
    ttk.Button(botones, text="Copiar la explicación", command=copiar).pack(side="left", padx=6)
    v.bind("<Return>", calcular)
    calcular()


# ── F9 · exportar preguntas ──────────────────────────────────────────
def generar_simulacro(app):
    """F2: examen nuevo con preguntas al azar de los supuestos marcados."""
    fuentes = [((d.get("config") or {}).get("titulo") or r.stem, r.name, d)
               for r, d in imp.leer_supuestos(sl.RAIZ_DEFECTO)]
    if not fuentes:
        messagebox.showinfo("Generar simulacro", "No encuentro supuestos en %s."
                            % (Path(sl.RAIZ_DEFECTO) / "supuestos"), parent=app)
        return
    v = _ventana(app, "Generar simulacro", 760, 600)
    marco = ttk.Frame(v, padding=10)
    marco.pack(fill="both", expand=True)
    ttk.Label(marco, style="Ayuda.TLabel", justify="left",
              text="Marca de qué supuestos sacar las preguntas (Ctrl+clic). La teoría se coge suelta; "
                   "cada caso práctico entra entero,\ncon su enunciado y todas sus preguntas. "
                   "Las preguntas repetidas en varios supuestos cuentan una vez.").pack(anchor="w")
    lista = tk.Listbox(marco, selectmode="extended", activestyle="none", exportselection=False, height=12,
                       font=("Consolas", 9))
    lista.pack(fill="both", expand=True, pady=6)
    for titulo, nombre, _d in fuentes:
        lista.insert("end", "%-24s %s" % (nombre, titulo))
    lista.selection_set(0, "end")
    hay = ttk.Label(marco, text="")
    hay.pack(anchor="w")

    rejilla = ttk.Frame(marco)
    rejilla.pack(fill="x", pady=6)
    v_teoria, v_casos = tk.IntVar(value=20), tk.IntVar(value=2)
    v_titulo = tk.StringVar(value="Simulacro %s" % date.today().strftime("%d/%m/%Y"))
    v_semilla = tk.StringVar()
    for fila, (texto, widget) in enumerate((
            ("Preguntas de teoría", ttk.Spinbox(rejilla, from_=0, to=500, width=6, textvariable=v_teoria)),
            ("Casos prácticos", ttk.Spinbox(rejilla, from_=0, to=50, width=6, textvariable=v_casos)),
            ("Título", ttk.Entry(rejilla, textvariable=v_titulo, width=50)),
            ("Semilla (opcional)", ttk.Entry(rejilla, textvariable=v_semilla, width=12)))):
        ttk.Label(rejilla, text=texto).grid(row=fila, column=0, sticky="w", pady=2)
        widget.grid(row=fila, column=1, sticky="w", padx=6, pady=2)
    ttk.Label(rejilla, style="Ayuda.TLabel",
              text="Con la misma semilla y los mismos supuestos sale el mismo simulacro.").grid(
        row=4, column=1, sticky="w", padx=6)

    def elegidas():
        return [(f[0], f[2]) for i, f in enumerate(fuentes) if i in lista.curselection()]

    def contar(*_):
        teoria, casos = sim.piezas(elegidas())
        hay.config(text="Disponibles: %d preguntas de teoría y %d casos prácticos (%d preguntas)."
                   % (len(teoria), len(casos), sum(len(c[2]) for c in casos)))

    def generar():
        if not lista.curselection():
            messagebox.showinfo("Generar simulacro", "Marca al menos un supuesto.", parent=v)
            return
        try:
            n_teoria, n_casos = int(v_teoria.get()), int(v_casos.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Generar simulacro", "Pon números en teoría y casos.", parent=v)
            return
        semilla = v_semilla.get().strip() or None
        datos, avisos = sim.generar(elegidas(), n_teoria, n_casos, semilla, v_titulo.get().strip())
        if not datos["preguntas"]:
            messagebox.showwarning("Generar simulacro", "No ha salido ninguna pregunta.", parent=v)
            return
        if avisos:
            messagebox.showinfo("Generar simulacro", "\n".join(avisos), parent=v)
        if app.abrir_como_nuevo(datos, "Simulacro con %d preguntas (%d min). Guárdalo con «Guardar como…»."
                                % (len(datos["preguntas"]), datos["config"]["minutos"])):
            v.destroy()

    lista.bind("<<ListboxSelect>>", contar)
    contar()
    pie = ttk.Frame(marco)
    pie.pack(fill="x", pady=(6, 0))
    ttk.Button(pie, text="Todos", command=lambda: (lista.selection_set(0, "end"), contar())).pack(side="left")
    ttk.Button(pie, text="Ninguno", command=lambda: (lista.selection_clear(0, "end"), contar())).pack(side="left", padx=6)
    ttk.Button(pie, text="Cerrar", command=v.destroy).pack(side="right")
    ttk.Button(pie, text="Generar", command=generar, style="Accion.TButton").pack(side="right", padx=6)


def exportar_preguntas(app):
    app.volcar_todo()
    marcadas = app.preguntas_marcadas() if hasattr(app, "preguntas_marcadas") else []
    todas = app.datos["preguntas"]
    if not todas:
        messagebox.showinfo("Exportar", "No hay preguntas.", parent=app)
        return
    solo = len(marcadas) > 1 and messagebox.askyesno(
        "Exportar", "Tienes %d preguntas marcadas en la lista.\n\n¿Exportar solo esas? (No = todas)" % len(marcadas),
        parent=app)
    elegidas = [todas[i] for i in marcadas] if solo else todas
    nombre = (app.ruta.stem if app.ruta else "preguntas") + ("_marcadas" if solo else "")
    ruta = filedialog.asksaveasfilename(
        parent=app, title="Exportar preguntas", initialfile=nombre + ".csv",
        filetypes=[("CSV para Excel (lo conserva todo)", "*.csv"), ("Texto (para leer o importar)", "*.txt")],
        defaultextension=".csv")
    if not ruta:
        return
    contenido = hd.exportar_texto(elegidas) if ruta.lower().endswith(".txt") else hd.exportar_csv(elegidas)
    try:
        Path(ruta).write_text(contenido, encoding="utf-8", newline="")
    except OSError as err:
        messagebox.showerror("Exportar", str(err), parent=app)
        return
    app.estado("%d preguntas exportadas a %s" % (len(elegidas), ruta))


def ayuda(app):
    ruta = Path(__file__).resolve().parent / "INSTRUCCIONES.txt"
    try:
        texto = ruta.read_text(encoding="utf-8")
    except OSError:
        messagebox.showinfo("Ayuda", "No encuentro INSTRUCCIONES.txt junto al programa.", parent=app)
        return
    titulo, cuerpo = pub.ayuda_para(texto, app.cuaderno.index("current"))
    v = _ventana(app, "Ayuda · " + titulo, 820, 600)
    _texto(v, cuerpo)


def impugnaciones(app):
    """Impugnaciones de la hoja de Google con su estado (pendiente, aceptada, rechazada)
    y una nota tuya; doble clic abre el supuesto en la pregunta exacta."""
    raiz = sl.RAIZ_DEFECTO
    v = _ventana(app, "Impugnaciones recibidas", 1000, 600)
    marco = ttk.Frame(v, padding=8)
    marco.pack(fill="both", expand=True)
    estado = tk.StringVar(value="Pulsa «Descargar» para leer la hoja de Google.")
    arriba = ttk.Frame(marco)
    arriba.pack(fill="x")
    ttk.Label(arriba, textvariable=estado).pack(side="left")
    ver = tk.StringVar(value="Todas")
    combo = ttk.Combobox(arriba, textvariable=ver, state="readonly", width=14,
                         values=("Todas",) + tuple(e.capitalize() + "s" for e in imp.ESTADOS))
    combo.pack(side="right")
    ttk.Label(arriba, text="Ver:").pack(side="right", padx=4)

    cols = ("estado", "fecha", "supuesto", "pregunta", "texto", "nota")
    arbol = ttk.Treeview(marco, columns=cols, show="headings", selectmode="extended")
    for c, t, w in (("estado", "Estado", 90), ("fecha", "Fecha", 120), ("supuesto", "Supuesto", 150),
                    ("pregunta", "Pregunta", 220), ("texto", "Impugnación", 270), ("nota", "Mi nota", 150)):
        arbol.heading(c, text=t, anchor="w")
        arbol.column(c, width=w, anchor="w")
    for e, color in (("pendiente", "#b45309"), ("aceptada", "#15803d"), ("rechazada", "#6b7280")):
        arbol.tag_configure(e, foreground=color)
    arbol.pack(fill="both", expand=True, pady=6)
    filas, sitios = [], {}
    estados = imp.leer_estados(raiz)

    def pintar(*_):
        arbol.delete(*arbol.get_children())
        filtro = ver.get()
        for i, f in enumerate(filas):
            k = imp.clave(f)
            e = imp.estado_de(estados, k)
            if filtro != "Todas" and e != filtro[:-1].lower():
                continue
            ruta, n, _r = sitios.get(i, (None, None, 0))
            donde = (ruta.stem.replace("supuesto_", "") if ruta else pub.columna(f, "supuesto")[:24])
            donde += " · P%d" % (n + 1) if n is not None else ""
            arbol.insert("", "end", iid=str(i), tags=(e,), values=(
                e, pub.columna(f, "marca", "fecha"), donde, imp.texto_pregunta(f)[:90],
                pub.columna(f, "texto", "impugn", "motivo")[:140], (estados.get(k) or {}).get("nota", "")))
        cuenta = imp.resumen(filas, estados)
        if filas:
            estado.set("%d impugnaciones: %d pendientes, %d aceptadas, %d rechazadas. Doble clic: ir a la pregunta."
                       % (len(filas), cuenta["pendiente"], cuenta["aceptada"], cuenta["rechazada"]))

    def descargar():
        def trabajo():
            datos = pub.leer_impugnaciones(pub.descargar_impugnaciones(raiz))
            supuestos = imp.leer_supuestos(raiz)
            return datos, {i: imp.localizar(f, supuestos) for i, f in enumerate(datos)}

        def hecho(res):
            filas[:], nuevos = res
            sitios.clear()
            sitios.update(nuevos)
            pintar()

        sp.lanzar(v, trabajo, hecho, al_fallar=lambda err: estado.set("No se han podido descargar: %s" % err),
                  botones=(b_desc,), aviso=estado, texto="Descargando de Google y buscando cada pregunta…")

    def marcadas():
        return [int(x) for x in arbol.selection()]

    def poner(e=None, nota=None):
        for i in marcadas():
            imp.poner_estado(raiz, estados, imp.clave(filas[i]), estado=e, nota=nota)
        pintar()

    def escribir_nota():
        sel = marcadas()
        if not sel:
            return
        previa = (estados.get(imp.clave(filas[sel[0]])) or {}).get("nota", "")
        texto = simpledialog.askstring("Nota", "Nota para %d impugnación(es):" % len(sel), initialvalue=previa, parent=v)
        if texto is not None:
            poner(nota=texto.strip())

    def abrir(*_):
        sel = marcadas()
        if not sel:
            return
        i = sel[0]
        ruta, n, parecido = sitios.get(i, (None, None, 0))
        if ruta is None:
            messagebox.showinfo("Impugnaciones", "No encuentro el supuesto «%s» en la carpeta supuestos/."
                                % pub.columna(filas[i], "supuesto"), parent=v)
            return
        if app.ruta is None or Path(app.ruta).resolve() != Path(ruta).resolve():
            app.abrir_ruta(ruta)
        if n is not None:
            app.ir_a_pregunta(n)
            app.estado("Impugnación de la pregunta %d (%d%% de parecido con el texto impugnado)."
                       % (n + 1, round(parecido * 100)))
        else:
            app.estado("No he encontrado la pregunta exacta: busca «%s»." % imp.texto_pregunta(filas[i])[:50])

    arbol.bind("<Double-Button-1>", abrir)
    combo.bind("<<ComboboxSelected>>", pintar)
    fila = ttk.Frame(marco)
    fila.pack(fill="x")
    b_desc = ttk.Button(fila, text="Descargar", command=descargar, style="Accion.TButton")
    b_desc.pack(side="left")
    ttk.Button(fila, text="Ir a la pregunta", command=abrir).pack(side="left", padx=6)
    ttk.Separator(fila, orient="vertical").pack(side="left", fill="y", padx=6)
    ttk.Button(fila, text="✔ Aceptada", command=lambda: poner("aceptada")).pack(side="left")
    ttk.Button(fila, text="✗ Rechazada", command=lambda: poner("rechazada")).pack(side="left", padx=4)
    ttk.Button(fila, text="… Pendiente", command=lambda: poner("pendiente")).pack(side="left")
    ttk.Button(fila, text="✎ Nota…", command=escribir_nota).pack(side="left", padx=4)
    ttk.Button(fila, text="Abrir la página de impugnaciones",
               command=lambda: webbrowser.open((Path(raiz) / "impugnaciones" / "impugnaciones.html").as_uri())
               ).pack(side="right")


def publicar_todo(app):
    """Comprobar → poner al día → subir la versión → sincronizar."""
    raiz = sl.RAIZ_DEFECTO
    if not sl.es_proyecto(raiz):
        messagebox.showinfo("Publicar", "Esta función necesita que «Py» esté dentro del proyecto.", parent=app)
        return
    if app.hay_cambios and not app.guardar():
        return
    informe = validar_supuestos_resumen(raiz)
    if informe["errores"]:
        messagebox.showerror("Publicar", "Hay errores en los supuestos; arréglalos antes de publicar:\n\n"
                             + "\n".join(informe["errores"][:12]), parent=app)
        return
    atrasadas = sl.paginas_atrasadas(raiz)
    try:
        version = pub.version_actual(raiz)
    except OSError:
        version = None
    # Primero se pregunta y DESPUÉS se toca algo: antes se rehacían las páginas
    # aunque se contestara que no.
    usa_git = gs.es_clon(raiz) and gs.hay_git()
    msg = ("Se va a publicar:\n\n · %d supuestos revisados, 0 errores\n · %d páginas se rehacen con la plantilla actual\n"
           " · la versión %s pasa al número siguiente %s\n\n%s ¿Seguir?"
           % (informe["revisados"], len(atrasadas), version or "?",
              "justo al subir (si cierras sin subir, no cambia)" if usa_git else "ahora",
              "Después eliges qué archivos subir a GitHub." if usa_git else
              "Después se prepara la carpeta PARA_SUBIR para arrastrarla a la web de GitHub."))
    if not messagebox.askyesno("Publicar", msg, parent=app):
        return
    hechos, _saltados = sl.poner_al_dia(raiz)
    if hechos:
        app.estado("%d página(s) rehechas con la plantilla actual." % len(hechos))
    if not usa_git:
        try:
            antes, despues = pub.subir_version(raiz)
            app.estado("Versión %s → %s." % (antes, despues))
        except (OSError, ValueError) as err:
            messagebox.showerror("Publicar", "No he podido subir la versión:\n\n%s" % err, parent=app)
        ventana_subir.abrir(app)
        return

    subida = {}

    def subir_version():
        """Se llama justo antes de subir; devuelve el archivo que hay que añadir.
        Solo sube el número una vez, aunque haya que reintentar la subida."""
        if not subida:
            try:
                antes, despues = pub.subir_version(raiz)
            except (OSError, ValueError) as err:
                messagebox.showerror("Publicar", "No he podido subir la versión:\n\n%s" % err, parent=app)
                return None
            subida["hecho"] = True
            app.estado("Versión %s → %s." % (antes, despues))
        return "config/version.js"

    ventana_sync.abrir(app, antes_de_subir=subir_version)


def validar_supuestos_resumen(raiz):
    """Pasa el validador del proyecto sin ventana: {'errores': [...], 'revisados': n}."""
    errores = []
    carpeta = Path(raiz) / "supuestos"
    revisados = 0
    for f in sorted(carpeta.glob("*.html")):
        revisados += 1
        try:
            datos, _, _ = datos_html.leer_html(f)
        except (OSError, ValueError, json.JSONDecodeError) as err:
            errores.append("%s: no se puede leer (%s)" % (f.name, err))
            continue
        errores += ["%s · %s" % (f.name, e) for e in hd.errores_graves(datos)]
    return {"errores": errores, "revisados": revisados}

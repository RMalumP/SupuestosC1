# -*- coding: utf-8 -*-
"""
VENTANAS «BUSCAR Y REEMPLAZAR» E «IMPORTAR PREGUNTAS»
═════════════════════════════════════════════════════
Parte del editor de supuestos. La lógica está en herramientas_datos.py (sin ventana).
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import herramientas_datos as hd

NOMBRE_CAMPO = {"q": "pregunta", "a": "opción", "law": "motivación", "tip": "consejo"}


def buscar_reemplazar(app):
    app.volcar_todo()
    d = tk.Toplevel(app)
    d.title("Buscar y reemplazar")
    d.transient(app)
    d.geometry("760x460")
    marco = ttk.Frame(d, padding=10)
    marco.pack(fill="both", expand=True)

    v_busca, v_nuevo, v_mayus = tk.StringVar(), tk.StringVar(), tk.BooleanVar(value=False)
    ttk.Label(marco, text="Buscar").grid(row=0, column=0, sticky="w")
    e1 = ttk.Entry(marco, textvariable=v_busca, width=50)
    e1.grid(row=0, column=1, sticky="we", padx=6, pady=2)
    ttk.Label(marco, text="Reemplazar por").grid(row=1, column=0, sticky="w")
    ttk.Entry(marco, textvariable=v_nuevo, width=50).grid(row=1, column=1, sticky="we", padx=6, pady=2)
    ttk.Checkbutton(marco, text="Distinguir mayúsculas", variable=v_mayus).grid(row=2, column=1, sticky="w")
    marco.columnconfigure(1, weight=1)

    lista = tk.Listbox(marco, activestyle="none", font=("Consolas", 9))
    lista.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=8)
    marco.rowconfigure(3, weight=1)
    lbl = ttk.Label(marco, text="")
    lbl.grid(row=4, column=0, columnspan=3, sticky="w")
    hallazgos = []

    def buscar(*_):
        app.volcar_todo()
        hallazgos[:] = hd.buscar(app.datos, v_busca.get(), v_mayus.get())
        lista.delete(0, "end")
        for n, campo, i, frag in hallazgos:
            extra = " %s" % "ABCDEFG"[i] if campo == "a" else ""
            lista.insert("end", "P%-3d %-10s %s" % (n + 1, NOMBRE_CAMPO[campo] + extra, frag))
        lbl.config(text="%d coincidencias." % len(hallazgos))

    def ir(*_):
        sel = lista.curselection()
        if sel:
            app.ir_a_pregunta(hallazgos[sel[0]][0])

    def reemplazar():
        if not v_busca.get():
            return
        if not messagebox.askyesno("Reemplazar",
                                   "¿Cambiar «%s» por «%s» en todo el supuesto?\n\n"
                                   "(Se puede deshacer con Ctrl+Z.)" % (v_busca.get(), v_nuevo.get()),
                                   parent=d):
            return
        app.anotar_historial()
        n = hd.reemplazar(app.datos, v_busca.get(), v_nuevo.get(), v_mayus.get())
        app.recargar_tras_cambio()
        buscar()
        lbl.config(text="%d sustituciones hechas." % n)
        app.estado("Reemplazar: %d sustituciones." % n)

    fila = ttk.Frame(marco)
    fila.grid(row=5, column=0, columnspan=3, sticky="e")
    ttk.Button(fila, text="Buscar", command=buscar).pack(side="left", padx=3)
    ttk.Button(fila, text="Ir a la pregunta", command=ir).pack(side="left", padx=3)
    ttk.Button(fila, text="Reemplazar todo", command=reemplazar).pack(side="left", padx=3)
    ttk.Button(fila, text="Cerrar", command=d.destroy).pack(side="left", padx=3)
    lista.bind("<Double-Button-1>", ir)
    e1.bind("<Return>", buscar)
    e1.focus_set()


AYUDA = ("Pega las preguntas separadas por una línea en blanco:\n\n"
         "1) Texto de la pregunta\na) opción\nb) *opción correcta (con * delante)\nc) opción\nd) opción\n"
         "Motivación: texto opcional\nConsejo: texto opcional\n\n"
         "En lugar del *, también vale una línea «Correcta: b» (o «b, c» si es múltiple).\n"
         "Un CSV (pregunta; a; b; c; d; correcta; motivación; consejo) se abre con «Abrir archivo…».")


def importar(app):
    app.volcar_todo()
    d = tk.Toplevel(app)
    d.title("Importar preguntas")
    d.transient(app)
    d.geometry("760x560")
    marco = ttk.Frame(d, padding=10)
    marco.pack(fill="both", expand=True)
    ttk.Label(marco, text=AYUDA, justify="left", style="Ayuda.TLabel").pack(anchor="w")
    fila = ttk.Frame(marco)
    fila.pack(fill="x", pady=6)
    ttk.Label(fila, text="Añadir al bloque:").pack(side="left")
    nombres = ["%s · %s" % (b["id"], b["titulo"]) for b in app.datos["bloques"]]
    combo = ttk.Combobox(fila, values=nombres, state="readonly", width=40)
    combo.current(0)
    combo.pack(side="left", padx=6)
    caja = tk.Text(marco, wrap="word", font=("Consolas", 10), undo=True)
    caja.pack(fill="both", expand=True)
    estado = {"csv": False}

    def abrir_archivo():
        ruta = filedialog.askopenfilename(parent=d, filetypes=[("Texto o CSV", "*.txt *.csv"),
                                                              ("Todos", "*.*")])
        if not ruta:
            return
        try:
            with open(ruta, encoding="utf-8-sig") as f:
                texto = f.read()
        except (OSError, UnicodeDecodeError) as err:
            messagebox.showerror("Importar", str(err), parent=d)
            return
        estado["csv"] = ruta.lower().endswith(".csv")
        caja.delete("1.0", "end")
        caja.insert("1.0", texto)

    def hacer():
        texto = caja.get("1.0", "end")
        bloque = app.datos["bloques"][combo.current()]
        sid = None
        if bloque["tipo"] != "test" and app.datos["enunciados"]:
            sid = app.datos["enunciados"][0]["id"]
        func = hd.importar_csv if estado["csv"] else hd.importar_texto
        nuevas, avisos = func(texto, bloque["id"], sid)
        if not nuevas:
            messagebox.showwarning("Importar", "No se ha podido leer ninguna pregunta.\n\n"
                                   + "\n".join(avisos[:8]), parent=d)
            return
        app.anotar_historial()
        app.datos["preguntas"].extend(nuevas)
        app.ordenar_preguntas_por_bloque()
        app.recargar_tras_cambio()
        app.estado("Importadas %d preguntas en %s." % (len(nuevas), bloque["id"]))
        msg = "Importadas %d preguntas." % len(nuevas)
        if avisos:
            msg += "\n\nAvisos:\n" + "\n".join(avisos[:10])
        if bloque["tipo"] != "test" and sid:
            msg += "\n\nSe han colgado del enunciado %s; cámbialo en la pestaña 4 si hace falta." % sid
        messagebox.showinfo("Importar", msg, parent=d)
        d.destroy()

    pie = ttk.Frame(marco)
    pie.pack(fill="x", pady=(8, 0))
    ttk.Button(pie, text="Abrir archivo…", command=abrir_archivo).pack(side="left")
    ttk.Button(pie, text="Cerrar", command=d.destroy).pack(side="right")
    ttk.Button(pie, text="Importar", command=hacer, style="Accion.TButton").pack(side="right", padx=6)

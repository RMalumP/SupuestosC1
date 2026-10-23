# -*- coding: utf-8 -*-
"""
VENTANA «PARA SUBIR A GITHUB»  (parte del editor; la lógica está en sincronizar_local.py)
"""
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

import sincronizar_local as sl


def _abrir_carpeta(ruta):
    ruta = str(ruta)
    if sys.platform.startswith("win"):
        os.startfile(ruta)                         # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", ruta])
    else:
        subprocess.Popen(["xdg-open", ruta])


def abrir(app):
    """Ventana con los tres pasos: poner al día, ver/abrir la carpeta, marcar como subido."""
    raiz = sl.RAIZ_DEFECTO
    if not sl.es_proyecto(raiz):
        messagebox.showinfo("Para subir a GitHub",
                            "Esta función necesita que la carpeta «Py» esté dentro del proyecto "
                            "(la carpeta que tiene index.html y «supuestos»).", parent=app)
        return
    sl.asegurar_base(raiz)
    v = tk.Toplevel(app)
    v.title("Para subir a GitHub")
    v.transient(app)
    v.resizable(False, False)
    marco = ttk.Frame(v, padding=16)
    marco.pack(fill="both", expand=True)
    ttk.Label(marco, wraplength=460, justify="left",
              text="Aquí ves qué archivos han cambiado desde que bajaste el repositorio. "
                   "Se copian a la carpeta «%s» con la misma estructura; "
                   "solo tienes que arrastrar su contenido a GitHub." % sl.CARPETA).pack(anchor="w")
    estado = tk.StringVar()
    lista = tk.Text(marco, width=62, height=14, wrap="none", relief="solid", borderwidth=1)
    lista.pack(fill="both", expand=True, pady=(10, 4))
    ttk.Label(marco, textvariable=estado, wraplength=460, justify="left").pack(anchor="w")

    def pintar(res=None):
        res = res if res is not None else sl.preparar_para_subir(raiz)
        nuevos, modif, borrados = res
        lista.configure(state="normal")
        lista.delete("1.0", "end")
        for titulo, rutas in (("NUEVOS", nuevos), ("MODIFICADOS", modif), ("BORRADOS EN LOCAL", borrados)):
            if rutas:
                lista.insert("end", titulo + " (%d)\n" % len(rutas))
                lista.insert("end", "".join("   · %s\n" % r for r in rutas) + "\n")
        if not (nuevos or modif or borrados):
            lista.insert("end", "Nada que subir: todo coincide con lo descargado.\n")
        lista.configure(state="disabled")
        estado.set(sl.resumen(*res))

    def al_dia():
        hechos, saltados = sl.poner_al_dia(raiz)
        msg = ["%s: motor %d → %d" % h for h in hechos] + ["%s: %s" % s for s in saltados]
        pintar()
        messagebox.showinfo("Poner todo al día",
                            ("Páginas rehechas con la plantilla actual:\n\n" + "\n".join(msg)) if msg
                            else "Todos los supuestos ya tienen el motor actual.", parent=v)

    def subido():
        if messagebox.askyesno("Marcar como subido",
                               "¿Ya has subido esos archivos a GitHub?\n\nLo actual pasará a ser la nueva "
                               "referencia y la carpeta %s se vaciará." % sl.CARPETA, parent=v):
            sl.marcar_subido(raiz)
            pintar()

    botones = ttk.Frame(marco)
    botones.pack(fill="x", pady=(10, 0))
    ttk.Button(botones, text="Poner todo al día", command=al_dia).pack(side="left")
    ttk.Button(botones, text="Actualizar lista", command=pintar).pack(side="left", padx=6)
    ttk.Button(botones, text="Abrir carpeta %s" % sl.CARPETA,
               command=lambda: (pintar(), _abrir_carpeta(raiz / sl.CARPETA) if (raiz / sl.CARPETA).exists()
                                else messagebox.showinfo("Para subir", "Todavía no hay nada que subir.", parent=v))
               ).pack(side="left")
    ttk.Button(botones, text="Marcar como subido", command=subido).pack(side="right")
    pintar()

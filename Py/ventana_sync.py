# -*- coding: utf-8 -*-
"""
VENTANA «SINCRONIZAR CON GITHUB»  (parte del editor; la lógica está en git_sync.py)
"""
import tkinter as tk
from tkinter import ttk, messagebox

import git_sync as gs
import sincronizar_local as sl

ETIQUETAS = {
    "dia": "Rama propia del día (la fusionas luego en GitHub)",
    "actual": "La rama que tengo abierta",
    "principal": "Directo a la rama principal",
}


def abrir(app):
    raiz = sl.RAIZ_DEFECTO
    if not gs.hay_git():
        messagebox.showinfo("Sincronizar", gs.SIN_GIT, parent=app)
        return
    if not gs.es_clon(raiz):
        messagebox.showinfo("Sincronizar", "Esta carpeta no es un clon del repositorio (no tiene «.git»).\n\n"
                            "Clona el repositorio con GitHub Desktop o con «git clone» y abre el editor "
                            "desde esa copia. Mientras tanto puedes usar «Para subir a GitHub…».", parent=app)
        return
    if app.hay_cambios and messagebox.askyesno("Sincronizar", "Hay cambios sin guardar en el supuesto abierto.\n\n"
                                               "¿Guardarlos antes de sincronizar?", parent=app):
        if not app.guardar():
            return

    v = tk.Toplevel(app)
    v.title("Sincronizar con GitHub")
    v.transient(app)
    v.geometry("700x600")
    marco = ttk.Frame(v, padding=14)
    marco.pack(fill="both", expand=True)

    try:
        actual, principal = gs.rama_actual(raiz), gs.rama_principal(raiz)
    except gs.ErrorGit as err:
        messagebox.showerror("Sincronizar", str(err), parent=v)
        v.destroy()
        return
    ttk.Label(marco, justify="left", wraplength=660,
              text="Rama abierta: %s    ·    rama principal: %s" % (actual, principal)).pack(anchor="w")

    ttk.Label(marco, text="¿Dónde subo los cambios?", style="Campo.TLabel").pack(anchor="w", pady=(10, 2))
    destino = tk.StringVar(value=app._prefs.get("sync_destino", "dia")
                           if app._prefs.get("sync_destino") in gs.DESTINOS else "dia")
    for clave in gs.DESTINOS:
        extra = {"dia": " → %s" % gs.nombre_rama_dia(), "actual": " → %s" % actual,
                 "principal": " → %s" % principal}[clave]
        ttk.Radiobutton(marco, text=ETIQUETAS[clave] + extra, variable=destino, value=clave).pack(anchor="w")

    ttk.Label(marco, text="Archivos que subir (marca los que quieras)", style="Campo.TLabel").pack(
        anchor="w", pady=(10, 2))
    cuerpo = ttk.Frame(marco)
    cuerpo.pack(fill="both", expand=True)
    lista = tk.Listbox(cuerpo, selectmode="extended", activestyle="none", font=("Consolas", 9), exportselection=False)
    barra = ttk.Scrollbar(cuerpo, orient="vertical", command=lista.yview)
    lista.configure(yscrollcommand=barra.set)
    lista.pack(side="left", fill="both", expand=True)
    barra.pack(side="left", fill="y")
    rutas = []

    msg = tk.StringVar()
    ttk.Label(marco, text="Mensaje (qué has cambiado)", style="Campo.TLabel").pack(anchor="w", pady=(10, 2))
    ttk.Entry(marco, textvariable=msg).pack(fill="x")
    estado = tk.StringVar()
    ttk.Label(marco, textvariable=estado, wraplength=660, justify="left").pack(anchor="w", pady=(8, 0))

    def refrescar(*_):
        try:
            n, m, b = gs.estado(raiz)
        except gs.ErrorGit as err:
            estado.set(str(err))
            return
        rutas[:] = [("nuevo", r) for r in n] + [("modificado", r) for r in m] + [("borrado", r) for r in b]
        lista.delete(0, "end")
        for tipo, r in rutas:
            lista.insert("end", "%-10s %s" % (tipo, r))
        lista.selection_set(0, "end")
        msg.set(gs.mensaje_sugerido(n, m, b) if rutas else "")
        estado.set("%d archivo(s) con cambios." % len(rutas) if rutas else "Nada que subir: todo coincide con GitHub.")

    def traer():
        try:
            v.config(cursor="watch")
            v.update_idletasks()
            estado.set(gs.traer(raiz))
        except gs.ErrorGit as err:
            messagebox.showerror("Traer de GitHub", str(err), parent=v)
        finally:
            v.config(cursor="")
        refrescar()

    def subir():
        marcados = [rutas[i][1] for i in lista.curselection()]
        if not marcados:
            messagebox.showinfo("Sincronizar", "No hay ningún archivo marcado.", parent=v)
            return
        if destino.get() == "principal" and not messagebox.askyesno(
                "Subir a la rama principal",
                "Los cambios irán DIRECTOS a la rama principal («%s»), sin revisión.\n\n¿Seguro?" % principal,
                parent=v):
            return
        try:
            v.config(cursor="watch")
            v.update_idletasks()
            texto, enlace = gs.subir(raiz, marcados, msg.get(), destino.get())
        except gs.ErrorGit as err:
            messagebox.showerror("No se ha podido subir", str(err), parent=v)
            return
        finally:
            v.config(cursor="")
        app._prefs["sync_destino"] = destino.get()
        estado.set(texto + ("\n" + enlace if enlace else ""))
        app.estado(texto)
        refrescar()
        estado.set(texto + ("\n" + enlace if enlace else ""))

    pie = ttk.Frame(marco)
    pie.pack(fill="x", pady=(10, 0))
    ttk.Button(pie, text="Traer lo último", command=traer).pack(side="left")
    ttk.Button(pie, text="Actualizar lista", command=refrescar).pack(side="left", padx=6)
    ttk.Button(pie, text="Cerrar", command=v.destroy).pack(side="right")
    ttk.Button(pie, text="☁ Subir", command=subir, style="Accion.TButton").pack(side="right", padx=6)
    refrescar()

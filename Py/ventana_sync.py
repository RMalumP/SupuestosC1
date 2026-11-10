# -*- coding: utf-8 -*-
"""
VENTANA «SINCRONIZAR CON GITHUB»  (parte del editor; la lógica está en git_sync.py)
"""
import tkinter as tk
from tkinter import ttk, messagebox

import git_sync as gs
import imagenes
import segundo_plano as sp
import sincronizar_local as sl

ETIQUETAS = {
    "dia": "Rama propia del día (la fusionas luego en GitHub)",
    "actual": "La rama que tengo abierta",
    "principal": "Directo a la rama principal",
}


def abrir(app, antes_de_subir=None):
    """antes_de_subir: función opcional que se llama justo antes de subir (por ejemplo,
    la de «Publicar todo», que sube el número de versión) y devuelve un archivo más
    que añadir a la subida, o None."""
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
    v.title("Publicar en GitHub")
    v.transient(app)
    v.geometry("720x620")
    marco = ttk.Frame(v, padding=14)
    marco.pack(fill="both", expand=True)

    try:
        actual, principal = gs.rama_actual(raiz), gs.rama_principal(raiz)
    except gs.ErrorGit as err:
        messagebox.showerror("Publicar", str(err), parent=v)
        v.destroy()
        return
    cabecera = ttk.Frame(marco)
    cabecera.pack(fill="x")
    lbl_ramas = ttk.Label(cabecera, justify="left", wraplength=520)
    lbl_ramas.pack(side="left", anchor="w")
    btn_volver = ttk.Button(cabecera, text="↩ Volver a la principal")

    ttk.Label(marco, text="¿Dónde subo los cambios?", style="Campo.TLabel").pack(anchor="w", pady=(10, 2))
    destino = tk.StringVar(value=app._prefs.get("sync_destino", "dia")
                           if app._prefs.get("sync_destino") in gs.DESTINOS else "dia")
    radios = []
    for clave in gs.DESTINOS:
        r = ttk.Radiobutton(marco, variable=destino, value=clave)
        r.pack(anchor="w")
        radios.append((clave, r))

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
    ttk.Label(marco, textvariable=estado, wraplength=680, justify="left").pack(anchor="w", pady=(8, 0))

    pie = ttk.Frame(marco)
    pie.pack(fill="x", pady=(10, 0))
    btn_traer = ttk.Button(pie, text="Traer lo último")
    btn_traer.pack(side="left")
    btn_lista = ttk.Button(pie, text="Actualizar lista")
    btn_lista.pack(side="left", padx=6)
    ttk.Button(pie, text="Cerrar", command=v.destroy).pack(side="right")
    btn_subir = ttk.Button(pie, text="☁ Subir", style="Accion.TButton")
    btn_subir.pack(side="right", padx=6)
    botones = (btn_traer, btn_lista, btn_subir, btn_volver)

    def pintar_ramas():
        lbl_ramas.configure(text="Rama abierta: %s    ·    rama principal: %s" % (actual, principal))
        if actual != principal:
            btn_volver.pack(side="right")
        else:
            btn_volver.pack_forget()
        for clave, r in radios:
            extra = {"dia": " → %s (sale de lo último de %s)" % (gs.nombre_rama_dia(), principal),
                     "actual": " → %s" % actual, "principal": " → %s" % principal}[clave]
            r.configure(text=ETIQUETAS[clave] + extra)

    def refrescar(*_):
        dest = destino.get()

        def trabajo():
            n, m, b = gs.estado(raiz)
            todas = n + m + b
            try:
                _rama, ref, _sha = gs.referencia_destino(raiz, dest)
                hechos = gs.ya_subidos(raiz, todas, ref) if todas else set()
            except gs.ErrorGit:
                hechos = set()
            return n, m, b, hechos

        def pintar(res):
            n, m, b, hechos = res
            rutas[:] = [("nuevo", r) for r in n] + [("modificado", r) for r in m] + [("borrado", r) for r in b]
            lista.delete(0, "end")
            pendientes = 0
            for i, (tipo, r) in enumerate(rutas):
                ya = r in hechos
                lista.insert("end", "%-10s %s%s" % (tipo, r, "   (ya está en esa rama)" if ya else ""))
                if ya:
                    lista.itemconfigure(i, foreground="#8a7a6a")
                else:
                    lista.selection_set(i)
                    pendientes += 1
            msg.set(gs.mensaje_sugerido(n, m, b) if rutas else "")
            if not rutas:
                estado.set("Nada que subir: todo coincide con GitHub.")
            else:
                estado.set("%d archivo(s) con cambios; %d sin subir a esa rama." % (len(rutas), pendientes))

        sp.lanzar(v, trabajo, pintar, botones=botones, aviso=estado, texto="Mirando qué ha cambiado…")

    def traer():
        sp.lanzar(v, lambda: gs.traer(raiz), lambda texto: (refrescar(), estado.set(texto)),
                  al_fallar=lambda err: messagebox.showerror("Traer de GitHub", str(err), parent=v),
                  botones=botones, aviso=estado, texto="Trayendo lo último de GitHub…")

    def volver():
        def hecho(texto):
            nonlocal actual
            actual = gs.rama_actual(raiz)
            pintar_ramas()
            refrescar()
            app.estado(texto)
        sp.lanzar(v, lambda: gs.volver_a_principal(raiz), hecho,
                  al_fallar=lambda err: messagebox.showerror("Volver a la principal", str(err), parent=v),
                  botones=botones, aviso=estado, texto="Cambiando a la rama principal…")

    def subir():
        marcados = [rutas[i][1] for i in lista.curselection()]
        if not marcados:
            messagebox.showinfo("Publicar", "No hay ningún archivo marcado.", parent=v)
            return
        if destino.get() == "principal" and not messagebox.askyesno(
                "Subir a la rama principal",
                "Los cambios irán DIRECTOS a la rama principal («%s»), sin revisión.\n\n¿Seguro?" % principal,
                parent=v):
            return
        if antes_de_subir:
            extra = antes_de_subir()
            if extra and extra not in marcados:
                marcados.append(extra)
        # Las imágenes de un supuesto marcado van siempre con él, aunque no se hayan marcado.
        marcados += imagenes.acompanantes(marcados, [r for _tipo, r in rutas])
        dest, texto_msg = destino.get(), msg.get()

        def hecho(res):
            texto, enlace = res
            app._prefs["sync_destino"] = dest
            app.estado(texto)
            refrescar()
            v.after(400, lambda: estado.set(texto + ("\n" + enlace if enlace else "")))

        sp.lanzar(v, lambda: gs.subir(raiz, marcados, texto_msg, dest), hecho,
                  al_fallar=lambda err: messagebox.showerror("No se ha podido subir", str(err), parent=v),
                  botones=botones, aviso=estado, texto="Subiendo a GitHub… (la ventana sigue respondiendo)")

    btn_traer.configure(command=traer)
    btn_lista.configure(command=refrescar)
    btn_subir.configure(command=subir)
    btn_volver.configure(command=volver)
    destino.trace_add("write", lambda *_: refrescar())
    pintar_ramas()
    refrescar()

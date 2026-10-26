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
"""
import json
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import herramientas_datos as hd
import publicar as pub
import sincronizar_local as sl
import datos_html
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
    v = _ventana(app, "Versiones anteriores de %s" % app.ruta.name, 420, 360)
    ttk.Label(v, text="Se guardan las últimas %d versiones (cada vez que guardas)." % pub.COPIAS, padding=8).pack(anchor="w")
    lista = tk.Listbox(v, activestyle="none")
    for c in copias:
        lista.insert("end", pub.etiqueta_copia(c))
    lista.selection_set(0)
    lista.pack(fill="both", expand=True, padx=8)

    def restaurar():
        s = lista.curselection()
        if not s:
            return
        if not messagebox.askyesno("Restaurar", "Se cargará esa versión en el editor (sin tocar el archivo hasta "
                                   "que guardes). ¿Seguir?", parent=v):
            return
        try:
            datos, modo, html = datos_html.leer_html(copias[s[0]])
        except (OSError, ValueError, json.JSONDecodeError) as err:
            messagebox.showerror("Restaurar", str(err), parent=v)
            return
        app.anotar_historial()
        app.datos, app.modo = datos, modo
        app._poner_datos(datos)
        app.estado("Versión del %s cargada. Pulsa Guardar si es la que quieres." % pub.etiqueta_copia(copias[s[0]]))
        v.destroy()

    ttk.Button(v, text="Cargar esta versión", command=restaurar, style="Accion.TButton").pack(pady=8)


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
    raiz = sl.RAIZ_DEFECTO
    v = _ventana(app, "Impugnaciones recibidas", 900, 560)
    marco = ttk.Frame(v, padding=8)
    marco.pack(fill="both", expand=True)
    estado = tk.StringVar(value="Pulsa «Descargar» para leer la hoja de Google.")
    ttk.Label(marco, textvariable=estado).pack(anchor="w")
    arbol = ttk.Treeview(marco, columns=("fecha", "supuesto", "pregunta", "texto"), show="headings")
    for c, t, w in (("fecha", "Fecha", 120), ("supuesto", "Supuesto", 150), ("pregunta", "Pregunta", 260), ("texto", "Impugnación", 330)):
        arbol.heading(c, text=t)
        arbol.column(c, width=w, anchor="w")
    arbol.pack(fill="both", expand=True, pady=6)
    filas = []

    def descargar():
        try:
            v.config(cursor="watch")
            v.update_idletasks()
            filas[:] = pub.leer_impugnaciones(pub.descargar_impugnaciones(raiz))
        except Exception as err:                       # red, permisos, configuración
            estado.set("No se han podido descargar: %s" % err)
            return
        finally:
            v.config(cursor="")
        arbol.delete(*arbol.get_children())
        for i, f in enumerate(filas):
            arbol.insert("", "end", iid=str(i), values=(
                pub.columna(f, "marca", "fecha"), pub.columna(f, "supuesto"),
                pub.columna(f, "pregunta")[:80], pub.columna(f, "texto", "motivo", "impugn")[:120]))
        estado.set("%d impugnaciones. Doble clic: abrir el supuesto en el editor y buscar la pregunta." % len(filas))

    def abrir(*_):
        s = arbol.selection()
        if not s:
            return
        f = filas[int(s[0])]
        nombre = pub.columna(f, "supuesto").strip()
        cand = Path(raiz) / "supuestos" / (nombre if nombre.endswith(".html") else nombre + ".html")
        if cand.is_file():
            app.abrir_ruta(cand)
            fragmento = pub.columna(f, "pregunta")[:40]
            if fragmento:
                for n, p in enumerate(app.datos["preguntas"]):
                    if fragmento.lower() in p["q"].lower():
                        app.ir_a_pregunta(n)
                        break
        else:
            messagebox.showinfo("Impugnaciones", "No encuentro el supuesto «%s» en la carpeta supuestos/." % nombre, parent=v)

    arbol.bind("<Double-Button-1>", abrir)
    fila = ttk.Frame(marco)
    fila.pack(fill="x")
    ttk.Button(fila, text="Descargar", command=descargar, style="Accion.TButton").pack(side="left")
    ttk.Button(fila, text="Abrir la página de impugnaciones",
               command=lambda: webbrowser.open((Path(raiz) / "impugnaciones" / "impugnaciones.html").as_uri())).pack(side="left", padx=6)


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
    hechos, _saltados = sl.poner_al_dia(raiz)
    try:
        version = pub.version_actual(raiz)
    except OSError:
        version = None
    msg = ("Se va a publicar:\n\n · %d supuestos revisados, 0 errores\n · %d páginas rehechas con la plantilla actual\n"
           " · versión %s → siguiente número\n\nDespués se abrirá «Sincronizar» para subirlo. ¿Seguir?"
           % (informe["revisados"], len(hechos), version or "?"))
    if not messagebox.askyesno("Publicar todo", msg, parent=app):
        return
    try:
        antes, despues = pub.subir_version(raiz)
    except (OSError, ValueError) as err:
        messagebox.showerror("Publicar", str(err), parent=app)
        return
    app.estado("Versión %s → %s. Sincroniza para subirla." % (antes, despues))
    ventana_sync.abrir(app)


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

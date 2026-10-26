# -*- coding: utf-8 -*-
"""
PIEZAS COMUNES DEL EDITOR
═════════════════════════
Importaciones, cuadros de texto con formato, rótulos y descripción de los campos.
Las usan editor_supuestos.py y los archivos pestana_*.py. No se ejecuta solo.
"""
import json
import os
import re
import sys
import webbrowser
from pathlib import Path

import menu_datos            # lista del menú
import sincronizar_local     # poner al día y carpeta PARA_SUBIR
import ventana_subir         # ventana «Para subir a GitHub»
import ventana_menu          # ventana «Menú de inicio»
import normas_enlaces        # normas que se enlazan al BOE (datos/normas-datos.js)
import herramientas_datos as herr   # deshacer, buscar, importar, autoguardado (sin ventana)
import ventana_herramientas      # ventanas «Buscar y reemplazar» e «Importar preguntas»
import ventana_sync              # ventana «Sincronizar con GitHub» (git)

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from tkinter import font as tkfont

# Todo lo que no es ventana (valores por defecto, normalizar, leer_html, escribir_html,
# alta en el menú…) está en datos_html.py, junto a este archivo.
from datos_html import *  # noqa: F401,F403

# ══════════════════════════════════════════════════════════════════════
#  4. PIEZAS REUTILIZABLES DE LA INTERFAZ
# ══════════════════════════════════════════════════════════════════════

class MarcoScroll(ttk.Frame):
    """Panel con barra de desplazamiento vertical. El contenido se
    añade dentro de .interior."""

    def __init__(self, padre, **kw):
        super().__init__(padre, **kw)
        self.lienzo = tk.Canvas(self, bg=C_FONDO, highlightthickness=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview)
        self.lienzo.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lienzo.pack(side="left", fill="both", expand=True)

        self.interior = ttk.Frame(self.lienzo, style="Panel.TFrame")
        self._ventana = self.lienzo.create_window((0, 0), window=self.interior, anchor="nw")

        self.interior.bind("<Configure>", self._al_redimensionar_interior)
        self.lienzo.bind("<Configure>", self._al_redimensionar_lienzo)
        self.bind("<Enter>", self._activar_rueda)
        self.bind("<Leave>", self._desactivar_rueda)

    def _al_redimensionar_interior(self, _evento):
        self.lienzo.configure(scrollregion=self.lienzo.bbox("all"))

    def _al_redimensionar_lienzo(self, evento):
        self.lienzo.itemconfigure(self._ventana, width=evento.width)

    # --- rueda del ratón (Windows/macOS usan <MouseWheel>; Linux, Button-4/5)
    def _activar_rueda(self, _e=None):
        self.bind_all("<MouseWheel>", self._rueda)
        self.bind_all("<Button-4>", self._rueda)
        self.bind_all("<Button-5>", self._rueda)

    def _desactivar_rueda(self, _e=None):
        self.unbind_all("<MouseWheel>")
        self.unbind_all("<Button-4>")
        self.unbind_all("<Button-5>")

    def _rueda(self, evento):
        bajo_raton = self.winfo_containing(evento.x_root, evento.y_root)
        if isinstance(bajo_raton, (tk.Text, tk.Listbox)):
            return                                   # deja que se desplace él
        if getattr(evento, "num", None) == 4:
            self.lienzo.yview_scroll(-3, "units")
        elif getattr(evento, "num", None) == 5:
            self.lienzo.yview_scroll(3, "units")
        else:
            self.lienzo.yview_scroll(int(-1 * (evento.delta / 40)), "units")


def rotulo(padre, visible, tecnico, html, ayuda="", con_titulo=True):
    """Rótulo doble de un campo:
         línea 1 → nombre tal y como se ve en la página publicada
         línea 2 → nombre del campo en el archivo + elemento HTML donde acaba
         línea 3 → (opcional) dónde se ve exactamente
    con_titulo=False omite la línea 1 (cuando el recuadro ya la lleva escrita).
    """
    marco = ttk.Frame(padre, style="Panel.TFrame")
    if con_titulo:
        ttk.Label(marco, text=visible, style="Campo.TLabel").pack(anchor="w")
    ttk.Label(marco, text="%s   →   HTML: %s" % (tecnico, html),
              style="Tec.TLabel").pack(anchor="w")
    if ayuda:
        ttk.Label(marco, text=ayuda, style="Ayuda.TLabel",
                  wraplength=820, justify="left").pack(anchor="w", pady=(1, 0))
    return marco


# ══════════════════════════════════════════════════════════════════════
#  FORMATO DEL TEXTO (negrita, cursiva, subrayado, tachado, resaltado y
#  tamaños de letra)
#  ─────────────────────────────────────────────────────────────────────
#  El texto del supuesto se guarda tal cual dentro del JSON y la página
#  lo pinta con innerHTML, así que el formato se escribe con etiquetas
#  HTML sencillas:
#
#      <b>…</b>        negrita
#      <i>…</i>        cursiva
#      <u>…</u>        subrayado
#      <s>…</s>        tachado
#      <mark>…</mark>  resaltado (rotulador); con class="mk-verde",
#                      "mk-azul" o "mk-rosa" cambia el color
#      <span class="fs-l">…</span>   tamaño de letra (fs-xs, fs-s, fs-m,
#                                    fs-l, fs-xl, fs-xxl)
#      <span class="al-j">…</span>   párrafo JUSTIFICADO (ajustado al ancho
#                                    de la línea). Sin esta etiqueta el
#                                    párrafo va alineado a la izquierda.
#      <span class="sg-1">…</span>   párrafo con SANGRÍA (sg-1, sg-2, sg-3:
#                                    cada nivel, más hacia dentro)
#      <span class="ff-mono">…</span> tipografía (ff-sans, ff-titulo, ff-mono,
#                                    ff-mano)
#
#  Los saltos de línea (Enter) se respetan: cada Enter es un salto de
#  párrafo en la página. En la narración de los hechos cada línea pasa a
#  ser un párrafo con su separación; en el resto de cuadros (pregunta,
#  respuestas, motivación, consejo, hitos) es un salto de línea.
#
#  Para no tener que escribirlas a mano, cada cuadro de texto lleva
#  encima una barra de botones que envuelve lo que esté seleccionado, y
#  el propio cuadro pinta el resultado a la vista (la negrita se ve en
#  negrita, el resaltado con su color…) dejando las etiquetas en gris
#  claro para que se sigan pudiendo tocar a mano.
# ══════════════════════════════════════════════════════════════════════

# Colores de rotulador: clase HTML → (color en la página, color en el editor)
RESALTADOS = [
    ("",          "Amarillo", "#ffe9a8"),
    ("mk-verde",  "Verde",    "#c9f0d2"),
    ("mk-azul",   "Azul",     "#cfe4fb"),
    ("mk-rosa",   "Rosa",     "#fbd0e2"),
]

# Tamaños de letra: clase HTML → (nombre visible, tamaño en el editor)
TAMANOS = [
    ("fs-xs",  "Muy pequeña",  8),
    ("fs-s",   "Pequeña",      9),
    ("fs-m",   "Normal",      10),
    ("fs-l",   "Grande",      12),
    ("fs-xl",  "Muy grande",  14),
    ("fs-xxl", "Enorme",      17),
]

_COLOR_RESALTADO = {clave: color for clave, _n, color in RESALTADOS}
_TAM_EDITOR = {clave: tam for clave, _n, tam in TAMANOS}

# Tipografías: clase HTML → (nombre visible, fuente con la que se pinta en el
# editor, que es una aproximación: en la página salen las reales).
FUENTES = [
    ("ff-sans",   "Sans-serif (limpia)",          "Segoe UI"),
    ("ff-titulo", "Elegante (Playfair Display)",  "Palatino Linotype"),
    ("ff-mono",   "Máquina de escribir (mono)",   "Consolas"),
    ("ff-mano",   "Manuscrita (Caveat)",          "Segoe Script"),
]
_FUENTE_EDITOR = {clave: fam for clave, _n, fam in FUENTES}

# Clases que afectan a un PÁRRAFO entero (no a un trozo de línea)
CLASES_PARRAFO = {"al-j", "sg-1", "sg-2", "sg-3"}
SANGRIA_PX = 26          # sangría por nivel en el editor

# Cualquier etiqueta HTML del texto (de apertura o de cierre).
RE_ETIQUETA_HTML = re.compile(r"</?\s*([a-zA-Z][a-zA-Z0-9]*)\b[^<>]*>")
RE_CLASE_HTML = re.compile(r"""class\s*=\s*["']([^"']*)["']""", re.I)

# Etiquetas que el editor sabe pintar y qué cambian del aspecto.
_EFECTO_ETIQUETA = {
    "b": "negrita", "strong": "negrita",
    "i": "cursiva", "em": "cursiva",
    "u": "subrayado",
    "s": "tachado", "del": "tachado", "strike": "tachado",
}

# Etiquetas que el editor sigue de apertura a cierre. <span> entra en la
# lista aunque no todos los <span> sean de formato: se apila igualmente
# (con estilo None) para que cada </span> cierre el suyo y no el de otro.
ETIQUETAS_FORMATO = set(_EFECTO_ETIQUETA) | {"mark", "span"}

FUENTE_CAJA = ("Georgia", 10)


def _estilo_de_etiqueta(nombre, atributos):
    """Qué cambia esta etiqueta de apertura. None si el editor no la pinta."""
    efecto = _EFECTO_ETIQUETA.get(nombre)
    if efecto:
        return (efecto, True)
    clases = ""
    m = RE_CLASE_HTML.search(atributos or "")
    if m:
        clases = m.group(1).lower()
    if nombre == "mark":
        clave = next((c for c in _COLOR_RESALTADO if c and c in clases.split()), "")
        return ("resaltado", clave)
    if nombre == "span":
        lista = clases.split()
        if any(c in CLASES_PARRAFO for c in lista):
            return ("parrafo", True)
        for clave in lista:
            if clave in _FUENTE_EDITOR:
                return ("fuente", clave)
        for clave in lista:
            if clave in _TAM_EDITOR:
                return ("tamano", clave)
    return None


def _etiqueta_compuesta(widget, estilo):
    """Devuelve (creándola si hace falta) la etiqueta de tkinter que pinta
    esa combinación de efectos. Se hace una sola por combinación para que
    negrita + cursiva + tamaño puedan verse a la vez."""
    negrita, cursiva, subrayado, tachado, tamano, resaltado, fuente = estilo
    nombre = "fmt_%s" % "_".join(
        str(x) for x in (int(negrita), int(cursiva), int(subrayado), int(tachado),
                         tamano or "-", resaltado if resaltado is not None else "-", fuente or "-"))
    if nombre in widget.tag_names():
        return nombre
    fuente = tkfont.Font(
        family=_FUENTE_EDITOR.get(fuente, FUENTE_CAJA[0]),
        size=_TAM_EDITOR.get(tamano, FUENTE_CAJA[1]),
        weight="bold" if negrita else "normal",
        slant="italic" if cursiva else "roman",
        underline=1 if subrayado else 0,
        overstrike=1 if tachado else 0)
    # La fuente hay que guardarla: si se la lleva el recolector de basura,
    # tkinter se queda sin ella y el cuadro deja de pintarse.
    widget._fuentes_formato.append(fuente)
    widget.tag_configure(nombre, font=fuente)
    if resaltado is not None:
        widget.tag_configure(nombre, background=_COLOR_RESALTADO.get(resaltado, "#ffe9a8"),
                             foreground="#111827")
    return nombre


def repintar_formato(widget):
    """Pinta el cuadro de texto como se verá en la página: lee las
    etiquetas HTML del contenido y aplica el aspecto a lo que envuelven."""
    if not getattr(widget, "_formato", False):
        return
    for etq in widget.tag_names():
        if etq.startswith("fmt_") or etq == "fmt_etiqueta":
            widget.tag_remove(etq, "1.0", "end")
    contenido = widget.get("1.0", "end-1c")

    def indice(n):
        return "1.0 + %d chars" % n

    def pintar(desde, hasta, pila):
        if hasta <= desde:
            return
        negrita = cursiva = subrayado = tachado = False
        tamano = None
        resaltado = None
        fuente = None
        for _nombre, estilo in pila:
            if not estilo:
                continue
            efecto, valor = estilo
            if efecto == "negrita":     negrita = True
            elif efecto == "cursiva":   cursiva = True
            elif efecto == "subrayado": subrayado = True
            elif efecto == "tachado":   tachado = True
            elif efecto == "tamano":    tamano = valor
            elif efecto == "resaltado": resaltado = valor
            elif efecto == "fuente":    fuente = valor
        if not (negrita or cursiva or subrayado or tachado or tamano or fuente
                or resaltado is not None):
            return
        etq = _etiqueta_compuesta(
            widget, (negrita, cursiva, subrayado, tachado, tamano, resaltado, fuente))
        widget.tag_add(etq, indice(desde), indice(hasta))

    pila = []
    pos = 0
    for m in RE_ETIQUETA_HTML.finditer(contenido):
        ini, fin = m.span()
        pintar(pos, ini, pila)
        widget.tag_add("fmt_etiqueta", indice(ini), indice(fin))
        nombre = m.group(1).lower()
        entero = m.group(0)
        if nombre in ETIQUETAS_FORMATO:
            if entero.startswith("</"):
                for k in range(len(pila) - 1, -1, -1):
                    if pila[k][0] == nombre:
                        pila.pop(k)
                        break
            elif not entero.endswith("/>"):
                pila.append((nombre, _estilo_de_etiqueta(nombre, entero)))
        pos = fin
    pintar(pos, len(contenido), pila)

    # Párrafos justificados o con sangría: se marcan líneas enteras. Tk no
    # sabe justificar, así que lo justificado se ve con fondo azulado; la
    # sangría sí se ve de verdad.
    for n, linea in enumerate(contenido.split("\n"), 1):
        env = envoltorio_parrafo(linea)
        if not env:
            continue
        clases = env[0]
        a, b = "%d.0" % n, "%d.end" % n
        if "al-j" in clases:
            widget.tag_add("fmt_just", a, b)
        nivel = nivel_sangria(clases)
        if nivel:
            widget.tag_add("fmt_sg%d" % nivel, a, b)
    # Las etiquetas, siempre en gris por encima de todo lo demás.
    widget.tag_raise("fmt_etiqueta")


def _repintar_luego(widget):
    """Repinta sin atascar la escritura: se espera a que el dedo levante."""
    pendiente = getattr(widget, "_repintado_pendiente", None)
    if pendiente:
        try:
            widget.after_cancel(pendiente)
        except tk.TclError:
            pass
    widget._repintado_pendiente = widget.after(120, lambda: repintar_formato(widget))


def envolver_formato(widget, apertura, cierre):
    """Envuelve lo seleccionado (o deja el cursor dentro de las etiquetas,
    si no hay nada seleccionado)."""
    try:
        ini = widget.index("sel.first")
        fin = widget.index("sel.last")
    except tk.TclError:
        ini = fin = widget.index("insert")
    largo = len(widget.get(ini, fin))
    widget.insert(fin, cierre)
    widget.insert(ini, apertura)
    dentro = widget.index("%s + %d chars" % (ini, len(apertura)))
    if largo:
        widget.tag_remove("sel", "1.0", "end")
        widget.tag_add("sel", dentro, "%s + %d chars" % (dentro, largo))
        widget.mark_set("insert", "%s + %d chars" % (dentro, largo))
    else:
        widget.mark_set("insert", dentro)
    widget.focus_set()
    widget.see("insert")
    repintar_formato(widget)
    widget.event_generate("<<TextoTocado>>")
    return "break"


def quitar_formato(widget):
    """Deja en texto pelado lo seleccionado: le quita todas las etiquetas
    de formato (si no hay nada seleccionado, limpia el cuadro entero)."""
    try:
        ini = widget.index("sel.first")
        fin = widget.index("sel.last")
    except tk.TclError:
        ini, fin = "1.0", "end-1c"
    trozo = widget.get(ini, fin)
    # Se quitan las etiquetas de formato con su cierre; lo que no sea
    # formato (un <br>, un <span> de otra cosa) se queda como estaba.
    pila = []

    def fuera(m):
        nombre = m.group(1).lower()
        entero = m.group(0)
        if nombre not in ETIQUETAS_FORMATO:
            return entero
        if entero.startswith("</"):
            for k in range(len(pila) - 1, -1, -1):
                if pila[k][0] == nombre:
                    era_formato = pila.pop(k)[1]
                    return "" if era_formato else entero
            return entero
        de_formato = bool(_estilo_de_etiqueta(nombre, entero))
        if not entero.endswith("/>"):
            pila.append((nombre, de_formato))
        return "" if de_formato else entero

    limpio = RE_ETIQUETA_HTML.sub(fuera, trozo)
    if limpio == trozo:
        return "break"
    widget.delete(ini, fin)
    widget.insert(ini, limpio)
    repintar_formato(widget)
    widget.event_generate("<<TextoTocado>>")
    return "break"


def nivel_sangria(clases):
    """Nivel de sangría (0-3) que dicen unas clases."""
    return next((n for n in (3, 2, 1) if "sg-%d" % n in clases), 0)


def envoltorio_parrafo(linea):
    """Si TODA la línea está envuelta en un único <span> de párrafo
    (justificado y/o sangría) devuelve (clases, interior); si no, None."""
    cuerpo = linea.rstrip()
    m = re.match(r'^\s*<span class="([^"]*)">', cuerpo)
    if not m or not cuerpo.endswith("</span>"):
        return None
    clases = set(m.group(1).split())
    if not clases or not clases <= CLASES_PARRAFO:
        return None
    prof = 0
    for t in RE_ETIQUETA_HTML.finditer(cuerpo):
        if t.group(1).lower() != "span":
            continue
        if t.group(0).startswith("</"):
            prof -= 1
            if prof == 0 and t.end() != len(cuerpo):
                return None             # el span se cierra antes del final
        elif not t.group(0).endswith("/>"):
            prof += 1
    if prof != 0:
        return None
    return clases, cuerpo[m.end():-len("</span>")]


def formato_parrafos(widget, accion):
    """Justifica, quita el justificado o cambia la sangría de los PÁRRAFOS
    tocados por la selección (cada línea escrita con Enter es un párrafo,
    y se envuelve entera). Sin selección actúa sobre la línea del cursor.

    accion: "just" · "izq" · "mas" (más sangría) · "menos" (menos sangría)."""
    try:
        ini = widget.index("sel.first")
        fin = widget.index("sel.last")
    except tk.TclError:
        ini = fin = widget.index("insert")
    l1, l2 = int(ini.split(".")[0]), int(fin.split(".")[0])
    if l2 > l1 and fin.endswith(".0"):      # la selección acaba al principio de una línea
        l2 -= 1
    for n in range(l1, l2 + 1):
        a, b = "%d.0" % n, "%d.end" % n
        linea = widget.get(a, b)
        if not linea.strip():
            continue
        env = envoltorio_parrafo(linea)
        clases, interior = (set(env[0]), env[1]) if env else (set(), linea.strip())
        nivel = nivel_sangria(clases)
        if accion == "just":
            clases.add("al-j")
        elif accion == "izq":
            clases.discard("al-j")
        elif accion == "mas":
            nivel = min(3, nivel + 1)
        elif accion == "menos":
            nivel = max(0, nivel - 1)
        clases -= {"sg-1", "sg-2", "sg-3"}
        if nivel:
            clases.add("sg-%d" % nivel)
        if clases:
            orden = [c for c in ("al-j", "sg-1", "sg-2", "sg-3") if c in clases]
            nueva = '<span class="%s">%s</span>' % (" ".join(orden), interior)
        else:
            nueva = interior
        if nueva != linea:
            widget.delete(a, b)
            widget.insert(a, nueva)
    widget.tag_remove("sel", "1.0", "end")
    widget.tag_add("sel", "%d.0" % l1, "%d.end" % l2)
    widget.focus_set()
    repintar_formato(widget)
    widget.event_generate("<<TextoTocado>>")
    return "break"


def barra_formato(padre, widget, compacta=False):
    """Barra de botones de formato de un cuadro de texto."""
    barra = ttk.Frame(padre, style="Panel.TFrame")
    fuente = ("Segoe UI", 8 if compacta else 9)
    ancho = 3 if compacta else 4

    def boton(texto, orden, ayuda, ancho_b=None, **kw):
        b = tk.Button(barra, text=texto, command=orden, relief="groove",
                      background="#efe6da", foreground="#3b2f26",
                      padx=2, pady=0, width=ancho_b or ancho, cursor="hand2", **kw)
        b.pack(side="left", padx=1)
        _consejo(b, ayuda)
        return b

    boton("N", lambda: envolver_formato(widget, "<b>", "</b>"),
          "Negrita  ·  <b>…</b>  ·  Ctrl+B",
          font=(fuente[0], fuente[1], "bold"))
    boton("K", lambda: envolver_formato(widget, "<i>", "</i>"),
          "Cursiva  ·  <i>…</i>  ·  Ctrl+I",
          font=(fuente[0], fuente[1], "italic"))
    boton("S", lambda: envolver_formato(widget, "<u>", "</u>"),
          "Subrayado  ·  <u>…</u>  ·  Ctrl+U",
          font=(fuente[0], fuente[1], "underline"))
    boton("ab", lambda: envolver_formato(widget, "<s>", "</s>"),
          "Tachado  ·  <s>…</s>  ·  Ctrl+T",
          font=(fuente[0], fuente[1], "overstrike"))

    # Resaltado: botón directo (amarillo) con menú de colores al lado.
    boton("🖍", lambda: envolver_formato(widget, "<mark>", "</mark>"),
          "Resaltar en amarillo  ·  <mark>…</mark>  ·  Ctrl+R", font=fuente)
    menu_color = tk.Menubutton(barra, text="▾", relief="groove", font=fuente,
                               background="#efe6da", foreground="#3b2f26",
                               padx=2, pady=0, cursor="hand2")
    menu_color.pack(side="left", padx=(0, 4))
    m1 = tk.Menu(menu_color, tearoff=0)
    for clave, nombre, color in RESALTADOS:
        etq = ' class="%s"' % clave if clave else ""
        m1.add_command(label="  %s  " % nombre, background=color, foreground="#111827",
                       command=lambda e=etq: envolver_formato(
                           widget, "<mark%s>" % e, "</mark>"))
    menu_color.configure(menu=m1)
    _consejo(menu_color, "Color del rotulador")

    menu_tam = tk.Menubutton(barra, text="Aa ▾", relief="groove", font=fuente,
                             background="#efe6da", foreground="#3b2f26",
                             padx=4, pady=0, cursor="hand2")
    menu_tam.pack(side="left", padx=(0, 4))
    m2 = tk.Menu(menu_tam, tearoff=0)
    for clave, nombre, tam in TAMANOS:
        m2.add_command(label="%s  (%s)" % (nombre, clave),
                       font=(FUENTE_CAJA[0], tam),
                       command=lambda c=clave: envolver_formato(
                           widget, '<span class="%s">' % c, "</span>"))
    menu_tam.configure(menu=m2)
    _consejo(menu_tam, "Tamaño de la letra  ·  <span class=\"fs-…\">…</span>")

    menu_fuente = tk.Menubutton(barra, text="Fuente ▾", relief="groove", font=fuente,
                                background="#efe6da", foreground="#3b2f26",
                                padx=4, pady=0, cursor="hand2")
    menu_fuente.pack(side="left", padx=(0, 4))
    m3 = tk.Menu(menu_fuente, tearoff=0)
    for clave, nombre, familia in FUENTES:
        m3.add_command(label="  %s  " % nombre, font=(familia, 10),
                       command=lambda c=clave: envolver_formato(
                           widget, '<span class="%s">' % c, "</span>"))
    menu_fuente.configure(menu=m3)
    _consejo(menu_fuente, "Tipografía  ·  <span class=\"ff-…\">…</span>")

    # Párrafo: «Izq.» es como se ve por defecto; «Just.» ajusta el párrafo al
    # ancho de la línea; «Sang+/Sang-» lo meten más o menos hacia dentro.
    boton("Izq.", lambda: formato_parrafos(widget, "izq"),
          "Quitar el justificado (alinear a la izquierda, como está por defecto)  ·  Ctrl+L",
          ancho_b=5, font=fuente)
    boton("Just.", lambda: formato_parrafos(widget, "just"),
          "Justificar: ajustar al ancho de la línea el párrafo  ·  "
          "<span class=\"al-j\">…</span>  ·  Ctrl+J",
          ancho_b=5, font=fuente)
    boton("Sang+", lambda: formato_parrafos(widget, "mas"),
          "Más sangría: mete el párrafo más hacia dentro (hasta 3 niveles)  ·  "
          "<span class=\"sg-1\">…</span>  ·  Tab",
          ancho_b=5, font=fuente)
    boton("Sang-", lambda: formato_parrafos(widget, "menos"),
          "Menos sangría: lo saca un nivel hacia fuera  ·  Mayús+Tab",
          ancho_b=5, font=fuente)
    boton("✕", lambda: quitar_formato(widget),
          "Quitar el formato de lo seleccionado", font=fuente)
    return barra


def _consejo(widget, texto):
    """Globo de ayuda amarillo al pasar el ratón por encima."""
    estado = {"ventana": None}

    def mostrar(_e=None):
        if estado["ventana"] or not texto:
            return
        v = tk.Toplevel(widget)
        v.wm_overrideredirect(True)
        v.wm_geometry("+%d+%d" % (widget.winfo_rootx() + 6,
                                  widget.winfo_rooty() + widget.winfo_height() + 4))
        tk.Label(v, text=texto, background="#fff8dc", foreground="#3b2f26",
                 relief="solid", borderwidth=1, font=("Segoe UI", 8),
                 padx=6, pady=2).pack()
        estado["ventana"] = v

    def ocultar(_e=None):
        if estado["ventana"]:
            estado["ventana"].destroy()
            estado["ventana"] = None

    widget.bind("<Enter>", mostrar, add="+")
    widget.bind("<Leave>", ocultar, add="+")
    widget.bind("<ButtonPress>", ocultar, add="+")


def caja_texto(padre, alto=4, ancho=90, formato=True):
    """Cuadro de texto multilínea con su barra de desplazamiento y, salvo
    que se pida lo contrario (formato=False), con su barra de botones de
    formato encima."""
    marco = ttk.Frame(padre, style="Panel.TFrame")
    cuerpo = ttk.Frame(marco, style="Panel.TFrame")
    texto = tk.Text(cuerpo, height=alto, width=ancho, wrap="word",
                    font=FUENTE_CAJA, relief="solid", borderwidth=1,
                    background="white", foreground="#111827",
                    insertbackground="#111827", padx=6, pady=4)
    barra = ttk.Scrollbar(cuerpo, orient="vertical", command=texto.yview)
    texto.configure(yscrollcommand=barra.set)

    if formato:
        texto._formato = True
        texto._fuentes_formato = []
        texto.tag_configure("fmt_just", background="#e6eefb")
        for nivel in (1, 2, 3):
            texto.tag_configure("fmt_sg%d" % nivel, lmargin1=SANGRIA_PX * nivel,
                                lmargin2=SANGRIA_PX * nivel)
        texto.tag_configure("fmt_etiqueta", foreground="#b3aaa0")
        barra_formato(marco, texto, compacta=(alto <= 3)).pack(fill="x", pady=(0, 2))
        texto.bind("<KeyRelease>", lambda e: _repintar_luego(texto), add="+")
        texto.bind("<<Paste>>", lambda e: _repintar_luego(texto), add="+")
        atajos = [("b", "<b>", "</b>"), ("i", "<i>", "</i>"),
                  ("u", "<u>", "</u>"), ("t", "<s>", "</s>"),
                  ("r", "<mark>", "</mark>")]
        for tecla, ap, ci in atajos:
            for pulsacion in ("<Control-%s>" % tecla, "<Control-%s>" % tecla.upper()):
                texto.bind(pulsacion,
                           lambda e, a=ap, c=ci: envolver_formato(e.widget, a, c))
        for tecla, accion in (("j", "just"), ("l", "izq")):
            for pulsacion in ("<Control-%s>" % tecla, "<Control-%s>" % tecla.upper()):
                texto.bind(pulsacion,
                           lambda e, ac=accion: formato_parrafos(e.widget, ac))
        # Tab / Mayús+Tab = más / menos sangría (en HTML un tabulador no
        # se vería, así que la tecla se aprovecha para esto).
        texto.bind("<Tab>", lambda e: formato_parrafos(e.widget, "mas"))
        for ev in ("<Shift-Tab>", "<ISO_Left_Tab>"):
            try:
                texto.bind(ev, lambda e: formato_parrafos(e.widget, "menos"))
            except tk.TclError:
                pass

    cuerpo.pack(fill="both", expand=True)
    texto.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return marco, texto


def poner_texto(widget, valor):
    widget.delete("1.0", "end")
    widget.insert("1.0", "" if valor is None else str(valor))
    repintar_formato(widget)


def sacar_texto(widget):
    return widget.get("1.0", "end-1c")


def limpiar_texto(valor):
    """Limpia un texto SIN perder los saltos de línea (Enter): quita los
    espacios sobrantes de cada línea y las líneas en blanco del principio
    y del final, y no deja más de una línea en blanco seguida."""
    crudo = str(valor or "").replace("\r\n", "\n").replace("\r", "\n")
    lineas = [" ".join(l.split()) for l in crudo.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas).strip("\n"))


def partir_parrafos(valor):
    """Cada línea escrita con Enter pasa a ser un párrafo (las líneas en
    blanco sobran). Si un formato (negrita, justificado…) abarca varias
    líneas, se cierra al final de cada párrafo y se reabre en el siguiente,
    para que ninguna etiqueta quede partida por la mitad."""
    parrafos, abiertas = [], []              # abiertas: [(nombre, etiqueta completa)]
    for linea in str(valor or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        linea = linea.strip()
        prefijo = "".join(ap for _n, ap in abiertas)
        for m in RE_ETIQUETA_HTML.finditer(linea):
            nombre, entero = m.group(1).lower(), m.group(0)
            if nombre not in ETIQUETAS_FORMATO:
                continue
            if entero.startswith("</"):
                for k in range(len(abiertas) - 1, -1, -1):
                    if abiertas[k][0] == nombre:
                        del abiertas[k]
                        break
            elif not entero.endswith("/>"):
                abiertas.append((nombre, entero))
        if not RE_ETIQUETA_HTML.sub("", linea).strip():
            continue                          # línea vacía (o solo etiquetas)
        cierre = "".join("</%s>" % n for n, _ap in reversed(abiertas))
        parrafos.append(prefijo + linea + cierre)
    return parrafos


def nUm(x):
    """Número con coma decimal y sin decimales inútiles: 1.0 → "1"; 0.33 → "0,33"."""
    r = round(float(x), 2)
    entero = int(r)
    return (str(entero) if r == entero else ("%.2f" % r).rstrip("0").rstrip(".")).replace(".", ",")


def resumen(texto, largo=60):
    """Primera línea recortada, para las listas laterales. Las etiquetas de
    formato (<b>, <mark>, <span class="fs-l">…) se quitan: en la lista
    estorban más que ayudan."""
    t = " ".join(RE_ETIQUETA_HTML.sub("", str(texto or "")).split())
    return t if len(t) <= largo else t[:largo - 1] + "…"


# ══════════════════════════════════════════════════════════════════════
#  5. DESCRIPCIÓN DE LOS CAMPOS (rótulo visible + nombre técnico + HTML)
# ══════════════════════════════════════════════════════════════════════

CAMPOS_CONFIG = [
    ("titulo", "Título del supuesto",
     "config.titulo",
     '<title> · <h1 id="inst-title"> · <h1 id="print-title-h1">',
     "Se ve como titular grande de la cabecera, en la pestaña del navegador y en la hoja "
     "de impresión. También es el nombre con el que se envían los resultados."),

    ("referencia", "Referencia / expediente",
     "config.referencia",
     '<span class="meta-pill" id="meta-referencia">',
     "Píldora pequeña de la cabecera (la última de la fila)."),

    ("ambito", "Ámbito / legislación aplicable",
     "config.ambito",
     '<span class="meta-pill" id="meta-legislacion"> · <p id="print-title-sub">',
     "Píldora de la cabecera con la normativa vigente y subtítulo de la hoja impresa."),

    ("minutos", "Tiempo por defecto (minutos)",
     "config.minutos",
     '<span class="meta-pill" id="meta-minutos"> · <span id="timer-display">',
     "Píldora «N MINUTOS» y tiempo con el que arranca el cronómetro. "
     "El alumno puede cambiarlo luego desde el panel ⚙ de la página."),

    ("logo", "Imagen del encabezado (logotipo)",
     "config.logo",
     '<img id="inst-logo" class="logo-img">',
     "Dirección de la imagen que corona la cabecera. Puede ser una dirección de "
     "internet o un archivo de la propia carpeta (por ejemplo «img/logo.png»). "
     "Si se deja vacía, no se muestra ninguna imagen."),

    ("logoAlt", "Texto alternativo de la imagen",
     "config.logoAlt",
     '<img id="inst-logo" alt="…">',
     "Lo que se lee si la imagen no carga, y lo que dicta un lector de pantalla."),

    ("organismo", "Línea del organismo",
     "config.organismo",
     '<div class="organismo" id="inst-organismo">',
     "Línea pequeña en mayúsculas que va justo encima del título, bajo el logotipo. "
     "Si se deja vacía, no se muestra."),

    ("aptoPorcentaje", "Porcentaje de puntos para ser APTO",
     "config.aptoPorcentaje",
     '<div class="score-verdict">',
     "Sobre la puntuación máxima del examen (sumando todos los bloques). Si el "
     "resultado llega a ese porcentaje, el marcador dice APTO; si no, NO APTO."),
]

CAMPOS_BLOQUE = [
    ("id", "Identificador interno del bloque",
     "bloques[].id",
     '.nav-box.blq-XX  ·  <div class="block-header" id="bhdr-XX">',
     "NO se ve en la página. Es el código (B1, B2…) con el que cada pregunta se "
     "asigna a este bloque."),

    ("titulo", "Nombre del bloque",
     "bloques[].titulo",
     '<span class="nav-group-label">  ·  <div class="block-header"> → <h3>',
     "Se ve arriba, delante de las casillas de este bloque, y en la barra que "
     "encabeza sus preguntas."),
]

CAMPOS_ENUNCIADO = [
    ("id", "Identificador interno del enunciado",
     "enunciados[].id",
     '<section class="statement" id="stmt-XX">',
     "NO se ve en la página. Es el código (E1, E2…) con el que cada pregunta se "
     "engancha a este bloque de hechos."),

    ("number", "Número de la insignia",
     "enunciados[].number",
     '<div class="exp-number">',
     "Cuadro con el número que aparece a la izquierda del título del expediente."),

    ("title", "Título del expediente",
     "enunciados[].title",
     '<div class="statement-title-block"> → <h2>',
     "Titular del bloque de hechos, encima de la narración."),

    ("ref", "Código de referencia del expediente",
     "enunciados[].ref",
     '<span class="ref"> → «REF: …»',
     "Línea pequeña bajo el título del expediente."),

    ("ambito", "Materias que abarca",
     "enunciados[].ambito",
     '<span class="ref"> → «· ÁMBITO: …»',
     "Continuación de esa misma línea pequeña."),
]


# ══════════════════════════════════════════════════════════════════════
#  6. VENTANA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

AUTOGUARDADO_MS = 120000          # copia de recuperación cada 2 minutos si hay cambios
PREFS = Path(__file__).resolve().parent.parent / ".editor_prefs.json"


def _leer_prefs():
    try:
        return json.loads(PREFS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _guardar_prefs(prefs):
    try:
        PREFS.write_text(json.dumps(prefs, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass                              # carpeta de solo lectura: no pasa nada

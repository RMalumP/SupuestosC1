# -*- coding: utf-8 -*-
"""
════════════════════════════════════════════════════════════════════════
 EDITOR DE SUPUESTOS  —  interfaz gráfica para la plantilla HTML
════════════════════════════════════════════════════════════════════════
 Qué hace:
   Abre en local un archivo de plantilla de supuesto (.html), muestra
   TODOS los campos editables en cuadros de texto (título, duración,
   bloques de hechos, hechos desencadenantes, línea de tiempo,
   preguntas, sus 4 respuestas marcando la correcta, la motivación
   legal y el consejo) y vuelve a guardarlos dentro del HTML.

 Cómo se ejecuta:
   Abrir este archivo con Thonny y pulsar F5 (Ejecutar).

 Librerías necesarias:
   NINGUNA instalación. Solo usa la biblioteca estándar de Python:
   tkinter, json, re, os, pathlib, webbrowser, unicodedata.
   (En Windows y macOS, tkinter viene incluido con Python/Thonny.
    En Linux, si diera error, instalar el paquete del sistema
    "python3-tk":  sudo apt install python3-tk)

 Cada campo de la ventana está rotulado por partida doble:
   · el nombre con el que se ve en la página publicada
   · el nombre técnico del campo y el elemento HTML donde acaba
════════════════════════════════════════════════════════════════════════
"""

import json
import os
import re
import sys
import webbrowser
from pathlib import Path

# Los módulos del editor (menu_datos, datos_html, alta_menu…) están junto a este archivo.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Modos sin ventana (se deciden antes de cargar tkinter). El lanzador es siempre este archivo:
#   --alta [--auto]      da de alta en el menú los supuestos que falten        (alta_menu.py)
#   --actualizar         pone todo al día y prepara la carpeta PARA_SUBIR      (sincronizar_local.py)
#   --para-subir         solo prepara la carpeta PARA_SUBIR
#   --subido             marca lo actual como ya subido a GitHub
if __name__ == "__main__":
    if "--alta" in sys.argv:
        import alta_menu
        sys.exit(alta_menu.main([a for a in sys.argv[1:] if a != "--alta"]))
    if any(a in sys.argv for a in ("--actualizar", "--para-subir", "--subido")):
        import sincronizar_local
        sys.exit(sincronizar_local.main(sys.argv[1:]))

import menu_datos            # lista del menú
import sincronizar_local     # poner al día y carpeta PARA_SUBIR
import ventana_subir         # ventana «Para subir a GitHub»
import ventana_menu          # ventana «Menú de inicio»
import normas_enlaces        # normas que se enlazan al BOE (datos/normas-datos.js)
import herramientas_datos as herr   # deshacer, buscar, importar, autoguardado (sin ventana)
import ventana_herramientas      # ventanas «Buscar y reemplazar» e «Importar preguntas»

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


class EditorApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(APP_TITULO)
        self._prefs = _leer_prefs()
        geo = self._prefs.get("geometria")
        self.geometry(geo if isinstance(geo, str) and re.fullmatch(r"\d+x\d+([+-]-?\d+){2}", geo)
                      else "1240x840")
        self.minsize(1000, 640)
        self.configure(bg=C_FONDO)
        self._estilos()

        self.ruta = None                 # archivo abierto (None = aún sin guardar)
        self.html_base = ""              # HTML completo del archivo abierto
        self.modo = "json"
        self.datos = datos_vacios()
        self.hay_cambios = False
        self._destinos_menu = None      # sitios del menú (los rellena _alta_en_menu)
        self._silencio = False           # evita reentradas al repintar listas

        self.i_sec = None
        self.i_enun = None
        self.i_bloque = None
        self.i_hito = None
        self.i_preg = None

        self.historial = herr.Historial()
        self._barra_superior()
        self._menu_principal()

        self.cuaderno = ttk.Notebook(self)
        self.cuaderno.pack(fill="both", expand=True, padx=10, pady=(6, 4))
        self._pestana_general()
        self._pestana_bloques()
        self._pestana_enunciados()
        self._pestana_preguntas()
        self._pestana_botones()
        self._pestana_comprobar()
        self._pestana_normas()

        self._barra_estado()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        self.bind_all("<Control-s>", lambda e: self.guardar())
        self.bind_all("<Control-o>", lambda e: self.abrir())
        self.bind_all("<Control-n>", lambda e: self.nuevo())
        self.bind_all("<Control-S>", lambda e: self.guardar_como())
        self.bind_all("<Control-f>", lambda e: ventana_herramientas.buscar_reemplazar(self))
        self.bind_all("<F5>", lambda e: self.ver_navegador())
        self.bind_all("<Control-z>", lambda e: self._atajo_historial(self.deshacer, e))
        self.bind_all("<Control-y>", lambda e: self._atajo_historial(self.rehacer, e))
        self.bind_all("<Control-Z>", lambda e: self._atajo_historial(self.rehacer, e))
        self.bind_all("<Alt-Up>", lambda e: self._mover_con_atajo(-1))
        self.bind_all("<Alt-Down>", lambda e: self._mover_con_atajo(1))
        self.after(AUTOGUARDADO_MS, self._autoguardar)

        self.after(200, self._carga_inicial)

    # ─────────────────────────────────────────────────────────────
    #  Estilos
    # ─────────────────────────────────────────────────────────────
    def _estilos(self):
        est = ttk.Style(self)
        try:
            est.theme_use("clam")
        except tk.TclError:
            pass
        est.configure("TFrame", background=C_FONDO)
        est.configure("Panel.TFrame", background=C_FONDO)
        est.configure("TLabel", background=C_FONDO, foreground=C_TINTA)
        est.configure("TLabelframe", background=C_FONDO, foreground=C_TINTA)
        est.configure("TLabelframe.Label", background=C_FONDO, foreground=C_ROJO,
                      font=("Georgia", 10, "bold"))
        est.configure("TNotebook", background=C_FONDO)
        est.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(14, 7),
                      background="#e2d6c8", foreground="#6b5344")
        est.map("TNotebook.Tab",
                background=[("selected", C_PANEL)],
                foreground=[("selected", C_ROJO)],
                expand=[("selected", (1, 1, 1, 0))])
        est.configure("Campo.TLabel", font=("Segoe UI", 10, "bold"), foreground=C_TINTA)
        est.configure("Tec.TLabel", font=("Consolas", 8), foreground=C_TEC)
        est.configure("Ayuda.TLabel", font=("Segoe UI", 8, "italic"), foreground=C_AYUDA)
        est.configure("Titulo.TLabel", font=("Georgia", 13, "bold"), foreground=C_ROJO)
        est.configure("Estado.TLabel", font=("Segoe UI", 9), foreground=C_TINTA)
        est.configure("TButton", font=("Segoe UI", 9))
        est.configure("Accion.TButton", font=("Segoe UI", 9, "bold"))

    # ─────────────────────────────────────────────────────────────
    #  Barra de botones superior
    # ─────────────────────────────────────────────────────────────
    def _barra_superior(self):
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Button(barra, text="📂  Abrir plantilla…", command=self.abrir,
                   style="Accion.TButton").pack(side="left")
        ttk.Button(barra, text="🆕  Nuevo supuesto", command=self.nuevo).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(barra, text="💾  Guardar", command=self.guardar,
                   style="Accion.TButton").pack(side="left")
        ttk.Button(barra, text="💾  Guardar como…", command=self.guardar_como).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(barra, text="🌐  Ver en el navegador", command=self.ver_navegador).pack(side="left")
        ttk.Button(barra, text="✔  Comprobar", command=self.comprobar).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(barra, text="🗂  Menú de inicio…",
                   command=lambda: ventana_menu.abrir(self)).pack(side="left", padx=(0, 6))
        ttk.Button(barra, text="📦  Para subir…",
                   command=lambda: ventana_subir.abrir(self)).pack(side="left")

        self.lbl_archivo = ttk.Label(barra, text="(ningún archivo abierto)",
                                     style="Tec.TLabel")
        self.lbl_archivo.pack(side="right")

    # ─────────────────────────────────────────────────────────────
    #  Menús, deshacer/rehacer y autoguardado
    # ─────────────────────────────────────────────────────────────
    def _menu_principal(self):
        barra = tk.Menu(self)
        archivo = tk.Menu(barra, tearoff=False)
        archivo.add_command(label="Nuevo supuesto", accelerator="Ctrl+N", command=self.nuevo)
        archivo.add_command(label="Abrir…", accelerator="Ctrl+O", command=self.abrir)
        archivo.add_command(label="Guardar", accelerator="Ctrl+S", command=self.guardar)
        archivo.add_command(label="Guardar como…", accelerator="Ctrl+Mayús+S", command=self.guardar_como)
        archivo.add_separator()
        archivo.add_command(label="Pasar a plantilla nueva…", command=self.convertir_a_plantilla_nueva)
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self._al_cerrar)
        barra.add_cascade(label="Archivo", menu=archivo)
        edicion = tk.Menu(barra, tearoff=False)
        edicion.add_command(label="Deshacer cambio de estructura", accelerator="Ctrl+Z", command=self.deshacer)
        edicion.add_command(label="Rehacer", accelerator="Ctrl+Y", command=self.rehacer)
        edicion.add_separator()
        edicion.add_command(label="Buscar y reemplazar…", accelerator="Ctrl+F",
                            command=lambda: ventana_herramientas.buscar_reemplazar(self))
        edicion.add_command(label="Importar preguntas…",
                            command=lambda: ventana_herramientas.importar(self))
        edicion.add_separator()
        edicion.add_command(label="Subir pregunta", accelerator="Alt+↑", command=lambda: self._mover_con_atajo(-1))
        edicion.add_command(label="Bajar pregunta", accelerator="Alt+↓", command=lambda: self._mover_con_atajo(1))
        barra.add_cascade(label="Edición", menu=edicion)
        herram = tk.Menu(barra, tearoff=False)
        herram.add_command(label="Ver en el navegador", accelerator="F5", command=self.ver_navegador)
        herram.add_command(label="Comprobar", command=self.comprobar)
        herram.add_separator()
        herram.add_command(label="Menú de inicio…", command=lambda: ventana_menu.abrir(self))
        herram.add_command(label="Para subir a GitHub…", command=lambda: ventana_subir.abrir(self))
        barra.add_cascade(label="Herramientas", menu=herram)
        self.config(menu=barra)

    def _instantanea(self):
        """Pasa lo escrito en la ventana a los datos sin reordenar nada."""
        for volcar in (self.volcar_config, self.volcar_botones, self.volcar_seccion,
                       self.volcar_enunciado, self.volcar_pregunta):
            try:
                volcar()
            except (ValueError, tk.TclError):
                pass

    def anotar_historial(self):
        self._instantanea()
        self.historial.anotar(self.datos)

    def _anotar_luego(self):
        if getattr(self, "_anotar_pendiente", None):
            self.after_cancel(self._anotar_pendiente)
        self._anotar_pendiente = self.after(1500, self._anotar_ya)

    def _anotar_ya(self):
        self._anotar_pendiente = None
        self.anotar_historial()

    def _atajo_historial(self, accion, evento):
        # En un cuadro de texto, Ctrl+Z deshace SU escritura; fuera, la estructura.
        if evento.widget.winfo_class() in ("Text", "Entry", "TEntry", "TSpinbox", "TCombobox"):
            return None
        accion()
        return "break"

    def deshacer(self):
        self._instantanea()
        previo = self.historial.deshacer(self.datos)
        if previo is None:
            self.estado("No hay nada que deshacer.")
            return
        self._poner_datos(previo)
        self.estado("Deshecho.")

    def rehacer(self):
        previo = self.historial.rehacer()
        if previo is None:
            self.estado("No hay nada que rehacer.")
            return
        self._poner_datos(previo)
        self.estado("Rehecho.")

    def _poner_datos(self, datos):
        i = self.i_preg
        self.datos = datos
        self._refrescar_todo(reiniciar=False)
        if i is not None and self.datos["preguntas"]:
            self.refrescar_lista_preg(min(i, len(self.datos["preguntas"]) - 1))
        self.hay_cambios = True
        self._pintar_titulo()

    def recargar_tras_cambio(self):
        """Tras un cambio hecho desde otra ventana (buscar, importar)."""
        self._poner_datos(self.datos)
        self.historial.anotar(self.datos)

    def ir_a_pregunta(self, n):
        if n is None or not (0 <= n < len(self.datos["preguntas"])):
            return
        self.volcar_pregunta()
        self.refrescar_lista_preg(n)
        self.cuaderno.select(3)

    def _mover_con_atajo(self, paso):
        if self.cuaderno.index("current") == 3:
            self.mover_pregunta(paso)
        return "break"

    def _ir_desde_informe(self, evento):
        """Doble clic en una línea «Pregunta N: …» del informe salta a esa pregunta."""
        linea = self.txt_informe.get("current linestart", "current lineend")
        m = re.search(r"Pregunta (\d+)", linea)
        if m:
            self.ir_a_pregunta(int(m.group(1)) - 1)

    def _ruta_recuperacion(self):
        return herr.ruta_recuperacion(self.ruta, PREFS.parent)

    def _autoguardar(self):
        if self.hay_cambios:
            self._instantanea()
            herr.guardar_recuperacion(self._ruta_recuperacion(), self.datos)
        self.after(AUTOGUARDADO_MS, self._autoguardar)

    def _borrar_recuperacion(self):
        try:
            self._ruta_recuperacion().unlink()
        except OSError:
            pass

    def _ofrecer_recuperacion(self):
        rec = self._ruta_recuperacion()
        try:
            if not rec.is_file() or (self.ruta and rec.stat().st_mtime <= self.ruta.stat().st_mtime):
                return
        except OSError:
            return
        if messagebox.askyesno(
                "Recuperar trabajo",
                "Hay una copia de recuperación MÁS NUEVA que el archivo (el programa se cerró "
                "sin guardar).\n\n¿Cargarla? (Si dices que no, se borra.)", parent=self):
            datos = herr.leer_recuperacion(rec)
            if datos:
                self._poner_datos(normalizar(datos))
                self.estado("Recuperado el trabajo sin guardar. Revisa y pulsa Guardar.")
                return
        self._borrar_recuperacion()

    def _barra_estado(self):
        marco = ttk.Frame(self)
        marco.pack(fill="x", padx=10, pady=(0, 8))
        self.lbl_estado = ttk.Label(marco, text="Listo.", style="Estado.TLabel")
        self.lbl_estado.pack(side="left")
        self.lbl_contadores = ttk.Label(marco, text="", style="Tec.TLabel")
        self.lbl_contadores.pack(side="right")

    def estado(self, texto):
        self.lbl_estado.config(text=texto)

    def _tocado(self, *_a):
        self.hay_cambios = True
        self._pintar_titulo()
        self._anotar_luego()

    def _pintar_titulo(self):
        # Se llama en cada pulsación: se junta en un solo repintado.
        if getattr(self, "_titulo_pendiente", None):
            return
        self._titulo_pendiente = self.after(150, self._pintar_titulo_ya)

    def _pintar_titulo_ya(self):
        self._titulo_pendiente = None
        nombre = self.ruta.name if self.ruta else "sin guardar"
        self.title("%s — %s%s" % (APP_TITULO, nombre, " *" if self.hay_cambios else ""))
        if hasattr(self, "lbl_archivo"):
            self.lbl_archivo.config(text=str(self.ruta) if self.ruta else "(sin guardar)")
        if hasattr(self, "lbl_contadores"):
            self.lbl_contadores.config(
                text="bloques: %d    ·    enunciados: %d    ·    preguntas: %d"
                     % (len(self.datos["bloques"]), len(self.datos["enunciados"]),
                        len(self.datos["preguntas"])))

    def _vigilar(self, *widgets):
        for w in widgets:
            w.bind("<KeyRelease>", self._tocado, add="+")
            # Los botones de formato no pasan por el teclado: avisan con
            # su propio evento para que el archivo se marque como tocado.
            w.bind("<<TextoTocado>>", self._tocado, add="+")

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 1 — DATOS GENERALES
    # ═════════════════════════════════════════════════════════════
    def _pestana_general(self):
        cont = MarcoScroll(self.cuaderno)
        self.cuaderno.add(cont, text="  1 · Datos generales  ")
        m = cont.interior

        ttk.Label(m, text="Datos generales del examen", style="Titulo.TLabel").pack(
            anchor="w", padx=16, pady=(14, 2))
        ttk.Label(m, style="Ayuda.TLabel", wraplength=880, justify="left",
                  text="Estos cuatro datos rellenan solos la cabecera de la página, la pestaña del "
                       "navegador, la hoja de impresión y el cronómetro. En el archivo HTML viven en "
                       "el apartado «config».").pack(anchor="w", padx=16, pady=(0, 10))

        self.w_cfg = {}
        for clave, visible, tecnico, html, ayuda in CAMPOS_CONFIG:
            caja = ttk.LabelFrame(m, text=" %s " % visible)
            caja.pack(fill="x", padx=16, pady=6)
            rotulo(caja, visible, tecnico, html, ayuda,
                   con_titulo=False).pack(anchor="w", padx=10, pady=(8, 4))
            if clave in ("minutos", "aptoPorcentaje"):
                var = tk.StringVar(value="30" if clave == "minutos" else "50")
                tope = 600 if clave == "minutos" else 100
                sp = ttk.Spinbox(caja, from_=0 if clave == "aptoPorcentaje" else 1,
                                 to=tope, textvariable=var, width=8,
                                 font=("Consolas", 11), command=self._tocado)
                sp.pack(anchor="w", padx=10, pady=(0, 10))
                self._vigilar(sp)
                self.w_cfg[clave] = var
            elif clave == "logo":
                var = tk.StringVar()
                linea = ttk.Frame(caja, style="Panel.TFrame")
                linea.pack(fill="x", padx=10, pady=(0, 10))
                ent = ttk.Entry(linea, textvariable=var, font=("Consolas", 9))
                ent.pack(side="left", fill="x", expand=True)
                self._vigilar(ent)
                ttk.Button(linea, text="📁 Elegir imagen…", command=self.elegir_logo
                           ).pack(side="left", padx=(6, 0))
                ttk.Button(linea, text="↺ La de la plantilla",
                           command=lambda v=var: (v.set(LOGO_POR_DEFECTO), self._tocado())
                           ).pack(side="left", padx=(6, 0))
                self.w_cfg[clave] = var
            else:
                var = tk.StringVar()
                ent = ttk.Entry(caja, textvariable=var, font=("Georgia", 11))
                ent.pack(fill="x", padx=10, pady=(0, 10))
                self._vigilar(ent)
                self.w_cfg[clave] = var

        caja = ttk.LabelFrame(m, text=" Cuántas respuestas salen en cada pregunta ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Respuestas que se muestran", "config.respuestas",
               '<div class="options-grid"> → nº de <div class="option">', con_titulo=False,
               ayuda=
                    "Lo normal son cuatro. Si eliges 3, 4 o 5, todas las preguntas saldrán con "
                    "ese número de respuestas: se muestran siempre la correcta (o las correctas) "
                    "y se sortean los distractores que falten. Eso permite escribir hasta SIETE "
                    "opciones en una pregunta y que cada intento enseñe unas cuantas distintas. "
                    "Una pregunta que tenga menos opciones escritas sale con las que tenga, y en "
                    "la pestaña 4 se puede dar a una pregunta suelta un número propio."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_cfg_respuestas = tk.StringVar()
        self._etiquetas_respuestas = [texto for _valor, texto in RESPUESTAS_EXAMEN]
        combo = ttk.Combobox(caja, textvariable=self.var_cfg_respuestas, state="readonly",
                             font=("Georgia", 10), values=self._etiquetas_respuestas)
        combo.pack(anchor="w", fill="x", padx=10, pady=(0, 10))
        combo.bind("<<ComboboxSelected>>", lambda e: self._tocado())

        caja = ttk.LabelFrame(m, text=" Corazón de favoritas ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Corazón de favoritas ♥", "config.corazon",
               '<button class="btn-corazon"> en la esquina de cada pregunta', con_titulo=False,
               ayuda=
                    "Un corazón pequeño en la esquina de cada pregunta con el que la persona guarda "
                    "sus favoritas (aparecen en «Mi estudio»). Si lo desmarcas, este supuesto no "
                    "lo muestra. Cada persona también puede ocultarlo desde el panel ⚙."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_cfg_corazon = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(caja, text="Mostrar el corazón de favoritas en este supuesto",
                              variable=self.var_cfg_corazon, command=self._tocado)
        chk.pack(anchor="w", padx=10, pady=(0, 10))

        caja = ttk.LabelFrame(m, text=" Subrayar con colores ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Subrayar texto", "config.subrayar",
               '<mark class="subr"> sobre enunciado, pregunta y respuestas', con_titulo=False,
               ayuda=
                    "Permite a la persona seleccionar un trozo del enunciado, de la pregunta o de una "
                    "respuesta y subrayarlo con el color que elija en una ventanita. Los subrayados se "
                    "guardan en su navegador y se ven también en «Mi estudio». Si lo desmarcas, este "
                    "supuesto no deja subrayar. Cada persona también puede apagarlo desde el panel ⚙."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_cfg_subrayar = tk.BooleanVar(value=True)
        chk2 = ttk.Checkbutton(caja, text="Permitir subrayar en este supuesto",
                               variable=self.var_cfg_subrayar, command=self._tocado)
        chk2.pack(anchor="w", padx=10, pady=(0, 10))

        caja = ttk.LabelFrame(m, text=" Número de preguntas (automático) ")
        caja.pack(fill="x", padx=16, pady=6)
        rotulo(caja, "Nº de preguntas",
               "(no se edita: se cuenta solo)",
               '<span class="meta-pill" id="meta-preguntas">', con_titulo=False,
               ayuda=
                    "La píldora «N PREGUNTAS» de la cabecera la calcula la propia página contando "
                    "las preguntas cargadas, así que nunca puede quedar desactualizada."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.lbl_num_preg = ttk.Label(caja, text="0 PREGUNTAS", font=("Consolas", 11, "bold"),
                                      foreground=C_VERDE)
        self.lbl_num_preg.pack(anchor="w", padx=10, pady=(0, 10))

        # ---------- paleta de colores de la página ----------
        caja = ttk.LabelFrame(m, text=" Colores de la página ")
        caja.pack(fill="x", padx=16, pady=(14, 18))
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=880, justify="left",
                  text="Cambia toda la apariencia del examen: fondos, textos, acentos y "
                       "hasta las transparencias derivadas de cada color. No afecta al color "
                       "de cada bloque de preguntas, que se elige en la pestaña «2 · Bloques». "
                       "En el archivo HTML viven en el apartado «tema» y sustituyen a las "
                       "variables de :root."
                  ).pack(anchor="w", padx=10, pady=(8, 8))

        rejilla = ttk.Frame(caja, style="Panel.TFrame")
        rejilla.pack(fill="x", padx=10)
        rejilla.columnconfigure(3, weight=1)

        self.w_tema = {}
        self.muestras_tema = {}
        for fila, (clave, visible, variable, ayuda) in enumerate(CAMPOS_TEMA):
            muestra = tk.Label(rejilla, text="      ", relief="solid", borderwidth=1)
            muestra.grid(row=fila, column=0, sticky="w", pady=3)
            self.muestras_tema[clave] = muestra

            var = tk.StringVar(value=TEMA_DEFECTO[clave])
            ent = ttk.Entry(rejilla, textvariable=var, font=("Consolas", 10), width=10)
            ent.grid(row=fila, column=1, sticky="w", padx=6)
            ent.bind("<KeyRelease>",
                     lambda e, c=clave: (self._tocado(), self._pintar_tema()), add="+")
            self.w_tema[clave] = var

            ttk.Button(rejilla, text="🎨", width=3,
                       command=lambda c=clave, v=visible: self.elegir_color_tema(c, v)
                       ).grid(row=fila, column=2, sticky="w")

            texto = ttk.Frame(rejilla, style="Panel.TFrame")
            texto.grid(row=fila, column=3, sticky="we", padx=(10, 0))
            ttk.Label(texto, text=visible, style="Campo.TLabel").pack(anchor="w")
            ttk.Label(texto, text="tema.%s   →   CSS: %s   ·   %s" % (clave, variable, ayuda),
                      style="Tec.TLabel").pack(anchor="w")

        pie = ttk.Frame(caja, style="Panel.TFrame")
        pie.pack(fill="x", padx=10, pady=(10, 12))
        ttk.Button(pie, text="↺  Restaurar los colores originales",
                   command=self.restaurar_tema).pack(side="left")
        ttk.Label(pie, style="Ayuda.TLabel",
                  text="   Vista previa aproximada →").pack(side="left")

        # Vista previa en miniatura
        self.previa = tk.Frame(caja, height=96, relief="solid", borderwidth=1)
        self.previa.pack(fill="x", padx=10, pady=(0, 12))
        self.previa_barra = tk.Frame(self.previa, height=26)
        self.previa_barra.pack(fill="x")
        self.previa_casilla = tk.Label(self.previa_barra, text=" 1 ", font=("Consolas", 9, "bold"))
        self.previa_casilla.pack(side="left", padx=8, pady=4)
        self.previa_rotulo = tk.Label(self.previa_barra, text="TIEMPO 30:00",
                                      font=("Consolas", 9, "bold"))
        self.previa_rotulo.pack(side="right", padx=8)
        self.previa_tarjeta = tk.Label(self.previa, text="  Texto de una pregunta de ejemplo",
                                       anchor="w", font=("Georgia", 10), padx=8, pady=6)
        self.previa_tarjeta.pack(fill="x", padx=10, pady=(8, 2))
        self.previa_hechos = tk.Label(self.previa, text="  Bloque de hechos del enunciado",
                                      anchor="w", font=("Georgia", 9), padx=8, pady=4)
        self.previa_hechos.pack(fill="x", padx=10, pady=(0, 10))

    # ---------- paleta ----------
    def _pintar_tema(self):
        """Refresca las muestras de color y la vista previa en miniatura."""
        col = {c: color_valido(self.w_tema[c].get(), TEMA_DEFECTO[c]) for c in TEMA_DEFECTO}
        for clave, muestra in self.muestras_tema.items():
            muestra.config(background=col[clave])
        self.previa.config(background=col["fondo"])
        self.previa_barra.config(background=col["barra"])
        self.previa_casilla.config(background=col["acento"], foreground=col["fondo"])
        self.previa_rotulo.config(background=col["barra"], foreground=col["acento"])
        self.previa_tarjeta.config(background=col["tarjeta"], foreground=col["texto"])
        self.previa_hechos.config(background=col["fondoHechos"], foreground=col["gris"])

    def elegir_color_tema(self, clave, visible):
        actual = color_valido(self.w_tema[clave].get(), TEMA_DEFECTO[clave])
        elegido = colorchooser.askcolor(color=actual, parent=self, title=visible)
        if elegido and elegido[1]:
            self.w_tema[clave].set(elegido[1])
            self._pintar_tema()
            self._tocado()

    def restaurar_tema(self):
        for clave, valor in TEMA_DEFECTO.items():
            self.w_tema[clave].set(valor)
        self._pintar_tema()
        self._tocado()
        self.estado("Paleta restaurada a los colores originales de la plantilla.")

    def elegir_logo(self):
        """Elige una imagen del disco y la guarda como ruta relativa al .html."""
        ruta = filedialog.askopenfilename(
            parent=self, title="Imagen del encabezado",
            initialdir=str(self.ruta.parent) if self.ruta else self._carpeta_inicial(),
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.gif *.webp *.svg"),
                       ("Todos los archivos", "*.*")])
        if not ruta:
            return
        elegida = Path(ruta)
        if self.ruta:
            try:
                relativa = os.path.relpath(elegida, self.ruta.parent).replace("\\", "/")
                self.w_cfg["logo"].set(relativa)
                self._tocado()
                self.estado("Imagen del encabezado: %s (ruta relativa al supuesto)" % relativa)
                return
            except ValueError:
                pass          # en otra unidad de disco: se usa la ruta completa
        else:
            messagebox.showinfo(
                "Guarda primero el supuesto",
                "Como el supuesto todavía no está guardado, se usará la ruta completa "
                "de la imagen. Al guardar el archivo conviene volver a elegirla para "
                "que quede una ruta relativa y el supuesto siga siendo portátil.",
                parent=self)
        self.w_cfg["logo"].set(elegida.as_uri())
        self._tocado()

    def cargar_config(self):
        cfg = self.datos["config"]
        for clave, *_ in CAMPOS_CONFIG:
            valor = cfg.get(clave, "")
            self.w_cfg[clave].set(nUm(valor) if clave == "aptoPorcentaje" else str(valor))
        valores = [v for v, _t in RESPUESTAS_EXAMEN]
        actual = cfg.get("respuestas", 0)
        pos = valores.index(actual) if actual in valores else 0
        self.var_cfg_respuestas.set(self._etiquetas_respuestas[pos])
        self.var_cfg_corazon.set(cfg.get("corazon", True) is not False)
        self.var_cfg_subrayar.set(cfg.get("subrayar", True) is not False)
        tema = self.datos.get("tema") or TEMA_DEFECTO
        for clave in TEMA_DEFECTO:
            self.w_tema[clave].set(tema.get(clave, TEMA_DEFECTO[clave]))
        self._pintar_tema()
        self.lbl_num_preg.config(text="%d PREGUNTAS" % len(self.datos["preguntas"]))

    def volcar_config(self):
        cfg = self.datos["config"]
        for clave, *_ in CAMPOS_CONFIG:
            valor = self.w_cfg[clave].get()
            if clave == "minutos":
                valor = max(1, int(numero(valor, 30)))
            elif clave == "aptoPorcentaje":
                valor = min(100.0, max(0.0, numero(valor, 50.0)))
            cfg[clave] = valor
        etiqueta = self.var_cfg_respuestas.get()
        cfg["respuestas"] = next((v for v, t in RESPUESTAS_EXAMEN if t == etiqueta), 0)
        cfg["corazon"] = bool(self.var_cfg_corazon.get())
        cfg["subrayar"] = bool(self.var_cfg_subrayar.get())
        self.datos["tema"] = {
            clave: color_valido(self.w_tema[clave].get(), TEMA_DEFECTO[clave])
            for clave in TEMA_DEFECTO}

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 2 — BLOQUES DEL EXAMEN (supuesto / teoría)
    # ═════════════════════════════════════════════════════════════
    def _pestana_bloques(self):
        panel = ttk.Frame(self.cuaderno)
        self.cuaderno.add(panel, text="  2 · Bloques  ")

        divisor = ttk.PanedWindow(panel, orient="horizontal")
        divisor.pack(fill="both", expand=True, padx=8, pady=8)

        izq = ttk.Frame(divisor, width=300)
        izq.pack_propagate(False)
        divisor.add(izq, weight=0)

        ttk.Label(izq, text="Bloques del examen", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(izq, style="Tec.TLabel", text="bloques[]").pack(anchor="w")
        ttk.Label(izq, style="Ayuda.TLabel", wraplength=280, justify="left",
                  text="Secciones del examen, EN EL ORDEN EN QUE SALEN. Con ▲▼ eliges "
                       "cuál va primero. Puede haber solo un bloque, o tres, o los que "
                       "necesites, de cualquiera de los dos tipos."
                  ).pack(anchor="w", pady=(0, 6))

        self.lst_sec = tk.Listbox(izq, font=("Consolas", 9), height=10,
                                  activestyle="none", exportselection=False)
        self.lst_sec.pack(fill="both", expand=True)
        self.lst_sec.bind("<<ListboxSelect>>", self._sel_seccion)

        bot = ttk.Frame(izq)
        bot.pack(fill="x", pady=6)
        ttk.Button(bot, text="＋ Bloque de supuesto", style="Accion.TButton", width=22,
                   command=lambda: self.anadir_seccion("supuesto")
                   ).grid(row=0, column=0, columnspan=2, padx=1, pady=1)
        ttk.Button(bot, text="＋ Bloque de teoría", style="Accion.TButton", width=22,
                   command=lambda: self.anadir_seccion("test")
                   ).grid(row=1, column=0, columnspan=2, padx=1, pady=1)
        ttk.Button(bot, text="🗑 Borrar", width=10,
                   command=self.borrar_seccion).grid(row=2, column=0, padx=1, pady=1)
        ttk.Button(bot, text="⧉ Duplicar", width=10,
                   command=self.duplicar_seccion).grid(row=2, column=1, padx=1, pady=1)
        ttk.Button(bot, text="▲ Subir", width=10,
                   command=lambda: self.mover_seccion(-1)).grid(row=3, column=0, padx=1, pady=1)
        ttk.Button(bot, text="▼ Bajar", width=10,
                   command=lambda: self.mover_seccion(1)).grid(row=3, column=1, padx=1, pady=1)

        cont = MarcoScroll(divisor)
        divisor.add(cont, weight=1)
        m = cont.interior

        # ---------- identificación ----------
        self.w_sec = {}
        caja = ttk.LabelFrame(m, text=" Identificación ")
        caja.pack(fill="x", padx=10, pady=(8, 6))
        for clave, visible, tecnico, html, ayuda in CAMPOS_BLOQUE:
            rotulo(caja, visible, tecnico, html, ayuda).pack(anchor="w", padx=10, pady=(8, 2))
            var = tk.StringVar()
            ent = ttk.Entry(caja, textvariable=var, font=("Georgia", 10))
            ent.pack(fill="x", padx=10, pady=(0, 2))
            self._vigilar(ent)
            self.w_sec[clave] = var
        ttk.Frame(caja, height=8).pack()

        # ---------- tipo ----------
        caja = ttk.LabelFrame(m, text=" Tipo de bloque ")
        caja.pack(fill="x", padx=10, pady=6)
        rotulo(caja, "Qué clase de preguntas lleva", "bloques[].tipo",
               '<span class="bh-tipo"> → «Supuesto práctico» / «Teoría · test»',
               "Un bloque de SUPUESTO enlaza sus preguntas con un enunciado (los hechos "
               "aparecen encima). Un bloque de TEORÍA son preguntas de test sueltas, sin "
               "enunciado: al elegir este tipo, sus preguntas se desenganchan del enunciado."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_sec_tipo = tk.StringVar(value="supuesto")
        for valor, texto in (("supuesto", "Supuesto práctico (preguntas con enunciado)"),
                             ("test", "Teoría (preguntas de test sueltas)")):
            ttk.Radiobutton(caja, text=texto, value=valor, variable=self.var_sec_tipo,
                            command=self._cambio_tipo_seccion).pack(anchor="w", padx=18, pady=1)
        ttk.Frame(caja, height=8).pack()

        # ---------- aspecto ----------
        caja = ttk.LabelFrame(m, text=" Aspecto en la página ")
        caja.pack(fill="x", padx=10, pady=6)

        rotulo(caja, "Color del bloque", "bloques[].color",
               '.nav-box.blq-XX  ·  .block-header  ·  banda lateral de las tarjetas',
               "Color de las casillas numeradas de la cabecera, del rótulo del bloque y de "
               "la barra que encabeza sus preguntas. Sirve para distinguir de un vistazo la "
               "teoría del supuesto."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        fila = ttk.Frame(caja, style="Panel.TFrame")
        fila.pack(fill="x", padx=10, pady=(0, 4))
        self.var_sec_color = tk.StringVar(value=COLOR_SUPUESTO)
        ent = ttk.Entry(fila, textvariable=self.var_sec_color, font=("Consolas", 10), width=12)
        ent.pack(side="left")
        ent.bind("<KeyRelease>", lambda e: (self._tocado(), self._pintar_muestra_color()), add="+")
        self.muestra_color = tk.Label(fila, text="        ", relief="solid", borderwidth=1)
        self.muestra_color.pack(side="left", padx=8)
        ttk.Button(fila, text="🎨 Elegir color…", command=self.elegir_color).pack(side="left")
        for nombre, valor in (("Azul supuesto", COLOR_SUPUESTO), ("Ámbar teoría", COLOR_TEST),
                              ("Verde", "#7fbf8f"), ("Lavanda", "#b9a6e0")):
            ttk.Button(fila, text=nombre, width=13,
                       command=lambda v=valor: self.poner_color(v)).pack(side="left", padx=(6, 0))

        rotulo(caja, "Cómo EMPIEZAN viéndose las preguntas de este bloque", "bloques[].modo",
               '.question-card.visible  ·  .question-card.encadenada',
               "«En cadena» muestra todas las preguntas del bloque seguidas, una debajo de "
               "otra (lo habitual en la teoría, y también en un supuesto que se lea de "
               "corrido). «De una en una» muestra solo la pregunta actual. Esto es solo el "
               "estado de PARTIDA: en la página, cada bloque tiene su propia casilla en el "
               "panel ⚙ y el alumno puede cambiarlo sin tocar los demás bloques."
               ).pack(anchor="w", padx=10, pady=(10, 4))
        self.var_sec_modo = tk.StringVar(value="individual")
        for valor, texto in (("cadena", "En cadena — todas las preguntas del bloque seguidas"),
                             ("individual", "De una en una — solo la pregunta actual")):
            ttk.Radiobutton(caja, text=texto, value=valor, variable=self.var_sec_modo,
                            command=self._tocado).pack(anchor="w", padx=18, pady=1)

        rotulo(caja, "¿Puede el alumno cambiarlo en este bloque?", "bloques[].opcionUnaEnUna",
               '<div id="una-por-bloque"> → una casilla por bloque',
               "Marcada (lo normal): el panel ⚙ de la página enseña una casilla para ESTE "
               "bloque, con su nombre y su color, y el alumno decide si lo ve en cadena o de "
               "una en una. Desmarcada: ese bloque no sale en el panel y se queda siempre "
               "como lo hayas dejado aquí arriba. Si desmarcas todos, la opción entera "
               "desaparece del panel."
               ).pack(anchor="w", padx=10, pady=(10, 4))
        self.var_sec_opcion_una = tk.BooleanVar(value=True)
        ttk.Checkbutton(caja, variable=self.var_sec_opcion_una, command=self._tocado,
                        text="Sacar la casilla de este bloque en el panel ⚙"
                        ).pack(anchor="w", padx=18, pady=1)

        ttk.Label(caja, style="Ayuda.TLabel", wraplength=820, justify="left",
                  text="EN CADENA, un bloque de supuesto se lee de corrido y en su orden "
                       "natural: enunciado 1 completo (con todas sus secciones) → todas las "
                       "preguntas de ese enunciado → enunciado 2 → sus preguntas, y así "
                       "sucesivamente."
                  ).pack(anchor="w", padx=18, pady=(6, 2))

        rotulo(caja, "Dónde va la barra con el nombre del bloque",
               "bloques[].cabeceraSobreEnunciado",
               '<div class="block-header"> antes o después de <section class="statement">',
               "Marcada (lo normal): la barra del bloque —nombre, nº de preguntas y "
               "baremo— sale ENCIMA del enunciado, encabezando toda la sección. "
               "Desmarcada: baja hasta justo delante de la primera pregunta, debajo de "
               "los hechos (como en las versiones anteriores de la plantilla). En los "
               "bloques de teoría da igual: no llevan enunciado."
               ).pack(anchor="w", padx=10, pady=(10, 4))
        self.var_sec_cabecera = tk.BooleanVar(value=True)
        ttk.Checkbutton(caja, variable=self.var_sec_cabecera, command=self._tocado,
                        text="La barra del bloque va encima del enunciado"
                        ).pack(anchor="w", padx=18, pady=1)
        ttk.Frame(caja, height=8).pack()

        # ---------- puntuación ----------
        caja = ttk.LabelFrame(m, text=" Puntuación de este bloque ")
        caja.pack(fill="x", padx=10, pady=6)
        rotulo(caja, "Cuánto suma y cuánto descuenta cada pregunta",
               "bloques[].acierto · bloques[].fallo · bloques[].blanco",
               '<div class="score-bloques"> → puntos del bloque',
               "Cada bloque se corrige por separado con su propio baremo y luego se suman "
               "los bloques. Se admiten decimales con coma: 0,33 descuenta un tercio."
               ).pack(anchor="w", padx=10, pady=(8, 6))

        rejilla = ttk.Frame(caja, style="Panel.TFrame")
        rejilla.pack(fill="x", padx=10, pady=(0, 4))
        self.var_sec_ac = tk.StringVar(value="1")
        self.var_sec_fa = tk.StringVar(value="0")
        self.var_sec_bl = tk.StringVar(value="0")
        for col, (texto, var, ayuda) in enumerate((
                ("Suma por acierto", self.var_sec_ac, "puntos que suma cada acierto"),
                ("Descuenta por fallo", self.var_sec_fa, "puntos que resta cada fallo"),
                ("Descuenta en blanco", self.var_sec_bl, "puntos que resta dejarla sin contestar"))):
            col_marco = ttk.Frame(rejilla, style="Panel.TFrame")
            col_marco.grid(row=0, column=col, padx=(0, 18), sticky="w")
            ttk.Label(col_marco, text=texto, style="Campo.TLabel").pack(anchor="w")
            ent = ttk.Entry(col_marco, textvariable=var, font=("Consolas", 11), width=8)
            ent.pack(anchor="w", pady=2)
            ent.bind("<KeyRelease>", lambda e: (self._tocado(), self._pintar_resumen_seccion()), add="+")
            ttk.Label(col_marco, text=ayuda, style="Ayuda.TLabel").pack(anchor="w")

        self.lbl_sec_resumen = ttk.Label(caja, text="", font=("Consolas", 10, "bold"),
                                         foreground=C_VERDE, background=C_FONDO)
        self.lbl_sec_resumen.pack(anchor="w", padx=10, pady=(8, 10))

        # ---------- aleatorio ----------
        caja = ttk.LabelFrame(m, text=" Intento aleatorio ")
        caja.pack(fill="x", padx=10, pady=(6, 14))
        rotulo(caja, "Cuántas preguntas de este bloque salen al azar",
               "bloques[].porIntento",
               'botón 🔀 «Nuevo Intento (Aleatorio)» → opción 🎲',
               "0 = salen todas. Si pones un número, en el intento aleatorio total saldrán "
               "solo esas preguntas del bloque, elegidas al azar. El orden de los bloques "
               "nunca cambia: el que pongas primero aquí sale siempre primero."
               ).pack(anchor="w", padx=10, pady=(8, 4))
        self.var_sec_por = tk.StringVar(value="0")
        sp = ttk.Spinbox(caja, from_=0, to=500, textvariable=self.var_sec_por, width=8,
                         font=("Consolas", 11), command=self._tocado)
        sp.pack(anchor="w", padx=10, pady=(0, 10))
        self._vigilar(sp)

    # ---------- color ----------
    def _pintar_muestra_color(self):
        color = color_valido(self.var_sec_color.get(), None)
        self.muestra_color.config(background=color or C_FONDO)

    def poner_color(self, valor):
        self.var_sec_color.set(valor)
        self._pintar_muestra_color()
        self._tocado()

    def elegir_color(self):
        actual = color_valido(self.var_sec_color.get(), COLOR_SUPUESTO)
        elegido = colorchooser.askcolor(color=actual, parent=self,
                                        title="Color del bloque")
        if elegido and elegido[1]:
            self.poner_color(elegido[1])

    # ---------- lista de bloques ----------
    def refrescar_lista_sec(self, seleccionar=None):
        self._silencio = True
        self.lst_sec.delete(0, "end")
        for i, b in enumerate(self.datos["bloques"]):
            cuantas = sum(1 for q in self.datos["preguntas"] if q["bloqueId"] == b["id"])
            marca = "📝" if b["tipo"] == "test" else "📁"
            self.lst_sec.insert("end", "%d. %s %-4s %-16s %2d preg."
                                % (i + 1, marca, b["id"], resumen(b["titulo"], 16), cuantas))
        if seleccionar is None:
            seleccionar = self.i_sec
        if self.datos["bloques"]:
            if seleccionar is None or seleccionar >= len(self.datos["bloques"]):
                seleccionar = 0
            self.lst_sec.selection_clear(0, "end")
            self.lst_sec.selection_set(seleccionar)
            self.lst_sec.see(seleccionar)
        else:
            seleccionar = None
        self._silencio = False
        self.i_sec = seleccionar
        self.cargar_seccion()
        self.refrescar_combo_bloques()
        self.refrescar_envio_bloques()
        self._pintar_titulo()

    def _sel_seccion(self, _e=None):
        if self._silencio:
            return
        sel = self.lst_sec.curselection()
        if not sel or sel[0] == self.i_sec:
            return
        self.volcar_seccion()
        self.i_sec = sel[0]
        self.cargar_seccion()

    def seccion_actual(self):
        if self.i_sec is None or self.i_sec >= len(self.datos["bloques"]):
            return None
        return self.datos["bloques"][self.i_sec]

    def cargar_seccion(self):
        b = self.seccion_actual()
        for clave, *_ in CAMPOS_BLOQUE:
            self.w_sec[clave].set("" if b is None else str(b.get(clave, "")))
        self.var_sec_tipo.set("supuesto" if b is None else b["tipo"])
        self.var_sec_modo.set("individual" if b is None else b["modo"])
        self.var_sec_cabecera.set(True if b is None
                                  else b.get("cabeceraSobreEnunciado", True) is not False)
        self.var_sec_opcion_una.set(True if b is None
                                    else b.get("opcionUnaEnUna", True) is not False)
        self.var_sec_color.set(COLOR_SUPUESTO if b is None else b["color"])
        self.var_sec_por.set("0" if b is None else str(b["porIntento"]))
        self.var_sec_ac.set("1" if b is None else nUm(b["acierto"]))
        self.var_sec_fa.set("0" if b is None else nUm(b["fallo"]))
        self.var_sec_bl.set("0" if b is None else nUm(b["blanco"]))
        self._pintar_muestra_color()
        self._pintar_resumen_seccion()

    def volcar_seccion(self):
        b = self.seccion_actual()
        if b is None:
            return
        antiguo = b["id"]
        nuevo = re.sub(r"[^A-Za-z0-9_-]", "", self.w_sec["id"].get().strip()) or antiguo
        otros = {x["id"] for x in self.datos["bloques"] if x is not b}
        while nuevo in otros:
            nuevo += "x"
        if nuevo != antiguo:
            for q in self.datos["preguntas"]:
                if q["bloqueId"] == antiguo:
                    q["bloqueId"] = nuevo
        b["id"] = nuevo
        b["titulo"] = self.w_sec["titulo"].get().strip() or ("Teoría" if b["tipo"] == "test"
                                                             else "Supuesto práctico")
        b["tipo"] = self.var_sec_tipo.get()
        b["modo"] = self.var_sec_modo.get()
        b["cabeceraSobreEnunciado"] = bool(self.var_sec_cabecera.get())
        b["opcionUnaEnUna"] = bool(self.var_sec_opcion_una.get())
        b["color"] = color_valido(self.var_sec_color.get(),
                                  COLOR_TEST if b["tipo"] == "test" else COLOR_SUPUESTO)
        try:
            b["porIntento"] = max(0, int(float(self.var_sec_por.get().replace(",", "."))))
        except ValueError:
            b["porIntento"] = 0
        b["acierto"] = numero(self.var_sec_ac.get(), 1.0)
        b["fallo"] = abs(numero(self.var_sec_fa.get(), 0.0))
        b["blanco"] = abs(numero(self.var_sec_bl.get(), 0.0))
        if b["tipo"] == "test":
            for q in self.datos["preguntas"]:
                if q["bloqueId"] == b["id"]:
                    q["statementId"] = None

    def _cambio_tipo_seccion(self):
        b = self.seccion_actual()
        if b is None:
            return
        nuevo = self.var_sec_tipo.get()
        if nuevo == "test":
            enganchadas = [q for q in self.datos["preguntas"]
                           if q["bloqueId"] == b["id"] and q["statementId"]]
            if enganchadas and not messagebox.askyesno(
                    "Cambiar a bloque de teoría",
                    "Este bloque tiene %d pregunta(s) enlazadas a un enunciado.\n\n"
                    "Al convertirlo en bloque de teoría dejarán de mostrar los hechos "
                    "(el enunciado no se borra).\n\n¿Continuar?" % len(enganchadas),
                    parent=self):
                self.var_sec_tipo.set(b["tipo"])
                return
        # Colores y modo por defecto del nuevo tipo, si estaban en los del anterior
        if self.var_sec_color.get() in (COLOR_SUPUESTO, COLOR_TEST):
            self.var_sec_color.set(COLOR_TEST if nuevo == "test" else COLOR_SUPUESTO)
        self.var_sec_modo.set("cadena" if nuevo == "test" else "individual")
        self.volcar_seccion()
        self._pintar_muestra_color()
        self.refrescar_lista_sec(self.i_sec)
        self.refrescar_lista_preg()
        self._tocado()

    def _pintar_resumen_seccion(self):
        b = self.seccion_actual()
        if b is None:
            self.lbl_sec_resumen.config(text="")
            return
        cuantas = sum(1 for q in self.datos["preguntas"] if q["bloqueId"] == b["id"])
        maximo = cuantas * numero(self.var_sec_ac.get(), 1.0)
        self.lbl_sec_resumen.config(
            text="%d preguntas en este bloque  ·  puntuación máxima: %s puntos"
                 % (cuantas, nUm(maximo)))

    # ---------- añadir / borrar / mover bloques ----------
    def _nuevo_id_bloque(self):
        usados = {b["id"] for b in self.datos["bloques"]}
        n = 1
        while ("B%d" % n) in usados:
            n += 1
        return "B%d" % n

    def anadir_seccion(self, tipo):
        self.volcar_seccion()
        self.datos["bloques"].append(bloque_vacio(tipo, self._nuevo_id_bloque()))
        self.refrescar_lista_sec(len(self.datos["bloques"]) - 1)
        self.refrescar_lista_preg()
        self._tocado()
        self.estado("Bloque de %s añadido. Ahora añade sus preguntas en la pestaña 4."
                    % ("teoría" if tipo == "test" else "supuesto"))

    def duplicar_seccion(self):
        b = self.seccion_actual()
        if b is None:
            return
        self.volcar_seccion()
        copia = json.loads(json.dumps(b))
        copia["id"] = self._nuevo_id_bloque()
        copia["titulo"] = b["titulo"] + " (copia)"
        self.datos["bloques"].insert(self.i_sec + 1, copia)
        self.refrescar_lista_sec(self.i_sec + 1)
        self._tocado()

    def borrar_seccion(self):
        b = self.seccion_actual()
        if b is None:
            return
        if len(self.datos["bloques"]) == 1:
            messagebox.showinfo("Un bloque como mínimo",
                                "El examen necesita al menos un bloque.", parent=self)
            return
        suyas = [q for q in self.datos["preguntas"] if q["bloqueId"] == b["id"]]
        aviso = "¿Borrar el bloque «%s»?" % b["titulo"]
        if suyas:
            aviso += ("\n\nATENCIÓN: se borrarán también sus %d preguntas."
                      % len(suyas))
        if not messagebox.askyesno("Borrar bloque", aviso, parent=self):
            return
        self.volcar_pregunta()
        self.datos["preguntas"] = [q for q in self.datos["preguntas"]
                                   if q["bloqueId"] != b["id"]]
        del self.datos["bloques"][self.i_sec]
        self.i_preg = 0 if self.datos["preguntas"] else None
        self.refrescar_lista_sec(max(0, self.i_sec - 1))
        self.refrescar_lista_preg(self.i_preg)
        self._tocado()

    def mover_seccion(self, paso):
        if self.i_sec is None:
            return
        destino = self.i_sec + paso
        lista = self.datos["bloques"]
        if destino < 0 or destino >= len(lista):
            return
        self.volcar_seccion()
        lista[self.i_sec], lista[destino] = lista[destino], lista[self.i_sec]
        self.ordenar_preguntas_por_bloque()
        self.refrescar_lista_sec(destino)
        self.refrescar_lista_preg()
        self._tocado()
        self.estado("Orden de los bloques: %s"
                    % " → ".join(b["titulo"] for b in self.datos["bloques"]))

    def ordenar_preguntas_por_bloque(self):
        """Las preguntas se guardan en el orden del examen: bloque a bloque."""
        orden = {b["id"]: i for i, b in enumerate(self.datos["bloques"])}
        self.datos["preguntas"].sort(key=lambda q: orden.get(q["bloqueId"], 0))

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
               "resaltado y otro tamaño de letra lo que esté seleccionado. «Just.» (Ctrl+J) "
               "justifica —ajusta al ancho de la línea— el párrafo donde esté el cursor o los "
               "seleccionados; «Izq.» (Ctrl+L) quita el justificado. «Sang+» (tecla Tab) mete "
               "el párrafo más hacia dentro que el anterior, hasta tres niveles, y «Sang-» "
               "(Mayús+Tab) lo saca. El menú «Fuente» cambia la tipografía de lo seleccionado. "
               "Los párrafos justificados se ven aquí con fondo azulado y justificados en la "
               "página; las tipografías se ven aquí de forma aproximada."
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

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 4 — PREGUNTAS, RESPUESTAS Y SOLUCIONES
    # ═════════════════════════════════════════════════════════════
    def _pestana_preguntas(self):
        panel = ttk.Frame(self.cuaderno)
        self.cuaderno.add(panel, text="  4 · Preguntas y respuestas  ")

        divisor = ttk.PanedWindow(panel, orient="horizontal")
        divisor.pack(fill="both", expand=True, padx=8, pady=8)

        izq = ttk.Frame(divisor, width=330)
        izq.pack_propagate(False)
        divisor.add(izq, weight=0)

        ttk.Label(izq, text="Preguntas del examen", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(izq, style="Tec.TLabel",
                  text='preguntas[]  →  <div class="question-card">').pack(anchor="w")
        ttk.Label(izq, style="Ayuda.TLabel", wraplength=310, justify="left",
                  text="Este es el orden por defecto del examen. Las preguntas de un mismo "
                       "enunciado deben ir seguidas."
                  ).pack(anchor="w", pady=(0, 6))

        self.lst_preg = tk.Listbox(izq, font=("Consolas", 9), height=20,
                                   activestyle="none", exportselection=False)
        self.lst_preg.pack(fill="both", expand=True)
        self.lst_preg.bind("<<ListboxSelect>>", self._sel_pregunta)

        bot = ttk.Frame(izq)
        bot.pack(fill="x", pady=6)
        ttk.Button(bot, text="＋ Añadir pregunta", command=self.anadir_pregunta,
                   style="Accion.TButton", width=17).grid(row=0, column=0, columnspan=2, padx=1, pady=1)
        ttk.Button(bot, text="⧉ Duplicar", command=self.duplicar_pregunta,
                   width=8).grid(row=0, column=2, padx=1, pady=1)
        ttk.Button(bot, text="🗑 Borrar", command=self.borrar_pregunta,
                   width=11).grid(row=1, column=0, padx=1, pady=1)
        ttk.Button(bot, text="▲ Subir", command=lambda: self.mover_pregunta(-1),
                   width=8).grid(row=1, column=1, padx=1, pady=1)
        ttk.Button(bot, text="▼ Bajar", command=lambda: self.mover_pregunta(1),
                   width=8).grid(row=1, column=2, padx=1, pady=1)

        cont = MarcoScroll(divisor)
        divisor.add(cont, weight=1)
        m = cont.interior

        # --- datos de la pregunta ---
        caja = ttk.LabelFrame(m, text=" Enunciado de la pregunta ")
        caja.pack(fill="x", padx=10, pady=(8, 6))

        rotulo(caja, "Bloque del examen en el que va esta pregunta", "preguntas[].bloqueId",
               '.nav-box.blq-XX  ·  <div class="block-header">',
               "Decide en qué sección sale la pregunta (supuesto o teoría), de qué color "
               "es su casilla y con qué baremo se corrige. Los bloques se crean y se "
               "ordenan en la pestaña «2 · Bloques»."
               ).pack(anchor="w", padx=10, pady=(8, 2))
        self.var_preg_bloque = tk.StringVar()
        self.combo_bloque = ttk.Combobox(caja, textvariable=self.var_preg_bloque,
                                         state="readonly", font=("Consolas", 10))
        self.combo_bloque.pack(fill="x", padx=10, pady=(0, 4))
        self.combo_bloque.bind("<<ComboboxSelected>>", self._cambio_bloque_pregunta)

        rotulo(caja, "Enunciado (bloque de hechos) al que pertenece", "preguntas[].statementId",
               '<section id="stmt-XX"> (vínculo interno)',
               "Al llegar a esta pregunta, la página muestra arriba los hechos de ese enunciado. "
               "Elige «(pregunta suelta)» si no depende de ningún caso práctico. En los "
               "bloques de teoría este campo se queda desactivado: no llevan enunciado."
               ).pack(anchor="w", padx=10, pady=(8, 2))
        self.var_preg_stmt = tk.StringVar()
        self.combo_stmt = ttk.Combobox(caja, textvariable=self.var_preg_stmt, state="readonly",
                                       font=("Consolas", 10))
        self.combo_stmt.pack(fill="x", padx=10, pady=(0, 4))
        self.combo_stmt.bind("<<ComboboxSelected>>", self._cambio_stmt)

        rotulo(caja, "Partes del enunciado de las que depende (modo foco)",
               "preguntas[].factIds",
               'factBlocks[].id  →  <div class="fact-block"> que se muestran en modo foco',
               "Marca aquí el hecho (o los hechos) desencadenantes concretos de los que "
               "depende esta pregunta. Con el MODO FOCO encendido en el panel ⚙ —y las "
               "preguntas de una en una—, esta pregunta mostrará SOLO esos bloques de "
               "hechos en vez del enunciado entero, con un botón para desplegarlo completo. "
               "Si no marcas ninguno, la pregunta enseña siempre el enunciado entero. "
               "Con Ctrl+clic se marcan y desmarcan varios."
               ).pack(anchor="w", padx=10, pady=(8, 2))
        marco_fl = ttk.Frame(caja, style="Panel.TFrame")
        marco_fl.pack(fill="x", padx=10, pady=(0, 2))
        self.lst_factlink = tk.Listbox(marco_fl, font=("Consolas", 9), height=5,
                                       selectmode="extended", activestyle="none",
                                       exportselection=False)
        self.lst_factlink.pack(side="left", fill="both", expand=True)
        self.lst_factlink.bind("<<ListboxSelect>>", self._sel_factlink)
        colf = ttk.Frame(marco_fl, style="Panel.TFrame")
        colf.pack(side="left", padx=(6, 0))
        ttk.Button(colf, text="Ninguno", width=11,
                   command=self.limpiar_factlink).pack(pady=1)
        self.lbl_factlink = ttk.Label(caja, text="", style="Tec.TLabel")
        self.lbl_factlink.pack(anchor="w", padx=10, pady=(0, 4))

        rotulo(caja, "Etiqueta de materia (q-tag)", "preguntas[].tag",
               '<span class="q-tag">',
               "Línea pequeña en mayúsculas encima de la pregunta (por ejemplo: "
               "«LPACAP · Art. 21»). Déjala VACÍA si el documento de origen no la pide."
               ).pack(anchor="w", padx=10, pady=(8, 2))
        self.var_preg_tag = tk.StringVar()
        ent = ttk.Entry(caja, textvariable=self.var_preg_tag, font=("Consolas", 10))
        ent.pack(fill="x", padx=10, pady=(0, 4))
        self._vigilar(ent)

        rotulo(caja, "Texto de la pregunta", "preguntas[].q", '<div class="q-text">',
               "Lo que se lee en negrita dentro de la tarjeta de la pregunta."
               ).pack(anchor="w", padx=10, pady=(8, 2))
        marco, self.txt_preg_q = caja_texto(caja, alto=4)
        marco.pack(fill="x", padx=10, pady=(0, 10))
        self._vigilar(self.txt_preg_q)

        # --- respuestas ---
        caja = ttk.LabelFrame(m, text=" Respuestas — marca cuál (o cuáles) es la correcta ")
        caja.pack(fill="x", padx=10, pady=6)
        rotulo(caja, "Las opciones de esta pregunta", "preguntas[].a[]",
               '<div class="option"> → <span class="opt-letter">A…G</span>',
               "De 2 a 7 opciones; lo normal son cuatro. La casilla de la izquierda marca "
               "la correcta (preguntas[].correctas). OJO: la página baraja las opciones en "
               "cada intento, así que la correcta no saldrá siempre en la letra que ocupa aquí."
               ).pack(anchor="w", padx=10, pady=(8, 6))

        # Respuesta múltiple
        self.var_preg_multiple = tk.BooleanVar(value=False)
        ttk.Checkbutton(caja, variable=self.var_preg_multiple, command=self._cambio_multiple,
                        text="Respuesta múltiple  ·  preguntas[].multiple  →  hay que marcar "
                             "TODAS las que procedan (solo cuenta si se aciertan todas)"
                        ).pack(anchor="w", padx=10, pady=(0, 8))

        # Filas de opciones: se crean las siete y se enseñan las que tenga
        # la pregunta. Así añadir o quitar una es solo mostrar u ocultar.
        self.var_preg_ok = []
        self.filas_opcion = []
        self.txt_opciones = []
        for i in range(MAX_OPCIONES):
            fila = ttk.Frame(caja, style="Panel.TFrame")
            var = tk.BooleanVar(value=(i == 0))
            ttk.Checkbutton(fila, text="  %s  " % LETRAS[i], variable=var,
                            command=lambda n=i: self._marcar_correcta(n)
                            ).pack(side="left", anchor="n", pady=4)
            marco, txt = caja_texto(fila, alto=3, ancho=70)
            marco.pack(side="left", fill="x", expand=True)
            self._vigilar(txt)
            self.var_preg_ok.append(var)
            self.filas_opcion.append(fila)
            self.txt_opciones.append(txt)

        linea = ttk.Frame(caja, style="Panel.TFrame")
        linea.pack(fill="x", padx=10, pady=(6, 2))
        ttk.Button(linea, text="＋ Añadir respuesta", width=20, style="Accion.TButton",
                   command=self.anadir_opcion).pack(side="left")
        ttk.Button(linea, text="🗑 Quitar la última", width=20,
                   command=self.quitar_opcion).pack(side="left", padx=(6, 0))
        self.lbl_correcta = ttk.Label(linea, text="", font=("Consolas", 10, "bold"),
                                      foreground=C_VERDE, background=C_FONDO)
        self.lbl_correcta.pack(side="left", padx=(16, 0))

        rotulo(caja, "Cuántas de estas respuestas salen en el examen",
               "preguntas[].respuestas",
               'nº de <div class="option"> de ESTA pregunta',
               "Normalmente, lo que hayas puesto en la pestaña 1 para todo el examen. Aquí "
               "se le puede dar un número propio a una pregunta suelta: por ejemplo, escribir "
               "siete opciones y que salgan solo cuatro (la correcta y tres distractores "
               "sorteados en cada intento). Nunca se recorta por debajo de las correctas."
               ).pack(anchor="w", padx=10, pady=(10, 2))
        self.var_preg_respuestas = tk.StringVar()
        self._etiquetas_preg_resp = ["Las que diga la pestaña 1 (todo el examen)"] + \
                                    ["%d respuestas" % n for n in range(MIN_OPCIONES, MAX_OPCIONES + 1)]
        self._valores_preg_resp = [0] + list(range(MIN_OPCIONES, MAX_OPCIONES + 1))
        combo = ttk.Combobox(caja, textvariable=self.var_preg_respuestas, state="readonly",
                             font=("Georgia", 10), values=self._etiquetas_preg_resp)
        combo.pack(fill="x", padx=10, pady=(0, 4))
        combo.bind("<<ComboboxSelected>>", lambda e: self._tocado())
        self.lbl_aviso_resp = ttk.Label(caja, text="", style="Tec.TLabel")
        self.lbl_aviso_resp.pack(anchor="w", padx=10, pady=(0, 10))

        # --- corrección ---
        caja = ttk.LabelFrame(m, text=" Solución y motivación ")
        caja.pack(fill="both", expand=True, padx=10, pady=(6, 12))

        rotulo(caja, "Motivación legal (normativa aplicable)", "preguntas[].law",
               '<div class="feedback-body"> → <p>   ·   <div class="ci-law">',
               "Texto que aparece tras corregir, bajo el rótulo «⚖️ MOTIVACIÓN LEGAL Y NORMATIVA "
               "APLICABLE», y también en la corrección completa y en el PDF."
               ).pack(anchor="w", padx=10, pady=(8, 2))
        marco, self.txt_preg_law = caja_texto(caja, alto=7)
        marco.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._vigilar(self.txt_preg_law)

        rotulo(caja, "Consejo o matiz práctico", "preguntas[].tip",
               '<div class="tip">  ·  <div class="ci-tip">',
               "Recuadro verde con 💡 debajo de la motivación legal. Déjalo vacío si no procede."
               ).pack(anchor="w", padx=10, pady=(4, 2))
        marco, self.txt_preg_tip = caja_texto(caja, alto=4)
        marco.pack(fill="x", padx=10, pady=(0, 12))
        self._vigilar(self.txt_preg_tip)

    # ---------- desplegable de bloques ----------
    def refrescar_combo_bloques(self):
        if not hasattr(self, "combo_bloque"):
            return
        self._ids_bloque = [b["id"] for b in self.datos["bloques"]]
        self.combo_bloque["values"] = [
            "%s · %s  (%s)" % (b["id"], resumen(b["titulo"], 34),
                               "teoría" if b["tipo"] == "test" else "supuesto")
            for b in self.datos["bloques"]]
        self._sincronizar_combo_bloque()

    def _sincronizar_combo_bloque(self):
        if not self.combo_bloque["values"]:
            return
        p = self.pregunta_actual()
        try:
            pos = self._ids_bloque.index(p["bloqueId"]) if p else 0
        except (ValueError, AttributeError, TypeError):
            pos = 0
        self.combo_bloque.current(pos)
        # En los bloques de teoría el enunciado no aplica
        es_test = bool(p) and self.tipo_de_bloque(p["bloqueId"]) == "test"
        self.combo_stmt.configure(state="disabled" if es_test else "readonly")

    def tipo_de_bloque(self, bloque_id):
        for b in self.datos["bloques"]:
            if b["id"] == bloque_id:
                return b["tipo"]
        return "supuesto"

    def _cambio_bloque_pregunta(self, _e=None):
        p = self.pregunta_actual()
        if p is None:
            return
        self.volcar_pregunta()
        self.ordenar_preguntas_por_bloque()
        nuevo = next((i for i, x in enumerate(self.datos["preguntas"]) if x is p), 0)
        self.refrescar_lista_preg(nuevo)
        self.refrescar_lista_sec(self.i_sec)
        self._tocado()

    # ---------- desplegable de enunciados ----------
    def refrescar_combo_enunciados(self):
        if not hasattr(self, "combo_stmt"):
            return
        self._ids_combo = [None] + [e["id"] for e in self.datos["enunciados"]]
        etiquetas = ["(pregunta suelta — sin bloque de hechos)"]
        etiquetas += ["%s · %s" % (e["id"], resumen(e["title"], 40))
                      for e in self.datos["enunciados"]]
        self.combo_stmt["values"] = etiquetas
        self._sincronizar_combo()

    def _sincronizar_combo(self):
        if not self.combo_stmt["values"]:
            self.refrescar_combo_enunciados()
            return
        p = self.pregunta_actual()
        sid = p["statementId"] if p else None
        try:
            pos = self._ids_combo.index(sid)
        except (ValueError, AttributeError):
            pos = 0
        self.combo_stmt.current(pos)

    def _cambio_stmt(self, _e=None):
        if self.pregunta_actual() is None:
            return
        self.volcar_pregunta()          # incluye el nuevo statementId
        self.refrescar_lista_preg(self.i_preg)
        self._tocado()

    # ---------- vínculo con los bloques de hechos (modo foco) ----------
    def refrescar_lista_factlink(self):
        """Rellena la lista de bloques de hechos del enunciado de la pregunta
        actual y marca los que tenga vinculados."""
        if not hasattr(self, "lst_factlink"):
            return
        self._silencio_fact = True
        self.lst_factlink.delete(0, "end")
        p = self.pregunta_actual()
        enun = None
        if p and p.get("statementId"):
            enun = next((e for e in self.datos["enunciados"]
                         if e["id"] == p["statementId"]), None)
        hechos = enun["factBlocks"] if enun else []
        self._ids_factlink = [h["id"] for h in hechos]
        for h in hechos:
            marca = "⚠" if h["red"] else "📋"
            if h["hidden"]:
                marca = "👁"
            self.lst_factlink.insert("end", "%-4s %s %s" % (h["id"], marca,
                                                            resumen(h["title"], 44)))
        if p is not None:
            # Se descartan los vínculos que ya no existan en ese enunciado
            p["factIds"] = [x for x in p.get("factIds", []) if x in self._ids_factlink]
            for i, ident in enumerate(self._ids_factlink):
                if ident in p["factIds"]:
                    self.lst_factlink.selection_set(i)
        self._silencio_fact = False

        if p is None:
            texto = ""
        elif not p.get("statementId"):
            texto = "Esta pregunta no depende de ningún enunciado: el modo foco no le afecta."
        elif not hechos:
            texto = ("El enunciado %s todavía no tiene bloques de hechos (pestaña 3)."
                     % p["statementId"])
        elif not p["factIds"]:
            texto = "Sin vincular: en modo foco esta pregunta muestra el enunciado entero."
        else:
            texto = ("En modo foco se mostrarán solo: %s." % ", ".join(p["factIds"]))
        self.lbl_factlink.config(text=texto)

    def _sel_factlink(self, _e=None):
        if getattr(self, "_silencio_fact", False) or self._silencio:
            return
        p = self.pregunta_actual()
        if p is None or not getattr(self, "_ids_factlink", None):
            return
        p["factIds"] = [self._ids_factlink[i] for i in self.lst_factlink.curselection()
                        if i < len(self._ids_factlink)]
        self.lbl_factlink.config(
            text="Sin vincular: en modo foco esta pregunta muestra el enunciado entero."
                 if not p["factIds"]
                 else "En modo foco se mostrarán solo: %s." % ", ".join(p["factIds"]))
        self._pintar_vinculos_bloque()
        self._tocado()

    def limpiar_factlink(self):
        """Quita todos los vínculos de la pregunta actual."""
        p = self.pregunta_actual()
        if p is None:
            return
        p["factIds"] = []
        self.refrescar_lista_factlink()
        self._pintar_vinculos_bloque()
        self._tocado()

    def _marcar_correcta(self, n=None):
        """Al marcar una casilla: si la pregunta NO es de respuesta múltiple,
        marcar una desmarca las demás (se comporta como un botón de radio)."""
        if n is not None and not self.var_preg_multiple.get() and self.var_preg_ok[n].get():
            for i, var in enumerate(self.var_preg_ok):
                if i != n:
                    var.set(False)
        if n is not None and not any(v.get() for v in self.var_preg_ok):
            # Siempre tiene que haber al menos una correcta
            self.var_preg_ok[n].set(True)
        self._pintar_correctas()
        self._tocado()

    def _cambio_multiple(self):
        """Al dejar de ser múltiple, se queda solo la primera correcta."""
        if not self.var_preg_multiple.get():
            visto = False
            for var in self.var_preg_ok:
                if var.get():
                    if visto:
                        var.set(False)
                    visto = True
        self._pintar_correctas()
        self._tocado()

    def _n_opciones(self):
        """Cuántas filas de respuesta hay a la vista."""
        return sum(1 for f in self.filas_opcion if f.winfo_manager())

    def _pintar_filas_opciones(self, cuantas):
        cuantas = max(MIN_OPCIONES, min(MAX_OPCIONES, cuantas))
        for i, fila in enumerate(self.filas_opcion):
            if i < cuantas:
                fila.pack(fill="x", padx=10, pady=2)
            else:
                fila.pack_forget()
                self.var_preg_ok[i].set(False)
        return cuantas

    def _pintar_correctas(self):
        marcadas = [LETRAS[i] for i, v in enumerate(self.var_preg_ok)
                    if v.get() and self.filas_opcion[i].winfo_manager()]
        if not marcadas:
            texto = "⚠ sin respuesta correcta marcada"
        elif len(marcadas) == 1:
            texto = "Correcta: %s" % marcadas[0]
        else:
            texto = "Correctas: %s" % ", ".join(marcadas)
        self.lbl_correcta.config(text=texto)
        self._pintar_aviso_respuestas()

    def _pintar_aviso_respuestas(self):
        """Explica, en cristiano, cuántas respuestas verá el alumno."""
        if not hasattr(self, "lbl_aviso_resp"):
            return
        escritas = self._n_opciones()
        propio = next((v for v, t in zip(self._valores_preg_resp, self._etiquetas_preg_resp)
                       if t == self.var_preg_respuestas.get()), 0)
        general = self.datos["config"].get("respuestas", 0)
        cuantas = propio or general or escritas
        correctas = sum(1 for i, v in enumerate(self.var_preg_ok)
                        if v.get() and i < escritas)
        minimo = correctas + (1 if escritas > correctas else 0)
        cuantas = min(escritas, max(cuantas, minimo))
        if cuantas >= escritas:
            texto = "Salen las %d opciones escritas." % escritas
        else:
            texto = ("De las %d escritas saldrán %d: la(s) correcta(s) y %d distractor(es) "
                     "sorteados en cada intento." % (escritas, cuantas, cuantas - correctas))
        self.lbl_aviso_resp.config(text=texto)

    def anadir_opcion(self):
        cuantas = self._n_opciones()
        if cuantas >= MAX_OPCIONES:
            self.estado("Una pregunta admite como mucho %d respuestas." % MAX_OPCIONES)
            return
        self._pintar_filas_opciones(cuantas + 1)
        poner_texto(self.txt_opciones[cuantas], "")
        self._pintar_correctas()
        self.txt_opciones[cuantas].focus_set()
        self._tocado()

    def quitar_opcion(self):
        cuantas = self._n_opciones()
        if cuantas <= MIN_OPCIONES:
            self.estado("Una pregunta necesita al menos %d respuestas." % MIN_OPCIONES)
            return
        if sacar_texto(self.txt_opciones[cuantas - 1]).strip() and not messagebox.askyesno(
                "Quitar respuesta",
                "La respuesta %s tiene texto escrito. ¿Quitarla igualmente?" % LETRAS[cuantas - 1],
                parent=self):
            return
        self._pintar_filas_opciones(cuantas - 1)
        if not any(v.get() for v in self.var_preg_ok):
            self.var_preg_ok[0].set(True)
        self._pintar_correctas()
        self._tocado()

    # ---------- lista de preguntas ----------
    def refrescar_lista_preg(self, seleccionar=None):
        self._silencio = True
        self.lst_preg.delete(0, "end")
        fallos = herr.problemas_por_pregunta(self.datos)
        for i, p in enumerate(self.datos["preguntas"]):
            marca = "📝" if self.tipo_de_bloque(p["bloqueId"]) == "test" else "📁"
            foco = "🔎" if p.get("factIds") else " "
            varias = "☑" if p.get("multiple") else " "
            etiqueta = "%02d %s%-3s %-3s%s%s %s" % (i + 1, marca, p["bloqueId"],
                                                    p["statementId"] or "--", foco, varias,
                                                    resumen(p["q"], 22))
            gravedad = fallos.get(i)
            if gravedad:
                etiqueta += "  " + ("✗ " if gravedad[0] == "error" else "! ") + gravedad[1]
            self.lst_preg.insert("end", etiqueta)
            if gravedad:
                self.lst_preg.itemconfig("end", foreground="#b91c1c" if gravedad[0] == "error" else "#b45309")
        if seleccionar is None:
            seleccionar = self.i_preg
        if self.datos["preguntas"]:
            if seleccionar is None or seleccionar >= len(self.datos["preguntas"]):
                seleccionar = 0
            self.lst_preg.selection_clear(0, "end")
            self.lst_preg.selection_set(seleccionar)
            self.lst_preg.see(seleccionar)
        else:
            seleccionar = None
        self._silencio = False
        self.i_preg = seleccionar
        self.cargar_pregunta()
        if hasattr(self, "lbl_sec_resumen"):
            self._pintar_resumen_seccion()
        if hasattr(self, "lbl_num_preg"):
            self.lbl_num_preg.config(text="%d PREGUNTAS" % len(self.datos["preguntas"]))
        self._pintar_titulo()

    def _sel_pregunta(self, _e=None):
        if self._silencio:
            return
        sel = self.lst_preg.curselection()
        if not sel or sel[0] == self.i_preg:
            return
        self.volcar_pregunta()
        self.i_preg = sel[0]
        self.cargar_pregunta()

    def pregunta_actual(self):
        if self.i_preg is None or self.i_preg >= len(self.datos["preguntas"]):
            return None
        return self.datos["preguntas"][self.i_preg]

    def cargar_pregunta(self):
        p = self.pregunta_actual()
        self.var_preg_tag.set("" if p is None else p["tag"])
        poner_texto(self.txt_preg_q, "" if p is None else p["q"])

        opciones = (p["a"] if p else [])[:MAX_OPCIONES]
        cuantas = self._pintar_filas_opciones(len(opciones) or OPCIONES_POR_DEFECTO)
        correctas = set(p["correctas"]) if p else {0}
        for i in range(MAX_OPCIONES):
            poner_texto(self.txt_opciones[i], opciones[i] if i < len(opciones) else "")
            self.var_preg_ok[i].set(i in correctas and i < cuantas)
        self.var_preg_multiple.set(bool(p and p.get("multiple")))
        propio = p.get("respuestas", 0) if p else 0
        pos = self._valores_preg_resp.index(propio) if propio in self._valores_preg_resp else 0
        self.var_preg_respuestas.set(self._etiquetas_preg_resp[pos])

        poner_texto(self.txt_preg_law, "" if p is None else p["law"])
        poner_texto(self.txt_preg_tip, "" if p is None else p["tip"])
        self._pintar_correctas()
        self._sincronizar_combo_bloque()
        self._sincronizar_combo()
        self.refrescar_lista_factlink()

    def volcar_pregunta(self):
        p = self.pregunta_actual()
        if p is None:
            return
        p["tag"] = self.var_preg_tag.get().strip()
        p["q"] = limpiar_texto(sacar_texto(self.txt_preg_q))

        # Solo cuentan las filas de respuesta que estén a la vista
        cuantas = self._n_opciones()
        p["a"] = [limpiar_texto(sacar_texto(self.txt_opciones[i])) for i in range(cuantas)]
        correctas = [i for i in range(cuantas) if self.var_preg_ok[i].get()]
        p["correctas"] = correctas or [0]
        p["c"] = p["correctas"][0]
        p["multiple"] = bool(self.var_preg_multiple.get())
        etiqueta = self.var_preg_respuestas.get()
        p["respuestas"] = next((v for v, t in zip(self._valores_preg_resp,
                                                  self._etiquetas_preg_resp) if t == etiqueta), 0)

        p["law"] = limpiar_texto(sacar_texto(self.txt_preg_law))
        p["tip"] = limpiar_texto(sacar_texto(self.txt_preg_tip))
        if getattr(self, "_ids_bloque", None) and self.combo_bloque["values"]:
            p["bloqueId"] = self._ids_bloque[self.combo_bloque.current()]
        if hasattr(self, "_ids_combo") and self.combo_stmt["values"]:
            p["statementId"] = self._ids_combo[self.combo_stmt.current()]
        if self.tipo_de_bloque(p["bloqueId"]) == "test":
            p["statementId"] = None
        # Vínculos con partes del enunciado (modo foco): solo se conservan
        # mientras la pregunta siga colgando de ese enunciado.
        if not p["statementId"]:
            p["factIds"] = []
        else:
            propios = next((set(h["id"] for h in e["factBlocks"])
                            for e in self.datos["enunciados"]
                            if e["id"] == p["statementId"]), set())
            p["factIds"] = [x for x in p.get("factIds", []) if x in propios]

    def anadir_pregunta(self):
        self.volcar_pregunta()
        # La nueva pregunta hereda el bloque y el enunciado de la anterior
        anterior = self.pregunta_actual()
        if anterior:
            bid = anterior["bloqueId"]
            sid = anterior["statementId"]
        else:
            bid = self.datos["bloques"][0]["id"]
            sid = self.datos["enunciados"][0]["id"] if self.datos["enunciados"] else None
        if self.tipo_de_bloque(bid) == "test":
            sid = None
        destino = (self.i_preg + 1) if self.i_preg is not None else len(self.datos["preguntas"])
        self.datos["preguntas"].insert(destino, pregunta_vacia(sid, bid))
        self.ordenar_preguntas_por_bloque()
        self.refrescar_lista_preg(destino)
        self.refrescar_lista_sec(self.i_sec)
        self.cuaderno.select(3)
        self.txt_preg_q.focus_set()
        self._tocado()
        self.estado("Pregunta nº %d añadida al bloque %s." % (destino + 1, bid))

    def duplicar_pregunta(self):
        p = self.pregunta_actual()
        if p is None:
            return
        self.volcar_pregunta()
        copia = json.loads(json.dumps(p))
        self.datos["preguntas"].insert(self.i_preg + 1, copia)
        self.refrescar_lista_preg(self.i_preg + 1)
        self.refrescar_lista_sec(self.i_sec)
        self._tocado()

    def borrar_pregunta(self):
        p = self.pregunta_actual()
        if p is None:
            return
        if not messagebox.askyesno(
                "Borrar pregunta",
                "¿Borrar la pregunta nº %d?\n\n%s" % (self.i_preg + 1, resumen(p["q"], 70)),
                parent=self):
            return
        del self.datos["preguntas"][self.i_preg]
        self.refrescar_lista_preg(max(0, self.i_preg - 1))
        self.refrescar_lista_sec(self.i_sec)
        self._tocado()

    def mover_pregunta(self, paso):
        """Mueve la pregunta dentro de SU bloque. Para cambiarla de bloque se
        usa el desplegable «Bloque del examen»."""
        if self.i_preg is None:
            return
        destino = self.i_preg + paso
        lista = self.datos["preguntas"]
        if destino < 0 or destino >= len(lista):
            return
        if lista[destino]["bloqueId"] != lista[self.i_preg]["bloqueId"]:
            self.estado("La pregunta ya está en el borde de su bloque. Para cambiarla de "
                        "bloque usa el desplegable «Bloque del examen».")
            return
        self.volcar_pregunta()
        lista[self.i_preg], lista[destino] = lista[destino], lista[self.i_preg]
        self.refrescar_lista_preg(destino)
        self._tocado()

    # ═════════════════════════════════════════════════════════════
    #  PESTAÑA 5 — BOTONES, OPCIONES Y ENVÍO DE RESULTADOS
    # ═════════════════════════════════════════════════════════════
    def _pestana_botones(self):
        cont = MarcoScroll(self.cuaderno)
        self.cuaderno.add(cont, text="  5 · Botones y envío  ")
        m = cont.interior
        self.w_ui = {}

        ttk.Label(m, text="Botones, opciones y envío de resultados",
                  style="Titulo.TLabel").pack(anchor="w", padx=16, pady=(14, 2))
        ttk.Label(m, style="Ayuda.TLabel", wraplength=880, justify="left",
                  text="Decide qué botones ve el alumno, cómo se llaman y a dónde se mandan "
                       "los resultados. En el archivo HTML viven en los apartados «interfaz» "
                       "y «envio»."
                  ).pack(anchor="w", padx=16, pady=(0, 10))

        # ---------- A. cabecera y panel ⚙ ----------
        caja = ttk.LabelFrame(m, text=" Cabecera y panel de opciones (⚙) ")
        caja.pack(fill="x", padx=16, pady=6)
        for clave, visible, html, rotulo_texto, ayuda in CAMPOS_CABECERA:
            self._fila_interfaz(caja, clave, visible, html, ayuda, rotulo_texto)
        ttk.Frame(caja, height=6).pack()

        # ---------- B. botonera ----------
        caja = ttk.LabelFrame(m, text=" Botones de abajo y de la pantalla de resultados ")
        caja.pack(fill="x", padx=16, pady=6)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Desmarca los que no quieras que aparezcan. Los cuatro últimos son "
                       "los que salen al terminar el examen, tanto en la botonera de abajo "
                       "como en la ventana de resultados."
                  ).pack(anchor="w", padx=10, pady=(8, 6))
        for clave, visible, html, ayuda in CAMPOS_BOTONERA:
            self._fila_interfaz(caja, clave, visible, html, ayuda, "Texto del botón",
                                compacto=True)
        ttk.Frame(caja, height=6).pack()

        # ---------- C. envío de resultados ----------
        caja = ttk.LabelFrame(m, text=" Envío de resultados (formulario de Google) ")
        caja.pack(fill="x", padx=16, pady=(6, 18))

        rotulo(caja, "Dirección a la que se envían los resultados", "envio.url",
               'formulario destino del botón 📤',
               "Es la dirección del formulario terminada en /formResponse. Se obtiene "
               "abriendo el formulario, copiando su enlace y cambiando el final "
               "«/viewform» por «/formResponse». Si se deja vacía, el botón de enviar "
               "no aparece."
               ).pack(anchor="w", padx=10, pady=(10, 2))
        self.var_envio_url = tk.StringVar()
        ent = ttk.Entry(caja, textvariable=self.var_envio_url, font=("Consolas", 9))
        ent.pack(fill="x", padx=10, pady=(0, 8))
        self._vigilar(ent)

        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="CÓMO SE AVERIGUA LA CASILLA DE CADA PREGUNTA: en el formulario, menú "
                       "⋮ → «Obtener enlace autorrellenado», rellena cada campo con un valor "
                       "cualquiera y copia el enlace: dentro verás trozos como "
                       "«entry.1234567=lo-que-escribiste». Ese «entry.1234567» es lo que hay "
                       "que pegar aquí. Las casillas que dejes vacías simplemente no se envían."
                  ).pack(anchor="w", padx=10, pady=(0, 8))

        rejilla = ttk.Frame(caja, style="Panel.TFrame")
        rejilla.pack(fill="x", padx=10)
        self.w_envio = {}
        for fila, (clave, visible, que) in enumerate(CAMPOS_ENVIO):
            ttk.Label(rejilla, text=visible, style="Campo.TLabel"
                      ).grid(row=fila, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            e = ttk.Entry(rejilla, textvariable=var, font=("Consolas", 9), width=22)
            e.grid(row=fila, column=1, sticky="w", padx=10)
            self._vigilar(e)
            self.w_envio[clave] = var
            ttk.Label(rejilla, text="envio.%s   ·   %s" % (clave, que), style="Tec.TLabel"
                      ).grid(row=fila, column=2, sticky="w")

        # ── Total absoluto: todos los bloques sumados como uno solo ──
        self.var_enviar_total = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            caja, variable=self.var_enviar_total, command=self._tocado,
            text="Enviar el TOTAL de todos los bloques (recuento absoluto)"
            ).pack(anchor="w", padx=10, pady=(14, 0))
        ttk.Label(caja, style="Tec.TLabel",
                  text="envio.enviarTotal  ·  envio.total{}   ·   suma las preguntas, "
                       "aciertos, fallos, en blanco y puntos de TODOS los bloques del "
                       "intento").pack(anchor="w", padx=10)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Es lo normal cuando el examen tiene varios bloques pero un solo "
                       "formulario: se manda una única cifra para todo el examen. Si una "
                       "casilla de aquí coincidiera con la de algún bloque, manda el total."
                  ).pack(anchor="w", padx=10, pady=(0, 4))
        rejilla_total = ttk.Frame(caja, style="Panel.TFrame")
        rejilla_total.pack(fill="x", padx=10, pady=(0, 6))
        self.w_envio_total = {}
        for col, (clave, etiqueta) in enumerate(CAMPOS_ENVIO_BLOQUE):
            ttk.Label(rejilla_total, text=etiqueta, style="Tec.TLabel"
                      ).grid(row=0, column=col, sticky="w", padx=(0 if col == 0 else 6, 0))
            var = tk.StringVar()
            ent = ttk.Entry(rejilla_total, textvariable=var, font=("Consolas", 9), width=16)
            ent.grid(row=1, column=col, sticky="w", padx=(0 if col == 0 else 6, 0), pady=2)
            self._vigilar(ent)
            self.w_envio_total[clave] = var

        ttk.Label(caja, text="Casillas de cada bloque (opcional)", style="Campo.TLabel"
                  ).pack(anchor="w", padx=10, pady=(14, 0))
        ttk.Label(caja, style="Tec.TLabel",
                  text="bloques[].envio   ·   se envían solo los bloques que hayan salido "
                       "en ese intento").pack(anchor="w", padx=10)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Un juego de casillas por bloque, para llevar al formulario cuántas "
                       "preguntas tuvo cada sección y cómo fue en ella. Vienen en blanco: "
                       "úsalas solo si el formulario tiene casillas para cada bloque."
                  ).pack(anchor="w", padx=10, pady=(0, 6))
        self.marco_envio_bloques = ttk.Frame(caja, style="Panel.TFrame")
        self.marco_envio_bloques.pack(fill="x", padx=10, pady=(0, 14))
        self.w_envio_bloque = {}

        # ---------- D. segundo formulario: detalle pregunta a pregunta ----------
        caja = ttk.LabelFrame(m, text=" Envío automático del detalle pregunta a pregunta ")
        caja.pack(fill="x", padx=16, pady=(6, 18))

        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Este segundo formulario NO sustituye al de arriba: es un complemento "
                       "y se manda solo, sin que el alumno tenga que pulsar nada, en cuanto "
                       "corrige el examen (o se le agota el tiempo). Lleva el nombre del "
                       "supuesto, la fecha y hora del envío, los aciertos y los fallos en "
                       "bruto (sin baremo) y, de cada pregunta, si la acertó y qué opción "
                       "marcó: «Correcta: …» o «Incorrecta: …», y «En blanco» si no la "
                       "contestó.\n\n"
                       "Cada pregunta va SIEMPRE a la casilla de su número de orden en la "
                       "pestaña «4 · Preguntas» (la 1ª a «Pregunta 1», y así hasta 80), "
                       "aunque el intento salga aleatorizado o solo con parte de ellas. Las "
                       "preguntas que no salgan en el intento dejan su casilla vacía.\n\n"
                       "Viene ya configurado con el formulario del proyecto: no hace falta "
                       "tocar nada."
                  ).pack(anchor="w", padx=10, pady=(10, 8))

        rotulo(caja, "Dirección del formulario del detalle", "envioDetalle.url",
               "formulario que se manda solo al corregir",
               "Igual que la de arriba: la del formulario, terminada en /formResponse. "
               "Si se deja vacía, no se manda nada."
               ).pack(anchor="w", padx=10, pady=(0, 2))
        self.var_detalle_url = tk.StringVar()
        ent = ttk.Entry(caja, textvariable=self.var_detalle_url, font=("Consolas", 9))
        ent.pack(fill="x", padx=10, pady=(0, 8))
        self._vigilar(ent)

        rejilla = ttk.Frame(caja, style="Panel.TFrame")
        rejilla.pack(fill="x", padx=10)
        self.w_detalle = {}
        for fila, (clave, visible, que) in enumerate(CAMPOS_ENVIO_DETALLE):
            ttk.Label(rejilla, text=visible, style="Campo.TLabel"
                      ).grid(row=fila, column=0, sticky="w", pady=2)
            var = tk.StringVar()
            e = ttk.Entry(rejilla, textvariable=var, font=("Consolas", 9), width=22)
            e.grid(row=fila, column=1, sticky="w", padx=10)
            self._vigilar(e)
            self.w_detalle[clave] = var
            ttk.Label(rejilla, text="envioDetalle.%s   ·   %s" % (clave, que),
                      style="Tec.TLabel").grid(row=fila, column=2, sticky="w")

        ttk.Label(caja, text="Casillas de las %d preguntas" % len(ENTRADAS_PREGUNTA_DETALLE), style="Campo.TLabel"
                  ).pack(anchor="w", padx=10, pady=(14, 0))
        ttk.Label(caja, style="Tec.TLabel",
                  text="envioDetalle.preguntas   ·   una casilla por línea, en orden: "
                       "Pregunta 1, Pregunta 2 …").pack(anchor="w", padx=10)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Solo hay que tocarlas si algún día cambia el formulario. Si se "
                       "borran todas, se vuelven a poner las del proyecto."
                  ).pack(anchor="w", padx=10, pady=(0, 6))
        marco_cas = ttk.Frame(caja, style="Panel.TFrame")
        marco_cas.pack(fill="x", padx=10, pady=(0, 6))
        self.txt_detalle_preguntas = tk.Text(
            marco_cas, height=8, wrap="none", font=("Consolas", 9), relief="solid",
            borderwidth=1, background="white", foreground="#111827",
            insertbackground="#111827", padx=6, pady=4)
        barra_cas = ttk.Scrollbar(marco_cas, orient="vertical",
                                  command=self.txt_detalle_preguntas.yview)
        self.txt_detalle_preguntas.configure(yscrollcommand=barra_cas.set)
        self.txt_detalle_preguntas.pack(side="left", fill="both", expand=True)
        barra_cas.pack(side="right", fill="y")
        self._vigilar(self.txt_detalle_preguntas)
        ttk.Button(caja, text="↺  Restaurar las casillas del proyecto",
                   command=self.restaurar_casillas_detalle).pack(anchor="w", padx=10, pady=(0, 14))

    def _fila_interfaz(self, padre, clave, visible, html, ayuda, rotulo_texto,
                       compacto=False):
        """Una línea de configuración: casilla «se ve» + campos de texto."""
        base = INTERFAZ_DEFECTO[clave]
        marco = ttk.Frame(padre, style="Panel.TFrame")
        marco.pack(fill="x", padx=10, pady=(8, 2))

        campos = {}
        var_visible = tk.BooleanVar(value=True)
        cabecera = ttk.Frame(marco, style="Panel.TFrame")
        cabecera.pack(fill="x")
        ttk.Checkbutton(cabecera, text=visible, variable=var_visible,
                        command=self._tocado).pack(side="left")
        campos["visible"] = var_visible

        # Estado con el que arranca el examen (solo algunas opciones lo tienen)
        for campo, etiqueta in CAMPOS_ESTADO.items():
            if campo not in base:
                continue
            var_estado = tk.BooleanVar(value=bool(base[campo]))
            ttk.Checkbutton(cabecera, text=etiqueta, variable=var_estado,
                            command=self._tocado).pack(side="left", padx=(18, 0))
            campos[campo] = var_estado

        if compacto and "texto" in base:
            var = tk.StringVar()
            ent = ttk.Entry(cabecera, textvariable=var, font=("Georgia", 10), width=34)
            ent.pack(side="right")
            self._vigilar(ent)
            campos["texto"] = var

        ttk.Label(marco, text="interfaz.%s   →   HTML: %s" % (clave, html),
                  style="Tec.TLabel").pack(anchor="w", padx=(22, 0))
        if ayuda:
            ttk.Label(marco, text=ayuda, style="Ayuda.TLabel", wraplength=820,
                      justify="left").pack(anchor="w", padx=(22, 0))

        if not compacto:
            for campo, etiqueta in (("texto", rotulo_texto or "Texto"),
                                    ("titulo", "Título (al pasar el ratón)"),
                                    ("url", "Página de destino")):
                if campo not in base:
                    continue
                linea = ttk.Frame(marco, style="Panel.TFrame")
                linea.pack(fill="x", padx=(22, 0), pady=1)
                ttk.Label(linea, text=etiqueta + ":", style="Ayuda.TLabel", width=24
                          ).pack(side="left")
                var = tk.StringVar()
                ancho = 12 if campo == "texto" and clave == "botonCasa" else 60
                ent = ttk.Entry(linea, textvariable=var, font=("Georgia", 10), width=ancho)
                ent.pack(side="left", fill="x", expand=(ancho > 12))
                self._vigilar(ent)
                campos[campo] = var

        self.w_ui[clave] = campos

    # ---------- casillas de envío por bloque ----------
    def refrescar_envio_bloques(self):
        if not hasattr(self, "marco_envio_bloques"):
            return
        self.volcar_envio_bloques()
        for hijo in self.marco_envio_bloques.winfo_children():
            hijo.destroy()
        self.w_envio_bloque = {}

        # Cabecera de columnas
        ttk.Label(self.marco_envio_bloques, text="Bloque", style="Tec.TLabel"
                  ).grid(row=0, column=0, sticky="w")
        for col, (_clave, etiqueta) in enumerate(CAMPOS_ENVIO_BLOQUE):
            ttk.Label(self.marco_envio_bloques, text=etiqueta, style="Tec.TLabel"
                      ).grid(row=0, column=col + 1, sticky="w", padx=(6, 0))

        for fila, b in enumerate(self.datos["bloques"], start=1):
            ttk.Label(self.marco_envio_bloques,
                      text="%s · %s" % (b["id"], resumen(b["titulo"], 18)),
                      style="Campo.TLabel").grid(row=fila, column=0, sticky="w", pady=2)
            vars_bloque = {}
            for col, (clave, _etiqueta) in enumerate(CAMPOS_ENVIO_BLOQUE):
                var = tk.StringVar(value=b["envio"].get(clave, ""))
                ent = ttk.Entry(self.marco_envio_bloques, textvariable=var,
                                font=("Consolas", 9), width=16)
                ent.grid(row=fila, column=col + 1, sticky="w", padx=(6, 0), pady=2)
                self._vigilar(ent)
                vars_bloque[clave] = var
            self.w_envio_bloque[b["id"]] = vars_bloque

    def volcar_envio_bloques(self):
        if not getattr(self, "w_envio_bloque", None):
            return
        por_id = {b["id"]: b for b in self.datos["bloques"]}
        for ident, campos in self.w_envio_bloque.items():
            bloque = por_id.get(ident)
            if not bloque:
                continue
            bloque["envio"] = {c: v.get().strip() for c, v in campos.items()}

    # ---------- cargar / volcar la pestaña ----------
    def cargar_botones(self):
        interfaz = self.datos.get("interfaz") or INTERFAZ_DEFECTO
        for clave, campos in self.w_ui.items():
            ajuste = interfaz.get(clave, INTERFAZ_DEFECTO[clave])
            for campo, var in campos.items():
                por_defecto = INTERFAZ_DEFECTO[clave].get(campo, "")
                valor = ajuste.get(campo, por_defecto)
                if isinstance(var, tk.BooleanVar):
                    var.set(bool(valor))
                else:
                    var.set(str(valor))
        envio = self.datos.get("envio") or ENVIO_DEFECTO
        self.var_envio_url.set(envio.get("url", ""))
        for clave, var in self.w_envio.items():
            var.set(envio.get(clave, ""))
        self.var_enviar_total.set(bool(envio.get("enviarTotal", True)))
        total = envio.get("total") if isinstance(envio.get("total"), dict) else {}
        for clave, var in self.w_envio_total.items():
            var.set(total.get(clave, ""))
        self.refrescar_envio_bloques()

        detalle = self.datos.get("envioDetalle") or envio_detalle_por_defecto()
        self.var_detalle_url.set(detalle.get("url", ""))
        for clave, var in self.w_detalle.items():
            var.set(detalle.get(clave, ""))
        self._poner_casillas_detalle(detalle.get("preguntas")
                                     or ENTRADAS_PREGUNTA_DETALLE)

    def volcar_botones(self):
        if not getattr(self, "w_ui", None):
            return
        interfaz = {}
        for clave, base in INTERFAZ_DEFECTO.items():
            ajuste = dict(base)
            campos = self.w_ui.get(clave, {})
            for campo, var in campos.items():
                if isinstance(var, tk.BooleanVar):
                    ajuste[campo] = bool(var.get())
                else:
                    valor = var.get().strip()
                    ajuste[campo] = valor if valor else base.get(campo, "")
            interfaz[clave] = ajuste
        self.datos["interfaz"] = interfaz

        envio = {"url": self.var_envio_url.get().strip()}
        for clave, var in self.w_envio.items():
            envio[clave] = var.get().strip()
        envio["enviarTotal"] = bool(self.var_enviar_total.get())
        envio["total"] = {clave: var.get().strip()
                          for clave, var in self.w_envio_total.items()}
        self.datos["envio"] = envio
        self.volcar_envio_bloques()

        detalle = {"url": self.var_detalle_url.get().strip()}
        for clave, var in self.w_detalle.items():
            detalle[clave] = var.get().strip()
        casillas = [l.strip() for l in
                    self.txt_detalle_preguntas.get("1.0", "end").splitlines()]
        casillas = [c for c in casillas if c]
        detalle["preguntas"] = (normalizar_casillas_detalle(casillas) if casillas
                                else list(ENTRADAS_PREGUNTA_DETALLE))
        self.datos["envioDetalle"] = detalle

    # ---------- casillas del segundo formulario ----------
    def _poner_casillas_detalle(self, casillas):
        self.txt_detalle_preguntas.delete("1.0", "end")
        self.txt_detalle_preguntas.insert("1.0", "\n".join(casillas))

    def restaurar_casillas_detalle(self):
        self._poner_casillas_detalle(ENTRADAS_PREGUNTA_DETALLE)
        self._tocado()
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

    def _pestana_comprobar(self):
        panel = ttk.Frame(self.cuaderno)
        self.cuaderno.add(panel, text="  6 · Comprobar  ")

        barra = ttk.Frame(panel)
        barra.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Button(barra, text="✔  Revisar el supuesto", command=self.comprobar,
                   style="Accion.TButton").pack(side="left")
        ttk.Button(barra, text="{ }  Ver los datos que se guardarán",
                   command=self.ver_json).pack(side="left", padx=6)

        ttk.Label(panel, style="Ayuda.TLabel", wraplength=1000, justify="left",
                  text="La revisión busca despistes típicos: preguntas sin texto, opciones "
                       "repetidas o vacías, preguntas del mismo enunciado que han quedado "
                       "separadas, identificadores duplicados…"
                  ).pack(anchor="w", padx=10)

        marco, self.txt_informe = caja_texto(panel, alto=30, formato=False)
        marco.pack(fill="both", expand=True, padx=10, pady=8)
        self.txt_informe.configure(font=("Consolas", 9))
        self.txt_informe.bind("<Double-Button-1>", self._ir_desde_informe, add="+")

    def comprobar(self):
        self.volcar_todo()
        avisos, errores = [], []
        d = self.datos

        if not d["config"]["titulo"].strip():
            errores.append("Los datos generales no tienen título.")
        if int(d["config"]["minutos"]) < 1:
            errores.append("El tiempo por defecto debe ser de 1 minuto o más.")

        vistos = set()
        for e in d["enunciados"]:
            if not e["id"].strip():
                errores.append("Hay un enunciado sin identificador.")
            elif e["id"] in vistos:
                errores.append("Identificador de enunciado repetido: «%s»." % e["id"])
            vistos.add(e["id"])
            if not e["factBlocks"]:
                avisos.append("El enunciado %s no tiene ningún bloque de hechos." % e["id"])
            ids_hechos = set()
            for j, b in enumerate(e["factBlocks"], 1):
                if not b["paragraphs"]:
                    avisos.append("Enunciado %s, bloque %d: no tiene texto." % (e["id"], j))
                if b["id"] in ids_hechos:
                    errores.append("Enunciado %s: código de bloque de hechos repetido «%s»."
                                   % (e["id"], b["id"]))
                ids_hechos.add(b["id"])

        if not d["preguntas"]:
            errores.append("El supuesto no tiene ninguna pregunta.")

        # ── bloques ──
        for b in d["bloques"]:
            suyas = [q for q in d["preguntas"] if q["bloqueId"] == b["id"]]
            if not suyas:
                avisos.append("El bloque «%s» no tiene ninguna pregunta: no saldrá en el examen."
                              % b["titulo"])
            if b["acierto"] <= 0:
                errores.append("El bloque «%s» no suma nada por acierto." % b["titulo"])
            if b["porIntento"] and b["porIntento"] > len(suyas):
                avisos.append("El bloque «%s» pide %d preguntas por intento pero solo tiene %d."
                              % (b["titulo"], b["porIntento"], len(suyas)))
            if b["tipo"] == "test" and any(q["statementId"] for q in suyas):
                avisos.append("El bloque de teoría «%s» tiene preguntas con enunciado: "
                              "no se mostrará." % b["titulo"])
            sin_enunciado = [q for q in suyas if not q["statementId"]]
            if b["tipo"] == "supuesto" and sin_enunciado and len(sin_enunciado) != len(suyas):
                avisos.append("El bloque «%s» mezcla preguntas con y sin enunciado (%d sueltas)."
                              % (b["titulo"], len(sin_enunciado)))

        # ── opciones del panel de la página que dejan cosas sin usar ──
        interfaz = d.get("interfaz") or {}
        opcion_una = interfaz.get("opcionUnaEnUna") or {}
        opcion_foco = interfaz.get("opcionFoco") or {}
        con_casilla = [b for b in d["bloques"] if b.get("opcionUnaEnUna", True)]
        if opcion_una.get("visible") is False:
            avisos.append("La opción «ver las preguntas de una en una» está OCULTA (pestaña 5): "
                          "el alumno no verá las casillas de cada bloque y cada uno se quedará "
                          "como diga su modo en la pestaña 2.")
        elif not con_casilla:
            avisos.append("Ningún bloque saca su casilla en el panel ⚙ (pestaña 2): la opción "
                          "«ver las preguntas de una en una» no aparecerá.")

        vinculadas = [q for q in d["preguntas"] if q.get("factIds")]
        if opcion_foco.get("visible") is not False and not vinculadas and d["enunciados"]:
            avisos.append("El modo foco está a la vista pero ninguna pregunta tiene hechos "
                          "vinculados (pestaña 4): encenderlo no cambiará nada.")
        if vinculadas:
            if opcion_foco.get("visible") is False and not opcion_foco.get("activa"):
                avisos.append("Hay %d pregunta(s) con hechos vinculados, pero el modo foco está "
                              "oculto y no arranca activado: nunca se usarán." % len(vinculadas))
            alcanzable = [b for b in d["bloques"]
                          if b["tipo"] != "test" and (b["modo"] == "individual"
                                                      or opcion_una.get("activa")
                                                      or (b.get("opcionUnaEnUna", True)
                                                          and opcion_una.get("visible") is not False))]
            if not alcanzable:
                avisos.append("Hay preguntas con hechos vinculados, pero ningún bloque de "
                              "supuesto puede verse de una en una: el modo foco no llegará a "
                              "aplicarse (solo actúa de una en una, nunca en cadena).")

        hechos_de = {e["id"]: {b["id"] for b in e["factBlocks"]} for e in d["enunciados"]}
        ocultos_de = {e["id"]: {b["id"] for b in e["factBlocks"] if b["hidden"]}
                      for e in d["enunciados"]}

        for i, p in enumerate(d["preguntas"], 1):
            if not p["q"].strip():
                errores.append("Pregunta %d: falta el texto de la pregunta." % i)
            if p["statementId"] and p["statementId"] not in vistos:
                errores.append("Pregunta %d: apunta al enunciado «%s», que no existe."
                               % (i, p["statementId"]))
            if p.get("factIds"):
                propios = hechos_de.get(p["statementId"] or "", set())
                perdidos = [x for x in p["factIds"] if x not in propios]
                if perdidos:
                    avisos.append("Pregunta %d: vinculada a hechos que no están en su "
                                  "enunciado (%s): en modo foco mostrará el enunciado entero."
                                  % (i, ", ".join(perdidos)))
                escondidos = ocultos_de.get(p["statementId"] or "", set())
                ocultos = [x for x in p["factIds"] if x in escondidos]
                if ocultos:
                    avisos.append("Pregunta %d: vinculada a hechos marcados como «no "
                                  "mostrar» (%s)." % (i, ", ".join(ocultos)))
            vacias = [n for n, t in enumerate(p["a"]) if not t.strip()]
            if vacias:
                errores.append("Pregunta %d: opciones vacías (%s)."
                               % (i, ", ".join(LETRAS[n] for n in vacias)))
            if len(p["a"]) < MIN_OPCIONES:
                errores.append("Pregunta %d: solo tiene %d respuesta(s); hacen falta al menos %d."
                               % (i, len(p["a"]), MIN_OPCIONES))
            normal = [" ".join(t.lower().split()) for t in p["a"] if t.strip()]
            if len(set(normal)) != len(normal):
                avisos.append("Pregunta %d: hay dos opciones con el mismo texto." % i)

            correctas = p.get("correctas") or []
            if not correctas:
                errores.append("Pregunta %d: no tiene marcada ninguna respuesta correcta." % i)
            if p.get("multiple") and len(correctas) < 2:
                avisos.append("Pregunta %d: está marcada como de respuesta múltiple pero solo "
                              "tiene una correcta." % i)
            if not p.get("multiple") and len(correctas) > 1:
                avisos.append("Pregunta %d: tiene %d correctas pero NO es de respuesta múltiple: "
                              "solo se dará por buena la primera." % (i, len(correctas)))

            # Cuántas respuestas verá el alumno en esta pregunta
            cuantas = p.get("respuestas") or d["config"].get("respuestas") or len(p["a"])
            if cuantas < len(correctas) + (1 if len(p["a"]) > len(correctas) else 0):
                avisos.append("Pregunta %d: se pide que salgan %d respuestas, pero tiene %d "
                              "correctas: saldrán más para que quepan todas."
                              % (i, cuantas, len(correctas)))
            elif p.get("respuestas") and p["respuestas"] > len(p["a"]):
                avisos.append("Pregunta %d: se piden %d respuestas y solo tiene %d escritas: "
                              "saldrán las %d." % (i, p["respuestas"], len(p["a"]), len(p["a"])))
            if not p["law"].strip():
                avisos.append("Pregunta %d: sin motivación legal (la corrección saldrá vacía)." % i)

        # preguntas del mismo enunciado que no van seguidas
        orden, bloques_vistos = [], set()
        for p in d["preguntas"]:
            sid = p["statementId"]
            if not orden or orden[-1] != sid:
                if sid and sid in bloques_vistos:
                    avisos.append("Las preguntas del enunciado «%s» no van todas seguidas: "
                                  "el enunciado se repetirá, uno delante de cada grupo." % sid)
                orden.append(sid)
                if sid:
                    bloques_vistos.add(sid)

        lineas = ["REVISIÓN DEL SUPUESTO", "=" * 60, ""]
        lineas.append("Título      : %s" % d["config"]["titulo"])
        lineas.append("Referencia  : %s" % d["config"]["referencia"])
        lineas.append("Duración    : %s minutos" % d["config"]["minutos"])
        lineas.append("Enunciados  : %d" % len(d["enunciados"]))
        lineas.append("Preguntas   : %d" % len(d["preguntas"]))
        lineas.append("APTO desde  : %s%% de la puntuación" % nUm(d["config"]["aptoPorcentaje"]))
        general = d["config"].get("respuestas", 0)
        lineas.append("Respuestas  : %s"
                      % ("las que tenga escritas cada pregunta" if not general
                         else "%d por pregunta (el resto se sortean)" % general))
        multiples = sum(1 for q in d["preguntas"] if q.get("multiple"))
        propias = sum(1 for q in d["preguntas"] if q.get("respuestas"))
        if multiples or propias:
            lineas.append("              %d de respuesta múltiple · %d con nº propio de respuestas"
                          % (multiples, propias))
        cambiados = [c for c in TEMA_DEFECTO if d["tema"][c] != TEMA_DEFECTO[c]]
        lineas.append("Colores     : %s"
                      % ("los originales de la plantilla" if not cambiados
                         else "%d cambiados (%s)" % (len(cambiados), ", ".join(cambiados))))
        lineas.append("")
        lineas.append("BLOQUES (en el orden en que salen)")
        lineas.append("-" * 60)
        maximo_total = 0.0
        for i, b in enumerate(d["bloques"], 1):
            suyas = [q for q in d["preguntas"] if q["bloqueId"] == b["id"]]
            maximo = len(suyas) * b["acierto"]
            maximo_total += maximo
            lineas.append("  %d. [%s] %s  (%s)" % (i, b["id"], b["titulo"],
                                                   "teoría" if b["tipo"] == "test" else "supuesto"))
            lineas.append("     %d preguntas · máximo %s puntos" % (len(suyas), nUm(maximo)))
            lineas.append("     +%s por acierto · −%s por fallo · −%s en blanco"
                          % (nUm(b["acierto"]), nUm(b["fallo"]), nUm(b["blanco"])))
            lineas.append("     empiezan %s (%s) · en el aleatorio salen %s"
                          % ("todas seguidas" if b["modo"] == "cadena" else "de una en una",
                             "el alumno puede cambiarlo" if b.get("opcionUnaEnUna", True)
                             else "sin casilla en el panel: no se puede cambiar",
                             "todas" if not b["porIntento"] else "%d al azar" % b["porIntento"]))
            if b["tipo"] != "test":
                con_foco = sum(1 for q in suyas if q.get("factIds"))
                lineas.append("     barra del bloque %s · %s"
                              % ("encima del enunciado"
                                 if b.get("cabeceraSobreEnunciado", True) is not False
                                 else "delante de la primera pregunta",
                                 "sin preguntas vinculadas al modo foco" if not con_foco
                                 else "%d pregunta(s) vinculadas al modo foco" % con_foco))
        lineas.append("  ----------------------------------------")
        lineas.append("  Puntuación máxima del examen: %s puntos" % nUm(maximo_total))
        lineas.append("  APTO a partir de %s puntos"
                      % nUm(maximo_total * d["config"]["aptoPorcentaje"] / 100.0))
        lineas.append("")
        if errores:
            lineas.append("ERRORES QUE HAY QUE CORREGIR (%d)" % len(errores))
            lineas.append("-" * 60)
            lineas += ["  ✗ " + x for x in errores]
            lineas.append("")
        if avisos:
            lineas.append("AVISOS (revisables, no impiden guardar) (%d)" % len(avisos))
            lineas.append("-" * 60)
            lineas += ["  ! " + x for x in avisos]
            lineas.append("")
        if not errores and not avisos:
            lineas.append("✓ Todo correcto: el supuesto está listo para guardarse.")

        poner_texto(self.txt_informe, "\n".join(lineas))
        self.cuaderno.select(5)
        self.estado("Revisión: %d errores, %d avisos." % (len(errores), len(avisos)))
        return errores

    def ver_json(self):
        self.volcar_todo()
        poner_texto(self.txt_informe, datos_a_json(self.datos).replace("\\u003c", "<"))
        self.cuaderno.select(5)

    # ═════════════════════════════════════════════════════════════
    #  ABRIR / GUARDAR
    # ═════════════════════════════════════════════════════════════
    def volcar_todo(self):
        """Pasa lo escrito en la ventana a la estructura de datos."""
        self.volcar_config()
        self.volcar_botones()
        self.volcar_seccion()
        self.volcar_enunciado()
        self.volcar_pregunta()
        self.ordenar_preguntas_por_bloque()

    def _refrescar_todo(self, reiniciar=True):
        self.i_sec = 0 if self.datos["bloques"] else None
        self.i_enun = 0 if self.datos["enunciados"] else None
        self.i_bloque = self.i_hito = None
        self.i_preg = 0 if self.datos["preguntas"] else None
        self.cargar_config()
        self.cargar_botones()
        self.refrescar_lista_sec(self.i_sec)
        self.refrescar_lista_enun(self.i_enun)
        self.refrescar_lista_preg(self.i_preg)
        self._pintar_titulo()
        if reiniciar:
            self.historial.iniciar(self.datos)

    def _recordar_carpeta(self):
        if self.ruta:
            self._prefs["carpeta"] = str(self.ruta.parent)

    def _carpeta_inicial(self):
        ultima = self._prefs.get("carpeta")
        if ultima and os.path.isdir(ultima):
            return ultima
        aqui = Path(__file__).resolve().parent
        for cand in (aqui / "supuestos", aqui.parent / "supuestos", aqui):
            if cand.is_dir():
                return str(cand)
        return str(aqui)

    def _carga_inicial(self):
        if self.ruta is not None or self.hay_cambios:
            return                       # el usuario ya ha abierto algo
        base = Path(__file__).resolve().parent / PLANTILLA_BASE
        if base.exists():
            try:
                self.datos, self.modo, self.html_base = leer_html(base)
                self.ruta = None
                self.hay_cambios = False
                self._refrescar_todo()
                self.estado("Plantilla en blanco cargada desde «%s». "
                            "Al guardar se pedirá un nombre nuevo." % PLANTILLA_BASE)
                return
            except (OSError, ValueError, json.JSONDecodeError):
                pass
        self.estado("Pulsa «Abrir plantilla…» para empezar.")

    def _confirmar_descartar(self):
        if not self.hay_cambios:
            return True
        r = messagebox.askyesnocancel(
            "Cambios sin guardar",
            "Hay cambios sin guardar.\n\n¿Quieres guardarlos antes de continuar?",
            parent=self)
        if r is None:
            return False
        if r:
            return self.guardar()
        return True

    def nuevo(self):
        if not self._confirmar_descartar():
            return
        base = Path(__file__).resolve().parent / PLANTILLA_BASE
        if not base.exists():
            messagebox.showerror(
                "Falta la plantilla",
                "No encuentro «%s» junto a este programa.\n\n"
                "Copia el archivo de plantilla en la misma carpeta que "
                "editor_supuestos.py y vuelve a intentarlo." % PLANTILLA_BASE, parent=self)
            return
        self.datos, self.modo, self.html_base = leer_html(base)
        self.datos["preguntas"] = []
        self.datos["enunciados"] = []
        self.datos["bloques"] = [bloque_vacio("supuesto", "B1")]
        self.datos["config"] = datos_vacios()["config"]
        self.ruta = None
        self.hay_cambios = False
        self._refrescar_todo()
        self.estado("Supuesto nuevo en blanco. Empieza por la pestaña «1 · Datos generales».")

    def abrir(self):
        if not self._confirmar_descartar():
            return
        ruta = filedialog.askopenfilename(
            parent=self, title="Abrir plantilla de supuesto",
            initialdir=self._carpeta_inicial(),
            filetypes=[("Páginas HTML", "*.html *.htm"), ("Todos los archivos", "*.*")])
        if not ruta:
            return
        try:
            self.datos, self.modo, self.html_base = leer_html(ruta)
        except (OSError, ValueError, json.JSONDecodeError) as err:
            messagebox.showerror("No se ha podido abrir",
                                 "%s\n\n%s" % (Path(ruta).name, err), parent=self)
            return
        self.ruta = Path(ruta)
        self._recordar_carpeta()
        self.hay_cambios = False
        self._refrescar_todo()
        self._ofrecer_recuperacion()
        self.estado("Abierto: %s  (%d enunciados, %d preguntas)"
                    % (self.ruta.name, len(self.datos["enunciados"]),
                       len(self.datos["preguntas"])))
        if self.modo == "js-sin-config":
            messagebox.showwarning(
                "Plantilla antigua",
                "Este archivo usa la plantilla ANTIGUA: el título, la referencia, el ámbito y "
                "los minutos están escritos a mano dentro del HTML y no en un apartado de datos.\n\n"
                "Se han cargado bien los enunciados y las preguntas, y se guardarán bien, pero "
                "los cambios de la pestaña «1 · Datos generales» NO se aplicarán a este archivo.\n\n"
                "Recomendación: usa «Guardar como…» sobre una copia de %s." % PLANTILLA_BASE,
                parent=self)
        elif self.modo == "js":
            self.estado(self.lbl_estado.cget("text") + "   ·   formato JavaScript (plantilla clásica)")
        else:
            plantilla = self._plantilla_base()
            if plantilla and version_motor(self.html_base) < version_motor(plantilla):
                self.estado(self.lbl_estado.cget("text") +
                            "   ·   página de una versión anterior: al guardar se ofrecerá "
                            "ponerla al día")

    def _nombre_sugerido(self):
        texto = self.datos["config"]["titulo"].lower()
        cambios = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
        for a, b in cambios.items():
            texto = texto.replace(a, b)
        texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
        return (texto or "supuesto")[:48] + ".html"

    def guardar(self):
        self.volcar_todo()
        if self.ruta is None:
            return self.guardar_como()
        return self._escribir(self.ruta)

    def guardar_como(self):
        self.volcar_todo()
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar supuesto como…",
            initialdir=self._carpeta_inicial(),
            initialfile=self._nombre_sugerido(),
            defaultextension=".html",
            filetypes=[("Páginas HTML", "*.html"), ("Todos los archivos", "*.*")])
        if not ruta:
            return False
        return self._escribir(Path(ruta))

    def convertir_a_plantilla_nueva(self):
        """Vuelca el supuesto abierto sobre una copia de la plantilla nueva.

        Sirve para modernizar los supuestos antiguos (los que llevan el
        título escrito a mano dentro del HTML): a partir de la conversión,
        los datos generales también se editan desde el programa.

        Para los archivos que YA usan la plantilla nueva no hace falta:
        al guardar, el editor detecta solo si la página se quedó en una
        versión anterior y ofrece rehacerla."""
        self.volcar_todo()
        base = Path(__file__).resolve().parent / PLANTILLA_BASE
        if not base.exists():
            messagebox.showerror(
                "Falta la plantilla",
                "No encuentro «%s» junto a este programa." % PLANTILLA_BASE, parent=self)
            return False
        ruta = filedialog.asksaveasfilename(
            parent=self, title="Guardar sobre la plantilla nueva…",
            initialdir=self._carpeta_inicial(),
            initialfile=self._nombre_sugerido(),
            defaultextension=".html",
            filetypes=[("Páginas HTML", "*.html"), ("Todos los archivos", "*.*")])
        if not ruta:
            return False
        self.html_base = base.read_text(encoding="utf-8")
        self.modo = "json"
        if self._escribir(Path(ruta)):
            messagebox.showinfo(
                "Convertido",
                "Supuesto guardado con la plantilla nueva.\n\n"
                "A partir de ahora también se pueden cambiar desde el programa el "
                "título, la referencia, el ámbito y los minutos, y la página estrena "
                "el motor actual de la plantilla.", parent=self)
            return True
        return False

    def _plantilla_base(self):
        """La plantilla que viene junto al programa, si está."""
        base = Path(__file__).resolve().parent / PLANTILLA_BASE
        if not base.exists():
            return None
        try:
            return base.read_text(encoding="utf-8")
        except OSError:
            return None

    def _poner_motor_al_dia(self):
        """Si el archivo abierto se quedó con una versión anterior de la
        PÁGINA, ofrece rehacerla con la plantilla actual.

        Al guardar solo se sustituyen los datos dentro del HTML, así que un
        supuesto creado hace meses conserva su página tal cual, sin las
        mejoras posteriores de la plantilla. Aquí se detecta y se arregla,
        que es justo lo que uno espera al guardar."""
        if self.modo != "json":
            return          # las plantillas antiguas van por «⇪ Pasar a plantilla nueva…»
        plantilla = self._plantilla_base()
        if plantilla is None:
            return
        nueva = version_motor(plantilla)
        vieja = version_motor(self.html_base)
        if vieja >= nueva:
            return          # ya está al día

        if not messagebox.askyesno(
                "Poner la página al día",
                "Este supuesto se creó con una versión anterior de la plantilla, así que "
                "su página no tiene las mejoras que sí trae la plantilla que acompaña al "
                "programa.\n\n"
                "Si NO se actualiza, se guardarán los datos nuevos pero la página seguirá "
                "comportándose como el día en que se creó el archivo: es lo que hace que "
                "opciones nuevas del editor no se noten al abrir el supuesto.\n\n"
                "¿Rehacer la página con la plantilla actual?\n"
                "(No se toca ni una pregunta: solo se cambia el armazón. Del archivo "
                "anterior queda una copia .bak.)", parent=self):
            self.estado("Guardado SIN actualizar la página: las novedades de la plantilla "
                        "no se verán en este archivo.")
            return

        self.html_base = plantilla
        self.estado("Página rehecha con la plantilla actual (versión %d)." % nueva)

    def _escribir(self, destino):
        self._prefs["carpeta"] = str(Path(destino).parent)
        self._poner_motor_al_dia()
        if self.modo != "json" and bloques_se_pierden(self.datos):
            seguir = messagebox.askyesno(
                "La plantilla clásica no tiene bloques",
                "Este archivo usa la plantilla CLÁSICA, que no conoce los bloques: solo "
                "guarda una lista de preguntas seguidas.\n\n"
                "Si guardas aquí se conservan todas las preguntas y su orden, pero se "
                "PIERDEN los bloques, sus colores, su baremo, la sección de teoría, la "
                "paleta de colores y los ajustes de botones y de envío.\n\n"
                "Lo recomendable es cerrar este aviso y usar «⇪ Pasar a plantilla nueva…».\n\n"
                "¿Guardar de todas formas?", parent=self)
            if not seguir:
                return False
        try:
            self.html_base = escribir_html(destino, self.html_base, self.datos, self.modo)
        except (OSError, ValueError) as err:
            messagebox.showerror("No se ha podido guardar", str(err), parent=self)
            return False
        self.ruta = Path(destino)
        self.hay_cambios = False
        self._pintar_titulo()
        self.estado("Guardado en %s   (%d preguntas)"
                    % (self.ruta, len(self.datos["preguntas"])))
        self._borrar_recuperacion()
        self._alta_en_menu()
        self.refrescar_para_subir()
        return True

    def refrescar_para_subir(self):
        """Tras guardar: deja la carpeta PARA_SUBIR al día con lo que se ha cambiado."""
        res = sincronizar_local.refrescar_silencioso(self.ruta) if self.ruta else None
        if res:
            self.estado(self.lbl_estado.cget("text") + "   ·   " + sincronizar_local.resumen(*res))

    def _alta_en_menu(self):
        """Mantiene al día la tarjeta del supuesto en el menú principal
        (supuestos-datos.js). Si el supuesto ya estaba, solo actualiza su
        título, referencia y descripción; si es nuevo, pregunta en qué grupo
        ponerlo. No hace nada si el archivo no está en «supuestos/»."""
        try:
            ruta_menu = ruta_menu_de(self.ruta)
            if ruta_menu is None:
                return
            texto, menu = leer_menu(ruta_menu)
            archivo = self.ruta.stem
            grupo = grupo_en_menu(menu, archivo)
            if grupo:
                for it in lista_de_grupo(menu, grupo):
                    if it.get("archivo") == archivo:
                        it.update({k: v for k, v in ficha_menu(archivo, self.datos).items()
                                   if k != "letra"})
                escribir_menu(ruta_menu, texto, menu)
                self.estado(self.lbl_estado.cget("text") + "   ·   menú actualizado")
                return
            self._destinos_menu = menu_datos.destinos(menu)
            elegido = self._pedir_grupo_menu(archivo)
            if not elegido:
                self.estado(self.lbl_estado.cget("text") + "   ·   sin añadir al menú")
                return
            clave, letra = elegido
            lista_de_grupo(menu, clave).append(ficha_menu(archivo, self.datos, letra))
            escribir_menu(ruta_menu, texto, menu)
            self.estado(self.lbl_estado.cget("text") + "   ·   añadido al menú (%s)" % clave)
        except (OSError, ValueError) as err:
            messagebox.showwarning(
                "Menú principal",
                "El supuesto se ha guardado, pero no he podido tocar %s:\n\n%s\n\n"
                "Añade su tarjeta a mano (las instrucciones están al principio de ese archivo)."
                % (ARCHIVO_MENU, err), parent=self)

    def _pedir_grupo_menu(self, archivo):
        """Pequeño diálogo: ¿en qué grupo del menú va este supuesto?
        Devuelve (grupo, letra) o None si se cancela."""
        ventana = tk.Toplevel(self)
        ventana.title("Añadir al menú principal")
        ventana.transient(self)
        ventana.resizable(False, False)
        marco = ttk.Frame(ventana, padding=16)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, wraplength=380, justify="left",
                  text="«%s» todavía no está en el menú principal de la web.\n"
                       "¿En qué sección y grupo lo pongo?" % archivo).pack(anchor="w", pady=(0, 8))
        sitios = self._destinos_menu or list(GRUPOS_MENU)
        grupo = tk.StringVar(value="generales/avanzados" if any(c == "generales/avanzados" for c, _ in sitios) else sitios[0][0])
        for clave, etiqueta in sitios:
            ttk.Radiobutton(marco, text=etiqueta, value=clave, variable=grupo).pack(anchor="w")
        fila = ttk.Frame(marco)
        fila.pack(fill="x", pady=(10, 0))
        ttk.Label(fila, text="Texto del círculo (1-4 caracteres):").pack(side="left")
        letra = tk.StringVar(value=archivo.replace("supuesto_", "").upper()[:4])
        ttk.Entry(fila, textvariable=letra, width=6).pack(side="left", padx=6)
        resultado = []

        def aceptar():
            resultado.append((grupo.get(), (letra.get().strip() or "?")[:4]))
            ventana.destroy()

        botones = ttk.Frame(marco)
        botones.pack(fill="x", pady=(14, 0))
        ttk.Button(botones, text="Añadir al menú", command=aceptar).pack(side="right")
        ttk.Button(botones, text="Ahora no", command=ventana.destroy).pack(side="right", padx=(0, 6))
        ventana.grab_set()
        self.wait_window(ventana)
        return resultado[0] if resultado else None

    def ver_navegador(self):
        if self.ruta is None or self.hay_cambios:
            if not messagebox.askyesno(
                    "Guardar antes de ver",
                    "Para verlo en el navegador hay que guardar el archivo.\n\n¿Guardo ahora?",
                    parent=self):
                return
            if not self.guardar():
                return
        webbrowser.open(self.ruta.resolve().as_uri())
        self.estado("Abierto en el navegador: %s" % self.ruta.name)

    def _al_cerrar(self):
        self.volcar_todo()
        self._prefs["geometria"] = self.geometry()
        _guardar_prefs(self._prefs)
        if self.hay_cambios:
            r = messagebox.askyesnocancel(
                "Salir", "Hay cambios sin guardar.\n\n¿Guardarlos antes de salir?", parent=self)
            if r is None:
                return
            if r and not self.guardar():
                return
        if self._normas_sucio:
            r = messagebox.askyesnocancel(
                "Salir", "La lista de normas (pestaña 7) tiene cambios sin guardar.\n\n¿Guardarlas antes de salir?",
                parent=self)
            if r is None:
                return
            if r:
                self._norma_guardar_archivo()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  7. ARRANQUE
# ══════════════════════════════════════════════════════════════════════

def main():
    try:                       # la primera vez, lo que hay ahora cuenta como «lo descargado de GitHub»
        if sincronizar_local.es_proyecto(sincronizar_local.RAIZ_DEFECTO):
            sincronizar_local.asegurar_base(sincronizar_local.RAIZ_DEFECTO)
    except OSError:
        pass
    app = EditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()

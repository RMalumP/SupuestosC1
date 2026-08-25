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
import webbrowser
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from tkinter import font as tkfont

APP_TITULO = "Editor de Supuestos — plantilla ECAP C1"
PLANTILLA_BASE = "supuesto_plantilla_python.html"   # se busca junto a este .py

# Paleta (a juego con la plantilla)
C_FONDO = "#f3ece4"
C_PANEL = "#fffef9"
C_TINTA = "#3d2a20"
C_TEC   = "#8a6f5c"     # texto técnico (nombre del campo / HTML)
C_AYUDA = "#6b7280"
C_ROJO  = "#8b1a1a"
C_VERDE = "#1a4731"

# Paleta original de la plantilla. Cada clave sustituye a una variable CSS
# de :root, y con ella cambian también todas las transparencias derivadas.
TEMA_DEFECTO = {
    "fondo":        "#3d2a20",
    "barra":        "#5c4033",
    "acento":       "#8fc4d9",
    "acentoClaro":  "#b8dceb",
    "azulProfundo": "#2f6f93",
    "textoClaro":   "#fdf8f0",
    "tarjeta":      "#fffef9",
    "fondoHechos":  "#f7ece7",
    "texto":        "#1a1a2e",
    "gris":         "#4a5568",
    "rojo":         "#8b1a1a",
    "verde":        "#1a4731",
}

# (clave, nombre visible, variable CSS, qué pinta exactamente)
CAMPOS_TEMA = [
    ("fondo", "Fondo de la página", "--navy",
     "Solo el fondo del documento, detrás de las tarjetas."),
    ("barra", "Barra superior, paneles y chips oscuros", "--navy-mid",
     "Cabecera, temporizador, panel ⚙, marcador, botones oscuros y los chips: "
     "insignia del expediente, letras A/B/C/D, línea de tiempo y cabecera de la "
     "motivación legal."),
    ("acento", "Color de acento", "--gold",
     "Bordes, líneas, rótulos pequeños, cifras del temporizador y píldoras de la cabecera."),
    ("acentoClaro", "Acento claro (al pasar el ratón)", "--gold-lt",
     "Variante clara del acento: botones y casillas al pasar por encima."),
    ("azulProfundo", "Azul profundo", "--blue-deep",
     "Detalles finos de la cabecera institucional y de los enunciados."),
    ("textoClaro", "Texto sobre fondo oscuro", "--cream",
     "Textos escritos encima de la barra, del marcador y de los modales."),
    ("tarjeta", "Fondo de las tarjetas", "--paper",
     "Fondo de cada pregunta, del enunciado y de las cabeceras de bloque."),
    ("fondoHechos", "Fondo de los bloques de hechos", "--parch",
     "Recuadros de la narración de hechos del supuesto (efecto pergamino)."),
    ("texto", "Texto principal y titulares", "--ink",
     "Preguntas, opciones, títulos del expediente y de cada bloque, y el texto "
     "escrito encima del color de acento."),
    ("gris", "Texto secundario", "--slate",
     "Motivación legal, referencias, notas pequeñas y textos de apoyo."),
    ("rojo", "Rojo de fallos y hechos críticos", "--crimson",
     "Respuestas falladas, bloques de hechos desencadenantes e hitos críticos."),
    ("verde", "Verde de aciertos y consejos", "--forest",
     "Respuestas acertadas y recuadro del consejo 💡."),
]

# ── BOTONES Y RÓTULOS DE LA PÁGINA ───────────────────────────────────────
# Cada clave gobierna un elemento (o pareja de elementos) del HTML.
INTERFAZ_DEFECTO = {
    "botonCasa":   {"visible": True, "texto": "🏠", "titulo": "Volver al menú principal",
                    "url": "../index.html"},
    "botonConfig": {"visible": True, "titulo": "Configuración"},
    "botonPlegar": {"visible": True, "titulo": "Plegar: ver solo el bloque actual",
                    "plegado": False},
    "opcionTiempo":   {"visible": True, "texto": "Duración del examen (mm:ss)"},
    "opcionCorregir": {"visible": True, "texto": "Corregir pregunta a pregunta",
                       "activa": False},
    "opcionUnaEnUna": {"visible": True, "texto": "Ver las preguntas de una en una",
                       "activa": False},
    "opcionFoco":     {"visible": True,
                       "texto": "Modo foco: solo los hechos de cada pregunta",
                       "activa": False},
    "opcionQtags":    {"visible": True, "texto": "Ocultar las etiquetas de pregunta",
                       "activa": False},
    "btnAnterior":      {"visible": True, "texto": "← Anterior"},
    "btnSiguiente":     {"visible": True, "texto": "Siguiente →"},
    "btnCorregir":      {"visible": True, "texto": "✓ Corregir Expediente"},
    "btnVerCorreccion": {"visible": True, "texto": "✓ Ver Corrección Completa"},
    "btnImprimir":      {"visible": True, "texto": "🖨 Imprimir / PDF"},
    "btnReintentar":    {"visible": True, "texto": "🔀 Nuevo Intento (Aleatorio)"},
    "btnEnviar":        {"visible": True, "texto": "📤 Enviar Resultados"},
    "btnMenu":          {"visible": True, "texto": "🏠 Volver al Menú Principal"},
}

# Campos de sí/no que, además de "se ve", tiene alguna opción: con qué
# estado arranca el examen. El alumno puede cambiarlo luego desde el ⚙.
CAMPOS_ESTADO = {
    "activa":  "Empieza activada",
    "plegado": "Empieza plegada",
}

# Elementos de la CABECERA (botones y opciones del panel ⚙)
# (clave, nombre visible, elemento HTML, rótulo del campo de texto, ayuda)
CAMPOS_CABECERA = [
    ("botonCasa", "Botón de inicio 🏠", '<button id="home-btn-top">', "Icono",
     "Botón de la cabecera que devuelve al menú principal. Debajo se elige a qué "
     "página lleva."),
    ("botonConfig", "Botón de configuración ⚙", '<button id="settings-toggle">', None,
     "Abre el panel de opciones del alumno. Si lo ocultas, no podrá cambiar el tiempo "
     "ni las opciones de abajo."),
    ("botonPlegar", "Botón de plegar la cabecera ⌃", '<button id="fold-btn">', None,
     "Deja a la vista solo la fila del bloque en el que está. Solo aparece cuando el "
     "examen tiene más de un bloque. Con «Empieza plegada», cada intento arranca "
     "mostrando una sola fila."),
    ("opcionTiempo", "Opción: cambiar la duración", '<div class="settings-row" id="row-tiempo">',
     "Texto", "Permite al alumno fijar otro tiempo. Ocúltala para que el examen dure "
     "siempre lo que hayas puesto en la pestaña 1."),
    ("opcionCorregir", "Opción: corregir pregunta a pregunta",
     '<div class="settings-row" id="row-corregir">', "Texto",
     "Enseña la solución nada más responder cada pregunta. Marca «Empieza activada» "
     "para que el examen arranque ya en ese modo."),
    ("opcionUnaEnUna", "Opción: ver las preguntas de una en una",
     '<div class="settings-row" id="row-una">', "Texto",
     "Anula el modo «en cadena» de los bloques que lo tengan. Con «Empieza activada», "
     "el examen arranca mostrando una sola pregunta cada vez."),
    ("opcionFoco", "Opción: modo foco (dentro de «una en una»)",
     '<div class="settings-row settings-sub" id="row-foco">', "Texto",
     "Sub-opción del panel ⚙ que cuelga de «ver las preguntas de una en una». Con el "
     "modo foco encendido, cada pregunta que esté vinculada a bloques de hechos "
     "concretos (pestaña «4 · Preguntas») muestra SOLO esa parte del enunciado, con un "
     "botón para desplegarlo entero; las preguntas sin vínculo siguen viendo el "
     "enunciado completo. La fila se apaga sola mientras no haya ningún bloque de "
     "supuesto viéndose de una en una."),

    ("opcionQtags", "Opción: ocultar las etiquetas de pregunta",
     '<div class="settings-row" id="row-qtags">', "Texto",
     "Oculta las etiquetas de materia que aparecen encima de cada pregunta. Con "
     "«Empieza activada», arrancan ya ocultas."),
]

# Botones de la BOTONERA y de la ventana de corrección
# (clave, nombre visible, elemento HTML, ayuda)
CAMPOS_BOTONERA = [
    ("btnAnterior", "Anterior", '<button id="prev-btn">',
     "Retrocede una pregunta."),
    ("btnSiguiente", "Siguiente", '<button id="next-btn">',
     "Avanza una pregunta."),
    ("btnCorregir", "Corregir el examen", '<button id="check-btn">',
     "Termina el examen y lo corrige. Está visible desde el principio."),
    ("btnVerCorreccion", "Ver corrección completa", '<button id="ov-corr-btn">',
     "En la ventana de resultados: despliega la corrección de todas las preguntas."),
    ("btnImprimir", "Imprimir / PDF", '#print-btn  ·  #ov-print-btn',
     "Aparece al terminar, abajo y en la ventana de resultados."),
    ("btnReintentar", "Nuevo intento aleatorio", '#restart-btn  ·  #ov-restart-btn',
     "Aparece al terminar. Abre la elección de tipo de aleatoriedad."),
    ("btnEnviar", "Enviar resultados", '#send-btn  ·  #ov-send-btn',
     "Aparece al terminar. Si no hay dirección de envío configurada, no se muestra "
     "aunque esté marcado."),
    ("btnMenu", "Volver al menú principal", '#home-btn-bottom  ·  #ov-home-btn',
     "Aparece al terminar, abajo y en la ventana de resultados."),
]

# ── ENVÍO DE RESULTADOS A UN FORMULARIO DE GOOGLE ────────────────────────
# Los datos generales del intento. Los recuentos (preguntas, aciertos,
# fallos, en blanco y puntos) NO van aquí: cada bloque tiene los suyos, y
# con un solo bloque ese bloque es el examen entero.
ENVIO_DEFECTO = {
    "url": ("https://docs.google.com/forms/d/e/"
            "1FAIpQLSd9h52UH7XzaRDRSIxSevScmqKZC28Fvtfnp39drKtC5SiwGA/formResponse"),
    "examen": "entry.241409513",
    "usuario": "entry.1810433543",
    "tiempoAsignado": "entry.1069013600",
    "tiempoEmpleado": "entry.815398067",
}

# (clave, nombre visible, qué valor se manda)
CAMPOS_ENVIO = [
    ("examen",         "Examen",          "el título del supuesto (pestaña 1)"),
    ("usuario",        "Alumno",          "el nombre que escribe al pulsar Enviar"),
    ("tiempoAsignado", "Tiempo asignado", "mm:ss"),
    ("tiempoEmpleado", "Tiempo empleado", "mm:ss"),
]

ENVIO_BLOQUE_DEFECTO = {"preguntas": "", "aciertos": "", "fallos": "",
                        "blancos": "", "puntos": ""}

# Casillas que ya usaba el formulario del proyecto: se asignan al primer
# bloque, que con un único bloque equivale al examen completo.
ENVIO_BLOQUE_PRIMERO = {
    "preguntas": "entry.771114786",
    "aciertos":  "entry.1903892811",
    "fallos":    "entry.1155230396",
    "blancos":   "entry.943386498",
    "puntos":    "",
}

# Recuentos que antes iban sueltos: si un archivo antiguo los trae, se
# trasladan al primer bloque en lugar de perderse.
EQUIVALENCIA_ENVIO_ANTIGUO = {
    "total": "preguntas", "aciertos": "aciertos",
    "fallos": "fallos", "blancos": "blancos", "puntos": "puntos",
}

CAMPOS_ENVIO_BLOQUE = [
    ("preguntas", "Preguntas"), ("aciertos", "Aciertos"), ("fallos", "Fallos"),
    ("blancos", "En blanco"), ("puntos", "Puntos"),
]

# Colores por defecto de cada tipo de bloque (los del HTML)
LOGO_POR_DEFECTO = ("https://academia.ecap.es/pluginfile.php?file=%2F1%2Fcore_admin"
                    "%2Flogo%2F0x200%2F1782109950%2FACADEMIA%20VIRTUAL%20%281%29.png")

COLOR_SUPUESTO = "#8fc4d9"      # azul de la plantilla
COLOR_TEST     = "#e0ac4a"      # ámbar, para distinguir la teoría


# ══════════════════════════════════════════════════════════════════════
#  1. MODELO DE DATOS
# ══════════════════════════════════════════════════════════════════════

def datos_vacios():
    """Estructura mínima de un supuesto recién creado."""
    return {
        "config": {
            "titulo": "Nuevo supuesto",
            "referencia": "EXP-000/2025",
            "ambito": "Legislación vigente",
            "minutos": 30,
            "aptoPorcentaje": 50,
            "logo": LOGO_POR_DEFECTO,
            "logoAlt": "ECAP - Escuela Ciudadana de Administración Pública",
            "organismo": "Comunidad ECAP ASS C1",
        },
        "tema": dict(TEMA_DEFECTO),
        "interfaz": {k: dict(v) for k, v in INTERFAZ_DEFECTO.items()},
        "envio": dict(ENVIO_DEFECTO),
        "bloques": [bloque_vacio("supuesto", "B1", primero=True)],
        "enunciados": [],
        "preguntas": [],
    }


def bloque_vacio(tipo="supuesto", sugerencia_id="B1", primero=False):
    """Un bloque es una sección del examen: un supuesto práctico (con
    enunciados) o una tanda de teoría tipo test."""
    es_test = (tipo == "test")
    return {
        "id": sugerencia_id,
        "tipo": "test" if es_test else "supuesto",
        "titulo": "Teoría" if es_test else "Supuesto práctico",
        "color": COLOR_TEST if es_test else COLOR_SUPUESTO,
        "modo": "cadena" if es_test else "individual",
        "cabeceraSobreEnunciado": True,
        "porIntento": 0,
        "acierto": 1.0,
        "fallo": 0.0,
        "blanco": 0.0,
        "envio": dict(ENVIO_BLOQUE_PRIMERO if primero else ENVIO_BLOQUE_DEFECTO),
    }


def enunciado_vacio(sugerencia_id="E1"):
    return {
        "id": sugerencia_id,
        "number": sugerencia_id.lstrip("Ee") or "1",
        "title": "Título del expediente",
        "ref": "REF-000",
        "ambito": "Materias que abarca",
        "factBlocks": [],
        "timeline": [],
    }


def bloque_hechos_vacio(ident="H1"):
    """Un trozo de la narración de hechos. El identificador (H1, H2…) NO se
    ve en la página: sirve para que una pregunta pueda vincularse a este
    hecho concreto y el modo foco recorte el enunciado a esa parte."""
    return {"id": ident, "title": "Título del bloque de hechos", "paragraphs": [""],
            "red": False, "hidden": False}


def nuevo_id_hecho(enunciado):
    """Primer H libre dentro de ese enunciado."""
    usados = {str(b.get("id") or "") for b in (enunciado.get("factBlocks") or [])}
    n = 1
    while ("H%d" % n) in usados:
        n += 1
    return "H%d" % n


def hito_vacio():
    return {"date": "01/01/2025", "text": "Descripción del hito",
            "red": False, "hidden": False}


def pregunta_vacia(statement_id=None, bloque_id="B1"):
    return {
        "bloqueId": bloque_id,
        "statementId": statement_id,
        # Bloques de hechos concretos de los que depende la pregunta
        # (su hecho desencadenante). Solo se usan en el modo foco.
        "factIds": [],
        "tag": "",
        "q": "Texto de la pregunta",
        "a": ["Opción correcta", "Opción incorrecta", "Opción incorrecta", "Opción incorrecta"],
        "c": 0,
        "law": "",
        "tip": "",
    }


def normalizar(datos):
    """Rellena las claves que falten para que la interfaz nunca reviente."""
    base = datos_vacios()
    cfg = dict(base["config"])
    cfg.update(datos.get("config") or {})
    try:
        cfg["minutos"] = int(float(str(cfg.get("minutos", 30)).replace(",", ".")))
    except (TypeError, ValueError):
        cfg["minutos"] = 30
    cfg["aptoPorcentaje"] = min(100.0, max(0.0, numero(cfg.get("aptoPorcentaje"), 50.0)))
    for k in ("titulo", "referencia", "ambito", "logo", "logoAlt", "organismo"):
        cfg[k] = "" if cfg.get(k) is None else str(cfg.get(k))

    # ── tema (colores de la página) ───────────────────────────────────
    tema_bruto = datos.get("tema") or {}
    tema = {clave: color_valido(tema_bruto.get(clave), valor)
            for clave, valor in TEMA_DEFECTO.items()}

    # ── interfaz (botones y rótulos) ──────────────────────────────────
    interfaz_bruta = datos.get("interfaz") or {}
    interfaz = {}
    for clave, base_clave in INTERFAZ_DEFECTO.items():
        ajuste = dict(base_clave)
        dado = interfaz_bruta.get(clave) or {}
        if isinstance(dado, dict):
            ajuste["visible"] = bool(dado.get("visible", True))
            for campo in CAMPOS_ESTADO:
                if campo in base_clave:
                    ajuste[campo] = bool(dado.get(campo, base_clave[campo]))
            for campo in ("texto", "titulo", "url"):
                if campo in base_clave and dado.get(campo) is not None:
                    ajuste[campo] = str(dado.get(campo))
        interfaz[clave] = ajuste

    # ── envío de resultados ───────────────────────────────────────────
    # Un archivo que nunca ha tenido apartado de envío (por ejemplo uno de
    # los antiguos) estrena la configuración del proyecto; si lo tiene, se
    # respeta tal cual, incluso con casillas vacías a propósito.
    sin_configurar = ("envio" not in datos and
                      not any((b or {}).get("envio") for b in (datos.get("bloques") or [])))
    envio_bruto = datos.get("envio") or (dict(ENVIO_DEFECTO) if sin_configurar else {})
    envio = {clave: str(envio_bruto.get(clave, "") or "").strip()
             for clave in ENVIO_DEFECTO}
    # Casillas de recuento que en versiones anteriores iban sueltas
    heredadas = {destino: str(envio_bruto.get(origen, "") or "").strip()
                 for origen, destino in EQUIVALENCIA_ENVIO_ANTIGUO.items()}

    # ── bloques ───────────────────────────────────────────────────────
    brutos = datos.get("bloques") or []
    bloques, usados = [], set()
    for i, b in enumerate(brutos):
        tipo = "test" if str(b.get("tipo")) == "test" else "supuesto"
        nb = bloque_vacio(tipo, "B%d" % (i + 1))
        ident = re.sub(r"[^A-Za-z0-9_-]", "", str(b.get("id") or "")) or ("B%d" % (i + 1))
        while ident in usados:
            ident += "x"
        usados.add(ident)
        nb["id"] = ident
        nb["titulo"] = str(b.get("titulo") or nb["titulo"])
        nb["color"] = color_valido(b.get("color"), nb["color"])
        modo = str(b.get("modo") or "")
        nb["modo"] = modo if modo in ("cadena", "individual") else nb["modo"]
        nb["cabeceraSobreEnunciado"] = b.get("cabeceraSobreEnunciado") is not False
        try:
            nb["porIntento"] = max(0, int(b.get("porIntento") or 0))
        except (TypeError, ValueError):
            nb["porIntento"] = 0
        env_bruto = b.get("envio") or {}
        nb["envio"] = {clave: str(env_bruto.get(clave, "") or "").strip()
                       for clave in ENVIO_BLOQUE_DEFECTO}
        if i == 0:      # el primer bloque hereda las casillas sueltas antiguas
            for clave, valor in heredadas.items():
                if valor and not nb["envio"].get(clave):
                    nb["envio"][clave] = valor
            if sin_configurar:
                nb["envio"] = dict(ENVIO_BLOQUE_PRIMERO)
        nb["acierto"] = numero(b.get("acierto"), 1.0)
        nb["fallo"] = abs(numero(b.get("fallo"), 0.0))
        nb["blanco"] = abs(numero(b.get("blanco"), 0.0))
        bloques.append(nb)
    if not bloques:
        # Sin bloques declarados: uno solo, que es el examen entero
        bloques = [bloque_vacio("supuesto", "B1", primero=sin_configurar)]
    ids_bloque = [b["id"] for b in bloques]
    tipos = {b["id"]: b["tipo"] for b in bloques}

    enunciados = []
    for e in (datos.get("enunciados") or []):
        n = enunciado_vacio()
        n.update({k: v for k, v in e.items() if v is not None})
        n["id"] = str(n.get("id") or "E1")
        n["number"] = str(n.get("number") or "")
        for k in ("title", "ref", "ambito"):
            n[k] = str(n.get(k) or "")
        bloques_hechos = []
        ids_hechos = set()
        for pos, fb in enumerate(e.get("factBlocks") or [], 1):
            b = bloque_hechos_vacio()
            ident = re.sub(r"[^A-Za-z0-9_-]", "", str(fb.get("id") or ""))
            if not ident:
                ident = "H%d" % pos
            while ident in ids_hechos:
                ident += "x"
            ids_hechos.add(ident)
            b["id"] = ident
            b["title"] = str(fb.get("title") or "")
            parr = fb.get("paragraphs") or []
            b["paragraphs"] = [str(p) for p in parr] if isinstance(parr, list) else [str(parr)]
            b["red"] = bool(fb.get("red"))
            b["hidden"] = bool(fb.get("hidden"))
            bloques_hechos.append(b)
        n["factBlocks"] = bloques_hechos
        hitos = []
        for t in (e.get("timeline") or []):
            h = hito_vacio()
            h["date"] = str(t.get("date") or "")
            h["text"] = str(t.get("text") or "")
            h["red"] = bool(t.get("red"))
            h["hidden"] = bool(t.get("hidden"))
            hitos.append(h)
        n["timeline"] = hitos
        enunciados.append(n)

    hechos_por_enunciado = {e["id"]: [b["id"] for b in e["factBlocks"]]
                            for e in enunciados}

    preguntas = []
    for p in (datos.get("preguntas") or []):
        q = pregunta_vacia()
        bid = str(p.get("bloqueId") or "")
        q["bloqueId"] = bid if bid in ids_bloque else ids_bloque[0]
        sid = p.get("statementId")
        q["statementId"] = str(sid) if sid else None
        if tipos[q["bloqueId"]] == "test":
            q["statementId"] = None      # la teoría nunca lleva enunciado
        # Vínculos con bloques de hechos: solo valen los que existan de
        # verdad dentro del enunciado al que apunta la pregunta.
        propios = hechos_por_enunciado.get(q["statementId"] or "", [])
        brutos = p.get("factIds")
        brutos = brutos if isinstance(brutos, list) else []
        vistos_f = set()
        q["factIds"] = [x for x in (str(y) for y in brutos)
                        if x in propios and not (x in vistos_f or vistos_f.add(x))]
        q["tag"] = str(p.get("tag") or "")
        q["q"] = str(p.get("q") or "")
        opciones = [str(x) for x in (p.get("a") or [])]
        while len(opciones) < 4:
            opciones.append("")
        q["a"] = opciones[:4]
        try:
            q["c"] = max(0, min(3, int(p.get("c", 0))))
        except (TypeError, ValueError):
            q["c"] = 0
        q["law"] = str(p.get("law") or "")
        q["tip"] = str(p.get("tip") or "")
        preguntas.append(q)

    # Las preguntas se guardan en el orden del examen: bloque a bloque.
    orden = {bid: i for i, bid in enumerate(ids_bloque)}
    preguntas.sort(key=lambda q: orden[q["bloqueId"]])

    return {"config": cfg, "tema": tema, "interfaz": interfaz, "envio": envio,
            "bloques": bloques, "enunciados": enunciados, "preguntas": preguntas}


def numero(valor, por_defecto):
    """Convierte a número admitiendo coma decimal ("0,33" → 0.33)."""
    try:
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return por_defecto


def color_valido(valor, por_defecto):
    """#rgb o #rrggbb; cualquier otra cosa se sustituye por el color base."""
    txt = str(valor or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{3}", txt) or re.fullmatch(r"#[0-9A-Fa-f]{6}", txt):
        return txt
    return por_defecto


# ══════════════════════════════════════════════════════════════════════
#  2. LECTURA DEL HTML
#     Formato A (recomendado): <script type="application/json" id="datos-supuesto">
#     Formato B (plantilla antigua en JavaScript): const EXAM_CONFIG = {...} etc.
# ══════════════════════════════════════════════════════════════════════

RE_BLOQUE_JSON = re.compile(
    r'(<script\b[^>]*\bid=["\']datos-supuesto["\'][^>]*>)(.*?)(</script>)',
    re.S | re.I)


class _AnalizadorJS:
    """Lector mínimo de literales JavaScript (objetos, arrays, cadenas con
    comillas invertidas, números, true/false/null y comentarios)."""

    def __init__(self, texto, pos=0):
        self.t = texto
        self.i = pos

    def _saltar(self):
        t, n = self.t, len(self.t)
        while self.i < n:
            c = t[self.i]
            if c in " \t\r\n":
                self.i += 1
            elif t.startswith("//", self.i):
                j = t.find("\n", self.i)
                self.i = n if j < 0 else j + 1
            elif t.startswith("/*", self.i):
                j = t.find("*/", self.i)
                self.i = n if j < 0 else j + 2
            else:
                return

    def valor(self):
        self._saltar()
        if self.i >= len(self.t):
            return None
        c = self.t[self.i]
        if c == "{":
            return self.objeto()
        if c == "[":
            return self.lista()
        if c in "`\"'":
            return self.cadena()
        return self.escalar()

    def cadena(self):
        comilla = self.t[self.i]
        self.i += 1
        salida = []
        mapa = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "`": "`",
                "'": "'", '"': '"', "/": "/", "$": "$", "\n": ""}
        while self.i < len(self.t):
            c = self.t[self.i]
            if c == "\\" and self.i + 1 < len(self.t):
                sig = self.t[self.i + 1]
                if sig == "u":
                    try:
                        salida.append(chr(int(self.t[self.i + 2:self.i + 6], 16)))
                        self.i += 6
                        continue
                    except ValueError:
                        pass
                salida.append(mapa.get(sig, sig))
                self.i += 2
                continue
            if c == comilla:
                self.i += 1
                break
            salida.append(c)
            self.i += 1
        return "".join(salida)

    def escalar(self):
        j = self.i
        while j < len(self.t) and self.t[j] not in ",}]\n":
            j += 1
        bruto = self.t[self.i:j].strip()
        self.i = j
        if bruto == "true":
            return True
        if bruto == "false":
            return False
        if bruto in ("null", "undefined", ""):
            return None
        try:
            return int(bruto)
        except ValueError:
            pass
        try:
            return float(bruto)
        except ValueError:
            return bruto

    def lista(self):
        self.i += 1                      # [
        salida = []
        while True:
            self._saltar()
            if self.i >= len(self.t):
                break
            c = self.t[self.i]
            if c == "]":
                self.i += 1
                break
            if c == ",":
                self.i += 1
                continue
            salida.append(self.valor())
        return salida

    def objeto(self):
        self.i += 1                      # {
        salida = {}
        while True:
            self._saltar()
            if self.i >= len(self.t):
                break
            c = self.t[self.i]
            if c == "}":
                self.i += 1
                break
            if c == ",":
                self.i += 1
                continue
            if c in "`\"'":
                clave = self.cadena()
            else:
                j = self.i
                while j < len(self.t) and (self.t[j].isalnum() or self.t[j] in "_$"):
                    j += 1
                clave = self.t[self.i:j]
                self.i = j
                if not clave:            # carácter inesperado: lo saltamos
                    self.i += 1
                    continue
            self._saltar()
            if self.i < len(self.t) and self.t[self.i] == ":":
                self.i += 1
            salida[clave] = self.valor()
        return salida


def _en_comentario(texto, pos):
    """¿La posición cae dentro de un comentario /* … */ o // … ?

    Las plantillas explican en sus comentarios cosas como
    «deja const STATEMENTS_BANK = [];», así que hay que descartar esas
    apariciones y quedarse con la declaración de verdad."""
    ini_bloque = texto.rfind("/*", 0, pos)
    fin_bloque = texto.rfind("*/", 0, pos)
    if ini_bloque > fin_bloque:
        return True
    ini_linea = texto.rfind("\n", 0, pos) + 1
    return "//" in texto[ini_linea:pos]


def _literal_js(texto, nombre):
    """Localiza  const NOMBRE = <literal>  dentro del texto.

    Devuelve (valor, posicion_inicial_de_la_declaracion, posicion_final_del_literal)
    o (None, -1, -1) si no aparece."""
    patron = re.compile(r"\b(?:const|let|var)\s+%s\s*=\s*" % re.escape(nombre))
    elegido = None
    for m in patron.finditer(texto):
        if not _en_comentario(texto, m.start()):
            elegido = m
            break
    if elegido is None:
        return None, -1, -1
    an = _AnalizadorJS(texto, elegido.end())
    valor = an.valor()
    return valor, elegido.start(), an.i


def leer_html(ruta):
    """Lee un archivo de plantilla. Devuelve (datos, modo, texto_html).

    modo: 'json'    → el archivo lleva el bloque <script id="datos-supuesto">
          'js'      → plantilla antigua con EXAM_CONFIG/STATEMENTS_BANK/QUESTIONS_BANK
          'js-sin-config' → plantilla antigua SIN EXAM_CONFIG (título fijo en el HTML)
    """
    html = Path(ruta).read_text(encoding="utf-8")

    m = RE_BLOQUE_JSON.search(html)
    if m:
        crudo = m.group(2).strip()
        datos = json.loads(crudo)
        return normalizar(datos), "json", html

    cfg, _, _ = _literal_js(html, "EXAM_CONFIG")
    enun, pos_enun, _ = _literal_js(html, "STATEMENTS_BANK")
    preg, pos_preg, _ = _literal_js(html, "QUESTIONS_BANK")
    if pos_enun < 0 and pos_preg < 0:
        raise ValueError(
            "El archivo no parece una plantilla de supuesto: no se ha encontrado\n"
            'ni el bloque <script id="datos-supuesto"> ni las listas\n'
            "STATEMENTS_BANK / QUESTIONS_BANK.")

    modo = "js" if cfg else "js-sin-config"
    if not cfg:
        # Rescatamos al menos el título de la pestaña
        mt = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
        cfg = {"titulo": (mt.group(1).strip() if mt else "Supuesto"),
               "referencia": "", "ambito": "", "minutos": 30}

    datos = {"config": cfg, "enunciados": enun or [], "preguntas": preg or []}
    return normalizar(datos), modo, html


# ══════════════════════════════════════════════════════════════════════
#  3. ESCRITURA DEL HTML
# ══════════════════════════════════════════════════════════════════════

def datos_a_json(datos):
    """JSON legible; se escapa '<' para que ningún texto pueda cerrar el <script>."""
    return json.dumps(datos, ensure_ascii=False, indent=2).replace("<", "\\u003c")


def _bt(valor):
    """Texto entre comillas invertidas, tal y como lo escribe la plantilla JS."""
    s = "" if valor is None else str(valor)
    s = s.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    return "`" + s + "`"


def bloques_se_pierden(datos):
    """¿Guardar en la plantilla clásica perdería información de bloques?

    La plantilla antigua no conoce los bloques: solo tiene una lista de
    preguntas. Si el supuesto tiene más de un bloque, alguno de teoría o
    un baremo distinto del simple "1 punto por acierto", al guardar en
    ese formato se pierde esa configuración."""
    if (datos.get("tema") or TEMA_DEFECTO) != TEMA_DEFECTO:
        return True
    if (datos.get("interfaz") or {}) != INTERFAZ_DEFECTO:
        return True
    if (datos.get("envio") or ENVIO_DEFECTO) != ENVIO_DEFECTO:
        return True
    bloques = datos.get("bloques") or []
    if len(bloques) > 1:
        return True
    for b in bloques:
        if b["tipo"] == "test" or b["fallo"] or b["blanco"] or b["porIntento"] \
           or b["acierto"] != 1.0 or b["modo"] != "individual" \
           or b.get("cabeceraSobreEnunciado") is False:
            return True
    if any(q.get("factIds") for q in (datos.get("preguntas") or [])):
        return True      # los vínculos del modo foco no caben en la plantilla antigua
    return False


def datos_a_js(datos):
    """Reconstruye la ZONA EDITABLE en JavaScript (plantilla antigua).

    Las preguntas se escriben seguidas, en el orden del examen: la
    plantilla clásica no tiene bloques."""
    cfg = datos["config"]
    out = []
    out.append("const EXAM_CONFIG = {")
    out.append("    titulo:     %s," % _bt(cfg["titulo"]))
    out.append("    referencia: %s," % _bt(cfg["referencia"]))
    out.append("    ambito:     %s," % _bt(cfg["ambito"]))
    out.append("    minutos:    %d" % int(cfg["minutos"]))
    out.append("};")
    out.append("")

    out.append("const STATEMENTS_BANK = [")
    partes = []
    for e in datos["enunciados"]:
        p = ["    {"]
        p.append("        id: %s," % _bt(e["id"]))
        p.append("        number: %s," % _bt(e["number"]))
        p.append("        title: %s," % _bt(e["title"]))
        p.append("        ref: %s," % _bt(e["ref"]))
        p.append("        ambito: %s," % _bt(e["ambito"]))
        p.append("        factBlocks: [")
        sub = []
        for fb in e["factBlocks"]:
            q = ["            {"]
            q.append("                title: %s," % _bt(fb["title"]))
            if fb["red"]:
                q.append("                red: true,")
            if fb["hidden"]:
                q.append("                hidden: true,")
            q.append("                paragraphs: [")
            q.append(",\n".join("                    %s" % _bt(x) for x in fb["paragraphs"]))
            q.append("                ]")
            q.append("            }")
            sub.append("\n".join(q))
        p.append(",\n".join(sub))
        p.append("        ],")
        p.append("        timeline: [")
        sub = []
        for t in e["timeline"]:
            trozo = "            { date: %s, text: %s" % (_bt(t["date"]), _bt(t["text"]))
            if t["red"]:
                trozo += ", red: true"
            if t["hidden"]:
                trozo += ", hidden: true"
            trozo += " }"
            sub.append(trozo)
        p.append(",\n".join(sub))
        p.append("        ]")
        p.append("    }")
        partes.append("\n".join(p))
    out.append(",\n".join(partes))
    out.append("];")
    out.append("")

    out.append("const QUESTIONS_BANK = [")
    partes = []
    for pr in datos["preguntas"]:
        p = ["    {"]
        sid = pr["statementId"]
        p.append("        statementId: %s," % (_bt(sid) if sid else "null"))
        p.append("        tag: %s," % _bt(pr["tag"]))
        p.append("        q: %s," % _bt(pr["q"]))
        p.append("        a: [")
        p.append(",\n".join("            %s" % _bt(x) for x in pr["a"]))
        p.append("        ],")
        p.append("        c: %d," % int(pr["c"]))
        p.append("        law: %s," % _bt(pr["law"]))
        p.append("        tip: %s" % _bt(pr["tip"]))
        p.append("    }")
        partes.append("\n".join(p))
    out.append(",\n".join(partes))
    out.append("];")
    return "\n".join(out)


MARCA_FIN = "FIN DE LA ZONA EDITABLE"


def escribir_html(ruta_destino, html_base, datos, modo):
    """Inserta los datos en el HTML y lo guarda en ruta_destino."""
    if modo == "json" and RE_BLOQUE_JSON.search(html_base):
        nuevo = RE_BLOQUE_JSON.sub(
            lambda m: m.group(1) + "\n" + datos_a_json(datos) + "\n" + m.group(3),
            html_base, count=1)
    else:
        # Plantilla antigua: sustituimos desde "const EXAM_CONFIG"/"const STATEMENTS_BANK"
        # hasta el marcador de fin de zona editable (o hasta el final de QUESTIONS_BANK).
        ini, fin_literal = -1, -1
        for nombre in ("EXAM_CONFIG", "STATEMENTS_BANK", "QUESTIONS_BANK"):
            _, pos, fin_lit = _literal_js(html_base, nombre)
            if pos >= 0:
                if ini < 0 or pos < ini:
                    ini = pos
                fin_literal = max(fin_literal, fin_lit)
        if ini < 0:
            raise ValueError("No se ha encontrado la zona editable en el archivo de destino.")

        # La zona editable termina en el comentario "FIN DE LA ZONA EDITABLE"
        # (que se conserva) o, si no existe, justo tras el último literal.
        pos_marca = html_base.find(MARCA_FIN, ini)
        if pos_marca >= 0:
            fin = html_base.rfind("/*", ini, pos_marca)
            if fin < 0:
                fin = pos_marca
        else:
            fin = fin_literal
            while fin < len(html_base) and html_base[fin] in " \t\r\n;":
                fin += 1
        nuevo = html_base[:ini] + datos_a_js(datos) + "\n\n" + html_base[fin:]

    destino = Path(ruta_destino)
    if destino.exists():                       # copia de seguridad .bak
        try:
            destino.with_suffix(destino.suffix + ".bak").write_text(
                destino.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass
    destino.write_text(nuevo, encoding="utf-8")
    return nuevo


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


def caja_texto(padre, alto=4, ancho=90):
    """Cuadro de texto multilínea con su barra de desplazamiento."""
    marco = ttk.Frame(padre, style="Panel.TFrame")
    texto = tk.Text(marco, height=alto, width=ancho, wrap="word",
                    font=("Georgia", 10), relief="solid", borderwidth=1,
                    background="white", foreground="#111827",
                    insertbackground="#111827", padx=6, pady=4)
    barra = ttk.Scrollbar(marco, orient="vertical", command=texto.yview)
    texto.configure(yscrollcommand=barra.set)
    texto.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return marco, texto


def poner_texto(widget, valor):
    widget.delete("1.0", "end")
    widget.insert("1.0", "" if valor is None else str(valor))


def sacar_texto(widget):
    return widget.get("1.0", "end-1c")


def nUm(x):
    """Número con coma decimal y sin decimales inútiles: 1.0 → "1"; 0.33 → "0,33"."""
    r = round(float(x), 2)
    entero = int(r)
    return (str(entero) if r == entero else ("%.2f" % r).rstrip("0").rstrip(".")).replace(".", ",")


def resumen(texto, largo=60):
    """Primera línea recortada, para las listas laterales."""
    t = " ".join(str(texto or "").split())
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

class EditorApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(APP_TITULO)
        self.geometry("1240x840")
        self.minsize(1000, 640)
        self.configure(bg=C_FONDO)
        self._estilos()

        self.ruta = None                 # archivo abierto (None = aún sin guardar)
        self.html_base = ""              # HTML completo del archivo abierto
        self.modo = "json"
        self.datos = datos_vacios()
        self.hay_cambios = False
        self._silencio = False           # evita reentradas al repintar listas

        self.i_sec = None
        self.i_enun = None
        self.i_bloque = None
        self.i_hito = None
        self.i_preg = None

        self._barra_superior()

        self.cuaderno = ttk.Notebook(self)
        self.cuaderno.pack(fill="both", expand=True, padx=10, pady=(6, 4))
        self._pestana_general()
        self._pestana_bloques()
        self._pestana_enunciados()
        self._pestana_preguntas()
        self._pestana_botones()
        self._pestana_comprobar()

        self._barra_estado()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        self.bind_all("<Control-s>", lambda e: self.guardar())
        self.bind_all("<Control-o>", lambda e: self.abrir())

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
        ttk.Button(barra, text="⇪  Pasar a plantilla nueva…",
                   command=self.convertir_a_plantilla_nueva).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(barra, text="🌐  Ver en el navegador", command=self.ver_navegador).pack(side="left")
        ttk.Button(barra, text="✔  Comprobar", command=self.comprobar).pack(side="left", padx=(6, 0))

        self.lbl_archivo = ttk.Label(barra, text="(ningún archivo abierto)",
                                     style="Tec.TLabel")
        self.lbl_archivo.pack(side="right")

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

    def _pintar_titulo(self):
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

        rotulo(caja, "Cómo se ven las preguntas", "bloques[].modo",
               '.question-card.visible  ·  .question-card.encadenada',
               "«En cadena» muestra todas las preguntas del bloque seguidas, una debajo de "
               "otra (lo habitual en la teoría). «De una en una» muestra solo la pregunta "
               "actual (lo habitual en un supuesto). El alumno siempre puede forzar «de una "
               "en una» desde el panel ⚙ de la página."
               ).pack(anchor="w", padx=10, pady=(10, 4))
        self.var_sec_modo = tk.StringVar(value="individual")
        for valor, texto in (("cadena", "En cadena — todas las preguntas del bloque seguidas"),
                             ("individual", "De una en una — solo la pregunta actual")):
            ttk.Radiobutton(caja, text=texto, value=valor, variable=self.var_sec_modo,
                            command=self._tocado).pack(anchor="w", padx=18, pady=1)

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
               "Un párrafo por bloque de texto: DEJA UNA LÍNEA EN BLANCO entre párrafo y párrafo. "
               "Se admiten etiquetas HTML sencillas, por ejemplo <strong>texto en negrita</strong>."
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
        b["paragraphs"] = [p.strip() for p in re.split(r"\n\s*\n", crudo) if p.strip()]
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
        h["text"] = " ".join(sacar_texto(self.txt_hito_texto).split())
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
        caja = ttk.LabelFrame(m, text=" Respuestas — marca cuál es la correcta ")
        caja.pack(fill="x", padx=10, pady=6)
        rotulo(caja, "Las cuatro opciones", "preguntas[].a[0..3]",
               '<div class="option"> → <span class="opt-letter">A/B/C/D</span>',
               "El punto de la izquierda marca la opción correcta (preguntas[].c). "
               "OJO: la página baraja las opciones en cada intento, así que la correcta "
               "no siempre saldrá en la letra que ocupa aquí."
               ).pack(anchor="w", padx=10, pady=(8, 6))

        self.var_preg_c = tk.IntVar(value=0)
        self.txt_opciones = []
        for i in range(4):
            fila = ttk.Frame(caja, style="Panel.TFrame")
            fila.pack(fill="x", padx=10, pady=2)
            ttk.Radiobutton(fila, text="  %s  " % "ABCD"[i], value=i,
                            variable=self.var_preg_c,
                            command=self._marcar_correcta).pack(side="left", anchor="n", pady=4)
            marco, txt = caja_texto(fila, alto=3, ancho=70)
            marco.pack(side="left", fill="x", expand=True)
            self._vigilar(txt)
            self.txt_opciones.append(txt)

        self.lbl_correcta = ttk.Label(caja, text="Correcta: A", font=("Consolas", 10, "bold"),
                                      foreground=C_VERDE, background=C_FONDO)
        self.lbl_correcta.pack(anchor="w", padx=10, pady=(4, 10))

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

    def _marcar_correcta(self):
        self.lbl_correcta.config(text="Correcta: %s" % "ABCD"[self.var_preg_c.get()])
        self._tocado()

    # ---------- lista de preguntas ----------
    def refrescar_lista_preg(self, seleccionar=None):
        self._silencio = True
        self.lst_preg.delete(0, "end")
        for i, p in enumerate(self.datos["preguntas"]):
            marca = "📝" if self.tipo_de_bloque(p["bloqueId"]) == "test" else "📁"
            foco = "🔎" if p.get("factIds") else " "
            etiqueta = "%02d %s%-3s %-3s%s %s" % (i + 1, marca, p["bloqueId"],
                                                  p["statementId"] or "--", foco,
                                                  resumen(p["q"], 24))
            self.lst_preg.insert("end", etiqueta)
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
        for i in range(4):
            poner_texto(self.txt_opciones[i], "" if p is None else p["a"][i])
        self.var_preg_c.set(0 if p is None else p["c"])
        poner_texto(self.txt_preg_law, "" if p is None else p["law"])
        poner_texto(self.txt_preg_tip, "" if p is None else p["tip"])
        self.lbl_correcta.config(text="Correcta: %s" % "ABCD"[self.var_preg_c.get()])
        self._sincronizar_combo_bloque()
        self._sincronizar_combo()
        self.refrescar_lista_factlink()

    def volcar_pregunta(self):
        p = self.pregunta_actual()
        if p is None:
            return
        p["tag"] = self.var_preg_tag.get().strip()
        p["q"] = " ".join(sacar_texto(self.txt_preg_q).split())
        p["a"] = [" ".join(sacar_texto(t).split()) for t in self.txt_opciones]
        p["c"] = int(self.var_preg_c.get())
        p["law"] = sacar_texto(self.txt_preg_law).strip()
        p["tip"] = sacar_texto(self.txt_preg_tip).strip()
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

        ttk.Label(caja, text="Casillas de cada bloque", style="Campo.TLabel"
                  ).pack(anchor="w", padx=10, pady=(14, 0))
        ttk.Label(caja, style="Tec.TLabel",
                  text="bloques[].envio   ·   se envían solo los bloques que hayan salido "
                       "en ese intento").pack(anchor="w", padx=10)
        ttk.Label(caja, style="Ayuda.TLabel", wraplength=860, justify="left",
                  text="Un juego de casillas por bloque, para llevar al formulario cuántas "
                       "preguntas tuvo cada sección y cómo fue en ella."
                  ).pack(anchor="w", padx=10, pady=(0, 6))
        self.marco_envio_bloques = ttk.Frame(caja, style="Panel.TFrame")
        self.marco_envio_bloques.pack(fill="x", padx=10, pady=(0, 14))
        self.w_envio_bloque = {}

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
        self.refrescar_envio_bloques()

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
        self.datos["envio"] = envio
        self.volcar_envio_bloques()
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

        marco, self.txt_informe = caja_texto(panel, alto=30)
        marco.pack(fill="both", expand=True, padx=10, pady=8)
        self.txt_informe.configure(font=("Consolas", 9))

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
                               % (i, ", ".join("ABCD"[n] for n in vacias)))
            normal = [" ".join(t.lower().split()) for t in p["a"] if t.strip()]
            if len(set(normal)) != len(normal):
                avisos.append("Pregunta %d: hay dos opciones con el mismo texto." % i)
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
            lineas.append("     se ven %s · en el aleatorio salen %s"
                          % ("todas seguidas" if b["modo"] == "cadena" else "de una en una",
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

    def _refrescar_todo(self):
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

    def _carpeta_inicial(self):
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
        self.datos["bloques"] = [bloque_vacio("supuesto", "B1", primero=True)]
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
        self.hay_cambios = False
        self._refrescar_todo()
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

        También es la forma de llevar a un supuesto ya hecho las mejoras
        de la plantilla: al guardar normalmente solo se cambian los datos
        DENTRO del archivo, y su página sigue funcionando como el día en
        que se creó. Pasándolo por aquí se estrena el motor actual (los
        enunciados encima de sus preguntas, el modo foco, etc.)."""
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
                "el motor actual de la plantilla: la barra del bloque encima del "
                "enunciado, cada enunciado delante de sus preguntas y el modo foco "
                "del panel \u2699.", parent=self)
            return True
        return False

    def _escribir(self, destino):
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
        return True

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
        if self.hay_cambios:
            r = messagebox.askyesnocancel(
                "Salir", "Hay cambios sin guardar.\n\n¿Guardarlos antes de salir?", parent=self)
            if r is None:
                return
            if r and not self.guardar():
                return
        self.destroy()


# ══════════════════════════════════════════════════════════════════════
#  7. ARRANQUE
# ══════════════════════════════════════════════════════════════════════

def main():
    app = EditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()

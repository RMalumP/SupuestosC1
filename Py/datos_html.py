# -*- coding: utf-8 -*-
"""
DATOS Y LECTURA/ESCRITURA DEL HTML DE UN SUPUESTO
═════════════════════════════════════════════════
Parte del editor de supuestos (la usa editor_supuestos.py). No necesita
tkinter: se puede usar y probar sin ventana (por ejemplo desde
sincronizar_local.py). Contiene los valores por defecto, la normalización
de los datos (normalizar), leer_html, escribir_html y el alta en el menú.
"""
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

import menu_datos

APP_TITULO = "Editor de Supuestos — plantilla ECAP C1"
PLANTILLA_BASE = "supuesto_plantilla_python.html"   # se busca junto a este .py

# Versión del MOTOR de la página (el código que la hace funcionar, no los
# datos del supuesto). Al guardar, el editor compara la versión que lleva
# el archivo con la de la plantilla que tiene al lado: si el archivo se
# quedó atrás, ofrece ponerlo al día. Sin esto, un supuesto guardado hace
# meses conserva para siempre la página con la que se creó, por muchas
# mejoras que se hagan luego en la plantilla.
RE_MOTOR = re.compile(
    r"""<meta\s+name=["']motor-plantilla["']\s+content=["'](\d+)["']""", re.I)


def version_motor(html):
    """Número de versión del motor que lleva un HTML (0 = de antes de que
    esto existiera)."""
    m = RE_MOTOR.search(html or "")
    try:
        return int(m.group(1)) if m else 0
    except (TypeError, ValueError):
        return 0

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
    "opcionUnaEnUna": {"visible": True, "texto": "Ver las preguntas de una en una"},
    # Las dos formas de repetir el examen que ofrece el botón 🔀
    "opcionRepetirRespuestas": {"visible": True,
                                "texto": "🔁 Mismas preguntas y mismo orden"},
    "opcionRepetirOrden":      {"visible": True,
                                "texto": "🎲 Mismas preguntas en otro orden"},
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

# Opciones del panel ⚙ que no son botones de la cabecera: tamaño de letra,
# tema oscuro, deslizar y atajos. "activa" = cómo arranca si la persona aún no
# ha elegido nada. Viven en config.panel.
PANEL_DEFECTO = {
    "fuente":   {"visible": True},
    "tema":     {"visible": True, "activa": False},
    "deslizar": {"visible": True, "activa": True},
    "atajos":   {"visible": True},
}

# Justificado por defecto del texto (config.justificar)
JUSTIFICAR_DEFECTO = {"enunciado": True, "pregunta": True, "motivacion": True}

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
     "Deja a la vista solo la fila del bloque en el que está, en UNA sola línea: si el "
     "bloque tiene más casillas de las que caben, la fila se desliza a izquierda y "
     "derecha y se centra sola en la pregunta actual al cambiar de pregunta o de "
     "bloque. Solo aparece cuando el examen tiene más de un bloque. Con «Empieza "
     "plegada», cada intento arranca mostrando una sola fila."),
    ("opcionTiempo", "Opción: cambiar la duración", '<div class="settings-row" id="row-tiempo">',
     "Texto", "Permite al alumno fijar otro tiempo. Ocúltala para que el examen dure "
     "siempre lo que hayas puesto en la pestaña 1."),
    ("opcionCorregir", "Opción: corregir pregunta a pregunta",
     '<div class="settings-row" id="row-corregir">', "Texto",
     "Enseña la solución nada más responder cada pregunta. Marca «Empieza activada» "
     "para que el examen arranque ya en ese modo."),
    ("opcionUnaEnUna", "Opción: ver las preguntas de una en una",
     '<div class="settings-row" id="row-una">  ·  una casilla por bloque', "Rótulo del grupo",
     "En la página NO es una casilla suelta: debajo de este rótulo sale UNA CASILLA POR "
     "BLOQUE (con su nombre y su color), de modo que se puede tener el supuesto de una en "
     "una y la teoría en cadena, o al revés. CADA BLOQUE ARRANCA COMO DIGA SU «MODO» EN LA "
     "PESTAÑA 2 —nada de aquí lo cambia—, y allí mismo se le puede quitar la casilla. "
     "Aquí solo se decide si el grupo entero se ve y cómo se titula."),
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
     "Aparece al terminar. Abre la ventana con las dos formas de repetir (justo debajo). "
     "Si quitas las dos, este botón no se muestra; si dejas una sola, no se pregunta nada: "
     "el botón repite directamente de esa forma."),
    ("opcionRepetirRespuestas", "· Repetir: mismas preguntas y mismo orden",
     '<button id="rnd-answers">',
     "Primera opción de la ventana del botón 🔀. Salen las mismas preguntas, en el mismo "
     "orden; lo único que cambia es el orden de las respuestas dentro de cada pregunta "
     "(y qué opciones salen, si alguna pregunta tiene más escritas de las que se muestran)."),
    ("opcionRepetirOrden", "· Repetir: mismas preguntas en otro orden",
     '<button id="rnd-order">',
     "Segunda opción de la ventana del botón 🔀. Salen TODAS las preguntas otra vez, pero "
     "barajadas: nunca se descarta ninguna. Se respeta el orden de los bloques y cada "
     "pregunta sigue pegada a su enunciado. (Si un bloque tiene puesto «cuántas preguntas "
     "salen al azar» en la pestaña 2, ese recorte sí se aplica: es una decisión tuya.)"),
    ("btnEnviar", "Enviar resultados", '#send-btn  ·  #ov-send-btn',
     "Aparece al terminar. Si no hay dirección de envío configurada, no se muestra "
     "aunque esté marcado."),
    ("btnMenu", "Volver al menú principal", '#home-btn-bottom  ·  #ov-home-btn',
     "Aparece al terminar, abajo y en la ventana de resultados."),
]

# ── ENVÍO DE RESULTADOS A UN FORMULARIO DE GOOGLE ────────────────────────
# Los datos generales del intento, más el recuento ABSOLUTO («total»: todos
# los bloques sumados como uno) y, opcionalmente, un recuento por bloque
# (cada bloque tiene sus casillas, en blanco por defecto).
# Casillas del recuento ABSOLUTO: todos los bloques sumados como uno solo.
ENVIO_TOTAL_DEFECTO = {
    "preguntas": "entry.771114786",
    "aciertos":  "entry.1903892811",
    "fallos":    "entry.1155230396",
    "blancos":   "entry.943386498",
    "puntos":    "",
}

ENVIO_DEFECTO = {
    "url": ("https://docs.google.com/forms/d/e/"
            "1FAIpQLSd9h52UH7XzaRDRSIxSevScmqKZC28Fvtfnp39drKtC5SiwGA/formResponse"),
    "examen": "entry.241409513",
    "usuario": "entry.1810433543",
    "tiempoAsignado": "entry.1069013600",
    "tiempoEmpleado": "entry.815398067",
    "enviarTotal": True,                       # mandar el total absoluto
    "total": dict(ENVIO_TOTAL_DEFECTO),
}

# Claves de texto sueltas del envío (las demás son «enviarTotal» y «total»)
CLAVES_ENVIO_TEXTO = ("url", "examen", "usuario", "tiempoAsignado", "tiempoEmpleado")


def envio_defecto():
    """Copia independiente de ENVIO_DEFECTO (con su «total» anidado)."""
    cfg = dict(ENVIO_DEFECTO)
    cfg["total"] = dict(ENVIO_TOTAL_DEFECTO)
    return cfg

# (clave, nombre visible, qué valor se manda)
CAMPOS_ENVIO = [
    ("examen",         "Examen",          "el título del supuesto (pestaña 1)"),
    ("usuario",        "Alumno",          "el nombre que escribe al pulsar Enviar"),
    ("tiempoAsignado", "Tiempo asignado", "mm:ss"),
    ("tiempoEmpleado", "Tiempo empleado", "mm:ss"),
]

ENVIO_BLOQUE_DEFECTO = {"preguntas": "", "aciertos": "", "fallos": "",
                        "blancos": "", "puntos": ""}

# Casillas que en versiones anteriores se asignaban al PRIMER bloque. Ya no
# se usan por defecto (ahora van al «total» y las de bloque quedan en
# blanco); se conservan para reconocer archivos antiguos y migrarlos.
ENVIO_BLOQUE_PRIMERO_ANTIGUO = {
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

# ── SEGUNDO FORMULARIO: EL DETALLE PREGUNTA A PREGUNTA ───────────────────
# Es un COMPLEMENTO del anterior, no un sustituto. El alumno no lo ve ni lo
# pulsa: sale solo, en cuanto pulsa «Corregir» (o se le agota el tiempo), y
# lleva el nombre del supuesto, la fecha y hora del envío, los aciertos y los
# fallos en bruto y, pregunta a pregunta, si la acertó y qué opción marcó.
#
# Cada pregunta viaja SIEMPRE a la casilla de su número de orden en este
# programa (la 1ª pregunta de la lista → «Pregunta 1», y así hasta 100), sin
# importar en qué bloque esté ni si el intento salió aleatorizado.
ENTRADAS_PREGUNTA_DETALLE = [
    "entry.712361381", "entry.709874002", "entry.661924675", "entry.1030651222", "entry.200283712", #  1- 5
    "entry.134789499", "entry.966701265", "entry.2110630525", "entry.1056110206", "entry.960222499", #  6-10
    "entry.1846963224", "entry.900211285", "entry.1003793269", "entry.263573841", "entry.784118366", # 11-15
    "entry.1588074600", "entry.1770731044", "entry.211278072", "entry.1659967631", "entry.1690155252", # 16-20
    "entry.2143039054", "entry.1904113686", "entry.1470800200", "entry.1255018865", "entry.1513500", # 21-25
    "entry.1854371083", "entry.1620187954", "entry.729113678", "entry.293340307", "entry.1724050220", # 26-30
    "entry.1062380832", "entry.2085402594", "entry.950414350", "entry.602730095", "entry.614220064", # 31-35
    "entry.1856632108", "entry.909455125", "entry.693661547", "entry.632847159", "entry.335441030", # 36-40
    "entry.1456618893", "entry.852090648", "entry.589626122", "entry.183473563", "entry.1217213161", # 41-45
    "entry.1968115194", "entry.531136136", "entry.1209534835", "entry.1577734057", "entry.312691398", # 46-50
    "entry.1116760340", "entry.768501311", "entry.694863628", "entry.673940089", "entry.1533606077", # 51-55
    "entry.253021395", "entry.1326657452", "entry.2041886464", "entry.1051043932", "entry.1809273037", # 56-60
    "entry.1108878147", "entry.1471749573", "entry.1082014329", "entry.2112539399", "entry.15417682", # 61-65
    "entry.2104298979", "entry.949437792", "entry.2071397813", "entry.2001115340", "entry.1445602013", # 66-70
    "entry.911131704", "entry.1517320485", "entry.548517073", "entry.932772700", "entry.1987322673", # 71-75
    "entry.529360562", "entry.2050801750", "entry.82935037", "entry.48912348", "entry.1553896761", # 76-80
    "entry.1016698177", "entry.1584638604", "entry.1327257853", "entry.1726180779", "entry.574614711", # 81-85
    "entry.2070952397", "entry.1752221665", "entry.203467465", "entry.470537063", "entry.1753285763", # 86-90
    "entry.1200176677", "entry.1600805991", "entry.1986998899", "entry.1552574829", "entry.290117084", # 91-95
    "entry.1429046308", "entry.1510972535", "entry.281414865", "entry.673373891", "entry.2071377334" # 96-100
]

def normalizar_casillas_detalle(casillas):
    """Deja la lista de casillas del detalle con TANTAS como tenga el
    formulario (ver ENTRADAS_PREGUNTA_DETALLE).

    Antes se cortaba en 80 a secas: un examen con más preguntas perdía de
    la 81 en adelante, y encima el recorte se volvía a aplicar cada vez
    que se guardaba, así que un archivo corto se quedaba corto para
    siempre. Ahora lo que sobra se corta y lo que falta se completa con
    las casillas del proyecto, respetando las que ya viniesen puestas.
    """
    limpias = [str(c or "").strip() for c in (casillas or [])]
    limpias = limpias[:len(ENTRADAS_PREGUNTA_DETALLE)]
    if len(limpias) < len(ENTRADAS_PREGUNTA_DETALLE):
        limpias += ENTRADAS_PREGUNTA_DETALLE[len(limpias):]
    return limpias


ENVIO_DETALLE_DEFECTO = {
    "url": ("https://docs.google.com/forms/d/e/"
            "1FAIpQLSfICCUGWcmcJ1zLFtphE1pictGOyfY9epNbSrHtEFfGvvK8HQ/formResponse"),
    "nombre":   "entry.315726614",
    "tiempo":   "entry.1329722701",
    "aciertos": "entry.979170555",
    "fallos":   "entry.1962238201",
    "preguntas": list(ENTRADAS_PREGUNTA_DETALLE),
}

# (clave, nombre visible, qué valor se manda)
CAMPOS_ENVIO_DETALLE = [
    ("nombre",   "Nombre supuesto", "el título del supuesto (pestaña 1)"),
    ("tiempo",   "Tiempo",          "fecha y hora del envío (dd/mm/aaaa hh:mm)"),
    ("aciertos", "Nº aciertos",     "recuento en bruto, sin baremo"),
    ("fallos",   "Nº fallos",       "recuento en bruto, sin baremo"),
]


def envio_detalle_por_defecto():
    """Copia independiente de la configuración del segundo formulario."""
    cfg = dict(ENVIO_DETALLE_DEFECTO)
    cfg["preguntas"] = list(ENVIO_DETALLE_DEFECTO["preguntas"])
    return cfg

# Colores por defecto de cada tipo de bloque (los del HTML)
LOGO_POR_DEFECTO = ("https://academia.ecap.es/pluginfile.php?file=%2F1%2Fcore_admin"
                    "%2Flogo%2F0x200%2F1782109950%2FACADEMIA%20VIRTUAL%20%281%29.png")

COLOR_SUPUESTO = "#8fc4d9"      # azul de la plantilla
COLOR_TEST     = "#e0ac4a"      # ámbar, para distinguir la teoría

# ── RESPUESTAS ──────────────────────────────────────────────────────────
# Una pregunta puede tener de 2 a 7 opciones escritas (4 es lo normal) y
# una o varias correctas. Además se puede decidir cuántas de esas opciones
# SALEN en el examen: si una pregunta tiene siete escritas y salen cuatro,
# cada intento enseña las correctas más unos distractores sorteados.
MIN_OPCIONES = 2
MAX_OPCIONES = 7
OPCIONES_POR_DEFECTO = 4
LETRAS = "ABCDEFG"

# Valores del desplegable "cuántas respuestas salen" (0 = todas las escritas)
RESPUESTAS_EXAMEN = [
    (0, "Todas las que tenga escritas cada pregunta"),
    (3, "3 respuestas"),
    (4, "4 respuestas"),
    (5, "5 respuestas"),
]


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
            "respuestas": 0,
            "corazon": True,
            "subrayar": True,
            "justificar": dict(JUSTIFICAR_DEFECTO),
            "panel": {k: dict(v) for k, v in PANEL_DEFECTO.items()},
            "logo": LOGO_POR_DEFECTO,
            "logoAlt": "ECAP - Escuela Ciudadana de Administración Pública",
            "organismo": "Comunidad ECAP ASS C1",
        },
        "tema": dict(TEMA_DEFECTO),
        "interfaz": {k: dict(v) for k, v in INTERFAZ_DEFECTO.items()},
        "envio": envio_defecto(),
        "envioDetalle": envio_detalle_por_defecto(),
        "bloques": [bloque_vacio("supuesto", "B1")],
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
        "opcionUnaEnUna": True,
        "porIntento": 0,
        "acierto": 1.0,
        "fallo": 0.0,
        "blanco": 0.0,
        "envio": dict(ENVIO_BLOQUE_DEFECTO),     # por bloque: en blanco
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
        "a": ["Opción correcta"] + ["Opción incorrecta"] * (OPCIONES_POR_DEFECTO - 1),
        "c": 0,
        # Correctas: una sola (lista de un elemento) salvo respuesta múltiple
        "correctas": [0],
        "multiple": False,
        # Cuántas de sus opciones salen en el examen (0 = lo que diga el
        # apartado general de la pestaña 1)
        "respuestas": 0,
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
    cfg["corazon"] = cfg.get("corazon", True) is not False      # corazón de favoritas (por defecto, sí)
    cfg["subrayar"] = cfg.get("subrayar", True) is not False    # subrayar con colores (por defecto, sí)
    # Justificado y opciones extra del panel ⚙ (valores raros vuelven al defecto)
    j = cfg.get("justificar") if isinstance(cfg.get("justificar"), dict) else {}
    cfg["justificar"] = {k: j.get(k, True) is not False for k in JUSTIFICAR_DEFECTO}
    pn = cfg.get("panel") if isinstance(cfg.get("panel"), dict) else {}
    cfg["panel"] = {}
    for k, base_k in PANEL_DEFECTO.items():
        dado = pn.get(k) if isinstance(pn.get(k), dict) else {}
        cfg["panel"][k] = {c: (dado.get(c, v) is not False) for c, v in base_k.items()}
    # Cuántas respuestas salen de cada pregunta (0 = todas las escritas)
    try:
        respuestas = int(cfg.get("respuestas") or 0)
    except (TypeError, ValueError):
        respuestas = 0
    cfg["respuestas"] = respuestas if respuestas == 0 or MIN_OPCIONES <= respuestas <= MAX_OPCIONES else 0
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
    envio_bruto = datos.get("envio") or (envio_defecto() if sin_configurar else {})
    envio = {clave: str(envio_bruto.get(clave, "") or "").strip()
             for clave in CLAVES_ENVIO_TEXTO}
    # Total absoluto (todos los bloques sumados): casillas y casilla de activar
    total_bruto = envio_bruto.get("total")
    tiene_total = isinstance(total_bruto, dict)
    total_dic = total_bruto if tiene_total else {}   # en archivos muy antiguos «total» era un texto
    envio["total"] = {clave: str(total_dic.get(clave, "") or "").strip()
                      for clave in ENVIO_BLOQUE_DEFECTO}
    envio["enviarTotal"] = bool(envio_bruto.get("enviarTotal", True))
    # Casillas de recuento que en versiones anteriores iban sueltas
    heredadas = {destino: str(envio_bruto.get(origen, "") or "").strip()
                 for origen, destino in EQUIVALENCIA_ENVIO_ANTIGUO.items()}

    # ── segundo formulario: detalle pregunta a pregunta ───────────────
    # Es el mismo para todo el proyecto, así que un archivo que no lo traiga
    # (los de antes de esta versión) lo estrena tal cual. Si lo trae, se
    # respeta lo que tenga y solo se completa lo que falte.
    detalle_bruto = datos.get("envioDetalle") or {}
    detalle = {clave: str(detalle_bruto.get(clave, ENVIO_DETALLE_DEFECTO[clave]) or "").strip()
               for clave in ("url", "nombre", "tiempo", "aciertos", "fallos")}
    casillas = detalle_bruto.get("preguntas")
    if isinstance(casillas, list) and casillas:
        detalle["preguntas"] = normalizar_casillas_detalle(casillas)
    else:
        detalle["preguntas"] = list(ENTRADAS_PREGUNTA_DETALLE)

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
        nb["opcionUnaEnUna"] = b.get("opcionUnaEnUna") is not False
        try:
            nb["porIntento"] = max(0, int(b.get("porIntento") or 0))
        except (TypeError, ValueError):
            nb["porIntento"] = 0
        env_bruto = b.get("envio") or {}
        nb["envio"] = {clave: str(env_bruto.get(clave, "") or "").strip()
                       for clave in ENVIO_BLOQUE_DEFECTO}
        nb["acierto"] = numero(b.get("acierto"), 1.0)
        nb["fallo"] = abs(numero(b.get("fallo"), 0.0))
        nb["blanco"] = abs(numero(b.get("blanco"), 0.0))
        bloques.append(nb)
    if not bloques:
        # Sin bloques declarados: uno solo, que es el examen entero
        bloques = [bloque_vacio("supuesto", "B1")]
    # Archivo de una versión anterior (sin «total»): las casillas que antes
    # llevaba el primer bloque eran, en realidad, las del examen entero. Se
    # trasladan al total absoluto y el bloque queda en blanco; así con varios
    # bloques ya no se manda solo el primero.
    if not tiene_total:
        primero_env = bloques[0]["envio"]
        if any(heredadas.values()):
            envio["total"] = {c: (heredadas.get(c) or "") for c in ENVIO_BLOQUE_DEFECTO}
        if primero_env == ENVIO_BLOQUE_PRIMERO_ANTIGUO:
            envio["total"] = dict(ENVIO_BLOQUE_PRIMERO_ANTIGUO)
            bloques[0]["envio"] = dict(ENVIO_BLOQUE_DEFECTO)
        elif any(heredadas.values()):
            for c in ENVIO_BLOQUE_DEFECTO:
                if primero_env.get(c) == envio["total"].get(c):
                    primero_env[c] = ""
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
        normalizar_respuestas(q, p)
        q["law"] = str(p.get("law") or "")
        q["tip"] = str(p.get("tip") or "")
        preguntas.append(q)

    # Las preguntas se guardan en el orden del examen: bloque a bloque.
    orden = {bid: i for i, bid in enumerate(ids_bloque)}
    preguntas.sort(key=lambda q: orden[q["bloqueId"]])

    return {"config": cfg, "tema": tema, "interfaz": interfaz, "envio": envio,
            "envioDetalle": detalle, "bloques": bloques, "enunciados": enunciados,
            "preguntas": preguntas}


def normalizar_respuestas(q, p):
    """Deja en q las opciones, las correctas y cuántas salen.

    Admite tanto el formato de siempre (cuatro opciones y la correcta en
    "c") como el nuevo (de 2 a 7 opciones, varias correctas en
    "correctas" y "multiple"). Las opciones que se dejen en blanco se
    descartan, para que una pregunta de tres respuestas se guarde con
    tres y no con una vacía."""
    opciones = [str(x) for x in (p.get("a") or []) if str(x).strip() != ""]
    while len(opciones) < MIN_OPCIONES:
        opciones.append("Opción %s" % LETRAS[len(opciones)])
    q["a"] = opciones[:MAX_OPCIONES]

    def dentro(i):
        return isinstance(i, int) and 0 <= i < len(q["a"])

    correctas = []
    for x in (p.get("correctas") or []):
        try:
            n = int(x)
        except (TypeError, ValueError):
            continue
        if dentro(n) and n not in correctas:
            correctas.append(n)
    if not correctas:
        try:
            c = int(p.get("c", 0))
        except (TypeError, ValueError):
            c = 0
        correctas = [c] if dentro(c) else [0]

    q["correctas"] = sorted(correctas)
    q["c"] = q["correctas"][0]
    q["multiple"] = bool(p.get("multiple"))

    try:
        cuantas = int(p.get("respuestas") or 0)
    except (TypeError, ValueError):
        cuantas = 0
    if cuantas and not (MIN_OPCIONES <= cuantas <= MAX_OPCIONES):
        cuantas = 0
    q["respuestas"] = cuantas
    return q


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
    # La plantilla clásica no manda el detalle pregunta a pregunta
    if (datos.get("envioDetalle") or envio_detalle_por_defecto()) != envio_detalle_por_defecto():
        return True
    bloques = datos.get("bloques") or []
    if len(bloques) > 1:
        return True
    for b in bloques:
        if b["tipo"] == "test" or b["fallo"] or b["blanco"] or b["porIntento"] \
           or b["acierto"] != 1.0 or b["modo"] != "individual" \
           or b.get("cabeceraSobreEnunciado") is False \
           or b.get("opcionUnaEnUna") is False:
            return True
    for q in (datos.get("preguntas") or []):
        # Vínculos del modo foco, respuesta múltiple y preguntas que no
        # tengan exactamente cuatro opciones: nada de esto cabe en la
        # plantilla antigua.
        if q.get("factIds") or q.get("multiple") or q.get("respuestas") \
           or len(q.get("a") or []) != 4 or len(q.get("correctas") or [0]) > 1:
            return True
    if (datos.get("config") or {}).get("respuestas"):
        return True
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


def escribir_html(ruta_destino, html_base, datos, modo, copia=True):
    """Inserta los datos en el HTML y lo guarda en ruta_destino.
    copia=False no deja la copia de seguridad .bak (la usa sincronizar_local.py)."""
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
    if copia and destino.exists():             # copia de seguridad .bak
        try:
            destino.with_suffix(destino.suffix + ".bak").write_text(
                destino.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass
    destino.write_text(nuevo, encoding="utf-8")
    return nuevo


# ──────────────────────────────────────────────────────────────────────
#  Alta en el menú principal (supuestos-datos.js)
# ──────────────────────────────────────────────────────────────────────
# El menú de la web se pinta desde «supuestos-datos.js», que está en la
# carpeta raíz del proyecto (la que contiene «supuestos/», «index.html»…).
# Al guardar un supuesto dentro de «supuestos/», el programa ofrece darlo de
# alta en ese archivo para no tener que tocarlo a mano.
ARCHIVO_MENU = menu_datos.ARCHIVO_MENU
# Cada destino del menú se identifica con «sección/grupo» (p. ej. «temas/iniciales»);
# «examenes» es la lista de exámenes y simulacros.
GRUPOS_MENU = (("temas/iniciales",    "Supuestos por temas · Iniciales"),
               ("temas/avanzados",    "Supuestos por temas · Avanzados"),
               ("generales/iniciales", "Supuestos generales · Iniciales"),
               ("generales/avanzados", "Supuestos generales · Avanzados"),
               ("examenes",           "Exámenes y simulacros"))
TITULOS_SECCION = {"temas": "Supuestos por temas", "generales": "Supuestos generales"}
TITULOS_GRUPO = {"iniciales": "Iniciales", "avanzados": "Avanzados"}


def ruta_menu_de(destino):
    """supuestos-datos.js del proyecto al que pertenece un supuesto, o None.
    Solo vale si el archivo está dentro de una carpeta «supuestos/»."""
    destino = Path(destino).resolve()
    if destino.parent.name.lower() != "supuestos":
        return None
    cand = destino.parent.parent / ARCHIVO_MENU
    return cand if cand.is_file() else None


def leer_menu(ruta_menu):
    """(texto_completo, datos) del archivo del menú (una línea por supuesto)."""
    return menu_datos.leer_archivo(ruta_menu)


def listas_del_menu(menu):
    """Recorre todas las listas del menú: (clave «sección/grupo», lista)."""
    for sec in menu.get("secciones", []):
        for g in sec.get("grupos", []):
            yield "%s/%s" % (sec.get("id"), g.get("id")), g.setdefault("items", [])
    yield "examenes", menu.setdefault("examenes", [])


def grupo_en_menu(menu, archivo):
    """Clave del grupo en el que ya está el supuesto, o None."""
    for clave, lista in listas_del_menu(menu):
        if any(it.get("archivo") == archivo for it in lista):
            return clave
    return None


def lista_de_grupo(menu, clave):
    """Lista de supuestos del grupo indicado (se crea si no existe)."""
    for c, lista in listas_del_menu(menu):
        if c == clave:
            return lista
    seccion_id, grupo_id = clave.split("/", 1)
    sec = next((x for x in menu.setdefault("secciones", []) if x.get("id") == seccion_id), None)
    if sec is None:
        sec = {"id": seccion_id, "titulo": TITULOS_SECCION.get(seccion_id, seccion_id.title()), "grupos": []}
        menu["secciones"].append(sec)
    g = {"id": grupo_id, "titulo": TITULOS_GRUPO.get(grupo_id, grupo_id.title()), "items": []}
    sec["grupos"].append(g)
    return g["items"]


def ficha_menu(archivo, datos, letra=None):
    """Tarjeta del menú a partir de los datos del supuesto."""
    return menu_datos.ficha(archivo, datos, letra)


def escribir_menu(ruta_menu, texto, menu):
    """Reescribe supuestos-datos.js (solo las dos listas; el resto se respeta)."""
    menu_datos.escribir_archivo(ruta_menu, texto, menu)



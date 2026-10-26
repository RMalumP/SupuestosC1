# -*- coding: utf-8 -*-
"""
UTILIDADES SIN VENTANA DEL EDITOR: versión, historial de archivos, recientes, ayuda, impugnaciones
═════════════════════════════════════════════════════════════════════════════════════════════════
Parte del editor de supuestos. No usa tkinter, así que se prueba sin pantalla.
"""
import csv
import io
import re
import shutil
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ── subir la versión de la app (config/version.js) ──────────────────
_RE_VERSION = re.compile(r'(SUPC1_VERSION\s*=\s*")v(\d+)\.(\d+)(")')


def version_actual(raiz):
    t = (Path(raiz) / "config" / "version.js").read_text(encoding="utf-8")
    m = _RE_VERSION.search(t)
    return "v%s.%s" % (m.group(2), m.group(3)) if m else None


def subir_version(raiz):
    """v28.9 → v28.10. Devuelve (antes, después). Lanza ValueError si no encuentra la versión."""
    ruta = Path(raiz) / "config" / "version.js"
    t = ruta.read_text(encoding="utf-8")
    m = _RE_VERSION.search(t)
    if not m:
        raise ValueError("No encuentro SUPC1_VERSION en config/version.js")
    antes = "v%s.%s" % (m.group(2), m.group(3))
    despues = "v%s.%d" % (m.group(2), int(m.group(3)) + 1)
    ruta.write_text(t[:m.start()] + 'SUPC1_VERSION = "%s"' % despues + t[m.end():], encoding="utf-8")
    return antes, despues


# ── historial de versiones de un supuesto ───────────────────────────
CARPETA_HISTORIAL = ".historial"
COPIAS = 10


def guardar_copia(ruta, raiz, ahora=None):
    """Antes de sobrescribir `ruta`, deja una copia con fecha en .historial/NOMBRE/. Devuelve la copia o None."""
    ruta = Path(ruta)
    if not ruta.is_file():
        return None
    carpeta = Path(raiz) / CARPETA_HISTORIAL / ruta.stem
    carpeta.mkdir(parents=True, exist_ok=True)
    marca = (ahora or datetime.now()).strftime("%Y%m%d-%H%M%S")
    destino = carpeta / ("%s%s" % (marca, ruta.suffix))
    shutil.copy2(ruta, destino)
    copias = sorted(carpeta.iterdir())
    for vieja in copias[:-COPIAS]:
        vieja.unlink()
    return destino


def copias_de(ruta, raiz):
    carpeta = Path(raiz) / CARPETA_HISTORIAL / Path(ruta).stem
    return sorted(carpeta.iterdir(), reverse=True) if carpeta.is_dir() else []


def etiqueta_copia(copia):
    try:
        return datetime.strptime(Path(copia).stem, "%Y%m%d-%H%M%S").strftime("%d/%m/%Y %H:%M:%S")
    except ValueError:
        return Path(copia).name


# ── archivos recientes ──────────────────────────────────────────────
def anotar_reciente(prefs, ruta, maximo=8):
    lista = [r for r in prefs.get("recientes", []) if r != str(ruta)]
    prefs["recientes"] = ([str(ruta)] + lista)[:maximo]


def recientes(prefs):
    return [r for r in prefs.get("recientes", []) if Path(r).is_file()]


# ── ayuda por pestaña: trozos de INSTRUCCIONES.txt ──────────────────
_TITULOS_PESTANA = {
    0: r"CREAR UN SUPUESTO NUEVO|COLORES DE LA P",
    1: r"QUÉ SON LOS BLOQUES",
    2: r"CREAR UN SUPUESTO NUEVO",
    3: r"CREAR UN SUPUESTO NUEVO",
    4: r"BOTONES, OPCIONES Y ENVÍO",
    5: r"CREAR UN SUPUESTO NUEVO",
    6: r"NORMAS ENLAZADAS",
}


def secciones_ayuda(texto):
    """[(titulo, cuerpo)] cortando por las rayas de INSTRUCCIONES.txt."""
    lineas = texto.split("\n")
    marcas = [i for i, l in enumerate(lineas) if re.match(r"^─{20,}$", l.strip())]
    res = []
    for a, b in zip(marcas, marcas[1:]):
        if b == a + 2:                      # raya, título, raya
            res.append((lineas[a + 1].strip(), a + 2))
    salida = []
    for k, (titulo, ini) in enumerate(res):
        fin = res[k + 1][1] - 3 if k + 1 < len(res) else len(lineas)
        salida.append((titulo, "\n".join(lineas[ini + 1:fin]).strip("\n")))
    return salida


def ayuda_para(texto, pestana):
    """Sección de la guía más relacionada con una pestaña (0 a 6)."""
    patron = _TITULOS_PESTANA.get(pestana, "QUÉ HAY")
    for titulo, cuerpo in secciones_ayuda(texto):
        if re.search(patron, titulo):
            return titulo, cuerpo
    # subapartados sin rayas: una línea de 2 espacios en MAYÚSCULAS hasta la siguiente
    lineas = texto.split("\n")
    es_titulo = re.compile(r"^  [A-ZÁÉÍÓÚÑ0-9«»][A-ZÁÉÍÓÚÑ0-9 «»·,()/\-]{8,}.*$")
    for i, l in enumerate(lineas):
        if es_titulo.match(l) and re.search(patron, l) and not l.rstrip().endswith(":"):
            fin = next((j for j in range(i + 1, len(lineas)) if es_titulo.match(lineas[j])
                        or re.match(r"^─{20,}$", lineas[j].strip())), len(lineas))
            return l.strip(), "\n".join(lineas[i + 1:fin]).strip("\n")
    return "Instrucciones", texto[:4000]


# ── impugnaciones (hoja pública de Google) ──────────────────────────
def config_impugnaciones(raiz):
    t = (Path(raiz) / "config" / "impugnaciones-config.js").read_text(encoding="utf-8")
    sheet = re.search(r'sheetId:\s*"([^"]+)"', t)
    hoja = re.search(r'hojaImpugnaciones:\s*"([^"]+)"', t)
    if not sheet:
        raise ValueError("No encuentro sheetId en config/impugnaciones-config.js")
    return sheet.group(1), (hoja.group(1) if hoja else "Impugnaciones")


def url_csv(sheet_id, hoja):
    return ("https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv&sheet=%s"
            % (sheet_id, urllib.parse.quote(hoja)))


def descargar_impugnaciones(raiz, abrir=urllib.request.urlopen):
    sheet, hoja = config_impugnaciones(raiz)
    with abrir(url_csv(sheet, hoja), timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def leer_impugnaciones(texto_csv):
    """→ lista de dicts {cabecera: valor} (cabeceras en minúsculas). Filas vacías fuera."""
    filas = list(csv.reader(io.StringIO(texto_csv)))
    if not filas:
        return []
    cab = [c.strip().lower() for c in filas[0]]
    res = []
    for f in filas[1:]:
        if any(c.strip() for c in f):
            res.append({cab[i]: (f[i].strip() if i < len(f) else "") for i in range(len(cab))})
    return res


def columna(fila, *claves):
    """Primer valor cuya cabecera contenga alguna de las claves."""
    for k, v in fila.items():
        if any(c in k for c in claves) and v:
            return v
    return ""

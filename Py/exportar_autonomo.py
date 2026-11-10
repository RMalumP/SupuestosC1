# -*- coding: utf-8 -*-
"""Exporta un supuesto como UN SOLO archivo HTML autónomo.

Mete dentro del HTML todo lo que el supuesto enlaza (motor, módulos, estilos,
fuentes e imágenes), para que funcione abierto en cualquier sitio sin las
carpetas de la web. No toca el supuesto original ni los HTML publicados.
Lo que solo tiene sentido en la web (service worker, manifiesto) se quita."""
import base64
import mimetypes
import re
from pathlib import Path

# Lo que en un archivo suelto no hace nada (o daría errores): se omite.
OMITIR = ("js/pwa.js",)

_RE_LINK_CSS = re.compile(r'<link\b[^>]*\brel=["\']stylesheet["\'][^>]*>', re.I)
_RE_LINK_OTRO = re.compile(r'<link\b[^>]*\brel=["\'](?:manifest|icon|apple-touch-icon)["\'][^>]*>\s*', re.I)
_RE_SCRIPT = re.compile(r'<script\b([^>]*)\bsrc=["\']([^"\']+)["\']([^>]*)>\s*</script>', re.I)
_RE_HREF = re.compile(r'\bhref=["\']([^"\']+)["\']', re.I)
_RE_URL = re.compile(r'url\(\s*(["\']?)([^)"\']+)\1\s*\)')
_RE_IMG = re.compile(r'(<img\b[^>]*\bsrc=)(["\'])([^"\']+)\2', re.I)
# Imágenes de los supuestos: no son etiquetas del HTML, van en los datos ("src": "img/…").
_RE_IMG_DATOS = re.compile(r'("src"\s*:\s*")((?:[^"\\]|\\.)+\.(?:png|jpe?g|gif|webp))(")', re.I)


def _local(ref):
    return not re.match(r'^(?:[a-z]+:|//|#)', ref, re.I)


def _data_uri(ruta):
    tipo = mimetypes.guess_type(str(ruta))[0] or {".woff2": "font/woff2", ".webp": "image/webp"}.get(
        ruta.suffix.lower(), "application/octet-stream")
    return "data:%s;base64,%s" % (tipo, base64.b64encode(ruta.read_bytes()).decode("ascii"))


def _css_en_linea(texto, carpeta):
    """Convierte los url(...) relativos de un CSS (fuentes, imágenes) en data: URIs."""
    def cambia(m):
        ref = m.group(2).strip()
        if not _local(ref) or ref.startswith("data:"):
            return m.group(0)
        ruta = (carpeta / ref.split("#")[0].split("?")[0]).resolve()
        return "url(%s)" % _data_uri(ruta) if ruta.is_file() else m.group(0)
    return _RE_URL.sub(cambia, texto)


def exportar_html(html, carpeta):
    """Devuelve el HTML con todo lo enlazado metido dentro.
    carpeta: la del supuesto, desde la que se resuelven las rutas relativas."""
    carpeta = Path(carpeta)
    faltan = []

    def ruta_de(ref):
        return (carpeta / ref.split("?")[0].split("#")[0]).resolve()

    def omitir(ref):
        return any(ref.replace("\\", "/").endswith(o) for o in OMITIR)

    def css(m):
        h = _RE_HREF.search(m.group(0))
        if not h or not _local(h.group(1)):
            return m.group(0)
        ruta = ruta_de(h.group(1))
        if not ruta.is_file():
            faltan.append(h.group(1))
            return m.group(0)
        texto = _css_en_linea(ruta.read_text(encoding="utf-8"), ruta.parent)
        return "<style>/* %s */\n%s\n</style>" % (h.group(1), texto.replace("</style", "<\\/style"))

    def script(m):
        ref = m.group(2)
        if not _local(ref):
            return m.group(0)
        if omitir(ref):
            return ""
        ruta = ruta_de(ref)
        if not ruta.is_file():
            faltan.append(ref)
            return ""
        js = ruta.read_text(encoding="utf-8").replace("</script", "<\\/script")
        return "<script>/* %s */\n%s\n</script>" % (ref, js)

    def img(m):
        ref = m.group(3)
        if not _local(ref) or ref.startswith("data:"):
            return m.group(0)
        ruta = ruta_de(ref)
        return m.group(1) + m.group(2) + _data_uri(ruta) + m.group(2) if ruta.is_file() else m.group(0)

    def img_datos(m):
        ref = m.group(2)
        if not _local(ref):
            return m.group(0)
        ruta = ruta_de(ref)
        if not ruta.is_file():
            faltan.append(ref)
            return m.group(0)
        return m.group(1) + _data_uri(ruta) + m.group(3)

    html = _RE_IMG_DATOS.sub(img_datos, html)     # antes de meter los scripts: solo toca los datos
    html = _RE_LINK_OTRO.sub("", html)
    html = _RE_LINK_CSS.sub(css, html)
    html = _RE_SCRIPT.sub(script, html)
    html = _RE_IMG.sub(img, html)
    html = re.sub(r'(<style>)(.*?)(</style>)', lambda m: m.group(1) + _css_en_linea(m.group(2), carpeta) + m.group(3), html, flags=re.S)
    return html, faltan


def exportar_archivo(origen, destino):
    """Lee el supuesto «origen» (un .html de la web) y escribe «destino» autónomo."""
    origen = Path(origen)
    html, faltan = exportar_html(origen.read_text(encoding="utf-8"), origen.parent)
    Path(destino).write_text(html, encoding="utf-8")
    return faltan

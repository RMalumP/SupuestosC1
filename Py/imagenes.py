# -*- coding: utf-8 -*-
"""
IMÁGENES DE LOS SUPUESTOS  (sin ventana)
════════════════════════════════════════
Parte del editor de supuestos. No usa tkinter, así que se prueba sin pantalla.

Cada bloque de hechos, cada pregunta y cada motivación legal admiten hasta
MAXIMO imágenes. En los datos son listas opcionales:

    enunciados[].factBlocks[].imgs     bajo los párrafos del bloque de hechos
    preguntas[].imgs                   entre el texto de la pregunta y las opciones
    preguntas[].imgsLaw                bajo la motivación legal (solo al corregir)

y cada imagen es  {"src": "img/supuesto_3/nomina.png", "pie": "Pie opcional"}.
«src» es relativa al .html del supuesto: las imágenes viven en la carpeta
complementaria  supuestos/img/NOMBRE_DEL_SUPUESTO/.

En el editor una imagen recién añadida lleva además «origen» (la ruta del archivo
elegido en el ordenador) y todavía no está en esa carpeta: repartir() la copia al
GUARDAR, le pone su «src» y retira de la carpeta las que ya no se usan (van a
.historial/img/, de donde vuelven solas si se deshace el cambio).
"""
import base64
import copy
import mimetypes
import re
import shutil
import unicodedata
from pathlib import Path

MAXIMO = 3
EXTENSIONES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
CARPETA = "img"
PESO_AVISO = 500 * 1024          # a partir de aquí «Comprobar» avisa (no bloquea)
CLAVES_PREGUNTA = ("imgs", "imgsLaw")
TIPOS_ARCHIVO = [("Imágenes", " ".join("*" + e for e in EXTENSIONES)), ("Todos los archivos", "*.*")]


def normalizar_lista(valor):
    """Lista limpia de imágenes (como mucho MAXIMO). Lo que no sea una imagen se descarta."""
    res = []
    for im in valor if isinstance(valor, list) else []:
        if not isinstance(im, dict):
            continue
        src = str(im.get("src") or "").strip().replace("\\", "/")
        origen = str(im.get("origen") or "").strip()
        if not src and not origen:
            continue
        n = {"src": src, "pie": str(im.get("pie") or "").strip()}
        if origen:
            n["origen"] = origen
        res.append(n)
    return res[:MAXIMO]


def recorrer(datos):
    """Todas las listas de imágenes del supuesto: (dónde, dueño, clave)."""
    for e in datos.get("enunciados") or []:
        for j, fb in enumerate(e.get("factBlocks") or [], 1):
            yield "Enunciado %s, bloque %d" % (e.get("id"), j), fb, "imgs"
    for i, p in enumerate(datos.get("preguntas") or [], 1):
        yield "Pregunta %d" % i, p, "imgs"
        yield "Pregunta %d (motivación)" % i, p, "imgsLaw"


def todas(datos):
    """Todas las imágenes del supuesto: (dónde, imagen)."""
    for donde, duenno, clave in recorrer(datos):
        for im in duenno.get(clave) or []:
            yield donde, im


def rutas(datos):
    """Los «src» que usa el supuesto, sin repetir y en orden."""
    vistos = []
    for _, im in todas(datos):
        if im.get("src") and im["src"] not in vistos:
            vistos.append(im["src"])
    return vistos


def nombre_de(im):
    return Path(im.get("origen") or im.get("src") or "").name


def para_guardar(datos):
    """Copia de los datos tal y como van al archivo: sin «origen» y sin listas de
    imágenes vacías (así un supuesto sin imágenes se guarda igual que siempre)."""
    d = copy.deepcopy(datos)
    for _, duenno, clave in recorrer(d):
        lista = [{"src": im["src"], "pie": im.get("pie", "")} for im in duenno.get(clave) or [] if im.get("src")]
        for im in lista:
            if not im["pie"]:
                del im["pie"]
        if lista:
            duenno[clave] = lista
        else:
            duenno.pop(clave, None)
    return d


# ── nombres y carpetas ──────────────────────────────────────────────
def nombre_limpio(nombre):
    """«Nómina de marzo (2).PNG» → «nomina-de-marzo-2.png»: sin acentos ni espacios."""
    p = Path(nombre)
    base = unicodedata.normalize("NFKD", p.stem).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower() or "imagen"
    return base[:60] + p.suffix.lower()


def carpeta_de(ruta_html):
    """Carpeta complementaria de un supuesto: supuestos/img/NOMBRE/."""
    ruta_html = Path(ruta_html)
    return ruta_html.parent / CARPETA / ruta_html.stem


def _retiradas(raiz, ruta_html):
    return Path(raiz) / ".historial" / CARPETA / Path(ruta_html).stem


def _iguales(a, b):
    try:
        return a.stat().st_size == b.stat().st_size and a.read_bytes() == b.read_bytes()
    except OSError:
        return False


def _origen_de(im, ruta_anterior, destino, raiz):
    """Dónde está ahora mismo el archivo de una imagen, o None."""
    candidatos = []
    if im.get("origen"):
        candidatos.append(Path(im["origen"]))
    if im.get("src"):
        for html in (destino, ruta_anterior):
            if html:
                candidatos.append(Path(html).parent / im["src"])
        if raiz:
            for html in (destino, ruta_anterior):
                if html:
                    candidatos.append(_retiradas(raiz, html) / Path(im["src"]).name)
    return next((c for c in candidatos if c.is_file()), None)


def repartir(datos, destino, ruta_anterior=None, raiz=None):
    """Al guardar el supuesto en «destino»: copia cada imagen a su carpeta
    complementaria, deja su «src» apuntando allí y aparta las que ya no se usan.

    ruta_anterior: el .html de donde venía el supuesto («Guardar como», duplicar).
    raiz: carpeta del proyecto, para apartar en .historial/ (None = se borran).
    Devuelve (copiadas, retiradas, faltan) con nombres de archivo."""
    destino = Path(destino)
    carpeta = carpeta_de(destino)
    copiadas, faltan, en_uso = [], [], set()
    for donde, im in todas(datos):
        origen = _origen_de(im, ruta_anterior, destino, raiz)
        if origen is None:
            faltan.append("%s: %s" % (donde, nombre_de(im)))     # se deja como está: puede volver
            continue
        if origen.parent.resolve() == carpeta.resolve():
            final = origen
        else:
            carpeta.mkdir(parents=True, exist_ok=True)
            nombre = nombre_limpio(origen.name)
            final, n = carpeta / nombre, 1
            # Mismo nombre con otro contenido: se numera en vez de pisar la otra imagen.
            while final.exists() and not _iguales(final, origen):
                n += 1
                final = carpeta / ("%s-%d%s" % (Path(nombre).stem, n, Path(nombre).suffix))
            if not final.exists():
                shutil.copy2(origen, final)
                copiadas.append(final.name)
        im["src"] = "%s/%s/%s" % (CARPETA, destino.stem, final.name)
        im.pop("origen", None)
        en_uso.add(final.name)

    retiradas = []
    if carpeta.is_dir():
        for f in sorted(carpeta.iterdir()):
            if not f.is_file() or f.name in en_uso or f.suffix.lower() not in EXTENSIONES:
                continue
            if raiz:
                aparte = _retiradas(raiz, destino)
                aparte.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, aparte / f.name)
            f.unlink()
            retiradas.append(f.name)
        if not any(carpeta.iterdir()):
            carpeta.rmdir()
    return copiadas, retiradas, faltan


# ── para el menú, la subida y las comprobaciones ────────────────────
def en_proyecto(datos, ruta_html):
    """Rutas de las imágenes respecto a la raíz del proyecto («supuestos/img/…»)."""
    carpeta = Path(ruta_html).parent.name
    return ["%s/%s" % (carpeta, src) for src in rutas(datos)]


def avisos(datos, carpeta_html=None):
    """Textos de aviso: más de MAXIMO, formato raro, archivo que falta o que pesa mucho."""
    res = []
    for donde, duenno, clave in recorrer(datos):
        lista = duenno.get(clave) or []
        if len(lista) > MAXIMO:
            res.append("%s: tiene %d imágenes y solo se muestran %d." % (donde, len(lista), MAXIMO))
        for im in lista:
            nombre = nombre_de(im)
            if Path(nombre).suffix.lower() not in EXTENSIONES:
                res.append("%s: «%s» no es PNG, JPG, GIF ni WebP y puede no verse." % (donde, nombre))
            archivo = Path(im["origen"]) if im.get("origen") else (
                Path(carpeta_html) / im["src"] if carpeta_html and im.get("src") else None)
            if archivo is None:
                continue
            if not archivo.is_file():
                res.append("%s: no encuentro la imagen «%s»." % (donde, nombre))
            elif archivo.stat().st_size > PESO_AVISO:
                res.append("%s: la imagen «%s» pesa %d KB; conviene reducirla (tarda en cargar con datos móviles)."
                           % (donde, nombre, archivo.stat().st_size // 1024))
    return res


def acompanantes(marcados, disponibles):
    """Al subir: las imágenes (nuevas, cambiadas o retiradas) de los supuestos marcados
    que no se habían marcado. Así un supuesto nunca se publica sin sus imágenes."""
    carpetas = []
    for r in marcados:
        p = Path(r)
        if p.suffix.lower() == ".html":
            carpetas.append("%s/%s/%s/" % (p.parent.as_posix(), CARPETA, p.stem))
    return [r for r in disponibles
            if r not in marcados and any(r.startswith(c) for c in carpetas)]


# ── vista previa y exportación autónoma ─────────────────────────────
def data_uri(ruta):
    ruta = Path(ruta)
    tipo = mimetypes.guess_type(ruta.name)[0] or ("image/webp" if ruta.suffix.lower() == ".webp" else "application/octet-stream")
    return "data:%s;base64,%s" % (tipo, base64.b64encode(ruta.read_bytes()).decode("ascii"))


def para_vista(datos, carpeta_html=None, incrustar=False):
    """Copia de los datos para enseñarlos SIN guardar: las imágenes aún sin repartir
    apuntan a su archivo de origen. Con incrustar=True todas van dentro (data:),
    que es lo que necesita el HTML autónomo. Devuelve (datos, faltan)."""
    d = copy.deepcopy(datos)
    faltan = []
    for donde, im in todas(d):
        origen = Path(im["origen"]) if im.get("origen") else (
            Path(carpeta_html) / im["src"] if carpeta_html and im.get("src") else None)
        if im.get("src", "").startswith("data:"):
            continue
        if origen is None or not origen.is_file():
            if incrustar or im.get("origen"):
                faltan.append("%s: %s" % (donde, nombre_de(im)))
            continue
        if incrustar:
            im["src"] = data_uri(origen)
        elif im.get("origen"):
            im["src"] = origen.resolve().as_uri()
    return d, faltan

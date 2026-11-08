# -*- coding: utf-8 -*-
"""
ESCRIBIR ARCHIVOS SIN RIESGO DE DEJARLOS A MEDIAS
═════════════════════════════════════════════════
Parte del editor de supuestos (sin ventana). Primero se escribe una copia
temporal junto al archivo y luego se cambia por el original de una sola vez
(os.replace). Si el programa se cierra a mitad, o OneDrive o el antivirus
bloquean el archivo en ese momento, el original sigue entero.
"""
import os
import tempfile
import time
from pathlib import Path


def escribir_seguro(ruta, texto, encoding="utf-8"):
    ruta = Path(ruta)
    fd, tmp = tempfile.mkstemp(prefix="." + ruta.name + ".", suffix=".tmp", dir=str(ruta.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(texto)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.chmod(tmp, os.stat(ruta).st_mode & 0o777)     # conserva los permisos del original
        except OSError:
            os.chmod(tmp, 0o644)
        for intento in range(5):
            try:
                os.replace(tmp, ruta)
                return
            except PermissionError:          # Windows: otro programa lo tiene abierto un instante
                if intento == 4:
                    raise
                time.sleep(0.2 * (intento + 1))
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def huella_disco(ruta):
    """(fecha de modificación, tamaño) del archivo, o None si no existe."""
    try:
        st = os.stat(ruta)
        return (st.st_mtime_ns, st.st_size)
    except (OSError, TypeError):
        return None

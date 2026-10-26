# -*- coding: utf-8 -*-
"""
SINCRONIZAR CON GITHUB USANDO GIT  (botón «☁ Sincronizar» del editor)
═════════════════════════════════════════════════════════════════════
Parte del editor de supuestos. Sin ventana (se prueba sin tkinter). Necesita git
instalado y que la carpeta del proyecto sea un clon del repositorio.

Destinos de la subida:
    "dia"        rama propia del día («editor-AAAA-MM-DD»); luego se fusiona en GitHub
    "actual"     la rama que tengas abierta ahora mismo
    "principal"  directamente la rama principal del repositorio

El editor nunca ve la contraseña ni el token: los gestiona git.
"""
import os
import re
import subprocess
from datetime import date
from pathlib import Path

PREFIJOS_FUERA = (".recuperacion_", "PARA_SUBIR/", ".git/", ".historial/")
NOMBRES_FUERA = {".editor_prefs.json", ".estado_local.json", ".DS_Store", "Thumbs.db"}
SUFIJOS_FUERA = (".bak", ".pyc", ".tmp")
DESTINOS = ("dia", "actual", "principal")


class ErrorGit(Exception):
    """Fallo de git con un mensaje que se puede enseñar tal cual."""


def _git(raiz, *args, permitir_fallo=False):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C", LANGUAGE="C")
    try:
        r = subprocess.run(["git", "-C", str(raiz), *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=180)
    except FileNotFoundError:
        raise ErrorGit("No encuentro git. Instálalo (git-scm.com o GitHub Desktop) y reinicia el editor.")
    except subprocess.TimeoutExpired:
        raise ErrorGit("git ha tardado demasiado (¿sin conexión o esperando un inicio de sesión?).")
    salida = (r.stdout + r.stderr).rstrip()
    if r.returncode != 0 and not permitir_fallo:
        raise ErrorGit(traducir(salida))
    return r.returncode, salida


def traducir(texto):
    """Pasa los errores típicos de git a una frase entendible."""
    t = texto.lower()
    pistas = (
        (("please tell me who you are", "unable to auto-detect email"),
         "git no sabe quién eres. Ejecuta una vez en una terminal:\n"
         "  git config --global user.name \"Tu nombre\"\n  git config --global user.email \"tu@correo\""),
        (("authentication failed", "could not read username", "terminal prompts disabled",
          "invalid username or password"),
         "GitHub no te ha reconocido. Inicia sesión una vez con GitHub Desktop o con «git push» "
         "en una terminal; después el botón funcionará."),
        (("permission denied", "403", "protected branch", "not allowed"),
         "GitHub no te deja subir a esa rama (permisos o rama protegida). Prueba con la rama del día."),
        (("could not resolve host", "unable to access", "network is unreachable"),
         "No hay conexión con GitHub."),
        (("would be overwritten", "your local changes", "needs merge"),
         "Hay cambios tuyos que chocan con los de GitHub. Sube primero lo tuyo a la rama del día "
         "o pide ayuda antes de seguir; no se ha tocado nada."),
        (("not possible to fast-forward", "diverging", "non-fast-forward", "rejected"),
         "La rama de GitHub tiene cambios que tú no tienes y los tuyos no encajan encima. "
         "Usa la rama del día para no pisar nada."),
        (("not a git repository",),
         "Esta carpeta no es un clon del repositorio (falta «.git»)."),
    )
    for claves, frase in pistas:
        if any(c in t for c in claves):
            return frase + "\n\n(git dijo: %s)" % texto.strip().splitlines()[-1][:200] if texto.strip() else frase
    return texto.strip() or "git ha fallado sin dar explicación."


def hay_git():
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=20)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def es_clon(raiz):
    return (Path(raiz) / ".git").exists()


def rama_actual(raiz):
    rc, out = _git(raiz, "rev-parse", "--abbrev-ref", "HEAD")
    return out.strip()


def rama_principal(raiz):
    """La rama por defecto del repositorio en GitHub (si no se sabe, la actual)."""
    rc, out = _git(raiz, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", permitir_fallo=True)
    out = out.strip()
    if rc == 0 and out.startswith("origin/"):
        return out[len("origin/"):]
    for cand in ("main", "master"):
        rc, _ = _git(raiz, "rev-parse", "--verify", "-q", "refs/remotes/origin/" + cand, permitir_fallo=True)
        if rc == 0:
            return cand
    return rama_actual(raiz)


def nombre_rama_dia(hoy=None):
    return "editor-%s" % (hoy or date.today()).isoformat()


def rama_destino(raiz, destino, hoy=None):
    if destino == "dia":
        return nombre_rama_dia(hoy)
    if destino == "principal":
        return rama_principal(raiz)
    if destino == "actual":
        return rama_actual(raiz)
    raise ErrorGit("Destino desconocido: %s" % destino)


def _ignorado(ruta):
    nombre = ruta.rsplit("/", 1)[-1]
    return (nombre in NOMBRES_FUERA or nombre.endswith(SUFIJOS_FUERA)
            or any(ruta.startswith(p) or ("/" + p) in ruta for p in PREFIJOS_FUERA))


def estado(raiz):
    """(nuevos, modificados, borrados) como listas de rutas relativas con «/»."""
    _, out = _git(raiz, "status", "--porcelain=v1", "-uall", "-z")
    nuevos, modif, borrados = [], [], []
    partes = out.split("\0") if out else []
    i = 0
    while i < len(partes):
        p = partes[i]
        i += 1
        if len(p) < 4:
            continue
        x, y, ruta = p[0], p[1], p[3:]
        if x in "RC":                    # renombrado/copiado: la siguiente pieza es el origen
            i += 1
        if _ignorado(ruta):
            continue
        if "?" in (x, y) or "A" in (x, y):
            nuevos.append(ruta)
        elif "D" in (x, y):
            borrados.append(ruta)
        else:
            modif.append(ruta)
    return sorted(nuevos), sorted(modif), sorted(borrados)


def traer(raiz):
    """Trae lo último de GitHub a la rama actual sin mezclar nada raro. Devuelve un texto."""
    _git(raiz, "fetch", "--prune", "origin")
    rc, _ = _git(raiz, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", permitir_fallo=True)
    if rc != 0:
        return "Esta rama aún no existe en GitHub: no hay nada que traer."
    _, out = _git(raiz, "pull", "--ff-only")
    return "Al día con GitHub." if "up to date" in out.lower() else "Traído lo último de GitHub."


def commits_atras(raiz):
    """Cuántos commits tiene la rama en GitHub que tú aún no tienes (0 si no hay red o upstream)."""
    try:
        _git(raiz, "fetch", "--quiet", "origin")
        rc, out = _git(raiz, "rev-list", "--count", "HEAD..@{u}", permitir_fallo=True)
        return int(out.strip()) if rc == 0 and out.strip().isdigit() else 0
    except ErrorGit:
        return 0


def _enlace(raiz, rama):
    rc, url = _git(raiz, "remote", "get-url", "origin", permitir_fallo=True)
    m = re.search(r"github\.com[:/]([^/\s]+)/([^/\s]+?)(?:\.git)?$", url.strip()) if rc == 0 else None
    return "https://github.com/%s/%s/tree/%s" % (m.group(1), m.group(2), rama) if m else ""


def subir(raiz, archivos, mensaje, destino="dia", hoy=None):
    """Sube SOLO `archivos` (rutas relativas). Devuelve (texto, enlace). Lanza ErrorGit si falla."""
    archivos = [a for a in archivos if not _ignorado(a)]
    if not archivos:
        raise ErrorGit("No hay ningún archivo marcado para subir.")
    if not mensaje.strip():
        raise ErrorGit("Escribe un mensaje para describir el cambio.")
    rama = rama_destino(raiz, destino, hoy)
    actual = rama_actual(raiz)
    if rama != actual:
        rc, _ = _git(raiz, "rev-parse", "--verify", "-q", "refs/heads/" + rama, permitir_fallo=True)
        if rc == 0:
            _git(raiz, "checkout", rama)
        elif destino == "principal":
            _git(raiz, "checkout", "-b", rama, "origin/" + rama)
        else:
            _git(raiz, "checkout", "-b", rama)
    _git(raiz, "reset", "-q")                                   # no arrastrar nada que no hayas marcado
    _git(raiz, "add", "-A", "--", *archivos)
    rc, _ = _git(raiz, "diff", "--cached", "--quiet", permitir_fallo=True)
    if rc == 0:
        return "No había nada nuevo que subir en esos archivos.", _enlace(raiz, rama)
    _git(raiz, "commit", "-q", "-m", mensaje.strip())
    _git(raiz, "push", "-u", "origin", rama)
    return "Subido a la rama «%s» (%d archivo(s))." % (rama, len(archivos)), _enlace(raiz, rama)


def mensaje_sugerido(nuevos, modif, borrados):
    todos = nuevos + modif
    if len(todos) == 1 and not borrados:
        return "Actualizo %s" % todos[0].rsplit("/", 1)[-1]
    return "Actualizo %d archivos (%d nuevos, %d modificados, %d borrados)" % (
        len(todos) + len(borrados), len(nuevos), len(modif), len(borrados))

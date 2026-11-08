# -*- coding: utf-8 -*-
"""
OPERACIONES CON LA LISTA DE PREGUNTAS  (sin ventana)
════════════════════════════════════════════════════
Parte del editor de supuestos. Todo lo que cambia o filtra la lista de
preguntas sin depender de tkinter, para poder probarlo solo:

  tipo_de_bloque      «test» (teoría) o «supuesto»
  filas               lo que enseña cada fila de la lista (columnas)
  filtrar             qué preguntas casan con un filtro (texto, errores, bloque…)
  mover_varias        sube o baja varias a la vez, sin salirse de su bloque
  borrar_varias, duplicar_varias
"""
import copy
import re

import revision

RE_TAG = re.compile(r"<[^<>]*>")

FILTROS_FIJOS = ("Todas", "Con errores", "Con avisos", "Sin motivación", "Respuesta múltiple",
                 "Con modo foco")


def tipo_de_bloque(datos, bloque_id):
    for b in datos.get("bloques") or []:
        if b.get("id") == bloque_id:
            return b.get("tipo") or "supuesto"
    return "supuesto"


def _visible(texto):
    return " ".join(RE_TAG.sub(" ", str(texto or "")).split())


def filas(datos, hallazgos=None):
    """[{n, num, bloque, enunciado, texto, marcas, nivel, motivo}] para cada pregunta."""
    fallos = revision.por_pregunta(hallazgos if hallazgos is not None else revision.revisar(datos))
    res = []
    for n, p in enumerate(datos.get("preguntas") or []):
        marcas = ("📝" if tipo_de_bloque(datos, p.get("bloqueId")) == "test" else "") + \
                 ("🔎" if p.get("factIds") else "") + ("☑" if p.get("multiple") else "")
        nivel, motivo = fallos.get(n, ("", ""))
        res.append({"n": n, "num": n + 1, "bloque": p.get("bloqueId") or "",
                    "enunciado": p.get("statementId") or "—", "texto": _visible(p.get("q")),
                    "marcas": marcas, "nivel": nivel, "motivo": motivo})
    return res


def opciones_de_filtro(datos):
    """Lo que ofrece el desplegable de filtro: los fijos, cada bloque y cada enunciado."""
    res = list(FILTROS_FIJOS)
    res += ["Bloque %s" % b.get("id") for b in datos.get("bloques") or []]
    res += ["Enunciado %s" % e.get("id") for e in datos.get("enunciados") or []]
    return res


def filtrar(datos, filtro="Todas", texto="", hallazgos=None):
    """Índices (desde 0) de las preguntas que casan con el filtro y contienen `texto`
    (en la pregunta, las opciones, la motivación o la etiqueta; sin mirar el formato)."""
    preguntas = datos.get("preguntas") or []
    fallos = revision.por_pregunta(hallazgos if hallazgos is not None else revision.revisar(datos))
    texto = " ".join((texto or "").lower().split())
    res = []
    for n, p in enumerate(preguntas):
        if filtro == "Con errores" and fallos.get(n, ("",))[0] != "error":
            continue
        if filtro == "Con avisos" and fallos.get(n, ("",))[0] != "aviso":
            continue
        if filtro == "Sin motivación" and _visible(p.get("law")):
            continue
        if filtro == "Respuesta múltiple" and not p.get("multiple"):
            continue
        if filtro == "Con modo foco" and not p.get("factIds"):
            continue
        if filtro.startswith("Bloque ") and p.get("bloqueId") != filtro[7:]:
            continue
        if filtro.startswith("Enunciado ") and (p.get("statementId") or "") != filtro[10:]:
            continue
        if texto:
            todo = " ".join([_visible(p.get("q")), _visible(p.get("law")), _visible(p.get("tip")),
                             str(p.get("tag") or "")] + [_visible(a) for a in p.get("a") or []]).lower()
            if texto not in todo and texto != str(n + 1):
                continue
        res.append(n)
    return res


def mover_varias(preguntas, indices, paso):
    """Sube (paso=-1) o baja (paso=1) las preguntas `indices` un puesto, todas a la vez.
    Ninguna se sale de su bloque. Devuelve los índices nuevos, o None si alguna está
    ya en el borde de su bloque (entonces no se mueve ninguna)."""
    if paso not in (-1, 1):
        return None
    elegidas = set(i for i in indices if 0 <= i < len(preguntas))
    if not elegidas:
        return None
    lista = list(preguntas)
    # Hacia arriba se recorre de arriba abajo (y al revés): cada elegida cambia el
    # sitio con su vecina si la vecina no está elegida; un grupo seguido se mueve entero.
    for i in sorted(elegidas, reverse=(paso > 0)):
        destino = i + paso
        if destino in elegidas:
            continue
        if destino < 0 or destino >= len(lista) or \
                lista[destino].get("bloqueId") != lista[i].get("bloqueId"):
            return None
        lista[i], lista[destino] = lista[destino], lista[i]
        elegidas.discard(i)
        elegidas.add(destino)
    preguntas[:] = lista
    return sorted(elegidas)


def borrar_varias(preguntas, indices):
    """Borra las preguntas `indices`. Devuelve cuántas ha borrado."""
    quitar = sorted(set(i for i in indices if 0 <= i < len(preguntas)), reverse=True)
    for i in quitar:
        del preguntas[i]
    return len(quitar)


def duplicar_varias(preguntas, indices):
    """Pone una copia de cada pregunta justo detrás de la última elegida. Devuelve los índices de las copias."""
    indices = sorted(set(i for i in indices if 0 <= i < len(preguntas)))
    if not indices:
        return []
    copias = [copy.deepcopy(preguntas[i]) for i in indices]
    destino = indices[-1] + 1
    preguntas[destino:destino] = copias
    return list(range(destino, destino + len(copias)))

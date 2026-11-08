# -*- coding: utf-8 -*-
"""
GENERAR UN SIMULACRO  (sin ventana)
═══════════════════════════════════
Parte del editor de supuestos. Monta un examen nuevo con preguntas sacadas al
azar de varios supuestos:

  · TEORÍA: preguntas sueltas de los bloques tipo test.
  · CASOS PRÁCTICOS: un enunciado entero con TODAS sus preguntas (no tiene
    sentido una pregunta de un caso sin su caso).

Las preguntas repetidas en varios supuestos (las versiones «I», por ejemplo) se
cuentan una sola vez. Con la misma semilla sale el mismo simulacro.
"""
import copy
import random
import re

import datos_html

RE_TAG = re.compile(r"<[^<>]*>")


def _plano(t):
    return " ".join(RE_TAG.sub("", str(t or "")).lower().split())


def _tipo(datos, bloque_id):
    for b in datos.get("bloques") or []:
        if b.get("id") == bloque_id:
            return b.get("tipo") or "supuesto"
    return "supuesto"


def piezas(fuentes):
    """De [(nombre, datos)] saca lo que se puede sortear, sin repetidos:
    (teoría, casos). Teoría: [(nombre, pregunta)]. Casos: [(nombre, enunciado, [preguntas])]."""
    teoria, casos, vistas, vistos = [], [], set(), set()
    for nombre, datos in fuentes:
        enunciados = {e.get("id"): e for e in datos.get("enunciados") or []}
        grupos = {}
        for p in datos.get("preguntas") or []:
            sid = p.get("statementId")
            if _tipo(datos, p.get("bloqueId")) == "supuesto" and sid in enunciados:
                grupos.setdefault(sid, []).append(p)
                continue
            huella = (_plano(p.get("q")), tuple(_plano(a) for a in p.get("a") or []))
            if huella[0] and huella not in vistas:
                vistas.add(huella)
                teoria.append((nombre, p))
        for sid, ps in grupos.items():
            e = enunciados[sid]
            huella = (_plano(e.get("title")), _plano(ps[0].get("q")))
            if huella not in vistos:
                vistos.add(huella)
                casos.append((nombre, e, ps))
    return teoria, casos


def _bloque_como(fuentes, tipo, ident):
    """Bloque nuevo que copia la puntuación y el aspecto del primero de ese tipo
    (pero no su envío a Google, que es de su examen)."""
    nuevo = datos_html.bloque_vacio(tipo, ident)
    for _n, datos in fuentes:
        for b in datos.get("bloques") or []:
            if (b.get("tipo") or "supuesto") == tipo:
                for k in ("titulo", "color", "modo", "cabeceraSobreEnunciado", "opcionUnaEnUna",
                          "porIntento", "acierto", "fallo", "blanco"):
                    if k in b:
                        nuevo[k] = copy.deepcopy(b[k])
                return nuevo
    return nuevo


def _minutos(fuentes, elegidas):
    """Tiempo en proporción a lo que se coge de cada supuesto, redondeado a 5."""
    total = 0.0
    for nombre, datos in fuentes:
        n = len(datos.get("preguntas") or [])
        if n and elegidas.get(nombre):
            minutos = (datos.get("config") or {}).get("minutos") or 30
            total += float(minutos) * elegidas[nombre] / n
    return max(10, int(5 * round(total / 5.0)))


def generar(fuentes, n_teoria=0, n_casos=0, semilla=None, titulo=None):
    """fuentes: [(nombre, datos)]. Devuelve (datos del simulacro, avisos).
    Pide `n_teoria` preguntas de teoría y `n_casos` casos prácticos; si no hay
    tantos, coge los que haya y lo dice en los avisos."""
    azar = random.Random(semilla)
    teoria, casos = piezas(fuentes)
    avisos = []
    if n_teoria > len(teoria):
        avisos.append("Solo hay %d preguntas de teoría distintas; se ponen todas." % len(teoria))
    if n_casos > len(casos):
        avisos.append("Solo hay %d casos prácticos distintos; se ponen todos." % len(casos))
    teoria = azar.sample(teoria, min(n_teoria, len(teoria)))
    casos = azar.sample(casos, min(n_casos, len(casos)))

    d = datos_html.datos_vacios()
    d["bloques"], d["enunciados"], d["preguntas"] = [], [], []
    elegidas = {}
    if casos:
        bloque = _bloque_como(fuentes, "supuesto", "B%d" % (len(d["bloques"]) + 1))
        d["bloques"].append(bloque)
        for k, (nombre, e, ps) in enumerate(casos, 1):
            nuevo = copy.deepcopy(e)
            nuevo["id"], nuevo["number"] = "E%d" % k, str(k)
            d["enunciados"].append(nuevo)
            for p in ps:
                q = copy.deepcopy(p)
                q["bloqueId"], q["statementId"] = bloque["id"], nuevo["id"]
                d["preguntas"].append(q)
            elegidas[nombre] = elegidas.get(nombre, 0) + len(ps)
    if teoria:
        bloque = _bloque_como(fuentes, "test", "B%d" % (len(d["bloques"]) + 1))
        d["bloques"].append(bloque)
        for nombre, p in teoria:
            q = copy.deepcopy(p)
            q["bloqueId"], q["statementId"], q["factIds"] = bloque["id"], None, []
            d["preguntas"].append(q)
            elegidas[nombre] = elegidas.get(nombre, 0) + 1
    if not d["bloques"]:
        d["bloques"] = [datos_html.bloque_vacio("supuesto", "B1")]
        avisos.append("No se ha podido coger ninguna pregunta.")

    cfg = d["config"]
    cfg["titulo"] = titulo or "Simulacro"
    cfg["referencia"] = "SIM-%s" % (semilla if semilla is not None else azar.randint(1000, 9999))
    cfg["ambito"] = "Preguntas de %d supuesto(s)" % len(elegidas) if elegidas else cfg["ambito"]
    cfg["minutos"] = _minutos(fuentes, elegidas)
    return d, avisos

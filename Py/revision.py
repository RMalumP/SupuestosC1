# -*- coding: utf-8 -*-
"""
REVISIÓN DE UN SUPUESTO  (una sola lista de reglas para todo)
═════════════════════════════════════════════════════════════
Parte del editor de supuestos. Sin ventana (se prueba sin tkinter).

Antes había cuatro revisores con reglas distintas (los colores de la lista de
preguntas, el aviso al guardar, «Comprobar» y validar_supuestos.py), y una
pregunta podía salir bien en uno y mal en otro. Ahora todos usan revisar():

    revisar(datos)  →  [Hallazgo(nivel, pregunta, texto, corto), …]
        nivel     "error" (hay que arreglarlo; el validador del proyecto falla)
                  o "aviso" (conviene mirarlo)
        pregunta  número de pregunta desde 0, o None si es del supuesto entero
        texto     frase completa (pestaña Comprobar, validador)
        corto     dos o tres palabras (lista de preguntas)

Acepta tanto los datos ya normalizados del editor como el JSON tal cual del
archivo (el validador lo lee sin normalizar).
"""
import re
from collections import Counter, namedtuple

MIN_OPCIONES = 2
LETRAS = "ABCDEFG"

Hallazgo = namedtuple("Hallazgo", "nivel pregunta texto corto")


def _norm(t):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(t or ""))).strip().lower()


def _correctas(q):
    cor = q.get("correctas")
    if cor is None and isinstance(q.get("c"), int):
        cor = [q["c"]]
    return list(cor or [])


def revisar(d, normas=None, parecidas=False):
    """Todos los problemas del supuesto, errores primero dentro de cada sitio.
    normas: lista de normas_enlaces (para avisar de citas que no se enlazarán).
    parecidas: buscar también preguntas casi iguales (más lento)."""
    res = []

    def error(texto, n=None, corto=""):
        res.append(Hallazgo("error", n, texto, corto))

    def aviso(texto, n=None, corto=""):
        res.append(Hallazgo("aviso", n, texto, corto))

    cfg = d.get("config") or {}
    if not str(cfg.get("titulo", "")).strip():
        error("Los datos generales no tienen título.")
    try:
        if float(cfg.get("minutos", 0)) < 1:
            error("El tiempo por defecto debe ser de 1 minuto o más.")
    except (TypeError, ValueError):
        error("El tiempo por defecto no es un número.")

    bloques = d.get("bloques") or []
    ids_b = [b.get("id") for b in bloques]
    for i, n in Counter(ids_b).items():
        if n > 1:
            error("El bloque «%s» está repetido." % i)

    enunciados = d.get("enunciados") or []
    ids_e = [str(e.get("id") or "") for e in enunciados]
    if any(not i.strip() for i in ids_e):
        error("Hay un enunciado sin identificador.")
    for i in sorted({i for i in ids_e if i and ids_e.count(i) > 1}):
        error("Identificador de enunciado repetido: «%s»." % i)
    hechos_de, ocultos_de = {}, {}
    for e in enunciados:
        hechos = e.get("factBlocks") or []
        if not hechos:
            aviso("El enunciado %s no tiene ningún bloque de hechos." % e.get("id"))
        ids_h = []
        for j, h in enumerate(hechos, 1):
            if "paragraphs" in h and not h.get("paragraphs"):
                aviso("Enunciado %s, bloque %d: no tiene texto." % (e.get("id"), j))
            if h.get("id"):
                ids_h.append(h["id"])
        for i, n in Counter(ids_h).items():
            if n > 1:
                error("Enunciado %s: código de bloque de hechos repetido «%s»." % (e.get("id"), i))
        hechos_de[e.get("id")] = set(ids_h)
        ocultos_de[e.get("id")] = {h.get("id") for h in hechos if h.get("hidden")}

    preguntas = d.get("preguntas") or []
    if not preguntas:
        error("El supuesto no tiene ninguna pregunta.")

    # ── bloques ──
    for b in bloques:
        suyas = [q for q in preguntas if q.get("bloqueId") == b.get("id")]
        titulo = b.get("titulo") or b.get("id")
        if not suyas:
            aviso("El bloque «%s» no tiene ninguna pregunta: no saldrá en el examen." % titulo)
        if "acierto" in b and (b.get("acierto") or 0) <= 0:
            error("El bloque «%s» no suma nada por acierto." % titulo)
        if b.get("porIntento") and b["porIntento"] > len(suyas):
            aviso("El bloque «%s» pide %d preguntas por intento pero solo tiene %d."
                  % (titulo, b["porIntento"], len(suyas)))
        if b.get("tipo") == "test" and any(q.get("statementId") for q in suyas):
            aviso("El bloque de teoría «%s» tiene preguntas con enunciado: no se mostrará." % titulo)
        sueltas = [q for q in suyas if not q.get("statementId")]
        if b.get("tipo") == "supuesto" and sueltas and len(sueltas) != len(suyas):
            aviso("El bloque «%s» mezcla preguntas con y sin enunciado (%d sueltas)." % (titulo, len(sueltas)))

    # ── opciones del panel de la página que dejan cosas sin usar ──
    interfaz = d.get("interfaz") or {}
    opcion_una = interfaz.get("opcionUnaEnUna") or {}
    opcion_foco = interfaz.get("opcionFoco") or {}
    if bloques and interfaz:
        if opcion_una.get("visible") is False:
            aviso("La opción «ver las preguntas de una en una» está OCULTA (pestaña 5): el alumno no "
                  "verá las casillas de cada bloque y cada uno se quedará como diga su modo en la pestaña 2.")
        elif not [b for b in bloques if b.get("opcionUnaEnUna", True)]:
            aviso("Ningún bloque saca su casilla en el panel ⚙ (pestaña 2): la opción «ver las preguntas "
                  "de una en una» no aparecerá.")
        vinculadas = [q for q in preguntas if q.get("factIds")]
        if opcion_foco.get("visible") is not False and not vinculadas and enunciados:
            aviso("El modo foco está a la vista pero ninguna pregunta tiene hechos vinculados "
                  "(pestaña 4): encenderlo no cambiará nada.")
        if vinculadas:
            if opcion_foco.get("visible") is False and not opcion_foco.get("activa"):
                aviso("Hay %d pregunta(s) con hechos vinculados, pero el modo foco está oculto y no "
                      "arranca activado: nunca se usarán." % len(vinculadas))
            alcanzable = [b for b in bloques
                          if b.get("tipo") != "test" and (b.get("modo") == "individual"
                                                          or opcion_una.get("activa")
                                                          or (b.get("opcionUnaEnUna", True)
                                                              and opcion_una.get("visible") is not False))]
            if not alcanzable:
                aviso("Hay preguntas con hechos vinculados, pero ningún bloque de supuesto puede verse "
                      "de una en una: el modo foco no llegará a aplicarse (solo actúa de una en una).")

    # ── cada pregunta ──
    respuestas_examen = cfg.get("respuestas") or 0
    textos = Counter(_norm(q.get("q", "")) for q in preguntas)
    for n, q in enumerate(preguntas):
        i = n + 1
        texto_q = _norm(q.get("q", ""))
        if not texto_q:
            error("Pregunta %d: falta el texto de la pregunta." % i, n, "sin texto")
        elif textos[texto_q] > 1:
            aviso("Pregunta %d: hay otra pregunta con el mismo texto." % i, n, "texto repetido")
        if q.get("bloqueId") and ids_b and q["bloqueId"] not in ids_b:
            error("Pregunta %d: pertenece al bloque «%s», que no existe." % (i, q["bloqueId"]), n, "sin bloque")
        sid = q.get("statementId")
        if sid and sid not in ids_e:
            error("Pregunta %d: apunta al enunciado «%s», que no existe." % (i, sid), n, "enunciado inexistente")
        fact = q.get("factIds") or []
        if fact and sid in hechos_de:
            perdidos = [x for x in fact if x not in hechos_de[sid]]
            if perdidos:
                error("Pregunta %d: vinculada a hechos que no están en su enunciado %s (%s)."
                      % (i, sid, ", ".join(perdidos)), n, "hechos perdidos")
            ocultos = [x for x in fact if x in ocultos_de.get(sid, set())]
            if ocultos:
                aviso("Pregunta %d: vinculada a hechos marcados como «no mostrar» (%s)."
                      % (i, ", ".join(ocultos)), n, "hechos ocultos")

        ops = [str(x) for x in (q.get("a") or [])]
        vacias = [k for k, t in enumerate(ops) if not _norm(t)]
        if vacias:
            error("Pregunta %d: opciones vacías (%s)." % (i, ", ".join(LETRAS[k % 7] for k in vacias)),
                  n, "opción vacía")
        if len(ops) < MIN_OPCIONES:
            error("Pregunta %d: solo tiene %d respuesta(s); hacen falta al menos %d."
                  % (i, len(ops), MIN_OPCIONES), n, "pocas opciones")
        llenas = [_norm(t) for t in ops if _norm(t)]
        if len(set(llenas)) != len(llenas):
            error("Pregunta %d: hay dos opciones con el mismo texto." % i, n, "opciones repetidas")

        cor = _correctas(q)
        if not cor:
            error("Pregunta %d: no tiene marcada ninguna respuesta correcta." % i, n, "sin correcta")
        else:
            if any(not isinstance(c, int) or c < 0 or c >= len(ops) for c in cor):
                error("Pregunta %d: una respuesta correcta apunta a una opción que no existe." % i,
                      n, "correcta perdida")
            if len(set(cor)) != len(cor):
                error("Pregunta %d: respuestas correctas repetidas." % i, n, "correctas repetidas")
            if len(cor) > 1 and not q.get("multiple"):
                error("Pregunta %d: tiene %d correctas pero NO es de respuesta múltiple (márcala como "
                      "múltiple o deja una sola)." % (i, len(cor)), n, "varias correctas")
            if q.get("multiple") and len(cor) < 2:
                aviso("Pregunta %d: está marcada como de respuesta múltiple pero solo tiene una correcta." % i,
                      n, "múltiple con una correcta")
            propia = q.get("respuestas") if isinstance(q.get("respuestas"), int) else 0
            cuantas = propia or respuestas_examen or len(ops)
            if cuantas and cuantas < len(cor) + (1 if len(ops) > len(cor) else 0):
                error("Pregunta %d: se pide que salgan %d respuestas, pero no caben las %d correctas y "
                      "al menos un distractor." % (i, cuantas, len(cor)), n, "pocas respuestas")
            elif propia and propia > len(ops):
                aviso("Pregunta %d: se piden %d respuestas y solo tiene %d escritas: saldrán las %d."
                      % (i, propia, len(ops), len(ops)), n, "faltan respuestas")
        if not _norm(q.get("law", "")):
            aviso("Pregunta %d: sin motivación legal (la corrección saldrá vacía)." % i, n, "sin motivación")

    # ── extras (usan herramientas_datos; se importa aquí para no hacer un círculo) ──
    if parecidas or normas:
        import herramientas_datos as herr
        if parecidas:
            for a, _donde, b, r in herr.duplicados(d):
                aviso("Pregunta %d se parece mucho a la %d (%d%%): ¿está repetida?" % (a, b, r * 100),
                      a - 1, "parecida a la %d" % b)
        if normas:
            for a, cita in herr.citas_sin_norma(d, normas):
                aviso("Pregunta %d: la cita «%s» no lleva ninguna norma conocida (pestaña 7): no se "
                      "enlazará al BOE." % (a, cita[:50]), a - 1, "cita sin norma")

    # ── preguntas del mismo enunciado que no van seguidas ──
    orden, vistos = [], set()
    for q in preguntas:
        sid = q.get("statementId")
        if not orden or orden[-1] != sid:
            if sid and sid in vistos:
                aviso("Las preguntas del enunciado «%s» no van todas seguidas: el enunciado se repetirá, "
                      "uno delante de cada grupo." % sid)
            orden.append(sid)
            if sid:
                vistos.add(sid)

    # errores antes que avisos, sin perder el orden de cada grupo
    return [h for h in res if h.nivel == "error"] + [h for h in res if h.nivel == "aviso"]


def por_pregunta(hallazgos):
    """{n.º de pregunta desde 0: (nivel, corto)} con el más grave de cada una (para la lista)."""
    res = {}
    for h in hallazgos:
        if h.pregunta is None:
            continue
        if h.pregunta not in res or (h.nivel == "error" and res[h.pregunta][0] != "error"):
            res[h.pregunta] = (h.nivel, h.corto or h.texto)
    return res


def errores(hallazgos):
    return [h.texto for h in hallazgos if h.nivel == "error"]


def avisos(hallazgos):
    return [h.texto for h in hallazgos if h.nivel == "aviso"]

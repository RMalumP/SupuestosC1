# -*- coding: utf-8 -*-
"""
PESTAÑA 6 · COMPROBAR (informe de revisión)
═══════════════════════════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
from editor_comun import *  # noqa: F401,F403


class PestanaComprobar:

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

        marco, self.txt_informe = caja_texto(panel, alto=30, formato=False)
        marco.pack(fill="both", expand=True, padx=10, pady=8)
        self.txt_informe.configure(font=("Consolas", 9))
        self.txt_informe.bind("<Double-Button-1>", self._ir_desde_informe, add="+")

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

        # ── opciones del panel de la página que dejan cosas sin usar ──
        interfaz = d.get("interfaz") or {}
        opcion_una = interfaz.get("opcionUnaEnUna") or {}
        opcion_foco = interfaz.get("opcionFoco") or {}
        con_casilla = [b for b in d["bloques"] if b.get("opcionUnaEnUna", True)]
        if opcion_una.get("visible") is False:
            avisos.append("La opción «ver las preguntas de una en una» está OCULTA (pestaña 5): "
                          "el alumno no verá las casillas de cada bloque y cada uno se quedará "
                          "como diga su modo en la pestaña 2.")
        elif not con_casilla:
            avisos.append("Ningún bloque saca su casilla en el panel ⚙ (pestaña 2): la opción "
                          "«ver las preguntas de una en una» no aparecerá.")

        vinculadas = [q for q in d["preguntas"] if q.get("factIds")]
        if opcion_foco.get("visible") is not False and not vinculadas and d["enunciados"]:
            avisos.append("El modo foco está a la vista pero ninguna pregunta tiene hechos "
                          "vinculados (pestaña 4): encenderlo no cambiará nada.")
        if vinculadas:
            if opcion_foco.get("visible") is False and not opcion_foco.get("activa"):
                avisos.append("Hay %d pregunta(s) con hechos vinculados, pero el modo foco está "
                              "oculto y no arranca activado: nunca se usarán." % len(vinculadas))
            alcanzable = [b for b in d["bloques"]
                          if b["tipo"] != "test" and (b["modo"] == "individual"
                                                      or opcion_una.get("activa")
                                                      or (b.get("opcionUnaEnUna", True)
                                                          and opcion_una.get("visible") is not False))]
            if not alcanzable:
                avisos.append("Hay preguntas con hechos vinculados, pero ningún bloque de "
                              "supuesto puede verse de una en una: el modo foco no llegará a "
                              "aplicarse (solo actúa de una en una, nunca en cadena).")

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
                               % (i, ", ".join(LETRAS[n] for n in vacias)))
            if len(p["a"]) < MIN_OPCIONES:
                errores.append("Pregunta %d: solo tiene %d respuesta(s); hacen falta al menos %d."
                               % (i, len(p["a"]), MIN_OPCIONES))
            normal = [" ".join(t.lower().split()) for t in p["a"] if t.strip()]
            if len(set(normal)) != len(normal):
                avisos.append("Pregunta %d: hay dos opciones con el mismo texto." % i)

            correctas = p.get("correctas") or []
            if not correctas:
                errores.append("Pregunta %d: no tiene marcada ninguna respuesta correcta." % i)
            if p.get("multiple") and len(correctas) < 2:
                avisos.append("Pregunta %d: está marcada como de respuesta múltiple pero solo "
                              "tiene una correcta." % i)
            if not p.get("multiple") and len(correctas) > 1:
                avisos.append("Pregunta %d: tiene %d correctas pero NO es de respuesta múltiple: "
                              "solo se dará por buena la primera." % (i, len(correctas)))

            # Cuántas respuestas verá el alumno en esta pregunta
            cuantas = p.get("respuestas") or d["config"].get("respuestas") or len(p["a"])
            if cuantas < len(correctas) + (1 if len(p["a"]) > len(correctas) else 0):
                avisos.append("Pregunta %d: se pide que salgan %d respuestas, pero tiene %d "
                              "correctas: saldrán más para que quepan todas."
                              % (i, cuantas, len(correctas)))
            elif p.get("respuestas") and p["respuestas"] > len(p["a"]):
                avisos.append("Pregunta %d: se piden %d respuestas y solo tiene %d escritas: "
                              "saldrán las %d." % (i, p["respuestas"], len(p["a"]), len(p["a"])))
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
        general = d["config"].get("respuestas", 0)
        lineas.append("Respuestas  : %s"
                      % ("las que tenga escritas cada pregunta" if not general
                         else "%d por pregunta (el resto se sortean)" % general))
        multiples = sum(1 for q in d["preguntas"] if q.get("multiple"))
        propias = sum(1 for q in d["preguntas"] if q.get("respuestas"))
        if multiples or propias:
            lineas.append("              %d de respuesta múltiple · %d con nº propio de respuestas"
                          % (multiples, propias))
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
            lineas.append("     empiezan %s (%s) · en el aleatorio salen %s"
                          % ("todas seguidas" if b["modo"] == "cadena" else "de una en una",
                             "el alumno puede cambiarlo" if b.get("opcionUnaEnUna", True)
                             else "sin casilla en el panel: no se puede cambiar",
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

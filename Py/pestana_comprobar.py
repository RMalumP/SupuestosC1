# -*- coding: utf-8 -*-
"""
PESTAÑA 6 · COMPROBAR (informe de revisión)
═══════════════════════════════════════════
Parte del editor de supuestos: los métodos de esta parte de la ventana viven aquí
y EditorApp (editor_supuestos.py) los hereda. No se ejecuta solo.
"""
import normas_enlaces
import revision
from tkinter import ttk
from editor_comun import (  # noqa: F401
    TEMA_DEFECTO, caja_texto, datos_a_json, nUm, poner_texto)


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
        d = self.datos
        try:
            normas = normas_enlaces.leer()[1]
        except OSError:
            normas = []
        # Las mismas reglas que la lista de preguntas, el aviso al guardar y el validador.
        hallazgos = revision.revisar(d, normas=normas, parecidas=True,
                                     carpeta=self.ruta.parent if self.ruta else None)
        errores, avisos = revision.errores(hallazgos), revision.avisos(hallazgos)

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

/* ════════════════════════════════════════════════════════════════
   LISTA DE SUPUESTOS DEL MENÚ
   El menú principal (index.html) y el modo sin conexión se montan
   a partir de este archivo. Hay UNA LÍNEA por supuesto.

   Para añadir un supuesto a mano, copia una línea de la lista, cámbiale
   los datos y GUÁRDALA CON LA COMA FINAL (menos la última, que no la lleva):

     { "seccion": "generales", "grupo": "iniciales", "archivo": "supuesto_4", "letra": "4",
       "ref": "S004", "titulo": "Supuesto 4 · Título", "desc": "15 preguntas · 30 minutos" },

   · seccion/grupo: dónde sale (mira «SECCIONES» más abajo). «examenes» va sin grupo.
   · archivo: nombre del .html de la carpeta supuestos/ SIN «.html».
   · letra: texto del círculo (máx. 4 caracteres).
   · "oculto": true  lo quita del menú sin borrarlo (se puede abrir con su enlace).
   Para comprobar que todo está bien:  python Py/validar_supuestos.py
   El editor de Python (editor_supuestos.py) hace este alta solo al guardar.
════════════════════════════════════════════════════════════════ */
(function (G) {
  "use strict";
  // >>> SECCIONES: orden y títulos de las secciones y grupos del menú
  var SECCIONES = [
  {"id": "temas", "titulo": "Supuestos por temas", "grupos": [{"id": "iniciales", "titulo": "Iniciales"}, {"id": "avanzados", "titulo": "Avanzados"}]},
  {"id": "generales", "titulo": "Supuestos generales", "grupos": [{"id": "iniciales", "titulo": "Iniciales"}, {"id": "avanzados", "titulo": "Avanzados"}]}
  ];
  // <<< SECCIONES

  // >>> SUPUESTOS: una línea por supuesto
  var SUPUESTOS = [
  {"seccion": "temas", "grupo": "iniciales", "archivo": "supuesto_T2I", "letra": "T2I", "ref": "T2I", "titulo": "SUPUESTO TEMA 2 Inicial. Encuadramientos y mas encuadramietos", "desc": "25 preguntas · 45 minutos · Legislación a 10 de octubre de 2026 · Tema 2."},
  {"seccion": "temas", "grupo": "avanzados", "archivo": "supuesto_T2", "letra": "T2", "ref": "T2", "titulo": "SUPUESTO TEMA 2. Encuadramientos y dolores de cabeza", "desc": "15 preguntas · 30 minutos · Legislación a 10 de octubre de 2026 · Tema 2."},
  {"seccion": "generales", "grupo": "iniciales", "archivo": "supuesto_1I", "letra": "I1", "ref": "S01I", "titulo": "SUPUESTO 1 Inicial. Conceptos básicos de temas 2 y 3", "desc": "15 preguntas · 30 minutos · Legislación a 27 de Septiembre de 2026 · Temas 2 y 3."},
  {"seccion": "generales", "grupo": "iniciales", "archivo": "supuesto_2I", "letra": "I2", "ref": "S02I", "titulo": "SUPUESTO 2 Inicial. Conceptos básicos de temas 4 y 7", "desc": "15 preguntas · 30 minutos · Legislación a 4 de octubre de 2026 · Temas 4 y 7."},
  {"seccion": "generales", "grupo": "avanzados", "archivo": "supuesto_0", "letra": "0", "ref": "S000", "titulo": "Supuesto 0 · Hay que espabilar que el verano se os va a comer", "desc": "15 preguntas · 30 minutos · Legislación a 28 de agosto de 2026 · Temas 1 al 13"},
  {"seccion": "generales", "grupo": "avanzados", "archivo": "supuesto_1", "letra": "1", "ref": "S001", "titulo": "Supuesto 1 · Los otros Alantara", "desc": "15 preguntas · 30 minutos · Legislación a 4 de Septiembre de 2026 · Temas Variados"},
  {"seccion": "generales", "grupo": "avanzados", "archivo": "supuesto_2", "letra": "2", "ref": "S002", "titulo": "Supuesto 2 · Un repasito antes de empezar", "desc": "15 preguntas · 30 minutos · Legislación a 11 de Septiembre de 2026 · Temas Variados"},
  {"seccion": "generales", "grupo": "avanzados", "archivo": "supuesto_3", "letra": "3", "ref": "S003", "titulo": "Supuesto 3 · Un mix de versiones del Tribunal", "desc": "15 preguntas · 30 minutos · Legislación a 21 de Septiembre de 2026 · Temas Variados"},
  {"seccion": "examenes", "archivo": "supuesto_EX03E", "letra": "3E", "ref": "E03E", "titulo": "Examen extraordinario · 12 de septiembre de 2026", "desc": "91 preguntas · 120 minutos · Cuestionario teórico (70) + supuesto práctico, con sus preguntas de reserva"}
  ];
  // <<< SUPUESTOS

  /* A partir de aquí no hace falta tocar nada: monta el menú. */
  function titulo(id) { return id.charAt(0).toUpperCase() + id.slice(1); }
  var datos = { secciones: [], examenes: [], lista: SUPUESTOS };
  var porId = {};
  SECCIONES.forEach(function (s) {
    var sec = { id: s.id, titulo: s.titulo, grupos: [] };
    (s.grupos || []).forEach(function (g) { sec.grupos.push({ id: g.id, titulo: g.titulo, items: [] }); });
    datos.secciones.push(sec); porId[s.id] = sec;
  });
  SUPUESTOS.forEach(function (it) {
    if (it.oculto) return;
    if (it.seccion === "examenes") { datos.examenes.push(it); return; }
    var sec = porId[it.seccion];
    if (!sec) { sec = { id: it.seccion, titulo: titulo(it.seccion), grupos: [] }; datos.secciones.push(sec); porId[it.seccion] = sec; }
    var g = null;
    sec.grupos.forEach(function (x) { if (x.id === it.grupo) g = x; });
    if (!g) { g = { id: it.grupo, titulo: titulo(it.grupo), items: [] }; sec.grupos.push(g); }
    g.items.push(it);
  });
  G.SUPUESTOS_DATOS = datos;
})(typeof window !== "undefined" ? window : self);

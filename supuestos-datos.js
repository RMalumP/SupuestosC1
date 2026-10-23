/* ════════════════════════════════════════════════════════════════
   LISTA DE SUPUESTOS DEL MENÚ
   El menú principal (index.html) se pinta a partir de este archivo.
   Estructura:  secciones → grupos (iniciales / avanzados) → supuestos,
   más la lista de «examenes».

   Para añadir un supuesto nuevo basta con añadir un bloque a su grupo:

     { "archivo": "supuesto_4", "letra": "4", "ref": "S004",
       "titulo": "Supuesto 4 · Título", "desc": "15 preguntas · 30 minutos · ..." }

   «archivo» es el nombre del .html de la carpeta supuestos/ sin extensión.
   El editor de Python (editor_supuestos.py) hace este alta al guardar.
════════════════════════════════════════════════════════════════ */
window.SUPUESTOS_DATOS = {
  "secciones": [
    {
      "id": "temas",
      "titulo": "Supuestos por temas",
      "grupos": [
        {
          "id": "iniciales",
          "titulo": "Iniciales",
          "items": [
            {
              "archivo": "supuesto_T2I",
              "letra": "T2I",
              "ref": "T2I",
              "titulo": "SUPUESTO TEMA 2 Inicial. Encuadramientos y mas encuadramietos",
              "desc": "25 preguntas · 45 minutos · Legislación a 10 de octubre de 2026 · Tema 2."
            }
          ]
        },
        {
          "id": "avanzados",
          "titulo": "Avanzados",
          "items": [
            {
              "archivo": "supuesto_T2",
              "letra": "T2",
              "ref": "T2",
              "titulo": "SUPUESTO TEMA 2. Encuadramientos y dolores de cabeza",
              "desc": "15 preguntas · 30 minutos · Legislación a 10 de octubre de 2026 · Tema 2."
            }
          ]
        }
      ]
    },
    {
      "id": "generales",
      "titulo": "Supuestos generales",
      "grupos": [
        {
          "id": "iniciales",
          "titulo": "Iniciales",
          "items": [
            {
              "archivo": "supuesto_1I",
              "letra": "I1",
              "ref": "S01I",
              "titulo": "SUPUESTO 1 Inicial. Conceptos básicos de temas 2 y 3",
              "desc": "15 preguntas · 30 minutos · Legislación a 27 de Septiembre de 2026 · Temas 2 y 3."
            },
            {
              "archivo": "supuesto_2I",
              "letra": "I2",
              "ref": "S02I",
              "titulo": "SUPUESTO 2 Inicial. Conceptos básicos de temas 4 y 7",
              "desc": "15 preguntas · 30 minutos · Legislación a 4 de octubre de 2026 · Temas 4 y 7."
            }
          ]
        },
        {
          "id": "avanzados",
          "titulo": "Avanzados",
          "items": [
            {
              "archivo": "supuesto_0",
              "letra": "0",
              "ref": "S000",
              "titulo": "Supuesto 0 · Hay que espabilar que el verano se os va a comer",
              "desc": "15 preguntas · 30 minutos · Legislación a 28 de agosto de 2026 · Temas 1 al 13"
            },
            {
              "archivo": "supuesto_1",
              "letra": "1",
              "ref": "S001",
              "titulo": "Supuesto 1 · Los otros Alantara",
              "desc": "15 preguntas · 30 minutos · Legislación a 4 de Septiembre de 2026 · Temas Variados"
            },
            {
              "archivo": "supuesto_2",
              "letra": "2",
              "ref": "S002",
              "titulo": "Supuesto 2 · Un repasito antes de empezar",
              "desc": "15 preguntas · 30 minutos · Legislación a 11 de Septiembre de 2026 · Temas Variados"
            },
            {
              "archivo": "supuesto_3",
              "letra": "3",
              "ref": "S003",
              "titulo": "Supuesto 3 · Un mix de versiones del Tribunal",
              "desc": "15 preguntas · 30 minutos · Legislación a 21 de Septiembre de 2026 · Temas Variados"
            }
          ]
        }
      ]
    }
  ],
  "examenes": [
    {
      "archivo": "supuesto_EX03E",
      "letra": "3E",
      "ref": "E03E",
      "titulo": "Examen extraordinario · 12 de septiembre de 2026",
      "desc": "91 preguntas · 120 minutos · Cuestionario teórico (70) + supuesto práctico, con sus preguntas de reserva"
    }
  ]
};

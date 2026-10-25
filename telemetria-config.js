/* ════════════════════════════════════════════════════════════════
   DATOS ANÓNIMOS DE INTENTOS INCOMPLETOS  ·  APAGADO POR DEFECTO
   ────────────────────────────────────────────────────────────────
   Hoy el único envío automático es el del detalle al CORREGIR. Esto añade,
   cuando se activa, una instantánea de los intentos que se DEJAN A MEDIAS
   (incluidos los de «corregir pregunta a pregunta» que no se llegan a
   corregir). No lleva nombre: solo un identificador aleatorio por navegador.

   PARA ACTIVARLO
     1. Crea un formulario de Google NUEVO (mejor aparte del actual) con
        preguntas de «respuesta corta» para cada dato de «campos» y, si quieres
        el detalle de las respuestas, una de «párrafo» para «respuestas».
     2. Copia la URL del formulario cambiando «viewform» por «formResponse».
     3. En cada campo, escribe el código «entry.123456» de su casilla
        (menú ⋮ del formulario → «Obtener enlace previamente rellenado»).
     4. Pon «activa: true». Los campos que dejes en "" no se envían.

   AVISO
     Mientras «activa» sea true, el texto de «aviso» aparece como última línea
     del menú principal (sin botones). Cámbialo si quieres.
════════════════════════════════════════════════════════════════ */
window.SUPC1_TELEMETRIA = {
    activa: false,
    url: "",                       // https://docs.google.com/forms/d/e/XXXX/formResponse
    minRespuestas: 1,              // solo se envía si hay al menos tantas preguntas respondidas
    aviso: "Esta web guarda de forma anónima (sin nombre) los resultados y los intentos que dejas a medias para mejorar los supuestos.",
    adminUrl: "",                  // enlace a tu panel privado (hoja o Apps Script); ver instrucciones
    campos: {
        examen: "",                // título del supuesto
        fecha: "",                 // dd/mm/aaaa hh:mm
        estado: "",                // «En curso / abandonado»
        modo: "",                  // «Normal» o «Pregunta a pregunta»
        intento: "",               // identificador del intento (agrupa varias instantáneas)
        anonimo: "",               // identificador aleatorio del navegador
        respondidas: "",
        total: "",
        aciertos: "",
        fallos: "",
        blancos: "",
        tiempoRestante: "",        // mm:ss
        respuestas: "",            // párrafo: una línea por pregunta, igual que el envío automático
        preguntas: []              // OPCIONAL: casillas «entry.…» una por pregunta (en vez de «respuestas»)
    }
};

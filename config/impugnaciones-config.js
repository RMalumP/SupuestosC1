/* ════════════════════════════════════════════════════════════════
   IMPUGNACIONES Y FORO
   ────────────────────────────────────────────────────────────────
   «Impugnar» manda la impugnación a un formulario de Google cuyas respuestas
   caen en la pestaña «Impugnaciones» de la hoja de resultados. La página
   «Impugnaciones» lee esa pestaña (y la del foro) sin servidor.

   FORMULARIO DE IMPUGNACIONES
     · «formUrl»: la URL del formulario con «formResponse» al final.
     · «campos»: el código «entry.…» de cada pregunta (ya puestos los de hoy).
       «id» es una pregunta nueva de respuesta corta (ver INSTRUCCIONES del PR);
       mientras esté en "" no se envía y no se podrá enlazar la respuesta con el foro.
   HOJA
     · Las columnas que rellenas tú a mano se buscan por el NOMBRE de su cabecera
       (primera fila de la pestaña): «cols».
   FORO
     · «foroUrl» y «foroCampos»: segundo formulario de Google (id del hilo, nombre,
       mensaje). Mientras «foroUrl» esté vacío el foro se ve pero no se puede escribir.
════════════════════════════════════════════════════════════════ */
window.SUPC1_IMPUG = {
    activa: true,
    formUrl: "https://docs.google.com/forms/d/e/1FAIpQLSe_8sRKj2HmSFfqikTDZIVLt33EhiwB-1wDnEdPB8qeCanTrQ/formResponse",
    campos: {
        publico: "entry.1757965325",
        nombre: "entry.628426951",
        supuesto: "entry.983942026",
        pregunta: "entry.1542587103",
        enunciado: "entry.1544444741",
        correcta: "entry.170349398",
        marcada: "entry.1901671757",
        texto: "entry.1263435838",
        id: ""                              // NUEVA pregunta «ID» (respuesta corta): pon aquí su entry.…
    },
    valorPublico: "Publico si",             // texto de la casilla «Publico»
    anonimo: "Anónimo",                     // nombre que se envía si se marca «Anónimo»

    sheetId: "19HZy6JZlljrvuEWdryuxWFqGHMf15qjsCVFe6OvLtLo",
    hojaImpugnaciones: "Impugnaciones",     // nombre exacto de la pestaña
    hojaForo: "foro inpugnaciones",         // nombre exacto de la pestaña del foro
    cols: {                                 // cabeceras (se ignoran mayúsculas y tildes)
        id: "ID",
        publico: "Publico",
        nombre: "Nombre",
        supuesto: "Supuesto",
        pregunta: "Pegunta",
        texto: "Impugnacion del usuario",
        respuesta: "Respuesta",             // tú la escribes: lo que se publica como contestación
        resuelta: "Resuelta",               // casilla tuya: solo las resueltas salen en la página
        cerrado: "Hilo cerrado",            // casilla tuya: cierra el foro de esa impugnación
        foroHilo: "Hilo", foroNombre: "Nombre", foroMensaje: "Mensaje", foroCerrado: "Cerrado",
        fecha: "Marca temporal"
    },

    foroUrl: "",                            // https://docs.google.com/forms/d/e/XXXX/formResponse
    foroCampos: { hilo: "", nombre: "", mensaje: "" }
};

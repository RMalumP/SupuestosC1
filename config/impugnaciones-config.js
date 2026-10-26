/* ════════════════════════════════════════════════════════════════
   IMPUGNACIONES Y FORO
   ────────────────────────────────────────────────────────────────
   «Impugnar» manda la impugnación a un formulario de Google cuyas respuestas
   caen en la pestaña «Impugnaciones» de la hoja de resultados. La página
   «Impugnaciones» lee esa pestaña (y la del foro) sin servidor.

   FORMULARIO DE IMPUGNACIONES
     · «formUrl»: la URL del formulario con «formResponse» al final.
     · «campos»: el código «entry.…» de cada pregunta (ya puestos los de hoy).
       «id» es una pregunta de respuesta corta que rellena la web sola; sin ella no
       se puede enlazar la respuesta con el foro.
   HOJA
     · Las columnas que rellenas tú a mano se buscan por el NOMBRE de su cabecera
       (primera fila de la pestaña): «cols».
   FORO (Issues de GitHub; guía en impugnaciones/LEEME.txt)
     · Cada impugnación resuelta es una «Issue» del repositorio (título «[ID] …»).
       La web las lee de la API pública de GitHub. Para escribir sin cuenta, el
       mensaje pasa por un Google Apps Script tuyo (foroScriptUrl) que lo publica.
     · Mientras «foroScriptUrl» esté vacío el foro se ve pero no se puede escribir.
════════════════════════════════════════════════════════════════ */
window.SUPC1_IMPUG = {
    activa: true,
    formUrl: "https://docs.google.com/forms/d/e/1FAIpQLSe_8sRKj2HmSFfqikTDZIVLt33EhiwB-1wDnEdPB8qeCanTrQ/formResponse",
    campos: {
        publico: "entry.746873418",
        nombre: "entry.628426951",
        supuesto: "entry.983942026",
        pregunta: "entry.1542587103",
        enunciado: "entry.1544444741",
        correcta: "entry.170349398",
        marcada: "entry.1901671757",
        texto: "entry.1263435838",
        id: "entry.1757965325"                // pregunta «ID» (respuesta corta) que rellena la web sola
    },
    valorPublico: "Publico si",             // texto de la casilla «Publico»
    anonimo: "Anónimo",                     // nombre que se envía si se marca «Anónimo»

    sheetId: "19HZy6JZlljrvuEWdryuxWFqGHMf15qjsCVFe6OvLtLo",
    hojaImpugnaciones: "Impugnaciones",     // nombre exacto de la pestaña
    cols: {                                 // cabeceras (se ignoran mayúsculas y tildes)
        id: "ID",
        publico: "Publico",
        nombre: "Nombre",
        supuesto: "Supuesto",
        pregunta: "Pegunta",
        correcta: "Correcta",               // las rellena la web (se busca la cabecera que contenga «correcta» / «marcada»)
        marcada: "Marcada",
        texto: "Impugnacion del usuario",
        respuesta: "Respuesta",             // tú la escribes: lo que se publica como contestación
        resuelta: "Resuelta",               // casilla tuya: solo las resueltas salen en la página
        cerrado: "Hilo cerrado",            // casilla tuya: cierra el foro de esa impugnación
        fecha: "Marca temporal"
    },

    repo: "RMalumP/SupuestosC1",            // repositorio donde viven las Issues del foro
    etiquetaForo: "foro-impugnaciones",     // etiqueta de esas Issues
    foroScriptUrl: "https://script.google.com/macros/s/AKfycbwMZJGu4jJtacD31KpN7pn2fcwgPFoFhmc92bwSl1XXSla3uwNpLu-LcGPU-s1O2Z9yjg/exec"
};

/* ═══════════════════════════════════════════
   CARGA DE LOS DATOS DEL SUPUESTO
   ───────────────────────────────────────────
   Lee el bloque JSON de arriba y lo convierte en las variables que
   usa el motor de la plantilla. Si el JSON tuviera un error de
   escritura, se avisa en pantalla en lugar de dejar la página en
   blanco.
═══════════════════════════════════════════ */
let DATOS_SUPUESTO;
try {
    DATOS_SUPUESTO = JSON.parse(document.getElementById('datos-supuesto').textContent);
} catch (err) {
    document.addEventListener('DOMContentLoaded', () => {
        document.body.innerHTML =
            '\u003cdiv style="max-width:760px;margin:60px auto;padding:24px;background:#fff;' +
            'border-left:6px solid #8b1a1a;font-family:Georgia,serif;color:#1a1a2e;">' +
            '\u003ch1 style="font-size:1.2rem;color:#8b1a1a;">Error en los datos del supuesto\u003c/h1>' +
            '\u003cp>El bloque JSON &lt;script id="datos-supuesto"&gt; tiene un error de formato ' +
            'y no se ha podido leer. Vuelve a guardar el archivo desde el editor de Python.\u003c/p>' +
            '\u003cpre style="white-space:pre-wrap;font-size:0.8rem;color:#4a5568;">' + err + '\u003c/pre>\u003c/div>';
    });
    throw err;
}

// Hasta siete opciones por pregunta (A…G)
const LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G'];
const MAX_OPCIONES = LETTERS.length;

/* ═══════════════════════════════════════════
   NORMALIZACIÓN DE LOS BLOQUES
   ───────────────────────────────────────────
   Rellena los valores que falten y reparte las preguntas en su
   bloque. Los archivos antiguos (sin "bloques") siguen funcionando:
   todas sus preguntas se meten en un único bloque de supuesto.
═══════════════════════════════════════════ */
function numeroSeguro(valor, porDefecto) {
    const n = parseFloat(String(valor === undefined || valor === null ? '' : valor).replace(',', '.'));
    return isNaN(n) ? porDefecto : n;
}

function normalizarBloques(datos) {
    const colorPorTipo = { supuesto: '#8fc4d9', test: '#e0ac4a' };
    let brutos = Array.isArray(datos.bloques) && datos.bloques.length ? datos.bloques : null;
    if (!brutos) brutos = [{ id: 'B1', tipo: 'supuesto', titulo: 'Supuesto práctico' }];

    const bloques = brutos.map((b, i) => {
        const tipo = (b.tipo === 'test') ? 'test' : 'supuesto';
        const id   = String(b.id || '').replace(/[^A-Za-z0-9_-]/g, '') || ('B' + (i + 1));
        return {
            id:         id,
            tipo:       tipo,
            titulo:     b.titulo || (tipo === 'test' ? 'Teoría' : 'Supuesto práctico'),
            color:      b.color  || colorPorTipo[tipo],
            modo:       (b.modo === 'cadena' || b.modo === 'individual')
                            ? b.modo
                            : (tipo === 'test' ? 'cadena' : 'individual'),
            // La cabecera de sección se pinta ENCIMA del enunciado (lo
            // natural en un supuesto). Poniéndolo a false baja hasta justo
            // delante de la primera pregunta, como en versiones anteriores.
            cabeceraSobreEnunciado: b.cabeceraSobreEnunciado !== false,
            // ¿Sale la casilla de este bloque en la opción «de una en una»
            // del panel ⚙? A false, el alumno no puede cambiar cómo se ven
            // las preguntas de este bloque: se quedan como diga "modo".
            opcionUnaEnUna: b.opcionUnaEnUna !== false,
            porIntento: Math.max(0, parseInt(b.porIntento, 10) || 0),
            envio:      b.envio || {},
            acierto:    numeroSeguro(b.acierto, 1),
            fallo:      Math.abs(numeroSeguro(b.fallo, 0)),
            blanco:     Math.abs(numeroSeguro(b.blanco, 0)),
            preguntas:  []
        };
    });

    const porId = new Map(bloques.map(b => [b.id, b]));
    (datos.preguntas || []).forEach((q, idx) => {
        // Nº de orden ORIGINAL de la pregunta dentro del supuesto, el del
        // editor y anterior a cualquier barajado. Se conserva pase lo que
        // pase para que el envío automático del detalle mande siempre cada
        // pregunta a su casilla fija del formulario (Pregunta 1 … 80),
        // aunque el intento salga aleatorizado o solo con parte de ellas.
        q.__ord = idx;
        const b = porId.get(String(q.bloqueId || '')) || bloques[0];
        q.bloqueId = b.id;
        // Bloques de hechos concretos de los que depende la pregunta
        // (hecho desencadenante). Solo se usan en el modo foco.
        q.factIds = Array.isArray(q.factIds)
                        ? q.factIds.map(x => String(x)).filter(Boolean)
                        : [];
        normalizarRespuestas(q);
        if (b.tipo === 'test') {          // la teoría no lleva enunciado
            q.statementId = null;
            q.factIds = [];
        }
        b.preguntas.push(q);
    });
    return bloques;
}

/* ═══════════════════════════════════════════
   NORMALIZACIÓN DE LAS RESPUESTAS DE UNA PREGUNTA
   ───────────────────────────────────────────
   Una pregunta puede tener de 2 a 7 opciones escritas y una o varias
   correctas. Los archivos antiguos traen exactamente cuatro opciones y
   la correcta en "c" (un número): se siguen leyendo igual.
     a[]         → las opciones escritas (se descartan las vacías)
     c           → la correcta, cuando solo hay una
     correctas[] → las correctas, cuando hay varias (respuesta múltiple)
     multiple    → true si hay que marcar todas las que procedan
     respuestas  → cuántas opciones salen en el examen para ESTA pregunta
                   (0 = lo que diga config.respuestas; y este, 0 = todas)
═══════════════════════════════════════════ */
function normalizarRespuestas(q) {
    q.a = (Array.isArray(q.a) ? q.a : [])
              .map(x => String(x === undefined || x === null ? '' : x))
              .filter(x => x.trim() !== '')
              .slice(0, MAX_OPCIONES);

    const dentro = i => Number.isInteger(i) && i >= 0 && i < q.a.length;

    let correctas = Array.isArray(q.correctas) ? q.correctas.map(x => parseInt(x, 10)) : [];
    correctas = correctas.filter(dentro);
    if (!correctas.length) {
        const c = parseInt(q.c, 10);
        correctas = dentro(c) ? [c] : (q.a.length ? [0] : []);
    }
    // Sin duplicados y en orden
    q.correctas = [...new Set(correctas)].sort((x, y) => x - y);
    q.c         = q.correctas.length ? q.correctas[0] : 0;
    q.multiple  = q.multiple === true && q.correctas.length > 0;
    q.respuestas = Math.max(0, Math.min(MAX_OPCIONES, parseInt(q.respuestas, 10) || 0));
    return q;
}

/* Qué opciones salen de esta pregunta en este intento.
   Si la pregunta tiene más opciones escritas de las que deben salir, se
   quedan siempre las correctas y se sortean los distractores que faltan:
   así se pueden escribir siete opciones y que cada intento enseñe cuatro
   distintas. Nunca se recorta por debajo de las correctas más un
   distractor. */
function opcionesDePregunta(q) {
    const correctas    = q.correctas;
    const distractores = q.a.map((_, i) => i).filter(i => !correctas.includes(i));

    let cuantas = q.respuestas || Math.round(numeroSeguro(EXAM_CONFIG.respuestas, 0)) || q.a.length;
    cuantas = Math.max(cuantas, correctas.length + (distractores.length ? 1 : 0));
    cuantas = Math.min(cuantas, q.a.length);

    const elegidos = correctas.concat(
        shuffle(distractores).slice(0, Math.max(0, cuantas - correctas.length)));
    return shuffle(elegidos).map(idx => ({ txt: q.a[idx], idx }));
}

/* ═══════════════════════════════════════════
   NORMALIZACIÓN DE LOS ENUNCIADOS
   ───────────────────────────────────────────
   Cada bloque de hechos recibe un identificador estable (H1, H2…) con el
   que las preguntas pueden vincularse a una parte concreta del enunciado
   (su hecho desencadenante) para el modo foco. Los archivos antiguos, que
   no lo traen, lo reciben aquí sin perder nada.
═══════════════════════════════════════════ */
function normalizarEnunciados(lista) {
    (lista || []).forEach(stmt => {
        const usados = new Set();
        (stmt.factBlocks || []).forEach((fb, i) => {
            let id = String(fb.id || '').replace(/[^A-Za-z0-9_-]/g, '');
            if (!id) id = 'H' + (i + 1);
            while (usados.has(id)) id += 'x';
            usados.add(id);
            fb.id = id;
        });
    });
    return lista || [];
}

const EXAM_CONFIG     = DATOS_SUPUESTO.config     || { titulo: '', referencia: '', ambito: '', minutos: 30 };
const STATEMENTS_BANK = normalizarEnunciados(DATOS_SUPUESTO.enunciados || []);
const BLOCKS_BANK     = normalizarBloques(DATOS_SUPUESTO);
const BLOCKS_BY_ID    = new Map(BLOCKS_BANK.map(b => [b.id, b]));
// Orden por defecto del examen: los bloques en su orden y, dentro de
// cada uno, sus preguntas en el orden en que están en el editor.
const QUESTIONS_BANK  = BLOCKS_BANK.reduce((acc, b) => acc.concat(b.preguntas), []);
// Porcentaje de puntuación a partir del cual el resultado es APTO
const APTO_PCT        = numeroSeguro(EXAM_CONFIG.aptoPorcentaje, 50);
// Qué botones se ven y cómo se llaman, y a dónde se envían los resultados
const INTERFAZ        = DATOS_SUPUESTO.interfaz || {};
const ENVIO           = DATOS_SUPUESTO.envio    || {};

/* ═══════════════════════════════════════════
   SEGUNDO FORMULARIO — DETALLE PREGUNTA A PREGUNTA
   ───────────────────────────────────────────
   COMPLEMENTO, no sustituto: el envío de arriba (botón 📤) se queda
   como está. Este otro sale solo, sin preguntar nada y sin salir de la
   página, en cuanto el alumno pulsa «Corregir» (o se le agota el
   tiempo), y manda:
       · el nombre del supuesto
       · la fecha y hora del envío
       · los aciertos y los fallos en bruto (sin baremo)
       · una casilla por pregunta, «Pregunta 1» … «Pregunta 80»
   Cada pregunta viaja SIEMPRE a la casilla de su número de orden
   ORIGINAL en el supuesto (el del editor), sin importar en qué bloque
   esté ni en qué orden haya salido en el intento.
   Las casillas son fijas; si algún día cambiara el formulario, se
   pueden sobrescribir desde el JSON con un apartado "envioDetalle".
═══════════════════════════════════════════ */
const ENVIO_DETALLE_DEFECTO = {
    url:      'https://docs.google.com/forms/d/e/1FAIpQLSfICCUGWcmcJ1zLFtphE1pictGOyfY9epNbSrHtEFfGvvK8HQ/formResponse',
    nombre:   'entry.315726614',   // Nombre supuesto
    tiempo:   'entry.1329722701',   // Tiempo (fecha y hora del envío)
    aciertos: 'entry.979170555',    // Nº de aciertos en bruto
    fallos:   'entry.1962238201',    // Nº de fallos en bruto
    preguntas: [
        'entry.712361381', 'entry.709874002', 'entry.661924675', 'entry.1030651222', 'entry.200283712', //  1- 5
        'entry.134789499', 'entry.966701265', 'entry.2110630525', 'entry.1056110206', 'entry.960222499', //  6-10
        'entry.1846963224', 'entry.900211285', 'entry.1003793269', 'entry.263573841', 'entry.784118366', // 11-15
        'entry.1588074600', 'entry.1770731044', 'entry.211278072', 'entry.1659967631', 'entry.1690155252', // 16-20
        'entry.2143039054', 'entry.1904113686', 'entry.1470800200', 'entry.1255018865', 'entry.1513500', // 21-25
        'entry.1854371083', 'entry.1620187954', 'entry.729113678', 'entry.293340307', 'entry.1724050220', // 26-30
        'entry.1062380832', 'entry.2085402594', 'entry.950414350', 'entry.602730095', 'entry.614220064', // 31-35
        'entry.1856632108', 'entry.909455125', 'entry.693661547', 'entry.632847159', 'entry.335441030', // 36-40
        'entry.1456618893', 'entry.852090648', 'entry.589626122', 'entry.183473563', 'entry.1217213161', // 41-45
        'entry.1968115194', 'entry.531136136', 'entry.1209534835', 'entry.1577734057', 'entry.312691398', // 46-50
        'entry.1116760340', 'entry.768501311', 'entry.694863628', 'entry.673940089', 'entry.1533606077', // 51-55
        'entry.253021395', 'entry.1326657452', 'entry.2041886464', 'entry.1051043932', 'entry.1809273037', // 56-60
        'entry.1108878147', 'entry.1471749573', 'entry.1082014329', 'entry.2112539399', 'entry.15417682', // 61-65
        'entry.2104298979', 'entry.949437792', 'entry.2071397813', 'entry.2001115340', 'entry.1445602013', // 66-70
        'entry.911131704', 'entry.1517320485', 'entry.548517073', 'entry.932772700', 'entry.1987322673', // 71-75
        'entry.529360562', 'entry.2050801750', 'entry.82935037', 'entry.48912348', 'entry.1553896761', // 76-80
        'entry.1016698177', 'entry.1584638604', 'entry.1327257853', 'entry.1726180779', 'entry.574614711', // 81-85
        'entry.2070952397', 'entry.1752221665', 'entry.203467465', 'entry.470537063', 'entry.1753285763', // 86-90
        'entry.1200176677', 'entry.1600805991', 'entry.1986998899', 'entry.1552574829', 'entry.290117084', // 91-95
        'entry.1429046308', 'entry.1510972535', 'entry.281414865', 'entry.673373891', 'entry.2071377334' // 96-100
    ]
};

const ENVIO_DETALLE = (() => {
    const dado = DATOS_SUPUESTO.envioDetalle || {};
    const cfg  = Object.assign({}, ENVIO_DETALLE_DEFECTO, dado);
    // La lista de casillas de pregunta solo se sustituye si viene con
    // contenido; si no, se mantiene la del formulario del proyecto.
    cfg.preguntas = (Array.isArray(dado.preguntas) && dado.preguntas.length)
                        ? dado.preguntas.map(x => String(x || '').trim())
                        : ENVIO_DETALLE_DEFECTO.preguntas.slice();
    return cfg;
})();
/* ═══════════ FIN DE LA ZONA EDITABLE ═══════════ */


/* ═══════════════════════════════════════════════════════════════════
   ██████  MOTOR DE LA PLANTILLA — no hace falta tocar nada de aquí  ██████
   ───────────────────────────────────────────────────────────────────
   A partir de aquí solo hay código que hace funcionar el examen
   (temporizador, barajado, corrección, impresión...). Para crear o
   editar un supuesto no hace falta leer ni modificar esta parte.
═══════════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════
   ESTADO DEL EXAMEN
═══════════════════════════════════════════ */

let questions          = [];
let examDurationSeconds = EXAM_CONFIG.minutos * 60; // ver EXAM_CONFIG, arriba
let timeLeft            = examDurationSeconds;
let current              = 0;
let userAns              = {};
let evaluated            = false;
let detalleEnviado       = false;    // El detalle pregunta a pregunta ya salió en este intento
let timerInt             = null;
let timerPaused          = false;
let audioCtx             = null;
let alerted10            = false;
let alerted5             = false;
let alerted5b            = false;
let alerted1             = false;
let instantFeedback      = false;    // Modo "corregir pregunta a pregunta"
// ⚙ "Ver las preguntas de una en una": una casilla por bloque.
//    { B1: true, B2: false } → B1 de una en una, B2 en cadena.
let unaEnUnaPorBloque    = {};
let modoFoco             = false;    // ⚙ "Modo foco" (dentro de la anterior)
let navPlegada           = false;    // cabecera plegada (solo el bloque actual)
let dedoEnMovimiento     = false;    // el dedo se ha desplazado: no es un toque
let ultimoScroll         = 0;        // instante del último desplazamiento del DEDO
let desplazamientoPropio = 0;        // instante del último movimiento que mandó el código
let panelAnterior        = null;     // enunciado de la pregunta anterior (para saber a dónde desplazar)

/* ═══════════════════════════════════════════
   AVISOS PARA LOS MÓDULOS (app-supuesto.js, app-uso.js…)
   ───────────────────────────────────────────
   El motor avisa de lo que pasa con eventos de document, y los módulos se
   cuelgan de ellos en lugar de vigilar con temporizadores o sustituir
   funciones del motor:
     supc1:antes-inicio  (detail.modo)  al empezar un intento, antes de montarlo
     supc1:inicio        (detail.modo)  con el intento ya montado
     supc1:respuesta     (detail.i)     al marcar o desmarcar una opción
     supc1:pregunta      (detail.i)     al cambiar de pregunta
     supc1:corregido                    al corregir o agotarse el tiempo
     supc1:salir                        justo antes de volver al menú
   SUPC1_MOTOR dice qué versión del motor hay (los módulos lo comprueban).
═══════════════════════════════════════════ */
window.SUPC1_MOTOR = 10;
function emitir(nombre, detalle) {
    try { document.dispatchEvent(new CustomEvent('supc1:' + nombre, { detail: detalle || {} })); }
    catch (e) { /* un módulo con fallos no debe parar el examen */ }
}

// Intento de práctica personal (solo falladas, marcadas…): lo decide app-supuesto.js.
// No se manda a los formularios.
function esPractica() {
    const S = window.SupC1;
    return !!(S && S.sup && typeof S.sup.esParcial === 'function' && S.sup.esParcial());
}

/* ═══════════════════════════════════════════
   VENTANAS PROPIAS (en vez de alert / confirm / prompt)
   ───────────────────────────────────────────
   dialogo({ titulo, texto, campo, botones }) → Promesa con el valor del
   botón pulsado (o el texto escrito, si hay campo). Esc o pulsar fuera =
   el botón con «cancelar: true» (o null). El foco se queda dentro.
═══════════════════════════════════════════ */
function dialogo(op) {
    return new Promise(resolve => {
        const previo  = document.activeElement;
        const fondo   = document.createElement('div');
        fondo.className = 'supc1-modal supc1-dialogo';
        const caja    = document.createElement('div');
        caja.className = 'supc1-modal-caja';
        caja.setAttribute('role', op.campo ? 'dialog' : 'alertdialog');
        caja.setAttribute('aria-modal', 'true');
        if (op.titulo) {
            const h = document.createElement('h3');
            h.id = 'dlg-titulo-' + Date.now();
            h.textContent = op.titulo;
            caja.appendChild(h);
            caja.setAttribute('aria-labelledby', h.id);
        }
        (Array.isArray(op.texto) ? op.texto : [op.texto]).filter(Boolean).forEach(t => {
            const p = document.createElement('p');
            p.textContent = t;
            caja.appendChild(p);
        });
        let campo = null;
        if (op.campo) {
            campo = document.createElement('input');
            campo.type = 'text';
            campo.className = 'supc1-dialogo-campo';
            campo.placeholder = op.campo.placeholder || '';
            campo.value = op.campo.valor || '';
            campo.setAttribute('aria-label', op.campo.etiqueta || op.titulo || '');
            caja.appendChild(campo);
        }
        const fila = document.createElement('div');
        fila.className = 'supc1-modal-botones';
        const botones = op.botones || [{ texto: 'Aceptar', valor: true, principal: true }];
        const cancelar = botones.find(b => b.cancelar);
        let terminado = false;
        const cerrar = valor => {
            if (terminado) return;
            terminado = true;
            fondo.remove();
            document.removeEventListener('keydown', teclas, true);
            if (previo && typeof previo.focus === 'function') { try { previo.focus({ preventScroll: true }); } catch (e) {} }
            resolve(valor);
        };
        const valorDe = b => (campo && !b.cancelar) ? campo.value : b.valor;
        botones.forEach(b => {
            const x = document.createElement('button');
            x.type = 'button';
            x.className = 'btn' + (b.principal ? ' btn-primary' : '');
            x.textContent = b.texto;
            x.addEventListener('click', () => cerrar(valorDe(b)));
            fila.appendChild(x);
        });
        caja.appendChild(fila);
        fondo.appendChild(caja);
        fondo.addEventListener('click', e => { if (e.target === fondo) cerrar(cancelar ? valorDe(cancelar) : null); });
        const teclas = e => {
            if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); cerrar(cancelar ? valorDe(cancelar) : null); }
            else if (e.key === 'Enter' && campo && e.target === campo) {
                e.preventDefault();
                const p = botones.find(b => b.principal) || botones[0];
                cerrar(valorDe(p));
            } else if (e.key === 'Tab') atraparFoco(e, caja);
        };
        document.addEventListener('keydown', teclas, true);
        document.body.appendChild(fondo);
        const primero = campo || fila.querySelector('.btn-primary') || fila.querySelector('button');
        if (primero) primero.focus({ preventScroll: true });
    });
}

// Pregunta sí/no con la ventana propia → Promesa<boolean>
function confirmar(titulo, texto, si, no) {
    return dialogo({ titulo, texto, botones: [
        { texto: no || 'Cancelar', valor: false, cancelar: true },
        { texto: si || 'Aceptar',  valor: true,  principal: true }] });
}

// Aviso con un solo botón → Promesa
function avisar(titulo, texto) {
    return dialogo({ titulo, texto, botones: [{ texto: 'Entendido', valor: true, principal: true, cancelar: true }] });
}

// Mantiene el foco de Tab dentro de una ventana abierta
function atraparFoco(e, caja) {
    const f = [...caja.querySelectorAll('button, [href], input, textarea, select, [tabindex]:not([tabindex="-1"])')]
                  .filter(x => !x.disabled && x.offsetParent !== null);
    if (!f.length) return;
    const primero = f[0], ultimo = f[f.length - 1];
    if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus(); }
    else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus(); }
    else if (!caja.contains(document.activeElement)) { e.preventDefault(); primero.focus(); }
}

/* ═══════════════════════════════════════════
   BLOQUES — utilidades
   ───────────────────────────────────────────
   Un bloque es una sección del examen (un supuesto práctico o una
   tanda de teoría tipo test). Cada bloque tiene su propio color, su
   forma de mostrarse (todas las preguntas seguidas o de una en una)
   y su propio baremo de puntuación.
═══════════════════════════════════════════ */
function getBlock(id) {
    return BLOCKS_BY_ID.get(id) || BLOCKS_BANK[0];
}

// "#8fc4d9" → "143,196,217" (para poder construir rgba() con transparencia)
function hexARgb(hex) {
    const limpio = String(hex || '').replace('#', '').trim();
    const largo  = limpio.length === 3 ? limpio.split('').map(c => c + c).join('') : limpio;
    const n      = parseInt(largo, 16);
    if (largo.length !== 6 || isNaN(n)) return '143,196,217';
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(',');
}

// Números con coma decimal y sin decimales inútiles: 1 → "1", 0.33 → "0,33"
function nUm(x) {
    const r = Math.round(x * 100) / 100;
    return String(r).replace('.', ',');
}

// Hoja de estilos que colorea cada bloque (casillas de navegación,
// cabecera de sección, marcador y corrección) con su propio color.
function inyectarEstilosBloques() {
    let hoja = document.getElementById('estilos-bloques');
    if (!hoja) {
        hoja = document.createElement('style');
        hoja.id = 'estilos-bloques';
        document.head.appendChild(hoja);
    }
    hoja.textContent = BLOCKS_BANK.map(b => {
        const rgb = hexARgb(b.color);
        return `
        .nav-box.blq-${b.id}:not(.answered):not(.nav-wrong) {
            border-color: rgba(${rgb},0.45); color: rgba(${rgb},0.95); background: rgba(${rgb},0.10);
        }
        .nav-box.blq-${b.id}:not(.answered):not(.nav-wrong):hover {
            border-color: ${b.color}; background: rgba(${rgb},0.22); color: #ffffff;
        }
        .nav-box.blq-${b.id}.active {
            background: ${b.color} !important; color: var(--navy) !important;
            border-color: ${b.color} !important; box-shadow: 0 0 12px rgba(${rgb},0.5);
        }
        .question-card.blq-${b.id}::before { background: linear-gradient(180deg, ${b.color}, var(--crimson)); }
        .question-card.blq-${b.id}.encadenada.active { box-shadow: 0 8px 32px var(--shadow), 0 0 0 2px ${b.color}; }
        .block-header.blq-${b.id} { border-left-color: ${b.color}; }
        .block-header.blq-${b.id} .bh-tipo { color: ${b.color}; border-color: rgba(${rgb},0.55); background: rgba(${rgb},0.10); }
        .score-bloques .sb-fila.blq-${b.id} { border-left-color: ${b.color}; }
        .score-bloques .sb-fila.blq-${b.id} .sb-nombre { color: ${b.color}; }
        .corr-bloque.blq-${b.id} { color: ${b.color}; border-bottom-color: rgba(${rgb},0.5); }`;
    }).join('\n');
}

/* ═══════════════════════════════════════════
   PALETA DE COLORES DE LA PÁGINA
   ───────────────────────────────────────────
   Los colores del apartado "tema" del bloque de datos sustituyen a
   las variables CSS de :root. Como todas las transparencias de la
   hoja de estilos se construyen con rgba(var(--x-rgb), …), cambiar
   un color aquí lo cambia en toda la página: fondos, bordes, textos
   y sombras incluidos.
═══════════════════════════════════════════ */
const TEMA_VARS = {
    fondo:        ['--navy',      '--navy-rgb'],
    barra:        ['--navy-mid',  null],
    acento:       ['--gold',      '--gold-rgb'],
    acentoClaro:  ['--gold-lt',   null],
    azulProfundo: ['--blue-deep', null],
    textoClaro:   ['--cream',     null],
    tarjeta:      ['--paper',     null],
    fondoHechos:  ['--parch',     null],
    texto:        ['--ink',       null],
    gris:         ['--slate',     null],
    rojo:         ['--crimson',   '--crimson-rgb'],
    verde:        ['--forest',    '--forest-rgb']
};

function aplicarTema() {
    const tema = (DATOS_SUPUESTO && DATOS_SUPUESTO.tema) || {};
    const raiz = document.documentElement;
    Object.keys(TEMA_VARS).forEach(clave => {
        const valor = tema[clave];
        if (!valor) return;
        const [variable, variableRgb] = TEMA_VARS[clave];
        raiz.style.setProperty(variable, valor);
        if (variableRgb) raiz.style.setProperty(variableRgb, hexARgb(valor));
    });
}

// La cabecera crece con el número de bloques (una fila por bloque): se
// publica su altura real en --nav-h para que el temporizador flotante
// quede siempre justo debajo y no la tape.
function medirCabecera() {
    const cab = document.getElementById('nav-header');
    if (!cab) return;
    document.documentElement.style.setProperty('--nav-h', cab.offsetHeight + 'px');
}
window.addEventListener('resize', medirCabecera);

/* En el móvil el reloj va DENTRO de la barra superior (flotando tapaba el
   texto de la pregunta); en pantallas anchas vuelve a su sitio de siempre,
   flotando bajo la barra. */
const MOVIL = window.matchMedia ? window.matchMedia('(max-width: 600px)') : { matches: false };
function colocarReloj() {
    const reloj = document.getElementById('timer');
    const cab   = document.getElementById('nav-header');
    if (!reloj || !cab) return;
    if (MOVIL.matches) {
        if (reloj.parentNode !== cab) cab.insertBefore(reloj, document.getElementById('fold-btn'));
    } else if (reloj.parentNode === cab) {
        cab.parentNode.insertBefore(reloj, cab.nextSibling);
    }
    medirCabecera();
}
if (MOVIL.addEventListener) MOVIL.addEventListener('change', colocarReloj);
else if (MOVIL.addListener) MOVIL.addListener(colocarReloj);

// Contador de la barra superior: pregunta actual / total y cuántas van respondidas
function actualizarContador() {
    const actual = document.getElementById('nav-actual');
    const resp   = document.getElementById('nav-respondidas');
    if (!actual || !questions.length) return;
    actual.textContent = (current + 1) + '/' + questions.length;
    const n = Object.keys(userAns).length;
    if (resp) resp.textContent = evaluated ? 'corregido' : n + ' resp.';
    const caja = document.getElementById('nav-contador');
    if (caja) caja.title = 'Pregunta ' + (current + 1) + ' de ' + questions.length + ' · ' + n + ' respondidas';
}

// Barra de casillas de un bloque que no cabe: degradado en el borde que indica que hay más
function marcarDesbordes() {
    document.querySelectorAll('.nav-row-boxes').forEach(c => {
        const sobra = c.scrollWidth > c.clientWidth + 1;
        c.classList.toggle('desborda-dcha', sobra && c.scrollLeft + c.clientWidth < c.scrollWidth - 2);
        c.classList.toggle('desborda-izda', sobra && c.scrollLeft > 2);
    });
}
window.addEventListener('resize', marcarDesbordes);
// Al cambiar el ancho cambian las casillas que caben en la línea:
// se vuelve a centrar la actual.
window.addEventListener('resize', () => centrarCasillaActiva(false));

/* Plegar la cabecera: deja a la vista solo la fila del bloque actual.
   Al cambiar de bloque (con Anterior/Siguiente o pulsando una casilla)
   la fila visible cambia sola. */
/* Con la cabecera plegada la fila del bloque actual es una sola línea que
   se desliza: esto la desplaza para que la casilla de la pregunta en la que
   estamos quede centrada (o lo más cerca posible del centro). Así, al pasar
   a otro bloque o avanzar hasta el número 60, la casilla activa nunca se
   queda fuera de la vista. */
function centrarCasillaActiva(suave = true) {
    if (!navPlegada) return;
    const casilla = document.getElementById('nav-' + current);
    if (!casilla) return;
    const carril = casilla.closest('.nav-row-boxes');
    if (!carril) return;
    // Si no hay nada que deslizar (el bloque cabe entero), no se toca nada.
    if (carril.scrollWidth <= carril.clientWidth + 1) return;
    const destino = casilla.offsetLeft - (carril.clientWidth - casilla.offsetWidth) / 2;
    const tope    = carril.scrollWidth - carril.clientWidth;
    const x       = Math.max(0, Math.min(destino, tope));
    if (typeof carril.scrollTo === 'function') {
        carril.scrollTo({ left: x, behavior: suave ? 'smooth' : 'auto' });
    } else {
        carril.scrollLeft = x;
    }
}

function togglePlegado() {
    navPlegada = !navPlegada;
    document.body.classList.toggle('nav-plegada', navPlegada);
    const btn = document.getElementById('fold-btn');
    if (btn) {
        btn.textContent = navPlegada ? '⌄' : '⌃';
        btn.title = navPlegada
            ? 'Desplegar: ver las casillas de todos los bloques'
            : 'Plegar: ver solo el bloque actual';
    }
    medirCabecera();
    // Al plegar, la fila pasa a una sola línea: hay que llevar la vista a la
    // casilla actual de inmediato (sin animación, que aún no se veía).
    centrarCasillaActiva(false);
}

// El botón de plegar solo tiene sentido con más de un bloque en pantalla.
// Además, cada intento arranca en el estado (plegada o desplegada) que se
// haya elegido en el editor.
function actualizarBotonPlegar() {
    const filas = document.querySelectorAll('.nav-row').length;
    const btn = document.getElementById('fold-btn');
    if (!btn) return;
    const procede = filas > 1 && interfazVisible('botonPlegar');
    btn.style.display = procede ? 'flex' : 'none';
    const deseada = procede && ajusteInterfaz('botonPlegar').plegado === true;
    if (navPlegada !== deseada) togglePlegado();
}

/* ¿Este bloque se ve con todas sus preguntas seguidas?
   Lo manda su casilla del panel ⚙: sin marcar, EN CADENA; marcada, de una
   en una. El "modo" que se elige en el editor es solo el estado con el que
   arranca esa casilla. */
function enCadena(bloque) {
    return !unaEnUnaPorBloque[bloque.id];
}

// Estado de arranque de las casillas: cada bloque empieza como diga SU
// modo en el editor («en cadena» → sin marcar; «de una en una» → marcada).
// No hay ningún interruptor general que lo pise: si un bloque está puesto
// en cadena, arranca en cadena.
function estrenarUnaEnUna() {
    unaEnUnaPorBloque = {};
    BLOCKS_BANK.forEach(b => {
        unaEnUnaPorBloque[b.id] = b.modo === 'individual';
    });
}

/* Monta en el panel ⚙ una casilla por cada bloque que salga en el intento
   (los bloques a los que el editor les haya quitado la casilla no salen).
   Con un solo bloque queda una sola casilla, como antes. */
function montarOpcionesUnaEnUna() {
    const caja = document.getElementById('una-por-bloque');
    if (!caja) return;
    caja.innerHTML = '';

    const presentes = new Set(questions.map(q => q.bloqueId));
    let alguna = false;
    BLOCKS_BANK.forEach(b => {
        if (!presentes.has(b.id) || b.opcionUnaEnUna === false) return;
        alguna = true;
        const fila = document.createElement('label');
        fila.innerHTML = `
            <input type="checkbox" id="una-${b.id}" ${unaEnUnaPorBloque[b.id] ? 'checked' : ''}>
            <span class="punto-bloque" style="background:${b.color}"></span>
            <span>${b.titulo}</span>`;
        fila.querySelector('input').onchange = (e) => toggleUnaEnUna(b.id, e.target.checked);
        caja.appendChild(fila);
    });

    // Si no queda ninguna casilla a la vista, sobra el rótulo del grupo.
    ponerVisible('row-una', alguna && interfazVisible('opcionUnaEnUna'), 'block');
    actualizarFilaFoco();
}

// Cabecera de sección que se pinta encima de las preguntas del bloque
function cabeceraBloque(bloque, cuantas) {
    const el = document.createElement('div');
    el.className = `block-header blq-${bloque.id}`;
    el.id = `bhdr-${bloque.id}`;
    el.dataset.bloque = bloque.id;
    const baremo = [
        `+${nUm(bloque.acierto)} por acierto`,
        bloque.fallo ? `−${nUm(bloque.fallo)} por fallo` : 'sin penalización por fallo',
        bloque.blanco ? `−${nUm(bloque.blanco)} en blanco` : ''
    ].filter(Boolean).join(' · ');
    el.innerHTML = `
        <span class="bh-tipo">${bloque.tipo === 'test' ? 'Teoría · test' : 'Supuesto práctico'}</span>
        <h3>${bloque.titulo}</h3>
        <div class="bh-datos">${cuantas} ${cuantas === 1 ? 'pregunta' : 'preguntas'}<br>${baremo}</div>`;
    return el;
}

/* ═══════════════════════════════════════════
   APLICAR EXAM_CONFIG AL DOM
   ───────────────────────────────────────────
   Rellena el título de la pestaña, la hoja de impresión y la
   cabecera institucional a partir de EXAM_CONFIG (ver ZONA
   EDITABLE). El nº de preguntas se recalcula cada vez que se
   (re)inicia el examen, para reflejar siempre las que hay
   realmente cargadas en pantalla.
═══════════════════════════════════════════ */
function applyExamConfig() {
    aplicarTema();
    estrenarUnaEnUna();
    aplicarInterfaz();

    // Encabezado: imagen y línea del organismo. Si se deja vacío el logo
    // (o el organismo), simplemente no se pinta.
    const logo = document.getElementById('inst-logo');
    if (logo) {
        if (EXAM_CONFIG.logo) {
            // Si no carga (sin conexión, o la imagen cambió de sitio) se oculta
            // en vez de dejar el icono de imagen rota con el texto alternativo
            logo.onerror = () => { logo.style.display = 'none'; };
            logo.src = EXAM_CONFIG.logo;
            logo.alt = EXAM_CONFIG.logoAlt || '';
            logo.style.display = '';
        } else {
            logo.removeAttribute('src');
            logo.style.display = 'none';
        }
    }
    const organismo = document.getElementById('inst-organismo');
    if (organismo) {
        organismo.textContent = EXAM_CONFIG.organismo || '';
        organismo.style.display = EXAM_CONFIG.organismo ? '' : 'none';
    }

    document.title = EXAM_CONFIG.titulo;
    document.getElementById('print-title-h1').textContent  = EXAM_CONFIG.titulo;
    document.getElementById('print-title-sub').textContent = `${EXAM_CONFIG.ambito} · Corrección con motivación legal completa`;
    document.getElementById('inst-title').textContent      = EXAM_CONFIG.titulo;
    document.getElementById('meta-minutos').textContent     = `${EXAM_CONFIG.minutos} MINUTOS`;
    document.getElementById('meta-legislacion').textContent = EXAM_CONFIG.ambito;
    document.getElementById('meta-referencia').textContent  = EXAM_CONFIG.referencia;
}

function updateQuestionCountPill() {
    document.getElementById('meta-preguntas').textContent = `${questions.length} PREGUNTAS`;
}

/* ═══════════════════════════════════════════
   BOTONES Y RÓTULOS CONFIGURABLES
   ───────────────────────────────────────────
   El apartado "interfaz" del bloque de datos decide qué botones se ven
   y con qué texto. Cada clave de configuración gobierna uno o varios
   elementos de la página (por ejemplo "btnImprimir" manda sobre el
   botón de la botonera y sobre su gemelo de la ventana de corrección).
═══════════════════════════════════════════ */
const BOTONES_INTERFAZ = {
    btnAnterior:      ['prev-btn'],
    btnSiguiente:     ['next-btn'],
    btnCorregir:      ['check-btn'],
    btnVerCorreccion: ['ov-corr-btn'],
    btnImprimir:      ['print-btn', 'ov-print-btn'],
    btnReintentar:    ['restart-btn', 'ov-restart-btn'],
    btnEnviar:        ['send-btn', 'ov-send-btn'],
    btnMenu:          ['home-btn-bottom', 'ov-home-btn']
};

// id de un elemento → clave de configuración que lo gobierna
const CLAVE_POR_BOTON = {};
Object.keys(BOTONES_INTERFAZ).forEach(clave => {
    BOTONES_INTERFAZ[clave].forEach(id => { CLAVE_POR_BOTON[id] = clave; });
});

function ajusteInterfaz(clave) {
    return (INTERFAZ && INTERFAZ[clave]) || {};
}

function interfazVisible(clave) {
    const ajuste = ajusteInterfaz(clave);
    if (ajuste.visible === false) return false;
    // Sin dirección de envío no tiene sentido ofrecer el botón de enviar
    if (clave === 'btnEnviar' && !(ENVIO && ENVIO.url)) return false;
    return true;
}

// ¿Puede verse este botón, según la configuración del supuesto?
function botonPermitido(id) {
    const clave = CLAVE_POR_BOTON[id];
    if (clave === 'btnReintentar' && !modosAleatoriosDisponibles().length) return false;
    return !clave || interfazVisible(clave);
}

// Muestra/oculta de golpe un grupo de botones por su id, respetando
// siempre lo que el supuesto haya configurado como oculto.
function setButtonsVisible(ids, visible) {
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        el.style.display = (visible && botonPermitido(id)) ? 'inline-flex' : 'none';
    });
}

// Escribe un texto en un elemento, si se ha configurado uno
function ponerTexto(id, texto) {
    const el = document.getElementById(id);
    if (el && texto) el.textContent = texto;
}

// Muestra u oculta un elemento según la configuración
function ponerVisible(id, visible, display) {
    const el = document.getElementById(id);
    if (el) el.style.display = visible ? (display || 'block') : 'none';
}

/* Aplica todo el apartado "interfaz": qué se ve y cómo se llama. */
function aplicarInterfaz() {
    // Cabecera
    const casa = ajusteInterfaz('botonCasa');
    ponerVisible('home-btn-top', casa.visible !== false, 'flex');
    const btnCasa = document.getElementById('home-btn-top');
    if (btnCasa && casa.titulo) {
        btnCasa.title = casa.titulo;
        btnCasa.setAttribute('aria-label', casa.titulo);
    }
    if (btnCasa && casa.texto) btnCasa.textContent = casa.texto;

    const config = ajusteInterfaz('botonConfig');
    ponerVisible('settings-toggle', config.visible !== false, 'flex');
    ponerTexto('settings-title', config.titulo);

    const plegar = ajusteInterfaz('botonPlegar');
    const btnPlegar = document.getElementById('fold-btn');
    if (btnPlegar && plegar.titulo) btnPlegar.title = plegar.titulo;

    // Opciones del panel ⚙
    [['opcionTiempo',   'row-tiempo',   'lbl-tiempo',    'block'],
     ['opcionCorregir', 'row-corregir', 'lbl-corregir',  'flex'],
     ['opcionUnaEnUna', 'row-una',      'lbl-una',       'block'],
     ['opcionFoco',     'row-foco',     'lbl-foco',      'flex'],
     ['opcionQtags',    'row-qtags',    'lbl-qtags',     'flex']].forEach(([clave, fila, rotulo, caja]) => {
        const ajuste = ajusteInterfaz(clave);
        ponerVisible(fila, ajuste.visible !== false, caja);
        ponerTexto(rotulo, ajuste.texto);
    });

    // Estado de partida de las opciones que se marcan y desmarcan
    [['opcionCorregir', 'instant-feedback-toggle',
      (v) => { instantFeedback = v; }],
     ['opcionFoco', 'foco-toggle',
      (v) => { modoFoco = v; }],
     ['opcionQtags', 'hide-qtags-toggle',
      (v) => { document.body.classList.toggle('hide-qtags', v); }]
    ].forEach(([clave, casilla, aplicar]) => {
        const activa = ajusteInterfaz(clave).activa === true;
        const el = document.getElementById(casilla);
        if (el) el.checked = activa;
        aplicar(activa);
    });

    // Las dos formas de repetir el intento (ventana del botón 🔀)
    [['opcionRepetirRespuestas', 'rnd-answers'],
     ['opcionRepetirOrden',      'rnd-order']].forEach(([clave, id]) => {
        const ajuste = ajusteInterfaz(clave);
        const boton  = document.getElementById(id);
        if (!boton) return;
        if (ajuste.texto) {
            const detalle = boton.querySelector('small');
            boton.innerHTML = ajuste.texto + (detalle ? '<br>' + detalle.outerHTML : '');
        }
        boton.style.display = interfazVisible(clave) ? '' : 'none';
    });

    // Botones: primero el texto, después la visibilidad
    Object.keys(BOTONES_INTERFAZ).forEach(clave => {
        const ajuste = ajusteInterfaz(clave);
        BOTONES_INTERFAZ[clave].forEach(id => {
            ponerTexto(id, ajuste.texto);
            if (!interfazVisible(clave)) ponerVisible(id, false);
        });
    });
    // Anterior/Siguiente están siempre a la vista salvo que se oculten
    ['btnAnterior', 'btnSiguiente'].forEach(clave => {
        BOTONES_INTERFAZ[clave].forEach(id => {
            ponerVisible(id, interfazVisible(clave), 'inline-flex');
        });
    });

    actualizarFilaFoco();
}

/* ═══════════════════════════════════════════
   SHUFFLE (Fisher-Yates)
═══════════════════════════════════════════ */
function shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

/* ═══════════════════════════════════════════
   ENUNCIADOS — render, panel incrustado y modo foco
═══════════════════════════════════════════ */
function getStatement(id) {
    return STATEMENTS_BANK.find(s => s.id === id) || null;
}

/* Pinta un enunciado entero o, en MODO FOCO, solo los bloques de hechos
   vinculados a la pregunta actual (opciones.factIds): así el alumno lee
   únicamente el hecho desencadenante del que depende esa pregunta. El
   botón «Ver enunciado completo» deshace el recorte. */
function renderStatementHTML(stmt, opciones) {
    if (!stmt) return '';
    const op     = opciones || {};
    const filtro = (op.factIds && op.factIds.length) ? new Set(op.factIds) : null;

    let visibles  = (stmt.factBlocks || []).filter(fb => !fb.hidden);
    let recortado = false;
    if (filtro) {
        const vinculados = visibles.filter(fb => filtro.has(fb.id));
        // Si el vínculo apunta a hechos que ya no existen (u ocultos), se
        // enseña el enunciado entero antes que dejar a la pregunta sin hechos.
        if (vinculados.length) { visibles = vinculados; recortado = true; }
    }

    const factsHtml = visibles.map(fb => {
        const cls   = fb.red ? 'fact-block red' : 'fact-block';
        const icon  = fb.red ? '⚠️' : '📋';
        const paras = (fb.paragraphs || []).map(p => `<p>${p}</p>`).join('');
        return `<div class="${cls}"><div class="fact-title">${icon} ${fb.title}</div>${paras}</div>`;
    }).join('');

    // En modo foco la cronología se calla: es contexto de todo el expediente.
    const tlItems = recortado ? [] : (stmt.timeline || []).filter(t => !t.hidden);
    const timelineHtml = tlItems.length
        ? `<div class="timeline">${tlItems.map(t =>
            `<div class="tl-item${t.red ? ' red-event' : ''}"><span class="tl-date">${t.date}</span>${t.text}</div>`
          ).join('')}</div>`
        : '';

    const avisoFoco = recortado
        ? `<div class="stmt-foco">🔎 MODO FOCO · solo se muestran los hechos de los que depende esta pregunta
             <button type="button" class="btn-foco" onclick="verEnunciadoCompleto(this)">Ver enunciado completo</button>
           </div>`
        : '';

    return `
        <section class="statement" id="stmt-${stmt.id}">
            <div class="statement-header">
                <div class="exp-number">${stmt.number || 'E'}</div>
                <div class="statement-title-block">
                    <h2>${stmt.title}</h2>
                    <span class="ref">REF: ${stmt.ref} · ÁMBITO: ${stmt.ambito}</span>
                </div>
            </div>
            ${avisoFoco}
            ${factsHtml}
            ${timelineHtml}
        </section>`;
}

/* Panel de enunciado incrustado en el hilo del examen. Se crea uno por
   cada grupo de preguntas que comparte enunciado, justo delante de la
   primera pregunta del grupo. */
function panelEnunciado(statementId, bloque, indicePrimera) {
    const el = document.createElement('div');
    el.className       = 'stmt-panel';
    el.id              = `stmtp-${indicePrimera}`;
    el.dataset.stmt    = statementId;
    el.dataset.bloque  = bloque.id;
    el.dataset.render  = 'full';
    el.innerHTML       = renderStatementHTML(getStatement(statementId));
    return el;
}

// Deja el enunciado entero a la vista pese al modo foco (botón del aviso).
function verEnunciadoCompleto(boton) {
    const panel = boton.closest('.stmt-panel');
    if (!panel) return;
    panel.dataset.render = 'full';
    panel.innerHTML = renderStatementHTML(getStatement(panel.dataset.stmt));
}

// Recorta (o restituye) el enunciado de la pregunta actual según el modo
// foco. Solo se repinta si hace falta, para no perder el desplazamiento.
function pintarPanelEnunciado(idPanel, pregunta, bloque) {
    const panel = document.getElementById(idPanel);
    if (!panel) return;
    const vinculos = pregunta.factIds || [];
    const foco  = modoFoco && bloque.tipo !== 'test' && vinculos.length > 0;
    const clave = foco ? ('foco:' + vinculos.join(',')) : 'full';
    if (panel.dataset.render === clave) return;
    panel.dataset.render = clave;
    panel.innerHTML = renderStatementHTML(getStatement(panel.dataset.stmt),
                                          foco ? { factIds: vinculos } : null);
}

// Agrupa un banco de preguntas por statementId, conservando el orden de
// aparición de cada grupo y el orden interno de sus preguntas. Las
// preguntas sin enunciado forman cada una su propio grupo de tamaño 1.
function groupByStatement(bank) {
    const groups = [];
    const indexByKey = new Map();
    bank.forEach((q, idx) => {
        const key = q.statementId ? q.statementId : `__solo_${idx}`;
        if (!indexByKey.has(key)) {
            indexByKey.set(key, groups.length);
            groups.push({ key, statementId: q.statementId || null, items: [] });
        }
        groups[indexByKey.get(key)].items.push(q);
    });
    return groups;
}

// Construye el listado final de preguntas para un intento según el modo:
//   'default' → orden proporcionado tal cual (bloques en su orden y, dentro
//               de cada bloque, sus preguntas en el orden del editor).
//   'answers' → reutiliza exactamente el mismo conjunto/orden que el
//               intento anterior (sourceBank); solo cambian las opciones.
//   'order'   → SALEN TODAS LAS PREGUNTAS, en otro orden. No se descarta
//               ninguna: la única diferencia con 'answers' es el orden.
//               El orden de los bloques NUNCA cambia: lo decide el editor,
//               así que si el supuesto va primero y la teoría después, así
//               se queda en todos los intentos.
//                 · bloque de teoría   → se barajan sus preguntas.
//                 · bloque de supuesto → se barajan los enunciados y, dentro
//                   de cada uno, sus preguntas (una pregunta nunca se
//                   separa de su enunciado, para no repetir los hechos).
//               Solo si el bloque tiene "porIntento" > 0 —que es una
//               decisión expresa del editor— se recorta a ese número.
function buildQuestionOrder(mode, sourceBank) {
    if (mode === 'answers') return [...sourceBank];

    const result = [];
    BLOCKS_BANK.forEach(b => {
        const banco = b.preguntas;
        if (!banco.length) return;

        if (mode !== 'order') {
            result.push(...banco);
            return;
        }

        let elegidas;
        if (b.tipo === 'test') {
            elegidas = shuffle(banco);
        } else {
            elegidas = [];
            shuffle(groupByStatement(banco)).forEach(g => {
                elegidas.push(...shuffle(g.items));
            });
        }
        if (b.porIntento > 0) elegidas = elegidas.slice(0, b.porIntento);
        result.push(...elegidas);
    });
    return result;
}

/* ═══════════════════════════════════════════
   PANEL DE CONFIGURACIÓN (⚙ temporizador + modo corrección)
═══════════════════════════════════════════ */
function toggleSettings() {
    const abierto = document.getElementById('settings-panel').classList.toggle('open');
    const boton   = document.getElementById('settings-toggle');
    boton.classList.toggle('open', abierto);
    boton.setAttribute('aria-expanded', abierto ? 'true' : 'false');
}

function closeSettings() {
    document.getElementById('settings-panel').classList.remove('open');
    const boton = document.getElementById('settings-toggle');
    boton.classList.remove('open');
    boton.setAttribute('aria-expanded', 'false');
}

// Cerrar el panel si se hace clic fuera de él
document.addEventListener('click', (e) => {
    const wrap = document.querySelector('.settings-wrap');
    if (wrap && !wrap.contains(e.target)) closeSettings();
    // La hoja «Más…» del móvil se cierra al tocar fuera (o al elegir una acción)
    if (document.body.classList.contains('mas-abierto') && !e.target.closest('#more-btn')) cerrarMasAcciones();
});

/* Esc cierra lo que esté abierto (panel ⚙, hoja «Más…», ventana de repetir) y
   el foco no se escapa de las ventanas abiertas. Si hay una ventana propia
   (dialogo) abierta, la atiende ella. */
document.addEventListener('keydown', (e) => {
    if (document.querySelector('.supc1-dialogo')) return;
    const modal   = document.getElementById('random-modal');
    const overlay = document.getElementById('overlay');
    if (e.key === 'Escape') {
        if (modal && modal.classList.contains('show')) { closeRandomModal(); return; }
        if (document.getElementById('settings-panel').classList.contains('open')) {
            closeSettings(); document.getElementById('settings-toggle').focus(); return;
        }
        if (document.body.classList.contains('mas-abierto')) { cerrarMasAcciones(); document.getElementById('more-btn').focus(); return; }
        if (overlay && overlay.classList.contains('show')) closeOverlay();
    } else if (e.key === 'Tab') {
        if (modal && modal.classList.contains('show')) atraparFoco(e, modal.querySelector('.modal-box'));
        else if (overlay && overlay.classList.contains('show')) atraparFoco(e, overlay);
    }
});

// Reloj como botón: Intro o espacio pausan y reanudan
document.addEventListener('keydown', (e) => {
    if (e.target && e.target.id === 'timer' && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        toggleTimerPause();
    }
});

/* ═══════════════════════════════════════════
   HOJA «MÁS…» (solo móvil, tras corregir)
   ───────────────────────────────────────────
   Tras corregir, en el móvil la barra de abajo deja solo Anterior, «Más…»
   y Siguiente; las demás acciones (imprimir, repetir, enviar, menú…) salen
   en una hoja desde abajo al pulsar «Más…». Son los mismos botones de
   siempre: solo cambia cómo se colocan (ver tema-supuesto.css).
═══════════════════════════════════════════ */
function toggleMasAcciones() {
    const abierto = document.body.classList.toggle('mas-abierto');
    document.getElementById('more-btn').setAttribute('aria-expanded', abierto ? 'true' : 'false');
}
function cerrarMasAcciones() {
    document.body.classList.remove('mas-abierto');
    const b = document.getElementById('more-btn');
    if (b) b.setAttribute('aria-expanded', 'false');
}

function formatTime(totalSeconds) {
    const m = Math.floor(totalSeconds / 60);
    const s = totalSeconds % 60;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

function parseTimeInput(str) {
    if (!str) return null;
    str = str.trim();
    if (str.includes(':')) {
        const [mm, ss] = str.split(':');
        const m = parseInt(mm, 10);
        const s = parseInt(ss, 10);
        if (isNaN(m) || isNaN(s)) return null;
        return m * 60 + s;
    }
    const m = parseFloat(str.replace(',', '.'));
    if (isNaN(m)) return null;
    return Math.round(m * 60);
}

function applyTimer() {
    const input = document.getElementById('time-input');
    const secs  = parseTimeInput(input.value);
    if (secs === null || secs <= 0) {
        avisar('Tiempo no válido', 'Introduce un tiempo válido, por ejemplo 30:00 (mm:ss) o 30 (minutos).')
            .then(() => input.focus());
        return;
    }
    examDurationSeconds = secs;
    timeLeft = secs;

    // Refrescar visualización del temporizador inmediatamente
    document.getElementById('timer-display').textContent = formatTime(timeLeft);
    colorReloj();

    // Evitar que se disparen avisos sonoros ya superados con el nuevo tiempo
    alerted10 = timeLeft <= 600;
    alerted5  = timeLeft <= 300;
    alerted5b = timeLeft <= 240;
    alerted1  = timeLeft <= 60;

    input.value = '';
    closeSettings();
}

function toggleInstantFeedback(checked) {
    instantFeedback = checked;
}

// Cambia cómo se ve UN bloque: marcado, sus preguntas salen de una en
// una; sin marcar, todas seguidas (en cadena). Cada bloque va por su
// cuenta, así que se puede tener el supuesto de una en una y la teoría
// encadenada, o al revés.
function toggleUnaEnUna(bloqueId, checked) {
    unaEnUnaPorBloque[bloqueId] = checked;
    actualizarFilaFoco();
    if (questions.length) jump(current);
}

/* MODO FOCO — cuelga de la opción anterior y solo actúa sobre los bloques
   que se estén viendo DE UNA EN UNA: cuando una pregunta está vinculada a
   hechos concretos del enunciado (factIds), se muestra únicamente esa
   parte. Las preguntas sin vínculo siguen viendo el enunciado entero, y un
   bloque en cadena no se recorta nunca. */
function toggleModoFoco(checked) {
    modoFoco = checked;
    if (questions.length) jump(current);
}

// La fila del modo foco se apaga (sin desaparecer) mientras no haya ningún
// bloque de supuesto viéndose de una en una: en cadena no puede aplicarse.
function actualizarFilaFoco() {
    const fila    = document.getElementById('row-foco');
    const casilla = document.getElementById('foco-toggle');
    if (!fila || !casilla) return;
    const presentes = new Set(questions.map(q => q.bloqueId));
    const aplicable = STATEMENTS_BANK.length > 0 && BLOCKS_BANK.some(
        b => b.tipo !== 'test' && presentes.has(b.id) && unaEnUnaPorBloque[b.id]);
    fila.classList.toggle('apagada', !aplicable);
    casilla.disabled = !aplicable;
}

function toggleHideQTags(checked) {
    document.body.classList.toggle('hide-qtags', checked);
}

function closeOverlay() {
    document.getElementById('overlay').classList.remove('show');

    // Si el overlay se cerró tras corregirse (p.ej. por tiempo agotado),
    // sincronizamos la página principal para que refleje el resultado
    // en lugar de quedarse "congelada" en el estado anterior.
    if (evaluated) {
        setButtonsVisible(['check-btn'], false);
        setButtonsVisible(['print-btn', 'restart-btn', 'send-btn', 'home-btn-bottom'], true);
        if (!document.getElementById('inline-score-banner')) {
            buildInlineScore();
        }
        jump(current);
    }
}

/* ═══════════════════════════════════════════
   AUDIO — Web Audio API
═══════════════════════════════════════════ */
function getAudioCtx() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    return audioCtx;
}

function playBeep(frequency = 880, duration = 0.3, type = 'sine', volume = 0.4) {
    try {
        const ctx = getAudioCtx();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.type = type;
        osc.frequency.setValueAtTime(frequency, ctx.currentTime);
        gain.gain.setValueAtTime(volume, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + duration);
    } catch(e) {}
}

function playAlert10() {
    // Un pitido grave y sostenido: aviso 10 min
    playBeep(440, 0.5, 'sine', 0.5);
    setTimeout(() => playBeep(550, 0.5, 'sine', 0.5), 600);
    speakText('Atención. Quedan diez minutos para finalizar el examen.');
}

function playAlert5() {
    // Doble pitido más urgente: aviso 5 min
    for (let i = 0; i < 2; i++) {
        setTimeout(() => { playBeep(660, 0.25, 'square', 0.5); }, i * 350);
        setTimeout(() => { playBeep(880, 0.25, 'square', 0.5); }, i * 350 + 150);
    }
    speakText('Atención. Quedan cinco minutos. Acelere el ritmo.');
}

function playAlert5b() {
    // Segundo doble pitido a los 5 min (refuerzo)
    setTimeout(() => { playBeep(880, 0.2, 'square', 0.6); }, 1500);
    setTimeout(() => { playBeep(660, 0.2, 'square', 0.6); }, 1800);
}

function playAlert1() {
    // Serie de pitidos breves y agudos
    for (let i = 0; i < 5; i++) {
        setTimeout(() => playBeep(1200, 0.15, 'square', 0.7), i * 200);
    }
}

function speakText(text) {
    try {
        if (!window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(text);
        u.lang = 'es-ES';
        u.rate = 0.92;
        u.pitch = 1.0;
        u.volume = 1.0;
        window.speechSynthesis.speak(u);
    } catch(e) {}
}

/* ═══════════════════════════════════════════
   INICIALIZACIÓN
═══════════════════════════════════════════ */
/* opcionesFijas (opcional): para cada pregunta, la lista de opciones (sus
   posiciones en el editor) en el orden en que deben salir. La usa «continuar
   un intento a medias» para devolver cada pregunta tal y como se dejó. */
function init(mode = 'default', sourceBank = null, opcionesFijas = null) {
    // Los módulos pueden ajustar el intento antes de montarlo (duración…)
    emitir('antes-inicio', { modo: mode });

    // Resetear estado
    questions  = buildQuestionOrder(mode, sourceBank || questions);
    if (!Object.keys(unaEnUnaPorBloque).length) estrenarUnaEnUna();
    timeLeft   = examDurationSeconds;
    current    = 0;
    userAns    = {};
    evaluated  = false;
    detalleEnviado = false;
    alerted10  = false;
    alerted5   = false;
    alerted5b  = false;
    alerted1   = false;
    timerPaused = false;
    panelAnterior = null;
    document.body.classList.remove('corregido');
    cerrarMasAcciones();

    // Limpiar DOM (solo las preguntas; el ⚙ de configuración se conserva)
    document.getElementById('nav-boxes').innerHTML  = '';
    document.getElementById('quiz-container').innerHTML = '';
    document.getElementById('overlay').classList.remove('show');
    document.getElementById('timer-display').textContent = formatTime(examDurationSeconds);
    document.getElementById('timer').removeAttribute('class');

    // El botón de corregir está siempre visible: se puede terminar el test desde la pregunta 1
    setButtonsVisible(['check-btn'], true);
    setButtonsVisible(['print-btn', 'restart-btn', 'send-btn', 'home-btn-bottom'], false);
    // Botones de envío listos otra vez (con el texto del editor, si lo hay)
    [['send-btn', '📤 Enviar Resultados'], ['ov-send-btn', '📤 Enviar Resultados']].forEach(([id, defecto]) => {
        const b = document.getElementById(id);
        if (!b) return;
        b.disabled = false;
        b.textContent = ajusteInterfaz('btnEnviar').texto || defecto;
    });
    document.getElementById('correction-panel').innerHTML = '';
    document.getElementById('score-banner').style.display = 'none';
    closeSettings();

    // Eliminar banner de puntuación si existe
    const old = document.getElementById('inline-score-banner');
    if (old) old.remove();

    updateQuestionCountPill();

    const nav     = document.getElementById('nav-boxes');
    const cont    = document.getElementById('quiz-container');

    inyectarEstilosBloques();

    // Cuántas preguntas de cada bloque han salido en este intento
    const cuantasPorBloque = {};
    questions.forEach(q => {
        cuantasPorBloque[q.bloqueId] = (cuantasPorBloque[q.bloqueId] || 0) + 1;
    });

    let bloqueAnterior    = null;
    let filaCasillas      = null;
    let stmtAnterior      = undefined;  // enunciado del grupo que se va montando
    let panelActual       = '';         // id del panel de ese grupo
    let cabeceraPendiente = null;       // cabecera que va DEBAJO del enunciado

    questions.forEach((q, i) => {
        const bloque = getBlock(q.bloqueId);

        // Cada bloque estrena su propia FILA en la cabecera: a la izquierda
        // su nombre (en su color) y a la derecha sus casillas numeradas.
        // Además se crea su cabecera de sección sobre las preguntas.
        if (bloque !== bloqueAnterior) {
            bloqueAnterior = bloque;
            stmtAnterior   = undefined;
            const primera = i;

            const fila = document.createElement('div');
            fila.className = 'nav-row';
            fila.dataset.bloque = bloque.id;

            const rotulo = document.createElement('span');
            rotulo.className = 'nav-group-label';
            rotulo.style.color = bloque.color;
            rotulo.textContent = bloque.titulo;
            rotulo.title = 'Ir al principio de: ' + bloque.titulo;
            rotulo.onclick = () => jump(primera);

            filaCasillas = document.createElement('div');
            filaCasillas.className = 'nav-row-boxes';
            filaCasillas.addEventListener('scroll', marcarDesbordes, { passive: true });

            fila.appendChild(rotulo);
            fila.appendChild(filaCasillas);
            nav.appendChild(fila);

            // La cabecera de sección va ENCIMA del enunciado (lo natural en
            // un supuesto: primero de qué sección se trata, luego los
            // hechos). Si el bloque lleva esa opción desactivada, espera y
            // se cuela justo delante de la primera pregunta.
            const cabecera = cabeceraBloque(bloque, cuantasPorBloque[bloque.id]);
            if (bloque.cabeceraSobreEnunciado) cont.appendChild(cabecera);
            else cabeceraPendiente = cabecera;
        }

        // Enunciado del grupo: se pinta UNA sola vez, delante de la primera
        // pregunta que lo comparte. Así, con las preguntas en cadena, el
        // documento sale como se lee un supuesto: enunciado 1 (completo) →
        // sus preguntas → enunciado 2 → sus preguntas…
        const sid = q.statementId || null;
        if (sid !== stmtAnterior) {
            stmtAnterior = sid;
            panelActual  = '';
            if (sid && getStatement(sid)) {
                const panel = panelEnunciado(sid, bloque, i);
                cont.appendChild(panel);
                panelActual = panel.id;
            }
        }
        if (cabeceraPendiente) {
            cont.appendChild(cabeceraPendiente);
            cabeceraPendiente = null;
        }

        // Botón nav, dentro de la fila de su bloque
        const box    = document.createElement('div');
        box.className = `nav-box blq-${bloque.id}`;
        box.id       = `nav-${i}`;
        box.innerText = i + 1;
        box.title     = bloque.titulo;
        box.setAttribute('role', 'button');
        box.setAttribute('tabindex', '0');
        box.setAttribute('aria-label', 'Ir a la pregunta ' + (i + 1));
        box.onclick  = () => jump(i);
        filaCasillas.appendChild(box);

        // Opciones: se eligen (si la pregunta tiene más de las que deben
        // salir) y se barajan en cada carga de la página, sea cual sea el
        // modo de intento, que solo decide qué preguntas salen y en qué orden.
        const fijas    = opcionesFijas && opcionesFijas[i];
        const opciones = Array.isArray(fijas) && fijas.length
                             ? fijas.map(idx => ({ txt: q.a[idx], idx }))
                             : opcionesDePregunta(q);

        // Dónde han quedado las correctas después de barajar
        const correctasNuevas = [];
        opciones.forEach((o, ni) => { if (q.correctas.includes(o.idx)) correctasNuevas.push(ni); });
        const multiple = q.multiple === true;

        let optHtml = '';
        opciones.forEach(({ txt }, ni) => {
            // Papel de radio / casilla para lectores de pantalla y teclado
            // (Intro o espacio la marcan: ver el teclado más abajo)
            optHtml += `
                <div class="option${multiple ? ' multi' : ''}" id="opt-${i}-${ni}" onclick="selectAnswer(${i}, ${ni})"
                     role="${multiple ? 'checkbox' : 'radio'}" tabindex="0" aria-checked="false">
                    <span class="opt-letter">${LETTERS[ni]}</span>
                    <span>${txt.replace(/^[A-G]\)\s*/, '')}</span>
                </div>`;
        });

        const card    = document.createElement('div');
        card.className = `question-card blq-${bloque.id}`;
        card.id       = `qcard-${i}`;
        card.dataset.correct  = correctasNuevas.join(',');
        // Traducción "opción tal y como se ve" → "opción tal y como está
        // escrita en el supuesto". Hace falta para poder mandar al
        // formulario el texto exacto que marcó el alumno.
        card.dataset.opciones = opciones.map(o => o.idx).join(',');
        card.dataset.multiple = multiple ? '1' : '';
        card.dataset.bloque   = bloque.id;
        card.dataset.panel    = panelActual;   // enunciado al que pertenece
        card.innerHTML = `
            <div class="q-header">
                <div class="q-num">${String(i+1).padStart(2,'0')}</div>
                <div class="q-body">
                    ${q.tag ? `<span class="q-tag">${q.tag}</span>` : ''}
                    <div class="q-text">${q.q}</div>
                </div>
            </div>
            ${multiple ? '<div class="multi-aviso">Marca todas las respuestas que procedan</div>' : ''}
            <div class="options-grid" role="${multiple ? 'group' : 'radiogroup'}" aria-label="Opciones de la pregunta ${i + 1}">${optHtml}</div>
            <div class="feedback" id="feed-${i}">
                <div class="feedback-header"><span>⚖️ MOTIVACIÓN LEGAL Y NORMATIVA APLICABLE</span></div>
                <div class="feedback-body">
                    <p>${q.law}</p>
                    ${q.tip ? `<div class="tip">${q.tip}</div>` : ''}
                </div>
            </div>`;
        cont.appendChild(card);
    });

    // Casillas «de una en una» del panel ⚙: una por cada bloque del intento
    montarOpcionesUnaEnUna();

    // Con un solo bloque, el rótulo del bloque en la barra sobra en el móvil
    document.body.classList.toggle('un-bloque', document.querySelectorAll('.nav-row').length === 1);

    // Con la cabecera ya montada: botón de plegado, reloj y altura para el reloj
    actualizarBotonPlegar();
    colocarReloj();
    medirCabecera();

    // Colocarse en la primera pregunta: jump() se encarga del enunciado,
    // de la cabecera de sección y de qué tarjetas se ven. Sin desplazar la
    // página: el examen empieza por su cabecera institucional.
    if (questions.length) jump(0, true);

    // Actualizar progress
    updateProgress();

    // Iniciar temporizador
    if (timerInt) clearInterval(timerInt);
    startTimer();

    // Fecha en print
    document.getElementById('print-fecha').textContent =
        'Fecha de realización: ' + new Date().toLocaleDateString('es-ES', { weekday:'long', year:'numeric', month:'long', day:'numeric' });

    actualizarContador();
    marcarDesbordes();
    emitir('inicio', { modo: mode });
}

/* ═══════════════════════════════════════════
   RESPUESTAS — consulta del estado
   ───────────────────────────────────────────
   Una pregunta puede tener una sola respuesta correcta o varias, así que
   tanto lo correcto como lo contestado se guardan SIEMPRE como lista de
   posiciones (ya barajadas). Sin responder = no hay entrada en userAns.
═══════════════════════════════════════════ */
function correctasDe(qIdx) {
    const card = document.getElementById(`qcard-${qIdx}`);
    const dato = card ? card.dataset.correct : '';
    return dato ? dato.split(',').map(Number) : [];
}

function contestadasDe(qIdx) {
    return userAns[qIdx] || [];
}

function sinResponder(qIdx) {
    return contestadasDe(qIdx).length === 0;
}

// Acierto = exactamente las correctas, ni una de más ni una de menos.
function esAcierto(qIdx) {
    const dadas     = contestadasDe(qIdx);
    const correctas = correctasDe(qIdx);
    return dadas.length === correctas.length && correctas.every(c => dadas.includes(c));
}

/* ═══════════════════════════════════════════
   SELECCIÓN DE RESPUESTA (permite desmarcar y modo corrección instantánea)
═══════════════════════════════════════════ */
function selectAnswer(qIdx, optIdx) {
    if (evaluated) return;

    // En pantallas táctiles, un "clic" que en realidad es un desplazamiento
    // (o que llega mientras la página aún se está moviendo) no debe cambiar
    // la respuesta: es el toque fantasma típico al bajar con el dedo.
    if (esTactil) {
        if (dedoEnMovimiento) { dedoEnMovimiento = false; return; }
        if (Date.now() - ultimoScroll < 300) return;
    }

    const card     = document.getElementById(`qcard-${qIdx}`);
    const multiple = card && card.dataset.multiple === '1';
    let dadas      = [...contestadasDe(qIdx)];

    if (dadas.includes(optIdx)) {
        // Volver a pulsar una opción ya marcada la desmarca
        dadas = dadas.filter(x => x !== optIdx);
    } else if (multiple) {
        dadas.push(optIdx);            // se pueden marcar varias
    } else {
        dadas = [optIdx];              // una sola: sustituye a la anterior
    }
    dadas.sort((x, y) => x - y);

    if (dadas.length) userAns[qIdx] = dadas;
    else delete userAns[qIdx];

    pintarRespuesta(qIdx);
    updateProgress();
    emitir('respuesta', { i: qIdx });

    // Con las preguntas en cadena se contesta bajando por la página, sin
    // tocar «Siguiente»: la casilla marcada en la cabecera se quedaba en la
    // primera del bloque por mucho que se avanzara. Al contestar una, esa
    // pasa a ser la pregunta actual (sin mover la página, que ya está donde
    // el alumno quiere), así que la cabecera señala siempre por dónde va.
    if (qIdx !== current) jump(qIdx, true);
}

// Marca en verde las correctas y en rojo las falladas de una pregunta.
function marcarSolucion(qIdx) {
    const dadas     = contestadasDe(qIdx);
    const correctas = correctasDe(qIdx);
    document.querySelectorAll(`#qcard-${qIdx} .option`).forEach((o, ni) => {
        o.classList.remove('correct', 'wrong');
        if (correctas.includes(ni))   o.classList.add('correct');
        else if (dadas.includes(ni))  o.classList.add('wrong');
    });
}

/* Repinta una pregunta según lo que lleve marcado. Con corrección
   pregunta a pregunta la solución no se enseña hasta que se han marcado
   tantas opciones como correctas tiene: si no, en una pregunta de
   respuesta múltiple se cantaría la solución con el primer clic. */
function pintarRespuesta(qIdx) {
    const dadas     = contestadasDe(qIdx);
    const correctas = correctasDe(qIdx);
    const navBox    = document.getElementById(`nav-${qIdx}`);
    const feed      = document.getElementById(`feed-${qIdx}`);

    document.querySelectorAll(`#qcard-${qIdx} .option`).forEach((o, ni) => {
        o.classList.remove('selected', 'correct', 'wrong');
        if (dadas.includes(ni)) o.classList.add('selected');
        o.setAttribute('aria-checked', dadas.includes(ni) ? 'true' : 'false');
    });
    navBox.classList.remove('nav-wrong', 'nav-correct');
    navBox.classList.toggle('answered', dadas.length > 0);

    if (!instantFeedback || dadas.length < correctas.length) {
        if (feed) feed.style.display = 'none';
        return;
    }
    marcarSolucion(qIdx);
    if (!esAcierto(qIdx)) navBox.classList.add('nav-wrong');
    if (feed) feed.style.display = 'block';
}

/* ═══════════════════════════════════════════
   TOQUES EN PANTALLAS TÁCTILES
   ───────────────────────────────────────────
   Al pasar de una pregunta a otra la página sube al principio; si el
   usuario baja con el dedo, el navegador puede convertir ese gesto en
   un "clic" sobre la opción que quede debajo y marcarla sin querer.
   Aquí se distingue un toque de un desplazamiento: si el dedo se mueve
   más de 10 píxeles, o la página se ha movido hace menos de 0,3 s, el
   toque no cuenta como respuesta.
═══════════════════════════════════════════ */
const esTactil = (typeof window !== 'undefined') &&
                 ('ontouchstart' in window || (navigator.maxTouchPoints || 0) > 0);
let inicioToqueX = 0, inicioToqueY = 0;

document.addEventListener('touchstart', (e) => {
    dedoEnMovimiento = false;
    const t = e.touches && e.touches[0];
    if (t) { inicioToqueX = t.clientX; inicioToqueY = t.clientY; }
}, { passive: true });

document.addEventListener('touchmove', (e) => {
    const t = e.touches && e.touches[0];
    if (!t) return;
    if (Math.abs(t.clientX - inicioToqueX) > 10 || Math.abs(t.clientY - inicioToqueY) > 10) {
        dedoEnMovimiento = true;
    }
}, { passive: true });

/* Solo cuenta el desplazamiento que hace el DEDO. Cuando la página se
   mueve porque se lo ha mandado el código (al cambiar de pregunta, que va
   con animación y puede durar bastante si el salto es largo), esos avisos
   de «scroll» no deben armar el guardia: si lo hacían, el toque con el que
   se contestaba nada más parar la página se perdía sin dejar rastro, y la
   pregunta se quedaba en blanco. Pasaba sobre todo en la primera pregunta
   de una cadena, a la que se llega tras recorrer todo el enunciado. */
window.addEventListener('scroll', () => {
    if (Date.now() - desplazamientoPropio < 1500) return;
    ultimoScroll = Date.now();
}, { passive: true });

/* ═══════════════════════════════════════════
   NAVEGACIÓN
═══════════════════════════════════════════ */
/* Lleva el examen a la pregunta i. Con "sinDesplazar" se actualiza lo que
   se ve pero la página no se mueve (al arrancar y al corregir, para no
   saltarse la cabecera ni el marcador). */
function jump(i, sinDesplazar) {
    current = i;
    const pregunta = questions[i];
    const bloque   = getBlock(pregunta.bloqueId);
    const cadena   = enCadena(bloque);

    // Cabecera de sección: solo la del bloque en el que estamos
    document.querySelectorAll('.block-header').forEach(h => {
        h.classList.toggle('visible', h.dataset.bloque === bloque.id);
    });

    // Fila de casillas del bloque actual (la única visible si está plegada)
    document.querySelectorAll('.nav-row').forEach(f => {
        f.classList.toggle('fila-actual', f.dataset.bloque === bloque.id);
    });
    if (navPlegada) {
        medirCabecera();
        // La fila visible es de una sola línea: se desliza sola hasta la
        // casilla de esta pregunta (imprescindible al cambiar de bloque).
        centrarCasillaActiva();
    }

    // Tarjetas: en cadena se ven todas las del bloque; si no, solo la actual.
    document.querySelectorAll('.question-card').forEach((c, idx) => {
        const suya = cadena ? (questions[idx].bloqueId === bloque.id) : (idx === i);
        c.classList.toggle('visible', suya);
        c.classList.toggle('encadenada', cadena && suya);
        c.classList.toggle('active', idx === i);
    });

    // Enunciados: en cadena se ven todos los del bloque (cada uno delante de
    // sus preguntas); de una en una, solo el de la pregunta actual.
    const tarjeta = document.getElementById(`qcard-${i}`);
    const idPanel = (tarjeta && tarjeta.dataset.panel) || '';
    document.querySelectorAll('.stmt-panel').forEach(p => {
        const suyo = cadena ? (p.dataset.bloque === bloque.id) : (p.id === idPanel);
        p.classList.toggle('visible', suyo);
        // Con las preguntas encadenadas el enunciado va siempre entero: no
        // hay una única pregunta a la que recortarlo.
        if (suyo && cadena && p.dataset.render !== 'full') {
            p.dataset.render = 'full';
            p.innerHTML = renderStatementHTML(getStatement(p.dataset.stmt));
        }
    });
    if (!cadena && idPanel) pintarPanelEnunciado(idPanel, pregunta, bloque);

    document.querySelectorAll('.nav-box').forEach(b => b.classList.remove('active'));
    const navBox = document.getElementById(`nav-${i}`);
    navBox.classList.add('active');
    navBox.setAttribute('aria-current', 'step');
    document.querySelectorAll('.nav-box[aria-current]').forEach(b => { if (b !== navBox) b.removeAttribute('aria-current'); });
    actualizarContador();
    emitir('pregunta', { i });

    // ¿Ha cambiado el enunciado respecto a la pregunta anterior? (para saber
    // si hay que llevar la vista a los hechos o directamente a la pregunta)
    const enunciadoNuevo = !idPanel || idPanel !== panelAnterior ||
                           (modoFoco && bloque.tipo !== 'test' && (pregunta.factIds || []).length > 0);
    panelAnterior = idPanel;

    if (sinDesplazar) return;

    // A partir de aquí la página se mueve porque lo manda el código: se deja
    // constancia para que el guardia táctil no confunda esa animación con un
    // desplazamiento del dedo y se trague la respuesta siguiente.
    desplazamientoPropio = Date.now();

    // En móvil la fila de preguntas se desplaza en horizontal: al cambiar
    // de pregunta la casilla activa siempre vuelve a quedar visible.
    navBox.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });

    if (cadena) {
        // Con las preguntas apiladas no se sube al principio: se lleva la
        // pregunta elegida justo debajo de la cabecera fija. Y si es la
        // PRIMERA pregunta de un enunciado, se sube hasta el enunciado: al
        // llegar a un caso práctico lo primero que hay que leer son los
        // hechos, no la pregunta.
        const panelGrupo = (idPanel === `stmtp-${i}`) ? document.getElementById(idPanel) : null;
        const destino    = panelGrupo || document.getElementById(`qcard-${i}`);
        const y          = destino.getBoundingClientRect().top + window.scrollY - 90;
        window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });
    } else {
        // De una en una: antes se subía al principio de la página y había que
        // volver a pasar la cabecera del supuesto y la del bloque en cada
        // pregunta. Ahora se lleva la vista a los hechos si el enunciado es
        // otro (o en modo foco, que los recorta) y, si es el mismo, directamente
        // a la pregunta, justo debajo de la barra superior.
        const cab     = document.getElementById('nav-header');
        const margen  = (cab ? cab.offsetHeight : 64) + 12;
        const panel   = idPanel ? document.getElementById(idPanel) : null;
        const destino = (enunciadoNuevo && panel) ? panel : document.getElementById(`qcard-${i}`);
        const y       = destino ? destino.getBoundingClientRect().top + window.scrollY - margen : 0;
        window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });
    }
}
function move(d) { const n = current + d; if (n >= 0 && n < questions.length) jump(n); }

/* ═══════════════════════════════════════════
   TEMPORIZADOR
═══════════════════════════════════════════ */
function startTimer() {
    timerInt = setInterval(() => {
        if (timerPaused) return;

        timeLeft--;
        document.getElementById('timer-display').textContent = formatTime(Math.max(0, timeLeft));

        // El color del reloj depende solo del tiempo que queda (antes se
        // borraba en el tic siguiente y el aviso duraba un segundo)
        colorReloj();

        if (timeLeft <= 60 && !alerted1) {
            alerted1 = true;
            playAlert1();
            speakText('Queda menos de un minuto. El tiempo se acaba.');
        } else if (timeLeft <= 240 && !alerted5b && alerted5) {
            // Refuerzo del aviso de 5 minutos, ya separado del primero (antes
            // sonaba un segundo después y se mezclaba con la voz)
            alerted5b = true;
            playAlert5b();
        } else if (timeLeft <= 300 && !alerted5) {
            alerted5 = true;
            playAlert5();
        } else if (timeLeft <= 600 && !alerted10) {
            alerted10 = true;
            playAlert10();
        }

        if (timeLeft <= 0) {
            clearInterval(timerInt);
            triggerTimeUp();
        }
    }, 1000);
}

// Color del reloj según lo que queda: ámbar (10 min), rojo (5 min), alarma (1 min)
function colorReloj() {
    const el = document.getElementById('timer');
    if (!el) return;
    el.classList.toggle('warn1',  timeLeft <= 60);
    el.classList.toggle('warn5',  timeLeft > 60  && timeLeft <= 300);
    el.classList.toggle('warn10', timeLeft > 300 && timeLeft <= 600);
}

function toggleTimerPause() {
    if (evaluated) return; // no tiene sentido pausar tras corregir o con el tiempo agotado
    timerPaused = !timerPaused;
    document.getElementById('timer').classList.toggle('paused', timerPaused);
}

function triggerTimeUp() {
    // Calcular resultado aunque no haya corregido
    evaluated = true;
    document.body.classList.add('corregido');
    // Se cierra lo que estuviera abierto a medias
    closeSettings();
    closeRandomModal();
    document.querySelectorAll('.supc1-dialogo').forEach(d => d.remove());
    const overlay = document.getElementById('overlay');
    overlay.classList.add('show');
    overlay.scrollTop = 0;
    // Marcador y panel de corrección (showCorrectionPanel pinta el marcador)
    showCorrectionPanel();
    // Botón de envío de resultados, si el supuesto lo permite
    setButtonsVisible(['send-btn', 'ov-send-btn'], true);
    actualizarContador();
    const cerrar = document.getElementById('overlay-close');
    if (cerrar) cerrar.focus({ preventScroll: true });

    // Envío automático del detalle pregunta a pregunta (segundo formulario)
    enviarDetalleCorreccion();
    emitir('corregido', { porTiempo: true });
}

/* ═══════════════════════════════════════════
   BARRA DE PROGRESO
═══════════════════════════════════════════ */
function updateProgress() {
    const pct = (Object.keys(userAns).length / questions.length) * 100;
    document.getElementById('progress-fill').style.width = pct + '%';
    actualizarContador();
}

/* ═══════════════════════════════════════════
   COLOR DE LAS CASILLAS DE NAVEGACIÓN TRAS CORREGIR
   ───────────────────────────────────────────
   Acierto → verde ("answered"). Fallo → rojo ("nav-wrong").
   Sin responder → sin clase, aspecto neutro ("en blanco").
═══════════════════════════════════════════ */
function updateNavResultColors() {
    questions.forEach((q, i) => {
        const navBox = document.getElementById(`nav-${i}`);
        navBox.classList.remove('answered', 'nav-wrong');
        if (sinResponder(i)) return;
        navBox.classList.add(esAcierto(i) ? 'answered' : 'nav-wrong');
    });
}

/* ═══════════════════════════════════════════
   CORRECCIÓN DEL EXAMEN (desde botón principal)
   Puede lanzarse en cualquier momento, incluso desde la
   pregunta 1 y sin haber respondido todas las preguntas.
═══════════════════════════════════════════ */
/* Con preguntas sin responder se pide confirmación en una ventana propia.
   sinPreguntar = true corrige directamente (lo usan las pruebas automáticas). */
async function evaluateExam(sinPreguntar) {
    if (evaluated) return;

    const answeredCount = Object.keys(userAns).length;
    if (answeredCount < questions.length && sinPreguntar !== true) {
        const proceed = await confirmar('¿Corregir el examen?',
            [`Has respondido ${answeredCount} de ${questions.length} preguntas.`,
             'Las preguntas sin responder contarán como no acertadas.'],
            'Corregir', 'Seguir respondiendo');
        if (!proceed || evaluated) return;
    }

    evaluated = true;
    document.body.classList.add('corregido');
    clearInterval(timerInt);

    // Marcar opciones correctas / erróneas en las tarjetas visibles
    questions.forEach((q, i) => {
        document.getElementById(`feed-${i}`).style.display = 'block';
        marcarSolucion(i);
    });
    updateNavResultColors();

    // Ocultar botón corregir, mostrar imprimir, repetir, enviar y menú
    setButtonsVisible(['check-btn'], false);
    setButtonsVisible(['print-btn', 'restart-btn', 'send-btn', 'home-btn-bottom'], true);

    // Banner de resultado inline
    buildInlineScore();

    // Envío automático del detalle pregunta a pregunta (segundo formulario)
    enviarDetalleCorreccion();

    // Se vuelve a la primera pregunta y se sube al principio, para que lo
    // primero que se vea sea el marcador.
    jump(0, true);
    actualizarContador();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    emitir('corregido', { porTiempo: false });
}

/* ═══════════════════════════════════════════
   SCORE — cálculo
═══════════════════════════════════════════ */
function calcScore() {
    let score = 0;
    questions.forEach((q, i) => { if (esAcierto(i)) score++; });
    return score;
}

/* Recuento completo, tratando cada bloque como una entidad separada:
   cada uno suma y descuenta según su propio baremo (acierto / fallo /
   en blanco) y se totaliza al final. */
function calcResultados() {
    const mapa  = new Map();
    const orden = [];

    questions.forEach((q, i) => {
        const b = getBlock(q.bloqueId);
        if (!mapa.has(b.id)) {
            mapa.set(b.id, { bloque: b, total: 0, aciertos: 0, fallos: 0,
                             blancos: 0, puntos: 0, max: 0 });
            orden.push(b.id);
        }
        const r = mapa.get(b.id);

        r.total++;
        r.max += b.acierto;
        if (sinResponder(i))   { r.blancos++;  r.puntos -= b.blanco; }
        else if (esAcierto(i)) { r.aciertos++; r.puntos += b.acierto; }
        else                   { r.fallos++;   r.puntos -= b.fallo;  }
    });

    const bloques = orden.map(id => mapa.get(id));
    const tot = { total: 0, aciertos: 0, fallos: 0, blancos: 0, puntos: 0, max: 0 };
    bloques.forEach(r => {
        ['total', 'aciertos', 'fallos', 'blancos', 'puntos', 'max'].forEach(k => { tot[k] += r[k]; });
    });
    tot.bloques = bloques;
    tot.pct = tot.max > 0 ? Math.max(0, (tot.puntos / tot.max) * 100) : 0;
    tot.apto = tot.pct >= APTO_PCT;
    return tot;
}

// Desglose por bloques (solo tiene sentido si hay más de uno en el intento)
function desgloseBloquesHTML(res) {
    if (res.bloques.length < 2) return '';
    return `<div class="score-bloques">${res.bloques.map(r => `
        <div class="sb-fila blq-${r.bloque.id}">
            <span class="sb-nombre">${r.bloque.titulo}</span>
            <span class="sb-detalle">${r.aciertos} ✓ · ${r.fallos} ✗ · ${r.blancos} —</span>
            <span class="sb-puntos">${nUm(r.puntos)} / ${nUm(r.max)}</span>
        </div>`).join('')}</div>`;
}

function lineaRecuento(res) {
    return `${nUm(res.pct)}% · ${res.aciertos} ACIERTOS · ${res.fallos} FALLOS · ${res.blancos} EN BLANCO`;
}

function buildScoreBanner() {
    const res     = calcResultados();
    const emoji   = res.aciertos === res.total ? '🏆' : res.apto ? '✅' : '📚';
    const verdict = res.aciertos === res.total ? '¡Expediente magistralmente resuelto!'
                  : res.apto ? 'APTO — Buen dominio normativo'
                             : 'NO APTO — Revise cada motivación legal';

    const banner  = document.getElementById('score-banner');
    banner.style.display = 'block';
    banner.innerHTML = `
        <div class="ml-emoji" aria-hidden="true">${emoji}</div>
        <div class="score-big">${nUm(res.puntos)} / ${nUm(res.max)}</div>
        <div class="score-lbl">${lineaRecuento(res)}</div>
        <div class="score-verdict ${res.apto ? 'apto':'no-apto'}">${verdict}</div>
        ${desgloseBloquesHTML(res)}`;
}

function buildInlineScore() {
    const res   = calcResultados();
    const emoji = res.aciertos === res.total ? '🏆' : res.apto ? '✅' : '📚';

    // El aspecto está en base-supuesto.css (.marcador-linea)
    const banner  = document.createElement('div');
    banner.id     = 'inline-score-banner';
    banner.className = 'marcador-linea';
    banner.setAttribute('role', 'status');
    banner.innerHTML = `
        <div class="ml-emoji" aria-hidden="true">${emoji}</div>
        <div class="ml-puntos">${nUm(res.puntos)} / ${nUm(res.max)}</div>
        <div class="ml-recuento">${lineaRecuento(res)}</div>
        <div class="ml-veredicto ${res.apto ? 'apto' : 'no-apto'}">${res.apto?'APTO — Buen dominio normativo':'NO APTO — Revise la motivación de cada respuesta'}</div>
        ${desgloseBloquesHTML(res)}`;

    // Los enunciados viven dentro del hilo de preguntas, así que el
    // marcador se coloca antes de la barra de progreso: encabeza todo el
    // examen y no se cuela entre un enunciado y sus preguntas.
    const container = document.querySelector('.container');
    const progress  = container.querySelector('.progress-bar-wrap');
    container.insertBefore(banner, progress || document.getElementById('quiz-container')
                                            || container.firstChild);
}

/* ═══════════════════════════════════════════
   PANEL CORRECCIÓN COMPLETA (overlay)
═══════════════════════════════════════════ */
function showCorrectionPanel() {
    buildScoreBanner();
    updateNavResultColors();

    const panel  = document.getElementById('correction-panel');
    const resumenBloques = new Map(calcResultados().bloques.map(r => [r.bloque.id, r]));
    let html = '';
    let bloqueAnterior = null;

    questions.forEach((q, i) => {
        // Separador cada vez que empieza un bloque distinto
        if (q.bloqueId !== bloqueAnterior) {
            bloqueAnterior = q.bloqueId;
            const b = getBlock(q.bloqueId);
            const r = resumenBloques.get(b.id);
            html += `<div class="corr-bloque blq-${b.id}">${b.titulo} — ${r.aciertos} ✓ · ${r.fallos} ✗ · ${r.blancos} — · ${nUm(r.puntos)} / ${nUm(r.max)} puntos</div>`;
        }
        const correctas = correctasDe(i);
        const dadas     = contestadasDe(i);
        const isCorrect = esAcierto(i);
        const isSkipped = sinResponder(i);

        // Marcar visualmente en las tarjetas
        marcarSolucion(i);
        document.getElementById(`feed-${i}`).style.display = 'block';

        // Textos de las opciones tal y como han salido en esta tarjeta
        const optEls   = document.querySelectorAll(`#qcard-${i} .option > span:last-child`);
        // innerHTML y no textContent: así el formato de la respuesta
        // (negrita, resaltado, tamaño…) también se ve en la corrección.
        const optTexts = [...optEls].map(el => el.innerHTML.trim());
        const listar   = idx => idx.map(n => `${LETTERS[n]}) ${String(optTexts[n]).replace(/\n/g, '<br>')}`).join('<br>');
        const varias   = correctas.length > 1;

        const badgeClass = isSkipped ? 'skip' : isCorrect ? 'ok' : 'err';
        const badgeText  = isSkipped ? '—'   : isCorrect ? '✓'  : '✗';

        html += `
        <div class="corr-item">
            <div class="ci-header">
                <div class="ci-badge ${badgeClass}">${badgeText}</div>
                <div class="ci-q"><strong>Pregunta ${i+1}.</strong> ${q.q}</div>
            </div>
            <div class="ci-answers">
                ${!isSkipped ? `<div class="given ${isCorrect?'':'wrong'}">
                    <strong>${varias ? 'Respuestas elegidas:' : 'Respuesta elegida:'}</strong><br>${listar(dadas)}
                </div>` : `<div class="given wrong"><em>Pregunta no respondida</em></div>`}
                ${!isCorrect ? `<div class="correct-ans">
                    <strong>${varias ? 'Respuestas correctas:' : 'Respuesta correcta:'}</strong><br>${listar(correctas)}
                </div>` : ''}
            </div>
            <div class="ci-law"><strong>⚖️ Normativa aplicable:</strong><br>${q.law}</div>
            ${q.tip ? `<div class="ci-tip">${q.tip}</div>` : ''}
        </div>`;
    });

    panel.innerHTML = html;
    panel.style.display = 'block';

    // Mostrar botones en overlay
    setButtonsVisible(['print-btn', 'restart-btn', 'home-btn-bottom'], true);
}

/* ═══════════════════════════════════════════
   IMPRESIÓN / PDF
═══════════════════════════════════════════ */
/* La página se prepara para el papel en «beforeprint» y vuelve a su estado
   en «afterprint», tanto con el botón 🖨 como con Ctrl+P o el menú del
   navegador. Antes se restauraba con un retraso fijo de 1 s, y en el móvil
   (donde el diálogo de imprimir no espera) podía salir solo la pregunta actual. */
let impresion = null;          // estado guardado mientras se imprime

function prepararImpresion() {
    if (impresion) return;
    const overlay = document.getElementById('overlay');
    impresion = { overlay: overlay.classList.contains('show') };

    // El documento ya está montado en el orden de lectura (cabecera de
    // sección → enunciado → sus preguntas → siguiente enunciado…), así que
    // para imprimir basta con enseñarlo entero: no hay que recolocar nada.
    document.querySelectorAll('.question-card').forEach(c => { c.style.display = 'block'; });
    // Las motivaciones solo salen en papel si ya se ha corregido
    if (evaluated) document.querySelectorAll('.feedback').forEach(f => { f.dataset.antes = f.style.display; f.style.display = 'block'; });
    document.querySelectorAll('.block-header').forEach(h => h.classList.add('visible'));
    // En papel los enunciados salen completos, aunque en pantalla
    // estuvieran recortados por el modo foco.
    document.querySelectorAll('.stmt-panel').forEach(p => {
        if (p.dataset.render !== 'full') {
            p.dataset.render = 'full';
            p.innerHTML = renderStatementHTML(getStatement(p.dataset.stmt));
        }
        p.classList.add('visible');
    });
    // Ocultar el overlay mientras se imprime (sin tocar el display inline,
    // para no romper el cierre posterior con classList en closeOverlay)
    overlay.classList.remove('show');
}

function restaurarTrasImpresion() {
    if (!impresion) return;
    const estaba = impresion;
    impresion = null;
    document.querySelectorAll('.question-card').forEach(c => { c.style.display = ''; });
    document.querySelectorAll('.feedback[data-antes]').forEach(f => { f.style.display = f.dataset.antes; delete f.dataset.antes; });
    // jump() vuelve a dejar a la vista solo lo que corresponde al modo en que
    // se estaba trabajando.
    if (questions.length) {
        jump(current, true);
    } else {
        document.querySelectorAll('.block-header, .stmt-panel').forEach(el => el.classList.remove('visible'));
    }
    if (evaluated && estaba.overlay) document.getElementById('overlay').classList.add('show');
}

window.addEventListener('beforeprint', prepararImpresion);
window.addEventListener('afterprint', restaurarTrasImpresion);

function printResults() {
    // El botón solo aparece tras corregir; por si acaso, sin corregir no se imprime la solución
    if (!evaluated) return;
    cerrarMasAcciones();
    prepararImpresion();          // por si el navegador no avisa con beforeprint
    window.print();
}

/* ═══════════════════════════════════════════
   ENVÍO A GOOGLE FORMS — UTILIDAD COMÚN
   ───────────────────────────────────────────
   Manda un juego de casillas a un formulario de Google mediante un
   formulario oculto dirigido a un iframe oculto: así no se navega
   fuera de la página ni hay problemas de CORS.
═══════════════════════════════════════════ */
/* Sin conexión el envío no se pierde: se guarda en una cola de este
   navegador (pwa.js) y sale solo al volver la conexión o al abrir la app.
   Devuelve 'enviado' o 'en-cola'. */
function postAFormulario(url, campos, nombreMarco) {
    const marco = nombreMarco || 'hidden-send-frame';
    const S = window.SupC1;
    if (navigator.onLine === false && S && typeof S.encolarEnvio === 'function') {
        S.encolarEnvio(url, campos);
        return 'en-cola';
    }

    let iframe = document.getElementById(marco);
    if (!iframe) {
        iframe = document.createElement('iframe');
        iframe.id = marco;
        iframe.name = marco;
        iframe.style.display = 'none';
        document.body.appendChild(iframe);
    }

    const form = document.createElement('form');
    form.action = url;
    form.method = 'POST';
    form.target = marco;
    form.style.display = 'none';

    Object.keys(campos).forEach(entryName => {
        const input = document.createElement('input');
        input.type  = 'hidden';
        input.name  = entryName;
        input.value = campos[entryName];
        form.appendChild(input);
    });

    document.body.appendChild(form);
    form.submit();
    form.remove();
    return 'enviado';
}

/* ═══════════════════════════════════════════
   ENVÍO AUTOMÁTICO DEL DETALLE PREGUNTA A PREGUNTA
   ───────────────────────────────────────────
   Se dispara solo al corregir (botón «Corregir» o tiempo agotado). No
   pide nada al alumno, no muestra avisos y no sustituye al envío
   manual del botón 📤: son dos formularios distintos y complementarios.

   Qué manda:
     · Nombre supuesto  → el título del supuesto
     · Tiempo           → fecha y hora del envío (dd/mm/aaaa hh:mm)
     · Nº de aciertos   → recuento en bruto, sin baremo
     · Nº de fallos     → recuento en bruto, sin baremo
     · Pregunta 1 … 80  → "Correcta: <lo que marcó>" si acertó,
                          "Incorrecta: <lo que marcó>" si falló,
                          "En blanco" si no la contestó.
   En las preguntas de respuesta múltiple se mandan todas las opciones
   que marcó, separadas por " | ", y cuentan como acierto solo si marcó
   exactamente las correctas (el mismo criterio que la corrección).

   Cada pregunta va a la casilla de su número ORIGINAL en el supuesto
   (q.__ord + 1), tal y como se planteó en el editor, aunque el intento
   la haya barajado o cambiado de sitio. Las preguntas que no hayan
   salido en el intento no ocupan casilla: se quedan vacías.
═══════════════════════════════════════════ */

// Texto de una opción sin la letra "A) " que a veces se escribe delante,
// igual que se presenta en pantalla. Las etiquetas de formato (<b>,
// <mark>, <span class="fs-l">…) se quitan: al formulario va texto pelado,
// que es lo que se puede comparar y contar en la hoja de resultados.
function textoOpcionLimpio(txt) {
    return String(txt === undefined || txt === null ? '' : txt)
                .replace(/<[^<>]*>/g, '')
                .replace(/^[A-G]\)\s*/, '')
                .replace(/\s+/g, ' ')
                .trim();
}

// Fecha y hora del envío en formato dd/mm/aaaa hh:mm
function fechaHoraEnvio() {
    const d  = new Date();
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mi = String(d.getMinutes()).padStart(2, '0');
    return `${dd}/${mm}/${d.getFullYear()} ${hh}:${mi}`;
}

// Qué contestó el alumno en una pregunta, con el texto tal y como está
// escrito en el supuesto (no la letra, que cambia en cada intento).
function loQueContesto(qIdx, q) {
    const card = document.getElementById(`qcard-${qIdx}`);
    // Posición en pantalla → posición en la lista de opciones del editor
    const barajado = String(card ? card.dataset.opciones || '' : '')
                        .split(',').filter(s => s !== '').map(Number);
    return contestadasDe(qIdx)
                .map(pos => barajado.length ? barajado[pos] : pos)
                // En el orden en que están escritas en el supuesto, no en el
                // barajado de este intento: así las mismas respuestas se
                // mandan siempre igual y se pueden comparar entre alumnos.
                .sort((x, y) => x - y)
                .map(idx => textoOpcionLimpio((q.a || [])[idx]))
                .filter(t => t !== '')
                .join(' | ');
}

function enviarDetalleCorreccion() {
    if (detalleEnviado) return;                 // una sola vez por intento
    if (esPractica()) return;                   // la práctica personal no se manda
    if (!ENVIO_DETALLE || !ENVIO_DETALLE.url) return;

    const campos = {};
    const anota = (casilla, valor) => {
        const nombre = String(casilla || '').trim();
        if (nombre) campos[nombre] = valor;
    };

    const res = calcResultados();

    anota(ENVIO_DETALLE.nombre,   (EXAM_CONFIG.titulo || document.title || '').trim());
    anota(ENVIO_DETALLE.tiempo,   fechaHoraEnvio());
    anota(ENVIO_DETALLE.aciertos, res.aciertos);
    anota(ENVIO_DETALLE.fallos,   res.fallos);

    const casillasPregunta = ENVIO_DETALLE.preguntas || [];

    questions.forEach((q, i) => {
        // Casilla fija según el orden original del supuesto
        const orden   = (typeof q.__ord === 'number') ? q.__ord : i;
        const casilla = casillasPregunta[orden];
        if (!casilla) return;                   // fuera de las 80 casillas

        let valor;
        if (sinResponder(i)) {
            valor = 'En blanco';
        } else {
            valor = (esAcierto(i) ? 'Correcta: ' : 'Incorrecta: ') + loQueContesto(i, q);
        }
        anota(casilla, valor);
    });

    detalleEnviado = true;
    try {
        postAFormulario(ENVIO_DETALLE.url, campos, 'hidden-detalle-frame');
    } catch (err) {
        detalleEnviado = false;                 // que pueda reintentarlo al repetir
    }
}

/* ═══════════════════════════════════════════
   ENVÍO DE RESULTADOS A GOOGLE FORMS
═══════════════════════════════════════════ */
async function enviarResultados() {
    if (!evaluated || esPractica()) return;
    cerrarMasAcciones();

    if (!ENVIO.url) {
        avisar('Envío no disponible', 'Este supuesto no tiene configurada la dirección de envío de resultados.');
        return;
    }

    const sendBtn = document.getElementById('send-btn');
    if (sendBtn && sendBtn.disabled) return;

    // Identificador del examen: título de la página
    const examId = document.title.trim();

    // Nombre del usuario (vacío = «Anónimo»; Cancelar = no se envía nada)
    let userName = await dialogo({
        titulo: 'Enviar resultados',
        texto: 'Escribe tu nombre para la tabla de resultados. Si lo dejas en blanco, se envía como «Anónimo».',
        campo: { placeholder: 'Tu nombre', etiqueta: 'Tu nombre para el envío de resultados' },
        botones: [{ texto: 'Cancelar', valor: null, cancelar: true },
                  { texto: 'Enviar', principal: true }]
    });
    if (userName === null || userName === undefined) return;
    userName = String(userName).trim();
    if (!userName) userName = 'Anónimo';

    // Estadísticas (globales y por bloque)
    const res      = calcResultados();
    const total    = res.total;
    const correct  = res.aciertos;
    const wrong    = res.fallos;
    const blank    = res.blancos;

    // Tiempos (formato mm:ss)
    const tiempoAsignado = formatTime(examDurationSeconds);
    const elapsedSeconds = Math.max(0, Math.min(examDurationSeconds, examDurationSeconds - timeLeft));
    const tiempoEmpleado = formatTime(elapsedSeconds);

    const FORM_ACTION_URL = ENVIO.url;

    // Cada dato va a la casilla que se le haya asignado en el editor.
    // Las casillas que se dejen vacías simplemente no se envían.
    const fieldMap = {};
    const anota = (casilla, valor) => {
        const nombre = String(casilla || '').trim();
        if (nombre) fieldMap[nombre] = valor;
    };

    anota(ENVIO.examen,         examId);
    anota(ENVIO.usuario,        userName);
    anota(ENVIO.tiempoAsignado, tiempoAsignado);
    anota(ENVIO.tiempoEmpleado, tiempoEmpleado);

    // Un juego de casillas por cada bloque que haya salido en el intento
    // (opcional: las casillas vacías no se envían).
    res.bloques.forEach(r => {
        const casillas = r.bloque.envio || {};
        anota(casillas.preguntas, r.total);
        anota(casillas.aciertos,  r.aciertos);
        anota(casillas.fallos,    r.fallos);
        anota(casillas.blancos,   r.blancos);
        anota(casillas.puntos,    nUm(r.puntos));
    });

    // TOTAL ABSOLUTO: todos los bloques sumados como si fueran uno solo
    // (preguntas, aciertos, fallos, en blanco y puntos). Se anota DESPUÉS
    // de los bloques: si una casilla coincidiera con la de algún bloque,
    // manda el total y no el último bloque que la pisaba.
    // Archivos antiguos sin apartado "total": se usan las casillas del
    // primer bloque, que es lo que antes hacía el formulario del proyecto.
    if (ENVIO.enviarTotal !== false) {
        const casTot = (ENVIO.total && typeof ENVIO.total === 'object') ? ENVIO.total
                     : ((BLOCKS_BANK[0] && BLOCKS_BANK[0].envio) || {});
        anota(casTot.preguntas, res.total);
        anota(casTot.aciertos,  res.aciertos);
        anota(casTot.fallos,    res.fallos);
        anota(casTot.blancos,   res.blancos);
        anota(casTot.puntos,    nUm(res.puntos));
    }

    // Formulario oculto dirigido a un iframe oculto: no se navega fuera de
    // la página y se evitan los problemas de CORS. Sin conexión, a la cola.
    const estado = postAFormulario(FORM_ACTION_URL, fieldMap, 'hidden-send-frame');
    const enCola = estado === 'en-cola';

    ['send-btn', 'ov-send-btn'].forEach(id => {
        const b = document.getElementById(id);
        if (!b) return;
        b.disabled = true;
        b.textContent = enCola ? '⏳ Se enviará al volver la conexión' : '✔ Resultados enviados';
    });

    const desglose = res.bloques.length < 2 ? '' :
        '\n\nPor bloques:' + res.bloques.map(r =>
            '\n · ' + r.bloque.titulo + ': ' + r.aciertos + ' ✓ · ' + r.fallos +
            ' ✗ · ' + r.blancos + ' — · ' + nUm(r.puntos) + ' / ' + nUm(r.max) + ' puntos').join('');

    // El formulario de Google no contesta a la página, así que no se puede
    // confirmar la llegada: se dice «enviados», no «recibidos».
    avisar(enCola ? 'Sin conexión: envío guardado' : 'Resultados enviados', [
        enCola ? 'Ahora no hay conexión. Tus resultados se han guardado en este dispositivo y se enviarán solos en cuanto vuelva la conexión.' : '',
        'Examen: ' + examId + ' · Usuario: ' + userName,
        'Aciertos: ' + correct + ' / ' + total + ' · Fallos: ' + wrong + ' · En blanco: ' + blank,
        'Puntuación: ' + nUm(res.puntos) + ' / ' + nUm(res.max) + ' · Tiempo empleado: ' + tiempoEmpleado + ' de ' + tiempoAsignado,
        desglose.trim()
    ]);
}

/* ═══════════════════════════════════════════
   REINICIAR (elección de aleatoriedad)
═══════════════════════════════════════════ */
/* Cada una de las dos formas de repetir se puede quitar por separado
   desde el editor. Si solo queda una, no tiene sentido preguntar: se
   arranca directamente con ella. Si no queda ninguna, el botón 🔀 ni
   siquiera se muestra (ver botonPermitido). */
function modosAleatoriosDisponibles() {
    return [['answers', 'opcionRepetirRespuestas'],
            ['order',   'opcionRepetirOrden']]
           .filter(([, clave]) => interfazVisible(clave))
           .map(([modo]) => modo);
}

function openRandomModal() {
    cerrarMasAcciones();
    const modos = modosAleatoriosDisponibles();
    if (modos.length === 1) { confirmRestart(modos[0]); return; }
    if (!modos.length) return;
    const modal = document.getElementById('random-modal');
    modal.classList.add('show');
    const primero = [...modal.querySelectorAll('button')].find(b => b.offsetParent !== null);
    if (primero) primero.focus({ preventScroll: true });
}

function closeRandomModal() {
    document.getElementById('random-modal').classList.remove('show');
}

// mode: 'answers' → mismas preguntas y mismo orden, solo cambian las
//                    opciones de respuesta.
//       'order'   → las mismas preguntas, todas, en otro orden (respetando
//                    siempre el vínculo pregunta-enunciado y renumerando
//                    1..N de forma correlativa y visible).
function confirmRestart(mode) {
    closeRandomModal();
    if (timerInt) clearInterval(timerInt);
    // Limpiar banner inline
    const old = document.getElementById('inline-score-banner');
    if (old) old.remove();
    // Ocultar overlay
    document.getElementById('overlay').classList.remove('show');
    // Reinicializar el intento. Para 'answers' se reutiliza el conjunto de
    // preguntas ya cargado (questions); para 'order' se recalcula desde cero
    // a partir de QUESTIONS_BANK dentro de buildQuestionOrder().
    init(mode, questions);
}

/* ═══════════════════════════════════════════
   VOLVER AL MENÚ PRINCIPAL
═══════════════════════════════════════════ */
/* Si el examen está a medias se pregunta antes de salir. El texto lo puede
   cambiar un módulo (app-supuesto.js guarda el intento y lo dice así), y
   justo antes de salir se avisa con «supc1:salir» para que guarde. */
async function goHome() {
    if (!evaluated) {
        const S = window.SupC1;
        const texto = (S && S.textoSalir) ||
            'Vas a salir del expediente dejando el test a medias: se perderá el progreso del intento actual.';
        const salir = await confirmar('¿Volver al menú principal?', texto, 'Volver al menú', 'Seguir aquí');
        if (!salir) return;
    }
    emitir('salir');
    window.location.href = (ajusteInterfaz('botonCasa').url || '../index.html');
}

/* ═══════════════════════════════════════════
   ARRANQUE INICIAL
═══════════════════════════════════════════ */
// Inicializar contexto de audio al primer clic del usuario
document.addEventListener('click', () => {
    try { getAudioCtx(); } catch(e) {}
}, { once: true });

applyExamConfig();
init('default');

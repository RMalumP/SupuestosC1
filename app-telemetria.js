/* Instantánea anónima de los intentos que se dejan a medias.
   Apagado por defecto: lo activa telemetria-config.js. Se carga con «defer»
   después de app-supuesto.js. No hace nada si no está activo o si la persona
   ha desmarcado «Enviar datos anónimos». */
(function () {
    'use strict';
    var C = window.SUPC1_TELEMETRIA;
    var S = window.SupC1;
    if (!C || !C.activa || !C.url || !S) return;
    if (typeof questions === 'undefined' || typeof userAns === 'undefined') return;

    var ID = (location.pathname.split('/').pop() || 'supuesto').replace(/\.html?$/i, '');
    var $ = function (id) { return document.getElementById(id); };
    var permitido = function () { return !S.get('telemetria-no', false); };

    /* Identificador anónimo del navegador (no es un dato personal) */
    var anonimo = S.get('anon-id', null);
    if (!anonimo) {
        var b = new Uint8Array(8);
        (window.crypto || window.msCrypto).getRandomValues(b);
        anonimo = Array.prototype.map.call(b, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
        S.set('anon-id', anonimo);
    }

    /* Identificador del intento: el mismo si se continúa un intento guardado */
    var K_INT = 'tel-intento:' + ID;
    var hayCurso = !!S.get('curso:' + ID, null);
    var intento = hayCurso ? S.get(K_INT, null) : null;
    function nuevoIntento() { intento = anonimo.slice(0, 6) + '-' + Date.now().toString(36); S.set(K_INT, intento); }
    if (!intento) nuevoIntento();
    var ultimaHuella = '', ultimoEnvio = 0;

    /* Cada vez que empieza un intento nuevo (init) se estrena identificador */
    var initPrevio = window.init;
    window.init = function () {
        var r = initPrevio.apply(this, arguments);
        nuevoIntento(); ultimaHuella = '';
        return r;
    };

    function hhmmss(s) { s = Math.max(0, s | 0); return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); }

    function lineaPregunta(q, i) {
        if (sinResponder(i)) return 'En blanco';
        return (esAcierto(i) ? 'Correcta: ' : 'Incorrecta: ') + (typeof loQueContesto === 'function' ? loQueContesto(i, q) : '');
    }

    function construir() {
        var campos = {}, cf = C.campos || {};
        var pon = function (casilla, valor) { casilla = String(casilla || '').trim(); if (casilla) campos[casilla] = valor; };
        var res = calcResultados();
        var resp = Object.keys(userAns).length;
        var parciales = [];
        questions.forEach(function (q, i) {
            var orden = (typeof q.__ord === 'number') ? q.__ord : i;
            var texto = lineaPregunta(q, i);
            if (cf.preguntas && cf.preguntas[orden]) pon(cf.preguntas[orden], texto);
            else parciales.push((orden + 1) + ' · ' + texto);
        });
        pon(cf.examen, ((typeof EXAM_CONFIG !== 'undefined' && EXAM_CONFIG.titulo) || document.title || '').trim());
        pon(cf.fecha, typeof fechaHoraEnvio === 'function' ? fechaHoraEnvio() : new Date().toLocaleString('es-ES'));
        pon(cf.estado, 'Incompleto (abandonado)');
        pon(cf.modo, (typeof instantFeedback !== 'undefined' && instantFeedback) ? 'Pregunta a pregunta' : 'Normal');
        pon(cf.intento, intento);
        pon(cf.anonimo, anonimo);
        pon(cf.respondidas, resp);
        pon(cf.total, questions.length);
        pon(cf.aciertos, res.aciertos);
        pon(cf.fallos, res.fallos);
        pon(cf.blancos, res.blancos);
        pon(cf.tiempoRestante, hhmmss(timeLeft));
        if (parciales.length) pon(cf.respuestas, parciales.join('\n'));
        return campos;
    }

    function enviar(campos) {
        var cuerpo = new URLSearchParams(campos).toString();
        var ok = false;
        try {
            if (navigator.sendBeacon) ok = navigator.sendBeacon(C.url, new Blob([cuerpo], { type: 'application/x-www-form-urlencoded' }));
        } catch (e) { ok = false; }
        if (!ok) {
            try { fetch(C.url, { method: 'POST', mode: 'no-cors', keepalive: true,
                                 headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: cuerpo }); }
            catch (e) { /* sin red: no pasa nada */ }
        }
    }

    function instantanea() {
        if (!permitido() || evaluated) return;
        if (document.body.classList.contains('intento-parcial')) return;       // repetir falladas: práctica personal
        var resp = Object.keys(userAns).length;
        if (resp < (C.minRespuestas || 1)) return;
        var huella = resp + '|' + JSON.stringify(userAns);
        if (huella === ultimaHuella) return;                                   // nada nuevo desde el último envío
        if (Date.now() - ultimoEnvio < 15000) return;                          // como mucho una cada 15 s
        try { enviar(construir()); ultimaHuella = huella; ultimoEnvio = Date.now(); } catch (e) { /* no estorbar al alumno */ }
    }

    document.addEventListener('visibilitychange', function () { if (document.hidden) instantanea(); });
    window.addEventListener('pagehide', instantanea);

    /* Casilla para no participar, en el panel ⚙ */
    var panel = $('settings-panel');
    if (panel && !$('row-telemetria')) {
        var fila = document.createElement('div');
        fila.className = 'settings-row settings-check'; fila.id = 'row-telemetria';
        fila.innerHTML = '<label><input type="checkbox" id="telemetria-toggle"><span>Enviar datos anónimos de mis intentos</span></label>';
        panel.appendChild(fila);
        var t = $('telemetria-toggle'); t.checked = permitido();
        t.addEventListener('change', function () { S.set('telemetria-no', !t.checked); });
    }
})();

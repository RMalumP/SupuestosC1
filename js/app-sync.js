/* Sincronización entre dispositivos con Google Drive (carpeta oculta «appDataFolder»
   del propio usuario). Apagado mientras sync-config.js no tenga «clientId».
   El núcleo (fusionar datos) no toca el navegador y se prueba aparte en Node. */
(function (raiz, fabrica) {
    if (typeof module === 'object' && module.exports) module.exports = fabrica(null);
    else raiz.SupC1Sync = fabrica(raiz);
})(typeof self !== 'undefined' ? self : this, function (W) {
    'use strict';

    /* ═══════════ NÚCLEO: fusionar dos copias ═══════════
       Cada elemento (fallada, marcada, nota) lleva su fecha «ts». Al borrar uno se deja una
       «lápida» con la fecha del borrado, para que no resucite al sincronizar con otro
       dispositivo. Para cada elemento gana lo más reciente (elemento o lápida). */
    var NOVENTA_DIAS = 90 * 24 * 3600 * 1000;
    var COLECCIONES = ['falladas', 'marcadas', 'notas', 'favoritas', 'subrayados'];
    var TIPO = { falladas: 'f', marcadas: 'm', notas: 'n', favoritas: 'v', subrayados: 'u' };   // prefijo de las lápidas

    function normBanco(b) {
        b = b || {};
        return { falladas: b.falladas || {}, marcadas: b.marcadas || {}, notas: b.notas || {}, favoritas: b.favoritas || {}, subrayados: b.subrayados || {}, borradas: b.borradas || {} };
    }
    function mezclarBanco(a, b, ahora) {
        a = normBanco(a); b = normBanco(b); ahora = ahora || Date.now();
        var out = { falladas: {}, marcadas: {}, notas: {}, favoritas: {}, subrayados: {}, borradas: {} };
        COLECCIONES.forEach(function (col) {
            var tipo = TIPO[col], claves = {};
            [a[col], b[col]].forEach(function (m) { Object.keys(m).forEach(function (k) { claves[k] = 1; }); });
            [a.borradas, b.borradas].forEach(function (m) { Object.keys(m).forEach(function (k) { if (k.charAt(0) === tipo && k.charAt(1) === ':') claves[k.slice(2)] = 1; }); });
            Object.keys(claves).forEach(function (k) {
                var ea = a[col][k], eb = b[col][k], mejor = null;
                [ea, eb].forEach(function (e) { if (e && (!mejor || (e.ts || 0) > (mejor.ts || 0))) mejor = e; });
                var lapida = Math.max(a.borradas[tipo + ':' + k] || 0, b.borradas[tipo + ':' + k] || 0);
                if (mejor && (mejor.ts || 0) >= lapida) out[col][k] = mejor;
                else if (lapida && ahora - lapida < NOVENTA_DIAS) out.borradas[tipo + ':' + k] = lapida;
            });
        });
        return out;
    }
    function mezclarProg(a, b) {
        if (!a) return b || null; if (!b) return a;
        var porFecha = {};
        (a.hist || []).concat(b.hist || []).forEach(function (r) { if (r && r.fecha != null) porFecha[r.fecha] = r; });
        var hist = Object.keys(porFecha).map(function (k) { return porFecha[k]; }).sort(function (x, y) { return x.fecha - y.fecha; }).slice(-40);
        var todos = hist.concat([a.mejor, b.mejor, a.ultima, b.ultima].filter(Boolean));
        var mejor = null, ultima = null;
        todos.forEach(function (r) {
            if (!mejor || r.pct > mejor.pct) mejor = r;
            if (!ultima || (r.fecha || 0) > (ultima.fecha || 0)) ultima = r;
        });
        // Aproximación: los intentos de cada dispositivo son distintos, así que se cuentan las fechas distintas
        return { intentos: Math.max(a.intentos || 0, b.intentos || 0, hist.length), mejor: mejor, ultima: ultima, hist: hist };
    }
    /* Intentos a medias («curso»): gana el más reciente; al terminar o descartar uno se deja una
       lápida con la fecha, para que no reaparezca en el otro dispositivo. Pasada una semana sin tocarlos se descartan. */
    var SIETE_DIAS = 7 * 24 * 3600 * 1000;
    function mezclarCurso(a, b, ba, bb, ahora) {
        a = a || {}; b = b || {}; ba = ba || {}; bb = bb || {}; ahora = ahora || Date.now();
        var out = { curso: {}, cursoBorr: {} }, ids = {};
        [a, b, ba, bb].forEach(function (m) { Object.keys(m).forEach(function (k) { ids[k] = 1; }); });
        Object.keys(ids).sort().forEach(function (k) {
            var ea = a[k], eb = b[k], mejor = ea;
            if (eb && (!mejor || (eb.ts || 0) > (mejor.ts || 0))) mejor = eb;
            var lapida = Math.max(ba[k] || 0, bb[k] || 0);
            if (mejor && (mejor.ts || 0) > lapida) { if (ahora - (mejor.ts || 0) < SIETE_DIAS) out.curso[k] = mejor; }
            else if (lapida && ahora - lapida < NOVENTA_DIAS) out.cursoBorr[k] = lapida;
        });
        return out;
    }
    function mezclarTodo(local, remoto, ahora) {
        local = local || {}; remoto = remoto || {};
        var mc = mezclarCurso(local.curso, remoto.curso, local.cursoBorr, remoto.cursoBorr, ahora);
        var out = { v: 1, banco: mezclarBanco(local.banco, remoto.banco, ahora), prog: {}, curso: mc.curso, cursoBorr: mc.cursoBorr };
        var claves = {};
        Object.keys(local.prog || {}).concat(Object.keys(remoto.prog || {})).forEach(function (k) { claves[k] = 1; });
        Object.keys(claves).forEach(function (k) {
            var m = mezclarProg((local.prog || {})[k], (remoto.prog || {})[k]);
            if (m) out.prog[k] = m;
        });
        return out;
    }
    // Qué trae la copia fusionada que no estuviera ya en este dispositivo (para decírselo a la persona)
    function novedades(local, fusion) {
        local = local || {}; var lb = normBanco(local.banco), fb = fusion.banco, r = { falladas: 0, marcadas: 0, notas: 0, favoritas: 0, subrayados: 0, intentos: 0, quitadas: 0, cursos: 0 };
        COLECCIONES.forEach(function (c) {
            Object.keys(fb[c]).forEach(function (k) { if (!lb[c][k] || (lb[c][k].ts || 0) < (fb[c][k].ts || 0)) r[c]++; });
            Object.keys(lb[c]).forEach(function (k) { if (!fb[c][k]) r.quitadas++; });
        });
        Object.keys(fusion.curso || {}).forEach(function (k) {
            var l = (local.curso || {})[k]; if (!l || (l.ts || 0) < (fusion.curso[k].ts || 0)) r.cursos++;
        });
        Object.keys(fusion.prog).forEach(function (k) {
            var l = (local.prog || {})[k]; r.intentos += Math.max(0, (fusion.prog[k].intentos || 0) - (l ? (l.intentos || 0) : 0));
        });
        return r;
    }

    var nucleo = { mezclarBanco: mezclarBanco, mezclarProg: mezclarProg, mezclarCurso: mezclarCurso, mezclarTodo: mezclarTodo, novedades: novedades };
    if (!W) return nucleo;

    /* ═══════════ NAVEGADOR: Google Drive + ventanas ═══════════ */
    var S = W.SupC1, C = W.SUPC1_SYNC || {}, doc = W.document;
    var API = 'https://www.googleapis.com';
    var $ = function (id) { return doc.getElementById(id); };
    var el = function (tag, cls, txt) { var e = doc.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
    var nombreArchivo = C.archivo || 'supc1-sync.json';
    var K_ULT = 'sync-ultima', K_NO = 'sync-explicacion-no', K_SES = 'sync-sesion';
    var K_TOK = 'supc1:sync-token';       // acceso temporal de Google (1 hora), compartido entre pestañas y páginas
    var K_INT = 'supc1:sync-intento';     // cuándo fue el último intento de renovarlo sin ventana (para no insistir)

    function leerLocal() {
        var prog = {};
        for (var i = 0; i < W.localStorage.length; i++) {
            var k = W.localStorage.key(i);
            if (k.indexOf('supc1:prog:') === 0) { try { prog[k.slice(11)] = JSON.parse(W.localStorage.getItem(k)); } catch (e) { /* ignorar */ } }
        }
        var curso = {}, cursoBorr = {};
        for (var j = 0; j < W.localStorage.length; j++) {
            var c = W.localStorage.key(j);
            try {
                if (c.indexOf('supc1:curso:') === 0) curso[c.slice(12)] = JSON.parse(W.localStorage.getItem(c));
                else if (c.indexOf('supc1:cursoborr:') === 0) cursoBorr[c.slice(16)] = JSON.parse(W.localStorage.getItem(c));
            } catch (e) { /* ignorar */ }
        }
        return { banco: S.get('banco', null), prog: prog, curso: curso, cursoBorr: cursoBorr };
    }
    var aplicando = false;      // mientras se escribe lo recibido, no se programa otra sincronización
    function escribirLocal(f) {
        aplicando = true;
        try {
            S.set('banco', f.banco);
            Object.keys(f.prog).forEach(function (k) { S.set('prog:' + k, f.prog[k]); });
            Object.keys(f.curso || {}).forEach(function (k) {
                var l = S.get('curso:' + k, null); if (!l || (l.ts || 0) < (f.curso[k].ts || 0)) S.set('curso:' + k, f.curso[k]);
            });
            Object.keys(f.cursoBorr || {}).forEach(function (k) {
                var l = S.get('curso:' + k, null); if (l && (l.ts || 0) <= f.cursoBorr[k]) S.del('curso:' + k);
                S.set('cursoborr:' + k, f.cursoBorr[k]);
            });
        } finally { aplicando = false; }
    }

    /* ─── Sesión: se recuerda hasta pulsar «Cerrar sesión» ─── */
    var sesion = function () { return !!S.get(K_SES, null); };
    function tokenGuardado() {
        try { var t = JSON.parse(W.localStorage.getItem(K_TOK)); if (t && t.t && t.exp > Date.now()) return t.t; } catch (e) { /* ignorar */ }
        return null;
    }
    function guardarToken(t, seg) {
        var exp = Date.now() + Math.max(60, (seg || 3600) - 60) * 1000;
        try { W.localStorage.setItem(K_TOK, JSON.stringify({ t: t, exp: exp })); } catch (e) { /* ignorar */ }
        vigilarCaducidad(exp);
    }
    function olvidarToken() { try { W.localStorage.removeItem(K_TOK); } catch (e) { /* ignorar */ } }
    function ultimoIntento() { try { return +W.localStorage.getItem(K_INT) || 0; } catch (e) { return 0; } }
    function anotarIntento() { try { W.localStorage.setItem(K_INT, String(Date.now())); } catch (e) { /* ignorar */ } }

    function cargarGoogle() {
        return new Promise(function (ok, ko) {
            if (W.google && W.google.accounts && W.google.accounts.oauth2) return ok();
            var s = el('script'); s.src = 'https://accounts.google.com/gsi/client'; s.async = true;
            s.onload = function () { ok(); }; s.onerror = function () { ko(new Error('red')); };
            doc.head.appendChild(s);
        });
    }
    // interactivo=false: renovar el acceso sin ventana (solo funciona si la persona ya dio el permiso y sigue con la sesión de Google abierta)
    function pedirPermiso(interactivo) {
        var previo = tokenGuardado(); if (previo) return Promise.resolve(previo);
        return new Promise(function (ok, ko) {
            var plazo = interactivo ? null : setTimeout(function () { ko(new Error('silencio')); }, 15000);
            var fin = function () { if (plazo) clearTimeout(plazo); };
            var cli = W.google.accounts.oauth2.initTokenClient({
                client_id: C.clientId, scope: 'https://www.googleapis.com/auth/drive.appdata',
                callback: function (r) { fin(); if (r && r.access_token) { guardarToken(r.access_token, +r.expires_in); ok(r.access_token); } else ko(new Error(r && r.error || 'denegado')); },
                error_callback: function (e) { fin(); ko(new Error(e && e.type || 'cerrada')); }
            });
            cli.requestAccessToken({ prompt: interactivo ? '' : 'none' });
        });
    }
    function drive(token, ruta, opciones) {
        opciones = opciones || {}; opciones.cache = 'no-store';      // nunca una copia antigua guardada por el navegador
        opciones.headers = Object.assign({ Authorization: 'Bearer ' + token }, opciones.headers || {});
        return W.fetch(API + ruta, opciones).then(function (r) {
            if (!r.ok) return r.text().then(function (t) { var e = new Error('drive ' + r.status); e.estado = r.status; e.detalle = t.slice(0, 200); throw e; });
            return r;
        });
    }
    function buscar(token) {
        return drive(token, '/drive/v3/files?spaces=appDataFolder&fields=files(id,name)&q=' + encodeURIComponent("name='" + nombreArchivo + "'"))
            .then(function (r) { return r.json(); }).then(function (j) { return (j.files || [])[0] || null; });
    }
    function descargar(token, id) { return drive(token, '/drive/v3/files/' + id + '?alt=media').then(function (r) { return r.json(); }); }
    function subir(token, id, datos) {
        var cuerpo = JSON.stringify(datos);
        if (id) return drive(token, '/upload/drive/v3/files/' + id + '?uploadType=media', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: cuerpo });
        var lim = 'supc1' + Date.now();
        var multi = '--' + lim + '\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n' + JSON.stringify({ name: nombreArchivo, parents: ['appDataFolder'] }) +
            '\r\n--' + lim + '\r\nContent-Type: application/json\r\n\r\n' + cuerpo + '\r\n--' + lim + '--';
        return drive(token, '/upload/drive/v3/files?uploadType=multipart', { method: 'POST', headers: { 'Content-Type': 'multipart/related; boundary=' + lim }, body: multi });
    }

    function sincronizar(interactivo, reintento) {
        var token;
        return cargarGoogle().then(function () { return pedirPermiso(interactivo); }).then(function (t) { token = t; return buscar(t); }).then(function (f) {
            return (f ? descargar(token, f.id) : Promise.resolve(null)).then(function (remoto) {
                var local = leerLocal(), fusion = mezclarTodo(local, remoto), nov = novedades(local, fusion);
                escribirLocal(fusion);
                return subir(token, f && f.id, fusion).then(function () {
                    S.set(K_ULT, Date.now());
                    return { nov: nov, primera: !f };
                });
            });
        }).catch(function (e) {
            if (e && e.estado === 401 && !reintento) { olvidarToken(); return sincronizar(interactivo, true); }      // el acceso había caducado
            throw e;
        });
    }

    /* ─── Sincronización automática (con la sesión recordada) ─── */
    var estado = 'fuera';       // fuera · ok · sincronizando · reconectar · error
    var enCurso = false, pendiente = false, reloj = null;
    var AVISO_ESPERA = 60000, GESTO_ESPERA = 15000, aCaducar = null;
    // Cuando caduca el acceso (1 hora) se intenta renovar solo; si el navegador lo impide, queda el aviso y se reintenta con el siguiente toque
    function vigilarCaducidad(exp) {
        if (aCaducar) clearTimeout(aCaducar);
        aCaducar = setTimeout(function () { aCaducar = null; if (sesion() && !tokenGuardado()) auto(); }, Math.max(1000, exp - Date.now() + 500));
    }
    function auto(conGesto) {
        if (!sesion()) return;
        if (enCurso) { pendiente = true; return; }
        // sin acceso válido: se intenta renovar sin ventana, pero sin insistir (varias páginas abiertas no deben abrir Google a la vez)
        if (!tokenGuardado()) {
            if (!conGesto && Date.now() - ultimoIntento() < AVISO_ESPERA) { estado = 'reconectar'; armarGesto(); pintarIcono(); pintarTarjeta(); return; }
            anotarIntento();
        }
        enCurso = true; estado = 'sincronizando'; pintarIcono(); pintarTarjeta();
        sincronizar(false).then(function (r) {
            estado = 'ok';
            var n = r.nov;
            if (W.SupC1Estudio && (n.falladas || n.marcadas || n.notas || n.favoritas || n.subrayados || n.intentos || n.cursos || n.quitadas)) W.SupC1Estudio.repintar();
        }).catch(function (e) {
            estado = /silencio|interaction|login|consent|popup|cerrada|denegado|access_denied|immediate/i.test(String(e && e.message)) ? 'reconectar' : 'error';
            if (estado === 'reconectar') armarGesto();
        }).then(function () {
            enCurso = false; pintarIcono(); pintarTarjeta();
            if (pendiente) { pendiente = false; programar(); }
        });
    }
    var gestoArmado = false;
    function armarGesto() {
        if (gestoArmado) return; gestoArmado = true;
        var h = function () {
            if (estado !== 'reconectar' && estado !== 'error') { quitar(); return; }
            if (enCurso || Date.now() - ultimoIntento() < GESTO_ESPERA) return;
            quitar(); auto(true);
        };
        var quitar = function () { gestoArmado = false; ['pointerdown', 'keydown'].forEach(function (t) { doc.removeEventListener(t, h, true); }); };
        ['pointerdown', 'keydown'].forEach(function (t) { doc.addEventListener(t, h, true); });
    }
    function programar() { if (reloj) clearTimeout(reloj); reloj = setTimeout(function () { reloj = null; auto(); }, 4000); }
    function vigilar() {
        var set = S.set, del = S.del, claves = /^(banco$|prog:|curso:|cursoborr:)/;
        S.set = function (k, v) { set.call(S, k, v); if (!aplicando && sesion() && claves.test(k)) programar(); };
        S.del = function (k) { del.call(S, k); if (!aplicando && sesion() && claves.test(k)) programar(); };
        doc.addEventListener('visibilitychange', function () { if (doc.visibilityState === 'hidden' && sesion() && !enCurso) { if (reloj) { clearTimeout(reloj); reloj = null; } auto(); } });
    }
    function cerrarSesion() {
        var terminar = function () { S.del(K_SES); S.del(K_ULT); olvidarToken(); estado = 'fuera'; pintarTarjeta(); pintarIcono(); };
        var t = tokenGuardado();
        var tener = t ? Promise.resolve(t) : cargarGoogle().then(function () { return pedirPermiso(false); });
        tener.then(function (tk) {
            if (W.google && W.google.accounts.oauth2.revoke) W.google.accounts.oauth2.revoke(tk, terminar); else terminar();
        }).catch(terminar);      // si no se pudo, al menos se deja de sincronizar aquí
    }

    /* ─── Ventanas ─── */
    function ventana(titulo, cuerpo, botones, clase) {
        var fondo = el('div', 'supc1-modal sync-modal' + (clase ? ' ' + clase : ''));
        var caja = el('div', 'supc1-modal-caja'); caja.setAttribute('role', 'dialog'); caja.setAttribute('aria-modal', 'true'); caja.setAttribute('aria-label', titulo);
        caja.appendChild(el('h3', null, titulo)); caja.appendChild(cuerpo);
        var fila = el('div', 'supc1-modal-botones');
        botones.forEach(function (b) {
            var x = el('button', 'btn ' + (b.principal ? 'btn-primary' : ''), b.texto); x.type = 'button';
            x.addEventListener('click', function () { b.accion(fondo); }); fila.appendChild(x);
        });
        caja.appendChild(fila); fondo.appendChild(caja);
        fondo.addEventListener('keydown', function (e) { if (e.key === 'Escape') fondo.remove(); });
        doc.body.appendChild(fondo);
        var primero = fila.querySelector('button'); if (primero) primero.focus({ preventScroll: true });
        return fondo;
    }
    function lista(tag, items) { var l = el(tag); items.forEach(function (t) { var li = el('li'); li.innerHTML = t; l.appendChild(li); }); return l; }

    function explicacion(siguiente) {
        var c = el('div', 'sync-texto');
        c.appendChild(el('p', null, 'Esto te permite tener tus notas, preguntas marcadas, favoritas, subrayados, falladas y estadísticas en el móvil, la tablet y el ordenador a la vez.'));
        c.appendChild(el('h4', null, '¿Qué va a pasar?'));
        c.appendChild(lista('ul', [
            'Se guarda una copia de tus datos de estudio en una <strong>carpeta privada y oculta de tu propio Google Drive</strong>.',
            '<strong>Nadie más puede verla</strong>: ni esta web, ni quien la mantiene, ni otras personas. Solo se accede a esa carpeta oculta, nunca a tus archivos.',
            'Es <strong>gratis</strong> y no hay que instalar nada. Necesitas una cuenta de Google (la de Gmail).'
        ]));
        c.appendChild(el('h4', null, 'Pasos'));
        c.appendChild(lista('ol', [
            'Pulsa <strong>«Continuar»</strong>. Se abrirá una ventana de Google.',
            'Elige tu cuenta de Google (o inicia sesión si te lo pide).',
            'Google te pedirá permiso para «ver y gestionar sus propios datos de configuración en tu Google Drive». Pulsa <strong>«Permitir»</strong> o «Continuar». Es la carpeta oculta de esta web.',
            'Espera unos segundos: verás el mensaje <strong>«Sincronizado»</strong> con lo que se ha añadido.',
            'Para usar tus datos en otro dispositivo, abre esta misma página allí, pulsa «Sincronizar» y repite los pasos <strong>con la misma cuenta de Google</strong>. Desde ese momento se sincroniza solo, incluidos los tests a medias, hasta que pulses «Cerrar sesión».'
        ]));
        c.appendChild(el('h4', null, 'Por si acaso'));
        c.appendChild(lista('ul', [
            'Si no se abre la ventana de Google, permite las ventanas emergentes para esta página y vuelve a intentarlo.',
            'Puedes sincronizar cuando quieras para ponerte al día; los datos de los dos dispositivos se <strong>combinan</strong>, no se pierde nada.',
            '<strong>Cada hora, Google corta el acceso</strong> por seguridad. Si pasa, verás un icono de aviso (☁⚠) y la web intentará reconectarse sola; con tu siguiente toque o clic puede verse un instante la ventana de Google. Cuando lo consiga, el icono desaparece. Mientras tanto no pierdes nada: tus datos siguen guardados en el dispositivo y se envían al reconectar.',
            'Para dejar de usarlo: en tu cuenta de Google → Seguridad → «Conexiones con aplicaciones y servicios de terceros» quita «Supuestos C1».'
        ]));
        var etq = el('label', 'sync-no-mas'); var chk = el('input'); chk.type = 'checkbox'; chk.id = 'sync-no-mas';
        etq.appendChild(chk); etq.appendChild(el('span', null, 'No volver a mostrar esta explicación')); c.appendChild(etq);
        ventana('Sincronizar mis datos entre dispositivos', c, [
            { texto: 'Continuar', principal: true, accion: function (f) { if (chk.checked) S.set(K_NO, true); f.remove(); siguiente(); } },
            { texto: 'Cancelar', accion: function (f) { f.remove(); } }
        ], 'sync-explicacion');
    }

    function mensajeError(e) {
        var m = String(e && e.message || e);
        if (/red|Failed to fetch|NetworkError/i.test(m)) return 'No hay conexión con Google. Comprueba tu internet y vuelve a intentarlo.';
        if (/popup_closed|cerrada|access_denied|denegado/i.test(m)) return 'No se completó el permiso de Google. No ha pasado nada: puedes volver a intentarlo cuando quieras.';
        if (/popup_failed_to_open|bloque/i.test(m)) return 'Tu navegador ha bloqueado la ventana de Google. Permite las ventanas emergentes para esta página y vuelve a intentarlo.';
        if (e && e.estado === 403) return 'Google ha rechazado el acceso a la carpeta oculta. Avisa a quien mantiene la web (puede que falte activar Google Drive API).';
        return 'No se ha podido sincronizar. Vuelve a intentarlo en unos minutos. (Detalle: ' + m.slice(0, 80) + ')';
    }
    function ejecutar() {
        var c = el('div', 'sync-texto'); var p = el('p', 'sync-estado', 'Conectando con Google… Sigue las indicaciones de la ventana que se ha abierto.'); c.appendChild(p);
        var f = ventana('Sincronizando…', c, [{ texto: 'Cerrar', accion: function (x) { x.remove(); } }], 'sync-proceso');
        sincronizar(true).then(function (r) {
            S.set(K_SES, { ts: Date.now() }); estado = 'ok';
            f.querySelector('h3').textContent = '✔ Sincronizado';
            var n = r.nov, partes = [];
            if (n.falladas) partes.push(n.falladas + (n.falladas === 1 ? ' pregunta fallada' : ' preguntas falladas'));
            if (n.marcadas) partes.push(n.marcadas + (n.marcadas === 1 ? ' pregunta marcada' : ' preguntas marcadas'));
            if (n.favoritas) partes.push(n.favoritas + (n.favoritas === 1 ? ' favorita' : ' favoritas'));
            if (n.subrayados) partes.push(n.subrayados + (n.subrayados === 1 ? ' subrayado' : ' subrayados'));
            if (n.notas) partes.push(n.notas + (n.notas === 1 ? ' nota' : ' notas'));
            if (n.intentos) partes.push(n.intentos + (n.intentos === 1 ? ' intento' : ' intentos'));
            if (n.cursos) partes.push(n.cursos + (n.cursos === 1 ? ' test a medias' : ' tests a medias'));
            p.textContent = (r.primera ? 'Se ha creado tu copia en Google Drive. ' : '') +
                (partes.length ? 'Se han añadido a este dispositivo: ' + partes.join(', ') + '.' : 'Este dispositivo ya estaba al día.') +
                ' La sesión queda iniciada: a partir de ahora se sincroniza solo, hasta que pulses «Cerrar sesión».';
            if (W.SupC1Estudio) W.SupC1Estudio.repintar();
            pintarTarjeta(); pintarIcono();
        }).catch(function (e) {
            f.querySelector('h3').textContent = 'No se ha podido sincronizar'; p.textContent = mensajeError(e); pintarIcono();
        });
    }
    function empezar() { if (S.get(K_NO, false)) ejecutar(); else explicacion(ejecutar); }

    /* ─── Tarjeta en «Mi estudio» ─── */
    function hace(ts) {
        var m = Math.round((Date.now() - ts) / 60000);
        if (m < 1) return 'ahora mismo'; if (m < 60) return 'hace ' + m + ' min';
        var h = Math.round(m / 60); if (h < 24) return 'hace ' + h + (h === 1 ? ' hora' : ' horas');
        var d = Math.round(h / 24); return 'hace ' + d + (d === 1 ? ' día' : ' días');
    }
    var TEXTO_ESTADO = { ok: 'Sincronizado', sincronizando: 'Sincronizando…', reconectar: 'Sincronización cortada: se reconecta con tu próximo toque', error: 'No se pudo sincronizar (se reintentará)' };
    var ICONO_ESTADO = { ok: '☁✔', sincronizando: '☁⟳', reconectar: '☁⚠', error: '☁⚠' };
    function pintarTarjeta() {
        var cont = $('estudio-sync'); if (!cont) return;
        while (cont.firstChild) cont.removeChild(cont.firstChild);
        var t = el('div', 'sync-tarjeta');
        var txt = el('div', 'sync-info');
        var ult = S.get(K_ULT, null), acc = el('div', 'sync-acciones');
        var ayuda = el('button', 'btn-link', '¿Cómo funciona?'); ayuda.type = 'button'; ayuda.addEventListener('click', function () { explicacion(ejecutar); });
        if (sesion()) {
            t.className = 'sync-tarjeta sync-compacta';
            var e = estado === 'fuera' ? 'ok' : estado;
            var ic = el('strong', 'sync-conectado', ICONO_ESTADO[e] + ' Conectado'); ic.id = 'sync-icono-tarjeta';
            ic.title = TEXTO_ESTADO[e] + (ult ? ' · última vez: ' + hace(ult) : '') + '. Se sincroniza solo, también los tests a medias.';
            txt.appendChild(ic);
            var ahora = el('button', 'btn-link', e === 'reconectar' ? 'Reconectar' : 'Sincronizar ahora'); ahora.type = 'button'; ahora.id = 'sync-ahora';
            ahora.addEventListener('click', function () { if (e === 'reconectar') ejecutar(); else auto(); });
            var salir = el('button', 'btn-practicar', 'Cerrar sesión'); salir.type = 'button'; salir.id = 'sync-salir'; salir.addEventListener('click', cerrarSesion);
            acc.appendChild(salir); acc.appendChild(ahora);
        } else {
            txt.appendChild(el('strong', null, '📱💻 Usar mis datos en todos mis dispositivos'));
            txt.appendChild(el('span', null, 'Sincroniza con tu Google Drive para tener tus notas, tu progreso y tus tests a medias en el móvil y en el ordenador.'));
            var b = el('button', 'btn-practicar', 'Sincronizar'); b.type = 'button'; b.id = 'sync-boton'; b.addEventListener('click', empezar);
            acc.appendChild(b);
        }
        acc.appendChild(ayuda);
        t.appendChild(txt); t.appendChild(acc); cont.appendChild(t);
        pintarBarra();
    }
    // Con la sesión iniciada: el aviso de privacidad pasa a ser un botón junto a «Volver al menú» y el estado de Drive
    // (símbolo + botones) se queda en esa misma fila, a su derecha
    function pintarBarra() {
        var cont = $('estudio-sync'), aviso = doc.querySelector('.aviso-privado'), volver = doc.querySelector('.back-link.boton');
        if (!cont) return;
        var b1 = $('sync-btn-aviso');
        if (!sesion() || !volver) {
            if (b1) b1.remove();
            cont.classList.remove('en-barra'); if (aviso) aviso.hidden = false;
            if (volver && volver.parentNode && cont.previousElementSibling !== aviso && aviso) aviso.insertAdjacentElement('afterend', cont);
            return;
        }
        if (aviso && !b1) {
            b1 = el('button', 'btn-barra', '🔒 Datos solo tuyos'); b1.type = 'button'; b1.id = 'sync-btn-aviso';
            b1.setAttribute('aria-expanded', 'false');
            b1.addEventListener('click', function () { aviso.hidden = !aviso.hidden; b1.setAttribute('aria-expanded', String(!aviso.hidden)); });
            volver.insertAdjacentElement('afterend', b1); aviso.hidden = true;
        }
        if (b1) b1.insertAdjacentElement('afterend', cont); else volver.insertAdjacentElement('afterend', cont);
        cont.classList.add('en-barra');
    }
    // Icono flotante en las páginas que no son «Mi estudio» (ahí ya está la tarjeta)
    function pintarIcono() {
        var ic = $('sync-icono');
        // solo aparece cuando la sincronización se ha cortado; se va sola al volver a conectar
        if (!sesion() || $('estudio-sync') || (estado !== 'reconectar' && estado !== 'error')) { if (ic) ic.remove(); return; }
        if (!ic) {
            ic = el('button', 'sync-icono'); ic.type = 'button'; ic.id = 'sync-icono';
            ic.style.cssText = 'position:fixed;left:10px;bottom:10px;z-index:50;min-width:44px;min-height:44px;border-radius:22px;border:1px solid rgba(0,0,0,.25);background:#fff;color:#222;font-size:14px;cursor:pointer;padding:0 10px;opacity:.9';
            ic.addEventListener('click', function () { if (estado === 'reconectar') ejecutar(); else if (estado !== 'sincronizando') auto(true); });
            doc.body.appendChild(ic);
        }
        var e = estado === 'fuera' ? 'ok' : estado;
        ic.textContent = ICONO_ESTADO[e]; ic.title = 'Google Drive: ' + TEXTO_ESTADO[e] + (e === 'reconectar' ? ' (pulsa para reconectar)' : ''); ic.setAttribute('aria-label', ic.title);
    }
    function iniciar() {
        if (!C.clientId) return;      // apagado
        vigilar(); pintarTarjeta(); pintarIcono();
        if (sesion()) auto();
        var av = doc.querySelector('.aviso-privado span');
        if (av) av.textContent += ' Si activas la sincronización, la copia se guarda en una carpeta oculta de tu propio Google Drive, que solo tú puedes ver.';
    }
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', iniciar); else iniciar();

    nucleo.sincronizar = sincronizar; nucleo.cerrarSesion = cerrarSesion;
    return nucleo;
});

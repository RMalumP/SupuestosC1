/* Página «Impugnaciones»: pestaña «Resueltas» (las que el administrador marca como resueltas en la hoja)
   y pestaña «Foro» (un hilo por impugnación; cada mensaje es una fila de la hoja del foro).
   Todo se lee de la hoja pública; escribir en el foro manda un formulario de Google. */
(function () {
    'use strict';
    var C = window.SUPC1_IMPUG, S = window.SupC1;
    var $ = function (id) { return document.getElementById(id); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
    if (!C || !C.activa) { $('imp-estado').textContent = 'Las impugnaciones no están activadas.'; return; }
    var g = function (f, k) { var v = S.col(f, C.cols[k]); return v == null ? '' : String(v); };
    var imp = [], foro = [], propios = S.get('impug-foro-local', []);

    function mostrar(foroVisible) {
        $('imp-pub').hidden = foroVisible; $('imp-foro').hidden = !foroVisible;
        $('tab-pub').setAttribute('aria-selected', String(!foroVisible)); $('tab-foro').setAttribute('aria-selected', String(foroVisible));
    }
    $('tab-pub').addEventListener('click', function () { mostrar(false); });
    $('tab-foro').addEventListener('click', function () { mostrar(true); });
    $('imp-actualizar').addEventListener('click', cargar);

    function autor(f) {
        var n = g(f, 'nombre').trim();
        return (S.esSi(S.col(f, C.cols.publico)) && n && n !== C.anonimo) ? n : 'Anónimo';
    }
    function tarjeta(f) {
        var c = el('div', 'item');
        c.appendChild(el('p', 'imp-meta', g(f, 'supuesto') + (g(f, 'pregunta') ? ' · pregunta ' + g(f, 'pregunta') : '') + ' · ' + autor(f)));
        c.appendChild(el('p', 'item-texto', g(f, 'texto')));
        if (g(f, 'respuesta')) c.appendChild(el('p', 'item-nota', '✔ Respuesta: ' + g(f, 'respuesta')));
        return c;
    }
    function resueltas() { return imp.filter(function (f) { return S.esSi(S.col(f, C.cols.resuelta)); }).reverse(); }

    function pintarPub() {
        var cont = $('imp-pub'); vaciar(cont);
        var r = resueltas();
        if (!r.length) { cont.appendChild(el('p', 'grupo-desc vacio', 'Todavía no hay impugnaciones resueltas.')); return; }
        r.forEach(function (f) { cont.appendChild(tarjeta(f)); });
    }

    function mensajesDe(id) {
        var ms = foro.filter(function (f) { return g(f, 'foroHilo') === id; }).map(function (f) { return { n: g(f, 'foroNombre') || 'Anónimo', m: g(f, 'foroMensaje'), c: S.esSi(S.col(f, C.cols.foroCerrado)) }; });
        propios.filter(function (p) { return p.hilo === id && !ms.some(function (x) { return x.m === p.m; }); }).forEach(function (p) { ms.push({ n: p.n, m: p.m, local: true }); });
        return ms;
    }
    function pintarForo() {
        var cont = $('imp-foro'); vaciar(cont);
        var r = resueltas();
        if (!r.length) { cont.appendChild(el('p', 'grupo-desc vacio', 'El foro se abre cuando una impugnación se resuelve.')); return; }
        r.forEach(function (f) {
            var id = g(f, 'id'), ms = id ? mensajesDe(id) : [];
            var cerrado = S.esSi(S.col(f, C.cols.cerrado)) || ms.some(function (x) { return x.c; });
            var h = el('div', 'imp-hilo'); h.appendChild(tarjeta(f));
            ms.forEach(function (x) {
                var d = el('div', 'imp-msg'); d.appendChild(el('b', null, x.n + (x.local ? ' (enviado, pendiente de aparecer)' : ''))); d.appendChild(el('div', null, x.m)); h.appendChild(d);
            });
            if (cerrado) h.appendChild(el('p', 'imp-meta', '🔒 Hilo cerrado'));
            else if (C.foroUrl && id) h.appendChild(formulario(id));
            else h.appendChild(el('p', 'imp-meta', 'Responder no está disponible todavía.'));
            cont.appendChild(h);
        });
    }
    function formulario(id) {
        var f = el('form', 'imp-form');
        var n = el('input'); n.type = 'text'; n.placeholder = 'Nombre (déjalo vacío para ir como Anónimo)'; n.value = S.get('impug-nombre', ''); n.setAttribute('aria-label', 'Nombre');
        var t = el('textarea'); t.rows = 3; t.placeholder = 'Escribe tu aportación…'; t.setAttribute('aria-label', 'Mensaje');
        var b = el('button', null, 'Enviar al foro'); b.type = 'submit';
        f.appendChild(n); f.appendChild(t); f.appendChild(b);
        f.addEventListener('submit', function (e) {
            e.preventDefault();
            var m = t.value.trim(); if (!m) return;
            var nom = n.value.trim() || C.anonimo || 'Anónimo', c = C.foroCampos || {}, body = new URLSearchParams();
            if (c.hilo) body.append(c.hilo, id); if (c.nombre) body.append(c.nombre, nom); if (c.mensaje) body.append(c.mensaje, m);
            b.disabled = true;
            fetch(C.foroUrl, { method: 'POST', mode: 'no-cors', body: body }).then(function () {
                if (n.value.trim()) S.set('impug-nombre', n.value.trim());
                propios.push({ hilo: id, n: nom, m: m }); S.set('impug-foro-local', propios.slice(-50)); pintarForo();
            }).catch(function () { b.disabled = false; alert('No se pudo enviar. Revisa la conexión e inténtalo de nuevo.'); });
        });
        return f;
    }

    function cargar() {
        var est = $('imp-estado'); est.textContent = 'Cargando…';
        S.leerHoja(C.sheetId, C.hojaImpugnaciones, function (filas) {
            imp = filas;
            S.leerHoja(C.sheetId, C.hojaForo, function (f2) { foro = f2; fin(); }, function () { foro = []; fin('No se pudo leer el foro.'); });
        }, function () { est.textContent = 'No se pudo leer la hoja. Comprueba la conexión y que la hoja sea pública.'; });
    }
    function fin(aviso) { $('imp-estado').textContent = aviso || ''; pintarPub(); pintarForo(); }
    cargar();
})();

/* Página «Impugnaciones»: pestaña «Resueltas» (las que el administrador marca como resueltas en la hoja)
   y pestaña «Foro» (un hilo por impugnación = una Issue de GitHub).
   Las resueltas se leen de la hoja pública; el foro, de la API pública de GitHub; escribir pasa por un Apps Script. */
(function () {
    'use strict';
    var C = window.SUPC1_IMPUG, S = window.SupC1;
    var $ = function (id) { return document.getElementById(id); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }
    if (!C || !C.activa) { $('imp-estado').textContent = 'Las impugnaciones no están activadas.'; return; }
    var g = function (f, k) { var v = S.col(f, C.cols[k]); return v == null ? '' : String(v); };
    var imp = [], foro = {}, propios = S.get('impug-foro-local', []);
    // Los mensajes que acabas de enviar se enseñan unos minutos mientras GitHub los devuelve; después solo vale lo que hay en GitHub
    // (si no, un comentario borrado allí seguiría viéndose aquí).
    function podarPropios() { var l = Date.now() - 180000; propios = propios.filter(function (p) { return (p.t || 0) > l; }); S.set('impug-foro-local', propios); }
    podarPropios();

    function mostrar(foroVisible) {
        $('imp-pub').hidden = foroVisible; $('imp-foro').hidden = !foroVisible;
        $('tab-pub').setAttribute('aria-selected', String(!foroVisible)); $('tab-foro').setAttribute('aria-selected', String(foroVisible));
    }
    $('tab-pub').addEventListener('click', function () { mostrar(false); });
    $('tab-foro').addEventListener('click', function () { mostrar(true); });
    $('imp-actualizar').addEventListener('click', cargar);

    // Identificador del hilo: la columna ID o, en las impugnaciones antiguas sin ID, uno estable sacado de la fecha y el texto
    function idDe(f) { var i = g(f, 'id').trim(); return /^[A-Za-z0-9]{6,40}$/.test(i) ? i : 'F' + S.huella(g(f, 'fecha') + '|' + g(f, 'texto')); }
    function autor(f) {
        var n = g(f, 'nombre').trim();
        return (S.esSi(S.col(f, C.cols.publico)) && n && n !== C.anonimo) ? n : 'Anónimo';
    }
    function detalle(f) {
        var p = S.parsePregunta(g(f, 'pregunta'));
        return { sup: g(f, 'supuesto'), n: p.n, q: p.q, ops: p.ops, correcta: g(f, 'correcta'), marcada: g(f, 'marcada'), texto: g(f, 'texto'),
                 autor: autor(f), resp: g(f, 'respuesta'), estado: S.esSi(S.col(f, C.cols.resuelta)) ? 'Resuelta' : 'Pendiente' };
    }
    function tarjeta(f) {
        var c = el('div', 'item'), p = S.parsePregunta(g(f, 'pregunta'));
        c.appendChild(el('p', 'imp-meta', g(f, 'supuesto') + (p.n ? ' · pregunta ' + p.n : '') + ' · ' + autor(f)));
        if (p.q) c.appendChild(el('p', 'imp-preg', p.q.length > 180 ? p.q.slice(0, 177) + '…' : p.q));
        c.appendChild(el('p', 'item-texto', g(f, 'texto')));
        if (g(f, 'respuesta')) c.appendChild(el('p', 'item-nota', '✔ Respuesta: ' + g(f, 'respuesta')));
        else if (!S.esSi(S.col(f, C.cols.resuelta))) c.appendChild(el('p', 'imp-meta', '⏳ Pendiente de respuesta'));
        var v = el('button', 'btn-link', 'Ver pregunta completa y respuestas'); v.type = 'button';
        v.addEventListener('click', function () { S.detalleImpug(detalle(f)); });
        c.appendChild(v);
        return c;
    }
    // El foro incluye también las marcadas como «Publicar», aunque aún no estén resueltas
    function delForo() { return imp.filter(function (f) { return S.esSi(S.col(f, C.cols.resuelta)) || S.esSi(S.col(f, C.cols.publico)); }).reverse(); }
    function resueltas() { return imp.filter(function (f) { return S.esSi(S.col(f, C.cols.resuelta)); }).reverse(); }

    function pintarPub() {
        var cont = $('imp-pub'); vaciar(cont);
        var r = resueltas();
        if (!r.length) { cont.appendChild(el('p', 'grupo-desc vacio', 'Todavía no hay impugnaciones resueltas.')); return; }
        r.forEach(function (f) { cont.appendChild(tarjeta(f)); });
    }

    // Hilos del foro = Issues de GitHub con la etiqueta del foro; el ID de la impugnación va en el título: «[ID] …»
    function api(ruta, pagina, acum) {
        pagina = pagina || 1; acum = acum || [];
        return fetch('https://api.github.com/repos/' + C.repo + ruta + (ruta.indexOf('?') < 0 ? '?' : '&') + 'per_page=100&page=' + pagina, { headers: { Accept: 'application/vnd.github+json' } })
            .then(function (r) { if (!r.ok) throw new Error('github ' + r.status); return r.json(); })
            .then(function (j) { acum = acum.concat(j); return (j.length === 100 && pagina < 5) ? api(ruta, pagina + 1, acum) : acum; });
    }
    // Un comentario crudo ({b: cuerpo, u: autor, t: ISO}) → mensaje del foro.
    // Los mensajes de la web los publica el script con la cuenta del administrador y empiezan por «**Nombre**»;
    // los comentarios escritos a mano en GitHub (sin ese encabezado) son los del administrador.
    function aMensaje(b, u, fecha) {
        var m = /^\*\*([^\n]*?)\*\*\n\n([\s\S]*)$/.exec(b || ''), t = Date.parse(fecha) || 0;
        var admin = !m && u && u.toLowerCase() === C.repo.split('/')[0].toLowerCase();
        return admin ? { n: 'Administrador', m: b || '', admin: true, t: t } : m ? { n: m[1] || 'Anónimo', m: m[2], t: t } : { n: u || 'GitHub', m: b || '', t: t };
    }
    // Lectura rápida: el Apps Script devuelve todos los hilos de una vez (caché de 10 s, sin el límite de GitHub).
    function cargarForoScript() {
        if (!C.foroScriptUrl) return Promise.reject(new Error('sin script'));
        return fetch(C.foroScriptUrl + (C.foroScriptUrl.indexOf('?') < 0 ? '?' : '&') + 'accion=foro&_=' + Math.floor(Date.now() / 10000))
            .then(function (r) { return r.json(); })
            .then(function (j) {
                if (!j || !j.ok || !j.hilos) throw new Error('script');
                var nuevo = {};
                Object.keys(j.hilos).forEach(function (id) {
                    var h = j.hilos[id]; nuevo[id] = { cerrado: !!h.cerrado, msgs: (h.msgs || []).map(function (x) { return aMensaje(x.b, x.u, x.t); }) };
                });
                foro = nuevo;
            });
    }
    // Respaldo: la API pública de GitHub (más lenta y con límite de consultas)
    function cargarForoGithub() {
        return api('/issues?state=all&labels=' + encodeURIComponent(C.etiquetaForo)).then(function (issues) {
            var porNum = {}, nuevo = {};
            issues.forEach(function (i) {
                var m = /^\[([A-Za-z0-9]+)\]/.exec(i.title || '');
                if (m && !i.pull_request) { nuevo[m[1]] = { cerrado: i.state === 'closed' || !!i.locked, msgs: [] }; porNum[i.number] = nuevo[m[1]]; }
            });
            return api('/issues/comments?sort=created&direction=asc').then(function (cs) {
                cs.forEach(function (c) {
                    var n = /\/issues\/(\d+)$/.exec(c.issue_url || ''), h = n && porNum[n[1]]; if (!h) return;
                    h.msgs.push(aMensaje(c.body, c.user && c.user.login, c.created_at));
                });
                foro = nuevo;
            });
        });
    }
    function cargarForo(ok, ko) { cargarForoScript().catch(cargarForoGithub).then(ok, ko); }
    function mensajesDe(id) {
        var h = foro[id], ms = h ? h.msgs.slice() : [];
        ms.sort(function (a, b) { return (a.t || 0) - (b.t || 0); });
        propios.filter(function (p) { return p.hilo === id && !ms.some(function (x) { return x.m === p.m; }); }).forEach(function (p) { ms.push({ n: p.n, m: p.m, local: true, t: p.t, fallo: !!p.fallo, ok: !!p.ok, p: p }); });
        return ms;
    }
    function pintarForo() {
        var cont = $('imp-foro'); vaciar(cont);
        var r = delForo();
        if (!r.length) { cont.appendChild(el('p', 'grupo-desc vacio', 'El foro se abre cuando una impugnación se resuelve o se marca como «Publicar».')); return; }
        r.forEach(function (f) {
            var id = idDe(f), h = el('div', 'imp-hilo'); h.id = 'hilo-' + id; h.appendChild(tarjeta(f));
            var lista = el('div', 'imp-msgs'); lista.id = 'msgs-' + id; h.appendChild(lista);
            var cerrado = S.esSi(S.col(f, C.cols.cerrado)) || !!(foro[id] && foro[id].cerrado);
            if (cerrado) h.appendChild(el('p', 'imp-meta', '🔒 Hilo cerrado'));
            else if (C.foroScriptUrl && id) h.appendChild(formulario(id, f));
            else h.appendChild(el('p', 'imp-meta', 'Responder no está disponible todavía.'));
            cont.appendChild(h);
            pintarMsgs(id);
        });
    }
    // Solo repinta los mensajes de un hilo (así no se pierde lo que se está escribiendo en los demás)
    function pintarMsgs(id) {
        var lista = $('msgs-' + id); if (!lista) return; vaciar(lista);
        mensajesDe(id).forEach(function (x) {
            var d = el('div', 'imp-msg' + (x.local ? ' imp-pend' : ''));
            var cab = x.n + (x.t && !x.local ? ' · ' + new Date(x.t).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'short' }) : '') + (x.local ? (x.fallo ? ' · no se pudo enviar' : x.ok ? ' · enviado ✔' : ' · enviando…') : '');
            d.appendChild(el('b', null, cab)); d.appendChild(el('div', null, x.m));
            if (x.fallo) { var r = el('button', 'btn-link', 'Reintentar'); r.type = 'button'; r.addEventListener('click', function () { enviarMsg(x.p); }); d.appendChild(r); }
            lista.appendChild(d);
        });
    }
    function enviarMsg(p, fin) {
        p.fallo = false; p.enviando = true; pintarMsgs(p.hilo);
        fetch(C.foroScriptUrl, { method: 'POST', headers: { 'Content-Type': 'text/plain;charset=utf-8' }, body: JSON.stringify({ hilo: p.hilo, titulo: p.titulo, nombre: p.n, mensaje: p.m, web: p.web || '' }) })
            .then(function (r) { return r.json(); })
            .then(function (j) { if (!j || !j.ok) throw new Error((j && j.error) || 'error'); p.t = Date.now(); delete p.enviando; p.ok = true; S.set('impug-foro-local', propios); pintarMsgs(p.hilo); refrescarMsgs(); })
            .catch(function (err) {
                p.fallo = true; delete p.enviando; S.set('impug-foro-local', propios); pintarMsgs(p.hilo);
                if (String(err && err.message) === 'limite') alert('Hay demasiados mensajes ahora mismo. Inténtalo más tarde.');
            })
            .then(function () { if (fin) fin(); });
    }
    function formulario(id, fila) {
        var f = el('form', 'imp-form');
        var n = el('input'); n.type = 'text'; n.maxLength = 40; n.placeholder = 'Nombre (déjalo vacío para ir como Anónimo)'; n.value = S.get('impug-nombre', ''); n.setAttribute('aria-label', 'Nombre');
        var t = el('textarea'); t.rows = 3; t.maxLength = 1500; t.placeholder = 'Escribe tu aportación…'; t.setAttribute('aria-label', 'Mensaje');
        var hp = el('input'); hp.type = 'text'; hp.name = 'web'; hp.tabIndex = -1; hp.autocomplete = 'off'; hp.setAttribute('aria-hidden', 'true'); hp.style.cssText = 'position:absolute;left:-9999px;height:0;opacity:0';   // trampa para robots
        var b = el('button', null, 'Enviar al foro'); b.type = 'submit';
        f.appendChild(n); f.appendChild(t); f.appendChild(hp); f.appendChild(b);
        f.addEventListener('submit', function (e) {
            e.preventDefault();
            var m = t.value.trim(); if (!m || b.disabled) return;
            var nom = n.value.trim() || C.anonimo || 'Anónimo';
            var titulo = '[' + id + '] ' + g(fila, 'supuesto') + (S.parsePregunta(g(fila, 'pregunta')).n ? ' · pregunta ' + S.parsePregunta(g(fila, 'pregunta')).n : '');
            if (n.value.trim()) S.set('impug-nombre', n.value.trim());
            // El mensaje aparece al instante; el envío real sigue en segundo plano y el botón se bloquea unos segundos (evita duplicados)
            var p = { hilo: id, n: nom, m: m, t: Date.now(), titulo: titulo, web: hp.value };
            propios.push(p); S.set('impug-foro-local', propios); t.value = ''; b.disabled = true;
            pintarMsgs(id);
            enviarMsg(p, function () { b.disabled = false; });
        });
        return f;
    }

    function cargar() {
        podarPropios();
        var est = $('imp-estado'); est.textContent = 'Cargando…';
        S.leerHoja(C.sheetId, C.hojaImpugnaciones, function (filas) {
            imp = filas;
            cargarForo(function () { fin(); }, function () { foro = {}; fin('No se pudo leer el foro de GitHub (puede que haya demasiadas consultas; prueba más tarde).'); });
        }, function () { est.textContent = 'No se pudo leer la hoja. Comprueba la conexión y que la hoja sea pública.'; });
    }
    // Refresco automático mientras la pestaña del foro está a la vista (solo se repintan los mensajes, no los formularios)
    function refrescarMsgs() {
        if (document.hidden || $('imp-foro').hidden) return;
        cargarForoScript().then(function () { podarPropios(); delForo().forEach(function (f) { pintarMsgs(idDe(f)); }); }).catch(function () { /* sin red: se intenta en el siguiente turno */ });
    }
    setInterval(refrescarMsgs, 15000);
    document.addEventListener('visibilitychange', function () { if (!document.hidden) refrescarMsgs(); });
    function fin(aviso) { $('imp-estado').textContent = aviso || ''; pintarPub(); pintarForo(); }
    cargar();
})();

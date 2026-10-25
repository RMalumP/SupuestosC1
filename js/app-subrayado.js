/* Subrayar: selecciona un trozo del enunciado, de la pregunta o de una respuesta y elige un color.
   Los subrayados se guardan en este navegador (dentro del banco personal, igual que las notas),
   se sincronizan con Google Drive si se activa, se ven en los supuestos y en «Mi estudio»
   (donde también se pueden subrayar las preguntas guardadas).

   · Se puede apagar en un supuesto (config.subrayar:false en el editor) o desde el panel ⚙.
   · Cada subrayado se guarda como «zona + trozo de texto + un poco de contexto». Así sigue
     funcionando aunque se barajen las respuestas, y si el texto cambia se ignora sin romper nada.
   Datos: banco.subrayados[clave] = { z: zona, f: supuesto, x: texto, pre: contexto, c: color, qt: pregunta, ts }
   Borrar deja una «lápida» banco.borradas['u:' + clave] para que no resucite al sincronizar. */
(function () {
    'use strict';
    var S = window.SupC1;
    if (!S || !document.body) return;

    var COLORES = [['Amarillo', 'c0'], ['Verde', 'c1'], ['Rosa', 'c2'], ['Azul', 'c3'], ['Naranja', 'c4']];
    var $ = function (id) { return document.getElementById(id); };
    var compacto = function (t) { return String(t || '').replace(/\s+/g, ''); };
    var version = 1, aplicando = false, pop = null, temporizador = null, observador = null;

    /* ── Interruptores ── */
    function disponible() { return !(typeof EXAM_CONFIG !== 'undefined' && EXAM_CONFIG && EXAM_CONFIG.subrayar === false); }
    function activo() { return disponible() && S.get('subrayar', true) !== false; }
    function aplicarInterruptor() { document.documentElement.classList.toggle('sin-subrayado', !activo()); }

    /* ── Datos ── */
    function leer() {
        var b = S.get('banco', null) || {};
        b.subrayados = b.subrayados || {}; b.borradas = b.borradas || {};
        return b;
    }
    function guardar(b) { S.set('banco', b); version++; }
    function huella(t) { return S.sup && S.sup.huella ? S.sup.huella(t) : String(t.length); }
    function delZona(b, z) {
        var r = [];
        Object.keys(b.subrayados).forEach(function (k) { if (b.subrayados[k].z === z) r.push(k); });
        return r;
    }
    // Posición (en caracteres sin espacios) de un subrayado dentro del texto compacto de su zona
    function rangoDe(h, C) {
        var cx = compacto(h.x); if (!cx) return null;
        var pre = h.pre || '', hallado = null, i = C.indexOf(cx);
        while (i !== -1) {
            if (hallado === null) hallado = i;
            if (!pre || C.slice(Math.max(0, i - pre.length), i) === pre) return [i, i + cx.length];
            i = C.indexOf(cx, i + 1);
        }
        return hallado === null ? null : [hallado, hallado + cx.length];
    }

    /* ── Zonas subrayables ── */
    // Se les pone data-sz (id de la zona), data-sf (supuesto) y data-sqt (pregunta, para mostrarla en «Mi estudio»).
    function marcarZonas() {
        if (!S.sup || typeof questions === 'undefined') return;
        document.querySelectorAll('.question-card').forEach(function (card) {
            var i = parseInt(card.id.replace('qcard-', ''), 10), q = questions[i];
            if (isNaN(i) || !q) return;
            var k = S.sup.clave(q), qt = S.sup.corto(q).slice(0, 90);
            function poner(el, z) {
                if (!el || el.dataset.sz === z) return;
                el.dataset.sz = z; el.dataset.sf = S.sup.id; el.dataset.sqt = qt; delete el.dataset.szok;
            }
            poner(card.querySelector('.q-text'), k + '#q');
            card.querySelectorAll('.option').forEach(function (o) {
                var sp = o.querySelector('span:last-child');
                if (sp && !sp.classList.contains('opt-letter')) poner(sp, k + '#o:' + huella(compacto(sp.textContent)));
            });
        });
        document.querySelectorAll('.fact-block').forEach(function (fb) {
            var z = S.sup.id + '#e:' + huella(compacto(fb.textContent));
            if (fb.dataset.sz !== z) { fb.dataset.sz = z; fb.dataset.sf = S.sup.id; fb.dataset.sqt = ''; delete fb.dataset.szok; }
        });
    }

    /* ── Dibujar los subrayados de una zona ── */
    function nodosDeTexto(raiz) {
        var w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT, null), n, lista = [];
        while ((n = w.nextNode())) lista.push(n);
        return lista;
    }
    function quitarMarcas(el) {
        el.querySelectorAll('mark.subr').forEach(function (m) {
            var padre = m.parentNode; while (m.firstChild) padre.insertBefore(m.firstChild, m); padre.removeChild(m);
        });
        el.normalize();
    }
    // Índice de carácter dentro de «texto» del carácter número «n» (contando solo los que no son espacio)
    function posCaracter(texto, n) {
        var c = 0;
        for (var i = 0; i < texto.length; i++) { if (/\S/.test(texto.charAt(i))) { if (c === n) return i; c++; } }
        return texto.length;
    }
    function envolver(el, s, e, clase, clave) {
        var nodos = nodosDeTexto(el), acum = 0, trozos = [];
        nodos.forEach(function (n) {
            var t = n.nodeValue, cuenta = compacto(t).length, ini = acum, fin = acum + cuenta;
            acum = fin;
            if (!cuenta || fin <= s || ini >= e) return;
            var a = Math.max(s, ini) - ini, b = Math.min(e, fin) - ini;      // en caracteres no-espacio dentro de este nodo
            trozos.push([n, posCaracter(t, a), posCaracter(t, b - 1) + 1]);
        });
        trozos.reverse().forEach(function (tr) {
            var r = document.createRange(); r.setStart(tr[0], tr[1]); r.setEnd(tr[0], tr[2]);
            var m = document.createElement('mark'); m.className = 'subr subr-' + clase; m.dataset.k = clave;
            r.surroundContents(m);
        });
    }
    function pintarZona(el, b) {
        quitarMarcas(el);
        var C = compacto(el.textContent), usados = [];
        delZona(b, el.dataset.sz).map(function (k) { return [k, rangoDe(b.subrayados[k], C)]; })
            .filter(function (p) { return p[1]; }).sort(function (x, y) { return x[1][0] - y[1][0]; })
            .forEach(function (p) {
                var r = p[1];
                if (usados.some(function (u) { return r[0] < u[1] && r[1] > u[0]; })) return;   // solapados: se dibuja el primero
                usados.push(r); envolver(el, r[0], r[1], b.subrayados[p[0]].c || 'c0', p[0]);
            });
        el.dataset.szok = version;
    }
    function aplicar() {
        if (aplicando) return;
        aplicando = true; if (observador) observador.disconnect();
        try {
            marcarZonas();
            var b = null;
            document.querySelectorAll('[data-sz]').forEach(function (el) {
                if (el.dataset.szok === String(version)) return;
                b = b || leer(); pintarZona(el, b);
            });
        } finally { aplicando = false; if (observador) observar(); }
    }
    function observar() { observador.observe(document.body, { childList: true, subtree: true }); }
    function pronto() { clearTimeout(temporizador); temporizador = setTimeout(aplicar, 120); }

    /* ── Ventana de colores ── */
    function cerrarPop() { if (pop) { pop.remove(); pop = null; } }
    function abrirPop(rect, opciones) {
        cerrarPop();
        var d = document.createElement('div');
        d.className = 'subr-pop'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', 'Subrayar');
        var ultimo = S.get('subr-color', 'c0');
        COLORES.forEach(function (c) {
            var b = document.createElement('button');
            b.type = 'button'; b.className = 'subr-punto subr-' + c[1] + (opciones.actual === c[1] || (!opciones.actual && ultimo === c[1]) ? ' on' : '');
            b.setAttribute('aria-label', 'Subrayar en ' + c[0].toLowerCase()); b.title = c[0];
            b.addEventListener('mousedown', function (e) { e.preventDefault(); });          // no perder la selección
            b.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); S.set('subr-color', c[1]); opciones.elegir(c[1]); cerrarPop(); });
            d.appendChild(b);
        });
        if (opciones.quitar) {
            var q = document.createElement('button');
            q.type = 'button'; q.className = 'subr-quitar'; q.textContent = 'Quitar'; q.title = 'Quitar el subrayado';
            q.addEventListener('mousedown', function (e) { e.preventDefault(); });
            q.addEventListener('click', function (e) { e.preventDefault(); e.stopPropagation(); opciones.quitar(); cerrarPop(); });
            d.appendChild(q);
        }
        document.body.appendChild(d);
        var w = d.offsetWidth, h = d.offsetHeight;
        var x = Math.min(Math.max(8, rect.left + rect.width / 2 - w / 2), window.innerWidth - w - 8);
        var y = rect.bottom + 10; if (y + h > window.innerHeight - 8) y = rect.top - h - 10;
        y = Math.min(Math.max(8, y), window.innerHeight - h - 8);
        d.style.left = x + 'px'; d.style.top = y + 'px';
        pop = d;
    }

    /* ── Crear, recolorear y quitar ── */
    function zonaDe(nodo) {
        var e = nodo && (nodo.nodeType === 1 ? nodo : nodo.parentElement);
        return e && e.closest ? e.closest('[data-sz]') : null;
    }
    function subrayarSeleccion(zona, rango, color) {
        var C = compacto(zona.textContent);
        var antes = document.createRange(); antes.selectNodeContents(zona); antes.setEnd(rango.startContainer, rango.startOffset);
        var s = compacto(antes.toString()).length, cx = compacto(rango.toString()), e = s + cx.length;
        if (!cx) return;
        var b = leer(), ahora = Date.now();
        delZona(b, zona.dataset.sz).forEach(function (k) {          // lo que se solape con lo nuevo se sustituye
            var r = rangoDe(b.subrayados[k], C);
            if (r && r[0] < e && r[1] > s) { delete b.subrayados[k]; b.borradas['u:' + k] = ahora; }
        });
        var texto = rango.toString().replace(/\s+/g, ' ').trim().slice(0, 240);
        var clave = zona.dataset.sz + '|' + huella(C.slice(Math.max(0, s - 24), s) + '|' + cx);
        b.subrayados[clave] = { z: zona.dataset.sz, f: zona.dataset.sf, x: texto, pre: C.slice(Math.max(0, s - 24), s), c: color, qt: zona.dataset.sqt || '', ts: ahora };
        delete b.borradas['u:' + clave];
        guardar(b); window.getSelection().removeAllRanges(); aplicar(); refrescarEstudio();
    }
    function cambiarColor(clave, color) {
        var b = leer(); if (!b.subrayados[clave]) return;
        b.subrayados[clave].c = color; b.subrayados[clave].ts = Date.now(); guardar(b); aplicar(); refrescarEstudio();
    }
    function quitar(clave) {
        var b = leer(); if (!b.subrayados[clave]) return;
        delete b.subrayados[clave]; b.borradas['u:' + clave] = Date.now(); guardar(b); aplicar(); refrescarEstudio();
    }
    function quitarEnSeleccion(zona, rango) {
        var b = leer(), C = compacto(zona.textContent), s0 = (function () {
            var a = document.createRange(); a.selectNodeContents(zona); a.setEnd(rango.startContainer, rango.startOffset); return compacto(a.toString()).length;
        })(), e0 = s0 + compacto(rango.toString()).length, hay = [];
        delZona(b, zona.dataset.sz).forEach(function (k) { var r = rangoDe(b.subrayados[k], C); if (r && r[0] < e0 && r[1] > s0) hay.push(k); });
        return hay;
    }
    function refrescarEstudio() { if (window.SupC1Estudio && window.SupC1Estudio.repintar) setTimeout(window.SupC1Estudio.repintar, 0); }

    /* ── Selección con ratón o dedo ── */
    function revisarSeleccion() {
        var sel = window.getSelection();
        if (!activo() || !sel || sel.isCollapsed || !sel.rangeCount) { cerrarPop(); return; }
        var r = sel.getRangeAt(0), z = zonaDe(r.startContainer), z2 = zonaDe(r.endContainer);
        if (!z || z !== z2 || !compacto(sel.toString())) { cerrarPop(); return; }
        var rango = r.cloneRange(), solapados = quitarEnSeleccion(z, rango);
        abrirPop(r.getBoundingClientRect(), {
            elegir: function (c) { subrayarSeleccion(z, rango, c); },
            quitar: solapados.length ? function () { solapados.forEach(quitar); window.getSelection().removeAllRanges(); } : null
        });
    }
    document.addEventListener('selectionchange', function () { clearTimeout(revisarSeleccion.t); revisarSeleccion.t = setTimeout(revisarSeleccion, 250); });
    // Un clic en un subrayado (fuera de las respuestas) deja cambiarle el color o quitarlo
    document.addEventListener('click', function (e) {
        var sel = window.getSelection();
        if (activo() && sel && !sel.isCollapsed && e.target.closest && e.target.closest('.option')) { e.stopPropagation(); e.preventDefault(); return; }   // arrastrar para seleccionar no es responder
        var m = e.target.closest && e.target.closest('mark.subr');
        if (m && activo() && !m.closest('.option')) {
            var clave = m.dataset.k, h = leer().subrayados[clave];
            if (h) abrirPop(m.getBoundingClientRect(), { actual: h.c, elegir: function (c) { cambiarColor(clave, c); }, quitar: function () { quitar(clave); } });
        } else if (pop && !e.target.closest('.subr-pop')) { cerrarPop(); }
    }, true);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') cerrarPop(); });

    /* ── Panel ⚙ ── */
    var panel = $('settings-panel');
    if (panel && disponible() && !$('row-subrayar')) {
        var fila = document.createElement('div');
        fila.className = 'settings-row'; fila.id = 'row-subrayar';
        fila.innerHTML = '<div class="settings-check"><label><input type="checkbox" id="subrayar-toggle"><span>Subrayar texto con colores</span></label></div>';
        panel.appendChild(fila);
        var cb = $('subrayar-toggle'); cb.checked = activo();
        cb.addEventListener('change', function () { S.set('subrayar', cb.checked); aplicarInterruptor(); if (!cb.checked) cerrarPop(); });
    }

    /* ── Arranque ── */
    aplicarInterruptor();
    observador = new MutationObserver(function (lista) {
        if (aplicando) return;
        for (var i = 0; i < lista.length; i++) {
            var t = lista[i].target;
            if (t && t.closest && t.closest('.subr-pop, #timer, mark.subr')) continue;
            return pronto();
        }
    });
    observar();
    aplicar();
    window.SupC1Subrayado = { aplicar: aplicar, activo: activo, quitar: quitar, cambiarColor: cambiarColor, COLORES: COLORES };
})();

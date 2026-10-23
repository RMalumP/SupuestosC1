/* «Mi estudio»: estadísticas personales y banco de preguntas falladas, marcadas y
   con nota. Todo sale de lo que los supuestos guardan en este navegador. */
(function () {
    'use strict';
    var S = window.SupC1, D = window.SUPUESTOS_DATOS || {};
    var $ = function (id) { return document.getElementById(id); };
    var fmt = function (n, d) { return Number(n).toLocaleString('es-ES', { maximumFractionDigits: d == null ? 1 : d }); };

    /* archivo → datos del menú */
    var info = {};
    (D.secciones || []).forEach(function (s) { (s.grupos || []).forEach(function (g) { (g.items || []).forEach(function (it) { info[it.archivo] = it; }); }); });
    (D.examenes || []).forEach(function (it) { info[it.archivo] = it; });
    var nombre = function (a) { return info[a] ? info[a].titulo : a; };

    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function vaciar(n) { while (n.firstChild) n.removeChild(n.firstChild); }

    function sparkline(vals) {
        var W = 130, H = 36, p = 4, ns = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H); svg.setAttribute('class', 'spark'); svg.setAttribute('role', 'img');
        svg.setAttribute('aria-label', 'Evolución de tus notas: ' + vals.map(function (v) { return Math.round(v) + '%'; }).join(', '));
        if (vals.length < 2) { var c = document.createElementNS(ns, 'circle'); c.setAttribute('cx', W / 2); c.setAttribute('cy', H / 2); c.setAttribute('r', 4); svg.appendChild(c); return svg; }
        var mn = Math.max(0, Math.min.apply(null, vals) - 5), mx = Math.min(100, Math.max.apply(null, vals) + 5); if (mx - mn < 10) { mn = Math.max(0, mn - 5); mx = mn + 10; }
        var pts = vals.map(function (v, i) { return [p + i * (W - 2 * p) / (vals.length - 1), H - p - ((Math.max(mn, Math.min(mx, v)) - mn) / (mx - mn)) * (H - 2 * p)]; });
        var l = document.createElementNS(ns, 'polyline');
        l.setAttribute('points', pts.map(function (q) { return q[0].toFixed(1) + ',' + q[1].toFixed(1); }).join(' ')); svg.appendChild(l);
        var u = pts[pts.length - 1], c2 = document.createElementNS(ns, 'circle');
        c2.setAttribute('cx', u[0]); c2.setAttribute('cy', u[1]); c2.setAttribute('r', 3.2); svg.appendChild(c2);
        return svg;
    }

    function pintar() {
        var banco = S.get('banco', null) || {}, falladas = banco.falladas || {}, marcadas = banco.marcadas || {}, notas = banco.notas || {};

        /* ── Evolución ── */
        var prog = [];
        Object.keys(info).forEach(function (a) { var p = S.get('prog:' + a, null); if (p && p.mejor) prog.push({ a: a, p: p }); });
        var ultimas = prog.map(function (x) { return x.p.ultima.pct; });
        var res = $('estudio-resumen'); vaciar(res);
        [[prog.length + '/' + Object.keys(info).length, 'supuestos hechos'],
         [prog.reduce(function (s, x) { return s + (x.p.intentos || 0); }, 0), 'intentos en total'],
         [ultimas.length ? Math.round(ultimas.reduce(function (s, v) { return s + v; }, 0) / ultimas.length) + ' %' : '—', 'nota media (último intento)'],
         [Object.keys(falladas).length, 'preguntas por repasar']].forEach(function (d) {
            var c = el('div', 'dato'); c.appendChild(el('strong', null, d[0])); c.appendChild(el('span', null, d[1])); res.appendChild(c);
        });

        var ev = $('estudio-evolucion'); vaciar(ev);
        if (!prog.length) ev.appendChild(el('p', 'grupo-desc vacio', 'Todavía no has completado ningún supuesto. Cuando corrijas el primero, aquí verás cómo evolucionas.'));
        prog.forEach(function (x) {
            var h = (x.p.hist && x.p.hist.length) ? x.p.hist : [x.p.ultima];
            var pcts = h.map(function (r) { return r.pct; });
            var media = pcts.reduce(function (s, v) { return s + v; }, 0) / pcts.length;
            var conTiempo = h.filter(function (r) { return r.seg && r.total; });
            var seg = conTiempo.length ? conTiempo.reduce(function (s, r) { return s + r.seg / r.total; }, 0) / conTiempo.length : 0;
            var tend = pcts.length > 1 ? pcts[pcts.length - 1] - pcts[pcts.length - 2] : 0;
            var c = el('a', 'supuesto-card evo'); c.href = 'supuestos/' + x.a + '.html';
            c.appendChild(el('h2', null, nombre(x.a)));
            c.appendChild(sparkline(pcts));
            var d = el('div', 'desc');
            d.textContent = 'Mejor ' + fmt(x.p.mejor.pct, 0) + ' % · última ' + fmt(x.p.ultima.pct, 0) + ' % · media ' + fmt(media, 0) + ' %' +
                            (seg ? ' · ' + fmt(seg, 0) + ' s por pregunta' : '') + ' · ' + x.p.intentos + (x.p.intentos === 1 ? ' intento' : ' intentos');
            c.appendChild(d);
            if (pcts.length > 1) c.appendChild(el('span', 'chip ' + (tend >= 0 ? 'ok' : 'curso'), (tend >= 0 ? '▲ +' : '▼ ') + fmt(tend, 0) + ' puntos respecto al intento anterior'));
            ev.appendChild(c);
        });

        /* ── Falladas ── */
        var fa = $('estudio-falladas'); vaciar(fa);
        var porArch = {};
        Object.keys(falladas).forEach(function (k) { var f = falladas[k]; (porArch[f.f] = porArch[f.f] || []).push([k, f]); });
        if (!Object.keys(porArch).length) fa.appendChild(el('p', 'grupo-desc vacio', 'No tienes preguntas falladas pendientes. ¡Bien!'));
        Object.keys(porArch).forEach(function (a) {
            var g = grupoCabecera(a, porArch[a].length, 'Practicar falladas', 'supuestos/' + a + '.html?practicar=falladas');
            porArch[a].sort(function (x, y) { return y[1].n - x[1].n; }).forEach(function (par) {
                var li = el('div', 'item');
                li.appendChild(el('p', 'item-texto', par[1].t));
                var m = el('div', 'item-meta');
                m.appendChild(el('span', 'chip', 'fallada ' + par[1].n + (par[1].n === 1 ? ' vez' : ' veces')));
                var q = el('button', 'btn-link', 'Quitar'); q.type = 'button';
                q.addEventListener('click', function () { var b = S.get('banco', {}); delete b.falladas[par[0]]; S.set('banco', b); pintar(); });
                m.appendChild(q); li.appendChild(m); g.appendChild(li);
            });
            fa.appendChild(g);
        });
        if (Object.keys(falladas).length) {
            var v = el('button', 'btn-link peligro', 'Vaciar todas las falladas'); v.type = 'button';
            v.addEventListener('click', function () { if (confirm('¿Borrar todas las preguntas falladas de este navegador?')) { var b = S.get('banco', {}); b.falladas = {}; S.set('banco', b); pintar(); } });
            fa.appendChild(v);
        }

        /* ── Marcadas y notas ── */
        var ma = $('estudio-marcadas'); vaciar(ma);
        var claves = {}; Object.keys(marcadas).concat(Object.keys(notas)).forEach(function (k) { claves[k] = 1; });
        var pa = {};
        Object.keys(claves).forEach(function (k) { var base = marcadas[k] || notas[k]; (pa[base.f] = pa[base.f] || []).push(k); });
        if (!Object.keys(pa).length) ma.appendChild(el('p', 'grupo-desc vacio', 'Aún no has marcado preguntas ni escrito notas. En un supuesto, usa «Marcar para revisar» (o la tecla M) y «Añadir nota» (tecla N).'));
        Object.keys(pa).forEach(function (a) {
            var nMarc = pa[a].filter(function (k) { return marcadas[k]; }).length;
            var g = grupoCabecera(a, pa[a].length, nMarc ? 'Practicar marcadas' : null, 'supuestos/' + a + '.html?practicar=marcadas');
            pa[a].forEach(function (k) {
                var base = marcadas[k] || notas[k], li = el('div', 'item');
                li.appendChild(el('p', 'item-texto', (marcadas[k] ? '🚩 ' : '') + base.t));
                if (notas[k]) li.appendChild(el('p', 'item-nota', '📝 ' + notas[k].txt));
                var m = el('div', 'item-meta');
                if (marcadas[k]) { var q = el('button', 'btn-link', 'Quitar marca'); q.type = 'button'; q.addEventListener('click', function () { var b = S.get('banco', {}); delete b.marcadas[k]; S.set('banco', b); pintar(); }); m.appendChild(q); }
                if (notas[k]) { var n = el('button', 'btn-link', 'Borrar nota'); n.type = 'button'; n.addEventListener('click', function () { if (confirm('¿Borrar esta nota?')) { var b = S.get('banco', {}); delete b.notas[k]; S.set('banco', b); pintar(); } }); m.appendChild(n); }
                li.appendChild(m); g.appendChild(li);
            });
            ma.appendChild(g);
        });
    }

    function grupoCabecera(arch, n, textoBoton, href) {
        var g = el('section', 'grupo-estudio');
        var cab = el('div', 'grupo-estudio-cab');
        cab.appendChild(el('h3', null, nombre(arch)));
        cab.appendChild(el('span', 'contador', n + (n === 1 ? ' pregunta' : ' preguntas')));
        if (textoBoton) { var a = el('a', 'btn-practicar', textoBoton + ' (' + n + ')'); a.href = href; cab.appendChild(a); }
        g.appendChild(cab); return g;
    }
    pintar();
})();

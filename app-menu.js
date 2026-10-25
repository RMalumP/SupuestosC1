/* Menú principal y resultados: pinta la lista desde supuestos-datos.js,
   muestra tu progreso (lo guardan los supuestos en este navegador),
   buscador, filtros y el interruptor de tema oscuro. */
(function () {
    'use strict';
    var S = window.SupC1;
    var D = window.SUPUESTOS_DATOS;
    var $ = function (id) { return document.getElementById(id); };
    var fmt = function (n) { return Number(n).toLocaleString('es-ES', { maximumFractionDigits: 2 }); };

    /* ── Interruptor de tema (flotante) ── */
    function botonTema() {
        var b = document.createElement('button');
        b.className = 'btn-tema'; b.type = 'button'; b.setAttribute('aria-label', 'Cambiar entre tema claro y oscuro');
        var pintar = function () {
            var o = document.documentElement.getAttribute('data-tema') === 'oscuro';
            b.textContent = o ? '☀️' : '🌙'; b.title = o ? 'Tema claro' : 'Tema oscuro';
        };
        b.addEventListener('click', function () {
            S.setTema(document.documentElement.getAttribute('data-tema') !== 'oscuro'); pintar();
        });
        pintar(); document.body.appendChild(b);
    }
    botonTema();

    /* ── Aviso de datos anónimos: una línea al final del menú (solo si está activado) ── */
    var T = window.SUPC1_TELEMETRIA;
    if (T && T.activa && T.url && T.aviso) {
        var pieAviso = document.querySelector('footer');
        if (pieAviso) {
            var linea = document.createElement('span');
            linea.className = 'aviso-pie'; linea.textContent = T.aviso;
            pieAviso.appendChild(linea);
        }
    }
    // Entrar una vez con «index.html#admin» deja visible, solo en ese navegador, un
    // enlace discreto al panel privado. No es una protección (el código es público):
    // lo que protege los datos es que el panel exige tu cuenta de Google.
    if (location.hash === '#admin') { S.set('admin', true); history.replaceState(null, '', location.pathname + location.search); }
    if (T && T.adminUrl && S.get('admin', false)) {
        var pie = document.querySelector('footer');
        if (pie) {
            var enl = document.createElement('a');
            enl.href = T.adminUrl; enl.target = '_blank'; enl.rel = 'noopener'; enl.className = 'enlace-admin'; enl.textContent = ' · admin';
            pie.appendChild(enl);
        }
    }

    if (!D || !$('menu-supuestos')) return;

    /* ── Estado de cada supuesto ── */
    function estado(arch) {
        var p = S.get('prog:' + arch, null), c = S.get('curso:' + arch, null);
        var enCurso = c && c.v === 1 && Date.now() - c.ts < 3 * 24 * 3600 * 1000;
        if (enCurso) return { clave: 'curso', c: c, p: p };
        if (p && p.mejor) return { clave: 'hecho', p: p };
        return { clave: 'nuevo' };
    }

    function tarjeta(it) {
        var e = estado(it.archivo);
        var a = document.createElement('a');
        a.className = 'supuesto-card'; a.href = 'supuestos/' + it.archivo + '.html';
        a.dataset.estado = e.clave;
        a.innerHTML = '<div class="exp-number"></div><h2></h2><span class="ref"></span><div class="desc"></div><div class="prog"></div><div class="go"></div>';
        a.querySelector('.exp-number').textContent = it.letra;
        a.querySelector('.ref').textContent = 'REF: ' + it.ref;
        a.querySelector('h2').textContent = it.titulo;
        a.querySelector('.desc').textContent = it.desc;
        var prog = a.querySelector('.prog'), go = a.querySelector('.go');
        if (e.clave === 'hecho') {
            var m = e.p.mejor;
            prog.innerHTML = '<span class="chip ok">✔ Mejor: ' + fmt(m.puntos) + '/' + fmt(m.max) + ' · ' + Math.round(m.pct) + ' %</span>' +
                             '<span class="chip">' + e.p.intentos + (e.p.intentos === 1 ? ' intento' : ' intentos') + '</span>';
            go.textContent = 'Repetir →';
        } else if (e.clave === 'curso') {
            prog.innerHTML = '<span class="chip curso">⏸ En curso · ' + Object.keys(e.c.a).length + '/' + e.c.q.length + ' respondidas</span>';
            go.textContent = 'Continuar →';
        } else { go.textContent = 'Comenzar →'; }
        return a;
    }

    function grupo(id, titulo, items, clase) {
        var sec = document.createElement('section');
        sec.className = 'grupo ' + clase; sec.dataset.grupo = id;
        sec.innerHTML = '<div class="grupo-head"><h3></h3><span class="linea"></span><span class="contador"></span></div><div class="supuestos-grid"></div>';
        sec.querySelector('h3').textContent = titulo;
        var g = sec.querySelector('.supuestos-grid'); g.id = id + '-grid';
        items.forEach(function (it) { g.appendChild(tarjeta(it)); });
        return sec;
    }

    var cont = $('menu-supuestos');
    (D.secciones || []).forEach(function (sec) {
        var cab = document.createElement('div');
        cab.className = 'seccion-head'; cab.dataset.seccion = sec.id;
        cab.innerHTML = '<h2></h2><span class="linea"></span>';
        cab.querySelector('h2').textContent = sec.titulo;
        var caja = document.createElement('div');
        caja.className = 'seccion'; caja.dataset.seccion = sec.id;
        caja.appendChild(cab);
        (sec.grupos || []).forEach(function (g) {
            caja.appendChild(grupo(sec.id + '-' + g.id, g.titulo, g.items || [], g.id));
        });
        cont.appendChild(caja);
    });
    var exa = $('examenes-grid');
    (D.examenes || []).forEach(function (it) { exa.appendChild(tarjeta(it)); });

    /* ── Buscador y filtros ── */
    var filtro = 'todos', texto = '';
    var barra = $('menu-filtros');
    barra.className = 'filtros';
    barra.innerHTML =
        '<input type="search" id="buscar" placeholder="Buscar supuesto, tema o referencia…" aria-label="Buscar">' +
        '<div class="chips" role="group" aria-label="Filtrar"></div>';
    var chips = barra.querySelector('.chips');
    [['todos', 'Todos'], ['nuevo', 'Sin hacer'], ['curso', 'En curso'], ['hecho', 'Hechos']].forEach(function (f) {
        var b = document.createElement('button');
        b.type = 'button'; b.dataset.f = f[0]; b.textContent = f[1];
        b.className = f[0] === filtro ? 'on' : '';
        b.addEventListener('click', function () { filtro = f[0]; aplicar(); });
        chips.appendChild(b);
    });
    $('buscar').addEventListener('input', function (e) { texto = e.target.value.trim().toLowerCase(); aplicar(); });

    var vacio = document.createElement('p');
    vacio.className = 'grupo-desc vacio'; vacio.textContent = 'Ningún supuesto coincide con la búsqueda.'; vacio.hidden = true;
    barra.parentNode.insertBefore(vacio, barra.nextSibling);

    function aplicar() {
        chips.querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b.dataset.f === filtro); });
        var totalVisibles = 0;
        function pasa(c) {
            return (filtro === 'todos' || c.dataset.estado === filtro) &&
                   (!texto || c.textContent.toLowerCase().indexOf(texto) !== -1);
        }
        document.querySelectorAll('.seccion').forEach(function (caja) {
            var visibles = 0;
            caja.querySelectorAll('.grupo').forEach(function (sec) {
                var n = 0;
                sec.querySelectorAll('.supuesto-card').forEach(function (c) { var ok = pasa(c); c.hidden = !ok; if (ok) n++; });
                sec.hidden = n === 0; visibles += n;
                sec.querySelector('.contador').textContent = n + (n === 1 ? ' supuesto' : ' supuestos');
            });
            caja.hidden = visibles === 0; totalVisibles += visibles;
        });
        var nEx = 0;
        exa.querySelectorAll('.supuesto-card').forEach(function (c) { var ok = pasa(c); c.hidden = !ok; if (ok) nEx++; });
        exa.hidden = $('cab-examenes').hidden = nEx === 0; totalVisibles += nEx;
        vacio.hidden = totalVisibles > 0;
    }
    aplicar();
    window.addEventListener('pageshow', function (e) { if (e.persisted) location.reload(); });
})();

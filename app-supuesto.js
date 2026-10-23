/* Funciones comunes a todos los supuestos y exámenes. Se carga con «defer»
   DESPUÉS del motor de cada página, así que sirve para cualquier versión del
   motor sin tocar su código:
     · guarda el resultado de cada intento completo (lo lee el menú)
     · guarda el intento a medias y permite continuarlo
     · «Repetir solo las falladas»
     · marcar preguntas para revisar (punto naranja en la casilla)
     · tamaño de letra y tema oscuro en el panel ⚙
   Si el motor no tiene lo que hace falta, no hace nada. */
(function () {
    'use strict';
    if (typeof init !== 'function' || typeof QUESTIONS_BANK === 'undefined' ||
        typeof calcResultados !== 'function' || typeof esAcierto !== 'function') return;

    var S = window.SupC1;
    var ID = (location.pathname.split('/').pop() || 'supuesto').replace(/\.html?$/i, '');
    var K_PROG = 'prog:' + ID, K_CURSO = 'curso:' + ID;
    var TRES_DIAS = 3 * 24 * 3600 * 1000;

    var initOrig = init;
    var marcas = new Set();
    var parcial = false;               // intento solo con las falladas
    var durOrig = examDurationSeconds;
    var durCambiada = false;
    var yaEvaluado = false;
    var $ = function (id) { return document.getElementById(id); };

    /* ── Marcar para revisar ── */
    function pintarMarca(i) {
        var on = marcas.has(i);
        var b = document.querySelector('#qcard-' + i + ' .btn-marcar');
        var n = $('nav-' + i);
        if (b) { b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); b.querySelector('span').textContent = on ? 'Marcada' : 'Marcar para revisar'; }
        if (n) n.classList.toggle('marcada', on);
    }
    function alternarMarca(i) {
        if (marcas.has(i)) marcas.delete(i); else marcas.add(i);
        pintarMarca(i);
    }
    function decorar() {
        document.querySelectorAll('.question-card').forEach(function (card) {
            var i = parseInt(card.id.replace('qcard-', ''), 10);
            var h = card.querySelector('.q-header');
            if (isNaN(i) || !h || h.querySelector('.btn-marcar')) return;
            var b = document.createElement('button');
            b.type = 'button'; b.className = 'btn-marcar'; b.innerHTML = '<i>🚩</i><span>Marcar para revisar</span>';
            b.addEventListener('click', function (e) { e.stopPropagation(); alternarMarca(i); });
            h.appendChild(b);
        });
        marcas.forEach(pintarMarca);
    }

    /* ── Botones de después de corregir ── */
    function quitarBotonesExtra() {
        document.querySelectorAll('.btn-extra').forEach(function (b) { b.remove(); });
    }
    function botonExtra(id, texto, fn) {
        var zona = document.querySelector('.btn-zone');
        if (!zona) return;
        var b = document.createElement('button');
        b.id = id; b.className = 'btn btn-info btn-extra'; b.style.display = 'inline-flex'; b.textContent = texto;
        b.addEventListener('click', fn);
        var ref = $('restart-btn');
        zona.insertBefore(b, ref || zona.firstChild);
    }
    function limpiarCorreccion() {
        if (timerInt) clearInterval(timerInt);
        var viejo = $('inline-score-banner'); if (viejo) viejo.remove();
        $('overlay').classList.remove('show');
    }
    function repetirFalladas() {
        var f = questions.filter(function (q, i) { return !esAcierto(i); });
        if (!f.length) return;
        limpiarCorreccion();
        durCambiada = true;
        examDurationSeconds = Math.max(60, Math.round(durOrig * f.length / Math.max(1, QUESTIONS_BANK.length)));
        parcial = true;
        init('answers', f);
    }
    function intentoCompleto() { limpiarCorreccion(); init('default'); }

    function alCorregir() {
        if (!parcial) registrar();
        S.del(K_CURSO);
        quitarBotonesExtra();
        if (parcial) botonExtra('completo-btn', '↩ Intento completo', intentoCompleto);
        var fall = questions.filter(function (q, i) { return !esAcierto(i); }).length;
        if (fall) botonExtra('falladas-btn', '↺ Repetir solo las falladas (' + fall + ')', repetirFalladas);
    }

    /* ── Resultado del intento (lo lee el menú) ── */
    function registrar() {
        var r; try { r = calcResultados(); } catch (e) { return; }
        var p = S.get(K_PROG, { intentos: 0 });
        var u = { fecha: Date.now(), pct: r.pct, puntos: r.puntos, max: r.max,
                  aciertos: r.aciertos, fallos: r.fallos, blancos: r.blancos, total: r.total };
        p.intentos = (p.intentos || 0) + 1;
        p.ultima = u;
        if (!p.mejor || u.pct > p.mejor.pct) p.mejor = u;
        S.set(K_PROG, p);
    }

    /* ── Intento a medias ── */
    function guardar() {
        if (evaluated || !Object.keys(userAns).length) return;
        var q = questions.map(function (x) { return QUESTIONS_BANK.indexOf(x); });
        if (q.indexOf(-1) !== -1) return;
        var cards = [], ok = true;
        questions.forEach(function (x, i) {
            var c = $('qcard-' + i);
            if (!c || !c.dataset.opciones) { ok = false; return; }
            cards.push(c.dataset.opciones.split(',').map(Number));
        });
        if (!ok) return;
        S.set(K_CURSO, { v: 1, ts: Date.now(), n: QUESTIONS_BANK.length, q: q, o: cards, a: userAns,
                         cur: current, t: timeLeft, dur: examDurationSeconds, m: Array.from(marcas), parcial: parcial });
    }

    function restaurar(st) {
        var cola = st.o.slice();
        var original = window.opcionesDePregunta;
        window.opcionesDePregunta = function (q) {
            return (cola.shift() || []).map(function (idx) { return { txt: q.a[idx], idx: idx }; });
        };
        try {
            if (timerInt) clearInterval(timerInt);
            parcial = !!st.parcial;
            durCambiada = st.dur !== durOrig;
            examDurationSeconds = st.dur;
            initOrig('answers', st.q.map(function (i) { return QUESTIONS_BANK[i]; }));
        } finally { window.opcionesDePregunta = original; }
        userAns = st.a;
        timeLeft = st.t;
        $('timer-display').textContent = formatTime(timeLeft);
        Object.keys(userAns).forEach(function (k) { pintarRespuesta(parseInt(k, 10)); });
        updateProgress();
        marcas = new Set(st.m || []);
        decorar();
        document.body.classList.toggle('intento-parcial', parcial);
        jump(Math.min(st.cur || 0, questions.length - 1), true);
    }

    function modalContinuar(st) {
        timerPaused = true;
        var resp = Object.keys(st.a).length;
        var m = Math.floor(st.t / 60), s = st.t % 60;
        var fondo = document.createElement('div');
        fondo.className = 'supc1-modal';
        fondo.innerHTML =
            '<div class="supc1-modal-caja" role="dialog" aria-modal="true">' +
            '<h3>Tienes un intento sin terminar</h3>' +
            '<p>Llevas <strong>' + resp + ' de ' + st.q.length + '</strong> preguntas respondidas y te quedan ' +
            '<strong>' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0') + '</strong>.</p>' +
            '<div class="supc1-modal-botones"><button class="btn btn-primary" data-r="si">Continuar</button>' +
            '<button class="btn" data-r="no">Empezar de nuevo</button></div></div>';
        fondo.addEventListener('click', function (e) {
            var r = e.target.getAttribute && e.target.getAttribute('data-r');
            if (!r) return;
            fondo.remove();
            if (r === 'si') { try { restaurar(st); } catch (err) { S.del(K_CURSO); } }
            else S.del(K_CURSO);
            timerPaused = false;
        });
        document.body.appendChild(fondo);
    }

    /* ── Panel ⚙: tamaño de letra y tema oscuro ── */
    function ajustesVisuales() {
        var panel = $('settings-panel');
        if (!panel || $('row-visual')) return;
        var fila = document.createElement('div');
        fila.className = 'settings-row'; fila.id = 'row-visual';
        fila.innerHTML =
            '<label>Tamaño de letra</label><div class="fuente-btns">' +
            '<button type="button" data-f="normal">A</button><button type="button" data-f="grande">A+</button>' +
            '<button type="button" data-f="enorme">A++</button></div>' +
            '<div class="settings-check" style="margin-top:12px"><label><input type="checkbox" id="tema-oscuro-toggle">' +
            '<span>Tema oscuro</span></label></div>';
        panel.appendChild(fila);
        var actual = S.get('fuente', 'normal');
        fila.querySelectorAll('[data-f]').forEach(function (b) {
            b.classList.toggle('on', b.dataset.f === actual);
            b.addEventListener('click', function () {
                S.setFuente(b.dataset.f);
                fila.querySelectorAll('[data-f]').forEach(function (x) { x.classList.toggle('on', x === b); });
            });
        });
        var t = $('tema-oscuro-toggle');
        t.checked = document.documentElement.getAttribute('data-tema') === 'oscuro';
        t.addEventListener('change', function () { S.setTema(t.checked); });
    }

    /* ── Enganches ── */
    window.init = function (modo) {
        if (modo !== 'answers') {
            parcial = false;
            if (durCambiada) { examDurationSeconds = durOrig; durCambiada = false; }
        }
        marcas.clear();
        yaEvaluado = false;
        quitarBotonesExtra();
        var r = initOrig.apply(this, arguments);
        document.body.classList.toggle('intento-parcial', parcial);
        decorar();
        return r;
    };

    var goHomeOrig = window.goHome;
    if (typeof goHomeOrig === 'function') {
        window.goHome = function () {
            if (!evaluated) {
                if (!window.confirm('Vas a salir con el test a medias. Tu intento queda guardado y podrás continuarlo desde este mismo supuesto.\n\n¿Volver al menú principal?')) return;
                guardar();
                var c = window.confirm; window.confirm = function () { return true; };
                try { goHomeOrig.apply(this, arguments); } finally { window.confirm = c; }
            } else goHomeOrig.apply(this, arguments);
        };
    }

    setInterval(function () {
        if (evaluated && !yaEvaluado) { yaEvaluado = true; alCorregir(); }
        else if (!evaluated) { yaEvaluado = false; guardar(); }
    }, 1500);
    document.addEventListener('visibilitychange', function () { if (document.hidden) guardar(); });
    window.addEventListener('pagehide', guardar);

    decorar();
    ajustesVisuales();
    var st = S.get(K_CURSO, null);
    if (st && st.v === 1 && st.n === QUESTIONS_BANK.length && Date.now() - st.ts < TRES_DIAS &&
        !evaluated && st.q && st.o && st.q.length === st.o.length && st.q.every(function (i) { return QUESTIONS_BANK[i]; })) {
        modalContinuar(st);
    } else if (st) S.del(K_CURSO);
})();

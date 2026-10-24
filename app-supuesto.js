/* Funciones comunes a todos los supuestos y exámenes. Se carga con «defer»
   DESPUÉS del motor de cada página, así que sirve para cualquier versión del
   motor sin tocar su código:
     · guarda el resultado de cada intento completo (lo lee el menú)
     · guarda el intento a medias y permite continuarlo
     · «Repetir solo las falladas»
     · marcar preguntas para más tarde (punto naranja en la casilla) y notas personales
     · banco personal de preguntas falladas / marcadas / con nota (lo lee «Mi estudio»)
     · historial de intentos para las estadísticas y «?practicar=falladas|marcadas»
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

    /* ── Banco personal (en este navegador): falladas, marcadas y notas ──
       Cada pregunta se identifica por «supuesto:huella del enunciado», así que
       sigue valiendo aunque se reordenen las preguntas del supuesto. */
    var K_BANCO = 'banco';
    function huella(t) { return S.huella(t); }
    function textoPlano(q) { return String(q.q || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim(); }
    function claveDe(q) { return ID + ':' + huella(textoPlano(q)); }
    function corto(q) { var t = textoPlano(q); return t.length > 220 ? t.slice(0, 217) + '…' : t; }
    function banco() {
        var b = S.get(K_BANCO, null) || {};
        b.falladas = b.falladas || {}; b.marcadas = b.marcadas || {}; b.notas = b.notas || {}; b.favoritas = b.favoritas || {}; b.borradas = b.borradas || {};
        return b;
    }
    function guardarBanco(b) { S.set(K_BANCO, b); }
    function aviso(texto) {
        var t = document.createElement('div');
        t.className = 'supc1-toast'; t.setAttribute('role', 'status'); t.textContent = texto;
        document.body.appendChild(t); setTimeout(function () { t.remove(); }, 4500);
    }

    /* Resultado de cada pregunta en el banco de falladas: una pregunta entra al
       fallarla y sale tras acertarla dos veces seguidas. «memo» evita contar dos
       veces lo mismo dentro de un intento. */
    var memoBanco = {};
    function anotarResultado(q, i) {
        if (sinResponder(i)) return;
        var k = claveDe(q), est = esAcierto(i) ? 'ok' : 'ko';
        if (memoBanco[k] === est) return;
        var b = banco(), f = b.falladas[k];
        if (est === 'ko') {
            f = f || { f: ID, h: k.split(':')[1], t: corto(q), n: 0, ok: 0 };
            f.n++; f.ok = 0; f.ts = Date.now(); b.falladas[k] = f; delete b.borradas['f:' + k];
        } else if (f) {
            f.ok = (f.ok || 0) + 1;
            if (f.ok >= 2) { delete b.falladas[k]; b.borradas['f:' + k] = Date.now(); } else f.ts = Date.now();
        }
        memoBanco[k] = est; guardarBanco(b);
    }
    // Con «corregir pregunta a pregunta» el alumno ya ve el resultado: se anota
    // enseguida, sin esperar a que corrija el examen entero.
    function anotarReveladas() {
        if (typeof instantFeedback === 'undefined' || !instantFeedback || evaluated) return;
        questions.forEach(function (q, i) {
            var f = $('feed-' + i);
            if (f && f.style.display === 'block') anotarResultado(q, i);
        });
    }

    /* ── Favoritas (corazón). Se pueden desactivar en el supuesto (config.corazon:false, desde el editor
       de Python) o en el panel ⚙ de cada persona. ── */
    function corazonDisponible() { return !(typeof EXAM_CONFIG !== 'undefined' && EXAM_CONFIG && EXAM_CONFIG.corazon === false); }
    function aplicarCorazon() { document.documentElement.classList.toggle('sin-corazon', !corazonDisponible() || S.get('corazon', true) === false); }
    function pintarFav(i) {
        var q = questions[i]; if (!q) return;
        var on = !!banco().favoritas[claveDe(q)];
        var b = document.querySelector('#qcard-' + i + ' .btn-corazon');
        if (b) { b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); b.querySelector('i').textContent = on ? '♥' : '♡'; b.title = on ? 'Quitar de favoritas' : 'Guardar en favoritas'; }
    }
    function alternarFav(i) {
        var q = questions[i]; if (!q) return;
        var b = banco(), k = claveDe(q);
        if (b.favoritas[k]) { delete b.favoritas[k]; b.borradas['v:' + k] = Date.now(); }
        else { b.favoritas[k] = { f: ID, h: k.split(':')[1], t: corto(q), ts: Date.now() }; delete b.borradas['v:' + k]; }
        guardarBanco(b); pintarFav(i);
    }

    /* ── Marcar para más tarde y notas ── */
    function pintarMarca(i) {
        var on = marcas.has(i);
        var b = document.querySelector('#qcard-' + i + ' .btn-marcar');
        var n = $('nav-' + i);
        if (b) { b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); b.querySelector('span').textContent = on ? 'Marcada' : 'Marcar para más tarde'; }
        if (n) n.classList.toggle('marcada', on);
    }
    function alternarMarca(i) {
        var q = questions[i]; if (!q) return;
        var b = banco(), k = claveDe(q);
        if (marcas.has(i)) { marcas.delete(i); delete b.marcadas[k]; b.borradas['m:' + k] = Date.now(); }
        else { marcas.add(i); b.marcadas[k] = { f: ID, h: k.split(':')[1], t: corto(q), ts: Date.now() }; delete b.borradas['m:' + k]; }
        guardarBanco(b); pintarMarca(i);
    }
    function marcasDelBanco() {
        var b = banco(); marcas = new Set();
        questions.forEach(function (q, i) { if (b.marcadas[claveDe(q)]) marcas.add(i); });
    }

    function pintarNota(i) {
        var q = questions[i]; if (!q) return;
        var n = banco().notas[claveDe(q)];
        var btn = document.querySelector('#qcard-' + i + ' .btn-nota');
        var caja = document.querySelector('#qcard-' + i + ' .nota-caja');
        if (btn) { btn.classList.toggle('on', !!n); btn.querySelector('span').textContent = n ? 'Nota' : 'Añadir nota'; }
        if (caja && n && !caja.value) { caja.value = n.txt; caja.hidden = false; }
    }
    function alternarNota(i) {
        var caja = document.querySelector('#qcard-' + i + ' .nota-caja'); if (!caja) return;
        caja.hidden = !caja.hidden;
        if (!caja.hidden) caja.focus();
    }
    function guardarNota(i, texto) {
        var q = questions[i]; if (!q) return;
        var b = banco(), k = claveDe(q);
        texto = texto.trim();
        if (texto) { b.notas[k] = { f: ID, h: k.split(':')[1], t: corto(q), txt: texto, ts: Date.now() }; delete b.borradas['n:' + k]; }
        else if (b.notas[k]) { delete b.notas[k]; b.borradas['n:' + k] = Date.now(); }
        guardarBanco(b); pintarNota(i);
    }

    function decorar() {
        aplicarCorazon();
        document.querySelectorAll('.question-card').forEach(function (card) {
            var i = parseInt(card.id.replace('qcard-', ''), 10);
            var h = card.querySelector('.q-header');
            if (isNaN(i) || !h || h.querySelector('.q-acciones')) return;
            var caja = document.createElement('div');
            caja.className = 'q-acciones';
            var b = document.createElement('button');
            b.type = 'button'; b.className = 'btn-marcar'; b.innerHTML = '<i aria-hidden="true">🚩</i><span>Marcar para más tarde</span>'; b.title = 'Marca la pregunta para repasarla o contestarla más tarde (tecla M)';
            b.addEventListener('click', function (e) { e.stopPropagation(); alternarMarca(i); });
            var nb = document.createElement('button');
            nb.type = 'button'; nb.className = 'btn-nota'; nb.innerHTML = '<i aria-hidden="true">📝</i><span>Añadir nota</span>';
            nb.addEventListener('click', function (e) { e.stopPropagation(); alternarNota(i); });
            caja.appendChild(b); caja.appendChild(nb); h.appendChild(caja);
            var ta = document.createElement('textarea');
            ta.className = 'nota-caja'; ta.hidden = true; ta.rows = 3;
            ta.placeholder = 'Tu nota personal sobre esta pregunta (solo se guarda en este navegador)';
            ta.setAttribute('aria-label', 'Nota personal de la pregunta ' + (i + 1));
            var t = null;
            ta.addEventListener('input', function () { clearTimeout(t); t = setTimeout(function () { guardarNota(i, ta.value); }, 400); });
            ta.addEventListener('blur', function () { clearTimeout(t); guardarNota(i, ta.value); });
            h.parentNode.insertBefore(ta, h.nextSibling);
            pintarNota(i);
            if (corazonDisponible() && !card.querySelector('.btn-corazon')) {
                var cb = document.createElement('button');
                cb.type = 'button'; cb.className = 'btn-corazon'; cb.innerHTML = '<i aria-hidden="true">♡</i>';
                cb.setAttribute('aria-label', 'Favorita (tecla H)');
                cb.addEventListener('click', function (e) { e.stopPropagation(); alternarFav(i); });
                card.appendChild(cb); pintarFav(i);
            }
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

    // «supuesto.html?practicar=falladas|marcadas»: intento de práctica solo con esas preguntas
    function practicarDesdeUrl() {
        var m = /[?&]practicar=(falladas|marcadas|favoritas)/.exec(location.search);
        if (!m) return false;
        history.replaceState(null, '', location.pathname);
        var b = banco(), mapa = b[m[1]];
        var sub = QUESTIONS_BANK.filter(function (q) { return mapa[claveDe(q)]; });
        if (!sub.length) { aviso('No te quedan preguntas ' + m[1] + ' en este supuesto.'); return false; }
        var curso = S.get(K_CURSO, null);
        if (curso && !curso.parcial && !window.confirm('Tienes un intento sin terminar de este supuesto. Si practicas ahora se sustituirá.\n\n¿Continuar?')) return false;
        if (timerInt) clearInterval(timerInt);
        durCambiada = true;
        examDurationSeconds = Math.max(60, Math.round(durOrig * sub.length / Math.max(1, QUESTIONS_BANK.length)));
        parcial = true;
        init('answers', sub);
        return true;
    }

    function alCorregir() {
        questions.forEach(anotarResultado);
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
                  aciertos: r.aciertos, fallos: r.fallos, blancos: r.blancos, total: r.total,
                  seg: Math.max(0, examDurationSeconds - timeLeft) };
        p.intentos = (p.intentos || 0) + 1;
        p.ultima = u;
        p.hist = (p.hist || []).concat([u]).slice(-40);
        if (!p.mejor || u.pct > p.mejor.pct) p.mejor = u;
        S.set(K_PROG, p);
    }

    /* ── Intento a medias ── */
    function guardar() {
        anotarReveladas();
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
        marcasDelBanco();
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
        marcas.clear(); memoBanco = {};
        yaEvaluado = false;
        quitarBotonesExtra();
        var r = initOrig.apply(this, arguments);
        marcasDelBanco();
        document.body.classList.toggle('intento-parcial', parcial);
        decorar();
        return r;
    };

    // Un intento solo con las falladas es práctica personal: no se manda a los
    // formularios (ni el envío manual, que se oculta, ni el detalle automático).
    var detalleOrig = window.enviarDetalleCorreccion;
    if (typeof detalleOrig === 'function') {
        window.enviarDetalleCorreccion = function () {
            if (parcial) return;
            return detalleOrig.apply(this, arguments);
        };
    }
    var enviarOrig = window.enviarResultados;
    if (typeof enviarOrig === 'function') {
        window.enviarResultados = function () {
            if (parcial) return;
            return enviarOrig.apply(this, arguments);
        };
    }

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

    // API para app-uso.js (atajos de teclado, etc.)
    S.sup = { id: ID, huella: huella, clave: claveDe, corto: corto, marcar: alternarMarca, nota: alternarNota, favorita: alternarFav, aplicarCorazon: aplicarCorazon, corazonDisponible: corazonDisponible, esParcial: function () { return parcial; } };

    marcasDelBanco();
    decorar();
    ajustesVisuales();
    if (practicarDesdeUrl()) return;
    var st = S.get(K_CURSO, null);
    if (st && st.v === 1 && st.n === QUESTIONS_BANK.length && Date.now() - st.ts < TRES_DIAS &&
        !evaluated && st.q && st.o && st.q.length === st.o.length && st.q.every(function (i) { return QUESTIONS_BANK[i]; })) {
        modalContinuar(st);
    } else if (st) S.del(K_CURSO);
})();

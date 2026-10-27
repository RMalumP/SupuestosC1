/* Comodidad y accesibilidad de los supuestos. Se carga con «defer» después de
   app-supuesto.js:
     · atajos de teclado (A–G / 1–7 responden, ← → cambian de pregunta, M marca,
       N nota, ? ayuda) y deslizar el dedo para cambiar de pregunta
     · accesibilidad: opciones como radios/casillas con teclado, anuncios para
       lectores de pantalla y enlace «saltar al contenido»
     · enlaces automáticos a la norma (BOE) en la motivación de las respuestas */
(function () {
    'use strict';
    if (typeof questions === 'undefined' || typeof selectAnswer !== 'function' || typeof jump !== 'function') return;
    var S = window.SupC1 || {};
    var $ = function (id) { return document.getElementById(id); };
    var LETRAS = ['A', 'B', 'C', 'D', 'E', 'F', 'G'];

    /* ── Anuncios para lectores de pantalla ── */
    var vivo = document.createElement('div');
    vivo.id = 'supc1-vivo'; vivo.className = 'solo-lectores'; vivo.setAttribute('aria-live', 'polite'); vivo.setAttribute('role', 'status');
    document.body.appendChild(vivo);
    function anunciar(t) { vivo.textContent = ''; setTimeout(function () { vivo.textContent = t; }, 50); }

    var enlace = document.createElement('a');
    enlace.href = '#quiz-container'; enlace.className = 'saltar-contenido'; enlace.textContent = 'Saltar a las preguntas';
    document.body.insertBefore(enlace, document.body.firstChild);

    /* ── Accesibilidad de opciones y casillas (idempotente: se repite al crearse tarjetas) ── */
    function preparar() {
        document.querySelectorAll('.options-grid').forEach(function (g, gi) {
            var card = g.closest('.question-card');
            var multi = card && card.dataset.multiple === '1';
            g.setAttribute('role', multi ? 'group' : 'radiogroup');
            g.setAttribute('aria-label', 'Opciones de la pregunta ' + (card ? parseInt(card.id.replace('qcard-', ''), 10) + 1 : gi + 1));
        });
        document.querySelectorAll('.option').forEach(function (o) {
            var card = o.closest('.question-card');
            var multi = card && card.dataset.multiple === '1';
            if (!o.hasAttribute('role')) {
                o.setAttribute('role', multi ? 'checkbox' : 'radio'); o.setAttribute('tabindex', '0');
            }
            o.setAttribute('aria-checked', o.classList.contains('selected') ? 'true' : 'false');
        });
        document.querySelectorAll('.nav-box').forEach(function (n) {
            if (n.hasAttribute('role')) return;
            n.setAttribute('role', 'button'); n.setAttribute('tabindex', '0');
            n.setAttribute('aria-label', 'Ir a la pregunta ' + n.textContent.trim());
        });
        document.querySelectorAll('.feedback').forEach(enlazarNormas);
    }

    /* ── Enlaces a la norma ── */
    var reglas = null;
    function construirReglas() {
        reglas = [];
        (window.NORMAS || []).forEach(function (n) {
            n.siglas.forEach(function (sig) { reglas.push({ sig: sig, boe: n.boe }); });
        });
        if (!reglas.length) return;
        var alt = reglas.map(function (r) { return r.sig.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); })
                        .sort(function (a, b) { return b.length - a.length; }).join('|');
        reglas.re = new RegExp('\\b([Aa]rt(?:ículos?|s?\\.?)?\\.?\\s*(\\d+)[^;:]{0,45}?\\b(' + alt + ')(?![\\wÀ-ÿ]))', 'g');
    }
    function enlazarNormas(raiz) {
        if (raiz.dataset.normas) return; raiz.dataset.normas = '1';
        if (reglas === null) construirReglas();
        if (!reglas.length || !reglas.re) return;
        var nodos = [], w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT, null);
        while (w.nextNode()) { if (!w.currentNode.parentNode.closest('a, button')) nodos.push(w.currentNode); }
        nodos.forEach(function (nodo) {
            var t = nodo.nodeValue; reglas.re.lastIndex = 0;
            var m, ult = 0, trozos = [];
            while ((m = reglas.re.exec(t))) {
                var r = reglas.filter(function (x) { return x.sig === m[3]; })[0]; if (!r) continue;
                trozos.push(document.createTextNode(t.slice(ult, m.index)));
                var a = document.createElement('a');
                a.href = 'https://www.boe.es/buscar/act.php?id=' + r.boe + '#a' + m[2];
                a.target = '_blank'; a.rel = 'noopener'; a.className = 'enlace-norma';
                a.title = 'Abrir el artículo ' + m[2] + ' en el BOE'; a.textContent = m[1];
                trozos.push(a); ult = m.index + m[0].length;
            }
            if (!trozos.length) return;
            trozos.push(document.createTextNode(t.slice(ult)));
            var frag = document.createDocumentFragment(); trozos.forEach(function (x) { frag.appendChild(x); });
            nodo.parentNode.replaceChild(frag, nodo);
        });
    }

    var cont = $('quiz-container');
    if (cont) {
        new MutationObserver(function (muts) {
            var nuevas = false;
            muts.forEach(function (m) {
                if (m.type === 'childList') nuevas = true;
                else if (m.type === 'attributes' && m.target.classList && m.target.classList.contains('option')) {
                    m.target.setAttribute('aria-checked', m.target.classList.contains('selected') ? 'true' : 'false');
                    if (m.target.classList.contains('correct')) anunciar('Correcta');
                    else if (m.target.classList.contains('wrong')) anunciar('Incorrecta');
                }
            });
            if (nuevas) preparar();
        }).observe(cont, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
    }
    var navb = $('nav-boxes');
    if (navb) new MutationObserver(preparar).observe(navb, { childList: true, subtree: true });
    preparar();

    /* Teclado sobre los elementos con role (Enter / espacio = clic) */
    document.addEventListener('keydown', function (e) {
        if ((e.key === 'Enter' || e.key === ' ') && e.target && e.target.getAttribute &&
            (e.target.classList.contains('option') || e.target.classList.contains('nav-box'))) {
            e.preventDefault(); e.target.click();
        }
    });

    /* ── Atajos de teclado ── */
    function bloqueado(e) {
        var t = e.target, tag = t && t.tagName;
        if (e.ctrlKey || e.metaKey || e.altKey) return true;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (t && t.isContentEditable)) return true;
        if (document.querySelector('.supc1-modal')) return true;
        var ov = $('overlay'); if (ov && ov.classList.contains('show')) return true;
        return false;
    }
    function cardActual() { return $('qcard-' + current); }
    function ayuda() {
        if (document.querySelector('.supc1-modal.ayuda')) return;
        var f = document.createElement('div'); f.className = 'supc1-modal ayuda';
        f.innerHTML = '<div class="supc1-modal-caja" role="dialog" aria-modal="true" aria-label="Atajos de teclado"><h3>Atajos de teclado</h3>' +
            '<p><kbd>A</kbd>–<kbd>G</kbd> o <kbd>1</kbd>–<kbd>7</kbd> responder · <kbd>←</kbd> <kbd>→</kbd> pregunta anterior / siguiente<br>' +
            '<kbd>M</kbd> marcar para más tarde · <kbd>H</kbd> favorita ♥ · <kbd>N</kbd> nota · <kbd>?</kbd> esta ayuda · <kbd>Esc</kbd> cerrar</p>' +
            '<div class="supc1-modal-botones"><button class="btn btn-primary" data-r="x">Entendido</button></div></div>';
        f.addEventListener('click', function (e) { if (e.target === f || (e.target.getAttribute && e.target.getAttribute('data-r'))) f.remove(); });
        document.body.appendChild(f); f.querySelector('button').focus();
    }
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { var h = document.querySelector('.supc1-modal.ayuda'); if (h) h.remove(); return; }
        if (bloqueado(e)) return;
        var k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
        var idx = LETRAS.map(function (l) { return l.toLowerCase(); }).indexOf(k);
        if (idx === -1 && /^[1-7]$/.test(k)) idx = parseInt(k, 10) - 1;
        if (idx !== -1) {
            var c = cardActual(), n = c ? c.querySelectorAll('.option').length : 0;
            if (idx < n) { e.preventDefault(); selectAnswer(current, idx); }
            return;
        }
        if (k === 'ArrowRight') { e.preventDefault(); move(1); anunciar('Pregunta ' + (current + 1) + ' de ' + questions.length); }
        else if (k === 'ArrowLeft') { e.preventDefault(); move(-1); anunciar('Pregunta ' + (current + 1) + ' de ' + questions.length); }
        else if (k === 'm' && S.sup) { e.preventDefault(); S.sup.marcar(current); }
        else if (k === 'h' && S.sup && S.sup.corazonDisponible() && S.get('corazon', true) !== false) { e.preventDefault(); S.sup.favorita(current); }
        else if (k === 'n' && S.sup) { e.preventDefault(); S.sup.nota(current); }
        else if (k === '?' && !(S.opcionPanel && S.opcionPanel('atajos').visible === false)) { e.preventDefault(); ayuda(); }
    });

    /* ── Deslizar para cambiar de pregunta (móvil) ── */
    var x0 = 0, y0 = 0, t0 = 0, desliza = false;
    document.addEventListener('touchstart', function (e) {
        var t = e.target, ok = e.touches.length === 1 && S.get && S.get('deslizar', !(S.opcionPanel && S.opcionPanel('deslizar').activa === false)) &&
            !(t.closest && t.closest('#nav-header, input, textarea, select, .table-scroll, .timeline, #settings-panel, .supc1-modal, #overlay'));
        desliza = !!ok;
        if (ok) { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; t0 = Date.now(); }
        // Los bordes de la pantalla los reserva el sistema para «volver»: no se usan
        if (ok && (x0 < 28 || x0 > window.innerWidth - 28)) desliza = false;
    }, { passive: true });
    document.addEventListener('touchend', function (e) {
        if (!desliza) return; desliza = false;
        var t = e.changedTouches[0], dx = t.clientX - x0, dy = t.clientY - y0;
        if (Date.now() - t0 > 700 || Math.abs(dx) < 80 || Math.abs(dy) > 45 || Math.abs(dx) < Math.abs(dy) * 2.5) return;
        if (window.getSelection && String(window.getSelection())) return;
        move(dx < 0 ? 1 : -1);
        anunciar('Pregunta ' + (current + 1) + ' de ' + questions.length);
    }, { passive: true });

    /* ── Panel ⚙: atajos y deslizar ── */
    var panel = $('settings-panel');
    if (panel && !$('row-uso') && S.get) {
        var fila = document.createElement('div');
        fila.className = 'settings-row'; fila.id = 'row-uso';
        var od = S.opcionPanel ? S.opcionPanel('deslizar') : {}, oa = S.opcionPanel ? S.opcionPanel('atajos') : {};
        fila.innerHTML = (od.visible === false ? '' : '<div class="settings-check"><label><input type="checkbox" id="deslizar-toggle"><span>Deslizar para cambiar de pregunta</span></label></div>') +
            (S.sup && S.sup.corazonDisponible() ? '<div class="settings-check" style="margin-top:8px"><label><input type="checkbox" id="corazon-toggle"><span>Mostrar el corazón de favoritas ♥</span></label></div>' : '') +
            (oa.visible === false ? '' : '<div style="margin-top:8px"><button type="button" class="btn-mini" id="atajos-btn">Atajos de teclado (?)</button></div>');
        panel.appendChild(fila);
        var d = $('deslizar-toggle');
        if (d) { d.checked = S.get('deslizar', od.activa !== false); d.addEventListener('change', function () { S.set('deslizar', d.checked); }); }
        var cz = $('corazon-toggle');
        if (cz) { cz.checked = S.get('corazon', true) !== false; cz.addEventListener('change', function () { S.set('corazon', cz.checked); S.sup.aplicarCorazon(); }); }
        if ($('atajos-btn')) $('atajos-btn').addEventListener('click', ayuda);
    }

    /* Anunciar el resultado al corregir */
    setInterval(function () {
        if (typeof evaluated !== 'undefined' && evaluated && !vivo.dataset.corregido) {
            vivo.dataset.corregido = '1';
            try { var r = calcResultados(); anunciar('Examen corregido: ' + r.aciertos + ' aciertos, ' + r.fallos + ' fallos y ' + r.blancos + ' en blanco.'); } catch (e) {}
        } else if (typeof evaluated !== 'undefined' && !evaluated) { delete vivo.dataset.corregido; }
    }, 1500);
})();

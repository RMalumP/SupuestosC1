/* Botón «Impugnar» en la corrección de cada pregunta (examen completo y «corregir
   pregunta a pregunta»). Manda la impugnación a un formulario de Google y la guarda
   en «Mi estudio» (banco.impugnaciones, que se sincroniza con Drive). Se carga con
   «defer» después de app-supuesto.js; no hace nada si no está activo. */
(function () {
    'use strict';
    var C = window.SUPC1_IMPUG, S = window.SupC1;
    if (!C || !C.activa || !C.formUrl || !S) return;
    if (typeof questions === 'undefined' || typeof contestadasDe !== 'function') return;

    var ARCH = (location.pathname.split('/').pop() || 'supuesto').replace(/\.html?$/i, '');
    var K_BANCO = 'banco', K_NOMBRE = 'impug-nombre';
    var $ = function (id) { return document.getElementById(id); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function plano(h) { return String(h || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim(); }
    function banco() { var b = S.get(K_BANCO, null) || {}; b.impugnaciones = b.impugnaciones || {}; b.borradas = b.borradas || {}; return b; }

    function enviar(datos) {
        var c = C.campos, f = new URLSearchParams();
        var pon = function (k, v) { if (c[k]) f.append(c[k], v); };
        if (datos.pub) pon('publico', C.valorPublico || 'Publico si');
        pon('nombre', datos.anon ? (C.anonimo || 'Anónimo') : (datos.nombre || (C.anonimo || 'Anónimo')));
        pon('supuesto', datos.sup); pon('pregunta', String(datos.n)); pon('enunciado', datos.enun);
        pon('correcta', datos.correcta); pon('marcada', datos.marcada); pon('texto', datos.imp); pon('id', datos.id);
        return fetch(C.formUrl, { method: 'POST', mode: 'no-cors', keepalive: true, body: f });
    }
    // Reintenta las que no llegaron a salir (sin conexión)
    function reintentar() {
        var b = banco(), ks = Object.keys(b.impugnaciones).filter(function (k) { return !b.impugnaciones[k].env; });
        ks.forEach(function (k) {
            enviar(b.impugnaciones[k]).then(function () { var x = banco(); if (x.impugnaciones[k]) { x.impugnaciones[k].env = true; S.set(K_BANCO, x); } }).catch(function () { /* se reintenta otro día */ });
        });
    }

    function estilo() {
        if ($('impug-css')) return;
        var s = el('style'); s.id = 'impug-css';
        s.textContent = '.impug-btn{font:inherit;font-size:.82rem;font-weight:600;margin-top:10px;padding:6px 12px;border-radius:8px;border:1px solid #a34a3a;background:transparent;color:#a34a3a;cursor:pointer}' +
            '.impug-ok{font-size:.82rem;margin-top:8px;opacity:.8}' +
            '.impug-fondo{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:10000;display:flex;align-items:center;justify-content:center;padding:16px}' +
            '.impug-caja{background:#fffefb;color:#2b2118;border-radius:12px;max-width:520px;width:100%;max-height:92vh;overflow:auto;padding:18px;font-size:.92rem;line-height:1.45}' +
            ':root[data-tema="oscuro"] .impug-caja{background:#2a1f19;color:#f1e6d8}' +
            '.impug-caja h3{margin:0 0 6px}.impug-caja textarea,.impug-caja input[type=text]{width:100%;box-sizing:border-box;font:inherit;padding:8px;border-radius:8px;border:1px solid #c9a58a;background:transparent;color:inherit;margin:4px 0 10px}' +
            '.impug-caja label.chk{display:flex;gap:8px;align-items:flex-start;margin:6px 0}.impug-caja small{opacity:.75;display:block}' +
            '.impug-acc{display:flex;gap:10px;justify-content:flex-end;margin-top:12px}.impug-acc button{font:inherit;font-weight:600;padding:8px 14px;border-radius:8px;border:1px solid #7a5b47;background:transparent;color:inherit;cursor:pointer}' +
            '.impug-acc .principal{background:#5c4033;color:#fff;border-color:#5c4033}.impug-acc button[disabled]{opacity:.5}';
        document.head.appendChild(s);
    }

    function contexto(i) {
        var card = $('qcard-' + i), opts = card ? Array.prototype.slice.call(card.querySelectorAll('.option')) : [];
        var txt = function (n) { var o = opts[n]; if (!o) return ''; var sp = o.querySelectorAll('span'); return (sp[0] ? sp[0].textContent.trim() + ') ' : '') + plano(sp[1] ? sp[1].textContent : o.textContent); };
        var dadas = contestadasDe(i), cor = correctasDe(i);
        var panel = card && card.dataset.panel ? $(card.dataset.panel) : null;
        return {
            n: i + 1, q: plano(card && card.querySelector('.q-text') ? card.querySelector('.q-text').textContent : ''),
            enun: panel ? plano(panel.textContent).slice(0, 1500) : '',
            marcada: dadas.length ? dadas.map(txt).join(' | ') : '(en blanco)',
            correcta: cor.map(txt).join(' | ')
        };
    }

    function abrir(i) {
        estilo();
        var ctx = contexto(i), fondo = el('div', 'impug-fondo'), caja = el('div', 'impug-caja');
        fondo.setAttribute('role', 'dialog'); fondo.setAttribute('aria-modal', 'true');
        caja.appendChild(el('h3', null, 'Impugnar la pregunta ' + ctx.n));
        caja.appendChild(el('small', null, 'Se envía la pregunta, la respuesta correcta y la que marcaste, junto con tu texto.'));
        var ta = el('textarea'); ta.rows = 5; ta.placeholder = 'Explica por qué crees que la respuesta es discutible…'; ta.setAttribute('aria-label', 'Texto de la impugnación');
        caja.appendChild(ta);
        var nom = el('input'); nom.type = 'text'; nom.placeholder = 'Tu nombre (opcional)'; nom.value = S.get(K_NOMBRE, ''); nom.setAttribute('aria-label', 'Nombre');
        caja.appendChild(nom);
        var l1 = el('label', 'chk'), anon = el('input'); anon.type = 'checkbox'; l1.appendChild(anon); l1.appendChild(el('span', null, 'Anónimo: no enviar mi nombre'));
        var l2 = el('label', 'chk'), pub = el('input'); pub.type = 'checkbox'; l2.appendChild(pub);
        var t2 = el('span', null, 'Publicar'); t2.appendChild(el('small', null, 'Si se resuelve, se podrá mostrar con tu nombre (salvo que marques «Anónimo»). Si no la marcas, solo se mostrará de forma anónima.')); l2.appendChild(t2);
        anon.addEventListener('change', function () { nom.disabled = anon.checked; });
        caja.appendChild(l1); caja.appendChild(l2);
        var acc = el('div', 'impug-acc'), no = el('button', null, 'Cancelar'), si = el('button', 'principal', 'Enviar impugnación');
        no.type = si.type = 'button'; acc.appendChild(no); acc.appendChild(si); caja.appendChild(acc);
        fondo.appendChild(caja); document.body.appendChild(fondo); ta.focus();
        var cerrar = function () { fondo.remove(); document.removeEventListener('keydown', tecla); };
        var tecla = function (e) { if (e.key === 'Escape') cerrar(); };
        document.addEventListener('keydown', tecla);
        no.addEventListener('click', cerrar);
        fondo.addEventListener('click', function (e) { if (e.target === fondo) cerrar(); });
        si.addEventListener('click', function () {
            var texto = ta.value.trim();
            if (!texto) { ta.focus(); return; }
            si.disabled = true;
            var a = new Uint8Array(6); (window.crypto || window.msCrypto).getRandomValues(a);
            var id = 'I' + Date.now().toString(36) + Array.prototype.map.call(a, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
            if (!anon.checked && nom.value.trim()) S.set(K_NOMBRE, nom.value.trim());
            var titulo = (typeof EXAM_CONFIG !== 'undefined' && EXAM_CONFIG && EXAM_CONFIG.titulo) || document.title || ARCH;
            var d = { id: id, f: ARCH, h: S.huella(ctx.q), t: ctx.q.length > 220 ? ctx.q.slice(0, 217) + '…' : ctx.q, sup: titulo, n: ctx.n,
                      enun: ctx.enun, correcta: ctx.correcta, marcada: ctx.marcada, imp: texto, pub: pub.checked, anon: anon.checked,
                      nombre: anon.checked ? '' : nom.value.trim(), ts: Date.now(), env: false };
            var b = banco(); b.impugnaciones[id] = d; S.set(K_BANCO, b);
            enviar(d).then(function () { var x = banco(); if (x.impugnaciones[id]) { x.impugnaciones[id].env = true; S.set(K_BANCO, x); } cerrar(); marcar(i, true); })
                     .catch(function () { cerrar(); marcar(i, false); });
        });
    }

    function marcar(i, enviada) {
        var f = $('feed-' + i); if (!f) return;
        var b = f.querySelector('.impug-ok') || el('div', 'impug-ok'); b.textContent = enviada ? '✔ Impugnación enviada. Puedes verla en «Mi estudio».' : '⏳ Guardada en «Mi estudio»; se enviará cuando haya conexión.';
        f.querySelector('.feedback-body').appendChild(b);
    }

    function decorar() {
        estilo();
        document.querySelectorAll('.feedback').forEach(function (f) {
            if (f.querySelector('.impug-btn')) return;
            var m = /^feed-(\d+)$/.exec(f.id), body = f.querySelector('.feedback-body'); if (!m || !body) return;
            var i = +m[1], btn = el('button', 'impug-btn', '⚑ Impugnar esta pregunta'); btn.type = 'button';
            btn.addEventListener('click', function (e) { e.stopPropagation(); abrir(i); });
            body.appendChild(btn);
        });
    }
    var t; new MutationObserver(function () { clearTimeout(t); t = setTimeout(decorar, 50); }).observe(document.body, { childList: true, subtree: true });
    decorar(); reintentar();
})();

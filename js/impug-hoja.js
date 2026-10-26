/* Lector de pestañas de la hoja de cálculo (pública) sin servidor: «gviz» por JSONP.
   Lo usan la página «Impugnaciones» y «Mi estudio». Devuelve filas como objetos
   cuyas claves son las cabeceras normalizadas (minúsculas, sin tildes). */
(function () {
    'use strict';
    var S = window.SupC1 = window.SupC1 || {};
    var n = 0;
    function norm(t) { return String(t == null ? '' : t).normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, ' ').trim().toLowerCase(); }
    function celda(c) { if (!c) return ''; var v = c.v; if (v == null) return ''; return (c.f && typeof v !== 'boolean' && typeof v !== 'string') ? c.f : v; }
    S.normHoja = norm;
    S.leerHoja = function (sheetId, hoja, ok, ko) {
        var cb = 'supc1Hoja' + (++n), s = document.createElement('script'), fin = false;
        var limpiar = function () { try { delete window[cb]; } catch (e) { window[cb] = undefined; } if (s.parentNode) s.parentNode.removeChild(s); };
        window[cb] = function (r) {
            fin = true; limpiar();
            if (!r || r.status !== 'ok' || !r.table) { ko(new Error('hoja')); return; }
            var cols = r.table.cols.map(function (c) { return norm(c.label); });
            ok(r.table.rows.map(function (f, i) {
                var o = { _fila: i };
                cols.forEach(function (k, j) { if (k) o[k] = celda(f.c && f.c[j]); });
                return o;
            }));
        };
        s.onerror = function () { if (!fin) { fin = true; limpiar(); ko(new Error('red')); } };
        s.src = 'https://docs.google.com/spreadsheets/d/' + sheetId + '/gviz/tq?sheet=' + encodeURIComponent(hoja) + '&headers=1&tqx=responseHandler:' + cb;
        document.head.appendChild(s);
        setTimeout(function () { if (!fin) { fin = true; limpiar(); ko(new Error('tiempo')); } }, 20000);
    };
    // «Verdadero» para casillas de la hoja: TRUE, «sí», «x», «1»…
    S.esSi = function (v) { if (v === true) return true; var t = norm(v); return !!t && t !== 'false' && t !== 'no' && t !== '0'; };
    // Valor de una columna por el nombre configurado de su cabecera
    S.col = function (fila, nombre) {
        var k = norm(nombre);
        if (k in fila) return fila[k];
        // Si la cabecera de la hoja no se llama exactamente así (p. ej. «Respuesta correcta» o «Opcion marcada»), vale la que la contenga
        if (k === 'correcta' || k === 'marcada') { for (var c in fila) if (c !== 'respuesta' && c.indexOf(k) >= 0) return fila[c]; }
        return undefined;
    };

    // Campo «Pregunta» de la hoja: «12. texto de la pregunta ‖ A) opción ‖ B) opción…». Las filas antiguas solo traen el número.
    S.SEP_PREG = ' ‖ ';
    S.parsePregunta = function (v) {
        var p = String(v == null ? '' : v).split(/\s*‖\s*/), m = /^\s*(\d+)\s*[.)]\s*([\s\S]*)$/.exec(p[0] || ''), solo = /^\s*\d+\s*$/.test(p[0] || '');
        return { n: m ? m[1] : (solo ? p[0].trim() : ''), q: m ? m[2].trim() : (solo ? '' : String(p[0] || '').trim()), ops: p.slice(1).filter(Boolean) };
    };

    // Ventana de detalle de una impugnación (la usan «Resueltas», el foro y «Mi estudio»).
    // d = { sup, n, enun, q, ops[], correcta, marcada, texto, autor, resp, estado }
    S.detalleImpug = function (d) {
        var doc = document;
        function el(tag, cls, txt) { var e = doc.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
        if (!doc.getElementById('impug-det-css')) {
            var st = el('style'); st.id = 'impug-det-css';
            st.textContent = '.idet-fondo{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:10000;display:flex;align-items:center;justify-content:center;padding:16px}' +
                '.idet-caja{background:#fffefb;color:#2b2118;border-radius:12px;max-width:620px;width:100%;max-height:92vh;overflow:auto;padding:18px;font-size:.92rem;line-height:1.45}' +
                ':root[data-tema="oscuro"] .idet-caja{background:#2a1f19;color:#f1e6d8}' +
                '.idet-caja h3{margin:0 0 4px}.idet-caja h4{margin:14px 0 4px;font-size:.82rem;text-transform:uppercase;letter-spacing:.04em;opacity:.7}' +
                '.idet-meta{font-size:.8rem;opacity:.75;margin:0}.idet-enun{background:rgba(120,90,70,.12);padding:8px 10px;border-radius:8px;white-space:pre-line}' +
                '.idet-op{border:1px solid #c9a58a;border-radius:8px;padding:6px 10px;margin:5px 0;white-space:pre-line}' +
                '.idet-op.cor{border-color:#2d8c5a;background:rgba(45,140,90,.16)}.idet-op.mar:not(.cor){border-color:#a34a3a;background:rgba(163,74,58,.16)}' +
                '.idet-op small{font-weight:700;margin-left:6px}.idet-txt{white-space:pre-wrap;margin:0}.idet-resp{border-left:3px solid #2d8c5a;padding:4px 10px;white-space:pre-wrap}' +
                '.idet-cerrar{display:block;margin:16px 0 0 auto;font:inherit;font-weight:600;padding:8px 16px;border-radius:8px;border:1px solid #5c4033;background:#5c4033;color:#fff;cursor:pointer}';
            doc.head.appendChild(st);
        }
        var fondo = el('div', 'idet-fondo'), caja = el('div', 'idet-caja');
        fondo.setAttribute('role', 'dialog'); fondo.setAttribute('aria-modal', 'true');
        caja.appendChild(el('h3', null, 'Pregunta ' + (d.n || '')));
        caja.appendChild(el('p', 'idet-meta', [d.sup, d.autor, d.estado].filter(Boolean).join(' · ')));
        if (d.enun) { caja.appendChild(el('h4', null, 'Enunciado del supuesto')); caja.appendChild(el('div', 'idet-enun', d.enun)); }
        caja.appendChild(el('h4', null, 'Pregunta'));
        caja.appendChild(el('p', 'idet-txt', d.q || '(texto no disponible en esta impugnación antigua)'));
        var cor = String(d.correcta || ''), mar = String(d.marcada || '');
        // Las respuestas correcta/marcada vienen como «A) texto | B) texto»: se resaltan las que coinciden con cada opción
        var esDe = function (lista, op) { return lista.split(' | ').some(function (x) { return x.trim() === op.trim(); }); };
        if (d.ops && d.ops.length) {
            d.ops.forEach(function (op) {
                var c = esDe(cor, op), m = esDe(mar, op), o = el('div', 'idet-op' + (c ? ' cor' : '') + (m ? ' mar' : ''), op);
                if (c) o.appendChild(el('small', null, '✔ correcta')); if (m) o.appendChild(el('small', null, 'marcada'));
                caja.appendChild(o);
            });
        } else {
            if (cor) { caja.appendChild(el('h4', null, 'Respuesta correcta')); caja.appendChild(el('div', 'idet-op cor', cor.split(' | ').join('\n'))); }
            if (mar) { caja.appendChild(el('h4', null, 'Respuesta marcada')); caja.appendChild(el('div', 'idet-op mar', mar.split(' | ').join('\n'))); }
        }
        caja.appendChild(el('h4', null, 'Impugnación alegada')); caja.appendChild(el('p', 'idet-txt', d.texto || ''));
        if (d.resp) { caja.appendChild(el('h4', null, 'Respuesta')); caja.appendChild(el('div', 'idet-resp', d.resp)); }
        var b = el('button', 'idet-cerrar', 'Cerrar'); b.type = 'button'; caja.appendChild(b);
        fondo.appendChild(caja); doc.body.appendChild(fondo); b.focus();
        var cerrar = function () { fondo.remove(); doc.removeEventListener('keydown', tecla); };
        var tecla = function (e) { if (e.key === 'Escape') cerrar(); };
        doc.addEventListener('keydown', tecla);
        b.addEventListener('click', cerrar);
        fondo.addEventListener('click', function (e) { if (e.target === fondo) cerrar(); });
    };
})();

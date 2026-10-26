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
    S.col = function (fila, nombre) { return fila[norm(nombre)]; };
})();

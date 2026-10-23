/* Preferencias de visualización (tema y tamaño de letra).
   Se carga en el <head> y sin «defer» para aplicarlas antes de pintar la
   página y evitar el parpadeo de claro a oscuro. */
(function () {
    var d = document.documentElement;
    var S = window.SupC1 = window.SupC1 || {};
    S.get = function (k, def) {
        try { var v = localStorage.getItem('supc1:' + k); return v === null ? def : JSON.parse(v); }
        catch (e) { return def; }
    };
    S.set = function (k, v) { try { localStorage.setItem('supc1:' + k, JSON.stringify(v)); } catch (e) {} };
    S.del = function (k) { try { localStorage.removeItem('supc1:' + k); } catch (e) {} };
    S.setTema = function (oscuro) {
        if (oscuro) d.setAttribute('data-tema', 'oscuro'); else d.removeAttribute('data-tema');
        S.set('tema', oscuro ? 'oscuro' : 'claro');
        var m = document.querySelector('meta[name="theme-color"]');
        if (m) m.setAttribute('content', oscuro ? '#1d1511' : '#3d2a20');
    };
    S.setFuente = function (f) {
        if (f && f !== 'normal') d.setAttribute('data-fuente', f); else d.removeAttribute('data-fuente');
        S.set('fuente', f || 'normal');
    };
    if (S.get('tema', 'claro') === 'oscuro') d.setAttribute('data-tema', 'oscuro');
    var f = S.get('fuente', 'normal');
    if (f !== 'normal') d.setAttribute('data-fuente', f);
})();

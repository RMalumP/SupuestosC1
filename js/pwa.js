/* Service worker, aviso de «hay versión nueva» y banner de instalación.
   Se carga con «defer» en todas las páginas. La ruta del service worker se
   calcula a partir de la de este mismo script (está en js/, el service worker en la raíz), así vale desde cualquier carpeta. */
(function () {
    var S = window.SupC1 = window.SupC1 || {};
    var base = document.currentScript ? new URL('../', document.currentScript.src).href : '';

    var css = document.createElement('style');
    css.textContent =
        '.supc1-toast{position:fixed;left:50%;bottom:16px;transform:translateX(-50%);z-index:5000;max-width:min(92vw,520px);' +
        'background:#3d2a20;color:#fdf8f0;border:1px solid #8fc4d9;border-radius:14px;padding:12px 14px;display:flex;gap:12px;' +
        'align-items:center;box-shadow:0 10px 30px rgba(0,0,0,.35);font:600 .85rem/1.35 "Source Serif 4",Georgia,serif}' +
        '.supc1-toast button{font:700 .66rem "JetBrains Mono",monospace;letter-spacing:.1em;text-transform:uppercase;border:0;' +
        'border-radius:99px;padding:9px 14px;cursor:pointer;background:#8fc4d9;color:#2b2118;white-space:nowrap}' +
        '.supc1-toast .cerrar{background:transparent;color:#b8dceb;padding:6px}';
    document.head.appendChild(css);

    function toast(texto, accion, onAccion, claveNo) {
        var t = document.createElement('div');
        t.className = 'supc1-toast'; t.setAttribute('role', 'status');
        var s = document.createElement('span'); s.textContent = texto; t.appendChild(s);
        if (accion) {
            var b = document.createElement('button'); b.textContent = accion;
            b.onclick = function () { t.remove(); onAccion(); }; t.appendChild(b);
        }
        var x = document.createElement('button'); x.className = 'cerrar'; x.textContent = '✕'; x.setAttribute('aria-label', 'Cerrar');
        x.onclick = function () { t.remove(); if (claveNo) S.set(claveNo, true); }; t.appendChild(x);
        document.body.appendChild(t);
        return t;
    }

    /* ── Service worker + aviso de actualización ── */
    if ('serviceWorker' in navigator) {
        var recargar = false;
        navigator.serviceWorker.addEventListener('controllerchange', function () {
            if (recargar) location.reload();
        });
        var avisar = function (reg) {
            toast('Hay una versión nueva de la app.', 'Actualizar', function () {
                recargar = true;
                if (reg.waiting) reg.waiting.postMessage('SKIP_WAITING'); else location.reload();
            });
        };
        window.addEventListener('load', function () {
            navigator.serviceWorker.register(base + 'sw.js').then(function (reg) {
                if (reg.waiting && navigator.serviceWorker.controller) avisar(reg);
                reg.addEventListener('updatefound', function () {
                    var nuevo = reg.installing;
                    if (!nuevo) return;
                    nuevo.addEventListener('statechange', function () {
                        if (nuevo.state === 'installed' && navigator.serviceWorker.controller) avisar(reg);
                    });
                });
            }).catch(function () {});
        });
    }

    /* ── Banner de instalación (solo en el menú: <body data-instalar>) ── */
    var instalada = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
    var evento = null;
    window.addEventListener('beforeinstallprompt', function (e) { e.preventDefault(); evento = e; mostrar(); });
    window.addEventListener('appinstalled', function () { S.set('instalar-no', true); });
    function mostrar() {
        if (!document.body || !document.body.hasAttribute('data-instalar')) return;
        if (instalada || S.get('instalar-no', false) || document.querySelector('.supc1-toast.instalar')) return;
        var ios = /iphone|ipad|ipod/i.test(navigator.userAgent) && !evento;
        if (!evento && !ios) return;
        var t = toast(ios ? 'Instala la app: pulsa Compartir y «Añadir a pantalla de inicio».'
                          : 'Instala Supuestos C1 para usarla como una app, también sin conexión.',
                      ios ? '' : 'Instalar',
                      function () { evento.prompt(); evento.userChoice.then(function () { evento = null; }); },
                      'instalar-no');
        t.classList.add('instalar');
    }
    window.addEventListener('load', function () { setTimeout(mostrar, 1500); });
})();

#!/usr/bin/env node
/* PRUEBAS AUTOMÁTICAS DE LA WEB
   Abre las páginas en un navegador real (Chromium, vía Playwright) y comprueba:
     · carga       todas las páginas cargan sin errores de JavaScript
     · envios      lo que se manda a los formularios de Google es EXACTAMENTE lo de siempre
     · estilos     el aspecto no cambia sin querer (huella de los estilos de las zonas clave)
     · funciones   progreso, continuar, falladas, marcas, notas, atajos, deslizar, «practicar»…
     · menu        el menú y «Mi estudio» se pintan bien

   Uso:   npm test                      (o: node tests/run.js)
          node tests/run.js --actualizar   guarda como «correcto» el estado actual
          node tests/run.js envios         solo un grupo (carga|envios|estilos|funciones|menu|sync)

   Nada se envía a Google de verdad: las peticiones a docs.google.com se interceptan.
   Variables opcionales: PLAYWRIGHT_PATH (ruta al módulo playwright), CHROMIUM_PATH. */
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');

let pw;
try { pw = require('playwright'); } catch (e) { pw = require(process.env.PLAYWRIGHT_PATH || '/opt/node-tools/node_modules/playwright'); }

const RAIZ = path.resolve(__dirname, '..');
const GOLDEN = path.join(__dirname, 'golden');
const ACTUALIZAR = process.argv.includes('--actualizar');
const SOLO = process.argv.slice(2).filter(a => !a.startsWith('--'));
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
               '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.png': 'image/png', '.woff2': 'font/woff2' };

function servidor() {
    return new Promise(ok => {
        const s = http.createServer((req, res) => {
            let p = decodeURIComponent(req.url.split('?')[0]); if (p.endsWith('/')) p += 'index.html';
            const f = path.join(RAIZ, p);
            if (!f.startsWith(RAIZ) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); return res.end('no'); }
            res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(res);
        }).listen(0, '127.0.0.1', () => ok(s));
    });
}

const supuestos = fs.readdirSync(path.join(RAIZ, 'supuestos')).filter(f => f.endsWith('.html')).sort();
const plantillas = fs.readdirSync(path.join(RAIZ, 'Py')).filter(f => /^supuesto_plantilla_.*\.html$/.test(f)).sort();
let BASE, navegador;
const resultados = [];
const registrar = (grupo, nombre, ok, detalle) => { resultados.push({ grupo, nombre, ok, detalle }); console.log((ok ? '  ✔ ' : '  ✘ ') + nombre + (ok || !detalle ? '' : '\n      ' + String(detalle).replace(/\n/g, '\n      '))); };
const leerGolden = f => { try { return JSON.parse(fs.readFileSync(path.join(GOLDEN, f), 'utf8')); } catch (e) { return null; } };
const escribirGolden = (f, d) => fs.writeFileSync(path.join(GOLDEN, f), JSON.stringify(d, null, 1) + '\n');

/* Contexto determinista: sin red externa, sin azar, sin animaciones; guarda lo que se manda a Google */
async function contexto(vp, init) {
    const ctx = await navegador.newContext({ viewport: vp || { width: 1100, height: 800 }, reducedMotion: 'reduce', hasTouch: true });
    await ctx.addInitScript(() => { let s = 4242; Math.random = () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; }; });
    if (init) await ctx.addInitScript(init);
    ctx.google = [];
    await ctx.route('**/*', async r => {
        const u = new URL(r.request().url());
        if (u.hostname === '127.0.0.1' || u.hostname === 'localhost') return r.continue();
        if (u.hostname === 'docs.google.com' && /formResponse/.test(u.pathname)) { ctx.google.push({ url: u.origin + u.pathname, body: r.request().postData() || '' }); return r.fulfill({ status: 200, body: 'ok' }); }
        return r.abort();
    });
    return ctx;
}
async function abrir(ctx, url) {
    const pg = await ctx.newPage(); pg.errores = [];
    pg.on('pageerror', e => pg.errores.push(e.message)); pg.on('dialog', d => d.accept('Alumno Prueba'));
    await pg.goto(BASE + url); await pg.waitForTimeout(700);
    await pg.addStyleTag({ content: '*{animation:none!important;transition:none!important}' });
    return pg;
}
const salirDePagina = pg => pg.evaluate(() => { Object.defineProperty(document, 'hidden', { value: true, configurable: true }); document.dispatchEvent(new Event('visibilitychange')); });
const normalizar = t => decodeURIComponent((t || '').replace(/\+/g, ' ')).replace(/\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}(:\d{2})?/g, 'FECHA').replace(/Incorrecta: [^&]*/g, 'Incorrecta');

/* ───────── 1. carga ───────── */
async function carga() {
    const paginas = ['index.html', 'mi-estudio.html', 'resultados/resultados.html']
        .concat(supuestos.map(s => 'supuestos/' + s), plantillas.map(s => 'Py/' + s));
    const ctx = await contexto();
    for (const p of paginas) {
        const pg = await abrir(ctx, p);
        let msg = pg.errores.join(' | ');
        if (/supuestos\/|Py\//.test(p)) {
            const r = await pg.evaluate(() => ({ n: questions.length, m: document.querySelectorAll('.btn-marcar').length, estilo: getComputedStyle(document.querySelector('.question-card')).borderRadius }));
            if (!r.n) msg += ' sin preguntas';
            if (r.m !== r.n) msg += ' faltan botones de marcar (' + r.m + '/' + r.n + ')';
            if (r.estilo !== '14px') msg += ' no se aplica el tema (radio ' + r.estilo + ')';
        }
        registrar('carga', 'carga ' + p, !msg, msg);
        await pg.close();
    }
    await ctx.close();
}

/* ───────── 2. envíos a Google ───────── */
async function envios() {
    const nuevo = {};
    for (const s of supuestos) {
        const ctx = await contexto(); const pg = await abrir(ctx, 'supuestos/' + s);
        await pg.evaluate(() => {
            for (let i = 0; i < Math.min(7, questions.length); i++) {
                const corr = document.getElementById('qcard-' + i).dataset.correct.split(',').map(Number);
                if (i < 6) corr.forEach(k => selectAnswer(i, k)); else { let k = 0; while (corr.includes(k)) k++; selectAnswer(i, k); }
            }
            window.confirm = () => true; evaluateExam();
        });
        await pg.waitForTimeout(1200);
        await pg.evaluate(() => document.getElementById('send-btn').click()); await pg.waitForTimeout(900);
        nuevo[s] = ctx.google.map(g => ({ url: g.url, body: normalizar(g.body).split('&') }));
        const gold = leerGolden('envios.json');
        if (!ACTUALIZAR) {
            const ok = gold && JSON.stringify(gold[s]) === JSON.stringify(nuevo[s]);
            registrar('envios', 'envíos a Google idénticos · ' + s + ' (' + nuevo[s].length + ' peticiones)', !!ok, gold ? 'Cambió lo que se manda al formulario (ver tests/golden/envios.json)' : 'no hay referencia: ejecuta con --actualizar');
        }
        await ctx.close();
    }
    if (ACTUALIZAR) { escribirGolden('envios.json', nuevo); registrar('envios', 'referencia de envíos guardada', true); }
}

/* ───────── 3. estilos ───────── */
const ZONAS = ['body', '#nav-header', '#timer', '.inst-header', '.block-header', '.question-card.active', '.option', '.btn-zone', '.progress-bar-wrap', '#settings-panel'];
/* Solo se miran estas propiedades visuales, siempre las mismas: cada versión de Chromium lista un
   conjunto distinto de propiedades «calculadas», y comparar todas hacía que las referencias guardadas
   en un ordenador fallaran en otro (por ejemplo, en GitHub). Tampoco se miran las medidas que dependen
   de las fuentes del sistema (ancho y alto). */
const PROPS_VISUALES = ['display', 'position', 'visibility', 'opacity', 'z-index', 'overflow-x', 'overflow-y',
    'color', 'background-color', 'background-image', 'box-shadow', 'text-shadow', 'filter', 'transform',
    'border-top-color', 'border-top-width', 'border-top-style', 'border-right-color', 'border-right-width', 'border-right-style',
    'border-bottom-color', 'border-bottom-width', 'border-bottom-style', 'border-left-color', 'border-left-width', 'border-left-style',
    'border-top-left-radius', 'border-top-right-radius', 'border-bottom-left-radius', 'border-bottom-right-radius',
    'outline-style', 'outline-width', 'outline-color',
    'font-family', 'font-size', 'font-weight', 'font-style', 'line-height', 'letter-spacing', 'text-transform', 'text-align',
    'text-decoration-line', 'white-space', 'cursor',
    'margin-top', 'margin-bottom', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'flex-direction', 'flex-wrap', 'align-items', 'justify-content', 'gap', 'grid-template-columns'];
async function huellas(pg) {
    return pg.evaluate(([zonas, props]) => {
        const h = s => { let a = 0xdeadbeef, b = 0x41c6ce57; for (let i = 0; i < s.length; i++) { const c = s.charCodeAt(i); a = Math.imul(a ^ c, 2654435761); b = Math.imul(b ^ c, 1597334677); } a = Math.imul(a ^ (a >>> 16), 2246822507) ^ Math.imul(b ^ (b >>> 13), 3266489909); return (a >>> 0).toString(36); };
        const out = {};
        zonas.forEach(z => {
            const el = document.querySelector(z); if (!el) { out[z] = 'ausente'; return; }
            const todos = [el].concat([...el.querySelectorAll('*')]).filter(e => !['SCRIPT', 'STYLE'].includes(e.tagName));
            let s = '';
            todos.forEach(e => { const cs = getComputedStyle(e); props.forEach(p => { s += p + ':' + cs.getPropertyValue(p) + ';'; }); s += '|'; });
            out[z] = h(s) + '/' + todos.length;
        });
        return out;
    }, [ZONAS, PROPS_VISUALES]);
}
async function estilos() {
    const nuevo = {}; const gold = leerGolden('estilos.json');
    const paginas = ['index.html'].concat(supuestos.map(s => 'supuestos/' + s));
    for (const [vn, vp] of [['pc', { width: 1100, height: 800 }], ['movil', { width: 390, height: 800 }]]) {
        const ctx = await contexto(vp);
        for (const p of paginas) {
            const pg = await abrir(ctx, p);
            if (p.startsWith('supuestos/')) await pg.evaluate(() => { selectAnswer(0, 0); });
            nuevo[vn + ' ' + p] = await huellas(pg); await pg.close();
        }
        await ctx.close();
    }
    if (ACTUALIZAR) { escribirGolden('estilos.json', nuevo); return registrar('estilos', 'referencia de estilos guardada (' + Object.keys(nuevo).length + ' vistas)', true); }
    Object.keys(nuevo).forEach(k => {
        const g = gold && gold[k]; const dif = g ? ZONAS.filter(z => g[z] !== nuevo[k][z]) : ['sin referencia'];
        registrar('estilos', 'aspecto sin cambios · ' + k, !dif.length, 'cambian estas zonas: ' + dif.join(', ') + '\n(si es intencionado: npm run test:actualizar)');
    });
}

/* ───────── 4. funciones ───────── */
async function funciones() {
    const T = 'supuestos/supuesto_T2I.html', id = 'supuesto_T2I';
    const caso = async (nombre, fn) => { try { const r = await fn(); registrar('funciones', nombre, r === true || r === undefined, r === true || r === undefined ? '' : r); } catch (e) { registrar('funciones', nombre, false, e.message.split('\n')[0]); } };
    const ls = (pg, k) => pg.evaluate(k => SupC1.get(k, null), k);

    await caso('guarda el progreso al corregir y deja el historial', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await pg.evaluate(() => { selectAnswer(0, 0); window.confirm = () => true; evaluateExam(); }); await pg.waitForTimeout(1800);
        const p = await ls(pg, 'prog:' + id); await ctx.close();
        return (p && p.intentos === 1 && p.hist && p.hist.length === 1 && p.hist[0].seg >= 0) || 'prog = ' + JSON.stringify(p);
    });
    await caso('ofrece continuar un intento a medias y restaura respuestas y opciones', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await pg.evaluate(() => { selectAnswer(0, 0); selectAnswer(1, 1); }); await pg.waitForTimeout(1800);
        const antes = await pg.evaluate(() => [...document.querySelectorAll('#qcard-0 .option span:last-child')].map(x => x.textContent));
        await pg.reload(); await pg.waitForTimeout(900);
        if (!(await pg.locator('.supc1-modal [data-r="si"]').count())) return 'no sale el aviso';
        await pg.click('.supc1-modal [data-r="si"]'); await pg.waitForTimeout(300);
        const r = await pg.evaluate(() => ({ a: JSON.stringify(userAns), o: [...document.querySelectorAll('#qcard-0 .option span:last-child')].map(x => x.textContent) }));
        await ctx.close();
        return (r.a === '{"0":[0],"1":[1]}' && JSON.stringify(r.o) === JSON.stringify(antes)) || JSON.stringify(r);
    });
    await caso('«repetir solo las falladas» no envía nada a Google', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await pg.evaluate(() => { selectAnswer(0, 0); window.confirm = () => true; evaluateExam(); }); await pg.waitForTimeout(1500);
        const antes = ctx.google.length;
        await pg.evaluate(() => document.getElementById('falladas-btn').click()); await pg.waitForTimeout(400);
        await pg.evaluate(() => { selectAnswer(0, 0); evaluateExam(); }); await pg.waitForTimeout(1500);
        const oculto = await pg.evaluate(() => getComputedStyle(document.getElementById('send-btn')).display === 'none');
        await pg.evaluate(() => enviarResultados()); await pg.waitForTimeout(500);
        const n = ctx.google.length - antes; await ctx.close();
        return (n === 0 && oculto) || ('envíos extra: ' + n + ', botón oculto: ' + oculto);
    });
    await caso('con la recogida anónima apagada, salir de la página no envía nada', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await pg.evaluate(() => { selectAnswer(0, 0); selectAnswer(1, 0); }); await salirDePagina(pg); await pg.waitForTimeout(500);
        const n = ctx.google.length; await ctx.close(); return n === 0 || n + ' envíos';
    });
    await caso('el banco de falladas: entra al fallar y sale tras acertar dos veces', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        const fallar = () => pg.evaluate(() => { const c = document.getElementById('qcard-0').dataset.correct.split(',').map(Number); let k = 0; while (c.includes(k)) k++; selectAnswer(0, k); window.confirm = () => true; evaluateExam(); });
        const acertar = () => pg.evaluate(() => { const c = document.getElementById('qcard-0').dataset.correct.split(',').map(Number); c.forEach(k => selectAnswer(0, k)); window.confirm = () => true; evaluateExam(); });
        const n = async () => (await ls(pg, 'banco') || { falladas: {} }).falladas ? Object.keys((await ls(pg, 'banco')).falladas).length : 0;
        await fallar(); await pg.waitForTimeout(1800); const a = await n();
        await pg.goto(BASE + T); await pg.waitForTimeout(700); await pg.evaluate(() => { const m = document.querySelector('.supc1-modal [data-r="no"]'); if (m) m.click(); });
        await acertar(); await pg.waitForTimeout(1800); const b = await n();
        await pg.goto(BASE + T); await pg.waitForTimeout(700); await pg.evaluate(() => { const m = document.querySelector('.supc1-modal [data-r="no"]'); if (m) m.click(); });
        await acertar(); await pg.waitForTimeout(1800); const c = await n(); await ctx.close();
        return (a === 1 && b === 1 && c === 0) || 'falladas tras fallar/acertar/acertar: ' + [a, b, c];
    });
    await caso('atajos de teclado: responder, moverse, marcar y nota', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await pg.keyboard.press('b'); await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('3'); await pg.keyboard.press('ArrowLeft');
        await pg.keyboard.press('m'); await pg.keyboard.press('n'); await pg.keyboard.type('nota'); await pg.waitForTimeout(700);
        const r = await pg.evaluate(() => ({ a: JSON.stringify(userAns), cur: current, marc: document.getElementById('nav-0').classList.contains('marcada'),
            nota: Object.values(SupC1.get('banco', {}).notas || {}).map(x => x.txt).join() }));
        await ctx.close();
        return (r.a === '{"0":[1],"1":[2]}' && r.cur === 0 && r.marc && r.nota === 'nota') || JSON.stringify(r);
    });
    await caso('corazón de favoritas: guarda, aparece en «Mi estudio», se practica y se puede desactivar', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        const hay = await pg.evaluate(() => document.querySelectorAll('.btn-corazon').length === questions.length);
        await pg.click('#qcard-0 .btn-corazon'); await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('h');
        const fav = await pg.evaluate(() => Object.keys(SupC1.get('banco', {}).favoritas || {}).length);
        await pg.keyboard.press('h');
        const tras = await pg.evaluate(() => ({ n: Object.keys(SupC1.get('banco', {}).favoritas).length, lap: Object.keys(SupC1.get('banco', {}).borradas) }));
        const et = await pg.evaluate(() => document.querySelector('#qcard-0 .btn-marcar span').textContent);
        const est = await ctx.newPage(); await est.goto(BASE + 'mi-estudio.html'); await est.waitForTimeout(500);
        const mi = await est.evaluate(() => ({ items: document.querySelectorAll('#estudio-favoritas .item').length, href: (document.querySelector('#estudio-favoritas .btn-practicar') || {}).href || '' }));
        await pg.goto(BASE + T + '?practicar=favoritas'); await pg.waitForTimeout(900);
        const pr = await pg.evaluate(() => ({ n: questions.length, p: document.body.classList.contains('intento-parcial') }));
        await pg.evaluate(() => SupC1.set('corazon', false)); await pg.goto(BASE + T); await pg.waitForTimeout(700);
        const oculto = await pg.evaluate(() => getComputedStyle(document.querySelector('#qcard-0 .btn-corazon')).display === 'none');
        await pg.keyboard.press('h'); const sigue = await pg.evaluate(() => Object.keys(SupC1.get('banco', {}).favoritas).length);
        await ctx.close();
        return (hay && fav === 2 && tras.n === 1 && tras.lap.length === 1 && /^v:/.test(tras.lap[0]) && /Marcar para más tarde/.test(et) &&
                mi.items === 1 && /practicar=favoritas/.test(mi.href) && pr.n === 1 && pr.p && oculto && sigue === 1) || JSON.stringify({ hay, fav, tras, et, mi, pr, oculto, sigue });
    });
    await caso('corazón desactivado desde el supuesto (config.corazon:false)', async () => {
        const ctx = await contexto();
        await ctx.route('**/supuestos/supuesto_T2I.html', async r => { const res = await r.fetch(); r.fulfill({ response: res, body: (await res.text()).replace('"referencia"', '"corazon": false, "referencia"') }); });
        const pg = await abrir(ctx, T);
        const r = await pg.evaluate(() => ({ cfg: EXAM_CONFIG.corazon, n: document.querySelectorAll('.btn-corazon').length, fila: !!document.getElementById('corazon-toggle') }));
        await ctx.close();
        return (r.cfg === false && r.n === 0 && !r.fila) || JSON.stringify(r);
    });
    const seleccionar = (pg, sel, ini, fin) => pg.evaluate(([sel, ini, fin]) => {
        document.querySelector(sel).scrollIntoView({ block: 'center' });
        const n = document.querySelector(sel).firstChild, r = document.createRange(); r.setStart(n, ini); r.setEnd(n, fin);
        const s = getSelection(); s.removeAllRanges(); s.addRange(r);
    }, [sel, ini, fin]);
    await caso('subrayar: elegir color, se guarda, sobrevive a recargar, se recolorea y se quita', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await seleccionar(pg, '#qcard-0 .q-text', 3, 20); await pg.waitForSelector('.subr-pop', { timeout: 3000 });
        await pg.click('.subr-pop .subr-punto.subr-c2'); await pg.waitForTimeout(200);
        const a = await pg.evaluate(() => ({ marcas: [...document.querySelectorAll('#qcard-0 .q-text mark.subr')].map(m => m.className + '|' + m.textContent).join(), n: Object.keys(SupC1.get('banco', {}).subrayados).length, pop: !!document.querySelector('.subr-pop') }));
        await seleccionar(pg, '#qcard-0 .options-grid .option span:last-child', 3, 15); await pg.waitForSelector('.subr-pop'); await pg.click('.subr-pop .subr-punto.subr-c3'); await pg.waitForTimeout(200);
        const resp = await pg.evaluate(() => ({ n: Object.keys(SupC1.get('banco', {}).subrayados).length, ans: JSON.stringify(userAns), m: document.querySelectorAll('#qcard-0 .option mark.subr').length }));
        await pg.reload(); await pg.waitForTimeout(900); const modal = await pg.locator('.supc1-modal [data-r="no"]').count(); if (modal) await pg.click('.supc1-modal [data-r="no"]');
        await pg.waitForTimeout(300);
        const tras = await pg.evaluate(() => document.querySelectorAll('mark.subr').length);
        await pg.click('#qcard-0 .q-text mark.subr'); await pg.waitForSelector('.subr-pop'); await pg.click('.subr-pop .subr-punto.subr-c0'); await pg.waitForTimeout(150);
        const color = await pg.evaluate(() => document.querySelector('#qcard-0 .q-text mark.subr').className);
        await pg.click('#qcard-0 .q-text mark.subr'); await pg.waitForSelector('.subr-pop .subr-quitar'); await pg.click('.subr-pop .subr-quitar'); await pg.waitForTimeout(150);
        const fin = await pg.evaluate(() => ({ n: Object.keys(SupC1.get('banco', {}).subrayados).length, lap: Object.keys(SupC1.get('banco', {}).borradas).filter(k => /^u:/.test(k)).length, m: document.querySelectorAll('#qcard-0 .q-text mark.subr').length }));
        await ctx.close();
        return (/subr-c2\|/.test(a.marcas) && a.n === 1 && !a.pop && resp.n === 2 && resp.ans === '{}' && resp.m === 1 && tras === 2 && /subr-c0/.test(color) && fin.n === 1 && fin.lap === 1 && fin.m === 0) || JSON.stringify({ a, resp, tras, color, fin });
    });
    await caso('subrayar: lo nuevo sustituye a lo solapado y arrastrar para seleccionar no responde', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await seleccionar(pg, '#qcard-0 .q-text', 3, 20); await pg.waitForSelector('.subr-pop'); await pg.click('.subr-pop .subr-punto.subr-c0'); await pg.waitForTimeout(150);
        await seleccionar(pg, '#qcard-0 .q-text mark.subr', 2, 8); await pg.waitForSelector('.subr-pop .subr-quitar');
        await pg.click('.subr-pop .subr-punto.subr-c1'); await pg.waitForTimeout(150);
        const r = await pg.evaluate(() => ({ n: Object.keys(SupC1.get('banco', {}).subrayados).length, c: [...document.querySelectorAll('#qcard-0 .q-text mark.subr')].map(m => m.className).join() }));
        await seleccionar(pg, '#qcard-0 .options-grid .option span:last-child', 0, 6); await pg.waitForTimeout(100);
        await pg.evaluate(() => document.querySelector('#qcard-0 .option').click());
        const resp = await pg.evaluate(() => JSON.stringify(userAns)); await ctx.close();
        return (r.n === 1 && /subr-c1/.test(r.c) && resp === '{}') || JSON.stringify({ r, resp });
    });
    await caso('subrayar se puede apagar (en el panel ⚙ y desde el supuesto)', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await pg.evaluate(() => SupC1.set('subrayar', false)); await pg.reload(); await pg.waitForTimeout(800);
        await seleccionar(pg, '#qcard-0 .q-text', 3, 20); await pg.waitForTimeout(500);
        const pop = await pg.locator('.subr-pop').count(); const fila = await pg.locator('#subrayar-toggle').isChecked();
        await ctx.close();
        const c2 = await contexto();
        await c2.route('**/supuestos/supuesto_T2I.html', async r => { const res = await r.fetch(); r.fulfill({ response: res, body: (await res.text()).replace('"referencia"', '"subrayar": false, "referencia"') }); });
        const p2 = await abrir(c2, T); await seleccionar(p2, '#qcard-0 .q-text', 3, 20); await p2.waitForTimeout(500);
        const r2 = { pop: await p2.locator('.subr-pop').count(), fila: await p2.locator('#subrayar-toggle').count() }; await c2.close();
        return (pop === 0 && fila === false && r2.pop === 0 && r2.fila === 0) || JSON.stringify({ pop, fila, r2 });
    });
    await caso('subrayar en «Mi estudio»: en las preguntas guardadas y en el listado de subrayados', async () => {
        const ctx = await contexto(null, () => { if (localStorage.getItem('supc1:sembrado')) return; localStorage.setItem('supc1:sembrado', '1');
            localStorage.setItem('supc1:banco', JSON.stringify({ falladas: { 'supuesto_T2I:a': { f: 'supuesto_T2I', h: 'a', t: 'Pregunta fallada de prueba para subrayar', n: 2, ok: 0 } }, marcadas: {}, notas: {} })); });
        const pg = await abrir(ctx, 'mi-estudio.html');
        await seleccionar(pg, '#estudio-falladas .item-zona', 9, 16); await pg.waitForSelector('.subr-pop'); await pg.click('.subr-pop .subr-punto.subr-c4'); await pg.waitForTimeout(500);
        const r = await pg.evaluate(() => ({ en: document.querySelectorAll('#estudio-falladas mark.subr').length, lista: document.querySelectorAll('#estudio-subrayados .item mark.subr').length, n: Object.keys(SupC1.get('banco', {}).subrayados).length, txt: document.querySelector('#estudio-falladas .item-zona').textContent }));
        await pg.reload(); await pg.waitForTimeout(700); const tras = await pg.evaluate(() => document.querySelectorAll('#estudio-falladas mark.subr').length);
        await pg.click('#estudio-subrayados .btn-link'); await pg.waitForTimeout(400);
        const fin = await pg.evaluate(() => ({ lista: document.querySelectorAll('#estudio-subrayados .item').length, marcas: document.querySelectorAll('mark.subr').length }));
        await ctx.close();
        return (r.en === 1 && r.lista === 1 && r.n === 1 && r.txt === 'Pregunta fallada de prueba para subrayar' && tras === 1 && fin.lista === 0 && fin.marcas === 0) || JSON.stringify({ r, tras, fin });
    });
    await caso('deslizar el dedo cambia de pregunta', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T); const cdp = await ctx.newCDPSession(pg);
        const toque = async (x1, x2) => { await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: x1, y: 400 }] }); await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x: (x1 + x2) / 2, y: 400 }] }); await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] }); await pg.waitForTimeout(250); };
        await toque(800, 300); const a = await pg.evaluate(() => current); await toque(300, 800); const b = await pg.evaluate(() => current); await ctx.close();
        return (a === 1 && b === 0) || [a, b];
    });
    await caso('?practicar=falladas y ?practicar=marcadas abren un intento parcial', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        await pg.evaluate(() => { const c = document.getElementById('qcard-0').dataset.correct.split(',').map(Number); let k = 0; while (c.includes(k)) k++; selectAnswer(0, k); window.confirm = () => true; evaluateExam(); }); await pg.waitForTimeout(1800);
        await pg.goto(BASE + T + '?practicar=falladas'); await pg.waitForTimeout(900);
        const f = await pg.evaluate(() => ({ n: questions.length, p: document.body.classList.contains('intento-parcial'), u: location.search }));
        await pg.evaluate(() => { SupC1.sup.marcar(0); }); await pg.goto(BASE + T + '?practicar=marcadas'); await pg.waitForTimeout(900);
        const m = await pg.evaluate(() => ({ n: questions.length, p: document.body.classList.contains('intento-parcial') })); await ctx.close();
        return (f.n === 1 && f.p && f.u === '' && m.n === 1 && m.p) || JSON.stringify([f, m]);
    });
    await caso('accesibilidad básica: roles, etiquetas y enlaces a la norma', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, T);
        const r = await pg.evaluate(() => ({ radios: document.querySelectorAll('.option[role=radio]').length, opciones: document.querySelectorAll('.option').length,
            nav: document.querySelectorAll('.nav-box[role=button][aria-label]').length, navs: document.querySelectorAll('.nav-box').length,
            norma: document.querySelectorAll('.enlace-norma').length, salto: !!document.querySelector('.saltar-contenido') }));
        await ctx.close();
        return (r.radios === r.opciones && r.nav === r.navs && r.norma > 0 && r.salto) || JSON.stringify(r);
    });
}

/* ───────── 5. menú y «Mi estudio» ───────── */
async function menu() {
    const caso = async (nombre, fn) => { try { const r = await fn(); registrar('menu', nombre, r === true, r === true ? '' : r); } catch (e) { registrar('menu', nombre, false, e.message.split('\n')[0]); } };
    await caso('el menú pinta todas las tarjetas de supuestos-datos.js', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, 'index.html');
        const r = await pg.evaluate(() => { const D = window.SUPUESTOS_DATOS; let n = (D.examenes || []).length; D.secciones.forEach(s => s.grupos.forEach(g => n += g.items.length));
            return { esperadas: n, pintadas: document.querySelectorAll('#menu-supuestos .supuesto-card, #examenes-grid .supuesto-card').length, secciones: document.querySelectorAll('.seccion').length }; });
        await ctx.close(); return (r.esperadas === r.pintadas && r.secciones === 2) || JSON.stringify(r);
    });
    await caso('buscador y filtros', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, 'index.html');
        await pg.fill('#buscar', 'zzzzzz'); const vacio = await pg.locator('.vacio').isVisible();
        await pg.fill('#buscar', 'tema 2'); const n = await pg.locator('#menu-supuestos .supuesto-card:visible').count(); await ctx.close();
        return (vacio && n > 0) || JSON.stringify({ vacio, n });
    });
    await caso('el service worker guarda sin conexión todos los supuestos del menú (aunque no estén en sw.js)', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, 'index.html');
        const r = await pg.evaluate(async () => {
            await navigator.serviceWorker.ready;
            const claves = await caches.keys(); const c = await caches.open(claves.filter(k => k.startsWith('supuestos-c1-'))[0]);
            const guardados = (await c.keys()).map(q => new URL(q.url).pathname);
            return { esperados: SUPUESTOS_DATOS.lista.map(i => '/supuestos/' + i.archivo + '.html'), guardados };
        });
        await ctx.close();
        const faltan = r.esperados.filter(e => !r.guardados.includes(e));
        return (r.esperados.length === 9 && faltan.length === 0) || 'faltan ' + faltan.join();
    });
    await caso('«Información» abre los créditos con la versión y pulsar en cualquier parte los cierra', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, 'index.html');
        const antes = await pg.evaluate(() => document.getElementById('creditos').hidden);
        await pg.click('#btn-info');
        const abierto = await pg.evaluate(() => !document.getElementById('creditos').hidden && /^v\d/.test(document.getElementById('version-app').textContent));
        await pg.mouse.click(5, 5);
        const cerrado = await pg.evaluate(() => document.getElementById('creditos').hidden);
        await ctx.close(); return (antes && abierto && cerrado) || JSON.stringify({ antes, abierto, cerrado });
    });
    await caso('el aviso de datos anónimos no aparece con la recogida apagada', async () => {
        const ctx = await contexto(); const pg = await abrir(ctx, 'index.html'); const n = await pg.locator('.aviso-pie').count(); await ctx.close(); return n === 0 || 'aparece';
    });
    await caso('«Mi estudio» muestra estadísticas, falladas y notas', async () => {
        const ctx = await contexto(null, () => {
            const r = p => ({ pct: p, puntos: p / 4, max: 25, aciertos: 10, fallos: 3, blancos: 2, total: 25, seg: 900, fecha: 1 });
            localStorage.setItem('supc1:prog:supuesto_T2I', JSON.stringify({ intentos: 2, mejor: r(70), ultima: r(70), hist: [r(50), r(70)] }));
            localStorage.setItem('supc1:banco', JSON.stringify({ falladas: { 'supuesto_T2I:a': { f: 'supuesto_T2I', h: 'a', t: 'Pregunta fallada', n: 2, ok: 0 } }, marcadas: {}, notas: { 'supuesto_T2I:b': { f: 'supuesto_T2I', h: 'b', t: 'Otra', txt: 'mi nota', ts: 1 } } }));
        });
        const pg = await abrir(ctx, 'mi-estudio.html');
        const r = await pg.evaluate(() => ({ datos: document.querySelectorAll('.dato').length, evo: document.querySelectorAll('.supuesto-card.evo').length, spark: document.querySelectorAll('.spark').length,
            falladas: document.querySelectorAll('#estudio-falladas .item').length, notas: document.querySelectorAll('#estudio-marcadas .item-nota').length,
            volver: document.querySelectorAll('.back-link.boton').length, aviso: !!document.querySelector('.aviso-privado'),
            enlace: (document.querySelector('a.btn-practicar') || {}).getAttribute && document.querySelector('a.btn-practicar').getAttribute('href') }));
        const err = pg.errores.join(); await ctx.close();
        return (r.datos === 4 && r.evo === 1 && r.spark === 1 && r.falladas === 1 && r.notas === 1 && /practicar=falladas/.test(r.enlace) && r.volver === 2 && r.aviso && !err) || JSON.stringify(r) + err;
    });
}


/* ───────── 6. sincronización con Google Drive (con un Google simulado) ───────── */
function driveFalso() {
    const est = { contenido: null }, CORS = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' };
    const ok = (route, cuerpo, tipo) => (route.fulfill({ status: 200, headers: Object.assign({ 'cache-control': 'no-store' }, CORS), contentType: tipo || 'application/json', body: cuerpo }));
    return { est, manejar: async route => {
        const r = route.request(), u = new URL(r.url());
        if (r.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: CORS });
        if (u.pathname === '/drive/v3/files' && r.method() === 'GET') return ok(route, JSON.stringify({ files: est.contenido ? [{ id: 'F1', name: 'supc1-sync.json' }] : [] }));
        if (u.pathname === '/drive/v3/files/F1' && u.searchParams.get('alt') === 'media') return ok(route, est.contenido);
        if (u.pathname === '/upload/drive/v3/files' && r.method() === 'POST') {
            const lim = /boundary=(\S+)/.exec(r.headers()['content-type'] || '')[1];
            est.contenido = (r.postData().split('--' + lim)[2].split('\r\n\r\n')[1] || '').replace(/\r\n$/, ''); return ok(route, '{"id":"F1"}');
        }
        if (u.pathname === '/upload/drive/v3/files/F1' && r.method() === 'PATCH') { est.contenido = r.postData(); return ok(route, '{"id":"F1"}'); }
        return route.fulfill({ status: 404, headers: CORS, body: 'no' });
    } };
}
async function dispositivo(drive, sembrar, opciones) {
    opciones = opciones || {};
    const ctx = await contexto({ width: 1000, height: 900 }, sembrar);
    await ctx.route('**/sync-config.js', r => r.fulfill({ contentType: 'text/javascript', body: opciones.sinId ? 'window.SUPC1_SYNC={clientId:""};' : 'window.SUPC1_SYNC={clientId:"prueba.apps.googleusercontent.com",archivo:"supc1-sync.json"};' }));
    await ctx.route('https://accounts.google.com/gsi/client', r => r.fulfill({ contentType: 'text/javascript', body:
        'window.google={accounts:{oauth2:{initTokenClient:function(c){return{requestAccessToken:function(){setTimeout(function(){' +
        (opciones.deniega ? 'c.error_callback({type:"popup_closed"})' : 'c.callback({access_token:"tok"})') + '},30)}}}}}};' }));
    await ctx.route('https://www.googleapis.com/**', drive.manejar);
    return ctx;
}
const hay = (pg, sel) => pg.locator(sel).count();
async function sync() {
    const caso = async (nombre, fn) => { try { const r = await fn(); registrar('sync', nombre, r === true, r === true ? '' : r); } catch (e) { registrar('sync', nombre, false, e.message.split('\n')[0]); } };
    const N = require(path.join(RAIZ, 'js', 'app-sync.js'));
    const e = (ts, t) => ({ f: 'supuesto_T2I', h: 'x', t: t || 'p', ts, n: 1, ok: 0 });

    await caso('fusión: une lo de los dos dispositivos y gana lo más reciente', async () => {
        const A = { falladas: { 'a': e(10) }, marcadas: {}, notas: { 'n': { txt: 'vieja', ts: 5, t: 'p' } }, borradas: {} };
        const B = { falladas: { 'b': e(20) }, marcadas: {}, notas: { 'n': { txt: 'nueva', ts: 9, t: 'p' } }, borradas: {} };
        const M = N.mezclarBanco(A, B);
        return (Object.keys(M.falladas).sort().join() === 'a,b' && M.notas.n.txt === 'nueva') || JSON.stringify(M);
    });
    await caso('fusión: lo borrado no resucita y lo vuelto a crear sí', async () => {
        const A = { falladas: {}, marcadas: {}, notas: {}, borradas: { 'n:n': 50, 'm:m': 10 } };
        const B = { falladas: {}, marcadas: { 'm': { ts: 30, t: 'p' } }, notas: { 'n': { txt: 'x', ts: 40, t: 'p' } }, borradas: {} };
        const M = N.mezclarBanco(A, B, 100);
        return (!M.notas.n && M.marcadas.m && M.borradas['n:n'] === 50) || JSON.stringify(M);
    });
    await caso('fusión: las favoritas se unen y un quitar corazón posterior gana', async () => {
        const A = { favoritas: { f1: { ts: 10, t: 'a' }, f2: { ts: 10, t: 'b' } }, borradas: {} };
        const B = { favoritas: { f1: { ts: 5, t: 'a' } }, borradas: { 'v:f2': 20 } };
        const M = N.mezclarBanco(A, B, 100);
        return (M.favoritas.f1 && !M.favoritas.f2 && M.borradas['v:f2'] === 20) || JSON.stringify(M);
    });
    await caso('fusión: los subrayados se unen y quitar uno gana si es más reciente', async () => {
        const A = { subrayados: { u1: { ts: 10, x: 'a' }, u2: { ts: 10, x: 'b' } }, borradas: {} };
        const B = { subrayados: { u3: { ts: 12, x: 'c' } }, borradas: { 'u:u2': 20 } };
        const M = N.mezclarBanco(A, B, 100);
        return (M.subrayados.u1 && M.subrayados.u3 && !M.subrayados.u2 && M.borradas['u:u2'] === 20) || JSON.stringify(M);
    });
    await caso('fusión: es conmutativa e idempotente', async () => {
        const A = { falladas: { a: e(10) }, marcadas: { m: { ts: 3, t: 'p' } }, notas: {}, borradas: { 'n:z': 7 } };
        const B = { falladas: { a: e(12), b: e(2) }, marcadas: {}, notas: { n: { txt: 'x', ts: 4, t: 'p' } }, borradas: { 'm:m': 9 } };
        const ab = JSON.stringify(N.mezclarBanco(A, B, 100)), ba = JSON.stringify(N.mezclarBanco(B, A, 100)), aba = JSON.stringify(N.mezclarBanco(JSON.parse(ab), B, 100));
        return (ab === ba && ab === aba) || [ab, ba, aba].join('\n');
    });
    await caso('fusión de estadísticas: une historiales sin duplicar y recalcula mejor y última', async () => {
        const r = (p, f) => ({ pct: p, fecha: f, total: 25, seg: 900 });
        const A = { intentos: 2, mejor: r(70, 2), ultima: r(70, 2), hist: [r(50, 1), r(70, 2)] };
        const B = { intentos: 2, mejor: r(80, 3), ultima: r(80, 3), hist: [r(70, 2), r(80, 3)] };
        const M = N.mezclarProg(A, B);
        return (M.hist.length === 3 && M.mejor.pct === 80 && M.ultima.fecha === 3 && M.intentos === 3) || JSON.stringify(M);
    });

    const SIEMBRA_A = () => {
        if (localStorage.getItem('supc1:sembrado')) return; localStorage.setItem('supc1:sembrado', '1');
        localStorage.setItem('supc1:banco', JSON.stringify({ falladas: { 'supuesto_T2I:a': { f: 'supuesto_T2I', h: 'a', t: 'Pregunta A', n: 2, ok: 0, ts: 1000 } }, marcadas: {}, notas: { 'supuesto_T2I:n1': { f: 'supuesto_T2I', h: 'n1', t: 'P', txt: 'nota del movil', ts: 1000 } } }));
        localStorage.setItem('supc1:prog:supuesto_T2I', JSON.stringify({ intentos: 1, mejor: { pct: 60, fecha: 1, total: 25 }, ultima: { pct: 60, fecha: 1, total: 25 }, hist: [{ pct: 60, fecha: 1, total: 25 }] }));
    };
    const SIEMBRA_B = () => {
        if (localStorage.getItem('supc1:sembrado')) return; localStorage.setItem('supc1:sembrado', '1');
        localStorage.setItem('supc1:banco', JSON.stringify({ falladas: {}, marcadas: { 'supuesto_T2I:m': { f: 'supuesto_T2I', h: 'm', t: 'Marcada B', ts: 2000 } }, notas: {} }));
        localStorage.setItem('supc1:prog:supuesto_T2I', JSON.stringify({ intentos: 1, mejor: { pct: 80, fecha: 2, total: 25 }, ultima: { pct: 80, fecha: 2, total: 25 }, hist: [{ pct: 80, fecha: 2, total: 25 }] }));
    };
    const pulsarSync = async pg => { await pg.click('#sync-boton'); };
    const hecho = async pg => { await pg.waitForSelector('.sync-proceso h3:has-text("Sincronizado")', { timeout: 8000 }); return pg.textContent('.sync-proceso .sync-estado'); };
    const recargar = async pg => { await pg.reload(); await pg.waitForSelector('#sync-boton'); };

    await caso('sin ID de cliente la opción no aparece en «Mi estudio»', async () => {
        const drive = driveFalso(), ctx = await dispositivo(drive, SIEMBRA_A, { sinId: true }); const pg = await abrir(ctx, 'mi-estudio.html');
        const n = await hay(pg, '#sync-boton'); await ctx.close(); return n === 0 || 'aparece';
    });
    await caso('antes de sincronizar se abre la explicación con los pasos', async () => {
        const drive = driveFalso(), ctx = await dispositivo(drive, SIEMBRA_A); const pg = await abrir(ctx, 'mi-estudio.html');
        await pulsarSync(pg); const t = await pg.textContent('.sync-explicacion'); const antes = drive.est.contenido;
        await ctx.close();
        return (/carpeta privada y oculta de tu propio Google Drive/.test(t) && /Pasos/.test(t) && /Continuar/.test(t) && antes === null && (t.match(/\d\./g) || []).length >= 0) || t.slice(0, 200);
    });
    await caso('dispositivo A sincroniza; dispositivo B recibe sus datos y conserva los suyos', async () => {
        const drive = driveFalso();
        const ca = await dispositivo(drive, SIEMBRA_A); const a = await abrir(ca, 'mi-estudio.html');
        await pulsarSync(a); await a.click('.sync-explicacion .btn-primary'); const resA = await hecho(a);
        const guardado = JSON.parse(drive.est.contenido);
        const cb = await dispositivo(drive, SIEMBRA_B); const b = await abrir(cb, 'mi-estudio.html');
        await pulsarSync(b); await b.click('.sync-explicacion .btn-primary'); const resB = await hecho(b);
        const bancoB = await b.evaluate(() => SupC1.get('banco', {})), progB = await b.evaluate(() => SupC1.get('prog:supuesto_T2I', {}));
        const visible = await b.evaluate(() => document.querySelector('#estudio-falladas').textContent.includes('Pregunta A') && document.querySelector('#estudio-marcadas').textContent.includes('nota del movil'));
        await ca.close(); await cb.close();
        return (/Se ha creado tu copia/.test(resA) && guardado.banco.notas['supuesto_T2I:n1'] && /Se han añadido/.test(resB) &&
                bancoB.falladas['supuesto_T2I:a'] && bancoB.marcadas['supuesto_T2I:m'] && bancoB.notas['supuesto_T2I:n1'] &&
                progB.hist.length === 2 && progB.mejor.pct === 80 && visible) || JSON.stringify({ resA, resB, bancoB, progB, visible });
    });
    await caso('un borrado en un dispositivo se propaga al otro y «No volver a mostrar» salta la explicación', async () => {
        const drive = driveFalso();
        const ca = await dispositivo(drive, SIEMBRA_A); const a = await abrir(ca, 'mi-estudio.html');
        await pulsarSync(a); await a.check('#sync-no-mas'); await a.click('.sync-explicacion .btn-primary'); await hecho(a);
        await a.reload(); await a.waitForSelector('#sync-ahora');       // la sesión se recuerda: no pide nada
        await a.click('#sync-salir'); await a.waitForSelector('#sync-boton');
        await pulsarSync(a); const sinExplicacion = (await hay(a, '.sync-explicacion')) === 0; await hecho(a);
        // borro la nota en A y sincronizo; B (con la nota) la pierde
        const cb = await dispositivo(drive, () => {}); const b = await abrir(cb, 'mi-estudio.html');
        await pulsarSync(b); await b.click('.sync-explicacion .btn-primary'); await hecho(b);
        const tenia = await b.evaluate(() => !!SupC1.get('banco', {}).notas['supuesto_T2I:n1']);
        await a.evaluate(() => { const bk = SupC1.get('banco', {}); delete bk.notas['supuesto_T2I:n1']; bk.borradas = bk.borradas || {}; bk.borradas['n:supuesto_T2I:n1'] = Date.now() + 10; SupC1.set('banco', bk); });
        await a.reload(); await a.waitForSelector('#sync-ahora'); await a.click('#sync-ahora'); await a.waitForTimeout(1500);
        await b.reload(); await b.waitForSelector('#sync-ahora'); await b.waitForTimeout(2000);
        const sigue = await b.evaluate(() => !!SupC1.get('banco', {}).notas['supuesto_T2I:n1']);
        await ca.close(); await cb.close();
        return (sinExplicacion && tenia && !sigue) || JSON.stringify({ sinExplicacion, tenia, sigue });
    });
    await caso('fusión: los tests a medias se unen, gana el más reciente y terminarlo lo borra en el otro dispositivo', async () => {
        const c = (ts, n) => ({ v: 1, ts, a: { 0: n } });
        const m1 = N.mezclarTodo({ curso: { X: c(10, 1) } }, { curso: { X: c(20, 2), Y: c(5, 1) } }, 30);
        const m2 = N.mezclarTodo({ curso: { X: c(20, 2) }, cursoBorr: {} }, { curso: { X: c(10, 1) }, cursoBorr: { X: 25 } }, 30);
        const m3 = N.mezclarTodo({ curso: { X: c(10, 1) } }, { curso: {}, cursoBorr: { X: 15 } }, 30);
        const m4 = N.mezclarTodo({ curso: { X: c(40, 1) } }, { cursoBorr: { X: 15 } }, 50);
        return (m1.curso.X.ts === 20 && !!m1.curso.Y && !m2.curso.X && m2.cursoBorr.X === 25 && !m3.curso.X && m4.curso.X.ts === 40) || JSON.stringify([m1, m2, m3, m4]);
    });
    await caso('con la sesión iniciada: sin botón, con icono, sincroniza solo (también tests a medias) y «Cerrar sesión» la quita', async () => {
        const drive = driveFalso();
        const ca = await dispositivo(drive, SIEMBRA_A); const a = await abrir(ca, 'mi-estudio.html');
        await pulsarSync(a); await a.click('.sync-explicacion .btn-primary'); await hecho(a);
        await a.reload(); await a.waitForSelector('#sync-ahora');
        const sinBoton = (await hay(a, '#sync-boton')) === 0, icono = await hay(a, '#sync-icono-tarjeta'), avisoOculto = await a.evaluate(() => document.querySelector('.aviso-privado').hidden);
        await a.click('#sync-btn-aviso'); const avisoVisible = await a.evaluate(() => !document.querySelector('.aviso-privado').hidden); await a.click('#sync-btn-aviso');
        // un test a medias en A se sube solo
        await a.evaluate(() => SupC1.set('curso:supuesto_T2I', { v: 1, ts: Date.now(), a: { 0: 1 } }));
        await a.waitForTimeout(6000);
        const cb = await dispositivo(drive, () => {}); const b = await abrir(cb, 'mi-estudio.html');
        await pulsarSync(b); await b.click('.sync-explicacion .btn-primary'); await hecho(b);
        const bTiene = await b.evaluate(() => !!SupC1.get('curso:supuesto_T2I', null));
        // al terminarlo en A (lápida) desaparece en B
        await a.evaluate(() => { SupC1.del('curso:supuesto_T2I'); SupC1.set('cursoborr:supuesto_T2I', Date.now() + 10); });
        await a.waitForTimeout(6000);
        await b.reload(); await b.waitForSelector('#sync-ahora'); await b.waitForTimeout(2000);
        const bSigue = await b.evaluate(() => !!SupC1.get('curso:supuesto_T2I', null));
        await a.click('#sync-salir'); await a.waitForSelector('#sync-boton');
        const avisoVuelve = await a.evaluate(() => !document.querySelector('.aviso-privado').hidden && (document.querySelectorAll('.btn-barra').length === 0));
        const salida = await a.evaluate(() => SupC1.get('sync-sesion', null));
        await ca.close(); await cb.close();
        return (sinBoton && icono === 1 && avisoOculto && avisoVisible && avisoVuelve && bTiene && !bSigue && salida === null) || JSON.stringify({ sinBoton, icono, avisoOculto, avisoVisible, avisoVuelve, bTiene, bSigue, salida });
    });
    await caso('si se corta el acceso aparece el aviso, se reintenta con el siguiente toque y al reconectar desaparece', async () => {
        const drive = driveFalso();
        const ctx = await dispositivo(drive, () => { localStorage.setItem('supc1:sync-sesion', JSON.stringify({ ts: 1 })); });
        await ctx.route('https://accounts.google.com/gsi/client', r => r.fulfill({ contentType: 'text/javascript', body:
            'window.google={accounts:{oauth2:{initTokenClient:function(c){return{requestAccessToken:function(){setTimeout(function(){' +
            'if(window.__ok)c.callback({access_token:"tok",expires_in:3600});else c.error_callback({type:"popup_failed_to_open"})},30)}}}}}};' }));
        const pg = await abrir(ctx, 'index.html');
        await pg.waitForSelector('#sync-icono', { timeout: 8000 });         // sin acceso: aviso visible
        const aviso = await hay(pg, '#sync-icono');
        await pg.evaluate(() => { window.__ok = true; localStorage.setItem('supc1:sync-intento', '1'); });
        await pg.mouse.click(5, 5);                                         // el siguiente toque reintenta
        await pg.waitForSelector('#sync-icono', { state: 'detached', timeout: 8000 });
        await pg.waitForFunction(() => !!localStorage.getItem('supc1:sync-token'), null, { timeout: 8000 }).catch(() => {});
        await pg.waitForTimeout(500);
        const token = await pg.evaluate(() => !!localStorage.getItem('supc1:sync-token')), vuelve = await hay(pg, '#sync-icono');
        await ctx.close();
        return (aviso === 1 && token && vuelve === 0) || JSON.stringify({ aviso, token, vuelve });
    });
    await caso('si Google no concede el permiso, el mensaje es claro y no se toca nada', async () => {
        const drive = driveFalso(), ctx = await dispositivo(drive, SIEMBRA_A, { deniega: true }); const pg = await abrir(ctx, 'mi-estudio.html');
        await pulsarSync(pg); await pg.click('.sync-explicacion .btn-primary'); await pg.waitForSelector('.sync-proceso h3:has-text("No se ha podido sincronizar")', { timeout: 8000 });
        const t = await pg.textContent('.sync-proceso .sync-estado'); await ctx.close();
        return (/No se completó el permiso de Google/.test(t) && drive.est.contenido === null) || t;
    });
}

(async () => {
    const server = await servidor(); BASE = 'http://127.0.0.1:' + server.address().port + '/';
    const opts = { args: ['--no-sandbox'] }; if (process.env.CHROMIUM_PATH) opts.executablePath = process.env.CHROMIUM_PATH;
    else if (fs.existsSync('/opt/pw-browsers/chromium-1243/chrome-linux64/chrome') && !process.env.CI) opts.executablePath = '/opt/pw-browsers/chromium-1243/chrome-linux64/chrome';
    navegador = await pw.chromium.launch(opts);
    const grupos = { carga, envios, estilos, funciones, menu, sync };
    for (const [n, f] of Object.entries(grupos)) {
        if (SOLO.length && !SOLO.includes(n)) continue;
        console.log('\n▶ ' + n); await f();
    }
    await navegador.close(); server.close();
    const malos = resultados.filter(r => !r.ok);
    console.log('\n' + resultados.length + ' comprobaciones · ' + malos.length + ' fallos');
    process.exit(malos.length ? 1 : 0);
})().catch(e => { console.error(e); process.exit(2); });

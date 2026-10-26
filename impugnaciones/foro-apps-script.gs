/* Intermediario del foro de impugnaciones: recibe el mensaje de la web y lo publica
   como comentario en una Issue de GitHub (la crea la primera vez). Va en Google Apps Script
   (gratis). El token de GitHub NO se escribe aquí: se guarda en «Propiedades del script».
   Guía: impugnaciones/LEEME.txt */

var REPO = 'RMalumP/SupuestosC1';
var ETIQUETA = 'foro-impugnaciones';
var MAX_MENSAJE = 1500, MAX_NOMBRE = 40;
var MAX_POR_HORA = 30;            // mensajes por hora entre todos los usuarios (freno anti-spam)

function doPost(e) {
  try {
    var d = JSON.parse(e.postData.contents);
    if (d.web) return salida({ ok: true });                       // campo trampa relleno: es un robot
    var hilo = String(d.hilo || ''), mensaje = String(d.mensaje || '').trim(), nombre = String(d.nombre || '').trim();
    if (!/^[A-Za-z0-9]{6,40}$/.test(hilo) || !mensaje) return salida({ ok: false, error: 'datos' });
    mensaje = limpiar(mensaje.slice(0, MAX_MENSAJE));
    nombre = limpiar((nombre || 'Anónimo').slice(0, MAX_NOMBRE)).replace(/[\r\n*]/g, ' ');
    if (!frenar()) return salida({ ok: false, error: 'limite' });

    var issue = buscarIssue(hilo);
    if (!issue) issue = crearIssue(hilo, limpiar(String(d.titulo || '').slice(0, 120)));
    if (issue.state === 'closed' || issue.locked) return salida({ ok: false, error: 'cerrado' });
    api('/issues/' + issue.number + '/comments', 'post', { body: '**' + nombre + '**\n\n' + mensaje });
    CacheService.getScriptCache().remove('foro');                  // la siguiente lectura ya trae el mensaje nuevo
    return salida({ ok: true });
  } catch (err) {
    return salida({ ok: false, error: 'error' });
  }
}

// Lectura del foro para la web: una sola llamada con todos los hilos (así los usuarios no dependen del límite de GitHub).
// Se guarda 10 s en caché; al publicar un mensaje se vacía.
function doGet(e) {
  if (!e || !e.parameter || e.parameter.accion !== 'foro') return salida({ ok: true, foro: 'impugnaciones' });
  try {
    var c = CacheService.getScriptCache(), g = c.get('foro');
    if (g) return ContentService.createTextOutput(g).setMimeType(ContentService.MimeType.JSON);
    var hilos = {}, porNum = {}, i, p;
    for (p = 1; p <= 5; p++) {
      var iss = api('/issues?state=all&labels=' + ETIQUETA + '&per_page=100&page=' + p);
      for (i = 0; i < iss.length; i++) {
        var m = /^\[([A-Za-z0-9]+)\]/.exec(iss[i].title || '');
        if (m && !iss[i].pull_request) { hilos[m[1]] = { cerrado: iss[i].state === 'closed' || !!iss[i].locked, msgs: [] }; porNum[iss[i].number] = hilos[m[1]]; }
      }
      if (iss.length < 100) break;
    }
    for (p = 1; p <= 10; p++) {
      var cs = api('/issues/comments?sort=created&direction=asc&per_page=100&page=' + p);
      for (i = 0; i < cs.length; i++) {
        var n = /\/issues\/(\d+)$/.exec(cs[i].issue_url || ''), h = n && porNum[n[1]];
        if (h) h.msgs.push({ b: cs[i].body || '', u: cs[i].user ? cs[i].user.login : '', t: cs[i].created_at });
      }
      if (cs.length < 100) break;
    }
    var out = JSON.stringify({ ok: true, hilos: hilos });
    try { c.put('foro', out, 10); } catch (x) { /* demasiado grande para la caché: se sirve igual */ }
    return ContentService.createTextOutput(out).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return salida({ ok: false, error: 'error' });
  }
}

function salida(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

// Evita menciones (@usuario), HTML y enlaces automáticos a otras Issues
function limpiar(t) { return t.replace(/</g, '&lt;').replace(/@/g, '@​').replace(/#(\d)/g, '#​$1'); }

function frenar() {
  var c = CacheService.getScriptCache(), n = Number(c.get('n') || 0);
  if (n >= MAX_POR_HORA) return false;
  c.put('n', String(n + 1), 3600);
  return true;
}

function token() { return PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN'); }

function api(ruta, metodo, cuerpo) {
  var r = UrlFetchApp.fetch('https://api.github.com/repos/' + REPO + ruta, {
    method: metodo || 'get', contentType: 'application/json', muteHttpExceptions: true,
    headers: { Authorization: 'Bearer ' + token(), Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
    payload: cuerpo ? JSON.stringify(cuerpo) : undefined
  });
  if (r.getResponseCode() >= 300) throw new Error('GitHub ' + r.getResponseCode());
  return JSON.parse(r.getContentText());
}

function buscarIssue(hilo) {
  for (var p = 1; p <= 5; p++) {
    var lista = api('/issues?state=all&labels=' + ETIQUETA + '&per_page=100&page=' + p);
    for (var i = 0; i < lista.length; i++) if (lista[i].title.indexOf('[' + hilo + ']') === 0 && !lista[i].pull_request) return lista[i];
    if (lista.length < 100) break;
  }
  return null;
}

function crearIssue(hilo, titulo) {
  return api('/issues', 'post', { title: '[' + hilo + '] ' + (titulo.replace(/^\[[^\]]*\]\s*/, '') || 'Impugnación'), labels: [ETIQUETA], body: 'Hilo del foro de la impugnación ' + hilo + '. Los comentarios de la web aparecen con el nombre en negrita.' });
}

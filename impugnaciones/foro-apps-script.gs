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
    return salida({ ok: true });
  } catch (err) {
    return salida({ ok: false, error: 'error' });
  }
}

function doGet() { return salida({ ok: true, foro: 'impugnaciones' }); }

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

/* ════════════════════════════════════════════════════════════════
   SINCRONIZAR ENTRE DISPOSITIVOS CON GOOGLE DRIVE  ·  APAGADO POR DEFECTO
   ────────────────────────────────────────────────────────────────
   Cada persona guarda una copia de sus datos de estudio (notas, marcadas, falladas
   y estadísticas) en una carpeta OCULTA de SU PROPIO Google Drive. Tú no recibes ni
   guardas nada: la web solo puede ver esa carpeta, no el resto de su Drive.

   PARA ACTIVARLO (una sola vez, gratis, unos 10 minutos):
     1. Entra en https://console.cloud.google.com con tu cuenta de Google y crea un
        proyecto nuevo (por ejemplo «Supuestos C1»).
     2. Menú «APIs y servicios» → «Biblioteca» → busca «Google Drive API» → «Habilitar».
     3. «APIs y servicios» → «Pantalla de consentimiento de OAuth»:
          · Tipo de usuario: «Externo».
          · Nombre de la aplicación: «Supuestos C1»; correo de asistencia: el tuyo.
          · En «Permisos» (Scopes) añade SOLO este:  …/auth/drive.appdata
          · Al terminar pulsa «Publicar aplicación» (pasarla de «Pruebas» a «En
            producción»). Con este permiso no hace falta verificación de Google.
     4. «APIs y servicios» → «Credenciales» → «Crear credenciales» → «ID de cliente de
        OAuth» → tipo «Aplicación web»:
          · Orígenes de JavaScript autorizados:  https://rmalump.github.io
            (y, si pruebas en local, http://localhost:8000)
          · (No hace falta «URI de redireccionamiento».)
     5. Copia el «ID de cliente» (acaba en .apps.googleusercontent.com) y pégalo abajo.
        Es público: no es una contraseña ni un secreto.
     6. Sube VERSION en sw.js antes de publicar.
   Mientras «clientId» esté vacío, la opción NO aparece en «Mi estudio».
════════════════════════════════════════════════════════════════ */
window.SUPC1_SYNC = {
    clientId: "592644810471-sahcfa82q4vlaql6a01m1psh4vm3td7q.apps.googleusercontent.com",                       // 1234567890-abc...apps.googleusercontent.com
    archivo: "supc1-sync.json"            // nombre del archivo dentro de la carpeta oculta de Drive
};

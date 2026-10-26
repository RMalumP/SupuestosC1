# -*- coding: utf-8 -*-
"""
════════════════════════════════════════════════════════════════════════
 EDITOR DE SUPUESTOS  —  interfaz gráfica para la plantilla HTML
════════════════════════════════════════════════════════════════════════
 Qué hace:
   Abre en local un archivo de plantilla de supuesto (.html), muestra
   TODOS los campos editables en cuadros de texto (título, duración,
   bloques de hechos, hechos desencadenantes, línea de tiempo,
   preguntas, sus 4 respuestas marcando la correcta, la motivación
   legal y el consejo) y vuelve a guardarlos dentro del HTML.

 Cómo se ejecuta:
   Abrir este archivo con Thonny y pulsar F5 (Ejecutar).

 Librerías necesarias:
   NINGUNA instalación. Solo usa la biblioteca estándar de Python:
   tkinter, json, re, os, pathlib, webbrowser, unicodedata.
   (En Windows y macOS, tkinter viene incluido con Python/Thonny.
    En Linux, si diera error, instalar el paquete del sistema
    "python3-tk":  sudo apt install python3-tk)

 Cada campo de la ventana está rotulado por partida doble:
   · el nombre con el que se ve en la página publicada
   · el nombre técnico del campo y el elemento HTML donde acaba
════════════════════════════════════════════════════════════════════════
"""

import json
import os
import re
import sys
import webbrowser
from pathlib import Path

# Los módulos del editor (menu_datos, datos_html, alta_menu…) están junto a este archivo.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Modos sin ventana (se deciden antes de cargar tkinter). El lanzador es siempre este archivo:
#   --alta [--auto]      da de alta en el menú los supuestos que falten        (alta_menu.py)
#   --actualizar         pone todo al día y prepara la carpeta PARA_SUBIR      (sincronizar_local.py)
#   --para-subir         solo prepara la carpeta PARA_SUBIR
#   --subido             marca lo actual como ya subido a GitHub
if __name__ == "__main__":
    if "--alta" in sys.argv:
        import alta_menu
        sys.exit(alta_menu.main([a for a in sys.argv[1:] if a != "--alta"]))
    if any(a in sys.argv for a in ("--actualizar", "--para-subir", "--subido")):
        import sincronizar_local
        sys.exit(sincronizar_local.main(sys.argv[1:]))

from editor_comun import *  # noqa: F401,F403
from editor_comun import (_leer_prefs)  # noqa: F401
from pestana_general import PestanaGeneral
from pestana_bloques import PestanaBloques
from pestana_enunciados import PestanaEnunciados
from pestana_preguntas import PestanaPreguntas
from pestana_envio import PestanaEnvio
from pestana_normas import PestanaNormas
from pestana_comprobar import PestanaComprobar
from archivo_guardado import ArchivoGuardado


class EditorApp(PestanaGeneral,
                PestanaBloques,
                PestanaEnunciados,
                PestanaPreguntas,
                PestanaEnvio,
                PestanaNormas,
                PestanaComprobar,
                ArchivoGuardado,
                tk.Tk):
    """Ventana principal. Cada pestaña vive en su archivo pestana_*.py."""

    def __init__(self):
        super().__init__()
        self.title(APP_TITULO)
        self._prefs = _leer_prefs()
        geo = self._prefs.get("geometria")
        self.geometry(geo if isinstance(geo, str) and re.fullmatch(r"\d+x\d+([+-]-?\d+){2}", geo)
                      else "1240x840")
        self.minsize(1000, 640)
        self.configure(bg=C_FONDO)
        self._estilos()

        self.ruta = None                 # archivo abierto (None = aún sin guardar)
        self.html_base = ""              # HTML completo del archivo abierto
        self.modo = "json"
        self.datos = datos_vacios()
        self.hay_cambios = False
        self._destinos_menu = None      # sitios del menú (los rellena _alta_en_menu)
        self._silencio = False           # evita reentradas al repintar listas

        self.i_sec = None
        self.i_enun = None
        self.i_bloque = None
        self.i_hito = None
        self.i_preg = None

        self.historial = herr.Historial()
        self._barra_superior()
        self._menu_principal()

        self.cuaderno = ttk.Notebook(self)
        self.cuaderno.pack(fill="both", expand=True, padx=10, pady=(6, 4))
        self._pestana_general()
        self._pestana_bloques()
        self._pestana_enunciados()
        self._pestana_preguntas()
        self._pestana_botones()
        self._pestana_comprobar()
        self._pestana_normas()

        self._barra_estado()
        self.protocol("WM_DELETE_WINDOW", self._al_cerrar)

        self.bind_all("<Control-s>", lambda e: self.guardar())
        self.bind_all("<Control-o>", lambda e: self.abrir())
        self.bind_all("<Control-n>", lambda e: self.nuevo())
        self.bind_all("<Control-S>", lambda e: self.guardar_como())
        self.bind_all("<Control-f>", lambda e: ventana_herramientas.buscar_reemplazar(self))
        self.bind_all("<Control-U>", lambda e: ventana_sync.abrir(self))
        self.bind_all("<F1>", lambda e: ventana_extra.ayuda(self))
        self.bind_all("<F6>", lambda e: ventana_extra.vista_previa(self))
        self.bind_all("<F5>", lambda e: self.ver_navegador())
        self.bind_all("<Control-z>", lambda e: self._atajo_historial(self.deshacer, e))
        self.bind_all("<Control-y>", lambda e: self._atajo_historial(self.rehacer, e))
        self.bind_all("<Control-Z>", lambda e: self._atajo_historial(self.rehacer, e))
        self.bind_all("<Alt-Up>", lambda e: self._mover_con_atajo(-1))
        self.bind_all("<Alt-Down>", lambda e: self._mover_con_atajo(1))
        self.after(AUTOGUARDADO_MS, self._autoguardar)

        self.after(200, self._carga_inicial)
        self.after(2500, self._avisar_si_hay_cambios_en_github)

    # ─────────────────────────────────────────────────────────────
    #  Estilos
    # ─────────────────────────────────────────────────────────────
    def _estilos(self):
        est = ttk.Style(self)
        try:
            est.theme_use("clam")
        except tk.TclError:
            pass
        est.configure("TFrame", background=C_FONDO)
        est.configure("Panel.TFrame", background=C_FONDO)
        est.configure("TLabel", background=C_FONDO, foreground=C_TINTA)
        est.configure("TLabelframe", background=C_FONDO, foreground=C_TINTA)
        est.configure("TLabelframe.Label", background=C_FONDO, foreground=C_ROJO,
                      font=("Georgia", 10, "bold"))
        est.configure("TNotebook", background=C_FONDO)
        est.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(14, 7),
                      background="#e2d6c8", foreground="#6b5344")
        est.map("TNotebook.Tab",
                background=[("selected", C_PANEL)],
                foreground=[("selected", C_ROJO)],
                expand=[("selected", (1, 1, 1, 0))])
        est.configure("Campo.TLabel", font=("Segoe UI", 10, "bold"), foreground=C_TINTA)
        est.configure("Tec.TLabel", font=("Consolas", 8), foreground=C_TEC)
        est.configure("Ayuda.TLabel", font=("Segoe UI", 8, "italic"), foreground=C_AYUDA)
        est.configure("Titulo.TLabel", font=("Georgia", 13, "bold"), foreground=C_ROJO)
        est.configure("Estado.TLabel", font=("Segoe UI", 9), foreground=C_TINTA)
        est.configure("TButton", font=("Segoe UI", 9))
        est.configure("Accion.TButton", font=("Segoe UI", 9, "bold"))

    # ─────────────────────────────────────────────────────────────
    #  Barra de botones superior
    # ─────────────────────────────────────────────────────────────
    def _barra_superior(self):
        barra = ttk.Frame(self)
        barra.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Button(barra, text="📂  Abrir plantilla…", command=self.abrir,
                   style="Accion.TButton").pack(side="left")
        ttk.Button(barra, text="🆕  Nuevo supuesto", command=self.nuevo).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(barra, text="💾  Guardar", command=self.guardar,
                   style="Accion.TButton").pack(side="left")
        ttk.Button(barra, text="💾  Guardar como…", command=self.guardar_como).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(barra, text="🌐  Ver en el navegador", command=self.ver_navegador).pack(side="left")
        ttk.Button(barra, text="✔  Comprobar", command=self.comprobar).pack(side="left", padx=(6, 0))
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(barra, text="🗂  Menú de inicio…",
                   command=lambda: ventana_menu.abrir(self)).pack(side="left", padx=(0, 6))
        ttk.Button(barra, text="📦  Para subir…",
                   command=lambda: ventana_subir.abrir(self)).pack(side="left")
        ttk.Button(barra, text="☁  Sincronizar",
                   command=lambda: ventana_sync.abrir(self)).pack(side="left", padx=(6, 0))

        self.lbl_archivo = ttk.Label(barra, text="(ningún archivo abierto)",
                                     style="Tec.TLabel")
        self.lbl_archivo.pack(side="right")

    # ─────────────────────────────────────────────────────────────
    #  Menús, deshacer/rehacer y autoguardado
    # ─────────────────────────────────────────────────────────────
    def _menu_principal(self):
        barra = tk.Menu(self)
        archivo = tk.Menu(barra, tearoff=False)
        archivo.add_command(label="Nuevo supuesto", accelerator="Ctrl+N", command=self.nuevo)
        archivo.add_command(label="Abrir…", accelerator="Ctrl+O", command=self.abrir)
        archivo.add_command(label="Guardar", accelerator="Ctrl+S", command=self.guardar)
        archivo.add_command(label="Guardar como…", accelerator="Ctrl+Mayús+S", command=self.guardar_como)
        archivo.add_separator()
        self._menu_recientes = tk.Menu(archivo, tearoff=False, postcommand=self._pintar_recientes)
        archivo.add_cascade(label="Abrir reciente", menu=self._menu_recientes)
        archivo.add_command(label="Duplicar este supuesto como uno nuevo…", command=self.duplicar_supuesto)
        archivo.add_command(label="Volver a una versión anterior de este archivo…",
                            command=lambda: ventana_extra.restaurar_version(self))
        archivo.add_separator()
        archivo.add_command(label="Pasar a plantilla nueva…", command=self.convertir_a_plantilla_nueva)
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self._al_cerrar)
        barra.add_cascade(label="Archivo", menu=archivo)
        edicion = tk.Menu(barra, tearoff=False)
        edicion.add_command(label="Deshacer cambio de estructura", accelerator="Ctrl+Z", command=self.deshacer)
        edicion.add_command(label="Rehacer", accelerator="Ctrl+Y", command=self.rehacer)
        edicion.add_separator()
        edicion.add_command(label="Buscar y reemplazar…", accelerator="Ctrl+F",
                            command=lambda: ventana_herramientas.buscar_reemplazar(self))
        edicion.add_command(label="Importar preguntas…",
                            command=lambda: ventana_herramientas.importar(self))
        edicion.add_command(label="Nueva pregunta desde plantilla…",
                            command=lambda: ventana_extra.nueva_de_plantilla(self))
        edicion.add_command(label="Copiar preguntas de otro supuesto…",
                            command=lambda: ventana_extra.copiar_de_otro(self))
        edicion.add_command(label="Vista previa de la pregunta", accelerator="F6",
                            command=lambda: ventana_extra.vista_previa(self))
        edicion.add_separator()
        edicion.add_command(label="Subir pregunta", accelerator="Alt+↑", command=lambda: self._mover_con_atajo(-1))
        edicion.add_command(label="Bajar pregunta", accelerator="Alt+↓", command=lambda: self._mover_con_atajo(1))
        barra.add_cascade(label="Edición", menu=edicion)
        herram = tk.Menu(barra, tearoff=False)
        herram.add_command(label="Ver en el navegador", accelerator="F5", command=self.ver_navegador)
        herram.add_command(label="Comprobar", command=self.comprobar)
        herram.add_command(label="Estadísticas del supuesto…", command=lambda: ventana_extra.estadisticas(self))
        herram.add_command(label="Preguntas repetidas…", command=lambda: ventana_extra.repetidas(self))
        herram.add_command(label="Impugnaciones recibidas…", command=lambda: ventana_extra.impugnaciones(self))
        herram.add_separator()
        herram.add_command(label="Publicar todo (comprobar, versión, sincronizar)…",
                           command=lambda: ventana_extra.publicar_todo(self))
        herram.add_command(label="Menú de inicio…", command=lambda: ventana_menu.abrir(self))
        herram.add_command(label="Para subir a GitHub…", command=lambda: ventana_subir.abrir(self))
        herram.add_command(label="Sincronizar con GitHub (git)…", accelerator="Ctrl+Mayús+U",
                           command=lambda: ventana_sync.abrir(self))
        barra.add_cascade(label="Herramientas", menu=herram)
        ayuda = tk.Menu(barra, tearoff=False)
        ayuda.add_command(label="Ayuda de esta pestaña", accelerator="F1", command=lambda: ventana_extra.ayuda(self))
        barra.add_cascade(label="Ayuda", menu=ayuda)
        self.config(menu=barra)

    def _pintar_recientes(self):
        self._menu_recientes.delete(0, "end")
        rec = publicar.recientes(self._prefs)
        for r in rec:
            self._menu_recientes.add_command(label=Path(r).name + "    " + str(Path(r).parent),
                                             command=lambda r=r: self.abrir_ruta(r))
        if not rec:
            self._menu_recientes.add_command(label="(ninguno todavía)", state="disabled")

    def _avisar_si_hay_cambios_en_github(self):
        """Al arrancar, mira en segundo plano si GitHub tiene cambios que aún no tienes."""
        import threading
        raiz = sincronizar_local.RAIZ_DEFECTO
        if not (git_sync.hay_git() and git_sync.es_clon(raiz)):
            return
        resultado = {}

        def mirar():
            resultado["n"] = git_sync.commits_atras(raiz)

        hilo = threading.Thread(target=mirar, daemon=True)
        hilo.start()

        def esperar(intentos=0):
            if hilo.is_alive() and intentos < 40:
                self.after(500, esperar, intentos + 1)
            elif resultado.get("n"):
                self.estado("GitHub tiene %d cambio(s) nuevo(s) que no tienes: ☁ Sincronizar → «Traer lo último»."
                            % resultado["n"])

        esperar()

    def _instantanea(self):
        """Pasa lo escrito en la ventana a los datos sin reordenar nada."""
        for volcar in (self.volcar_config, self.volcar_botones, self.volcar_seccion,
                       self.volcar_enunciado, self.volcar_pregunta):
            try:
                volcar()
            except (ValueError, tk.TclError):
                pass

    def anotar_historial(self):
        self._instantanea()
        self.historial.anotar(self.datos)

    def _anotar_luego(self):
        if getattr(self, "_anotar_pendiente", None):
            self.after_cancel(self._anotar_pendiente)
        self._anotar_pendiente = self.after(1500, self._anotar_ya)

    def _anotar_ya(self):
        self._anotar_pendiente = None
        self.anotar_historial()

    def _atajo_historial(self, accion, evento):
        # En un cuadro de texto, Ctrl+Z deshace SU escritura; fuera, la estructura.
        if evento.widget.winfo_class() in ("Text", "Entry", "TEntry", "TSpinbox", "TCombobox"):
            return None
        accion()
        return "break"

    def deshacer(self):
        self._instantanea()
        previo = self.historial.deshacer(self.datos)
        if previo is None:
            self.estado("No hay nada que deshacer.")
            return
        self._poner_datos(previo)
        self.estado("Deshecho.")

    def rehacer(self):
        previo = self.historial.rehacer()
        if previo is None:
            self.estado("No hay nada que rehacer.")
            return
        self._poner_datos(previo)
        self.estado("Rehecho.")

    def _poner_datos(self, datos):
        i = self.i_preg
        self.datos = datos
        self._refrescar_todo(reiniciar=False)
        if i is not None and self.datos["preguntas"]:
            self.refrescar_lista_preg(min(i, len(self.datos["preguntas"]) - 1))
        self.hay_cambios = True
        self._pintar_titulo()

    def recargar_tras_cambio(self):
        """Tras un cambio hecho desde otra ventana (buscar, importar)."""
        self._poner_datos(self.datos)
        self.historial.anotar(self.datos)

    def ir_a_pregunta(self, n):
        if n is None or not (0 <= n < len(self.datos["preguntas"])):
            return
        self.volcar_pregunta()
        self.refrescar_lista_preg(n)
        self.cuaderno.select(3)

    def _mover_con_atajo(self, paso):
        if self.cuaderno.index("current") == 3:
            self.mover_pregunta(paso)
        return "break"

    def _ir_desde_informe(self, evento):
        """Doble clic en una línea «Pregunta N: …» del informe salta a esa pregunta."""
        linea = self.txt_informe.get("current linestart", "current lineend")
        m = re.search(r"Pregunta (\d+)", linea)
        if m:
            self.ir_a_pregunta(int(m.group(1)) - 1)

    def _ruta_recuperacion(self):
        return herr.ruta_recuperacion(self.ruta, PREFS.parent)

    def _autoguardar(self):
        if self.hay_cambios:
            self._instantanea()
            herr.guardar_recuperacion(self._ruta_recuperacion(), self.datos)
        self.after(AUTOGUARDADO_MS, self._autoguardar)

    def _borrar_recuperacion(self):
        try:
            self._ruta_recuperacion().unlink()
        except OSError:
            pass

    def _ofrecer_recuperacion(self):
        rec = self._ruta_recuperacion()
        try:
            if not rec.is_file() or (self.ruta and rec.stat().st_mtime <= self.ruta.stat().st_mtime):
                return
        except OSError:
            return
        if messagebox.askyesno(
                "Recuperar trabajo",
                "Hay una copia de recuperación MÁS NUEVA que el archivo (el programa se cerró "
                "sin guardar).\n\n¿Cargarla? (Si dices que no, se borra.)", parent=self):
            datos = herr.leer_recuperacion(rec)
            if datos:
                self._poner_datos(normalizar(datos))
                self.estado("Recuperado el trabajo sin guardar. Revisa y pulsa Guardar.")
                return
        self._borrar_recuperacion()

    def _barra_estado(self):
        marco = ttk.Frame(self)
        marco.pack(fill="x", padx=10, pady=(0, 8))
        self.lbl_estado = ttk.Label(marco, text="Listo.", style="Estado.TLabel")
        self.lbl_estado.pack(side="left")
        self.lbl_contadores = ttk.Label(marco, text="", style="Tec.TLabel")
        self.lbl_contadores.pack(side="right")

    def estado(self, texto):
        self.lbl_estado.config(text=texto)

    def _tocado(self, *_a):
        self.hay_cambios = True
        self._pintar_titulo()
        self._anotar_luego()

    def _pintar_titulo(self):
        # Se llama en cada pulsación: se junta en un solo repintado.
        if getattr(self, "_titulo_pendiente", None):
            return
        self._titulo_pendiente = self.after(150, self._pintar_titulo_ya)

    def _pintar_titulo_ya(self):
        self._titulo_pendiente = None
        nombre = self.ruta.name if self.ruta else "sin guardar"
        self.title("%s — %s%s" % (APP_TITULO, nombre, " *" if self.hay_cambios else ""))
        if hasattr(self, "lbl_archivo"):
            self.lbl_archivo.config(text=str(self.ruta) if self.ruta else "(sin guardar)")
        if hasattr(self, "lbl_contadores"):
            self.lbl_contadores.config(
                text="bloques: %d    ·    enunciados: %d    ·    preguntas: %d"
                     % (len(self.datos["bloques"]), len(self.datos["enunciados"]),
                        len(self.datos["preguntas"])))

    def _vigilar(self, *widgets):
        for w in widgets:
            w.bind("<KeyRelease>", self._tocado, add="+")
            # Los botones de formato no pasan por el teclado: avisan con
            # su propio evento para que el archivo se marque como tocado.
            w.bind("<<TextoTocado>>", self._tocado, add="+")




# ══════════════════════════════════════════════════════════════════════
#  7. ARRANQUE
# ══════════════════════════════════════════════════════════════════════

def main():
    try:                       # la primera vez, lo que hay ahora cuenta como «lo descargado de GitHub»
        if sincronizar_local.es_proyecto(sincronizar_local.RAIZ_DEFECTO):
            sincronizar_local.asegurar_base(sincronizar_local.RAIZ_DEFECTO)
    except OSError:
        pass
    app = EditorApp()
    app.mainloop()


if __name__ == "__main__":
    main()

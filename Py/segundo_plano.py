# -*- coding: utf-8 -*-
"""
TRABAJOS LARGOS SIN CONGELAR LA VENTANA
═══════════════════════════════════════
Parte del editor de supuestos. git, descargas de Google… pueden tardar; si se
hacen en el hilo de la ventana, esta se queda «Sin responder». Aquí el trabajo
va en un hilo aparte y la ventana solo mira cada poco si ha terminado (Tk no
se puede tocar desde otro hilo, así que el resultado se entrega en el principal).
"""
import threading


def lanzar(ventana, trabajo, al_terminar, al_fallar=None, botones=(), aviso=None,
           texto="Trabajando…", cada_ms=120):
    """Ejecuta trabajo() en segundo plano.
      al_terminar(resultado) / al_fallar(excepcion) se llaman en la ventana al acabar.
      botones: se desactivan mientras dura (y se reactivan después).
      aviso: StringVar (o función de un argumento) donde se escribe `texto`."""
    caja = {}

    def correr():
        try:
            caja["ok"] = trabajo()
        except Exception as err:            # se entrega al hilo de la ventana
            caja["error"] = err

    estados = []
    for b in botones:
        try:
            estados.append((b, str(b.cget("state"))))
            b.configure(state="disabled")
        except Exception:
            pass
    _avisar(aviso, texto)
    try:
        ventana.configure(cursor="watch")
    except Exception:
        pass
    hilo = threading.Thread(target=correr, daemon=True)
    hilo.start()

    def mirar():
        if hilo.is_alive():
            try:
                ventana.after(cada_ms, mirar)
            except Exception:
                pass                         # la ventana se ha cerrado: nada que pintar
            return
        try:
            ventana.configure(cursor="")
        except Exception:
            return
        for b, previo in estados:
            try:
                b.configure(state=previo if previo != "disabled" else "normal")
            except Exception:
                pass
        if "error" in caja:
            if al_fallar:
                al_fallar(caja["error"])
            else:
                _avisar(aviso, str(caja["error"]))
        else:
            al_terminar(caja.get("ok"))

    ventana.after(cada_ms, mirar)
    return hilo


def _avisar(aviso, texto):
    if aviso is None:
        return
    if callable(aviso):
        aviso(texto)
    else:
        aviso.set(texto)

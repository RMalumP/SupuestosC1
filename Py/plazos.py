# -*- coding: utf-8 -*-
"""
CALCULADORA DE PLAZOS  (sin ventana)
════════════════════════════════════
Parte del editor de supuestos. Para comprobar al escribir una pregunta en qué
fecha vence un plazo, con las reglas del art. 30 de la Ley 39/2015 (LPAC):

  · Días HÁBILES: se cuentan desde el día siguiente a la notificación y se
    saltan sábados, domingos y festivos.
  · Días NATURALES: desde el día siguiente, todos seguidos; si el último es
    inhábil, pasa al primer día hábil siguiente.
  · MESES o AÑOS: desde el día siguiente; vence el mismo número de día en el
    mes (o año) de vencimiento; si ese mes no tiene ese día, el último del mes;
    si cae en inhábil, el primer día hábil siguiente.

calcular() devuelve la fecha y los pasos explicados (para la motivación).
Los festivos nacionales fijos y el Viernes Santo vienen ya; se pueden añadir
otros (autonómicos, locales) como fechas sueltas.
"""
import calendar
import re
from datetime import date, timedelta

UNIDADES = ("días hábiles", "días naturales", "meses", "años")
DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre")
FIJOS = ((1, 1, "Año Nuevo"), (6, 1, "Epifanía"), (1, 5, "Fiesta del Trabajo"), (15, 8, "Asunción"),
         (12, 10, "Fiesta Nacional"), (1, 11, "Todos los Santos"), (6, 12, "Constitución"),
         (8, 12, "Inmaculada"), (25, 12, "Navidad"))


def pascua(anio):
    """Domingo de Pascua (algoritmo de Butcher)."""
    a, b, c = anio % 19, anio // 100, anio % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def festivos_nacionales(anio):
    res = {date(anio, m, d): nombre for d, m, nombre in FIJOS}
    res[pascua(anio) - timedelta(days=2)] = "Viernes Santo"
    return res


RE_FECHA = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})")


def leer_fecha(texto):
    """«5/3/2026», «05-03-26» → date (o None)."""
    m = RE_FECHA.search(texto or "")
    if not m:
        return None
    d, mes, a = (int(x) for x in m.groups())
    if a < 100:
        a += 2000
    try:
        return date(a, mes, d)
    except ValueError:
        return None


def leer_festivos(texto):
    """Fechas sueltas, una por línea (lo que va detrás de la fecha es un comentario)."""
    res = {}
    for linea in (texto or "").splitlines():
        f = leer_fecha(linea)
        if f:
            resto = RE_FECHA.sub("", linea, count=1).strip(" -·:\t")
            res[f] = resto or "festivo añadido"
    return res


def fecha_larga(f):
    return "%s %d de %s de %d" % (DIAS[f.weekday()], f.day, MESES[f.month - 1], f.year)


class Calendario:
    def __init__(self, extra=None, sabados_habiles=False):
        self.extra = dict(extra or {})
        self.sabados_habiles = sabados_habiles
        self._cache = {}

    def festivo(self, f):
        if f.year not in self._cache:
            self._cache[f.year] = festivos_nacionales(f.year)
        return self.extra.get(f) or self._cache[f.year].get(f)

    def por_que_inhabil(self, f):
        """Motivo por el que el día no es hábil (o None si es hábil)."""
        if f.weekday() == 6 or (f.weekday() == 5 and not self.sabados_habiles):
            return DIAS[f.weekday()]
        return self.festivo(f)

    def siguiente_habil(self, f):
        saltados = []
        while self.por_que_inhabil(f):
            saltados.append((f, self.por_que_inhabil(f)))
            f += timedelta(days=1)
        return f, saltados


def _sumar_meses(f, meses):
    total = f.month - 1 + meses
    anio, mes = f.year + total // 12, total % 12 + 1
    ultimo = calendar.monthrange(anio, mes)[1]
    return date(anio, mes, min(f.day, ultimo)), f.day > ultimo


def calcular(inicio, cantidad, unidad, calendario=None):
    """inicio: fecha de la notificación o publicación (date). Devuelve (vencimiento, pasos)."""
    cal = calendario or Calendario()
    if cantidad < 1:
        raise ValueError("El plazo tiene que ser de 1 o más.")
    if unidad not in UNIDADES:
        raise ValueError("Unidad desconocida: %s" % unidad)
    pasos = ["Notificación o publicación: %s." % fecha_larga(inicio),
             "Se empieza a contar el día siguiente: %s." % fecha_larga(inicio + timedelta(days=1))]
    if unidad == "días hábiles":
        f, contados, saltados = inicio, 0, 0
        while contados < cantidad:
            f += timedelta(days=1)
            if cal.por_que_inhabil(f):
                saltados += 1
            else:
                contados += 1
        pasos.append("Se cuentan %d días hábiles (se saltan %d inhábiles: %s y festivos)."
                     % (cantidad, saltados, "domingos" if cal.sabados_habiles else "sábados, domingos"))
        pasos.append("Último día: %s." % fecha_larga(f))
        return f, pasos
    if unidad == "días naturales":
        f = inicio + timedelta(days=cantidad)
        pasos.append("Se cuentan %d días naturales: el último es el %s." % (cantidad, fecha_larga(f)))
    else:
        meses = cantidad * (12 if unidad == "años" else 1)
        f, sin_dia = _sumar_meses(inicio, meses)
        nombre = {"meses": ("mes", "meses"), "años": ("año", "años")}[unidad][cantidad > 1]
        pasos.append("De fecha a fecha: %d %s después, el mismo día del mes: %s."
                     % (cantidad, nombre, fecha_larga(f)))
        if sin_dia:
            pasos.append("Ese mes no tiene día %d: vence el último día del mes." % inicio.day)
    final, saltados = cal.siguiente_habil(f)
    if saltados:
        pasos.append("Ese día es inhábil (%s): pasa al primer día hábil siguiente, %s."
                     % (", ".join(m for _x, m in saltados), fecha_larga(final)))
    return final, pasos

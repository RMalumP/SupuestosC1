# -*- coding: utf-8 -*-
"""
RECUADRO «IMÁGENES» DEL EDITOR  (la lógica está en imagenes.py)
═══════════════════════════════════════════════════════════════
Parte del editor de supuestos. Un recuadro pequeño que se repite en el bloque de
hechos, en la pregunta y en la motivación legal: lista de hasta 3 imágenes con
Añadir, Quitar, Subir, Bajar y un pie opcional para la imagen seleccionada.

Añadir NO copia nada todavía: solo recuerda el archivo elegido. Al guardar el
supuesto, imagenes.repartir() lo lleva a la carpeta supuestos/img/NOMBRE/.
"""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import imagenes


class RecuadroImagenes(ttk.LabelFrame):
    def __init__(self, padre, app, titulo, tecnico, ayuda):
        super().__init__(padre, text=" %s " % titulo)
        self.app = app
        self.titulo = titulo
        self.lista = []
        ttk.Label(self, style="Tec.TLabel", text=tecnico).pack(anchor="w", padx=8, pady=(4, 0))
        ttk.Label(self, style="Ayuda.TLabel", wraplength=700, justify="left", text=ayuda
                  ).pack(anchor="w", padx=8)
        fila = ttk.Frame(self)
        fila.pack(fill="x", padx=8, pady=(4, 2))
        self.caja = tk.Listbox(fila, font=("Consolas", 9), height=imagenes.MAXIMO,
                               activestyle="none", exportselection=False)
        self.caja.pack(side="left", fill="x", expand=True)
        self.caja.bind("<<ListboxSelect>>", lambda e: self._pintar_pie())
        col = ttk.Frame(fila)
        col.pack(side="left", padx=(6, 0))
        self.b_anadir = ttk.Button(col, text="＋ Añadir…", width=11, style="Accion.TButton", command=self.anadir)
        self.b_anadir.grid(row=0, column=0, padx=1, pady=1)
        ttk.Button(col, text="🗑 Quitar", width=11, command=self.quitar).grid(row=0, column=1, padx=1, pady=1)
        ttk.Button(col, text="▲ Subir", width=11, command=lambda: self.mover(-1)).grid(row=1, column=0, padx=1, pady=1)
        ttk.Button(col, text="▼ Bajar", width=11, command=lambda: self.mover(1)).grid(row=1, column=1, padx=1, pady=1)
        pie = ttk.Frame(self)
        pie.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Label(pie, text="Pie de la imagen marcada (opcional):").pack(side="left")
        self.var_pie = tk.StringVar()
        self.ent_pie = ttk.Entry(pie, textvariable=self.var_pie)
        self.ent_pie.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.ent_pie.bind("<KeyRelease>", lambda e: self._cambio_pie())
        self._pintar()

    # ---------- lo que lee y escribe el editor ----------
    def poner(self, lista):
        """Enseña las imágenes de un bloque de hechos o de una pregunta."""
        self.lista = [dict(im) for im in (lista or [])]
        self._pintar(0 if self.lista else None)

    def sacar(self):
        return [dict(im) for im in self.lista]

    # ---------- pintar ----------
    def _sel(self):
        s = self.caja.curselection()
        return s[0] if s and s[0] < len(self.lista) else None

    def _pintar(self, seleccionar=None):
        self.caja.delete(0, "end")
        for i, im in enumerate(self.lista, 1):
            texto = "%d. %s" % (i, imagenes.nombre_de(im))
            if im.get("origen"):
                texto += "   (nueva: se copia al guardar)"
            if im.get("pie"):
                texto += "   — %s" % im["pie"]
            self.caja.insert("end", texto)
        if seleccionar is not None and self.lista:
            self.caja.selection_set(max(0, min(seleccionar, len(self.lista) - 1)))
        self.configure(text=" %s (%d/%d) " % (self.titulo, len(self.lista), imagenes.MAXIMO))
        self._pintar_pie()

    def _pintar_pie(self):
        i = self._sel()
        self.var_pie.set("" if i is None else self.lista[i].get("pie", ""))
        self.ent_pie.configure(state="normal" if i is not None else "disabled")

    def _cambio_pie(self):
        i = self._sel()
        if i is None or self.lista[i].get("pie", "") == self.var_pie.get().strip():
            return
        self.lista[i]["pie"] = self.var_pie.get().strip()
        pos = self.ent_pie.index("insert")
        self._pintar(i)
        self.ent_pie.icursor(pos)
        self.app._tocado()

    # ---------- botones ----------
    def anadir(self):
        libres = imagenes.MAXIMO - len(self.lista)
        if libres <= 0:
            self.app.estado("Este recuadro ya tiene %d imágenes, que es el máximo." % imagenes.MAXIMO)
            return
        elegidas = filedialog.askopenfilenames(
            parent=self, title="Añadir imágenes (quedan %d huecos)" % libres,
            filetypes=imagenes.TIPOS_ARCHIVO)
        self.anadir_archivos(list(elegidas or ()))

    def anadir_archivos(self, archivos):
        """Añade esos archivos (hasta completar el máximo). Devuelve cuántos ha añadido."""
        validos = [a for a in archivos if Path(a).suffix.lower() in imagenes.EXTENSIONES]
        libres = imagenes.MAXIMO - len(self.lista)
        for a in validos[:libres]:
            self.lista.append({"src": "", "pie": "", "origen": str(a)})
        hechos = len(validos[:libres])
        if hechos:
            self._pintar(len(self.lista) - 1)
            self.app._tocado()
        sobran = len(validos) - hechos
        raros = len(archivos) - len(validos)
        if sobran or raros:
            self.app.estado(
                ("%d imagen(es) añadida(s)." % hechos)
                + (" %d no caben: el máximo es %d por recuadro." % (sobran, imagenes.MAXIMO) if sobran else "")
                + (" %d archivo(s) no son PNG, JPG, GIF ni WebP." % raros if raros else ""))
        elif hechos:
            self.app.estado("%d imagen(es) añadida(s): se copiarán a la carpeta del supuesto al guardar." % hechos)
        return hechos

    def quitar(self):
        i = self._sel()
        if i is None:
            return
        del self.lista[i]
        self._pintar(i)
        self.app._tocado()

    def mover(self, paso):
        i = self._sel()
        if i is None or not 0 <= i + paso < len(self.lista):
            return
        self.lista[i], self.lista[i + paso] = self.lista[i + paso], self.lista[i]
        self._pintar(i + paso)
        self.app._tocado()

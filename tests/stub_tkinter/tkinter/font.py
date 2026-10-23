from tkinter import _mk
def __getattr__(n): return _mk(n)

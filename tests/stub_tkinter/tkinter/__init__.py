class _M(type):
    def __getattr__(c, n): return _mk(n)
def _mk(n): return _M(n, (object,), {"__init__": lambda self,*a,**k: None})
def __getattr__(n): return _mk(n)
Tk=_mk("Tk"); Frame=_mk("Frame")

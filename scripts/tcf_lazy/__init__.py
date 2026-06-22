"""tcf_lazy — SHIM de compat. A view lazy foi promovida pro core em `tcf.view` (A4, 0.8).

    from tcf import view            # caminho canônico (vai no wheel)
    from tcf_lazy import view       # ainda funciona (re-exporta de tcf.view)

    v = view(encode(table))                 # conecta, NÃO descomprime
    v.count()                               # toca a coluna mais barata
    v.where("cidade", "SP").sum("valor")    # toca só cidade + valor

Mantido pra não quebrar código/labs que importam `tcf_lazy`. Ver src/tcf/view.py.
"""
from tcf.view import Filtered, LazyTCF, view

__all__ = ["LazyTCF", "Filtered", "view"]

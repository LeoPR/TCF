"""tcf_lazy — view lazy/consultável sobre um blob TCF (gadget auxiliar, lê #TCF.7).

    from tcf import encode
    from tcf_lazy import view

    v = view(encode(table))                 # conecta, NÃO descomprime
    v.count()                               # toca a coluna mais barata
    v.where("cidade", "SP").sum("valor")    # toca só cidade + valor

Não faz parte do TCF-CORE; não toca src/tcf. Ver lazy.py.
"""
from .lazy import LazyTCF, Filtered, view

__all__ = ["LazyTCF", "Filtered", "view"]

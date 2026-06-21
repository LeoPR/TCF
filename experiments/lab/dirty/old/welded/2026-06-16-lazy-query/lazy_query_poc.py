"""PoC — "lazy decode" / consulta com descompressao seletiva sobre um blob TCF.

PROPOSTA (nao welded, fora de src/tcf). Demonstra a tese da 1.0: conectar a um
.tcf e so' descomprimir o necessario quando um agregador e' puxado.

Ideia: o header multi-col ja' diz nome/modo/tamanho de cada coluna. Da' pra
FATIAR o corpo por coluna sem decodificar nada; cada coluna so' e' descomprimida
sob demanda (column pruning). Uma query como "soma(valor) onde cidade=SP" toca
apenas {cidade, valor} — nunca materializa cliente/plano.

Reusa os decoders por-coluna do core (decode real, byte-exato).
"""
from tcf import encode, decode
from tcf.multi import (
    _decode_v2b, _decode_struct_split, MAGIC_MULTI, MAGIC_MULTI_V2, META_PREFIX,
)
from tcf.decoder import _decode_column


class LazyTCF:
    """View lazy sobre um blob TCF multi-col. Nada e' descomprimido no __init__."""

    def __init__(self, blob: str):
        self._cols = {}     # name -> (mode, body_bytes)  [ainda NAO decodificado]
        self._cache = {}    # name -> list[str]  (decodificado sob demanda)
        self._order = []
        self.touched = []   # colunas que de fato foram descomprimidas (prova seletividade)
        self._parse(blob)

    def _parse(self, blob: str) -> None:
        raw = blob.encode("utf-8")
        nl1 = raw.find(b"\n"); line1 = raw[:nl1]
        is_v7 = line1.startswith(MAGIC_MULTI_V2)
        if not (line1.startswith(MAGIC_MULTI) or is_v7):
            raise ValueError("nao e' TCF multi-col")
        nl2 = raw.find(b"\n", nl1 + 1); line2 = raw[nl1 + 1:nl2]
        if line2.startswith(META_PREFIX):
            meta = line2[len(META_PREFIX):].decode("utf-8")
        elif is_v7:
            meta = (line2[1:] if line2.startswith(b"#") else line2).decode("utf-8")
        else:
            raise ValueError("meta invalido")
        cursor = nl2 + 1
        for p in meta.split(","):
            mode = "tcf"
            if p[:1] in "!@%":
                mode = {"!": "raw", "@": "dict", "%": "split"}[p[0]]; p = p[1:]
            if "=" in p:
                size_str, name = p.split("=", 1); size = int(size_str)
            else:
                size, name = None, p           # ultima coluna: corpo ate' EOF
            body = raw[cursor:] if size is None else raw[cursor:cursor + size]
            self._cols[name] = (mode, body)
            self._order.append(name)
            cursor += len(body)

    # --- introspeccao barata (so' header, sem descomprimir) ---
    def columns(self) -> list[str]:
        return list(self._order)

    def column_bytes(self, name: str) -> int:
        return len(self._cols[name][1])

    # --- decode de UMA coluna, sob demanda + cache + tracking ---
    def _col(self, name: str) -> list[str]:
        if name not in self._cache:
            mode, body = self._cols[name]
            if mode == "raw":
                vals = body.decode("utf-8").split("\n")
            elif mode == "dict":
                vals = _decode_v2b(body)
            elif mode == "split":
                vals = _decode_struct_split(body)
            else:
                vals = _decode_column(body.decode("utf-8"))
            self._cache[name] = vals
            self.touched.append(name)
        return self._cache[name]

    def _nums(self, col, idx=None):
        vals = self._col(col)
        sel = vals if idx is None else [vals[i] for i in idx]
        return [float(v) for v in sel]

    # --- agregadores ---
    def count(self, idx=None):
        if idx is not None:
            return len(idx)
        # conta linhas tocando a coluna de MENOR corpo (a mais barata)
        cheapest = min(self._cols, key=lambda n: len(self._cols[n][1]))
        return len(self._col(cheapest))

    def sum(self, col, idx=None): return sum(self._nums(col, idx))
    def max(self, col, idx=None): return max(self._nums(col, idx))
    def min(self, col, idx=None): return min(self._nums(col, idx))
    def avg(self, col, idx=None):
        n = self._nums(col, idx); return sum(n) / len(n)

    # --- filtro: descomprime SO' a coluna do filtro, devolve uma view restrita ---
    def where(self, col, value):
        vals = self._col(col)
        idx = [i for i, v in enumerate(vals) if v == value]
        return _Filtered(self, idx)


class _Filtered:
    """Resultado de .where(): agrega so' nas linhas que casaram."""
    def __init__(self, parent: LazyTCF, idx: list[int]):
        self.parent = parent; self.idx = idx
    def count(self): return len(self.idx)
    def sum(self, col): return self.parent.sum(col, self.idx)
    def avg(self, col): return self.parent.avg(col, self.idx)
    def max(self, col): return self.parent.max(col, self.idx)
    def min(self, col): return self.parent.min(col, self.idx)


# =========================================================================
if __name__ == "__main__":
    pedidos = {
        "cliente": ["Ana", "Bruno", "Carla", "Diego", "Ana", "Bruno"],
        "cidade":  ["Sao Paulo", "Sao Paulo", "Rio de Janeiro",
                    "Sao Paulo", "Rio de Janeiro", "Sao Paulo"],
        "plano":   ["Premium", "Basic", "Premium", "Premium", "Basic", "Premium"],
        "valor":   ["120", "80", "200", "120", "80", "150"],
    }
    blob = encode(pedidos)
    print("blob TCF (", len(blob.encode()), "B,", len(pedidos), "colunas ):")
    print(blob)
    print("=" * 60)

    def run(label, fn):
        v = LazyTCF(blob)                  # conecta — NAO descomprime nada
        res = fn(v)
        print(f"{label:<42} = {res!r:>10}   tocou: {v.touched}")

    run("count()",                         lambda v: v.count())
    run("sum('valor')",                    lambda v: v.sum("valor"))
    run("avg('valor')",                    lambda v: round(v.avg("valor"), 2))
    run("max('valor') / min('valor')",     lambda v: (v.max("valor"), v.min("valor")))
    run("where('cidade','Sao Paulo').count()", lambda v: v.where("cidade", "Sao Paulo").count())
    run("where('cidade','Sao Paulo').sum('valor')", lambda v: v.where("cidade", "Sao Paulo").sum("valor"))
    run("where('cidade','Sao Paulo').avg('valor')", lambda v: round(v.where("cidade", "Sao Paulo").avg("valor"), 2))

    print("=" * 60)
    print("Controle: decode() materializa TODAS as", len(pedidos), "colunas.")
    full = decode(blob)
    print("RT lossless:", full == pedidos)

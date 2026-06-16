"""tcf_lazy — view lazy sobre um blob TCF: descomprime só o suficiente pra responder.

Gadget AUXILIAR (não faz parte do TCF-CORE; lê o `#TCF.7` existente, NÃO toca src/tcf).
Promovido do PoC `experiments/lab/dirty/2026-06-16-lazy-query/`.

Princípio (a "venda" do TCF): a estrutura do formato já diz, no header, o nome / modo /
tamanho de cada coluna. Dá pra FATIAR o corpo por coluna sem decodificar nada, e só
descomprimir a(s) coluna(s) — e, no filtro, só as linhas — que a pergunta precisa.
`count` / `sum` / `min` / `max` / `avg` + `where`, materializando uma fração do blob.

**Alinhamento de linha**: o formato é row-aligned por POSIÇÃO — a i-ésima posição de
cada coluna é a linha `i`. `where()` devolve os índices das linhas que casaram; agregação
e `select()` em QUALQUER outra coluna usam os MESMOS índices. É assim que "a linha de uma
coluna é a mesma linha na outra".

FUNCIONAL primeiro. Otimizações (saltos dedutivos, agregar runs `*N|` sem expandir, índice
de dicionário, dicas no header) são hooks documentados pra depois — ver NOTAS no fim.
"""
from __future__ import annotations

from collections.abc import Callable

from tcf.multi import (
    MAGIC_MULTI, MAGIC_MULTI_V2, META_PREFIX, _decode_v2b, _decode_struct_split,
)
from tcf.decoder import _decode_column


class LazyTCF:
    """View lazy sobre um blob TCF multi-coluna. Nada é descomprimido no __init__."""

    def __init__(self, blob: str):
        self._mode: dict[str, str] = {}        # name -> 'raw'|'dict'|'split'|'tcf'
        self._body: dict[str, bytes] = {}      # name -> bytes (NÃO decodificado)
        self._cache: dict[str, list[str]] = {}  # name -> valores (sob demanda)
        self._order: list[str] = []
        self.touched: list[str] = []           # colunas que foram descomprimidas
        self._parse(blob)

    # ---- parse do header (barato; sem decodificar corpos) ----
    def _parse(self, blob: str) -> None:
        raw = blob.encode("utf-8")
        nl1 = raw.find(b"\n")
        if nl1 == -1:
            raise ValueError("blob inválido: sem shebang")
        line1 = raw[:nl1]
        is_v7 = line1.startswith(MAGIC_MULTI_V2)
        if not (line1.startswith(MAGIC_MULTI) or is_v7):
            raise ValueError("não é TCF multi-coluna (esperado #TCF.6 M / #TCF.7 M)")
        nl2 = raw.find(b"\n", nl1 + 1)
        if nl2 == -1:
            raise ValueError("blob inválido: sem linha de meta")
        line2 = raw[nl1 + 1:nl2]
        if line2.startswith(META_PREFIX):
            meta = line2[len(META_PREFIX):].decode("utf-8")
        elif is_v7:
            meta = (line2[1:] if line2.startswith(b"#") else line2).decode("utf-8")
        else:
            raise ValueError("meta inválido (#TCF.6 exige '# ')")

        cursor = nl2 + 1
        for part in meta.split(","):
            mode = "tcf"
            if part[:1] in "!@%":
                mode = {"!": "raw", "@": "dict", "%": "split"}[part[0]]
                part = part[1:]
            if "=" in part:
                size_str, name = part.split("=", 1)
                size = int(size_str)
            else:
                size, name = None, part            # última coluna: corpo até EOF
            body = raw[cursor:] if size is None else raw[cursor:cursor + size]
            self._mode[name] = mode
            self._body[name] = body
            self._order.append(name)
            cursor += len(body)

    # ---- introspecção barata (só header) ----
    @property
    def columns(self) -> list[str]:
        return list(self._order)

    def column_bytes(self, name: str) -> int:
        """Tamanho do corpo (comprimido) da coluna, sem decodificar."""
        return len(self._body[name])

    @property
    def total_bytes(self) -> int:
        return sum(len(b) for b in self._body.values())

    @property
    def materialized_bytes(self) -> int:
        """Bytes do blob já descomprimidos (soma dos corpos tocados)."""
        return sum(len(self._body[n]) for n in self.touched)

    # ---- decode de UMA coluna, sob demanda (cache + tracking) ----
    def _col(self, name: str) -> list[str]:
        if name not in self._mode:
            raise KeyError(f"coluna inexistente: {name!r} (tem: {self._order})")
        if name not in self._cache:
            mode, body = self._mode[name], self._body[name]
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

    @property
    def nrows(self) -> int:
        """Número de linhas — toca a coluna de menor corpo (a mais barata)."""
        cheapest = min(self._body, key=lambda n: len(self._body[n]))
        return len(self._col(cheapest))

    # ---- numérico (contrato: ignora vazios; erra em não-numérico) ----
    def _floats(self, col: str, idx: list[int] | None) -> list[float]:
        vals = self._col(col)
        rng = idx if idx is not None else range(len(vals))
        out = []
        for i in rng:
            s = vals[i]
            if s == "":
                continue
            out.append(float(s))   # ValueError em não-numérico = intencional
        return out

    # ---- agregadores ----
    def count(self, idx: list[int] | None = None) -> int:
        return len(idx) if idx is not None else self.nrows

    def sum(self, col: str, idx: list[int] | None = None) -> float:
        return sum(self._floats(col, idx))

    def min(self, col: str, idx: list[int] | None = None) -> float:
        f = self._floats(col, idx)
        if not f:
            raise ValueError(f"sem valores numéricos em {col!r}")
        return min(f)

    def max(self, col: str, idx: list[int] | None = None) -> float:
        f = self._floats(col, idx)
        if not f:
            raise ValueError(f"sem valores numéricos em {col!r}")
        return max(f)

    def avg(self, col: str, idx: list[int] | None = None) -> float:
        f = self._floats(col, idx)
        if not f:
            raise ValueError(f"sem valores numéricos em {col!r}")
        return sum(f) / len(f)

    # ---- filtro: descomprime SÓ a coluna do filtro, devolve view restrita ----
    def where(self, col: str, value=None, *, pred: Callable[[str], bool] | None = None) -> "Filtered":
        vals = self._col(col)
        if pred is not None:
            idx = [i for i, v in enumerate(vals) if pred(v)]
        else:
            idx = [i for i, v in enumerate(vals) if v == value]
        return Filtered(self, idx)

    # ---- linhas alinhadas (decodifica só as colunas pedidas) ----
    def select(self, cols: list[str] | None = None, idx: list[int] | None = None) -> list[dict]:
        cols = cols or self._order
        decoded = {c: self._col(c) for c in cols}
        rng = idx if idx is not None else range(self.nrows)
        return [{c: decoded[c][i] for c in cols} for i in rng]

    # ---- relatório da seletividade (memória/latência) ----
    def report(self) -> dict:
        mat = self.materialized_bytes
        tot = self.total_bytes
        return {
            "total_bytes": tot,
            "materialized_bytes": mat,
            "pct": round(100 * mat / tot, 1) if tot else 0.0,
            "touched": list(self.touched),
            "n_cols": len(self._order),
        }


class Filtered:
    """Resultado de `where()`: agrega/seleciona só nas linhas que casaram (alinhadas)."""

    def __init__(self, parent: LazyTCF, idx: list[int]):
        self._p = parent
        self.indices = idx

    def count(self) -> int:
        return len(self.indices)

    def sum(self, col: str) -> float:
        return self._p.sum(col, self.indices)

    def min(self, col: str) -> float:
        return self._p.min(col, self.indices)

    def max(self, col: str) -> float:
        return self._p.max(col, self.indices)

    def avg(self, col: str) -> float:
        return self._p.avg(col, self.indices)

    def select(self, cols: list[str] | None = None) -> list[dict]:
        return self._p.select(cols, self.indices)

    def where(self, col: str, value=None, *, pred=None) -> "Filtered":
        """Encadeia filtro (AND): restringe os índices atuais."""
        vals = self._p._col(col)
        if pred is not None:
            idx = [i for i in self.indices if pred(vals[i])]
        else:
            idx = [i for i in self.indices if vals[i] == value]
        return Filtered(self._p, idx)


def view(blob: str) -> LazyTCF:
    """Conecta a um blob TCF multi-coluna sem descomprimir. Ver LazyTCF."""
    return LazyTCF(blob)


# ===========================================================================
# NOTAS — otimizações futuras (FUNCIONAL primeiro; estas ficam pra depois):
#   L3  agregar runs `*N|` / `*N+delta|` lendo o marcador, sem expandir a coluna.
#   L4  filtro assistido por índice: coluna `@` (dicionário) dá pertinência de
#       grupo sem decodificar todos os valores.
#   L5  layout p/ baixa latência: organizar/encodar pra uma query-alvo tocar o
#       mínimo (ordenar/agrupar pela chave), mantendo a compressão da transmissão.
#   +   saltos dedutivos / inferência pela estrutura serializada; em último caso,
#       dicas baratas no header. Cada uma medida antes de adotar.
# Acoplamento: reusa decoders internos de src/tcf (_decode_column/_decode_v2b/
#   _decode_struct_split). É um gadget que LÊ o formato; se os internos mudarem,
#   o gadget acompanha. Não toca src/tcf.
# ===========================================================================

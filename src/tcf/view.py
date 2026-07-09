"""tcf.view — view lazy/consultável sobre um blob TCF: descomprime só o suficiente pra responder.

Camada READ-ONLY do TCF (parte do pacote desde A4; lê `#TCF.8M`/`#TCF.7`/`#TCF.6` —
NÃO muda encode/decode/formato). `#TCF.8` (ADR-0029): meta inline + natures (revertidas
LAZY ao materializar a coluna) + colunas anônimas (nome = ordem). Caminho canônico:
`from tcf import view`. O shim em
`scripts/tcf_lazy/` re-exporta daqui pra compat com código/labs antigos.
PoC de origem: `experiments/lab/dirty/old/welded/2026-06-16-lazy-query/`.

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

from collections import Counter
from collections.abc import Callable

from tcf.multi import (
    MAGIC_MULTI_V3,
    _decode_v2b, _decode_struct_split, _v2b_width, _V2B_BASE,
)
from tcf.decoder import _decode_column


def _idx_at(stream: bytes, off: int, width: int) -> int:
    """Decoda UM índice base-94 do stream V2-B na posição de byte `off`."""
    k = 0
    for ch in stream[off:off + width]:
        k = k * _V2B_BASE + (ch - 0x21)
    return k


class LazyTCF:
    """View lazy sobre um blob TCF multi-coluna. Nada é descomprimido no __init__."""

    def __init__(self, blob: str):
        self._mode: dict[str, str] = {}        # name -> 'raw'|'dict'|'split'|'tcf'
        self._nature: dict[str, str] = {}      # name -> nature-id (#TCF.8 :spec)
        self._body: dict[str, bytes] = {}      # name -> bytes (NÃO decodificado)
        self._cache: dict[str, list[str]] = {}  # name -> valores (sob demanda)
        self._dict_cache: dict[str, tuple] = {}  # A3-O2: (unicas,width,stream) parseado do @dict
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
        # #TCF.8M = UNICO multi-col vivo (ADR-0032). Legado #TCF.6/#TCF.7 cortado —
        # fail-loud. Meta INLINE na linha do shebang.
        if not line1.startswith(MAGIC_MULTI_V3):
            raise ValueError(
                f"não é #TCF.8M multi-col (legado #TCF.6/#TCF.7 cortado, ADR-0032; "
                f"git checkout <pre-0.8> pra ler): {line1[:16]!r}")
        is_v8 = True
        meta = line1[len(MAGIC_MULTI_V3):].decode("utf-8")   # inline
        cursor = nl1 + 1

        tokens = meta.split(",")
        n_cols = len(tokens)
        _szbase = 16   # HEX sempre no .8 (T-FMT-HEADER-BASE-HEX + ADR-0032 §3)
        for i, part in enumerate(tokens):
            mode = "tcf"
            if part[:1] in "!@%":
                mode = {"!": "raw", "@": "dict", "%": "split"}[part[0]]
                part = part[1:]
            # sufixo ':id' (nature, so' #TCF.8); coluna anonima -> nome posicional
            nat_id = None
            if is_v8 and ":" in part:
                part, nat_id = part.rsplit(":", 1)
            if "=" in part:
                size_str, name = part.split("=", 1)
                size = int(size_str, _szbase)
            elif i == n_cols - 1:
                size = None                          # ultima: corpo ate' EOF
                name = part if part else str(i)      # nome OU posicional (anonima)
            else:
                size = int(part, _szbase)            # anonima nao-ultima -> so' size
                name = str(i)                        # posicional (nome = ordem)
            body = raw[cursor:] if size is None else raw[cursor:cursor + size]
            self._mode[name] = mode
            self._body[name] = body
            self._order.append(name)
            if nat_id is not None:
                self._nature[name] = nat_id
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
            # Nature self-describing (#TCF.8, ADR-0027): reverte LAZY — so' ao
            # materializar a coluna consultada (decode_value), preservando a
            # laziness (colunas nao tocadas nem decodam o body).
            nat_id = self._nature.get(name)
            if nat_id is not None:
                from tcf.natures import _resolve_nature_id
                spec = _resolve_nature_id(nat_id)
                if spec is not None:
                    vals = [spec.decode_value(v) for v in vals]
            self._cache[name] = vals
            if name not in self.touched:   # A2: evita dupla contagem (coluna ja' tocada via _dict_parts)
                self.touched.append(name)
        return self._cache[name]

    # ---- L3: estrutura (dict/raw) — contar/agrupar SEM expandir as N linhas ----
    def _dict_parts(self, name: str):
        """Parseia um corpo V2-B (`@`): (unicas, width, stream). Decodifica só a
        tabelinha de únicos (K valores), nunca as N linhas. A3-O2: cacheado por
        coluna — ops dict repetidas (group_count + where) não re-decodam a tabela."""
        cached = self._dict_cache.get(name)
        if cached is not None:
            return cached
        body = self._body[name]
        nl = body.find(b"\n")
        ntable = int(body[:nl]); start = nl + 1
        unicas = _decode_column(body[start:start + ntable].decode("utf-8"))
        if name not in self.touched:
            self.touched.append(name)
        parts = (unicas, _v2b_width(len(unicas)), body[start + ntable:])
        self._dict_cache[name] = parts
        return parts

    def _structural_count(self, name: str):
        """Linhas SEM decodificar valores: dict (tamanho do stream) / raw
        (nº de '\\n'). None se o modo exige decode (tcf/split)."""
        mode = self._mode[name]
        if mode == "dict":
            _, width, stream = self._dict_parts(name)
            return len(stream) // width
        if mode == "raw":
            if name not in self.touched:
                self.touched.append(name)
            return self._body[name].count(b"\n") + 1
        return None

    @property
    def nrows(self) -> int:
        """Número de linhas, pelo CAMINHO mais curto (A3-O1):
        1) raw → conta `\\n` (ZERO decode); 2) dict → 1 decode da tabela;
        3) fallback → decodifica a coluna tcf/split mais barata."""
        for name in self._order:                 # O1: raw primeiro (custo zero)
            if self._mode[name] == "raw":
                if name not in self.touched:
                    self.touched.append(name)
                return self._body[name].count(b"\n") + 1
        for name in self._order:                 # senão dict (1 decode de tabela)
            sc = self._structural_count(name)
            if sc is not None:
                return sc
        cheapest = min(self._body, key=lambda n: len(self._body[n]))
        return len(self._col(cheapest))

    def group_count(self, col: str) -> dict[str, int]:
        """Contagem por grupo (`{valor: n}`) SEM expandir a coluna, quando ela é
        dicionário (`@`): tallia o stream de índices + decodifica só os únicos.
        Demais modos: fallback (decode + Counter). É a 'agregação sem expandir'."""
        if self._mode[col] == "dict":
            unicas, width, stream = self._dict_parts(col)
            tally = Counter()
            for off in range(0, len(stream), width):
                tally[unicas[_idx_at(stream, off, width)]] += 1
            return dict(tally)
        return dict(Counter(self._col(col)))

    # ---- L4: filtro assistido por índice de dicionário (sem decodar tudo) ----
    def _dict_target_ids(self, col: str, value, pred):
        """Para uma coluna `@`: (width, stream, set de ids dos únicos que casam).
        Avalia value/pred sobre os K únicos (não sobre as N linhas)."""
        unicas, width, stream = self._dict_parts(col)
        if pred is not None:
            ids = {i for i, u in enumerate(unicas) if pred(u)}
        else:
            ids = {i for i, u in enumerate(unicas) if u == value}
        return width, stream, ids

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

    # ---- L5: layout p/ baixa latência — grupos contíguos (requer sort_by) ----
    def group_ranges(self, key: str) -> dict[str, tuple[int, int]]:
        """`{valor: (início, fim)}` por grupo CONTÍGUO. Pensado pra um blob já
        ordenado por `key` (`encode(table, sort_by=key)`), onde os grupos ficam
        adjacentes (a chave vira runs `*N|`). Erra se a coluna não está agrupada."""
        vals = self._col(key)
        ranges: dict[str, tuple[int, int]] = {}
        i, n = 0, len(vals)
        while i < n:
            v = vals[i]; j = i + 1
            while j < n and vals[j] == v:
                j += 1
            if v in ranges:
                raise ValueError(
                    f"coluna {key!r} não está agrupada (valor {v!r} reaparece); "
                    f"use encode(table, sort_by={key!r}) pro layout L5"
                )
            ranges[v] = (i, j); i = j
        return ranges

    def agg_by(self, key: str, col: str | None = None, op: str = "count") -> dict:
        """Group-by sobre o layout ordenado: `{valor_da_chave: agregado}`.
        `op='count'` (default) usa só os intervalos; `sum/min/max/avg` agregam `col`
        em cada intervalo (a coluna é decodificada UMA vez; cada grupo = um slice).
        É o 'qtd por usuário': `agg_by('usuario', 'qtd', 'sum')`."""
        ranges = self.group_ranges(key)
        if op == "count":
            return {v: e - s for v, (s, e) in ranges.items()}
        fn = {"sum": self.sum, "min": self.min, "max": self.max, "avg": self.avg}[op]
        return {v: fn(col, range(s, e)) for v, (s, e) in ranges.items()}

    # ---- filtro: descomprime SÓ a coluna do filtro, devolve view restrita ----
    def where(self, col: str, value=None, *, pred: Callable[[str], bool] | None = None) -> "Filtered":
        if self._mode[col] == "dict":           # L4: varre o stream, sem decodar os N valores
            width, stream, ids = self._dict_target_ids(col, value, pred)
            idx = [i for i, off in enumerate(range(0, len(stream), width))
                   if _idx_at(stream, off, width) in ids]
            return Filtered(self, idx)
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
        p = self._p
        if p._mode[col] == "dict":              # L4: lê só as posições já filtradas no stream
            width, stream, ids = p._dict_target_ids(col, value, pred)
            idx = [i for i in self.indices if _idx_at(stream, i * width, width) in ids]
            return Filtered(p, idx)
        vals = p._col(col)
        if pred is not None:
            idx = [i for i in self.indices if pred(vals[i])]
        else:
            idx = [i for i in self.indices if vals[i] == value]
        return Filtered(p, idx)


def view(blob: str) -> LazyTCF:
    """Conecta a um blob TCF multi-coluna sem descomprimir. Ver LazyTCF."""
    return LazyTCF(blob)


# ===========================================================================
# NOTAS — otimizações:
#   L3 (FEITO, via dict/raw) — `nrows`/`group_count` contam/agrupam SEM expandir as
#       N linhas: dicionário (`@`) = tamanho do stream + tally; raw = nº de '\n'.
#       ACHADO (verificado, 2026-06-16): agregar os runs `*N|` direto no modo-tcf
#       NÃO é barato/separável — OBAT+HCC entrelaçam o valor com refs de outras
#       linhas (invariante de contagem falhou em colunas tipo-ID; 0 colunas tcf
#       "clean-numeric"). O ganho estrutural limpo vive no dict/raw. Por isso L3
#       usa o dicionário, não o parse de `*N|` do tcf. tcf/split caem em fallback.
#   L4 (FEITO) — `where` sobre coluna `@` varre só o stream de índices (compara id,
#       sem decodar os N valores); value/pred avaliados sobre os K únicos. Encadeado
#       (AND) lê só as posições já filtradas. Non-dict: fallback (decode + filtro).
#   L5 (FEITO) — layout p/ baixa latência: `encode(table, sort_by=key)` agrupa as linhas
#       (a chave vira runs `*N|` contíguos) → `group_ranges(key)` dá `{valor:(início,fim)}`
#       e `agg_by(key, col, op)` faz group-by por SLICE (cada grupo = um intervalo). É o
#       "qtd por usuário". sort_by é order-free; mantém/melhora a compressão da transmissão.
#   +   saltos dedutivos / inferência pela estrutura; em último caso, dicas no header.
# Acoplamento: reusa decoders internos de tcf.multi/tcf.decoder (_decode_column/
#   _decode_v2b/_decode_struct_split). É a camada que LÊ o formato; se os internos
#   mudarem, ela acompanha. NÃO muda encode/decode/formato (read-only por design).
# ===========================================================================

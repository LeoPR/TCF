"""TCF v0.5 encoder — SRDM (Sort + RLE + Dict + auto-discriM).

Produz arquivos no formato lido por decoder.py.

Header (shebang-style):
  #TCF.5 SRDM          versao 0.5, flags SRDM
  #TCF.5 SRDM\n# s:1,2 com sort em colunas 1 e 2

Algoritmo (mesa rle-dict-unificado, 01-regra.md):
  Para cada posicao i de cada coluna:
    1. Mede run-length R contigua começando em i
    2. Se valor v eh primeira aparicao: literal forçado (declara dict)
    3. Caso contrario: compara custo literal vs ref e escolhe menor
    4. Em runs (R≥2): comparar R*literal vs R*ref se idx existe

Auto-discriminacao (flag M):
  1a passada por coluna: se TODOS valores sao int puro -> marked (`:idx`)
  Caso contrario -> bare (`idx` sem prefixo)

NAO cobre ainda: A (alfabeto), delta, P, L', K, I, Pi.
"""
from __future__ import annotations
import re
from typing import Iterable

from .flags import Flags, DEFAULT_FLAGS


# Versao default da implementacao (TCF v0.5)
_DEFAULT_VERSION = "0.5"


def _format_version(v: str) -> str:
    """Inverso de _normalize_version do decoder.

      '0.5' -> '.5'
      '1.0' -> '1'
      '1.3' -> '1.3'
      '2.10' -> '2.10'
    """
    parts = v.split(".")
    if len(parts) == 1:
        return parts[0]
    major, minor = parts[0], parts[1]
    if major == "0":
        return f".{minor}"
    if minor == "0":
        return major
    return f"{major}.{minor}"


_INT_RE = re.compile(r"^-?\d+$")

# Affix-DICT thresholds (Proposta H, etapa 1)
_AFFIX_MIN_PREFIX_LEN = 4
_AFFIX_MIN_COVERAGE = 0.7
_AFFIX_MIN_GAIN_BYTES = 50  # gain previsto minimo p/ ativar


def _detect_affix(values: list[str]) -> tuple[str, float]:
    """Detecta longest common prefix com tolerancia.

    Retorna (prefix, coverage). Se nao vale a pena, retorna ("", 0).
    """
    if not values:
        return "", 0.0
    n = len(values)

    # Tenta LCP completo primeiro
    p = values[0]
    for v in values[1:]:
        i = 0
        while i < min(len(p), len(v)) and p[i] == v[i]:
            i += 1
        p = p[:i]
        if not p:
            break

    if len(p) >= _AFFIX_MIN_PREFIX_LEN:
        # Estima ganho: cobertura 100%
        gain = (n - 1) * len(p) - 30  # ~30B de overhead da declaracao
        if gain >= _AFFIX_MIN_GAIN_BYTES:
            return p, 1.0
        return "", 0.0

    # LCP completo nao vale; tenta com cobertura parcial
    candidate = values[0]
    while len(candidate) >= _AFFIX_MIN_PREFIX_LEN:
        matches = sum(1 for v in values if v.startswith(candidate))
        c = matches / n
        if c >= _AFFIX_MIN_COVERAGE:
            # Ganho com cobertura parcial
            marker_cost = (n - matches) * 2  # \! marker
            gain = matches * (len(candidate) - 1) - 30 - marker_cost
            if gain >= _AFFIX_MIN_GAIN_BYTES:
                return candidate, c
            return "", 0.0
        candidate = candidate[:-1]
    return "", 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_columns(rows: list[dict] | dict[str, list]) -> dict[str, list[str]]:
    """Normaliza input: list[dict] ou dict[col, list] -> dict[col, list[str]]."""
    if isinstance(rows, dict):
        return {k: [str(v) for v in vals] for k, vals in rows.items()}
    if not rows:
        return {}
    cols = list(rows[0].keys())
    out: dict[str, list[str]] = {c: [] for c in cols}
    for r in rows:
        for c in cols:
            out[c].append(str(r.get(c, "")))
    return out


def _count_runs(values: list[str]) -> int:
    if not values:
        return 0
    runs = 1
    for i in range(1, len(values)):
        if values[i] != values[i - 1]:
            runs += 1
    return runs


def _infer_discrim(values: list[str]) -> str:
    """Coluna onde TODOS os literais sao int puro -> marked. Senao -> bare."""
    for v in values:
        if not _INT_RE.match(v):
            return "bare"
    return "marked"


# ---------------------------------------------------------------------------
# Sort
# ---------------------------------------------------------------------------

def _auto_detect_sort_keys(columns: dict[str, list[str]],
                            max_keys: int = 3) -> list[str]:
    """Heuristica: escolhe ate `max_keys` colunas com cardinality baixa que
    reduzem mais runs quando ordenadas. Tie-break por menor cardinality.
    """
    if not columns:
        return []
    n = len(next(iter(columns.values())))
    if n < 4:
        return []  # poucos rows: sort raramente compensa

    candidates = []
    for col, vals in columns.items():
        c = len(set(vals))
        if c < 2 or c > n / 2:
            continue
        unsorted_runs = _count_runs(vals)
        sorted_runs = _count_runs(sorted(vals))
        gain = unsorted_runs - sorted_runs
        if gain > 0:
            candidates.append((col, gain, c))
    candidates.sort(key=lambda x: (-x[1], x[2]))
    return [c[0] for c in candidates[:max_keys]]


def _apply_sort(columns: dict[str, list[str]],
                sort_keys: list[str]) -> dict[str, list[str]]:
    """Sort multi-key. Strings ordenadas lex; numeros ordenados numericamente
    quando a coluna inteira eh int puro.
    """
    if not sort_keys or not columns:
        return columns
    n = len(next(iter(columns.values())))
    if n == 0:
        return columns

    # Decide tipo de ordenacao por coluna-chave
    key_types = {}
    for k in sort_keys:
        if k in columns:
            try:
                _ = [int(v) for v in columns[k]]
                key_types[k] = "int"
            except (ValueError, TypeError):
                key_types[k] = "str"

    def key_fn(i: int) -> tuple:
        out = []
        for k in sort_keys:
            if k not in columns:
                continue
            v = columns[k][i]
            if key_types[k] == "int":
                out.append(int(v))
            else:
                out.append(v)
        return tuple(out)

    indices = sorted(range(n), key=key_fn)
    return {col: [vals[i] for i in indices] for col, vals in columns.items()}


# ---------------------------------------------------------------------------
# Encode de uma coluna
# ---------------------------------------------------------------------------

def _ref_cost(idx: int, discrim: str) -> int:
    """Bytes de uma ref (sem newline, sem `*` de RLE)."""
    digits = len(str(idx))
    return digits + (1 if discrim == "marked" else 0)


def _literal_cost(v: str) -> int:
    return len(v)


def _emit_token(R: int, kind: str, payload: str, discrim: str) -> str:
    """Constroi linha do token.

    kind: "literal" | "ref"
    payload: valor literal ou string do idx
    """
    body: str
    if kind == "literal":
        body = payload
    else:  # ref
        body = (":" + payload) if discrim == "marked" else payload
    if R > 1:
        return f"{R}*{body}"
    return body


def _encode_column(values: list[str], discrim: str,
                    flags: Flags,
                    affix_prefix: str = "") -> list[str]:
    """Aplica regra unificada. Retorna lista de linhas-token (sem newline).

    Se `affix_prefix` for nao-vazio, valores que comecam com ele sao
    emitidos com o prefixo removido; valores que NAO comecam recebem
    marker `\\!` na frente.
    """
    out: list[str] = []
    col_dict: dict[str, int] = {}  # value efetivo (apos remocao de affix) -> idx
    i = 0
    n = len(values)

    # Pre-processa values aplicando affix
    if affix_prefix:
        effective_values = []
        for v in values:
            if v.startswith(affix_prefix):
                effective_values.append(v[len(affix_prefix):])
            else:
                effective_values.append("\\!" + v)  # excecao
    else:
        effective_values = values

    while i < n:
        v = effective_values[i]

        # Mede run-length R
        R = 1
        if flags.R:
            while i + R < n and effective_values[i + R] == v:
                R += 1

        is_first = v not in col_dict

        if is_first:
            if flags.D:
                col_dict[v] = len(col_dict) + 1
            out.append(_emit_token(R, "literal", v, discrim))
        else:
            idx = col_dict[v]
            cost_lit = _literal_cost(v)
            cost_ref = _ref_cost(idx, discrim)
            if cost_ref < cost_lit:
                out.append(_emit_token(R, "ref", str(idx), discrim))
            else:
                out.append(_emit_token(R, "literal", v, discrim))

        i += R

    return out


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

def _emit_header(flags: Flags,
                  sort_keys: list[str],
                  discrim: dict[str, str],
                  emit_discrim: bool,
                  columns: dict[str, list[str]] | None = None,
                  header_style: str = "compact") -> list[str]:
    """Monta linhas de header.

    header_style:
      - "verbose": '# sort: comprador, produto' (legivel)
      - "compact": '# s:1,2' (indices 1-based, sem espacos)  — DEFAULT
    """
    out = [f"#TCF{_format_version(_DEFAULT_VERSION)} {flags.to_string()}"]
    if sort_keys:
        if header_style == "compact" and columns:
            col_names = list(columns.keys())
            indices = []
            for k in sort_keys:
                if k in col_names:
                    indices.append(str(col_names.index(k) + 1))
            if indices:
                out.append(f"# s:{','.join(indices)}")
        else:
            out.append(f"# sort: {', '.join(sort_keys)}")
    if emit_discrim and discrim:
        if header_style == "compact" and columns:
            col_names = list(columns.keys())
            # so emite os marked (bare eh default quando M off)
            marked_indices = [
                str(col_names.index(c) + 1)
                for c, d in discrim.items()
                if c in col_names and d == "marked"
            ]
            if marked_indices:
                out.append(f"# d:{','.join(marked_indices)}")
        else:
            parts = [f"{c}={d}" for c, d in discrim.items()]
            out.append(f"# discrim: {', '.join(parts)}")
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def encode(rows: list[dict] | dict[str, list],
            flags: Flags | None = None,
            sort_keys: list[str] | None = None,
            discrim: dict[str, str] | None = None,
            header_style: str = "compact") -> str:
    """Encoda dados em TCF v0.5.

    Args:
        rows: list[dict] (row-oriented) ou dict[col, list] (columnar)
        flags: subset de features ativas. Default = SRDM (M no decoder cuida
               da auto-discrim mesmo sem M no encoder, mas aqui ativamos
               por consistencia)
        sort_keys: lista de colunas para sort. None = auto-detect se flag S.
        discrim: override manual de discrim por coluna. None = auto-detect.
        header_style: "compact" (default, '# s:1,2') ou "verbose" ('# sort: ...').

    Returns:
        Texto TCF v0.5 (string).
    """
    if flags is None:
        flags = Flags(S=True, R=True, D=True, M=True)

    columns = _to_columns(rows)
    if not columns:
        return f"#TCF{_format_version(_DEFAULT_VERSION)} {flags.to_string()}\n"

    # Sort (flag S)
    if flags.S:
        if sort_keys is None:
            sort_keys = _auto_detect_sort_keys(columns)
        columns = _apply_sort(columns, sort_keys)
    else:
        sort_keys = []

    # Discriminacao por coluna (flag M)
    final_discrim: dict[str, str] = {}
    for col, vals in columns.items():
        if discrim and col in discrim:
            final_discrim[col] = discrim[col]
        elif flags.M:
            final_discrim[col] = _infer_discrim(vals)
        else:
            final_discrim[col] = "bare"

    # Decide se emite # discrim:
    # Quando M esta ativo, decoder infere igual — entao podemos omitir
    emit_discrim = (not flags.M) and bool(final_discrim)

    # Detecta affix por coluna se flag P ativa
    affix_per_col: dict[str, str] = {}
    if flags.P:
        for col, vals in columns.items():
            # So tenta affix em colunas string (nao numericas puras)
            if final_discrim[col] == "marked":
                continue
            prefix, coverage = _detect_affix(vals)
            if prefix:
                affix_per_col[col] = prefix

    # Monta saida
    out = _emit_header(flags, sort_keys or [], final_discrim, emit_discrim,
                        columns=columns, header_style=header_style)
    for col, vals in columns.items():
        affix = affix_per_col.get(col, "")
        if affix:
            # Escapa aspas no prefixo (raro mas seguro)
            esc = affix.replace('\\', '\\\\').replace('"', '\\"')
            out.append(f'{col}: affix="{esc}"')
        else:
            out.append(f"{col}:")
        col_lines = _encode_column(vals, final_discrim[col], flags,
                                     affix_prefix=affix)
        out.extend(col_lines)

    return "\n".join(out) + "\n"

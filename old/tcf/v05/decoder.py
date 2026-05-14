"""TCF v0.5 decoder — implementacao mínima conforme gramatica formal.

Cobre flags: S, R, D, M (subset SRDM).
NAO cobre ainda: A (alfabeto), delta, P (prefix elision), L' (line-RLE),
K (count-recycling), I (inline mode), Pi (packed absolutes).

Spec: experiments/lab/dirty/2026-05-09-gramatica-densidade/04-gramatica-formal.md

Header sintaxe (shebang-style):
  #TCF.5 SRDM       <- versao 0.5, flags SRDM
  #TCF1 SRDM        <- versao 1.0
  #TCF1.3 SRDMA     <- versao 1.3, flags SRDMA

Regras de versao:
  major 0 -> '.minor'  (ex: 0.5 -> '.5')
  minor 0 -> 'major'   (ex: 1.0 -> '1')
  caso geral -> 'major.minor'
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any

from .flags import Flags


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

@dataclass
class Header:
    version: str = "0.5"
    flags: Flags = field(default_factory=Flags)
    sort_keys: list[str] = field(default_factory=list)
    discrim: dict[str, str] = field(default_factory=dict)  # col -> "bare" | "marked"
    ext: dict[str, str] = field(default_factory=dict)      # col -> "delta" | "prefix" | "packed"
    layout: dict[str, str] = field(default_factory=dict)   # col -> "line" | "inline"
    # Sintaxe compacta: indices 1-based; resolvidos para nomes apos parsear body
    sort_indices: list[int] = field(default_factory=list)
    discrim_indices: list[int] = field(default_factory=list)  # indices marked


_VERSION_TOKEN_RE = re.compile(r"^TCF([\d.]+)(?:\s+(\S*))?\s*$")


def _normalize_version(s: str) -> str:
    """Header version token -> '<major>.<minor>'.

      '.5' -> '0.5'
      '1' -> '1.0'
      '1.3' -> '1.3'
    """
    if not s:
        return "0.0"
    if s.startswith("."):
        return f"0{s}"
    if "." not in s:
        return f"{s}.0"
    return s


def _parse_header(lines: list[str]) -> tuple[Header, int]:
    """Parseia linhas de header; retorna (Header, indice da 1a linha apos)."""
    h = Header()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("#"):
            break
        body = line.lstrip("#").strip()

        # Linha shebang: "TCF.5 SRDM" ou "TCF1.3 SRDMA"
        m = _VERSION_TOKEN_RE.match(body)
        if m:
            h.version = _normalize_version(m.group(1))
            flag_str = m.group(2) or ""
            if flag_str:
                h.flags = Flags.from_string(flag_str)
            i += 1
            continue

        # "sort: col1, col2, ..." (verboso) ou "s:1,2" (compacto)
        if body.lower().startswith("sort:"):
            keys = body.split(":", 1)[1].strip()
            h.sort_keys = [k.strip() for k in keys.split(",") if k.strip()]
            i += 1
            continue
        if body.lower().startswith("s:"):
            keys = body.split(":", 1)[1].strip()
            try:
                h.sort_indices = [int(k.strip()) for k in keys.split(",") if k.strip()]
            except ValueError:
                pass
            i += 1
            continue

        # "discrim: col1=bare, col2=marked" ou "d:3,5" (compacto: indices marked)
        if body.lower().startswith("discrim:"):
            entries = body.split(":", 1)[1].strip()
            for entry in entries.split(","):
                if "=" in entry:
                    k, v = entry.split("=", 1)
                    h.discrim[k.strip()] = v.strip()
            i += 1
            continue
        if body.lower().startswith("d:"):
            entries = body.split(":", 1)[1].strip()
            try:
                h.discrim_indices = [int(k.strip()) for k in entries.split(",") if k.strip()]
            except ValueError:
                pass
            i += 1
            continue

        # "ext: col1=delta, col2=prefix"
        if body.lower().startswith("ext:"):
            entries = body.split(":", 1)[1].strip()
            for entry in entries.split(","):
                if "=" in entry:
                    k, v = entry.split("=", 1)
                    h.ext[k.strip()] = v.strip()
            i += 1
            continue

        # "layout: col1=inline, col2=line"
        if body.lower().startswith("layout:"):
            entries = body.split(":", 1)[1].strip()
            for entry in entries.split(","):
                if "=" in entry:
                    k, v = entry.split("=", 1)
                    h.layout[k.strip()] = v.strip()
            i += 1
            continue

        # Comentario livre — pula
        i += 1

    return h, i


# ---------------------------------------------------------------------------
# Token parsing (line-mode)
# ---------------------------------------------------------------------------

_RUN_PREFIX_RE = re.compile(r"^(\d+)\*(.*)$")


@dataclass
class Token:
    """Forma intermediaria parseada de uma linha."""
    kind: str         # "literal" | "ref" | "run-literal" | "run-ref"
    value: str = ""   # literal value ou idx (string)
    count: int = 1    # run length


def _parse_line_token(line: str, discrim: str) -> Token:
    """Parseia uma linha em line-mode, dada a regra de discriminacao da coluna.

    discrim: "bare" (refs sao digitos sem prefixo) ou "marked" (refs com `:`).

    Em modo "bare":
      - Linha que eh apenas digitos = ref
      - Linha com nao-digito = literal
      - "N*..." = run

    Em modo "marked":
      - Linha que comeca com `:` seguido de digitos = ref
      - Resto = literal (inclui digitos, que sao literais inteiros)
      - "N*..." = run
    """
    s = line.rstrip("\n")

    # Detecta run
    m = _RUN_PREFIX_RE.match(s)
    if m:
        count = int(m.group(1))
        rest = m.group(2)
        # Sub-token sem o prefixo de count
        sub = _parse_line_token(rest, discrim)
        if sub.kind == "literal":
            return Token(kind="run-literal", value=sub.value, count=count)
        elif sub.kind == "ref":
            return Token(kind="run-ref", value=sub.value, count=count)
        else:
            raise ValueError(f"run cannot wrap another run: {s!r}")

    # Sem run prefix
    if discrim == "marked":
        if s.startswith(":"):
            # ref marcada
            idx_str = s[1:]
            if not idx_str.isdigit():
                raise ValueError(f"marked ref with non-digit body: {s!r}")
            return Token(kind="ref", value=idx_str)
        else:
            return Token(kind="literal", value=s)
    else:  # bare
        if s.isdigit():
            return Token(kind="ref", value=s)
        else:
            return Token(kind="literal", value=s)


# ---------------------------------------------------------------------------
# Auto-discrim (flag M) — 1a passada por coluna
# ---------------------------------------------------------------------------

_INT_RE = re.compile(r"^-?\d+$")


def _infer_discrim(column_lines: list[str]) -> str:
    """Infere discriminacao da coluna olhando os literais.

    Regra (do user, mesa unificada):
      - Coluna onde TODOS os literais sao inteiros puros: "marked" (refs com `:`)
      - Senao: "bare" (refs sao digitos)

    Para inferir, precisamos ver alguns valores literais (1a aparicoes).
    Heuristica: se nenhuma linha contem nao-digito e nao-`:`, eh marked.
    Se alguma linha tem letras/decimais/etc, eh bare.
    """
    for line in column_lines:
        s = line.rstrip("\n").strip()
        if not s:
            continue
        # Tira prefixo de run se houver: "N*..."
        m = _RUN_PREFIX_RE.match(s)
        if m:
            s = m.group(2)
        # Se tem `:` no inicio, eh ref marcada — pula (nao decide o dominio)
        if s.startswith(":"):
            continue
        # Se NAO eh inteiro puro, dominio nao-numerico → bare
        if not _INT_RE.match(s):
            return "bare"
    # Todos os literais sao inteiros puros → coluna numerica → marked
    return "marked"


# ---------------------------------------------------------------------------
# Body parsing
# ---------------------------------------------------------------------------

# Col header eh restritivo:
#   - Nome de coluna eh identificador valido (letra/_, depois letra/digit/_)
#   - Apos `:` ou (a) fim de linha, opcionalmente espacos, ou
#                  (b) um modifier estilo `<keyword>=...`
# Isso evita confundir literais como `https://...` com col header.
_COL_HEADER_RE = re.compile(
    r"^([a-zA-Z_][a-zA-Z0-9_]*):(\s*$|\s+\w+=.*$)"
)
_AFFIX_RE = re.compile(r'\baffix="((?:[^"\\]|\\.)*)"')


def _parse_col_modifiers(modifier_str: str) -> dict[str, str]:
    """Parseia parte apos `:` em uma linha de col header.

    Suporta: affix="<prefix>" (proposta H, etapa 1)
    Futuro: pattern, dict_ref, etc.
    """
    out: dict[str, str] = {}
    s = modifier_str.strip()
    if not s:
        return out
    am = _AFFIX_RE.search(s)
    if am:
        # Remove escape de \" e \\
        prefix = am.group(1).replace('\\"', '"').replace("\\\\", "\\")
        out["affix"] = prefix
    return out


def _parse_columns(lines: list[str], start: int) -> tuple[dict[str, list[str]],
                                                           dict[str, dict]]:
    """Quebra body em {coluna: [linhas]} + {coluna: {modifiers}}."""
    columns: dict[str, list[str]] = {}
    modifiers: dict[str, dict] = {}
    current_col: str | None = None
    for line in lines[start:]:
        if not line.strip():
            continue
        m = _COL_HEADER_RE.match(line.rstrip("\n"))
        if m:
            current_col = m.group(1).strip()
            mods = _parse_col_modifiers(m.group(2))
            columns[current_col] = []
            modifiers[current_col] = mods
            continue
        if line.startswith("#"):
            continue
        if current_col is not None:
            columns[current_col].append(line.rstrip("\n"))
    return columns, modifiers


# ---------------------------------------------------------------------------
# Decode public API
# ---------------------------------------------------------------------------

def decode(text: str) -> dict[str, list[Any]]:
    """Decodifica um arquivo TCF v0.5 em dict[col, lista de valores].

    Tipo dos valores: por enquanto todos como string. Type-preserving via
    `# ext:` ou flag de tipo eh extensao futura.
    """
    lines = text.splitlines(keepends=False)
    if not lines:
        return {}

    header, body_start = _parse_header(lines)
    raw_columns, col_modifiers = _parse_columns(lines, body_start)

    # Resolve indices compactos para nomes (sintaxe compacta '# s:1,2', '# d:3')
    col_names_list = list(raw_columns.keys())
    if header.sort_indices and not header.sort_keys:
        header.sort_keys = [col_names_list[i - 1]
                             for i in header.sort_indices
                             if 1 <= i <= len(col_names_list)]
    if header.discrim_indices and not header.discrim:
        for idx in header.discrim_indices:
            if 1 <= idx <= len(col_names_list):
                header.discrim[col_names_list[idx - 1]] = "marked"

    decoded: dict[str, list[str]] = {}
    for col_name, col_lines in raw_columns.items():
        # Descobre discriminacao
        if col_name in header.discrim:
            discrim = header.discrim[col_name]
        elif header.flags.M:
            discrim = _infer_discrim(col_lines)
        else:
            discrim = "bare"

        # Affix da coluna (se houver)
        affix_prefix = col_modifiers.get(col_name, {}).get("affix", "")

        # Parseia cada linha em token
        tokens = [_parse_line_token(line, discrim) for line in col_lines if line.strip()]

        # Resolve dict + emite valores (no espaço efetivo, sem o prefix)
        col_dict: list[str] = []
        effective_out: list[str] = []

        for tok in tokens:
            if tok.kind == "literal":
                v = tok.value
                if header.flags.D:
                    col_dict.append(v)
                effective_out.append(v)
            elif tok.kind == "ref":
                idx = int(tok.value) - 1
                if idx < 0 or idx >= len(col_dict):
                    raise ValueError(
                        f"ref idx out of bounds in col {col_name!r}: "
                        f"got {tok.value}, dict has {len(col_dict)} entries"
                    )
                effective_out.append(col_dict[idx])
            elif tok.kind == "run-literal":
                v = tok.value
                if header.flags.D:
                    col_dict.append(v)
                for _ in range(tok.count):
                    effective_out.append(v)
            elif tok.kind == "run-ref":
                idx = int(tok.value) - 1
                if idx < 0 or idx >= len(col_dict):
                    raise ValueError(
                        f"run-ref idx out of bounds in col {col_name!r}: "
                        f"got {tok.value}, dict has {len(col_dict)} entries"
                    )
                v = col_dict[idx]
                for _ in range(tok.count):
                    effective_out.append(v)
            else:
                raise ValueError(f"unknown token kind: {tok.kind}")

        # Aplica affix de volta (se houver)
        if affix_prefix:
            out: list[str] = []
            for v in effective_out:
                if v.startswith("\\!"):
                    out.append(v[2:])  # excecao — sem prefix
                else:
                    out.append(affix_prefix + v)
        else:
            out = effective_out

        decoded[col_name] = out

    return decoded

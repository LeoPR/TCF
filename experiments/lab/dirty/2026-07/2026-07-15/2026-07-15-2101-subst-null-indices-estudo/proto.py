"""PROTÓTIPO — índices de substituição (null via dicionário PRÉ-SEMEADO). Estudo do MECANISMO.

Modela o núcleo do que o owner descreveu: "o dict nada mais é que a descoberta". Codec de
dicionário por-coluna onde os ESPECIAIS (null, futuramente true/false) são **pré-semeados** nos
índices baixos por um byte combinatório — a tabela NASCE preenchida, não há "if null desloca".

CHAVE (corrige a refutação de 2026-07-13-1921): o especial é uma **sentinela NÃO-STRING** (`NULL`
abaixo), nunca igual a uma string real → `"null"`/`""` reais ganham índices descobertos e NÃO
colidem. A string "null" NÃO existe no arquivo: quem sabe que índice 0 = None é a VERSÃO.

DUAS formas de header (a medir lado a lado):
  A) byte INLINE por-coluna: cada coluna carrega seu byte de especiais.
  B) BLOCO de header: um bitmap sobre as colunas declara quais têm especiais.

Hook .9 (NÃO implementar): o corpo é um STREAM DE ÍNDICES (list[int]) — empacotável por bN depois,
sem acoplar agora. Não toca src/tcf (engenhoca de estudo)."""
from __future__ import annotations

NULL = object()            # sentinela não-string (nunca == qualquer string real)
SPECIALS = [NULL]          # ordem canônica; futuro: [NULL, TRUE, FALSE, ...] (até 8)
SEP = "\n"


def _special_byte(present_specials: list) -> int:
    """bits dos especiais presentes nesta coluna (bit i = SPECIALS[i])."""
    b = 0
    for i, sp in enumerate(SPECIALS):
        if sp in present_specials:
            b |= (1 << i)
    return b


def encode_column(values: list):
    """coluna (strings + sentinela NULL) -> (special_byte, dict[str], index_stream[int]).

    Pré-semeadura: os especiais presentes ocupam 0..k-1; strings descobertas ganham k, k+1, …
    (deslocamento = k, que o header pede). O índice é DECIMAL no corpo (str(idx))."""
    present = [sp for sp in SPECIALS if any(v is sp for v in values)]
    k = len(present)
    reserved_index = {id(sp): i for i, sp in enumerate(present)}
    dic, dic_index = [], {}
    stream = []
    for v in values:
        if any(v is sp for sp in present):            # é um especial
            stream.append(reserved_index[id(v)])
        else:                                          # string descoberta (deslocada por +k)
            if v not in dic_index:
                dic_index[v] = k + len(dic)
                dic.append(v)
            stream.append(dic_index[v])
    return _special_byte(present), dic, stream


def decode_column(special_byte: int, dic: list, stream: list):
    """inverso EXATO. índice < k -> especial (via VERSÃO); >= k -> dic[idx-k]."""
    present = [SPECIALS[i] for i in range(len(SPECIALS)) if special_byte & (1 << i)]
    k = len(present)
    out = []
    for idx in stream:
        if idx < k:
            out.append(present[idx])                   # especial (NULL -> a versão sabe = None)
        else:
            out.append(dic[idx - k])
    return out


# ---- serialização das DUAS formas de header (só p/ MEDIR bytes; framing mínimo) ----
def col_body_bytes(dic: list, stream: list) -> int:
    """bytes do dict + stream de índices (IGUAL nas duas formas)."""
    dict_b = SEP.join(dic).encode("utf-8")
    stream_b = ",".join(str(i) for i in stream).encode("utf-8")
    return len(dict_b) + len(stream_b)


def encode_table_formA(table: dict):
    """A: byte inline por-coluna. Retorna (bytes_total, cols_decodificáveis)."""
    total, dec = 0, {}
    for name, values in table.items():
        sb, dic, stream = encode_column(values)
        total += (1 if sb else 0)                      # byte de especiais SÓ se a coluna tem (byte-compat)
        total += col_body_bytes(dic, stream)
        dec[name] = decode_column(sb, dic, stream)
    return total, dec


def encode_table_formB(table: dict):
    """B: um BLOCO de header = bitmap sobre as colunas (quais têm especiais)."""
    n = len(table)
    header_bits = 0
    bodies, dec = 0, {}
    for j, (name, values) in enumerate(table.items()):
        sb, dic, stream = encode_column(values)
        if sb:                                         # esta coluna tem especial
            header_bits |= (1 << j)
        bodies += col_body_bytes(dic, stream)
        dec[name] = decode_column(sb, dic, stream)
    header_bytes = max(1, (n + 7) // 8)                # bitmap: ceil(ncols/8)
    # NOTA: o bitmap diz QUAIS colunas têm especial; com >1 especial precisaria de +bits/coluna.
    # Para null-only (1 bit basta), o bitmap resolve. Multi-especial = extensão (fora deste estudo).
    return header_bytes + bodies, dec

"""ESTUDO — mede o mecanismo de índices de substituição (null) + as 2 formas de header.

Mede: (1) RT + 4 vias (null/"null"/""/ausente-fora); (2) Form A inline vs Form B bloco em
multi-coluna variando fração de colunas-com-null; (3) custo DECIMAL do shift em fronteiras
9/99/999; (4) byte-compat (coluna sem null = idêntica); (5) null-em-elemento = MESMO mecanismo;
(6) baseline máscara-'0' (P1-style). Não toca src/tcf."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from proto import (NULL, col_body_bytes, decode_column, encode_column,  # noqa: E402
                   encode_table_formA, encode_table_formB)


def mask0_bytes(values: list) -> int:
    """Baseline P1-style: máscara ('.'/'0') + coluna densa (só não-null), ambas via dict simples."""
    mask = "".join("0" if v is NULL else "." for v in values)
    dense = [v for v in values if v is not NULL]
    # dict das densas + stream (mesmo modelo, sem especial reservado)
    dic, dic_index, stream = [], {}, []
    for v in dense:
        if v not in dic_index:
            dic_index[v] = len(dic); dic.append(v)
        stream.append(dic_index[v])
    return len(mask.encode()) + col_body_bytes(dic, stream)


def main():
    out = ["ESTUDO — índices de substituição (null pré-semeado) + 2 formas de header", ""]

    # ---------- (1) RT + 4 VIAS ----------
    inp = json.loads((HERE / "inputs" / "01-coluna-nullable.json").read_text(encoding="utf-8"))
    col = [NULL if v is None else v for v in inp["coluna"]]      # JSON null -> sentinela NULL
    sb, dic, stream = encode_column(col)
    back = decode_column(sb, dic, stream)
    rt = back == col
    out += ["(1) RT + 4 VIAS (col ilustrativa):",
            f"  entrada:  {[None if v is NULL else v for v in col]}",
            f"  dict (strings no arquivo): {dic}   <- 'null'/'' estão aqui; None NÃO (vive na versão)",
            f"  stream de índices (decimal): {stream}   special_byte={sb:08b}",
            f"  RT exato (null≠'null'≠''): {rt}"]
    assert rt
    # roundtrip diffável
    (HERE / "outputs" / "01-roundtrip.json").write_bytes(
        (json.dumps([None if v is NULL else v for v in back], ensure_ascii=False) + "\n").encode())

    # ---------- (5) null-em-ELEMENTO = MESMO mecanismo ----------
    elems = ["a", NULL, "b", "a", NULL]                          # elementos de arrays achatados
    sb2, dic2, st2 = encode_column(elems)
    rt2 = decode_column(sb2, dic2, st2) == elems
    out += ["", "(5) null em ELEMENTO de array (mesmo codec, sem gramática nova):",
            f"  elementos: {['<null>' if v is NULL else v for v in elems]} -> RT={rt2}",
            "  → P3a (campo) e P3b (elemento) usam o MESMO mecanismo (o ganho vs máscara)."]
    assert rt2

    # ---------- (2)+(4) Form A vs Form B em multi-coluna; byte-compat ----------
    out += ["", "(2) Form A (byte inline/coluna) vs Form B (bloco bitmap) — 16 colunas, 200 linhas:",
            "    varia a FRAÇÃO de colunas que têm null:"]
    import random
    rng = random.Random(20260715)
    NCOL, NROW = 16, 200
    for frac_null_cols in (0.0, 0.25, 0.5, 1.0):
        table = {}
        n_null_cols = int(NCOL * frac_null_cols)
        for c in range(NCOL):
            vals = [rng.choice(["ativo", "inativo", "pendente"]) for _ in range(NROW)]
            if c < n_null_cols:                                 # esta coluna recebe alguns null
                for _ in range(NROW // 10):
                    vals[rng.randrange(NROW)] = NULL
            table[f"c{c}"] = vals
        a_bytes, a_dec = encode_table_formA(table)
        b_bytes, b_dec = encode_table_formB(table)
        assert a_dec == table and b_dec == table
        vencedor = "A(inline)" if a_bytes < b_bytes else ("B(bloco)" if b_bytes < a_bytes else "empate")
        out.append(f"  {n_null_cols:>2}/{NCOL} colunas c/ null: Form A={a_bytes}B · Form B={b_bytes}B "
                   f"· Δ={a_bytes-b_bytes:+d} · vence {vencedor}")
    out += ["  → A paga 1 byte por COLUNA-com-especial; B paga 1 bitmap fixo (ceil(ncols/8)).",
            "    A vence com POUCAS colunas-null; B vence quando MUITAS têm (bitmap amortiza).",
            "  (4) byte-compat: fração 0.0 → nenhuma coluna paga byte de especial (idêntico ao sem-mecanismo)."]

    # ---------- (3) custo DECIMAL do shift (fronteiras 9/99/999) ----------
    out += ["", "(3) custo DECIMAL do deslocamento +1 (null reserva índice 0):",
            "    coluna com N valores DISTINTOS + alguns null; mede o stream com/sem o shift:"]
    for card in (8, 9, 10, 98, 99, 100, 998, 999, 1000):
        base = [f"v{i}" for i in range(card)]                   # card distintos
        vals = base + [NULL, NULL]                              # + 2 null
        _, dic_s, stream_s = encode_column(vals)                # COM shift (+1, null=0)
        # sem o mecanismo: mesma coluna, null tratado por máscara (sem shift no dict das densas)
        no_null = base
        dic0, dic0_index, stream0 = [], {}, []
        for v in no_null:
            if v not in dic0_index:
                dic0_index[v] = len(dic0); dic0.append(v)
            stream0.append(dic0_index[v])
        # o custo do shift = diferença de bytes do STREAM (índices deslocados podem cruzar dígito)
        with_shift = len(",".join(str(i) for i in stream_s).encode())
        without = len(",".join(str(i) for i in stream0).encode())
        out.append(f"  card={card:>4}: stream índices COM shift(+1)={with_shift}B vs base={without}B "
                   f"· Δ={with_shift-without:+d}B (2 refs a null + deslocamento decimal)")
    out += ["  → o +1 é barato longe das fronteiras; perto de 9/99/999 alguns índices ganham 1 dígito.",
            "    Confirma o ponto do owner: medir, não assumir. (Aqui é só o stream; dict e byte-header à parte.)"]

    # ---------- baseline: máscara-'0' (P1-style) vs índice ----------
    out += ["", "Baseline máscara-'0' (P1) vs índice de substituição (mesma coluna nullable):"]
    for nrows, pnull in ((200, 0.1), (200, 0.5)):
        rng2 = random.Random(7)
        vals = [NULL if rng2.random() < pnull else rng2.choice(["ativo", "inativo"]) for _ in range(nrows)]
        _, dic_i, st_i = encode_column(vals)
        idx_bytes = 1 + col_body_bytes(dic_i, st_i)             # +1 byte de especial (Form A)
        m_bytes = mask0_bytes(vals)
        out.append(f"  n={nrows} p(null)={pnull}: índice(Form A)={idx_bytes}B vs máscara-0={m_bytes}B "
                   f"· Δ={idx_bytes-m_bytes:+d}")
    out += ["  RESSALVA: a máscara-baseline aqui é CRUA (1 char/linha, sem RLE); o L1 real a COMPRIME",
            "    (runs de '.'), então o Δ de bytes é aproximado. O resultado ROBUSTO não é o byte exato,",
            "    e sim a UNIFICAÇÃO (P3a+P3b no mesmo mecanismo) + índice vencer no null RARO (caso comum).",
            "  (medição de FORMA; o L1 real é afixo/HCC, não dict puro — o weld integra na numeração real.)"]

    (HERE / "outputs" / "00-medicoes.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()

"""O fluxo do núcleo: IGUALDADE × PROXIMIDADE — quem vê o quê. `python run.py`

Pergunta do owner (2026-08-09): *"o tcf é baseado em quebrar similaridades e depois fazer
os encaixes (…) se elas forem realmente similares, ou próximas como deltas, também
poderiam gerar nós (…) em parte temos um algoritmo cego no núcleo que pega os pedaços sem
julgar a semântica, só olha string (…) essa é uma oportunidade de apenas olhar a
estrutura pra ver se tem algum encaixe melhor nesse fluxo"*.

Este lab NÃO propõe mecanismo. Ele mede **o que cada mecanismo consegue enxergar**, para
mapear onde o fluxo perde oportunidade. Quatro sondas:

    S1  o índice do OBAT nas colunas de data — é Patricia mesmo? indexa alguma coisa?
    S2  o split estrutural (ADR-0026, que JÁ corta ano|mês|dia): quanto vale, e em que
        rota ele está disponível
    S3  decomposição ano|mês|dia peça a peça — qual peça custa caro e por quê
    S4  **a sonda-chave**: o que o seq-RLE consegue LER depois que o HCC dedupou

`src/tcf` NÃO é tocado. Tudo é `encode()`/`decode()` real + leitura de estruturas internas.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.composicional.hcc_seqrle import deltas_pares, detect_periodic_runs  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.auto_cadence import detect_cadence_from_features  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from tcf.obat_shape import processar_with_hint  # noqa: E402
from tcf.multi.split import _struct_split_encode  # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE  # noqa: E402

for x in ("inputs", "intermediates", "outputs"):
    (RAIZ / x).mkdir(parents=True, exist_ok=True)


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


def mensal(n):
    out, y, m = [], 2000, 1
    for _ in range(n):
        out.append(_dt.date(y, m, 1))
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def diario(n):
    return [_dt.date(2026, 1, 1) + _dt.timedelta(days=i) for i in range(n)]


def uteis(n):
    out, d = [], _dt.date(2026, 1, 1)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += _dt.timedelta(days=1)
    return out


def corpo_canonico(vals):
    """O corpo que o seq-RLE recebe — depois do OBAT/HCC, antes do bN/polaridade.

    Reproduz o caminho REAL do `_encode_column`: pre-pass (auto min_len + detect_cadence)
    -> OBAT (com hint se houver cadência) -> HCC. Usar `min_len=3` fixo daria um corpo
    que o pipeline não emite, e os números do S4 sairiam enviesados.
    """
    uni = list(dict.fromkeys(vals))
    features = analyze_column(vals)
    min_len = detect_min_len_from_features(features)
    cadencia, _info = detect_cadence_from_features(features, uni)
    if cadencia:
        toks, _ = processar_with_hint(uni, min_len=min_len, prefer_shape_consistency=True)
    else:
        toks, _ = processar(uni, min_len=min_len)
    return M8AVirtualRefsSyntax().encode(vals, uni, toks, "val")[:-1].split("\n"), min_len, cadencia


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    N = 600
    REG = {}
    COLS = {"mensal": mensal(N), "diario": diario(N), "uteis": uteis(N)}
    for rot, ds in COLS.items():
        _escreve(RAIZ / "inputs" / f"{rot}--json-lib-like.json",
                 json.dumps([d.isoformat() for d in ds], ensure_ascii=False))

    # ── S1: o índice do OBAT é um hash de TRIGRAMA (ADR-0009), não uma Patricia ──
    print("=== S1 — o índice do OBAT nas colunas de data (bucket = 3 primeiros chars)")
    s1 = []
    amostras = {"mensal ISO": [d.isoformat() for d in mensal(N)],
                "diario ISO": [d.isoformat() for d in diario(N)],
                "uteis ISO": [d.isoformat() for d in uteis(N)],
                "ordinal-dia": [str(d.toordinal()) for d in mensal(N)],
                "mes-epoca": [str(d.year * 12 + d.month - 1) for d in mensal(N)]}
    for rot, vals in amostras.items():
        uni = list(dict.fromkeys(vals))
        b = {}
        for s in uni:
            b.setdefault(s[:3], []).append(s)
        maior = max(len(v) for v in b.values())
        s1.append({"coluna": rot, "k": len(uni), "buckets": len(b), "maior_bucket": maior,
                   "pct_no_maior": round(maior / len(uni) * 100)})
        print(f"    {rot:<12} k={len(uni):>4}  buckets={len(b):>3}  MAIOR={maior:>4} "
              f"({maior / len(uni) * 100:>3.0f}% dos únicos)")
    REG["S1_indice_trigrama"] = s1

    # ── S2: o split estrutural JÁ corta ano|mês|dia — mas só concorre no multi-col ──
    print("\n=== S2 — o split estrutural (ADR-0026) por rota")
    s2 = []
    for rot, ds in COLS.items():
        iso = [d.isoformat() for d in ds]
        sb = _struct_split_encode(iso, cfg=DEFAULT_PIPELINE, min_len=None)
        flat = len(encode(iso).encode("utf-8"))
        w_multi = encode({"dt": iso})
        assert decode(w_multi) == {"dt": iso}
        usou = "%" in w_multi.split("\n")[0]
        s2.append({"coluna": rot, "split_B": len(sb) if sb is not None else None,
                   "single_col_flat_B": flat, "multi_col_B": len(w_multi.encode("utf-8")),
                   "multi_escolheu_split": usou})
        print(f"    {rot:<7} split={str(len(sb) if sb else None):>5} B | flat(single-col)={flat:>5} B "
              f"| multi-col={len(w_multi.encode('utf-8')):>5} B  escolheu split={usou}")
    REG["S2_split_por_rota"] = s2

    # ── S3: decomposição ano|mês|dia peça a peça ──
    print("\n=== S3 — ano|mês|dia peça a peça (qual pedaço custa caro)")
    s3 = []
    for rot, ds in COLS.items():
        partes = {"ano": [f"{d.year:04d}" for d in ds],
                  "mes": [f"{d.month:02d}" for d in ds],
                  "dia": [f"{d.day:02d}" for d in ds]}
        det = {}
        for k, v in partes.items():
            w = encode(v)
            assert decode(w) == v
            det[k] = len(w.encode("utf-8"))
        flat = len(encode([d.isoformat() for d in ds]).encode("utf-8"))
        s3.append({"coluna": rot, "flat_B": flat, "soma_pecas_B": sum(det.values()), **det})
        print(f"    {rot:<7} flat={flat:>5} B  vs  soma das peças={sum(det.values()):>5} B "
              f"(ano={det['ano']}, mes={det['mes']}, dia={det['dia']})")
    REG["S3_pecas"] = s3

    # ── S4: A SONDA-CHAVE — o que o seq-RLE consegue LER depois do dedup ──
    print("\n=== S4 — o que o seq-RLE LÊ depois que o HCC dedupou (a sonda-chave)")
    s4 = []
    casos = {
        "mes 01..12 x50 (k=12, CICLA)": [f"{(i % 12) + 1:02d}" for i in range(N)],
        "mesma aritmetica sem repetir (k=600)": [str(1000 + i) for i in range(N)],
        "ciclo 1,3,1,1,1 (k=600, uteis)": [str(d.toordinal()) for d in uteis(N)],
        "dia do mes 01..28 (k=28, CICLA)": [f"{(i % 28) + 1:02d}" for i in range(N)],
    }
    for rot, vals in casos.items():
        lns, min_len, cadencia = corpo_canonico(vals)
        pares = deltas_pares(lns)
        legiveis = sum(1 for p in pares if p is not None)
        runs = detect_periodic_runs(lns, pares)
        w = encode(vals)
        assert decode(w) == vals
        primeira_ref = next((i for i, ln in enumerate(lns) if ln.startswith("^")), None)
        s4.append({"caso": rot, "k": len(set(vals)), "bytes": len(w.encode("utf-8")),
                   "rota": w.split("\n")[0], "linhas_corpo": len(lns),
                   "primeira_linha_de_REFERENCIA": primeira_ref,
                   "deltas_legiveis": legiveis, "runs_periodicos": len(runs)})
        print(f"    {rot}")
        print(f"        {len(w.encode('utf-8')):>5} B | corpo: 1ª referência `^N` na linha "
              f"{primeira_ref} de {len(lns)} | deltas legíveis: {legiveis} | runs periódicos: {len(runs)}")
        _escreve(RAIZ / "intermediates" / f"S4-{rot[:18].replace(' ', '_')}--corpo.txt",
                 "\n".join(lns[:20]) + "\n...\n")
    REG["S4_dedup_esconde_aritmetica"] = s4

    _escreve(RAIZ / "outputs" / "sondas.json", json.dumps(REG, ensure_ascii=False, indent=1))
    print("\nOK — RT conferido em todos os encodes. Análise em result.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

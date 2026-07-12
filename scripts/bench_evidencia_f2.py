"""F2 — controle minúsculo do material comprobatório (T-QA-8 F2; T-REL-08 P2b).

Driver REPRODUTÍVEL: gera todos os casos de controle, mede via bench_evidencia
(runner F1, validado contra a régua) e escreve:

    experiments/results/evidencia-0.8/f2/<caso>.jsonl   (1 registro por caso)
    experiments/results/evidencia-0.8/f2/<caso>.tcf     (blobs-exemplo inspecionáveis)
    experiments/results/evidencia-0.8/f2/RESULT.md      (síntese GERADA — medida, não prosa)

Grupos (T-QA-8 §4 F2-1..F2-7):
  A  single-col com/sem header (órfão · stamp · dict-1col · spec)
  B  matriz de readers: decode() × view() por forma de blob
  C  README-propaganda (4×5) + variantes de knob (tabela pro F6)
  D  controles específicos do .8 (escaping, hex na borda, fail-loud, anônimas)
  E  1 blob-exemplo por mecanismo de dict (V2-B w1/w2, split, HCC implícito, natures)
  F  boundary do cap V2-B (K=8192 candidato vs K=8193 skip)

REGRA CPF (T-QA-8 §2.3, owner): medição com DV-VÁLIDOS EFÊMEROS (gerador+seed
20260601 de setup_br_identidades; assert apply_rate==1.0) — blob NUNCA salvo;
o material publicado só carrega DV-INVÁLIDO rotulado fallback-path. O JSONL não
contém valores (só contagens/stats) — publicável.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from bench_evidencia import (  # noqa: E402
    RESULTS_DIR, load_csv_multi, load_csv_single, run_case, validate_pins,
    write_jsonl,
)
from setup_br_identidades import _gen_cnpj, _gen_cpf  # noqa: E402
from tcf import SPEC_CNPJ, SPEC_CPF, SPEC_IP, decode, encode, view  # noqa: E402

F2 = RESULTS_DIR / "f2"
SEED = 20260601

# README-propaganda (README.md §exemplo; CPFs = placeholders INVÁLIDOS por
# convenção — dígitos repetidos, publicáveis)
README_TABLE = {
    "nome":   ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha"],
    "email":  ["ana@acme.com.br", "bruno@acme.com.br", "carla@acme.com.br",
               "diego@acme.com.br"],
    "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plano":  ["Premium", "Premium", "Basic", "Premium"],
    "cpf":    ["111.111.111-11", "222.222.222-22", "333.333.333-33",
               "444.444.444-44"],
}
EMAILS = ["joao@gmail.com", "maria@gmail.com", "pedro@gmail.com"]

_summary: list[dict] = []


def case(cid: str, data, kw: dict | None = None, *, n: int = 9, warmup: int = 2,
         save_blob: bool = False, ephemeral: bool = False, note: str = "",
         require_apply_rate: float | None = None) -> dict:
    """Roda 1 caso, grava JSONL (+ blob se público) e acumula na síntese."""
    rec = run_case(cid, data, kw, n=n, warmup=warmup, seed=SEED if ephemeral else None)
    if ephemeral:
        rec["ephemeral_data"] = ("valores DV-validos regenerados por gerador+seed "
                                 f"{SEED} (setup_br_identidades) — NUNCA publicados; "
                                 "registro so' carrega contagens (T-QA-8 §2.3)")
    if require_apply_rate is not None and rec.get("rt_ok"):
        na = rec["side"].get("nature_apply") or {}
        rates = [v.get("apply_rate") for v in na.values() if isinstance(v, dict)]
        assert rates and all(r == require_apply_rate for r in rates), (
            f"{cid}: apply_rate {rates} != {require_apply_rate} — o caso NAO "
            f"exercitou o codepath esperado (gate §2.3)")
    write_jsonl([rec], F2 / f"{cid}.jsonl")
    if save_blob and rec.get("rt_ok"):
        assert not ephemeral, "blob de dados efemeros NAO pode ser salvo (§2.3)"
        (F2 / f"{cid}.tcf").write_text(encode(data, **(kw or {})),
                                       encoding="utf-8", newline="\n")
    row = {"id": cid, "note": note}
    if rec.get("rt_ok"):
        b = rec["bytes"]
        modes = (rec["side"].get("multi_info") or {}).get("col_modes", {})
        row.update(total=b["total"], header=b["header"], body=b["body"],
                   input=b["input_join_lf"], rt="OK",
                   enc_ms=rec["timing"]["encode"]["median_ns"] / 1e6,
                   modes="".join({"tcf": "t", "raw": "!", "dict": "@",
                                  "split": "%"}[m] for m in modes.values()) or "-")
    else:
        row.update(rt="FAIL", total="-")
    _summary.append(row)
    return rec


# ---------------------------------------------------------------------------
# Grupos
# ---------------------------------------------------------------------------

def grupo_a() -> None:
    """F2-1/F2-2: single com/sem header — custo de header medido no MESMO dado."""
    case("a1-orfao-emails", list(EMAILS), note="single órfão (header 0B)",
         save_blob=True)
    case("a2-stamp-emails", list(EMAILS), {"stamp": True},
         note="version-stamp '#TCF.8\\n' (+7B)", save_blob=True)
    case("a3-dict1col-emails", {"email": list(EMAILS)},
         note="multi de 1 coluna nomeada (#TCF.8M)", save_blob=True)
    case("a4-d1-orfao", load_csv_single(ROOT / "datasets/synthetic/D1-emails-simples.csv"),
         note="D1 órfão (controle da régua, 118B)")


def grupo_b() -> list[dict]:
    """F2-3: matriz decode() × view() por forma de blob (paridade e suporte)."""
    rng = random.Random(SEED)
    seen: set = set()
    cpfs_validos = [_gen_cpf(rng, seen) for _ in range(4)]
    blobs = {
        "orfao": encode(list(EMAILS)),
        "stamp": encode(list(EMAILS), stamp=True),
        "spec-cpf(efemero)": encode(cpfs_validos, nature=SPEC_CPF),
        "M": encode(README_TABLE),
        "M+escaping": encode({"a:b,c=d": ["x", "y"], "no\\me": ["p", "q"]}),
        "M+drop_names": encode(README_TABLE, drop_names=True),
        "M+natures(invalidos)": encode(
            {"cpf": README_TABLE["cpf"], "x": ["a", "b", "c", "d"]},
            nature_per_col={"cpf": SPEC_CPF}),
        "M+sort_by": encode(README_TABLE, sort_by="cidade"),
    }
    matrix = []
    for form, blob in blobs.items():
        dec_ok, view_ok, parity = True, None, "-"
        try:
            d = decode(blob)
        except Exception as e:
            dec_ok, d = f"ERRO: {type(e).__name__}", None
        try:
            v = view(blob)
            view_ok = True
            if isinstance(d, dict):
                parity = ("igual" if {c: v._col(c) for c in v.columns} == d
                          else "DIVERGIU")
        except ValueError:
            view_ok = "não-suportado (fail-loud)"
        matrix.append({"forma": form, "decode": dec_ok, "view": view_ok,
                       "paridade": parity})
    # L3 demo: seletividade da view no blob do README (bytes tocados)
    v = view(blobs["M"])
    v.group_count("cidade")
    rep = v.report()
    matrix.append({"forma": "M (view.group_count('cidade'))",
                   "decode": "-", "view": f"tocou {rep['pct']}% do corpo",
                   "paridade": f"touched={rep['touched']}"})
    return matrix


def grupo_c() -> None:
    """F2-4: README-propaganda re-medido sob 0.8 + variantes (tabela pro F6)."""
    case("c1-readme-default", dict(README_TABLE), note="o exemplo do README (F6)",
         save_blob=True)
    case("c2-readme-fallback-off", dict(README_TABLE), {"fallback": False},
         note="só candidato tcf")
    case("c3-readme-minheader-off", dict(README_TABLE), {"min_header": False},
         note="todas as colunas com size")
    case("c4-readme-dropnames", dict(README_TABLE), {"drop_names": True},
         note="colunas anônimas")
    case("c5-readme-sortby", dict(README_TABLE), {"sort_by": "cidade"},
         note="order-free por cidade")
    case("c6-readme-parallel2", dict(README_TABLE), {"parallel": 2},
         note="byte-idêntico ao serial (pool 2)")


def grupo_d() -> list[dict]:
    """F2-5: controles específicos do .8."""
    case("d1-escaping", {"a:b,c=d": ["x1", "y2"], "no\\me": ["p", "q"],
                         "!bang": ["1", "2"]},
         note="separadores escapados no meta", save_blob=True)
    # hex na borda: colunas raw com body EXATO 15/16B (meta 'f' e '10')
    case("d2-hex-borda-f", {"a": ["aaaaa", "bbbbb", "ccc"], "z": ["fim", "x", "y"]},
         note="1a col raw=15B -> size hex 'f'", save_blob=True)
    case("d3-hex-borda-10", {"a": ["aaaaa", "bbbbb", "cccc"], "z": ["fim", "x", "y"]},
         note="1a col raw=16B -> size hex '10'", save_blob=True)
    case("d4-hex-256", {"a": [f"linha-{i:03d}-xyz" for i in range(20)],
                        "z": ["fim"] * 20},
         note="1a col >=256B -> size hex 3 dígitos")
    case("d5-multi-1col", {"solo": ["um", "dois", "tres"]},
         note="multi de 1 coluna")
    case("d6-anon-ultima-tcf", {"a": [str(i) for i in range(20)],
                                "b": ["constante-longa-x"] * 20},
         {"drop_names": True}, note="última anônima em modo tcf (token vazio)")
    case("d7-col-vazias", {"a": ["", "", ""], "b": ["x", "y", "z"]},
         note="coluna só-vazias (1 linha vazia é dado)")
    # fail-loud paramétrico (controles comportamentais — sem bytes)
    probes = []
    for cid, blob in [("#TCF.8X...", "#TCF.8X2=a,b\nxxyy"),
                      ("#TCF.8H...", "#TCF.8H{a}\nxx"),
                      ("#TCF.9M...", "#TCF.9M2=a,b\nxxyy"),
                      ("#TCF.6 M...", "#TCF.6 M\n# 2=a\nxx"),
                      ("meta vazio s/ body", "#TCF.8M\n"),
                      ("size>body", "#TCF.8Mff=a,!b\nxx\nyy")]:
        try:
            decode(blob)
            probes.append({"blob": cid, "resultado": "ACEITOU (inesperado!)"})
        except (ValueError, TypeError) as e:
            probes.append({"blob": cid,
                           "resultado": f"fail-loud OK ({str(e)[:48]}...)"})
    return probes


def grupo_e() -> None:
    """F2-6: 1 blob-exemplo POR mecanismo de dict (+ natures sob a regra §2.3)."""
    case("e1-v2b-width1", {"uf": ["SP", "RJ", "MG"] * 20, "id": [str(i) for i in range(60)]},
         note="V2-B K=3 (índice width 1)", save_blob=True)
    uniq = [f"item-{i:03d}" for i in range(120)]
    case("e2-v2b-width2", {"sku": [uniq[i % 120] for i in range(400)],
                           "n": [str(i) for i in range(400)]},
         note="V2-B K=120>94 (índice width 2)", save_blob=True)
    case("e3-split", {"quando": [f"2026-07-{d:02d} 12:{m:02d}" for d, m in
                                 zip([1, 2, 3, 1, 2, 3, 1, 2], [10, 10, 10, 20, 20, 20, 30, 30])],
                      "z": list("abcdefgh")},
         note="split '%' (template uniforme, campos low-card)", save_blob=True)
    case("e4-hcc-implicito", ["alpha-beta", "gamma-delta", "alpha-beta",
                              "epsilon", "gamma-delta", "alpha-beta"],
         note="dict implícito HCC (refs ^N no body)", save_blob=True)
    # natures — medição EFÊMERA (DV-válidos por seed; §2.3) + publicado inválido
    rng = random.Random(SEED)
    seen: set = set()
    cpfs = [_gen_cpf(rng, seen) for _ in range(24)]
    cnpjs = [_gen_cnpj(rng, seen) for _ in range(24)]
    ips = [f"10.0.{i % 4}.{i}" for i in range(24)]
    case("e5-nature-cpf-validos", list(cpfs), {"nature": SPEC_CPF},
         ephemeral=True, require_apply_rate=1.0,
         note="spec cpf, DV-válidos EFÊMEROS (apply_rate==1.0)")
    case("e6-nature-cnpj-validos", list(cnpjs), {"nature": SPEC_CNPJ},
         ephemeral=True, require_apply_rate=1.0,
         note="spec cnpj, DV-válidos EFÊMEROS (apply_rate==1.0)")
    case("e7-nature-ip", list(ips), {"nature": SPEC_IP},
         require_apply_rate=1.0, note="spec ip (sintético, sem PII)",
         save_blob=True)
    # ACHADO (gate §2.3 pegou): os placeholders do README (111.111.111-11...)
    # são ARITMETICAMENTE válidos no mod-11 (a invalidade deles é convenção de
    # cadastro) -> o spec COMPRIME (apply_rate 1.0). Fallback-path publicável
    # usa a ANONIMIZAÇÃO da regra do owner: DV re-invalidado por (dv+1)%10.
    def _anon(cpf: str) -> str:          # §2.3: re-invalida o DV -> publicável
        return cpf[:-1] + str((int(cpf[-1]) + 1) % 10)

    anon = [_anon(c) for c in cpfs[:4]]
    case("e8-nature-cpf-anon-publicado", anon, {"nature": SPEC_CPF},
         require_apply_rate=0.0,
         note="FALLBACK-PATH publicável: DV re-invalidado (anonimização §2.3) cai literal",
         save_blob=True)
    mistos = cpfs[:2] + anon[:2]
    case("e9-nature-cpf-misto", mistos, {"nature": SPEC_CPF}, ephemeral=True,
         require_apply_rate=0.5, note="coluna MISTA 2 válidos + 2 anonimizados")
    case("e10-nature-placeholders-readme", list(README_TABLE["cpf"]),
         {"nature": SPEC_CPF}, require_apply_rate=1.0, save_blob=True,
         note="ACHADO: placeholders do README são mod-11-VÁLIDOS -> spec comprime "
              "(a 'invalidade' é convenção de cadastro; nota pro F6/README)")


def grupo_f() -> None:
    """F2-7: boundary do cap de compute do V2-B (8192 candidato / 8193 skip)."""
    for k, cid in ((8192, "f1-v2b-cap-8192"), (8193, "f2-v2b-cap-8193")):
        uniq = [f"u{i:04x}q{i % 7}" for i in range(k)]
        values = uniq + uniq                      # cada único 2x, espalhado
        rec = case(cid, {"k": values}, n=1, warmup=0,
                   note=f"K={k}: {'candidato' if k <= 8192 else 'SKIP (cap)'}")
        mode = (rec["side"]["multi_info"]["col_modes"]["k"]
                if rec.get("rt_ok") else "?")
        _summary[-1]["note"] += f" -> modo {mode}"


# ---------------------------------------------------------------------------
# Síntese (RESULT.md — gerado, tudo medido)
# ---------------------------------------------------------------------------

def emit_result(matrix: list[dict], probes: list[dict]) -> Path:
    L = ["# F2 — controle minúsculo (gerado por scripts/bench_evidencia_f2.py)",
         "", "Registros completos nos `.jsonl` ao lado (schema evidencia-0.8/v1);",
         "blobs `.tcf` = exemplos inspecionáveis (nenhum contém CPF DV-válido — §2.3).",
         "Runner validado contra a régua ANTES da rodada (D1-D9/D17a/real-world).", "",
         "## Casos medidos", "",
         "| caso | total B | header B | body B | input B | modos | enc mediana ms | RT | nota |",
         "|---|---:|---:|---:|---:|---|---:|---|---|"]
    for r in _summary:
        if r["rt"] == "OK":
            L.append(f"| {r['id']} | {r['total']} | {r['header']} | {r['body']} "
                     f"| {r['input']} | {r['modes']} | {r['enc_ms']:.2f} | OK "
                     f"| {r['note']} |")
        else:
            L.append(f"| {r['id']} | - | - | - | - | - | - | FAIL | {r['note']} |")
    L += ["", "## Matriz de readers (F2-3)", "",
          "| forma do blob | decode() | view() | paridade |", "|---|---|---|---|"]
    for m in matrix:
        L.append(f"| {m['forma']} | {m['decode']} | {m['view']} | {m['paridade']} |")
    L += ["", "## Fail-loud paramétrico (F2-5, controles comportamentais)", "",
          "| blob | resultado |", "|---|---|"]
    for p in probes:
        L.append(f"| `{p['blob']}` | {p['resultado']} |")
    L += ["", "Notas fixas: view() cobre SÓ `#TCF.8M` (órfão/stamp/spec = fail-loud",
          "por design — matriz acima); timing de F (boundary) é indicativo (n=1).", ""]
    out = F2 / "RESULT.md"
    out.write_text("\n".join(L), encoding="utf-8", newline="\n")
    return out


def main() -> int:
    assert validate_pins(verbose=False), "régua divergiu — NÃO produza material (F1-4)"
    if F2.exists():                       # artefato GERADO: rodada limpa, sem append duplicado
        import shutil
        shutil.rmtree(F2)
    F2.mkdir(parents=True, exist_ok=True)
    grupo_a()
    matrix = grupo_b()
    grupo_c()
    probes = grupo_d()
    grupo_e()
    grupo_f()
    out = emit_result(matrix, probes)
    print(f"F2 completo: {len(_summary)} casos -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

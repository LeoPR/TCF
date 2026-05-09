"""Workbench sujo — flow categoricos (cenario MAX para TCF).

Testa se os padroes consolidados em flow-pessoas (cabecalho minimal
v0.4, encoding implicito) sobrevivem em dados categoricos com
repeticao — onde RLE/DICT deveriam brilhar.

Dataset: TPC-H supplier — 100 rows, coluna s_nationkey (25 distintos).
Cenarios: A) random; B) sorted; C) mix categ+unico.

Saida: ./output/
"""
from __future__ import annotations
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from tcf import encode_rows, decode, EncodeConfig
from data_sources import load_dataset


HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers (pipe duplo)
# ---------------------------------------------------------------------------

def tee_write_bytes(path: Path, text: str) -> str:
    path.write_bytes(text.encode("utf-8"))
    return text


def encode_csv(rows: list[dict]) -> str:
    """CSV LF puro (lineterminator='\\n', io.StringIO newline='')."""
    buf = io.StringIO(newline="")
    if not rows:
        return ""
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                       lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def encode_json_compact(rows: list[dict]) -> str:
    return json.dumps(rows, separators=(",", ":"))


def encode_tcf(rows: list[dict], level: int) -> str:
    cfg = EncodeConfig(level=level, include_stats=True)
    return encode_rows("supplier", rows, config=cfg)


# ---------------------------------------------------------------------------
# v0.4 envelope (do ciclo 3 do flow-pessoas)
# ---------------------------------------------------------------------------

def encode_tcf_v04(rows: list[dict], level: int = 2,
                   with_llm_hints: bool = False) -> str:
    """Envelope v0.4 — cabecalho minimal '# TCF v0.4 lv=N'.

    LLM hints opcionais via bloco @llm-hint.
    Encoding utf-8 implicito (omite enc=).
    Line-ending LF (decoder detecta).
    """
    cfg = EncodeConfig(level=level, include_stats=True)
    body_v02 = encode_rows("supplier", rows, config=cfg)

    if body_v02.startswith("# TCF"):
        body_v02 = body_v02.split("\n", 1)[1]
    if body_v02.startswith("# N*val"):
        body_v02 = body_v02.split("\n", 1)[1]

    header = f"# TCF v0.4 lv={level}\n"
    hints = ""
    if with_llm_hints:
        if level >= 2:
            hints = ("# @llm-hint: dados em formato columnar; cada coluna lista valores\n"
                     "# @llm-hint: N*val = val repetido N vezes (RLE)\n")
        else:
            hints = "# @llm-hint: dados em formato columnar; cada coluna lista valores\n"

    return header + hints + body_v02


def encode_tcf_v04_smart(rows: list[dict], level: int = 3,
                         with_llm_hints: bool = False) -> tuple[str, int]:
    """Auto-bypass: se nivel pedido nao reduz vs nivel anterior, cai.

    Retorna (text, level_efetivo).
    """
    text_target = encode_tcf_v04(rows, level=level,
                                  with_llm_hints=with_llm_hints)
    if level == 0:
        return text_target, 0
    text_prev = encode_tcf_v04(rows, level=level - 1,
                                with_llm_hints=with_llm_hints)
    if len(text_target.encode("utf-8")) >= len(text_prev.encode("utf-8")):
        return text_prev, level - 1
    return text_target, level


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 72)
    print("flow-categoricos — cenario MAX para TCF (RLE/DICT deveriam brilhar)")
    print("=" * 72)

    # Dados: TPC-H supplier (100 rows)
    print("\n[1] Carregando TPC-H supplier (volume=100)...")
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=100, seed=42, schema=["supplier"])
    supplier = tables.get("supplier", [])
    print(f"    {len(supplier)} rows. Sample s_nationkey:")
    nk_sample = [s["s_nationkey"] for s in supplier[:10]]
    print(f"    {nk_sample}")

    # Diversity check
    nk_all = [s["s_nationkey"] for s in supplier]
    distinct = sorted(set(nk_all))
    print(f"    Distinct nationkeys: {len(distinct)} -> {distinct}")
    print(f"    Cardinality ratio: {len(distinct)}/{len(nk_all)} "
          f"= {len(distinct)/len(nk_all):.0%}")

    # ---- CENARIO A: 100 x s_nationkey (random/natural order) ----
    print("\n" + "=" * 72)
    print("[A] 100 rows x s_nationkey (NATURAL order — como vem do dataset)")
    print("=" * 72)
    rows_A = [{"s_nationkey": s["s_nationkey"]} for s in supplier]
    run_scenario("A-natural", rows_A)

    # ---- CENARIO B: 100 x s_nationkey (SORTED) ----
    print("\n" + "=" * 72)
    print("[B] 100 rows x s_nationkey (SORTED ASC — best case for RLE)")
    print("=" * 72)
    rows_B = sorted(rows_A, key=lambda r: r["s_nationkey"])
    run_scenario("B-sorted", rows_B)

    # ---- CENARIO C: mix categorico + unico (s_nationkey + s_name) ----
    print("\n" + "=" * 72)
    print("[C] 100 rows x (s_nationkey, s_name) — mix categorico + unico")
    print("=" * 72)
    rows_C = [{"s_nationkey": s["s_nationkey"], "s_name": s["s_name"]}
              for s in supplier]
    run_scenario("C-mix-natural", rows_C)

    # C sorted
    print("\n  -- C sorted by s_nationkey --")
    rows_C_sorted = sorted(rows_C, key=lambda r: r["s_nationkey"])
    run_scenario("C-mix-sorted", rows_C_sorted)

    # ---- Resumo das hipoteses ----
    print("\n" + "=" * 72)
    print("[RESUMO] Hipoteses do notes.md")
    print("=" * 72)
    print("  H1) TCF L2 sorted vence CSV em bytes:")
    print("      -> ver tabela bytes do cenario B")
    print("  H2) TCF L3 (DICT) auto-bypass NAO bypassa em categoricos:")
    print("      -> ver level efetivo do SMART em A/B")
    print("  H3) Cabecalho minimal v0.4 continua adequado:")
    print("      -> overhead deve ser pequeno em todos cenarios")

    print(f"\n[OK] Arquivos em: {OUT}")


def run_scenario(label: str, rows: list[dict]) -> None:
    """Encoda em todos formatos + auto-bypass + tabela comparativa."""
    if not rows:
        return

    n = len(rows)
    cols = list(rows[0].keys())
    print(f"\n  {n} rows x {len(cols)} cols: {cols}")

    # Encode
    csv_t = tee_write_bytes(OUT / f"{label}-01-csv.csv", encode_csv(rows))
    json_t = tee_write_bytes(OUT / f"{label}-02-json.json",
                              encode_json_compact(rows))

    tcf_l0 = tee_write_bytes(OUT / f"{label}-03-tcf-v02-L0.tcf",
                              encode_tcf(rows, 0))
    tcf_l2 = tee_write_bytes(OUT / f"{label}-04-tcf-v02-L2.tcf",
                              encode_tcf(rows, 2))
    tcf_l3 = tee_write_bytes(OUT / f"{label}-05-tcf-v02-L3.tcf",
                              encode_tcf(rows, 3))

    # v0.4 envelope (cabecalho minimal)
    tcf_v04_l2 = tee_write_bytes(OUT / f"{label}-06-tcf-v04-L2.tcf",
                                  encode_tcf_v04(rows, 2))
    tcf_v04_l3, lvl_smart = encode_tcf_v04_smart(rows, level=3)
    tee_write_bytes(OUT / f"{label}-07-tcf-v04-L3-smart.tcf", tcf_v04_l3)

    # Tabela
    csv_b = len(csv_t.encode("utf-8"))
    print(f"  {'formato':<26} {'bytes':>7}  {'vs CSV':>9}")
    print(f"  {'-'*26} {'-'*7}  {'-'*9}")
    for fmt, text in [
        ("csv (LF)",          csv_t),
        ("json (compact)",    json_t),
        ("tcf v0.2 L0",       tcf_l0),
        ("tcf v0.2 L2",       tcf_l2),
        ("tcf v0.2 L3",       tcf_l3),
        ("tcf v0.4 L2",       tcf_v04_l2),
        (f"tcf v0.4 L{lvl_smart} (smart)", tcf_v04_l3),
    ]:
        nb = len(text.encode("utf-8"))
        delta = (nb / csv_b - 1) * 100 if csv_b else 0
        sign = "+" if delta > 0 else ""
        marker = ""
        if "tcf" in fmt and nb < csv_b:
            marker = "  WIN"
        print(f"  {fmt:<26} {nb:>7}  {sign}{delta:>6.1f}%{marker}")

    # Roundtrip TCF v0.2 L2
    try:
        result = decode(tcf_l2)
        if isinstance(result, dict):
            decoded_rows = result.get("supplier") or list(result.values())[0]
        else:
            decoded_rows = result
        # Compara so as colunas alvo (cast para str — TCF perde tipos)
        ok_count = 0
        for src, dst in zip(rows, decoded_rows):
            if all(str(src.get(k)) == str(dst.get(k)) for k in cols):
                ok_count += 1
        print(f"  Roundtrip TCF v0.2 L2: {ok_count}/{len(rows)} match")
    except Exception as e:
        print(f"  Roundtrip TCF v0.2 L2: ERRO {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

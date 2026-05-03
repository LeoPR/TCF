"""Workbench sujo — flow basico encode/decode com nomes de pessoas.

Pega TPC-H supplier (so coluna s_name como `name`), gera 4 formatos
em arquivos para inspecao visual, decode + roundtrip, compara com input.

NAO e experimento formal — e sujo. Resultados em ./output/.
"""
from __future__ import annotations
import csv
import io
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from tcf import encode_rows, decode, EncodeConfig
from data_sources import load_dataset


HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)


def tee_write(path: Path, text: str) -> str:
    """Pipe duplo: escreve em arquivo E retorna a string para proximo passo."""
    path.write_text(text, encoding="utf-8")
    return text


def encode_csv(rows: list[dict]) -> str:
    """Encode CSV simples."""
    buf = io.StringIO()
    if not rows:
        return ""
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def decode_csv(text: str) -> list[dict]:
    """Decode CSV simples — sem inferencia de tipos (so name = str)."""
    return list(csv.DictReader(io.StringIO(text)))


def encode_json(rows: list[dict]) -> str:
    """JSON compacto."""
    return json.dumps(rows, separators=(",", ":"))


def decode_json(text: str) -> list[dict]:
    return json.loads(text)


def encode_tcf(rows: list[dict], level: int) -> str:
    cfg = EncodeConfig(level=level, include_stats=True)
    return encode_rows("supplier", rows, config=cfg)


def decode_tcf(text: str) -> list[dict]:
    """Decode TCF — extrai a tabela 'supplier' do dict de retorno."""
    result = decode(text)
    if isinstance(result, dict):
        if "supplier" in result:
            return result["supplier"]
        return list(result.values())[0]
    return result


def main() -> None:
    print("=== Workbench: flow encode/decode com nomes de pessoas ===\n")

    # 1. Carregar dados via Shaper
    print("[1] Carregando TPC-H supplier (volume=20)...")
    tables, meta = load_dataset("canonical:tpch-sf001",
                                 volume=20, seed=42,
                                 schema=["supplier"])
    supplier = tables.get("supplier", [])
    print(f"    {len(supplier)} linhas. Colunas: {list(supplier[0].keys())[:6]}")

    # 2. Extrair APENAS s_name como `name`
    rows_in = [{"name": s["s_name"]} for s in supplier[:10]]
    print(f"\n[2] Extraido s_name -> 'name'. Sample:")
    for r in rows_in[:3]:
        print(f"    {r}")

    # 3. Encode em 5 formatos com TEE (escreve arquivo + retorna string)
    print(f"\n[3] Encode em 5 formatos (escrevendo arquivos)...\n")

    # CSV
    csv_text = tee_write(OUT / "01-csv.csv", encode_csv(rows_in))
    print(f"    csv:        {OUT / '01-csv.csv'} ({len(csv_text)}B)")

    # JSON
    json_text = tee_write(OUT / "02-json.json", encode_json(rows_in))
    print(f"    json:       {OUT / '02-json.json'} ({len(json_text)}B)")

    # TCF L0/L2/L3
    tcf_l0 = tee_write(OUT / "03-tcf-L0.tcf", encode_tcf(rows_in, level=0))
    print(f"    tcf-L0:     {OUT / '03-tcf-L0.tcf'} ({len(tcf_l0)}B)")
    tcf_l2 = tee_write(OUT / "04-tcf-L2.tcf", encode_tcf(rows_in, level=2))
    print(f"    tcf-L2:     {OUT / '04-tcf-L2.tcf'} ({len(tcf_l2)}B)")
    tcf_l3 = tee_write(OUT / "05-tcf-L3.tcf", encode_tcf(rows_in, level=3))
    print(f"    tcf-L3:     {OUT / '05-tcf-L3.tcf'} ({len(tcf_l3)}B)  (schema-only)")

    # 4. Decode + re-emit como CSV (para comparacao visual)
    print(f"\n[4] Decode + re-emit como CSV em arquivos de saida...\n")

    rows_csv_back = decode_csv(csv_text)
    tee_write(OUT / "01-csv-decoded.csv", encode_csv(rows_csv_back))
    print(f"    csv decode -> {len(rows_csv_back)} rows")

    rows_json_back = decode_json(json_text)
    tee_write(OUT / "02-json-decoded.csv", encode_csv(rows_json_back))
    print(f"    json decode -> {len(rows_json_back)} rows")

    rows_tcf_l0_back = decode_tcf(tcf_l0)
    tee_write(OUT / "03-tcf-L0-decoded.csv", encode_csv(rows_tcf_l0_back))
    print(f"    tcf-L0 decode -> {len(rows_tcf_l0_back)} rows")

    rows_tcf_l2_back = decode_tcf(tcf_l2)
    tee_write(OUT / "04-tcf-L2-decoded.csv", encode_csv(rows_tcf_l2_back))
    print(f"    tcf-L2 decode -> {len(rows_tcf_l2_back)} rows")

    # L3: schema-only — nao espero rows; apenas marco
    try:
        rows_tcf_l3_back = decode_tcf(tcf_l3)
        print(f"    tcf-L3 decode -> {len(rows_tcf_l3_back)} rows (esperado 0 — schema only)")
    except Exception as e:
        print(f"    tcf-L3 decode -> ERRO esperado (schema only): {type(e).__name__}")

    # 5. Comparacao input vs output
    print(f"\n[5] Comparacao input vs decoded (so 'name')...\n")

    def names(rows: list[dict]) -> list[str]:
        return [str(r.get("name", "")) for r in rows]

    inp = names(rows_in)
    print(f"    Input: {len(inp)} nomes")

    for label, decoded in [
        ("csv", rows_csv_back),
        ("json", rows_json_back),
        ("tcf-L0", rows_tcf_l0_back),
        ("tcf-L2", rows_tcf_l2_back),
    ]:
        out = names(decoded)
        if inp == out:
            print(f"    {label}: roundtrip EXATO ({len(out)} nomes)")
        else:
            n_match = sum(1 for a, b in zip(inp, out) if a == b)
            print(f"    {label}: roundtrip DIVERGE — {n_match}/{len(inp)} match")
            # Mostra diferencas
            for i, (a, b) in enumerate(zip(inp, out)):
                if a != b:
                    print(f"      row {i}: input={a!r} -> decoded={b!r}")
                    if i > 2:
                        print(f"      (truncado)")
                        break

    # 6. Tabela bytes
    print(f"\n[6] Tabela de bytes (comparativo de formatos):\n")
    print(f"    {'formato':<12} {'bytes':>8}  {'vs CSV':>8}")
    print(f"    {'-'*12} {'-'*8} {'-'*8}")
    csv_b = len(csv_text)
    for label, text in [
        ("csv", csv_text),
        ("json", json_text),
        ("tcf-L0", tcf_l0),
        ("tcf-L2", tcf_l2),
        ("tcf-L3", tcf_l3),
    ]:
        n = len(text)
        delta = (n / csv_b - 1) * 100 if csv_b else 0
        sign = "+" if delta > 0 else ""
        print(f"    {label:<12} {n:>8}  {sign}{delta:>6.1f}%")

    print(f"\n[OK] Arquivos gerados em: {OUT}")
    print(f"     Inspeciona-os manualmente para ver os formatos.")


if __name__ == "__main__":
    main()

"""Workbench sujo CICLO 2 — analise critica do flow inicial.

Preservar run.py original (ciclo 1). Este script:
- Diagnostica bug do CSV (line endings duplicados em Windows)
- Compara variantes JSON (compact / pretty / jsonl)
- Simula TCF L3 com auto-bypass (fallback automatico para L2)
- Propoe cabecalho v0.4 com encoding + line-ending explicitos
- Inspeciona bytes literais (hex dump) dos arquivos

Saida: ./output-v2/ (preserva ./output/ do ciclo 1)
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
OUT = HERE / "output-v2"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_bytes(path: Path, data: bytes) -> bytes:
    """Escreve bytes literais (sem traducao de line endings)."""
    path.write_bytes(data)
    return data


def show_bytes(label: str, data: bytes, max_chars: int = 250) -> None:
    """Visualiza bytes com line endings explicitos."""
    visible = data[:max_chars].replace(b'\r\n', b'<CRLF>\n').replace(b'\n', b'<LF>\n').replace(b'\r', b'<CR>')
    crlf = data.count(b'\r\n')
    lf_only = data.count(b'\n') - crlf
    cr_only = data.count(b'\r') - crlf
    print(f"  --- {label} ({len(data)}B, CRLF={crlf} LF={lf_only} CR={cr_only}) ---")
    print(visible.decode('utf-8', errors='replace'))


# ---------------------------------------------------------------------------
# CSV variantes — controlando line ending
# ---------------------------------------------------------------------------

def encode_csv(rows: list[dict], lineterm: str = "\n") -> str:
    """CSV com lineterminator EXPLICITO (default \\n para evitar duplicacao)."""
    if not rows:
        return ""
    buf = io.StringIO(newline="")  # newline="" evita traducao automatica
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                       lineterminator=lineterm)
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# JSON variantes
# ---------------------------------------------------------------------------

def encode_json_compact(rows: list[dict]) -> str:
    """JSON sem espacos — ideal para tamanho minimo / transmissao."""
    return json.dumps(rows, separators=(",", ":"))


def encode_json_pretty(rows: list[dict]) -> str:
    """JSON indentado — ideal para inspecao humana."""
    return json.dumps(rows, indent=2)


def encode_jsonl(rows: list[dict]) -> str:
    """JSON Lines — 1 record por linha. Stream-friendly, append-friendly."""
    return "\n".join(json.dumps(r, separators=(",", ":")) for r in rows)


# ---------------------------------------------------------------------------
# TCF L3 com AUTO-BYPASS simulado
# ---------------------------------------------------------------------------

def encode_tcf_smart(rows: list[dict], requested_level: int) -> tuple[str, int, str]:
    """Encoder TCF "inteligente": pede level X, mas faz bypass se nao compensa.

    Returns (text, effective_level, reason).

    Logica:
    - Tenta encode no level pedido
    - Tenta encode em level inferior (L2 ou L0)
    - Se level inferior tem >= bytes, mantem o pedido
    - Se level inferior tem < bytes, usa o inferior + marca como "auto-bypass"

    NOTA: este e um SIMULADOR no workbench. v0.4 deveria ter essa logica
    no encoder TCF de fato.
    """
    candidates = []
    for lvl in (requested_level, max(0, requested_level - 1), 0):
        if lvl == requested_level or lvl < requested_level:
            cfg = EncodeConfig(level=lvl, include_stats=True)
            text = encode_rows("data", rows, config=cfg)
            candidates.append((lvl, text))

    # Encontrar menor bytes
    candidates.sort(key=lambda x: len(x[1]))
    best_lvl, best_text = candidates[0]

    if best_lvl == requested_level:
        return best_text, requested_level, f"requested={requested_level} kept"
    else:
        return best_text, best_lvl, (
            f"requested={requested_level} but auto-bypassed to L{best_lvl} "
            f"(would save {len(candidates[-1][1]) - len(best_text)}B)"
        )


# ---------------------------------------------------------------------------
# Proposta de cabecalho TCF v0.4 (so wrapper externo, nao muda encoder)
# ---------------------------------------------------------------------------

def wrap_tcf_v04_header(text: str, level: int, encoding: str = "utf-8",
                         line_ending: str = "LF") -> str:
    """Adiciona cabecalho v0.4 PROPOSTO antes do TCF v0.2 atual.

    Cabecalho expandido inclui encoding e line-ending para deixar
    explicito como o consumidor deve interpretar.
    """
    le_marker = {"LF": "\\n", "CRLF": "\\r\\n", "CR": "\\r"}[line_ending]
    header_v04 = (
        f"# TCF v0.4 level={level} encoding={encoding} line-ending={line_ending}\n"
        f"# (legacy v0.2 body follows)\n"
    )
    # Remove o cabecalho v0.2 do `text` (primeira linha) para nao duplicar
    body_lines = text.split("\n", 1)[1] if text.startswith("#") else text
    return header_v04 + body_lines


def main() -> None:
    print("=" * 70)
    print("Workbench CICLO 2 — analise critica + variantes + L3 auto-bypass")
    print("=" * 70)

    # 1. Carregar dados
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=20, seed=42, schema=["supplier"])
    rows_in = [{"name": s["s_name"]} for s in tables["supplier"][:10]]
    print(f"\n[1] {len(rows_in)} linhas (TPC-H supplier, so 'name')")

    # ---- 2. CSV bug investigation ----
    print("\n" + "=" * 70)
    print("[2] CSV — diagnostico de line endings")
    print("=" * 70)

    print("\n--- 2a. CSV CICLO 1 (comportamento bugado: CRLF + LF Windows) ---")
    # Reproduz o bug: usar StringIO sem newline='' + write_text (default)
    buf = io.StringIO()  # SEM newline=''
    w = csv.DictWriter(buf, fieldnames=["name"])
    w.writeheader()
    w.writerows(rows_in)
    bug_text = buf.getvalue()
    bug_path = OUT / "01a-csv-bug-CRLF+LF.csv"
    bug_path.write_text(bug_text, encoding="utf-8")  # WRITE_TEXT bug
    show_bytes("01a-csv-bug-CRLF+LF.csv (write_text)", bug_path.read_bytes(), 80)

    print("\n--- 2b. CSV LF puro (Linux-style, lineterminator='\\n') ---")
    csv_lf = encode_csv(rows_in, lineterm="\n").encode("utf-8")
    write_bytes(OUT / "01b-csv-LF.csv", csv_lf)
    show_bytes("01b-csv-LF.csv", csv_lf, 80)

    print("\n--- 2c. CSV CRLF puro (Windows-style, lineterminator='\\r\\n') ---")
    csv_crlf = encode_csv(rows_in, lineterm="\r\n").encode("utf-8")
    write_bytes(OUT / "01c-csv-CRLF.csv", csv_crlf)
    show_bytes("01c-csv-CRLF.csv", csv_crlf, 80)

    print(f"\n  Bytes: bug={len(bug_text.encode('utf-8'))} "
          f"LF={len(csv_lf)} CRLF={len(csv_crlf)}")
    print(f"  Diff bug vs LF: +{len(bug_text.encode('utf-8'))-len(csv_lf)}B "
          f"(cada linha tem 2 bytes extras)")

    # ---- 3. JSON variantes ----
    print("\n" + "=" * 70)
    print("[3] JSON — comparativo entre variantes")
    print("=" * 70)
    json_compact = encode_json_compact(rows_in).encode("utf-8")
    json_pretty = encode_json_pretty(rows_in).encode("utf-8")
    json_lines = encode_jsonl(rows_in).encode("utf-8")
    write_bytes(OUT / "02a-json-compact.json", json_compact)
    write_bytes(OUT / "02b-json-pretty.json", json_pretty)
    write_bytes(OUT / "02c-jsonl.jsonl", json_lines)

    print(f"  JSON compact: {len(json_compact)}B  (sem espacos)")
    print(f"  JSON pretty:  {len(json_pretty)}B  (+{len(json_pretty)-len(json_compact)}B vs compact)")
    print(f"  JSONL:        {len(json_lines)}B  (1 obj por linha — stream-friendly)")

    # ---- 4. TCF L0/L2/L3 standard ----
    print("\n" + "=" * 70)
    print("[4] TCF v0.2 — encode no nivel pedido (sem bypass)")
    print("=" * 70)
    for lvl in (0, 2, 3):
        text = encode_rows("data", rows_in,
                            config=EncodeConfig(level=lvl, include_stats=True))
        b = text.encode("utf-8")
        write_bytes(OUT / f"03-tcf-L{lvl}.tcf", b)
        print(f"  TCF L{lvl}: {len(b)}B")

    # ---- 5. TCF L3 com auto-bypass (NOVO) ----
    print("\n" + "=" * 70)
    print("[5] TCF L3 SMART — auto-bypass (proposta v0.4)")
    print("=" * 70)
    text, eff_lvl, reason = encode_tcf_smart(rows_in, requested_level=3)
    b = text.encode("utf-8")
    write_bytes(OUT / "04-tcf-L3-smart.tcf", b)
    print(f"  Pedido: L3   Effective: L{eff_lvl}   Bytes: {len(b)}B")
    print(f"  Razao:  {reason}")
    print(f"  Compare com forced L3: {(OUT / '03-tcf-L3.tcf').stat().st_size}B")

    # ---- 6. Proposta cabecalho v0.4 com encoding/line-ending ----
    print("\n" + "=" * 70)
    print("[6] Proposta v0.4: cabecalho explicito (encoding + line-ending)")
    print("=" * 70)
    base_l2 = encode_rows("data", rows_in,
                           config=EncodeConfig(level=2, include_stats=True))
    wrapped = wrap_tcf_v04_header(base_l2, level=2,
                                    encoding="utf-8", line_ending="LF")
    write_bytes(OUT / "05-tcf-v04-proposed.tcf", wrapped.encode("utf-8"))
    print(f"  v0.2 atual: {len(base_l2.encode('utf-8'))}B")
    print(f"  v0.4 proposta (com header): {len(wrapped.encode('utf-8'))}B")
    print(f"  Overhead: +{len(wrapped) - len(base_l2)}B (so 2 linhas de header)")
    print()
    print("  Cabecalho v0.4 proposto:")
    for line in wrapped.splitlines()[:4]:
        print(f"    {line}")

    # ---- 7. Tabela final consolidada ----
    print("\n" + "=" * 70)
    print("[7] Tabela final (bytes — CICLO 2)")
    print("=" * 70)
    print(f"  {'arquivo':<32} {'bytes':>7}  obs")
    print(f"  {'-' * 32} {'-' * 7}  {'-' * 30}")
    rows_tab = [
        ("CSV (bug CRLF+LF)", len(bug_text.encode("utf-8")), "*** BUGADO ***"),
        ("CSV LF puro", len(csv_lf), "ideal Linux/macOS"),
        ("CSV CRLF puro", len(csv_crlf), "ideal Windows/RFC 4180"),
        ("JSON compact", len(json_compact), ""),
        ("JSON pretty", len(json_pretty), "+overhead p/ leitura humana"),
        ("JSONL", len(json_lines), "stream-friendly"),
        ("TCF L0", (OUT / "03-tcf-L0.tcf").stat().st_size, "raw columnar"),
        ("TCF L2", (OUT / "03-tcf-L2.tcf").stat().st_size, "RLE+STATS (sem ganho aqui)"),
        ("TCF L3 forced", (OUT / "03-tcf-L3.tcf").stat().st_size, "DICT + indices"),
        ("TCF L3 SMART", (OUT / "04-tcf-L3-smart.tcf").stat().st_size,
         f"auto-bypass: {reason}"),
        ("TCF v0.4 proposed", len(wrapped.encode("utf-8")),
         "+header com encoding/line-ending"),
    ]
    for label, n, obs in rows_tab:
        print(f"  {label:<32} {n:>7}B  {obs}")

    print(f"\n[OK] Arquivos gerados em: {OUT}")


if __name__ == "__main__":
    main()

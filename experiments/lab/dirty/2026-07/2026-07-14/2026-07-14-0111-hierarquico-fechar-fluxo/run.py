"""Fecha a FUNCIONALIDADE + o FLUXO encode/decode do hierárquico, com os clássicos
de transmissão (cadastro, pedido, telemetria) — todos JSON.

Dois fluxos por entrada (o owner: performance dá pra SIMULAR sem API real):
  A) FUNCIONAL:  JSON -> encode_h -> TCF.H -> decode_h -> JSON   (RT-exato)
  B) TRANSMISSÃO (simulada): JSON -> encode_h -> gzip/brotli -> gunzip/unbrotli
                 -> decode_h -> JSON   (RT-exato) + bytes por estágio.

Estrutura (convenção): inputs/ intermediates/ outputs/. Rodar: python run.py
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

from shred import decode_h, encode_h

try:
    import brotli
    HAVE_BROTLI = True
except ImportError:
    HAVE_BROTLI = False

HERE = Path(__file__).resolve().parent
INP, INTER, OUT = HERE / "inputs", HERE / "intermediates", HERE / "outputs"
for d in (INTER, OUT):
    d.mkdir(exist_ok=True)


def w(p: Path, t: str):
    p.write_bytes(t.encode("utf-8"))  # LF-only


def process(src: Path, log: list, sizes: list):
    records = json.loads(src.read_text(encoding="utf-8"))
    stem = src.stem
    canon = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    w(INTER / f"{stem}.canonico.json", canon)

    # ---- FLUXO A: funcional (encode/decode) ----
    blob = encode_h(records)
    w(OUT / f"{stem}.tcf", blob)
    back = decode_h(blob)
    rt = json.dumps(back, ensure_ascii=False, indent=2) + "\n"
    w(OUT / f"{stem}.roundtrip.json", rt)
    ok_A = back == records and rt == canon

    # ---- FLUXO B: transmissão simulada (encode/compress/decompress/decode) ----
    tcf_bytes = blob.encode("utf-8")
    json_bytes = json.dumps(records, ensure_ascii=False).encode("utf-8")
    gz = gzip.compress(tcf_bytes, 9)
    ok_B_gz = decode_h(gzip.decompress(gz).decode("utf-8")) == records
    if HAVE_BROTLI:
        br = brotli.compress(tcf_bytes, quality=11)
        ok_B_br = decode_h(brotli.decompress(br).decode("utf-8")) == records
        json_br = len(brotli.compress(json_bytes, quality=11))
    else:
        br, ok_B_br, json_br = b"", True, None

    assert ok_A and ok_B_gz and ok_B_br, f"RT falhou em {stem}"

    log.append(f"== {stem} ==")
    log.append(f"  header: {blob.splitlines()[0]}")
    log.append(f"  FLUXO A funcional  (JSON->encode->decode->JSON): RT={ok_A}  "
               f"(roundtrip.json == canonico: {rt == canon})")
    log.append(f"  FLUXO B transmissão (encode->gzip->gunzip->decode): RT gzip={ok_B_gz}"
               + (f", brotli={ok_B_br}" if HAVE_BROTLI else " (brotli ausente)"))
    log.append("")
    row = [stem, len(json_bytes), len(tcf_bytes), len(gz)]
    row += [len(br) if HAVE_BROTLI else "-", json_br if HAVE_BROTLI else "-"]
    sizes.append(row)
    return blob


def main() -> None:
    log = ["FECHAR FLUXO — hierárquico por shredding (blocos + counts), clássicos de transmissão", ""]
    sizes = []
    for src in sorted(INP.glob("*.json")):
        process(src, log, sizes)

    # tabela de bytes (simula transmissão; performance real = .9)
    tbl = ["entrada | JSON | TCF.H | TCF+gzip | TCF+brotli | JSON+brotli",
           "---|---:|---:|---:|---:|---:"]
    for r in sizes:
        tbl.append(" | ".join(str(x) for x in r))
    w(OUT / "10-bytes-transmissao.txt", "\n".join(tbl) + "\n")
    w(OUT / "11-contraprova.txt", "\n".join(log) + "\n")

    print("\n".join(log))
    print("--- bytes (transmissão simulada) ---")
    print("\n".join(tbl))
    print("\n--- amostra: 01-cadastro-clientes.tcf ---")
    print((OUT / "01-cadastro-clientes.tcf").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

"""Verificacao adicional: compressao standalone vs streaming (gzip).

Pergunta do user: o comportamento de gzip em CANAIS STREAM eh similar
a compressao standalone? Se nao, em qual magnitude?

Testes:
  M1 — standalone:           gzip.compress(data) — referencia
  M2 — stream sem flush:     GzipFile escreve chunks, fecha no final
  M3 — stream com flush/chunk: GzipFile escreve, flush() a cada N KB
                              (simula HTTP transfer-encoding ou WS msg)

Datasets: os 5 do EXP-003a (CSV).

NAO substitui teste real com servidor HTTP/1/2/3 — eh referencia
em-processo apenas.
"""
from __future__ import annotations
import csv
import io
import gzip
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Reuso dos datasets do run.py (mesma seed)
# ---------------------------------------------------------------------------

def encode_csv(rows):
    if not rows:
        return ""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()),
                        lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def get_datasets():
    """Reusa os mesmos 5 datasets do EXP-003a."""
    from data_sources import load_dataset

    out = []

    # tpch
    tables, _ = load_dataset("canonical:tpch-sf001",
                              volume=100, seed=42, schema=["supplier"])
    out.append(("tpch-supplier-100", tables.get("supplier", [])))

    # adult
    tables, _ = load_dataset("canonical:adult-census",
                              volume=1000, seed=42, schema=["adult"])
    out.append(("adult-1k", tables.get("adult", [])))

    # categorical-heavy
    statuses = ["pago", "pendente", "cancelado", "ok"]
    categorias = ["A", "B", "C", "D"]
    cidades = ["SP", "RJ", "BH", "POA", "REC"]
    rows = []
    for i in range(500):
        rows.append({
            "id": i + 1,
            "status": random.choice(statuses),
            "categoria": random.choice(categorias),
            "cidade": random.choice(cidades),
            "valor": round(random.uniform(10, 999), 2),
            "qtd": random.randint(1, 10),
            "ativo": random.choice([True, False]),
        })
    out.append(("categorical-heavy", rows))

    # time-series
    from datetime import date, timedelta
    base = date(2026, 1, 1)
    rows = []
    for i in range(500):
        d = base + timedelta(days=i)
        rows.append({
            "data": d.isoformat(),
            "temperatura": round(20 + random.gauss(0, 5), 1),
            "umidade": round(60 + random.gauss(0, 10), 1),
            "pressao": round(1013 + random.gauss(0, 5), 2),
            "vento": round(random.uniform(0, 30), 1),
        })
    out.append(("time-series", rows))

    # mixed-relational
    nomes = [f"Cliente_{i:03d}" for i in range(50)]
    produtos = [f"Prod-{i:03d}" for i in range(20)]
    rows = []
    for i in range(800):
        rows.append({
            "pedido_id": i + 1,
            "cliente_id": random.randint(1, 50),
            "cliente_nome": random.choice(nomes),
            "produto_id": random.randint(1, 20),
            "produto_nome": random.choice(produtos),
            "qtd": random.randint(1, 5),
            "valor_unit": round(random.uniform(5, 500), 2),
            "status": random.choice(["pago", "pendente", "cancelado"]),
        })
    out.append(("mixed-relational", rows))

    return out


# ---------------------------------------------------------------------------
# 3 modos de compressao
# ---------------------------------------------------------------------------

def gzip_standalone(data: bytes, level: int = 9) -> bytes:
    """M1 — referencia. Tudo de uma vez."""
    return gzip.compress(data, compresslevel=level)


def gzip_stream_no_flush(data: bytes, chunk_size: int = 1024,
                          level: int = 9) -> bytes:
    """M2 — streaming sem flush forcado. Praticamente identico a M1."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=level) as gz:
        for i in range(0, len(data), chunk_size):
            gz.write(data[i:i + chunk_size])
    return buf.getvalue()


def gzip_stream_flush_per_chunk(data: bytes, chunk_size: int = 1024,
                                  level: int = 9) -> bytes:
    """M3 — streaming COM flush a cada chunk. Simula HTTP transfer-encoding
    ou WebSocket per-message-deflate sem context_takeover."""
    import zlib
    # gzip header manual (10 bytes)
    out = bytearray()
    out.extend(bytes([0x1f, 0x8b, 0x08, 0x00, 0, 0, 0, 0, 0, 0xff]))

    compressor = zlib.compressobj(
        level=level,
        method=zlib.DEFLATED,
        wbits=-zlib.MAX_WBITS,  # raw deflate
        memLevel=zlib.DEF_MEM_LEVEL,
        strategy=zlib.Z_DEFAULT_STRATEGY,
    )
    crc = 0
    total_in = 0
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i + chunk_size]
        out.extend(compressor.compress(chunk))
        # Forca flush sync: emite tudo que tem mas mantem janela
        out.extend(compressor.flush(zlib.Z_SYNC_FLUSH))
        crc = zlib.crc32(chunk, crc) & 0xffffffff
        total_in += len(chunk)
    out.extend(compressor.flush(zlib.Z_FINISH))
    # gzip footer: crc32 (4) + isize (4)
    out.extend(crc.to_bytes(4, "little"))
    out.extend((total_in & 0xffffffff).to_bytes(4, "little"))
    return bytes(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 86)
    print("Verificacao: gzip standalone vs streaming")
    print("=" * 86)
    print()
    print("  M1 = standalone (gzip.compress)")
    print("  M2 = stream sem flush forcado (GzipFile com writes)")
    print("  M3 = stream com flush por chunk (Z_SYNC_FLUSH a cada 1KB)")
    print()

    chunk_size = 1024  # 1KB por chunk de stream

    print(f"  {'dataset':<24} {'csv':>7} {'M1 std':>10} {'M2 stream':>11} {'M3 flush':>11}")
    print(f"  {'-'*24} {'-'*7} {'-'*10} {'-'*11} {'-'*11}")

    results = []
    for name, rows in get_datasets():
        if not rows:
            continue
        csv_bytes = encode_csv(rows).encode("utf-8")
        b_csv = len(csv_bytes)

        b_m1 = len(gzip_standalone(csv_bytes))
        b_m2 = len(gzip_stream_no_flush(csv_bytes, chunk_size))
        b_m3 = len(gzip_stream_flush_per_chunk(csv_bytes, chunk_size))

        # diferenca relativa
        d_m2 = (b_m2 / b_m1 - 1) * 100
        d_m3 = (b_m3 / b_m1 - 1) * 100

        print(f"  {name:<24} {b_csv:>7} {b_m1:>10} "
              f"{b_m2:>5} ({d_m2:+.1f}%) "
              f"{b_m3:>5} ({d_m3:+.1f}%)")

        results.append({
            "dataset": name,
            "bytes_csv": b_csv,
            "M1_standalone": b_m1,
            "M2_stream_no_flush": b_m2,
            "M3_stream_flush_per_1KB": b_m3,
            "M2_diff_pct": d_m2,
            "M3_diff_pct": d_m3,
        })

    # ---- Sintese ----
    print("\n" + "=" * 86)
    print("Sintese")
    print("=" * 86)

    m2_diffs = [r["M2_diff_pct"] for r in results]
    m3_diffs = [r["M3_diff_pct"] for r in results]

    print(f"\n  M2 vs M1 (stream sem flush): "
          f"min={min(m2_diffs):+.2f}%  avg={sum(m2_diffs)/len(m2_diffs):+.2f}%  "
          f"max={max(m2_diffs):+.2f}%")
    print(f"  M3 vs M1 (stream flush/1KB):  "
          f"min={min(m3_diffs):+.2f}%  avg={sum(m3_diffs)/len(m3_diffs):+.2f}%  "
          f"max={max(m3_diffs):+.2f}%")

    print(f"""
  Interpretacao:

  - M2 (stream sem flush) ≈ M1 (standalone). Diferenca <1% esperada.
    Em HTTP/1.1+ com transfer-encoding gzip de payload completo,
    comportamento eh proximo a M2.

  - M3 (flush por chunk) PIOR que M1, magnitude depende do chunk_size.
    Cada flush sincroniza dicionario e emite bloco — perde entropy.
    Em WebSocket com per-message-deflate sem context_takeover,
    comportamento eh proximo a M3 com chunk = mensagem.

  - Quanto MAIOR o chunk_size em M3, mais proximo de M1.
""")

    # ---- O que NAO conseguimos testar aqui ----
    print("=" * 86)
    print("O que esta verificacao NAO cobre")
    print("=" * 86)
    print("""
  1. HTTP/1.x real com Content-Encoding: gzip (servidor + cliente)
  2. HTTP/2 com hpack + gzip body (header compression eh outra historia)
  3. HTTP/3 + QUIC + brotli streaming
  4. WebSocket per-message-deflate
  5. gRPC com gzip codec
  6. Latencia (bytes nao eh tudo — flush antes vence se tempo importa)

  Para teste rigoroso futuro: levantar servidor real com Apache/Nginx
  ou Caddy e medir bytes via curl --compressed (HTTP/1.1, /2, /3).

  Por agora, M2 (stream sem flush) eh referencia razoavel para o
  cenario HTTP comum.
""")

    # ---- Salva ----
    out = {
        "experiment": "EXP-003a-calibration",
        "verification": "stream_vs_standalone",
        "chunk_size": chunk_size,
        "results": results,
        "pending_real_tests": [
            "HTTP/1.x Apache/Nginx com Content-Encoding: gzip",
            "HTTP/2 + gzip body",
            "HTTP/3 + QUIC + brotli",
            "WebSocket per-message-deflate",
            "gRPC gzip codec",
        ],
    }
    (RESULTS / "stream-verification.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print(f"  Resultados: {RESULTS / 'stream-verification.json'}")


if __name__ == "__main__":
    main()

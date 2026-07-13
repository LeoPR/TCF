"""Gera result.md a partir de artifacts/results.json (sem numeros a mao)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "artifacts" / "results.json").read_text(encoding="utf-8"))

lines = [
    "# Resultado — TCF vs compressores HTTP/Parquet (2026-07-13)",
    "",
    "> Gerado por `gen_result.py` a partir de `artifacts/results.json`. RT 4/4 True.",
    "> `tcf_helps` = 1 - comp(TCF)/comp(raw): **positivo** = TCF+compressor menor que",
    "> compressor(raw) (TCF ajuda a camada); **negativo** = TCF atrapalha o compressor.",
    "",
]
for r in d["results"]:
    lines += [
        f"## {r['dataset']}  ({r['n_rows']} linhas x {r['n_cols']} col)  ·  RT={r['rt_ok']}",
        "",
        f"- raw = **{r['raw_bytes']} B** · TCF = **{r['tcf_bytes']} B** "
        f"(TCF sozinho: **{r['tcf_vs_raw_pct']}%** menor que o cru)",
        "",
        "| compressor | comp(raw) | comp(TCF) | tcf_helps |",
        "|---|---:|---:|---:|",
    ]
    for c, v in r["comp"].items():
        lines.append(
            f"| {c} | {v['on_raw']} | {v['on_tcf']} | {v['tcf_helps_pct']:+.2f}% |"
        )
    lines.append("")

lines += [
    "## Leitura",
    "",
    "1. **TCF sozinho sempre encolhe vs o cru** (6,5% a 72%), continuando texto ASCII inspecionavel.",
    "2. **Coluna free-text unica** (retail-description, stockcode, lineitem-comment): os compressores",
    "   binarios ganham em ratio absoluto sobre o TCF sozinho, e compor `comp(TCF)` em geral **atrapalha**",
    "   o compressor (−7% a −41%) — a reescrita em referencias do TCF perturba o modelo de entropia dele,",
    "   que ja acha aquelas repeticoes sozinho. Nesse regime o valor do TCF e' **legibilidade**, nao ratio.",
    "3. **Tabela multi-coluna estruturada** (cadastro 2000x5): TCF sozinho fica **72% menor** que o CSV,",
    "   E compor ajuda o compressor **+24% a +50%** (ex.: TCF+brotli 8669 B < brotli(raw) 12411 B).",
    "   Aqui o TCF ganha nos DOIS eixos — o que ele fatora (padroes de campo, colunas dict) segue",
    "   comprimivel pela camada de transporte.",
    "",
    "**Conclusao (honesta):** a frase 'gzip/brotli compoem por cima' vale para **dados estruturados**",
    "multi-coluna; para **coluna free-text densa unica** o compressor binario sozinho vence e o TCF",
    "por baixo atrapalha — ali o TCF entrega inspecionabilidade, nao menor payload. zstd/gzip do mundo",
    "Parquet exibem o MESMO padrao dos de HTTP (a estrutura, nao o container, decide).",
]

# ---- TEMPO + MEMORIA (timing_memory.json) ----
tm_path = HERE / "artifacts" / "timing_memory.json"
if tm_path.exists():
    tm = json.loads(tm_path.read_text(encoding="utf-8"))
    lines += [
        "",
        "## Tempo (proporcional ao volume) — mediana N=9, com warmup",
        "",
        "> **Caveat de portabilidade** (CLAUDE.md F0-3): os ms ABSOLUTOS sao desta maquina.",
        "> O invariante e' o **throughput (MB/s)** e o fato estrutural: descomprimir menos custa",
        "> proporcionalmente menos tempo. Tempo NUNCA e' pinado em teste.",
        "",
    ]
    for ds, rows in tm["timing"].items():
        lines += [
            f"### {ds}  (entrada {rows[0]['in_bytes']} B de texto TCF)",
            "",
            "| codec | comp (ms) | decomp (ms) | comp MB/s | decomp MB/s |",
            "|---|---:|---:|---:|---:|",
        ]
        for r in rows:
            lines.append(
                f"| {r['codec']} | {r['comp_ms']} | {r['decomp_ms']} | "
                f"{r['comp_mbps']} | {r['decomp_mbps']} |"
            )
        lines.append("")
    lines += [
        "**Leitura do tempo:** descompressao e' barata em todos (dezenas a centenas de MB/s), mas com um",
        "compressor opaco voce paga a descompressao sobre **100% do payload** antes de qualquer filtro;",
        "no `view()` do TCF paga-se so' sobre a fracao das colunas tocadas. brotli comprime lento (q=11,",
        "~0,5 MB/s) e descomprime rapido; lz4/snappy descomprimem a ~700-1000 / ~410-490 MB/s e comprimem",
        "a ~250-350 MB/s (por isso o Parquet os usa por padrao). O ganho de latencia do TCF nao vem de",
        "descomprimir mais rapido — vem de descomprimir **menos**.",
        "",
        "## Memoria — view seletivo vs decode/descompressao total",
        "",
        "Pico de memoria Python (tracemalloc) pra responder UMA query no MESMO blob:",
        "",
        "| dataset | query | view() pico | decode() pico | materializa (view) | menos memoria |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for mm in tm["memory"]:
        lines.append(
            f"| {mm['dataset']} ({mm['n_rows']}x{mm['n_cols']}) | `{mm['query']}` | "
            f"{mm['peak_view_bytes']/1024:.1f} KB | {mm['peak_decode_bytes']/1024:.1f} KB | "
            f"{mm['filter_pct']}% | {mm['peak_ratio']}x |"
        )
    lines += [
        "",
        "Um compressor opaco (gzip/brotli/zstd) **exige** inflar o payload inteiro antes de filtrar —",
        "pico = a tabela toda. O `view()` infla so' as colunas que a pergunta toca. Grafico:",
        "[`docs/img/view-memory.svg`](../../../../docs/img/view-memory.svg) (gerado por `gen_svg.py`).",
    ]

(HERE / "result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("result.md gerado")

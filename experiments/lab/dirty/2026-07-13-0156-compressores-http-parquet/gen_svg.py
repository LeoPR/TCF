"""Gera docs/img/view-memory.svg a partir dos numeros MEDIDOS (timing_memory.json).

Barras EXATAMENTE proporcionais aos bytes de pico (tracemalloc) — nada a mao.
Auto-contido (sem refs externas), card opaco legivel em tema claro/escuro do
GitHub. Mostra o processo do view: mesma query, duas memorias de pico.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]  # .../TCF (HERE = lab dir; up 4 dirs: 2026.../dirty/lab/experiments/TCF)
d = json.loads((HERE / "artifacts" / "timing_memory.json").read_text(encoding="utf-8"))
m = next(x for x in d["memory"] if x["dataset"] == "online-retail-100x8")

COLS = ["InvoiceNo", "StockCode", "Description", "Quantity",
        "InvoiceDate", "UnitPrice", "CustomerID", "Country"]
touched = set(m["filter_touched"])  # Country, Quantity

peak_view = m["peak_view_bytes"]
peak_decode = m["peak_decode_bytes"]
ratio = m["peak_ratio"]
filt_pct = m["filter_pct"]

# --- geometria ---
W, H = 900, 470
BAR_X = 300
BAR_MAX = 360  # px para o maior pico (deixa espaco pro rotulo a direita)
scale = BAR_MAX / peak_decode
w_view = peak_view * scale
w_decode = peak_decode * scale

# paleta (card claro, alto contraste — imagem legivel em ambos os temas)
BG = "#ffffff"; CARD = "#f6f8fa"; INK = "#1f2328"; SUB = "#57606a"
GREEN = "#1a7f37"; GREENL = "#aceebb"; GREY = "#8c959f"; GREYL = "#d0d7de"
RED = "#cf222e"

def cell_strip(x, y, lit_set, lit_color, dim_color):
    cw, gap = 26, 3
    out = []
    for i, c in enumerate(COLS):
        cx = x + i * (cw + gap)
        fill = lit_color if c in lit_set else dim_color
        out.append(f'<rect x="{cx}" y="{y}" width="{cw}" height="14" rx="2" fill="{fill}"/>')
    return "\n".join(out)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Roboto,sans-serif">
<rect x="0" y="0" width="{W}" height="{H}" rx="14" fill="{BG}"/>
<rect x="12" y="12" width="{W-24}" height="{H-24}" rx="10" fill="{CARD}"/>
<text x="40" y="52" font-size="21" font-weight="700" fill="{INK}">One blob, one query — two memory footprints</text>
<text x="40" y="78" font-size="13" fill="{SUB}">online-retail · 100 rows × 8 cols · query: where(Country="United Kingdom").sum(Quantity)</text>

<!-- LEGEND: which columns each path materializes -->
<text x="40" y="116" font-size="13" fill="{SUB}">columns materialized (of 8):</text>
<text x="40" y="150" font-size="13" font-weight="600" fill="{GREEN}">view():</text>
{cell_strip(120, 138, touched, GREEN, GREYL)}
<text x="360" y="150" font-size="12" fill="{SUB}">2 of 8 — Country + Quantity</text>
<text x="40" y="176" font-size="13" font-weight="600" fill="{RED}">decode():</text>
{cell_strip(120, 164, set(COLS), GREY, GREY)}
<text x="360" y="176" font-size="12" fill="{SUB}">8 of 8 — the whole table</text>

<!-- BARS: peak process memory (tracemalloc), proportional -->
<text x="40" y="238" font-size="14" font-weight="600" fill="{INK}">peak memory to answer the query (tracemalloc, proportional):</text>

<text x="40" y="286" font-size="14" font-weight="600" fill="{INK}">TCF view()</text>
<rect x="{BAR_X}" y="272" width="{w_view:.1f}" height="26" rx="4" fill="{GREEN}"/>
<text x="{BAR_X + w_view + 10:.1f}" y="291" font-size="13" fill="{INK}">{peak_view/1024:.1f} KB  ·  materializes {filt_pct}%</text>

<text x="40" y="336" font-size="14" font-weight="600" fill="{INK}">TCF decode() then filter</text>
<rect x="{BAR_X}" y="322" width="{w_decode:.1f}" height="26" rx="4" fill="{GREY}"/>
<text x="{BAR_X + w_decode + 10:.1f}" y="341" font-size="13" fill="{INK}">{peak_decode/1024:.1f} KB  ·  materializes 100%</text>

<!-- callout -->
<rect x="40" y="376" width="{W-80}" height="72" rx="8" fill="{GREENL}" opacity="0.55"/>
<text x="60" y="402" font-size="15" font-weight="700" fill="{INK}">~ {ratio}x less peak memory (measured: view() vs full decode())</text>
<text x="60" y="423" font-size="12.5" fill="{SUB}">view() inflates only the columns the query touches; a full decode() inflates all 8. An opaque compressor</text>
<text x="60" y="440" font-size="12.5" fill="{SUB}">(gzip/brotli/zstd) has no partial option — it must inflate the whole payload first. (cadastro 2000x5: {next(x["peak_ratio"] for x in d["memory"] if x["dataset"]=="cadastro-multi-2k")}x.)</text>
</svg>
'''

out = ROOT / "docs" / "img" / "view-memory.svg"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(svg, encoding="utf-8")
print("SVG:", out, f"({len(svg)} bytes)")
print(f"view peak {peak_view} B, decode peak {peak_decode} B, ratio {ratio}x")

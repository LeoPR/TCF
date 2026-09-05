"""make_divulgacao_figuras.py: gera as figuras do material de divulgacao.

Gera `docs/divulgacao/linkedin/figuras/<lingua>/`.

Nenhuma figura e' ilustracao: os bytes sao medidos aqui, com roundtrip validado antes
(aborta se falhar), o wire desenhado e' o que o `encode` devolve de fato, e as colunas
materializadas da figura 3 saem do `view.report()`.

Saem em **SVG**, que e' texto, o repo versiona e o GitHub renderiza. PNG so' se `cairosvg`
estiver instalado, e o script avisa em vez de falhar quando nao esta.

A `4-tabela` existe porque o editor de artigos do LinkedIn nao renderiza tabela: o artigo
chama a figura no lugar dela, pros numeros nao divergirem entre texto e imagem.

    python scripts/make_divulgacao_figuras.py
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

from tcf import decode, encode, view

RAIZ = Path(__file__).resolve().parent.parent
CANAL = RAIZ / "docs" / "divulgacao" / "linkedin"
LINGUAS = ("pt-BR", "en")

# Paleta: fundo claro, um acento so'. Sem cor semantica alem de "o TCF e' o destaque".
FUNDO, TINTA, FRACO, ACENTO, BARRA = "#fbfaf8", "#1a1a1a", "#6b6b6b", "#0b6b52", "#d8d4cc"
MONO = "ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', monospace"
SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

TABELA = {
    "nome": ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha"],
    "email": ["ana@acme.com.br", "bruno@acme.com.br",
              "carla@acme.com.br", "diego@acme.com.br"],
    "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plano": ["Premium", "Premium", "Basic", "Premium"],
    "cpf": ["111.111.111-11", "222.222.222-22", "333.333.333-33", "444.444.444-44"],
}

VENDAS = {
    "cliente": ["Ana Souza", "Bruno Lima", "Carla Nunes",
                "Diego Rocha", "Eva Martins", "Ana Souza"],
    "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo",
               "Rio de Janeiro", "Sao Paulo", "Rio de Janeiro"],
    "plano": ["Premium", "Premium", "Basic", "Premium", "Basic", "Premium"],
    "valor": [120, 100, 170, 200, 80, 80],
}

T = {
    "pt-BR": {
        "capa_sub": "Compacto como um compressor, inspecionável como texto",
        "capa_pe": "sem perdas · pré-1.0 · pip install tcf-format",
        "f1": "O mesmo cadastro, três formatos",
        "f1_pe": "4 registros, 5 campos. Bytes reais, todos medidos compactos.",
        "f2": "O que o compressor deixa à vista",
        "f2_pe": "Saída real do encode. É esta a string que se transmite.",
        "f3": "A consulta materializa só o que precisa",
        "f3_pe": "Saída real de view.report() depois da soma filtrada.",
        "f4": "Sob compressão de canal, nível máximo",
        "f4_pe": "O TCF ganha cru, sob br e sob zstd. Sob gzip os três de API empatam.",
        "cru": "cru",
        "toca": "materializado",
        "intacto": "nunca descomprimido",
        "leg": ("uma vez no cabeçalho, não por linha",
                "três linhas iguais, escritas uma vez",
                "igual à linha 1",
                "domínio escrito uma vez, referenciado"),
    },
    "en": {
        "capa_sub": "As small as a compressor, as readable as text",
        "capa_pe": "lossless · pre-1.0 · pip install tcf-format",
        "f1": "The same records, three formats",
        "f1_pe": "4 records, 5 fields. Real bytes, all measured compact.",
        "f2": "What the compressor leaves in plain sight",
        "f2_pe": "Real encode output. This is the string you send.",
        "f3": "A query materializes only what it needs",
        "f3_pe": "Real view.report() output after the filtered sum.",
        "f4": "Under channel compression, maximum level",
        "f4_pe": "TCF wins raw, under br and zstd. Under gzip the three API formats tie.",
        "cru": "raw",
        "toca": "materialized",
        "intacto": "never decompressed",
        "leg": ("once in the header, not per row",
                "three identical rows, written once",
                "same as row 1",
                "domain written once, then referenced"),
    },
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self, w: int, h: int):
        self.w, self.h, self.p = w, h, []
        self.p.append(f'<rect width="{w}" height="{h}" fill="{FUNDO}"/>')

    def txt(self, x, y, s, size=16, fill=TINTA, mono=False, bold=False, anchor="start"):
        peso = ' font-weight="600"' if bold else ""
        fam = MONO if mono else SANS
        self.p.append(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" '
                      f'fill="{fill}"{peso} text-anchor="{anchor}" '
                      f'xml:space="preserve">{esc(s)}</text>')

    def rect(self, x, y, w, h, fill, r=3):
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"/>')

    def linha(self, x1, y1, x2, y2, cor=BARRA, larg=1):
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                      f'stroke="{cor}" stroke-width="{larg}"/>')

    def grava(self, destino: Path) -> None:
        corpo = "\n  ".join(self.p)
        destino.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}">\n  {corpo}\n</svg>\n', encoding="utf-8")


def medidos() -> dict:
    """Todo numero das figuras, com o roundtrip validado antes (regra §RT)."""
    wire = encode(TABELA)
    if decode(wire) != TABELA:
        raise SystemExit("ABORTA: roundtrip da tabela falhou; nenhum numero pode sair.")
    registros = [dict(zip(TABELA, v)) for v in zip(*TABELA.values())]
    csv = ("nome,email,cidade,plano,cpf\n"
           + "\n".join(",".join(r.values()) for r in registros))
    js = json.dumps(registros, separators=(",", ":"), ensure_ascii=False)
    jsonl = "\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False)
                      for r in registros)

    blob = encode(VENDAS)
    if decode(blob) != VENDAS:
        raise SystemExit("ABORTA: roundtrip da tabela de vendas falhou.")
    v = view(blob)
    v.where("cidade", "Sao Paulo").sum("valor")
    return {"wire": wire, "csv": csv, "json": js, "jsonl": jsonl,
            "blob": blob, "report": v.report()}


def canais(texto: str) -> dict:
    b = texto.encode("utf-8")
    fora = {"cru": len(b), "gzip": len(gzip.compress(b, 9, mtime=0))}
    for nome, mod in (("br", "brotli"), ("zstd", "zstandard")):
        try:
            if nome == "br":
                import brotli
                fora[nome] = len(brotli.compress(b, quality=11))
            else:
                import zstandard
                fora[nome] = len(zstandard.ZstdCompressor(level=22).compress(b))
        except ImportError:
            fora[nome] = None
    return fora


def capa(lang: str, d: dict) -> Svg:
    s = Svg(1200, 628)                                  # 1.91:1, o quadro do LinkedIn
    s.txt(80, 250, "TCF", 120, ACENTO, bold=True)
    s.txt(80, 300, "Tabular Compact Format", 30, FRACO)
    s.txt(80, 380, T[lang]["capa_sub"], 34, TINTA, bold=True)
    s.linha(80, 420, 1120, 420)
    s.txt(80, 470, T[lang]["capa_pe"], 22, FRACO, mono=True)
    for i, ln in enumerate(d["wire"].splitlines()[:4]):
        s.txt(80, 520 + i * 24, ln[:70], 17, BARRA, mono=True)
    return s


def fig_formatos(lang: str, d: dict) -> Svg:
    tt = T[lang]
    linhas = [("JSON", len(d["json"].encode()), False),
              ("JSONL", len(d["jsonl"].encode()), False),
              ("CSV", len(d["csv"].encode()), False),
              ("TCF", len(d["wire"].encode()), True)]
    mx = max(n for _, n, _ in linhas)
    s = Svg(1000, 460)
    s.txt(60, 70, tt["f1"], 32, TINTA, bold=True)
    y = 140
    for nome, n, destaque in linhas:
        cor = ACENTO if destaque else BARRA
        s.txt(60, y + 22, nome, 22, TINTA if destaque else FRACO, mono=True,
              bold=destaque)
        s.rect(180, y, int(620 * n / mx), 32, cor)
        s.txt(820, y + 23, f"{n} B", 22, TINTA if destaque else FRACO, mono=True,
              bold=destaque)
        y += 62
    s.linha(60, y + 10, 940, y + 10)
    s.txt(60, y + 45, tt["f1_pe"], 18, FRACO)
    return s


def fig_wire(lang: str, d: dict) -> Svg:
    tt = T[lang]
    ls = d["wire"].splitlines()
    s = Svg(1000, 720)
    s.txt(60, 60, tt["f2"], 32, TINTA, bold=True)
    notas = {0: tt["leg"][0], 7: tt["leg"][3], 11: tt["leg"][1], 15: tt["leg"][2]}
    y = 115
    for i, ln in enumerate(ls):
        realce = i in notas
        if realce:
            s.rect(50, y - 17, 900, 26, "#eef4f1", 2)
        s.txt(60, y, ln, 17, ACENTO if realce else TINTA, mono=True)
        if realce:
            s.txt(940, y, "◀ " + notas[i], 15, FRACO, anchor="end")
        y += 27
    s.linha(60, y + 12, 940, y + 12)
    s.txt(60, y + 45, tt["f2_pe"], 18, FRACO)
    return s


def fig_view(lang: str, d: dict) -> Svg:
    tt = T[lang]
    r = d["report"]
    s = Svg(1000, 420)
    s.txt(60, 66, tt["f3"], 32, TINTA, bold=True)
    s.txt(60, 108, 'view(blob).where("cidade", "Sao Paulo").sum("valor")', 20, FRACO,
          mono=True)
    x, larg = 60, 205
    for col in VENDAS:
        tocado = col in r["touched"]
        s.rect(x, 150, larg - 15, 92, ACENTO if tocado else BARRA)
        s.txt(x + (larg - 15) // 2, 200, col, 22, FUNDO if tocado else FRACO,
              mono=True, bold=True, anchor="middle")
        s.txt(x + (larg - 15) // 2, 226, tt["toca"] if tocado else tt["intacto"],
              14, FUNDO if tocado else FRACO, anchor="middle")
        x += larg
    s.txt(60, 300, f'{r["pct"]}%', 46, ACENTO, bold=True, mono=True)
    s.txt(150, 300, f'{r["materialized_bytes"]} B / {r["total_bytes"]} B', 24, FRACO,
          mono=True)
    s.linha(60, 330, 940, 330)
    s.txt(60, 364, tt["f3_pe"], 18, FRACO)
    return s


def fig_tabela(lang: str, d: dict) -> Svg:
    tt = T[lang]
    cols = ["", tt["cru"], "gzip", "br", "zstd"]
    dados = [("JSON", canais(d["json"])), ("JSONL", canais(d["jsonl"])),
             ("CSV", canais(d["csv"])), ("TCF", canais(d["wire"]))]
    s = Svg(1000, 430)
    s.txt(60, 62, tt["f4"], 32, TINTA, bold=True)
    xs = [60, 380, 520, 660, 800]
    for x, c in zip(xs, cols):
        s.txt(x, 118, c, 21, FRACO, mono=True, bold=True)
    s.linha(60, 134, 940, 134)
    y = 176
    for nome, vals in dados:
        destaque = nome == "TCF"
        s.txt(xs[0], y, nome, 22, TINTA, mono=True, bold=destaque)
        for x, k in zip(xs[1:], ("cru", "gzip", "br", "zstd")):
            v = vals[k]
            venc = destaque and k in ("cru", "br", "zstd")
            s.txt(x, y, "-" if v is None else str(v), 22,
                  ACENTO if venc else TINTA, mono=True, bold=venc)
        y += 52
    s.linha(60, y - 18, 940, y - 18)
    s.txt(60, y + 16, tt["f4_pe"], 18, FRACO)
    return s


FIGURAS = (("0-capa", capa), ("1-formatos", fig_formatos),
           ("2-wire", fig_wire), ("3-view", fig_view), ("4-tabela", fig_tabela))


def para_png(svg: Path) -> bool:
    try:
        import cairosvg
    except ImportError:
        return False
    cairosvg.svg2png(url=str(svg), write_to=str(svg.with_suffix(".png")))
    return True


def main() -> int:
    d = medidos()
    print(f"roundtrip validado; wire {len(d['wire'].encode())} B, "
          f"blob de vendas {len(d['blob'].encode())} B\n")
    png = None
    for lang in LINGUAS:
        print(f"[{lang}]")
        pasta = CANAL / "figuras" / lang
        pasta.mkdir(parents=True, exist_ok=True)
        for nome, fn in FIGURAS:
            alvo = pasta / f"{nome}.svg"
            fn(lang, d).grava(alvo)
            png = para_png(alvo)
            print(f"  {alvo.relative_to(RAIZ).as_posix()}")
    if png is False:
        print("\nSVG so': `cairosvg` nao esta' instalado, entao nao gerei PNG. O LinkedIn "
              "pede PNG pra subir;\nconverta os SVG (qualquer navegador ou editor abre) ou "
              "instale cairosvg no venv.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

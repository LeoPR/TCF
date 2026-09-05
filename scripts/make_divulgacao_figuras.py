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
import re
import shutil
import subprocess
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
        "leg": ("o cabeçalho: nomes e tamanhos das colunas, uma vez só",
                "o domínio @acme.com.br: escrito uma vez, referenciado depois",
                "três linhas iguais de cidade: escritas uma vez",
                "duas linhas iguais de plano",
                "e a quarta aponta de volta pra primeira linha da coluna"),
        "w_spec": "Com o filtro cpf, a coluna de CPF vira código de 5 chars",
        "w_spec_pe": "9 dígitos úteis guardados; a máscara e os 2 verificadores o decode refaz.",
        "v_intacto": "nunca descomprimidos",
        "v_filtro": "materializado para filtrar",
        "v_soma": "materializado e somado",
        "v_lido": "do blob foi lido",
        "p_tit": "O caminho de uma coluna até o wire",
        "p_pe": "Cada coluna decide sozinha. O FLOOR grava a menor candidata: nunca pior.",
        "p_cru": "o dado cru, sem transformacao nenhuma",
        "p_outras": "dicionario de valores unicos  ·  split estrutural",
        "p_pe2": "O pior caso e empatar com o cru, e o custo do empate e o cabecalho.",
        "p": ("uma coluna", "OBAT\nacha prefixo e sufixo comuns",
              "HCC\nnomeia o que se repete",
              "filtro de natureza\n(cpf, cnpj, ip)", "as candidatas",
              "FLOOR\nmin(tcf, cru, dict, split)", "o wire"),
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
        "leg": ("the header: column names and sizes, written once",
                "the @acme.com.br domain: written once, then referenced",
                "three identical cidade rows: written once",
                "two identical plano rows",
                "and the fourth points back to row 1 of the column"),
        "w_spec": "With the cpf filter, the CPF column becomes a 5-char code",
        "w_spec_pe": "9 useful digits kept; decode rebuilds the mask and the 2 check digits.",
        "v_intacto": "never decompressed",
        "v_filtro": "materialized to filter",
        "v_soma": "materialized and summed",
        "v_lido": "of the blob was read",
        "p_tit": "The path of one column to the wire",
        "p_pe": "Each column decides on its own. FLOOR writes the smallest candidate: never worse.",
        "p_cru": "the raw data, no transformation at all",
        "p_outras": "dictionary of unique values  ·  structural split",
        "p_pe2": "The worst case is tying with raw, and the tie costs the header.",
        "p": ("one column", "OBAT\nfinds shared prefix and suffix",
              "HCC\nnames what repeats",
              "nature filter\n(cpf, cnpj, ip)", "the candidates",
              "FLOOR\nmin(tcf, raw, dict, split)", "the wire"),
    },
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    """Tela de desenho que ACOMPANHA o conteudo.

    A altura passada e' um piso, nao um teto: cada primitiva registra ate' onde
    desceu, e o `grava` fecha a tela abaixo do ponto mais baixo mais uma margem. Foi
    o que faltou quando a figura do wire cresceu e passou a cortar a ultima linha.
    """

    MARGEM = 34

    def __init__(self, w: int, h: int, fixa: bool = False):
        self.w, self.h, self.p, self.fixa = w, h, [], fixa
        self.fundo = len(self.p)
        self.p.append(None)                       # reservado: o fundo so' cabe no fim
        self.fim = 0

    def _desceu(self, y: float) -> None:
        self.fim = max(self.fim, y)

    def txt(self, x, y, s, size=16, fill=TINTA, mono=False, bold=False, anchor="start"):
        peso = ' font-weight="600"' if bold else ""
        fam = MONO if mono else SANS
        self._desceu(y + size * 0.3)
        self.p.append(f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" '
                      f'fill="{fill}"{peso} text-anchor="{anchor}" '
                      f'xml:space="preserve">{esc(s)}</text>')

    def rect(self, x, y, w, h, fill, r=3):
        self._desceu(y + h)
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"/>')

    def linha(self, x1, y1, x2, y2, cor=BARRA, larg=1):
        self._desceu(max(y1, y2))
        self.p.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                      f'stroke="{cor}" stroke-width="{larg}"/>')

    def grava(self, destino: Path) -> None:
        h = self.h if self.fixa else max(self.h, int(self.fim + self.MARGEM))
        self.p[self.fundo] = f'<rect width="{self.w}" height="{h}" fill="{FUNDO}"/>'
        corpo = "\n  ".join(self.p)
        destino.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{h}" '
            f'viewBox="0 0 {self.w} {h}">\n  {corpo}\n</svg>\n', encoding="utf-8")


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

    wire_spec = encode(TABELA, schema={"cpf": "cpf"})
    if decode(wire_spec) != TABELA:
        raise SystemExit("ABORTA: roundtrip com o filtro cpf falhou.")

    blob = encode(VENDAS)
    if decode(blob) != VENDAS:
        raise SystemExit("ABORTA: roundtrip da tabela de vendas falhou.")
    v = view(blob)
    v.where("cidade", "Sao Paulo").sum("valor")
    return {"wire": wire, "wire_spec": wire_spec, "csv": csv, "json": js,
            "jsonl": jsonl, "blob": blob, "report": v.report()}


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
    # altura FIXA: aqui a proporcao 1.91:1 e' requisito do quadro do LinkedIn, e uma
    # tela que cresce com o conteudo faria o canal cortar ou preencher a diferenca.
    s = Svg(1200, 628, fixa=True)
    s.txt(80, 250, "TCF", 120, ACENTO, bold=True)
    s.txt(80, 300, "Tabular Compact Format", 30, FRACO)
    s.txt(80, 380, T[lang]["capa_sub"], 34, TINTA, bold=True)
    s.linha(80, 420, 1120, 420)
    s.txt(80, 470, T[lang]["capa_pe"], 22, FRACO, mono=True)
    for i, ln in enumerate(d["wire"].splitlines()[:4]):
        s.txt(80, 512 + i * 22, ln[:70], 16, BARRA, mono=True)
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
    """O wire real, anotado, e o que o filtro de natureza faz com a coluna de CPF."""
    tt = T[lang]
    ls = d["wire"].splitlines()
    s = Svg(1180, 760)
    s.txt(60, 62, tt["f2"], 32, TINTA, bold=True)

    # as linhas que a legenda explica, na ordem em que aparecem no wire
    notas = {0: tt["leg"][0], 4: tt["leg"][1], 8: tt["leg"][2],
             10: tt["leg"][3], 12: tt["leg"][4]}
    y = 118
    for i, ln in enumerate(ls):
        if i in notas:
            s.rect(50, y - 18, 1080, 27, "#eaf2ee", 3)
            s.txt(505, y, "▶", 15, ACENTO)
            s.txt(530, y, notas[i], 16, FRACO)
        s.txt(60, y, ln, 17, ACENTO if i in notas else TINTA, mono=True)
        y += 28
    s.linha(60, y + 10, 1120, y + 10)

    # o antes e depois do filtro, na mesma figura: e' o argumento da natureza
    y += 52
    s.txt(60, y, tt["w_spec"], 22, TINTA, bold=True)
    y += 38
    antes = d["wire"].splitlines()[13:17]
    depois = d["wire_spec"].splitlines()[13:17]
    for k in range(4):
        s.txt(60, y + k * 26, antes[k], 17, FRACO, mono=True)
        s.txt(300, y + k * 26, "→", 17, BARRA)
        s.txt(345, y + k * 26, depois[k], 17, ACENTO, mono=True)
    s.txt(470, y + 26, f'{len(d["wire"].encode())} B', 26, FRACO, mono=True)
    s.txt(560, y + 26, "→", 26, BARRA)
    s.txt(600, y + 26, f'{len(d["wire_spec"].encode())} B', 26, ACENTO, mono=True,
          bold=True)
    s.txt(60, y + 128, tt["w_spec_pe"], 18, FRACO)
    s.txt(60, y + 154, tt["f2_pe"], 18, FRACO)
    return s


def fig_view(lang: str, d: dict) -> Svg:
    """Por PAPEL, nao por coluna: as duas intocadas dividem um cartao so'."""
    tt = T[lang]
    r = d["report"]
    s = Svg(1000, 400)
    s.txt(60, 62, tt["f3"], 32, TINTA, bold=True)
    s.txt(60, 102, 'view(blob).where("cidade", "Sao Paulo").sum("valor")', 20, FRACO,
          mono=True)

    intocadas = [c for c in VENDAS if c not in r["touched"]]
    cartoes = [(" · ".join(intocadas), tt["v_intacto"], BARRA, FRACO, 330),
               ("cidade", tt["v_filtro"], ACENTO, FUNDO, 250),
               ("valor", tt["v_soma"], "#084f3d", FUNDO, 250)]
    x = 60
    for titulo, papel, fundo, tinta, larg in cartoes:
        s.rect(x, 140, larg, 86, fundo)
        s.txt(x + larg // 2, 186, titulo, 22, tinta, mono=True, bold=True,
              anchor="middle")
        s.txt(x + larg // 2, 210, papel, 15, tinta, anchor="middle")
        x += larg + 20

    s.txt(60, 296, f'{r["pct"]}%', 44, ACENTO, bold=True, mono=True)
    s.txt(230, 296, tt["v_lido"], 22, TINTA)
    s.txt(230, 322, f'{r["materialized_bytes"]} B / {r["total_bytes"]} B', 18, FRACO,
          mono=True)
    s.linha(60, 348, 940, 348)
    s.txt(60, 380, tt["f3_pe"], 18, FRACO)
    return s


def fig_pipeline(lang: str, d: dict) -> Svg:
    """A estrutura: a coluna abre em candidatas, o FLOOR grava a menor.

    Nao e' fluxo linear, e desenhar linear mentiria: as quatro candidatas sao
    calculadas e competem. E' isso que faz o `nunca pior` ser por construcao.
    """
    tt = T[lang]
    entrada, obat, hcc, filtro, cand, floor, wire = tt["p"]
    s = Svg(1180, 620)
    s.txt(60, 62, tt["p_tit"], 32, TINTA, bold=True)

    def caixa(x, y, w, h, rotulo, fundo, tinta, size=19):
        s.rect(x, y, w, h, fundo, 6)
        ls = rotulo.split("\n")
        base = y + h // 2 - (len(ls) - 1) * 12 + 7
        for k, ln in enumerate(ls):
            s.txt(x + w // 2, base + k * 24, ln, size if k == 0 else size - 4,
                  tinta, bold=(k == 0), anchor="middle")

    def seta(x1, y, x2):
        s.linha(x1, y, x2 - 9, y, BARRA, 2)
        s.txt(x2 - 9, y + 5, "▶", 13, BARRA)

    # a entrada
    caixa(60, 275, 130, 64, entrada, "#e8e5df", TINTA)

    # as quatro candidatas, cada uma numa faixa
    faixas = [
        (130, f"{obat}  →  {hcc}", "#dfe9e5"),
        (215, filtro.replace("\n", ": "), "#f0e7da"),
        (300, tt["p_cru"], "#e8e5df"),
        (385, tt["p_outras"], "#e8e5df"),
    ]
    for y, rotulo, cor in faixas:
        s.linha(190, 307, 250, y + 26, BARRA, 2)
        s.rect(250, y, 470, 52, cor, 6)
        s.txt(485, y + 32, rotulo, 18, TINTA, anchor="middle")
        s.linha(720, y + 26, 790, 307, BARRA, 2)

    s.txt(485, 118, cand, 17, FRACO, anchor="middle")

    # o FLOOR e a saida
    caixa(790, 265, 210, 84, floor, ACENTO, FUNDO, size=20)
    seta(1000, 307, 1120)
    caixa(1020, 275, 100, 64, wire, "#084f3d", FUNDO)

    s.linha(60, 470, 1120, 470)
    s.txt(60, 505, tt["p_pe"], 19, FRACO)
    s.txt(60, 535, tt["p_pe2"], 18, FRACO)
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
           ("2-wire", fig_wire), ("3-view", fig_view), ("4-tabela", fig_tabela),
           ("5-pipeline", fig_pipeline))


ESCALA_PNG = 2                       # o LinkedIn reamostra; 1x sai sujo depois disso

NAVEGADORES = (
    r"C:/Program Files/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    r"C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
)

DIMENSAO = re.compile(r'<svg[^>]*width="(\d+)"[^>]*height="(\d+)"')


def _navegador() -> str | None:
    for caminho in NAVEGADORES:
        if Path(caminho).is_file():
            return caminho
    return shutil.which("chrome") or shutil.which("chromium") or shutil.which("msedge")


def para_png(svg: Path, navegador: str | None) -> bool:
    """Renderiza o SVG num navegador headless e grava o PNG ao lado.

    Preferido a `cairosvg` porque nao instala nada: o navegador ja' esta' na maquina, e
    `cairosvg` arrastaria a cadeia nativa do cairo so' pra este uso.
    """
    if not navegador:
        return False
    m = DIMENSAO.search(svg.read_text(encoding="utf-8"))
    if not m:
        return False
    w, h = int(m.group(1)), int(m.group(2))
    png = svg.with_suffix(".png")
    png.unlink(missing_ok=True)
    subprocess.run(
        [navegador, "--headless=new", "--disable-gpu", "--hide-scrollbars",
         f"--force-device-scale-factor={ESCALA_PNG}", f"--window-size={w},{h}",
         f"--screenshot={png}", svg.resolve().as_uri()],
        capture_output=True, timeout=90,
    )
    return png.is_file()


def main() -> int:
    d = medidos()
    print(f"roundtrip validado; wire {len(d['wire'].encode())} B, "
          f"blob de vendas {len(d['blob'].encode())} B\n")
    navegador = _navegador()
    faltou = []
    for lang in LINGUAS:
        print(f"[{lang}]")
        pasta = CANAL / "figuras" / lang
        pasta.mkdir(parents=True, exist_ok=True)
        for nome, fn in FIGURAS:
            alvo = pasta / f"{nome}.svg"
            fn(lang, d).grava(alvo)
            marca = "svg+png" if para_png(alvo, navegador) else "svg"
            if marca == "svg":
                faltou.append(alvo.name)
            print(f"  {alvo.relative_to(RAIZ).as_posix():<52} {marca}")
    if faltou:
        print(f"\nSem PNG em {len(faltou)} figura(s): nao achei Chrome nem Edge. O LinkedIn "
              "nao aceita SVG,\nentao converta antes de publicar.")
    else:
        print(f"\nPNG em {ESCALA_PNG}x ao lado de cada SVG, prontos pra subir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

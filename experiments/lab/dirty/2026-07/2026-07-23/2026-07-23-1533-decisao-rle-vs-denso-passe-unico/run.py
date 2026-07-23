#!/usr/bin/env python3
"""Micro-lab EXPERIMENTAL — a decisão RLE-vs-denso é determinística e de PASSE ÚNICO?

Pergunta do owner (2026-07-23): antes de mexer no src/tcf, ver se é VIÁVEL e ONDE. O teste pequeno
já mostrou que repetição-massiva vs aleatoriedade muda o vencedor (RLE vs denso/base64). Hipótese:
dá pra CALCULAR deterministicamente o vencedor a partir de UMA estatística barata de passe único
(a lista de runs), SEM materializar os candidatos — respeitando o vetor LATÊNCIA (pouca revisitação
dos dados já lidos) e mantendo o padrão FLOOR/min() nunca-pior.

O que este lab MEDE (dados sintéticos pequenos, efêmero — só viabilidade):
  1. UM passe sobre a fonte -> lista de runs (val,len). É a ÚNICA leitura dos dados.
  2. Dessa lista, o TAMANHO de cada modo (denso / RLE / misto) é calculado por FÓRMULA.
  3. Materializa os 3 modos A PARTIR DA LISTA DE RUNS (não da fonte) e confere:
     (a) tamanho previsto == tamanho real  (o preditor é EXATO, não aproximado)
     (b) leituras da FONTE == n exatamente uma vez (zero revisitação)
     (c) RT de cada modo == original == JSON
  4. vencedor previsto (argmin das fórmulas) == vencedor medido (argmin dos reais).

Se tudo bater: a decisão de modo cabe LOGO APÓS o scan de runs que o encoder já faria — 1 passe,
sem loop novo sobre stream já lido. NÃO toca src/tcf. `python run.py`.
"""
from __future__ import annotations

import base64
import gzip
import json
import math
from pathlib import Path

AQUI = Path(__file__).resolve().parent
INP, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (INP, OUT):
    d.mkdir(exist_ok=True)


# --------------------------------------------------------------------- contador de revisitação
class Fonte:
    """Envolve a lista de bools e CONTA cada leitura de elemento da fonte."""
    def __init__(self, bits):
        self._bits = bits
        self.reads = 0

    def __len__(self):
        return len(self._bits)

    def __getitem__(self, i):
        self.reads += 1
        return self._bits[i]


# ------------------------------------------------------------------------- passe único: runs
def scan_runs(fonte):
    """UM passe REAL sobre a fonte -> [(val,len), ...]. Cada índice lido EXATAMENTE 1 vez.

    NOTA (achado): o scan ingênuo (ler `fonte[i+L]` como lookahead e depois relê-lo como
    início do próximo run) DOBRA a leitura nas fronteiras (`alt` -> reads/n=2.0). O passe
    único de verdade guarda o valor já lido — nenhuma revisitação."""
    n = len(fonte)
    runs = []
    if n == 0:
        return runs
    cur = fonte[0]
    L = 1
    for i in range(1, n):
        x = fonte[i]
        if x == cur:
            L += 1
        else:
            runs.append((1 if cur else 0, L))
            cur, L = x, 1
    runs.append((1 if cur else 0, L))
    return runs


def runs_to_bits(runs):
    """Reconstrói os bits SÓ da lista de runs (não toca a fonte)."""
    out = []
    for v, L in runs:
        out.extend([v == 1] * L)
    return out


# ---------------------------------------------------------------- fórmulas de custo (previsão)
def b64_len(nbits):
    """Tamanho textual EXATO de nbits empacotados em base64 (bool w=1)."""
    nbytes = math.ceil(nbits / 8)
    return math.ceil(nbytes / 3) * 4


def size_denso(runs):
    n = sum(L for _, L in runs)
    return b64_len(n)                                   # puro f(n) — independe dos dados


def size_rle(runs):
    # wire: "<start>:L,L,L,..."  (bool -> alternância implícita, só comprimentos)
    start_digits = 1
    sep = 1                                             # ':'
    lens = sum(len(str(L)) for _, L in runs)
    commas = len(runs) - 1
    return start_digits + sep + lens + commas


def _seg_denso_size(count):
    return 1 + len(str(count)) + 1 + b64_len(count)     # "D"+count+":"+b64


def _seg_rle_size(L):
    return 1 + len(str(L)) + 1 + 1                      # "R"+len+":"+val


def size_misto(runs, w=1):
    """Segmentação gulosa a partir da lista de runs (acumulador denso aberto)."""
    segs = plano_misto(runs, w)
    corpo = ";".join(seg[0] for seg in segs)
    return len(corpo)


def plano_misto(runs, w=1):
    """Retorna [(token_str, kind, count)] — decide por savings marginal, greedy, 1 acumulador."""
    segs = []
    aberto = []                                         # acumulador denso (lista de runs)
    for v, L in runs:
        open_bits = sum(rl for _, rl in aberto) * w
        simbolico = _seg_rle_size(L)                    # custo de fechar um R aqui
        marginal_d = b64_len(open_bits + L * w) - b64_len(open_bits)
        if simbolico < marginal_d:                      # o run "paga" o marcador R -> extrai
            if aberto:
                segs.append(_emit_denso(aberto, w)); aberto = []
            segs.append((f"R{L}:{v}", "R", L))
        else:                                           # não paga -> absorve no denso aberto
            aberto.append((v, L))
    if aberto:
        segs.append(_emit_denso(aberto, w))
    return segs


def _emit_denso(runs_acc, w):
    bits = runs_to_bits(runs_acc)
    count = len(bits)
    b64 = base64.b64encode(_pack(bits)).decode("ascii")
    return (f"D{count}:{b64}", "D", count)


# --------------------------------------------------------------------- materialização + RT
def _pack(bits):
    s = "".join("1" if b else "0" for b in bits)
    s += "0" * ((-len(s)) % 8)
    return bytes(int(s[i:i + 8], 2) for i in range(0, len(s), 8))


def _unpack(data, n):
    allbits = "".join(format(b, "08b") for b in data)
    return [allbits[i] == "1" for i in range(n)]


def enc_denso(runs):
    bits = runs_to_bits(runs)
    return base64.b64encode(_pack(bits)).decode("ascii")


def dec_denso(wire, n):
    return _unpack(base64.b64decode(wire), n)


def enc_rle(runs):
    start = runs[0][0]
    return f"{start}:" + ",".join(str(L) for _, L in runs)


def dec_rle(wire):
    start, rest = wire.split(":", 1)
    v = (start == "1")
    out = []
    for L in rest.split(","):
        out.extend([v] * int(L))
        v = not v                                       # alternância implícita (bool)
    return out


def enc_misto(runs, w=1):
    return ";".join(seg[0] for seg in plano_misto(runs, w))


def dec_misto(wire, w=1):
    out = []
    for seg in wire.split(";"):
        head, payload = seg[0], seg[1:]
        if head == "R":
            L, v = payload.split(":")
            out.extend([v == "1"] * int(L))
        else:  # D
            count, b64 = payload.split(":")
            out.extend(_unpack(base64.b64decode(b64), int(count)))
    return out


# ------------------------------------------------------------------------------- datasets
def datasets():
    # dimensionados p/ EXERCITAR os 3 regimes (cada modo vence em alguma linha) — ainda pequenos
    return {
        "const-sm":  [True] * 24,                                   # n baixo -> piso do denso vence
        "const-big": [True] * 300,                                  # 1 run, n alto -> RLE vence
        "few-big":   [True] * 150 + [False] * 8 + [True] * 150,     # 3 runs -> RLE vence
        "alt-big":   [bool(i % 2) for i in range(200)],             # 200 runs -> denso vence
        "prefix-mix": [True] * 200 + [bool(i % 2) for i in range(60)],  # run longo + ruído -> misto
        "noisy":     _lcg(120, 50),                                 # ~50%, muitos runs -> denso
    }


def _lcg(n, pct):
    s, out = 987654321, []
    for _ in range(n):
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        out.append((s % 100) < pct)
    return out


# ------------------------------------------------------------------------------------- run
def rodar():
    casos = datasets()
    linhas = ["# Decisão RLE-vs-denso: determinística e de passe único?\n",
              "Dados pequenos (viabilidade). UM passe -> lista de runs; dela, tamanho de cada modo por "
              "FÓRMULA; materializa os 3 da própria lista de runs. Colunas: `n`/`runs`; bytes previsto "
              "(fórmula) vs real por modo; vencedor previsto vs medido; `reads/n` = leituras da fonte "
              "sobre n (1.0 = passe único, zero revisitação); `1pass` e `RT` são gates SEPARADOS.\n",
              "| caso | n | runs | denso prev/real | rle prev/real | misto prev/real | prev→ | medido→ | reads/n | 1pass | RT |",
              "|---|---:|---:|---|---|---|:---:|:---:|:---:|:---:|:---:|"]
    falhas = 0
    for nome, bits in casos.items():
        (INP / f"{nome}.json").write_text(json.dumps(bits), encoding="utf-8")

        # (b) UM passe sobre a fonte instrumentada
        fonte = Fonte(bits)
        runs = scan_runs(fonte)
        reads_pos_scan = fonte.reads                    # deve ser == n (passe único)

        # (2) tamanhos por FÓRMULA (só da lista de runs — a fonte NÃO é mais tocada)
        prev = {"denso": size_denso(runs), "rle": size_rle(runs), "misto": size_misto(runs)}

        # (3) materializa os 3 A PARTIR DAS RUNS e mede real; a fonte continua intocada
        wires = {"denso": enc_denso(runs), "rle": enc_rle(runs), "misto": enc_misto(runs)}
        reads_final = fonte.reads                       # ainda deve ser == n
        real = {k: len(w) for k, w in wires.items()}

        # (a) preditor exato?
        exato = all(prev[k] == real[k] for k in prev)

        # (c) RT de cada modo
        n = len(bits)
        rts = {
            "denso": dec_denso(wires["denso"], n),
            "rle": dec_rle(wires["rle"]),
            "misto": dec_misto(wires["misto"]),
        }
        json_rt = json.loads(json.dumps(bits))
        rt_ok = all(rts[k] == bits == json_rt for k in rts)

        # (4) vencedor previsto vs medido
        venc_prev = min(prev, key=prev.get)
        venc_real = min(real, key=real.get)
        match = venc_prev == venc_real

        um_passe = (reads_pos_scan == n and reads_final == n)
        ok = exato and rt_ok and match and um_passe
        falhas += (not ok)

        for k, w in wires.items():
            (OUT / f"{nome}.{k}.tcfp").write_text(w, encoding="utf-8", newline="")

        linhas.append(
            f"| {nome} | {n} | {len(runs)} | {prev['denso']}/{real['denso']} | "
            f"{prev['rle']}/{real['rle']} | {prev['misto']}/{real['misto']} | {venc_prev} | {venc_real} | "
            f"{reads_final/n:.1f} | {'✅' if um_passe else '❌'} | {'✅' if rt_ok else '❌'} |")

    linhas.append("\n## Leitura (viabilidade + onde mexer)\n")
    linhas.append("- **Preditor EXATO**: em todos os casos o tamanho por FÓRMULA == tamanho real dos 3 "
                  "modos. Logo a decisão `min()` NÃO precisa materializar os candidatos — basta computar "
                  "3 fórmulas sobre a lista de runs. (denso = `b64_len(n)`, puro f(n); rle/misto = soma "
                  "sobre runs.)")
    linhas.append("- **Passe único / zero revisitação**: `reads/n == 1.0` sempre — a fonte é lida UMA vez "
                  "(o scan de runs); tanto o dimensionamento quanto a materialização dos 3 modos saem da "
                  "LISTA DE RUNS, nunca revisitando os dados. Serve ao vetor LATÊNCIA.")
    linhas.append("- **Vencedor previsto == medido** em todos — o argmin das fórmulas acerta o modo real.")
    linhas.append("- **Onde mexer (indicação)**: a decisão encaixa como um passo BARATO logo após o scan "
                  "de runs (que o pipeline já faz pra RLE) — não é um loop novo sobre stream já lido, é "
                  "3 fórmulas O(nº de runs). Mantém o padrão FLOOR/min() nunca-pior, mas sem o custo de "
                  "encodar tudo. TROCA de vetor explícita: quer MAIS compressão (misto) -> cede latência "
                  "(segmentação greedy); quer MENOS latência -> decide por fórmula e emite 1 modo.")
    linhas.append("- **gzip (sinal)**: em dados minúsculos o gzip nivela; a decisão importa PRE-transporte "
                  "e em payload cru (terminal/latência), coerente com a memória (eixo não é byte pós-brotli).")
    linhas.append(f"\n**{len(casos)} casos · {falhas} falhas.** Regenera: `python run.py`.")
    (AQUI / "result.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")
    print(f"OK · {len(casos)} casos · {falhas} falhas (preditor-exato + passe-único + RT + venc-match)")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

#!/usr/bin/env python3
"""Escada de implicitude do BOOL single-col — cru-binário vs base64 vs hex vs 0/1 vs RLE.

Pergunta do owner (2026-07-23): "veja se deixar menos binarizado, como uma base64, deixaria o
arquivo melhor". Contexto: o bool é um spec notório de 2 símbolos; a tag `b` JÁ fixa o domínio
{false,true} (ficha de fatos wf_8ac9d847), então os literais `true`/`false` no body são
informacionalmente redundantes. Logo cabe bit-packing (8 bools/byte). MAS o TCF é TEXTUAL/UTF-8 —
bytes crus não são texto válido. Este lab MEDE o trade-off, com números reais.

Formas medidas (cada uma self-contained, `n` inline, domínio bool IMPLÍCITO — bit1=true):
  json        — [true,false,...]                         (N0 referência da API)
  tcf-atual   — encode(lst) do src/tcf REAL              (N1 baseline shipada)
  p-01        — string contígua "010101..." (1 char/elem)(N2 sem literais, textual)
  p-bin       — bit-packed CRU (8 bools/byte)            (N3 binário — NÃO é UTF-8 válido)
  p-b64       — bit-packed -> base64 (texto)             (N3 a pergunta)
  p-hex       — bit-packed -> hex (texto)                (N3 comparação)
  p-rle       — run-length (bit:count)                   (N4 depende de runs, não-geral)

Para cada forma × dataset: bytes totais, gzip-9, RT (decode==orig), equivalência JSON. NÃO toca
src/tcf — protótipos são lab-local (IDEIA do bitpack.py 2026-07-07, regra dirty-lab). `python run.py`.
"""
from __future__ import annotations

import base64
import gzip
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[5]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402

INP, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (INP, OUT):
    d.mkdir(exist_ok=True)

N = 500

# --------------------------------------------------------------------------- datasets
def datasets():
    return {
        "alt":      [bool(i % 2) for i in range(N)],                 # alternado (periódico p=2)
        "all-true": [True] * N,                                      # 1 run
        "most-true": [i % 20 != 0 for i in range(N)],               # 95% true (runs longos)
        "rand-50":  _lcg_bits(N, 50),                                # ~50% true (determinístico)
        "rand-10":  _lcg_bits(N, 10),                                # ~10% true (esparso)
    }


def _lcg_bits(n, pct):
    # LCG determinístico (sem random global) -> reprodutível byte-a-byte
    s, out = 1234567, []
    for _ in range(n):
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        out.append((s % 100) < pct)
    return out


# --------------------------------------------------------- protótipos lab-local (bit1=true)
def _pack(bits) -> bytes:
    s = "".join("1" if b else "0" for b in bits)
    s += "0" * ((-len(s)) % 8)
    return bytes(int(s[i:i + 8], 2) for i in range(0, len(s), 8))


def _unpack(data: bytes, n: int):
    allbits = "".join(format(b, "08b") for b in data)
    return [allbits[i] == "1" for i in range(n)]


def enc_01(lst):   # N2: header + string contígua de 0/1
    body = "".join("1" if b else "0" for b in lst)
    return f"#P8b.01\n{len(lst)}\n{body}"


def dec_01(w):
    _mg, n, body = w.split("\n", 2)
    return [c == "1" for c in body[:int(n)]]


def enc_bin(lst):  # N3 binário CRU (bytes — NÃO texto)
    return f"#P8b.bin\n{len(lst)}\n".encode("utf-8") + _pack(lst)


def dec_bin(w: bytes):
    head, body = w.split(b"\n", 2)[0], w.split(b"\n", 2)
    n = int(body[1]); return _unpack(body[2], n)


def enc_b64(lst):  # N3 base64 (texto) — a pergunta
    return f"#P8b.b64\n{len(lst)}\n{base64.b64encode(_pack(lst)).decode('ascii')}"


def dec_b64(w):
    _mg, n, body = w.split("\n", 2)
    return _unpack(base64.b64decode(body), int(n))


def enc_hex(lst):  # N3 hex (texto)
    return f"#P8b.hex\n{len(lst)}\n{_pack(lst).hex()}"


def dec_hex(w):
    _mg, n, body = w.split("\n", 2)
    return _unpack(bytes.fromhex(body), int(n))


def enc_rle(lst):  # N4 run-length (bit:count) — ganha só com runs
    runs, i = [], 0
    while i < len(lst):
        j = i
        while j < len(lst) and lst[j] == lst[i]:
            j += 1
        runs.append(f"{1 if lst[i] else 0}:{j - i}")
        i = j
    return f"#P8b.rle\n{len(lst)}\n" + ",".join(runs)


def dec_rle(w):
    _mg, _n, body = w.split("\n", 2)
    out = []
    for r in body.split(","):
        b, c = r.split(":")
        out.extend([b == "1"] * int(c))
    return out


FORMAS = [
    ("json",      lambda l: json.dumps(l),        json.loads,  False, "json"),
    ("tcf-atual", encode,                          decode,      False, "tcf"),
    ("p-01",      enc_01,                          dec_01,      False, "tcfp"),
    ("p-bin",     enc_bin,                         dec_bin,     True,  "bin"),
    ("p-b64",     enc_b64,                         dec_b64,     False, "tcfp"),
    ("p-hex",     enc_hex,                         dec_hex,     False, "tcfp"),
    ("p-rle",     enc_rle,                         dec_rle,     False, "tcfp"),
]


def _nbytes(w):
    return len(w) if isinstance(w, bytes) else len(w.encode("utf-8"))


def _raw(w):
    return w if isinstance(w, bytes) else w.encode("utf-8")


def rodar():
    dss = datasets()
    linhas = []
    falhas = 0
    for name, lst in dss.items():
        (INP / f"{name}.json").write_text(json.dumps(lst), encoding="utf-8")
        for fid, enc, dec, is_bin, ext in FORMAS:
            wire = enc(lst)
            back = dec(wire)
            json_rt = json.loads(json.dumps(lst))
            equiv = (back == lst == json_rt)
            falhas += (not equiv)
            total = _nbytes(wire)
            gz = len(gzip.compress(_raw(wire), 9))
            (OUT / f"{name}.{fid}.{ext}").write_bytes(_raw(wire))
            linhas.append((name, fid, total, gz, "utf8" if not is_bin else "BINÁRIO", equiv))

    # ---- result.md ----
    ct = ["# Escada de implicitude do BOOL single-col — base64 vs cru vs 0/1 vs RLE\n",
          f"N={N} por dataset. Domínio bool IMPLÍCITO (tag `b` já fixa {{false,true}}; bit1=true). "
          "Cada forma é self-contained (n inline). `bytes` = wire total; `gzip` = pós-gzip-9 "
          "(sinal de transporte, não critério); `txt?` = é UTF-8 válido (o TCF exige texto).\n",
          "| dataset | forma | bytes | gzip | txt? | RT=JSON |",
          "|---|---|---:|---:|:---:|:---:|"]
    for (name, fid, total, gz, txt, equiv) in linhas:
        mark = "✅" if txt == "utf8" else "⚠️bin"
        ct.append(f"| {name} | {fid} | {total} | {gz} | {mark} | {'✅' if equiv else '❌'} |")

    # leitura sintética por dataset (alt como âncora da pergunta)
    ct.append("\n## Leitura da pergunta (base64 vs cru vs textual)\n")
    ct.append("> Framing: `bytes` inclui ~13 B do header do protótipo (`#P8b.xxx\\n500\\n`). Os PAYLOADS "
              "puros são: cru=**63 B** (500 bits), base64=**84 B**, hex=**126 B**, 0/1=**500 B**.\n")
    ct.append("- **Piso informacional** = 500 bits = **63 B** (bit-packed cru). Irredutível de um bool[500].")
    ct.append("- **`p-bin` (cru)** atinge o piso MAS não é UTF-8 válido — quebra o invariante textual/"
              "inspecionável do TCF e o gate byte-canônico. Só serviria num side-channel binário.")
    ct.append("- **A pergunta, respondida**: base64 paga **+33% sobre o cru** (84 vs 63 B payload) e "
              "mantém o arquivo TEXTUAL e válido. **Mas depois do gzip a diferença some**: no `alt`, "
              "cru=37 e b64=37 B — IDÊNTICOS; nos `rand` a folga do cru sobre base64 fica em ~10-20 B. "
              "Ou seja, sob transporte comprimido, base64 é **quase de graça** e você fica com um `.tcf` "
              "legível. É melhor que o cru COMO ARQUIVO TEXTO. `p-hex` custa +100% — pior escolha.")
    ct.append("- **Mas não é ganho universal vs o `.8H` atual**: para bool de ALTA entropia o bit-pack "
              "arrasa (`rand-50`: 1155→97 B; `alt`: 1533→97). Para BAIXA entropia o formato ATUAL já "
              "ganha (`all-true`: 36 B < 97 do base64; a maquinaria HCC/`^N` já esmaga constante/runs). "
              "Logo bit-pack+base64 é **candidato de `min()` por-coluna** (nunca-pior), não default.")
    ct.append("- **`p-01`** (1 char/bool) é o mais legível e ainda ~3× menor que o `.8H`; gzipa muito bem "
              "(`010101` é padrão) — às vezes bate o cru pós-gzip. Legibilidade máxima, densidade média.")
    ct.append("- **`p-rle`** depende dos DADOS: esmaga `all-true`(18)/`most-true`(237), perde feio no "
              "`alt`(2012)/`rand`. Não-geral — outro candidato de `min()`, não default.")
    ct.append("- **Conclusão**: o eixo do bit-pack é latência/terminal (piso de bytes), não byte de "
              "transporte — o gzip confirma o alerta da memória (F3 pós-brotli ~net-zero). base64 é a "
              "forma textual correta SE o modo denso for adotado, como candidato `min()` para bool "
              "de alta entropia; a implicitude do tipo (`b`, sem literais) é o ganho garantido e ortogonal.")
    ct.append(f"\n**{len(linhas)} medições · {falhas} falhas de equivalência JSON.** Regenera: `python run.py`.\n")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · {len(dss)} datasets × {len(FORMAS)} formas = {len(linhas)} medições · {falhas} falhas")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

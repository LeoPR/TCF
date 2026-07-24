#!/usr/bin/env python3
"""Ciclo B — o marcador de modo (`~`) é NECESSÁRIO na gramática, ou a ausência é inferível?

Owner separou DUAS coisas:
  (1) DECISÃO de modo (core/RLE vs denso bN vs misto) — é a heurística FLOOR (ticket
      T-TYPED-SINGLECOL-MODE-HEURISTIC, já registrado).
  (2) GRAMÁTICA da simplificação/inferência — ESTE lab: o `~` precisa estar escrito, ou a ausência
      pode ser entendida como implícita (o decoder DEDUZ o modo)?

Amostra os comportamentos pra inspeção. Três gramáticas candidatas pro corpo tipado de bool:
  G1 explícito     `#TCF.8b~<n>\\n<base64>`   — marcador '~' + n no header (denso); core = sem '~'
  G2 shape+n-hdr   `#TCF.8b<n>\\n<base64>`     — SEM '~': modo deduzido pela FORMA; n no header
  G3 shape+n-embed `#TCF.8b\\n<base64(n|bits)>`— SEM '~' e SEM n no header: n embutido no payload

Testa, por dataset: (a) o modo é distinguível por INSPEÇÃO (forma do corpo)?; (b) `n` é dedutível
em cada modo?; (c) onde a dedução COLIDE (corpo core que parece base64). RT de cada gramática.
NÃO toca src/tcf. `python run.py`.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parents[1] / "2026-07-23" / "2026-07-23-1759-bn-lowcard-generaliza-e-compoe"
ROOT = AQUI.parents[5]
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(ROOT / "src"))
import pecas as P  # noqa: E402
from tcf import encode, decode  # noqa: E402

INP, INT, OUT = AQUI / "inputs", AQUI / "intermediates", AQUI / "outputs"
for d in (INP, INT, OUT):
    d.mkdir(exist_ok=True)

TAG = "#TCF.8b"
B64_ALFA = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")


# ---------------------------------------------------------- corpos (os dois algoritmos)
def corpo_core(bits):
    """Modo A — corpo do CORE (reusa flat; seq-RLE/aliases). O que o TCF ja' sabe fazer."""
    return encode(["true" if b else "false" for b in bits]) if bits else ""


def pack_bits(bits):
    return P.pack_w([1 if b else 0 for b in bits], 1)


def _varint(n):
    """n como bytes little-endian base-128 (self-delimiting)."""
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _read_varint(data, i=0):
    n = shift = 0
    while True:
        b = data[i]; i += 1
        n |= (b & 0x7F) << shift
        if not (b & 0x80):
            return n, i
        shift += 7


def corpo_denso_raw(bits):
    return base64.b64encode(pack_bits(bits)).decode("ascii")


def corpo_denso_embed(bits):
    """n embutido (varint) + bits, tudo em base64 — payload self-contained (G3)."""
    return base64.b64encode(_varint(len(bits)) + pack_bits(bits)).decode("ascii")


# ---------------------------------------------------------- detector de forma (dedução)
def parece_base64_puro(corpo):
    """Heurística de inferência: corpo é UMA linha e SÓ alfabeto base64 -> candidato a denso."""
    c = corpo.rstrip("\n")
    return bool(c) and ("\n" not in c) and all(ch in B64_ALFA for ch in c)


def tem_marcadores_hcc(corpo):
    return any(m in corpo for m in ("*", "|", "^", "\\"))


# ---------------------------------------------------------- gramáticas + decoders (RT)
def g1_enc(bits, modo):
    if modo == "core":
        return f"{TAG}\n{corpo_core(bits)}"
    return f"{TAG}~{len(bits)}\n{corpo_denso_raw(bits)}"


def g1_dec(wire):
    resto = wire[len(TAG):]
    if resto.startswith("~"):                         # denso EXPLÍCITO
        head, body = resto[1:].split("\n", 1)
        return [x == 1 for x in P.unpack_w(base64.b64decode(body), 1, int(head))]
    body = resto[1:]                                  # core (sem '~')
    return [s == "true" for s in (decode(body) if body else [])]


def g2_enc(bits, modo):
    if modo == "core":
        return f"{TAG}\n{corpo_core(bits)}"
    return f"{TAG}{len(bits)}\n{corpo_denso_raw(bits)}"


def g2_dec(wire):
    resto = wire[len(TAG):][1:] if wire[len(TAG):].startswith("\n") else wire[len(TAG):]
    # deduz: se comeca com digito no header -> denso (n prefixado); senao core
    head = wire[len(TAG):]
    if head[:1].isdigit():                            # n no header -> denso
        h, body = head.split("\n", 1)
        return [x == 1 for x in P.unpack_w(base64.b64decode(body), 1, int(h))]
    body = head[1:] if head.startswith("\n") else head
    return [s == "true" for s in (decode(body) if body else [])]


def g3_enc(bits, modo):
    if modo == "core":
        return f"{TAG}\n{corpo_core(bits)}"
    return f"{TAG}\n{corpo_denso_embed(bits)}"


def g3_dec_shape(wire):
    """G3: SEM marcador. Deduz o modo pela FORMA do corpo (parece base64 puro -> denso)."""
    body = wire[len(TAG) + 1:]
    if parece_base64_puro(body) and not tem_marcadores_hcc(body):
        raw = base64.b64decode(body.rstrip("\n"))
        n, i = _read_varint(raw)
        return [x == 1 for x in P.unpack_w(raw[i:], 1, n)]
    return [s == "true" for s in (decode(body) if body else [])]


# ------------------------------------------------------------------------------- datasets
def _lcg(n, pct, seed):
    s, out = seed, []
    for _ in range(n):
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        out.append((s % 100) < pct)
    return out


def datasets():
    return [
        ("n1-true", [True]),                          # COLISÃO potencial: core = 'true' (base64-limpo!)
        ("n1-false", [False]),                        # core = 'false' (base64-limpo!)
        ("n2-alt", [True, False]),                    # core multi-linha
        ("all-true", [True] * 8),                     # core = '*8|true' (tem '*' -> nao-base64)
        ("n8-alt", [bool(i % 2) for i in range(8)]),  # fronteira de padding (8 bits = 1 byte)
        ("n9-alt", [bool(i % 2) for i in range(9)]),  # 9 bits = 2 bytes (padding)
        ("p50-64", _lcg(64, 50, 23)),                 # denso favorável
        ("runs-64", [True] * 40 + [False] * 24),      # core/RLE favorável
    ]


def rodar():
    ct = ["# Ciclo B — o marcador de modo `~` é necessário, ou a ausência é inferível?\n",
          "Duas coisas separadas (owner): (1) DECISÃO de modo = FLOOR (outro ticket); (2) GRAMÁTICA "
          "= ESTE lab. Três candidatas: **G1** `~<n>` explícito · **G2** sem `~`, n no header (deduz "
          "por dígito) · **G3** sem `~` e sem n no header (n embutido no base64, deduz por FORMA).\n"]

    # ---- 1. os corpos + a forma (é distinguível por inspeção?) ----
    ct.append("## 1. Os corpos e a FORMA (o modo é distinguível por inspeção?)\n")
    ct.append("| dataset | n | corpo core | corpo denso(raw) | core parece base64? | core tem marcador HCC? |")
    ct.append("|---|---:|---|---|:---:|:---:|")
    colisoes = []
    for did, bits in datasets():
        cc = corpo_core(bits)
        cd = corpo_denso_raw(bits)
        pb = parece_base64_puro(cc)
        mk = tem_marcadores_hcc(cc)
        if pb and not mk:
            colisoes.append((did, cc))                # core que se DISFARÇA de denso
        ct.append(f"| {did} | {len(bits)} | `{cc!r}` | `{cd!r}` | {'⚠️ SIM' if pb else 'não'} | "
                  f"{'sim' if mk else 'não'} |")
    ct.append(f"\n**Colisões de forma: {len(colisoes)}** — corpos CORE que passam por base64 puro "
              "(sem marcador HCC), logo indistinguíveis de um corpo denso SÓ pela forma:")
    for did, cc in colisoes:
        ct.append(f"- `{did}`: corpo core = `{cc!r}` — é alfabeto base64 puro, 1 linha. "
                  f"`base64.decode` daria bytes; a dedução por forma erraria.")

    # ---- 2. n é dedutível? ----
    ct.append("\n## 2. `n` (contagem) é dedutível em cada modo?\n")
    ct.append("- **core**: `n` = nº de linhas do corpo (após expandir RLE). **DEDUZÍVEL** de graça.")
    ct.append("- **denso raw**: base64 de `ceil(n/8)` bytes → dado B bytes, `n ∈ [8(B-1)+1, 8B]` "
              "(8 valores possíveis pelo padding). **NÃO-dedutível** — `n` TEM que viajar.")
    for B, lo, hi in [(1, 1, 8), (8, 57, 64), (9, 65, 72)]:
        ct.append(f"  - {B} byte(s) de payload → n pode ser {lo}..{hi} (ambíguo). Ex.: p50-64 "
                  "empacota em 8 bytes; sem `n`, 57..64 são consistentes.")
    ct.append("- **denso embed (G3)**: `n` vai como varint DENTRO do base64 → self-contained, "
              "**dedutível do payload**. Custo: +1..2 bytes de varint (antes do base64).")

    # ---- 3. RT das três gramáticas + onde falham ----
    ct.append("\n## 3. RT das três gramáticas (e onde a dedução QUEBRA)\n")
    ct.append("| dataset | G1 (~ explícito) | G2 (n-header, sem ~) | G3 (embed, deduz forma) |")
    ct.append("|---|:---:|:---:|:---:|")
    falhas = {"G1": 0, "G2": 0, "G3": 0}
    for did, bits in datasets():
        # modo escolhido = FLOOR simplificado (o menor entre core e denso), pra amostrar os dois
        modo = "denso" if len(corpo_denso_raw(bits)) < len(corpo_core(bits)) else "core"
        row = [did]
        for gid, enc, dec in [("G1", g1_enc, g1_dec), ("G2", g2_enc, g2_dec), ("G3", g3_enc, g3_dec_shape)]:
            try:
                w = enc(bits, "core" if modo == "core" else "denso")
                back = dec(w)
                ok = (back == bits)
            except Exception as e:
                ok, back = False, f"ERRO {type(e).__name__}"
            falhas[gid] += (not ok)
            row.append(f"{'✅' if ok else '❌'}({modo[0]})")
            (INT / f"{did}-{gid}.tcfp").write_text(enc(bits, "core" if modo == "core" else "denso"),
                                                   encoding="utf-8", newline="")
        ct.append("| " + " | ".join(row) + " |")

    # também: força DENSO em TODOS (inclusive colisões) pra estressar a dedução do G3
    ct.append("\n### Estresse do G3 — FORÇANDO denso em todos (inclui as colisões):\n")
    ct.append("| dataset | wire G3 (denso forçado) | dedução acerta o modo? | RT |")
    ct.append("|---|---|:---:|:---:|")
    g3_stress_fail = 0
    for did, bits in datasets():
        w = g3_enc(bits, "denso")
        body = w[len(TAG) + 1:]
        deduz_denso = parece_base64_puro(body) and not tem_marcadores_hcc(body)
        back = g3_dec_shape(w)
        ok = (back == bits)
        g3_stress_fail += (not ok)
        ct.append(f"| {did} | `{w[:38]!r}...` | {'denso✅' if deduz_denso else 'core❌'} | "
                  f"{'✅' if ok else '❌'} |")

    # ---- 4. O TESTE DECISIVO: forçar CORE nas colisões sob G3 (a dedução deve QUEBRAR) ----
    ct.append("\n## 4. DECISIVO — forçando CORE nas colisões (G3 sem marcador deve QUEBRAR)\n")
    ct.append("> O 8/8 acima é enganoso: nas colisões (`n1-true`/`false`) o FLOOR escolheu DENSO, "
              "então o corpo core nunca foi emitido. Aqui FORÇO core e testo se o G3 (deduz por forma) "
              "ainda acerta — é onde a ausência de marcador falha.\n")
    ct.append("| dataset | wire G3 core forçado | G3 deduz | G3 RT | G1 (`~`) RT |")
    ct.append("|---|---|:---:|:---:|:---:|")
    g3_core_fail = g1_core_fail = 0
    for did, bits in datasets():
        w3 = g3_enc(bits, "core")                     # core, SEM marcador
        body = w3[len(TAG) + 1:]
        deduz = "denso" if (parece_base64_puro(body) and not tem_marcadores_hcc(body)) else "core"
        try:
            back3 = g3_dec_shape(w3)
            ok3 = (back3 == bits)
        except Exception as e:                        # dedução errada -> crash = corrupção dura
            ok3 = False
            back3 = f"CRASH {type(e).__name__}"
        g3_core_fail += (not ok3)
        w1 = g1_enc(bits, "core")                     # G1: core sem '~' -> inambíguo
        ok1 = (g1_dec(w1) == bits)
        g1_core_fail += (not ok1)
        marca = " ⬅️ COLISÃO" if deduz == "denso" else ""
        ct.append(f"| {did} | `{w3!r}` | {deduz}{marca} | {'✅' if ok3 else '❌ CORROMPE'} | "
                  f"{'✅' if ok1 else '❌'} |")
    ct.append(f"\n**G3 (sem marcador) corrompe {g3_core_fail}/{len(datasets())}** quando o FLOOR escolhe "
              f"core num corpo base64-limpo. **G1 (`~`) acerta {len(datasets())-g1_core_fail}/{len(datasets())}** "
              "— o marcador remove a ambiguidade por construção.")

    ct.append("\n## Leitura (pra você inspecionar)\n")
    ct.append(f"- **A resposta à sua pergunta**: a ausência do marcador **NÃO** pode ser sempre "
              f"entendida como implícita. O modo core-vs-denso NÃO é distinguível pela forma em "
              f"{len(colisoes)} casos ({', '.join(c[0] for c in colisoes)}): o corpo core de bool "
              "pequeno (`true`/`false`) é alfabeto base64 puro, indistinguível de um payload denso.")
    ct.append(f"- **Prova (seção 4)**: forçando core nas colisões, o **G3 (sem marcador) corrompe** — "
              "a dedução por forma lê `true` como base64 e devolve lixo. O **G1 (`~`) nunca corrompe**.")
    ct.append("- **E o `n` do denso não é dedutível** (padding) — algo tem que carregá-lo (o `~<n>` do "
              "G1, ou o varint embutido do G3). Então nem o denso 'de graça' escapa de carregar info.")
    ct.append("- **Conclusão pra decidir** (não é decisão): o marcador (ou um disambiguador equivalente) "
              "é **necessário na gramática completa** — a menos que se aceite ACOPLAR a gramática à "
              "heurística (denso só quando vence ⇒ nunca nos N pequenos base64-limpos), o que é frágil "
              "e mistura as duas coisas que você pediu pra separar. O caminho limpo: manter o `~` "
              "explícito no wire denso; a implicitude fica no CORE (modo A sem marcador, o default).")
    ct.append("- **Assimetria elegante**: o modo A (core) É o implícito (sem marcador, deduzido por "
              "exclusão como no header); o modo B (denso) é a EXCEÇÃO opt-in que se declara com `~`. "
              "Implícito = o comum; explícito = o desvio. Consistente com o resto do formato.")
    ct.append(f"\n---\n**RT: G1={len(datasets())-falhas['G1']}/{len(datasets())} · "
              f"G2={len(datasets())-falhas['G2']}/{len(datasets())} · "
              f"G3={len(datasets())-falhas['G3']}/{len(datasets())} (FLOOR) · "
              f"G3 core-forçado corrompe {g3_core_fail}/{len(datasets())} · "
              f"G1 core-forçado {len(datasets())-g1_core_fail}/{len(datasets())}.** "
              "Artefatos: `intermediates/*.tcfp`. Regenera: `python run.py`.\n")

    for did, bits in datasets():
        (INP / f"{did}-fonte.json").write_text(json.dumps(bits), encoding="utf-8")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · colisoes de forma={len(colisoes)} · RT G1/G2/G3 falhas={falhas} · G3-estresse falhas={g3_stress_fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(rodar())

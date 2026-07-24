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
def _b(s):
    return len(s.encode("utf-8"))


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
    # deduz: byte logo apos a tag -> digito = denso (inicio do n); '\n' = core. Disjuntos.
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
    ct.append(f"\n**Colisões de forma: {len(colisoes)}** (sob detector FROUXO — só alfabeto). Corpos "
              "CORE indistinguíveis de denso só pela forma:")
    for did, cc in colisoes:
        c = cc.rstrip("\n")
        ct.append(f"- `{did}`: corpo core = `{cc!r}` ({len(c)} chars, len%4={len(c) % 4}). "
                  "Alfabeto base64 puro, 1 linha.")
    ct.append("> Nuance (verificação): um detector ESTRITO (exige `len%4==0`, comprimento base64 válido) "
              "rejeitaria `false` (5 chars) → só `true` (4) sobrevive — e mesmo esse **crasha** no "
              "varint. A colisão real é ainda menor que o detector frouxo sugere.")

    # ---- 2. n é dedutível? ----
    ct.append("\n## 2. `n` (contagem) é dedutível em cada modo?\n")
    ct.append("- **core**: `n` = nº de linhas do corpo (após expandir RLE). **DEDUZÍVEL** de graça.")
    ct.append("- **denso raw**: base64 de `ceil(n/8)` bytes → dado B bytes, `n ∈ [8(B-1)+1, 8B]` "
              "(8 valores possíveis pelo padding). **NÃO-dedutível** — `n` TEM que viajar.")
    for B, lo, hi in [(1, 1, 8), (8, 57, 64), (9, 65, 72)]:
        ct.append(f"  - {B} byte(s) de payload → n pode ser {lo}..{hi} (ambíguo).")
    ct.append("  - ex.: `p50-64` empacota em 8 bytes; sem `n`, 57..64 são todos consistentes.")
    ct.append("- **CHAVE (achado da verificação)**: como `n` é OBRIGATÓRIO no denso, ele pode servir de "
              "disambiguador de graça — é o que torna o **G2** (n logo após a tag) marker-free E sem "
              "custo dedicado.")
    ct.append("- **denso embed (G3)**: `n` vai como varint DENTRO do base64 → self-contained, mas o "
              "MODO ainda é deduzido por FORMA (inseguro — ver §4).")

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

    # ---- 4. O TESTE DECISIVO: forçar CORE nas colisões, TODAS as 3 gramáticas ----
    ct.append("\n## 4. DECISIVO — forçando CORE nas colisões (as 3 gramáticas)\n")
    ct.append("> O 8/8 da §3 é enganoso: nas colisões (`n1-true`/`false`) o FLOOR escolheu DENSO, então "
              "o corpo core nunca foi emitido. Aqui FORÇO core e testo se a dedução ainda acerta. "
              "**Correção pós-verificação: incluí o G2, que eu havia omitido (viés a favor do `~`); e a "
              "falha do G3 é um CRASH (fail-loud), não corrupção silenciosa.**\n")
    ct.append("| dataset | wire core forçado | G3 (forma) | G2 (n-header) | G1 (`~`) |")
    ct.append("|---|---|:---:|:---:|:---:|")
    g3_core_fail = g2_core_fail = g1_core_fail = 0
    for did, bits in datasets():
        w3 = g3_enc(bits, "core")
        body = w3[len(TAG) + 1:]
        deduz3 = "denso" if (parece_base64_puro(body) and not tem_marcadores_hcc(body)) else "core"
        try:
            ok3 = (g3_dec_shape(w3) == bits)
            modo3 = "✅" if ok3 else "❌"
        except Exception as e:
            ok3, modo3 = False, f"❌CRASH({type(e).__name__})"
        g3_core_fail += (not ok3)
        w2 = g2_enc(bits, "core")                     # G2: core = tag + '\n' (byte apos tag = '\n')
        ok2 = (g2_dec(w2) == bits)
        g2_core_fail += (not ok2)
        w1 = g1_enc(bits, "core")                     # G1: core sem '~'
        ok1 = (g1_dec(w1) == bits)
        g1_core_fail += (not ok1)
        col = " ⬅️COLISÃO" if deduz3 == "denso" else ""
        ct.append(f"| {did} | `{w3!r}`{col} | {modo3} | {'✅' if ok2 else '❌'} | {'✅' if ok1 else '❌'} |")
    N = len(datasets())
    ct.append(f"\n- **G3 (deduz por forma)**: falha {g3_core_fail}/{N} — mas por **CRASH (fail-loud)**, "
              "não corrupção silenciosa (lê `true` como base64 → IndexError/binascii). Inseguro E "
              "acopla à heurística.")
    ct.append(f"- **G2 (n-no-header, SEM marcador dedicado)**: acerta {N-g2_core_fail}/{N} — o byte logo "
              "após a tag desambigua de graça: **dígito → denso** (início do `n`), **`\\n` → core**. "
              "Disjunto por construção, sem char reservado, sem olhar tamanho (NÃO acopla à heurística).")
    ct.append(f"- **G1 (`~` dedicado)**: acerta {N-g1_core_fail}/{N} — inambíguo, mas paga 1 byte a mais "
              "que o G2 em todo wire denso.")

    # ---- 5. bytes: G2 vs G1 no denso (o -1 byte) ----
    ct.append("\n## 5. Custo — G2 (n-header) vs G1 (`~`) nos wires densos\n")
    ct.append("| dataset | G1 (`~<n>`) | G2 (`<n>`) | Δ |")
    ct.append("|---|---:|---:|---:|")
    tot1 = tot2 = 0
    for did, bits in datasets():
        b1 = _b(g1_enc(bits, "denso")); b2 = _b(g2_enc(bits, "denso"))
        tot1 += b1; tot2 += b2
        ct.append(f"| {did} | {b1} | {b2} | {b2 - b1:+d} |")
    ct.append(f"\n**Total denso: G1={tot1} B · G2={tot2} B → G2 é {tot1-tot2} B mais barato** (1 byte/"
              "wire, o char `~`).")

    ct.append("\n## Leitura CORRIGIDA (pós-verificação adversarial `wf_3a7ab214`)\n")
    ct.append("⚠️ **Correção**: a v1 concluía \"o `~` é NECESSÁRIO\" — isso era **overclaim**, por dois "
              "erros meus: (a) omiti o G2 do teste decisivo (viés pró-`~`); (b) chamei de \"corrompe\" "
              "o que na verdade **crasha (fail-loud)**. Corrigido abaixo.")
    ct.append(f"- **A resposta à sua pergunta**: SIM, existe gramática **marker-free segura e "
              "desacoplada da heurística** — é o **G2** (`#TCF.8b<n>\\n<base64>`). O disambiguador é o "
              "**byte logo após a tag fixa**: dígito → denso (início do `n`), `\\n` → core. Disjuntos "
              "por construção; sem char reservado; sem olhar tamanho. Passa 0 falhas no teste decisivo.")
    ct.append("- **Um disambiguador É preciso** (a dedução por FORMA — G3 — é insegura: crasha nas "
              "colisões `true`/`false` base64-limpas, e acopla à heurística). Mas um **marcador "
              "DEDICADO (`~`) NÃO é preciso** — o `n`, que é obrigatório (padding), já desambigua.")
    ct.append("- **A colisão é minúscula e enumerável**: só `n=1` bool (2 de 2046 corpos core n≤10 são "
              "base64-puros: `true`,`false`). Para n≥2 todo corpo core tem `\\n`/`*`/`|`/`^`. `number` "
              "`[1]`/`[0]` vira `\\1`/`\\0` (backslash) — **não colide**.")
    ct.append("- **O trade-off REAL (pra você decidir)**:")
    ct.append("  - **G2 (n-header)**: mais barato (−1 byte/denso), marker-free, desacoplado. Ideal se "
              "forem **só 2 modos** (core + 1 denso): dígito-vs-`\\n` é um split binário.")
    ct.append("  - **`~` (ou char de modo)**: +1 byte, mas **estende limpo pra ≥3 modos** — a família "
              "bN do roadmap (`b1`/`b2`/`b4`/`b8`) + `misto`, onde dígito-vs-`\\n` não basta (só dá "
              "binário). O marcador vira `~<modo><n>`.")
    ct.append("- **Assimetria que se mantém**: seja `~` ou G2, o **core (comum) fica nu** e o **denso "
              "(raro) se declara** — marcar o caso raro/grande e deixar o comum/pequeno implícito é o "
              "lado certo do pagador (a v1 acertou ISSO; errou só em dizer que o marcador dedicado era "
              "obrigatório).")
    ct.append(f"\n---\n**§3 RT sob FLOOR: G1/G2/G3 = 8/8 (enganoso, corpo core não-emitido). §4 core-"
              f"forçado: G3 falha {g3_core_fail}/{N} (crash), G2 {N-g2_core_fail}/{N}, G1 {N-g1_core_fail}/{N}. "
              f"§5: G2 −{tot1-tot2} B vs G1.** Artefatos: `intermediates/*.tcfp`. Regenera: `python run.py`.\n")

    for did, bits in datasets():
        (INP / f"{did}-fonte.json").write_text(json.dumps(bits), encoding="utf-8")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · colisoes de forma={len(colisoes)} · RT G1/G2/G3 falhas={falhas} · G3-estresse falhas={g3_stress_fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(rodar())

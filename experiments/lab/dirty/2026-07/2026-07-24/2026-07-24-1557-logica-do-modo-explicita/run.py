#!/usr/bin/env python3
"""A lógica do `~` (modo) — forma EXPLÍCITA (o `var` visível), referência do weld #4.

Direção do owner (2026-07-24): tudo isto JÁ EXISTE e é aplicado (o FLOOR/`min` no multi/core.py, a
dispatch posicional no decoder.py) — só nomeamos as etapas. Codificar na forma GERAL/EXPLÍCITA, com a
variável de decisão VISÍVEL:

    lógica geral (o que codamos AGORA):        otimizada (trabalho do .9/compilador):
      var = <default>                            if (cond) then função_var
      if (cond) then var = <x>
      if var then função_var

A variável escondida de decisão (`var` = o "modo", o conceito do `~`) **existe conceitualmente sempre**.
No wire ela NÃO aparece (categoria 4: preenchível por posição). No código ela é EXPLÍCITA — a função é
acionada PELA VARIÁVEL, não pelo caractere. O `~` nunca é byte; é o nome (livre) dessa variável.

Este protótipo implementa encode/decode do single-col TIPADO com a variável `modo` explícita, RT nos
perfis de bool. Mapeia 1:1 pro weld #4: encode = ramo no dispatch (encoder.py); decode = ramo no
discriminador (decoder.py). NÃO toca src/tcf. `python run.py`.
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
import pecas as P  # noqa: E402  (pack_w/unpack_w — os dois algoritmos ja' existem)
from tcf import encode as _core_encode, decode as _core_decode  # noqa: E402

INP, INT, OUT = AQUI / "inputs", AQUI / "intermediates", AQUI / "outputs"
for d in (INP, INT, OUT):
    d.mkdir(exist_ok=True)

MAGIC = "#TCF.8"

# ---- registry (camada 2: SIGNIFICADO — char de modo -> largura). Namespace do <modo>. ----
# Tudo isto e' o "map char->significado"; o '~' nao entra aqui: ele nunca e' byte.
LARGURA_DE_MODO = {"1": 1, "2": 2, "4": 4, "8": 8}          # 1/2/4/8 = largura fisica (funciona)
MODO_DE_LARGURA = {w: c for c, w in LARGURA_DE_MODO.items()}
# subtipos (letras/outros digitos) = PREPARADO, nao construido (hook do .9)

TAG_TIPO = {"b": bool, "n": "number", "s": str}            # whitelist fechada (camada 2 da TAG)


# ---- renderer/caster de TIPO (a semantica NAO some — o tipo volta) ----
def render(values, tag):
    if tag == "b":
        return ["true" if v else "false" for v in values]
    if tag == "n":
        return [repr(v) if isinstance(v, float) else str(v) for v in values]
    return [str(v) for v in values]


def restaura(strs, tag):
    if tag == "b":
        return [s == "true" for s in strs]
    if tag == "n":
        return [float(s) if ("." in s or "e" in s.lower()) else int(s) for s in strs]
    return list(strs)


def cardinalidade(values):
    return len(dict.fromkeys(values))


def _b(s):
    return len(s.encode("utf-8"))


# ============================ ENCODE — a logica GERAL, com o `var` EXPLICITO ============
def encode_typed(values, tag):
    n = len(values)
    # --- os DOIS ALGORITMOS (ja' existem) ---
    #  A) core/text: reusa o compressor de coluna do core (seq-RLE/aliases de graca)
    corpo_core = _core_encode(render(values, tag)) if values else ""
    wire_core = f"{MAGIC}{tag}\n{corpo_core}"
    #  B) denso bN: bit-pack a `w` bits -> base64. w vem da cardinalidade.
    w = P.width_for(cardinalidade(values)) if values else 1
    if w in MODO_DE_LARGURA and values:
        idx = _indices(values, tag)
        corpo_denso = base64.b64encode(P.pack_w(idx, w)).decode("ascii")
        wire_denso = f"{MAGIC}{tag}{MODO_DE_LARGURA[w]}{n}\n{corpo_denso}"
    else:
        wire_denso = None

    # --- A VARIAVEL DE DECISAO EXPLICITA (o `var` = modo; o conceito do `~`) ---
    #     lógica geral: var = core (default); if denso menor -> var = denso.
    modo = "core"                                          # default (implicito no wire)
    if wire_denso is not None and _b(wire_denso) < _b(wire_core):
        modo = "denso"                                     # FLOOR/min (o padrao que ja' existe)

    # --- a funcao e' acionada PELA VARIAVEL, nao pelo caractere ---
    if modo == "core":
        return wire_core
    return wire_denso


def _indices(values, tag):
    # dominio IMPLICITO exige convencao FIXA (canonica), nao ordem de aparicao — senao o dominio
    # teria que viajar. p/ bool: false=0, true=1 SEMPRE (independe de quem aparece primeiro).
    if tag == "b":
        return [1 if v else 0 for v in values]
    dom = list(dict.fromkeys(values))                      # n/s: dominio embutido (fora do escopo bool)
    ix = {v: i for i, v in enumerate(dom)}
    return [ix[v] for v in values]


# ============================ DECODE — a variavel deduzida da POSICAO, mas NOMEADA ======
def decode_typed(wire):
    assert wire.startswith(MAGIC)
    tag = wire[6:7]                                        # camada 1->2: char da tag -> tipo
    if tag not in TAG_TIPO:
        raise ValueError(f"tag de tipo desconhecida: {tag!r} (whitelist {sorted(TAG_TIPO)})")
    c7 = wire[7:8]                                         # o byte de fronteira (indice 7)

    # --- A VARIAVEL DE DECISAO EXPLICITA (deduzida da posicao — o `var` escondido, agora nomeado) ---
    #     lógica geral: modo = core (default); if c7 e' char de modo -> modo = <largura>.
    #     Aqui o '~' NAO existe como byte; existe como esta variavel `modo`.
    if c7 == "\n":
        modo = "core"
    elif c7 in LARGURA_DE_MODO:
        modo = LARGURA_DE_MODO[c7]                          # largura (int)
    else:
        raise ValueError(f"byte de modo invalido no indice 7: {c7!r}")

    # --- a funcao e' acionada PELA VARIAVEL ---
    if modo == "core":
        corpo = wire[len(MAGIC) + 2:]                       # apos "#TCF.8<tag>\n"
        strs = _core_decode(corpo) if corpo else []
        return restaura(strs, tag)
    # denso: le n (digitos ate '\n'), depois base64
    resto = wire[len(MAGIC) + 2:]                           # apos "#TCF.8<tag><modo>"
    ndig, _, corpo = resto.partition("\n")
    n = int(ndig)
    idx = P.unpack_w(base64.b64decode(corpo), modo, n)
    dom_strs = render(_dom_bool(tag, modo), None) if False else None  # dominio implicito p/ bool
    return _idx_para_tipo(idx, tag)


def _idx_para_tipo(idx, tag):
    if tag == "b":
        return [i == 1 for i in idx]                       # dominio implicito {false=0, true=1}
    raise NotImplementedError("denso p/ n/s exigiria dominio embutido — fora do escopo bool")


def _dom_bool(tag, modo):
    return None


# ================================================================= perfis + RT
def _lcg(n, pct, seed):
    s, out = seed, []
    for _ in range(n):
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        out.append((s % 100) < pct)
    return out


def perfis():
    N = 64
    return [
        ("all-true", [True] * N), ("all-false", [False] * N),
        ("alt", [bool(i % 2) for i in range(N)]),
        ("runs", [True] * 40 + [False] * 24),
        ("p10", _lcg(N, 10, 11)), ("p50", _lcg(N, 50, 23)), ("p90", _lcg(N, 90, 37)),
        ("n1", [True]),
    ]


def rodar():
    ct = ["# A lógica do `~` (modo) — forma EXPLÍCITA (o `var` visível)\n",
          "Tudo já existe (FLOOR/`min`, dispatch posicional) — só nomeamos as etapas. Codado na forma "
          "GERAL/explícita (variável `modo` visível no encode E no decode). O `~` NÃO é byte de wire; é "
          "essa variável. A função é acionada PELA VARIÁVEL. Otimização (colapsar o `var`) = `.9`.\n",
          "| perfil | n | wire (linha-0) | modo (var) | bytes | RT-tipado |",
          "|---|---:|---|:---:|---:|:---:|"]
    falhas = 0
    for pid, vals in perfis():
        (INP / f"{pid}-fonte.json").write_text(json.dumps(vals), encoding="utf-8")
        (INT / f"{pid}-dataset-consumido.json").write_text(json.dumps(vals), encoding="utf-8")
        wire = encode_typed(vals, "b")
        back = decode_typed(wire)
        ok = (back == vals)
        falhas += (not ok)
        (OUT / f"{pid}-wire.tcfp").write_text(wire, encoding="utf-8", newline="")
        (OUT / f"{pid}-roundtrip.json").write_text(json.dumps(back), encoding="utf-8")
        l0 = wire.split("\n", 1)[0]
        var = "core" if wire[7:8] == "\n" else f"denso(w={LARGURA_DE_MODO.get(wire[7:8],'?')})"
        ct.append(f"| {pid} | {len(vals)} | `{l0}` | {var} | {_b(wire)} | {'✅' if ok else '❌'} |")

    ct.append("\n## As etapas nomeadas (o que o código mostra)\n")
    ct.append("- **camada 1 — caractere**: o byte no índice 6 (tag) e no índice 7 (fronteira de modo).")
    ct.append("- **camada 2 — significado**: `tag→tipo` (`b`→bool) e `char→largura` (`1`→w=1). Registros "
              "`TAG_TIPO`, `LARGURA_DE_MODO`. O `~` NÃO está aqui (nunca é byte).")
    ct.append("- **camada 3 — presença/decisão**: a variável `modo`. No ENCODE ela é o FLOOR "
              "(`var=core; if denso menor→var=denso`). No DECODE ela é deduzida da posição "
              "(`if c7=='\\n'→core; elif c7 é largura→denso`). **É o `var` explícito — o `~` conceitual.**")
    ct.append("- **função**: acionada PELA variável `modo`, não pelo caractere (`if modo==core → decode "
              "core; else → decode denso`).")
    ct.append("\n## Mapa pro weld #4 (1:1)\n")
    ct.append("- `encode_typed` → ramo no dispatch de `encoder.py` (antes do `.8H`), reusando "
              "`_encode_column` (core) e o pack bN. A variável `modo` = o FLOOR que já existe.")
    ct.append("- `decode_typed` → ramo no discriminador de `decoder.py`: hoje `disc8 not in (M, ,'')` é "
              "fail-loud; add `elif tag in whitelist`. A variável `modo` = a dispatch posicional que já existe.")
    ct.append("- **Explícito agora, íntimo no `.9`**: mantemos `modo` visível; a fusão (colapsar o `var` "
              "na condição) fica pro `.9`/compilador — em código ajudamos só se o compilador limitar.")
    ct.append("- **Escopo do protótipo**: bool (`w=1`, domínio implícito). n/s densos exigem domínio "
              "embutido (fora daqui). Larguras 2/4/8 e subtipos = namespace preparado, não exercido.")
    ct.append(f"\n---\n**{len(perfis())} perfis · {falhas} falhas de RT-tipado.** Artefatos: `inputs/` · "
              "`intermediates/` · `outputs/*-wire.tcfp`. Regenera: `python run.py`.\n")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · {len(perfis())} perfis · {falhas} falhas de RT-tipado")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

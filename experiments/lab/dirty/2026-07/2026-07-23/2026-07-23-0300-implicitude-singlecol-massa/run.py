#!/usr/bin/env python3
"""Massa single-column por TIPO — baseline do comportamento ATUAL + equivalência JSON.

Testa a "regra de implicitude" (nota 2026-07-23-0259): numa coluna única, lista/count/estrutura
são implícitos; só o TIPO é irredutível. String já é o default implícito (órfão, 0 B header);
number/bool/null caem hoje no `.8H` (envelope #V + \\z + #count + []); specs = nature single-col.

Pra cada tipo: encode -> wire real · decode -> RT · EQUIVALÊNCIA JSON (RT do TCF == RT do JSON,
mesmo objeto Python) · bytes total vs body-dos-elementos (quantifica o OVERHEAD que um single-col
tipado arrancaria). NÃO muda src/tcf — é medição da baseline antes de qualquer código.

`python run.py` regenera inputs/ outputs/ + result.md. N moderado (massa, mas rápido).
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[5]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode, SideOutputs, SPEC_CPF, SPEC_CNPJ, SPEC_IP  # noqa: E402

INP, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (INP, OUT):
    d.mkdir(exist_ok=True)

N = 500
RNG = random.Random(20260723)


def cpfs(n):  # placeholders seguros (dígitos repetidos mod-11-válidos), reciclados
    base = ["111.111.111-11", "222.222.222-22", "333.333.333-33", "444.444.444-44"]
    return [base[i % len(base)] for i in range(n)]


def cnpjs(n):
    base = ["11.222.333/0001-81", "11.444.777/0001-61"]      # synthetic DV-válido
    return [base[i % len(base)] for i in range(n)]


def ips(n):
    return [f"10.{(i // 65536) % 255}.{(i // 256) % 255}.{i % 255}" for i in range(n)]


# ---- os casos: (id, tipo_logico, desc, lista, kwargs) ----
def casos():
    C = []
    a = lambda *x: C.append(x)
    # STRING (default IMPLÍCITO — órfão)
    a("str-email", "string", "emails c/ sufixo compartilhado (prefix/suffix OBAT)",
      [f"user{i:04d}@empresa.com.br" for i in range(N)], {})
    a("str-lowcard", "string", "3 valores repetidos (baixa cardinalidade)",
      [["ativo", "inativo", "pendente"][i % 3] for i in range(N)], {})
    a("str-uuid", "string", "hex alta-cardinalidade (quase incompressível)",
      [f"{(i * 2654435761) & 0xFFFFFFFF:08x}" for i in range(N)], {})
    a("str-freetext", "string", "texto livre variado",
      [f"registro numero {i} com descricao {RNG.choice(['alfa','beta','gama','delta'])}" for i in range(N)], {})
    # NUMBER (hoje -> .8H tipado)
    a("int-seq", "number", "inteiros SEQUENCIAIS 0..N (seq-RLE +1)", list(range(N)), {})
    a("int-rand", "number", "inteiros aleatórios", [RNG.randrange(1_000_000) for _ in range(N)], {})
    a("int-repeat", "number", "inteiro repetido (1 valor)", [42] * N, {})
    a("int-big", "number", "inteiros grandes (> 2^53? não — dentro do JSON)", [10 ** 12 + i for i in range(N)], {})
    a("float-dec", "number", "floats decimais", [round(i / 7, 4) for i in range(N)], {})
    # BOOL / NULL
    a("bool-alt", "bool", "booleanos alternados", [bool(i % 2) for i in range(N)], {})
    a("null-all", "null", "todos null", [None] * N, {})
    # SPECS (nature single-col -> #TCF.8 :id, FLOOR)
    a("spec-cpf", "spec:cpf", "CPFs (nature CPF single-col)", cpfs(N), {"nature": SPEC_CPF})
    a("spec-cnpj", "spec:cnpj", "CNPJs (nature CNPJ single-col)", cnpjs(N), {"nature": SPEC_CNPJ})
    a("spec-ip", "spec:ip", "IPs (nature IP single-col)", ips(N), {"nature": SPEC_IP})
    return C


def _forma(wire):
    l0 = wire.split("\n", 1)[0]
    if not wire.startswith("#TCF."):
        return "órfão (0 B header)"
    if l0.startswith("#TCF.8H"):
        return f"#TCF.8H ({'#'+l0[8:9] if l0[7:8]=='#' else 'dataset'})"
    if l0.startswith("#TCF.8 "):
        return f"#TCF.8 nature ({l0[6:].strip()})"
    if l0.startswith("#TCF.8M"):
        return "#TCF.8M"
    return l0[:14]


def rodar():
    ct = ["# Single-column em massa por TIPO — baseline atual + equivalência JSON\n",
          f"N = {N} elementos por caso. Mede o wire ATUAL, o RT (== JSON), e o OVERHEAD estrutural "
          "(bytes que NÃO são os elementos) — o que um single-col tipado arrancaria.\n",
          "| caso | tipo | forma do wire | total B | elems B | overhead B | B/elem | RT=JSON |",
          "|---|---|---|---:|---:|---:|---:|:---:|"]
    falhas = 0
    for (cid, tipo, desc, lst, kw) in casos():
        (INP / f"{cid}.json").write_text(json.dumps(lst, ensure_ascii=False), encoding="utf-8")
        so = SideOutputs()
        wire = encode(lst, side_outputs=so, **kw)
        (OUT / f"{cid}.tcf").write_text(wire, encoding="utf-8", newline="")
        back = decode(wire)
        # EQUIVALÊNCIA JSON: o RT do TCF e o RT do JSON dão o MESMO objeto Python
        json_rt = json.loads(json.dumps(lst))
        equiv = (back == lst == json_rt)
        falhas += (not equiv)
        (OUT / f"{cid}.roundtrip.json").write_text(json.dumps(back, ensure_ascii=False), encoding="utf-8")
        total = len(wire.encode("utf-8"))
        # body dos ELEMENTOS (o que sobreviveria num single-col tipado):
        #  - órfão (string): o wire inteiro É os elementos (header 0) -> elems = total
        #  - .8H tipado: per_col[:arr_scalars].body_bytes
        #  - nature single-col: o body após o header
        elems = total
        per = getattr(so, "per_col", None) or {}
        if ":arr_scalars" in per and getattr(per[":arr_scalars"], "body_bytes", None) is not None:
            elems = per[":arr_scalars"].body_bytes
        elif wire.startswith("#TCF.8H") or wire.startswith("#TCF.8 "):
            elems = len(wire.split("\n", 1)[1].encode("utf-8")) if "\n" in wire else total
        overhead = total - elems
        ct.append(f"| {cid} | {tipo} | {_forma(wire)} | {total} | {elems} | {overhead} | "
                  f"{total/len(lst):.2f} | {'✅' if equiv else '❌'} |")

    ct.append("\n## Leitura\n")
    ct.append("- **string** (órfão): header 0 B, overhead 0 — a `list`-ness e o tipo já são "
              "IMPLÍCITOS. É o alvo de baixo-overhead que os outros tipos deveriam alcançar.")
    ct.append("- **number/bool/null** (`.8H` hoje): o `overhead B` é o custo do envelope `#V` + "
              "nome-vazio `\\z` + coluna de `#count` + `[]` — estrutura que numa coluna única é "
              "DEDUTÍVEL. Um single-col tipado (`#TCF.8:n` + body) manteria só `elems B` + ~9 B de header.")
    ct.append("- **specs**: a nature JÁ é uma coluna tipada (`#TCF.8 :id`, self-describing) — moldura "
              "candidata a unificar com o tipo primitivo.")
    ct.append("- **equivalência JSON**: RT do TCF == RT do JSON em TODOS os casos (mesmo objeto "
              "Python; tipos preservados) — datasets similares. ✅ é o gate; nunca reportar bytes sem ele.")
    ct.append(f"\n**{len(casos())} casos · {falhas} falhas de equivalência.** Regenera: `python run.py`.\n")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · {len(casos())} casos · {falhas} falhas de equivalência JSON")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

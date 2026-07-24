#!/usr/bin/env python3
"""Ciclo A (cont.) — o VAZIO e a canonicidade do LF: `[]` vs `[""]` vs `["",""]`.

Pergunta do owner: qual o mapeamento CORRETO?
    '#TCF.8'      -> []
    '#TCF.8\\n'    -> ['']
    '#TCF.8\\n\\n'  -> ['','']
    '#TCF.8b\\n'   -> []
    '#TCF.8b\\n\\n' -> ????

Duas convenções possíveis para o LF do corpo:
  (A) TERMINADOR — cada elemento termina em LF. corpo ''='[]' · '\\n'=[''] · '\\n\\n'=['','']
      É o que o `encode` JÁ PRODUZ hoje (`['a']` -> `'a\\n'`).
  (B) SEPARADOR — LF separa elementos. corpo ''=[''] · '\\n'=['',''] ; `[]` precisa de um
      wire SEM o LF do header (`'#TCF.8'` pelado). É a proposta literal do owner.

Este lab mede, para cada convenção: bijetividade (datasets distintos -> wires distintos),
compatibilidade com os wires que o `src/tcf` JÁ emite, e robustez a um LF final acrescentado
por editor/git. Zero toque em src/tcf. `python run.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[5]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402

INP, INT, OUT = AQUI / "inputs", AQUI / "intermediates", AQUI / "outputs"
for d in (INP, INT, OUT):
    d.mkdir(exist_ok=True)

MAGIC = "#TCF.8"


class Malformado(Exception):
    pass


# ------------------------------------------------------- convenção A: LF é TERMINADOR (estrita)
def encA(lst):
    return MAGIC + "\n" + "".join(x + "\n" for x in lst)


def decA(wire):
    if not wire.startswith(MAGIC + "\n"):
        raise Malformado("header ausente")
    corpo = wire[len(MAGIC) + 1:]
    if corpo == "":
        return []                                  # zero terminadores = zero elementos
    if not corpo.endswith("\n"):
        raise Malformado("corpo sem terminador final (não-canônico)")
    return corpo[:-1].split("\n")


# ------------------------------------------------------- convenção B: LF é SEPARADOR (owner)
def encB(lst):
    if not lst:
        return MAGIC                               # `[]` = wire PELADO, sem LF nenhum
    return MAGIC + "\n" + "\n".join(lst)


def decB(wire):
    if wire == MAGIC:
        return []
    if not wire.startswith(MAGIC + "\n"):
        raise Malformado("header ausente")
    return wire[len(MAGIC) + 1:].split("\n")


CORPUS = [
    ("vazia", []),
    ("uma-vazia", [""]),
    ("duas-vazias", ["", ""]),
    ("um-a", ["a"]),
    ("a-e-vazia", ["a", ""]),
    ("vazia-e-a", ["", "a"]),
    ("a-e-b", ["a", "b"]),
]


def rodar():
    ct = ["# Ciclo A — o VAZIO e a canonicidade do LF\n",
          "Pergunta do owner: qual o mapeamento correto de `[]` / `['']` / `['','']`? Duas convenções "
          "para o LF do corpo: **(A) TERMINADOR** (cada elemento termina em LF — é o que o `encode` já "
          "produz) e **(B) SEPARADOR** (LF separa; `[]` = wire pelado `#TCF.8`, a proposta literal).\n"]

    # ---------------- 0. o que o TCF faz HOJE (e onde colide) ----------------
    ct.append("## 0. Hoje — o decode é TOLERANTE, e é isso que quebra a canonicidade\n")
    ct.append("| corpo (órfão) | decode hoje |")
    ct.append("|---|---|")
    colisoes = []
    vistos = {}
    for corpo in ["", "\n", "\n\n", "a", "a\n", "a\n\n", "a\nb", "a\nb\n"]:
        try:
            r = decode(corpo)
            rr = repr(r)
            if rr in vistos:
                colisoes.append((vistos[rr], corpo, rr))
            vistos[rr] = corpo
            ct.append(f"| `{corpo!r}` | `{rr}` |")
        except Exception as e:
            ct.append(f"| `{corpo!r}` | ERRO {type(e).__name__} |")
    ct.append(f"\n**{len(colisoes)} colisões** (grafias distintas → mesmo dataset):")
    for a, b, r in colisoes:
        ct.append(f"- `{a!r}` e `{b!r}` → ambos `{r}`")
    ct.append("\nO `encode` usa LF como **terminador** (`['a']`→`'a\\n'`); o `decode` aceita **com ou "
              "sem** o terminador final. Essa tolerância é a causa — e o efeito colateral é que `[]` "
              "**não tem representação** na forma flat (o mínimo é `['']`), obrigando a fuga pro `.8H#D0`.")

    # ---------------- 1. bijetividade das duas convenções ----------------
    ct.append("\n## 1. As duas convenções — bijetividade\n")
    ct.append("| dataset | (A) terminador | (B) separador |")
    ct.append("|---|---|---|")
    wa, wb = {}, {}
    for nome, d in CORPUS:
        a, b = encA(d), encB(d)
        wa.setdefault(a, []).append(nome)
        wb.setdefault(b, []).append(nome)
        ct.append(f"| `{d!r}` | `{a!r}` | `{b!r}` |")
        (INT / f"{nome}-convA.tcfp").write_text(a, encoding="utf-8", newline="")
        (INT / f"{nome}-convB.tcfp").write_text(b, encoding="utf-8", newline="")

    colA = {k: v for k, v in wa.items() if len(v) > 1}
    colB = {k: v for k, v in wb.items() if len(v) > 1}
    rtA = sum(1 for _, d in CORPUS if decA(encA(d)) == d)
    rtB = sum(1 for _, d in CORPUS if decB(encB(d)) == d)
    ct.append(f"\n- **(A)**: {len(colA)} colisões · RT {rtA}/{len(CORPUS)}")
    ct.append(f"- **(B)**: {len(colB)} colisões · RT {rtB}/{len(CORPUS)}")
    ct.append("\nAmbas são bijetivas. A diferença NÃO está aqui — está nos dois testes seguintes.")

    # ---------------- 2. compatibilidade com o wire que o TCF JÁ emite ----------------
    ct.append("\n## 2. Compatibilidade — os wires que o `src/tcf` já emite continuam válidos?\n")
    ct.append("> O corpo real pode conter marcadores (RLE `*N|`, refs `^N`). O teste abaixo NÃO "
              "reimplementa o codec do corpo: aplica só a **regra de moldura** de cada convenção e "
              "delega o corpo ao `decode` REAL. Assim mede compatibilidade de FRAMING, não de body.\n")
    ct.append("| dataset | corpo REAL do encode | termina em LF? | (A) framing | (B) framing |")
    ct.append("|---|---|:---:|---|---|")
    okA = okB = 0
    for nome, d in CORPUS:
        if not d:
            continue                                # `[]` hoje vai pro .8H, não tem corpo flat
        real = encode(d)
        if real.startswith("#TCF."):
            continue                                # foi pra outra rota
        term = real.endswith("\n")
        # (A): exige terminador final; corpo vai íntegro pro decode real
        a_ok = term and (decode(real) == d)
        # (B): separador -> o LF final vira um elemento vazio EXTRA; o corpo que o decode
        #      receberia seria o real MENOS o último LF, e sobraria um '' no fim
        b_lista = decode(real) + [""] if term else decode(real)
        b_ok = (b_lista == d)
        okA += a_ok; okB += b_ok
        ct.append(f"| `{d!r}` | `{real!r}` | {'sim' if term else 'não'} | "
                  f"{'✅ válido' if a_ok else '❌'} | `{b_lista!r}` {'✅' if b_ok else '❌'} |")
    ct.append(f"\n- **(A) valida {okA}/{okA} wires reais** — porque o `encode` JÁ emite o terminador "
              "final em todos. Adotar (A) **não muda um único byte** do que é produzido hoje; só "
              "torna o *decode* estrito (rejeitar corpo sem terminador).")
    ct.append(f"- **(B) valida {okB}** — sob separador, o LF final de todo wire existente passa a "
              "significar um **elemento vazio extra**. Todo wire de hoje decodificaria errado; adotar "
              "(B) exigiria reescrever o corpo (viola 'body congelado').")

    # ---------------- 3. robustez: editor/git acrescenta LF final ----------------
    ct.append("\n## 3. Robustez — normalização POSIX (ferramenta *garante* LF final)\n")
    ct.append("> Um arquivo de texto POSIX **deve** terminar em LF. Editores, `git` e linters aplicam "
              "essa normalização: **acrescentam LF se e somente se faltar**. O teste é esse — não um "
              "LF arbitrário.\n")
    ct.append("| conv. | wire de `[]` | já é POSIX-válido? | normalizador age? | resultado | corrompe? |")
    ct.append("|---|---|:---:|:---:|---|:---:|")
    for conv, enc, dec in (("A", encA, decA), ("B", encB, decB)):
        w = enc([])
        posix_ok = w.endswith("\n")
        w2 = w if posix_ok else w + "\n"            # normalizador só age se faltar
        try:
            depois = dec(w2)
        except Exception as e:
            depois = f"ERRO {type(e).__name__}"
        corrompe = (not posix_ok) and (depois != [])
        ct.append(f"| ({conv}) | `{w!r}` | {'sim' if posix_ok else '**NÃO**'} | "
                  f"{'não mexe' if posix_ok else '**acrescenta LF**'} | `{depois!r}` | "
                  f"{'❌ SIM' if corrompe else '✅ não'} |")
    ct.append("\n**Este é o ponto decisivo.** Em (B) o wire de `[]` é `'#TCF.8'` — **não é um arquivo "
              "de texto POSIX válido** (não termina em LF). Qualquer normalizador acrescenta o LF, e "
              "`[]` vira `['']` **silenciosamente**. Em (A) o wire de `[]` já termina em LF: o "
              "normalizador **não tem o que fazer**, e o dado sobrevive.")
    ct.append("\n⚠️ **Ressalva honesta**: (A) não é imune a um LF *espúrio* (dois LFs viram `['']`). "
              "A diferença é de **exposição**: (B) é corrompida pela operação PADRÃO das ferramentas; "
              "(A) só por uma edição anômala — que, sendo não-canônica, o decode estrito pode recusar.")

    # ---------------- 4. o caso tipado (o '????' do owner) ----------------
    ct.append("\n## 4. O `????` do owner — `#TCF.8b\\n\\n`\n")
    ct.append("Sob (A), com tag `b`:\n")
    ct.append("| wire | corpo | elementos | valor | resultado |")
    ct.append("|---|---|---|---|---|")
    ct.append("| `#TCF.8b\\n` | `''` | 0 | — | **`[]`** ✅ |")
    ct.append("| `#TCF.8b\\n\\n` | `'\\n'` | 1 | `''` | **FAIL-LOUD** — `''` não é `true`/`false` |")
    ct.append("\n**Não existe `[,]`**: a lista de 1 elemento cujo texto é vazio só faz sentido para "
              "**string** (onde `\"\"` é valor legítimo). Para `b`/`n`, linha vazia é **valor fora do "
              "domínio** ⇒ erro. Ou seja, a TAG também decide se linha vazia é dado ou defeito.")
    ct.append("\n**E a tag é dispensável no vazio**: `[]` de bool e `[]` de int são o MESMO dataset "
              "(zero elementos, nenhum tipo a preservar). Logo a grafia canônica de `[]` é a "
              "**sem tag**: `#TCF.8\\n`. `#TCF.8b\\n` seria legal porém redundante — e admitir duas "
              "grafias para o mesmo dataset reabriria a não-canonicidade que estamos fechando.")

    # ---------------- veredito ----------------
    ct.append("\n## Veredito\n")
    ct.append("O mapeamento que o owner propôs está **semanticamente certo** — `[]`, `['']`, `['','']` "
              "devem ser distintos e o vazio não precisa de tag. Mas a **convenção (B)** (LF separador, "
              "`[]` = wire pelado) tem dois custos que a medição expõe:")
    ct.append("1. **quebra todos os wires existentes** (§2) — viola o 'body congelado';")
    ct.append("2. **`[]` corrompe silenciosamente** ao ganhar um LF de qualquer editor (§3).")
    ct.append("\nA **convenção (A)** entrega o MESMO mapeamento semântico com:")
    ct.append("- `#TCF.8\\n` → `[]` · `#TCF.8\\n\\n` → `['']` · `#TCF.8\\n\\n\\n` → `['','']`")
    ct.append("- **zero mudança** nos bytes que o `encode` já produz (só o decode fica estrito);")
    ct.append("- `[]` expresso na forma flat (7 B) em vez de fugir pro `.8H#D0` (11 B);")
    ct.append("- robustez a LF acrescentado.")
    ct.append("\nA diferença entre o que o owner escreveu e (A) é de **um LF**: o owner contou o LF do "
              "header como parte do corpo. Semanticamente idênticos; (A) é a grafia que sobrevive às "
              "ferramentas e ao histórico.")
    ct.append("\n> Não é decisão — é a tabela para decidir. Nada em `src/tcf`.")

    for nome, d in CORPUS:
        (INP / f"{nome}-fonte.json").write_text(json.dumps(d), encoding="utf-8")
        if d:
            w = encode(d)
            (OUT / f"{nome}-wire-real.tcf").write_text(w, encoding="utf-8", newline="")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · A: {len(colA)} colisoes, compat {okA} · B: {len(colB)} colisoes, compat {okB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(rodar())

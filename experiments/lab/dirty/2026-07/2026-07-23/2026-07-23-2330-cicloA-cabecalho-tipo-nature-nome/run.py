#!/usr/bin/env python3
"""Ciclo A — cabeçalho single-col: tipo × nature × nome. **v3 — fluxo real de dados.**

CORREÇÃO (owner 2026-07-23): as v1/v2 eram manipulação ABSTRATA de strings — sem dataset, sem JSON,
sem encode/decode, sem roundtrip. Violavam a convenção do catálogo `2026-07-23-0204` e o fluxo §3.2 do
plano. Esta v3 segue o fluxo materializado:

    inputs/<ID>-fonte.json           (a fonte literal)
      -> json.loads
    intermediates/<ID>-dataset-consumido.json   (o dataset que o TCF realmente consome)
      -> tcf.encode(dataset)
    outputs/<ID>-wire.tcf            (WIRE REAL — nunca reconstruído à mão)
      -> tcf.decode
    outputs/<ID>-dataset.roundtrip.json         (RT real)

REGRA: `outputs/` só contém o que o TCF REALMENTE produz hoje. As gramáticas HIPOTÉTICAS vivem em
`intermediates/` marcadas como hipótese — nunca em outputs como se fossem reais.

As 6 formas enumeradas pelo owner são analisadas ancoradas nos wires REAIS:
  (1) #TCF.8 {nome}:{id}   (2) #TCF.8{nome}:{id}   (3) #TCF.8 {nome}
  (4) #TCF.8{nome}         (5) #TCF.8:{id}         (6) #TCF.8{id}

Zero toque em src/tcf. `python run.py` regenera tudo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[5]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode, SideOutputs, SPEC_CPF  # noqa: E402

INP, INT, OUT = AQUI / "inputs", AQUI / "intermediates", AQUI / "outputs"
for d in (INP, INT, OUT):
    d.mkdir(exist_ok=True)

# placeholders SEGUROS (dígitos repetidos mod-11-válidos; nunca CPF real)
CPFS = ["111.111.111-11", "222.222.222-22", "333.333.333-33", "111.111.111-11"]

# Eixo-1 do registry: chars JÁ ocupados no índice 6 (logo após "#TCF.8")
EIXO1_OCUPADOS = {"M": "multi-col", "H": "hierárquico", " ": "single-col+spec", "\n": "version-stamp"}


def casos():
    """(id, kind, desc, dado, kwargs, o_que_investiga). kind: 'ok' | 'fail' (fail-loud esperado)."""
    return [
        ("A1", "ok", "string órfã — sem header nenhum (piso: o TCF não escreve moldura)",
         ["ana@site.com", "ana.b@site.com", "carlos@site.com"], {},
         "o que o formato faz quando NADA precisa ser declarado"),
        ("A2", "ok", "nature CPF SEM nome — forma (1) com nome vazio == forma (5)",
         CPFS, {"nature": SPEC_CPF},
         "forma (5) `#TCF.8:{id}` é o caso degenerado de (1) com nome vazio?"),
        ("A3", "ok", "nature CPF COM nome 'doc' — forma (1) completa, REAL hoje",
         CPFS, {"nature": SPEC_CPF, "name": "doc"},
         "forma (1) `#TCF.8 {nome}:{id}` — já existe em produção"),
        ("A4", "ok", "nature CPF com nome 'b' (= colide com uma TAG DE TIPO hipotética)",
         CPFS, {"nature": SPEC_CPF, "name": "b"},
         "nome igual a tag de tipo quebra a forma (1)?"),
        ("A5", "ok", "nature CPF com nome 'M' (= colide com o Eixo-1 multi-col)",
         CPFS, {"nature": SPEC_CPF, "name": "M"},
         "nome igual a discriminador de ESTRUTURA quebra a forma (1)?"),
        ("A6", "fail", "nature CPF com nome contendo ':' — contrato REJEITA (não escapa)",
         CPFS, {"nature": SPEC_CPF, "name": "a:b"},
         "o formato ESCAPA ou PROÍBE o separador no nome?"),
        ("A6b", "fail", "nature CPF com nome contendo LF — idem",
         CPFS, {"nature": SPEC_CPF, "name": "a\nb"},
         "idem A6 para quebra de linha"),
        ("A6c", "fail", "name= SEM nature — rótulo sozinho não existe (forma (3) não é suportada)",
         CPFS, {"name": "doc"},
         "a forma (3) `#TCF.8 {nome}` existe hoje?"),
        ("A7", "ok", "lista de BOOL — hoje NÃO tem forma single-col tipada (vai pro .8H)",
         [True, False, True, True], {},
         "A LACUNA que motiva o estudo: tipo não tem onde morar em single-col"),
        ("A8", "ok", "lista de INT — mesma lacuna",
         [1, 2, 3], {},
         "idem A7 para number"),
        ("A9", "ok", "version-stamp — ocupa o índice 6 com '\\n'",
         ["a", "ab", "abc"], {"stamp": True},
         "prova que o índice 6 é o eixo de ESTRUTURA, não de tipo"),
    ]


def _decompoe_header(wire: str) -> list[str]:
    """Decompõe a moldura REAL do wire, byte a byte, sem inventar."""
    if not wire.startswith("#TCF."):
        return ["(sem header — single-col órfão: o body começa no byte 0)"]
    l0 = wire.split("\n", 1)[0]
    L = [f"linha-0 do wire: {l0!r}  ({len(l0.encode())} B + 1 B LF)"]
    L.append("  bytes: " + " ".join(repr(c) for c in l0))
    idx6 = wire[6:7]
    L.append(f"  índice 6 (discriminador do Eixo-1) = {idx6!r} -> "
             f"{EIXO1_OCUPADOS.get(idx6, 'LIVRE/desconhecido')}")
    if l0.startswith("#TCF.8 "):
        resto = l0[len("#TCF.8 "):]
        if ":" in resto:
            nome, ident = resto.rsplit(":", 1)
            L.append(f"  forma (1) `#TCF.8 {{nome}}:{{id}}` -> nome={nome!r} · id={ident!r}")
            L.append(f"  nome vazio? {'SIM -> degenera na forma (5)' if nome == '' else 'não'}")
    return L


def _formas_hipoteticas(nome: str | None, ident: str | None) -> list[str]:
    """As 6 formas do owner, instanciadas. HIPOTÉTICO — nunca vai pra outputs/."""
    n = nome if nome is not None else "<nome>"
    i = ident if ident is not None else "<id>"
    f = {
        1: f"#TCF.8 {n}:{i}",
        2: f"#TCF.8{n}:{i}",
        3: f"#TCF.8 {n}",
        4: f"#TCF.8{n}",
        5: f"#TCF.8:{i}",
        6: f"#TCF.8{i}",
    }
    L = []
    for k in sorted(f):
        h = f[k]
        c6 = h[6:7]
        colide = EIXO1_OCUPADOS.get(c6)
        marca = f"  <-- COLIDE com Eixo-1 ({colide})" if colide and k in (2, 4, 6) else ""
        L.append(f"  ({k}) {h!r}{marca}")
    return L


def rodar():
    ct = ["# Ciclo A (v3) — cabeçalho single-col: fluxo REAL de dados\n",
          "Fluxo §3.2 do plano: `inputs/-fonte.json` -> `intermediates/-dataset-consumido.json` -> "
          "`outputs/-wire.tcf` (REAL) -> `outputs/-dataset.roundtrip.json`. As gramáticas hipotéticas "
          "ficam em `intermediates/`, NUNCA em outputs.\n"]
    rt_ok = rt_fail = 0

    for (cid, kind, desc, dado, kw, investiga) in casos():
        # 1) fonte literal
        fonte_txt = json.dumps(dado, ensure_ascii=False, indent=1)
        (INP / f"{cid}-fonte.json").write_text(fonte_txt, encoding="utf-8")
        # 2) dataset consumido (o que json.loads materializa e o TCF recebe)
        dataset = json.loads(fonte_txt)
        (INT / f"{cid}-dataset-consumido.json").write_text(
            json.dumps(dataset, ensure_ascii=False, indent=1), encoding="utf-8")

        nome = kw.get("name")
        ident = getattr(kw.get("nature"), "name", None)
        dbg = [f"CASE {cid} [{kind}] — {desc}", f"INVESTIGA: {investiga}",
               f"kwargs: {({k: (getattr(v,'name',v)) for k,v in kw.items()}) or '{}'}", "",
               "-- FLUXO (§3.2) --",
               f"1. inputs/{cid}-fonte.json           (fonte literal)",
               f"2. intermediates/{cid}-dataset-consumido.json  -> {repr(dataset)[:100]}"]

        if kind == "fail":
            # contraprova: o contrato deve REJEITAR. Não há wire nem roundtrip.
            try:
                encode(dataset, **kw)
                status = "ERRO: deveria ter FALHADO e NÃO falhou!"
                rt_fail += 1
            except Exception as e:
                status = f"FAIL-LOUD (esperado): {type(e).__name__}: {e}"
            dbg += ["3. (sem wire — contrato rejeita antes de emitir)", "",
                    "-- RESULTADO --", status]
            ct.append(f"- **{cid}** — {desc}\n"
                      f"    - investiga: {investiga}\n"
                      f"    - resultado: `{status[:150]}`")
        else:
            so = SideOutputs()
            wire = encode(dataset, side_outputs=so, **kw)
            (OUT / f"{cid}-wire.tcf").write_text(wire, encoding="utf-8", newline="")
            back = decode(wire)
            ok = (back == dataset)
            rt_ok += ok; rt_fail += (not ok)
            (OUT / f"{cid}-dataset.roundtrip.json").write_text(
                json.dumps(back, ensure_ascii=False, indent=1), encoding="utf-8")
            nb = len(wire.encode())
            dbg += [f"3. outputs/{cid}-wire.tcf            ({nb} B) REAL",
                    f"4. outputs/{cid}-dataset.roundtrip.json  -> RT {'OK' if ok else 'FALHOU'}",
                    "", "-- WIRE REAL --", repr(wire),
                    "", "-- MOLDURA (decomposta do wire real) --"] + _decompoe_header(wire)
            l0 = wire.split("\n", 1)[0] if wire.startswith("#TCF.") else "(órfão)"
            ct.append(f"- **{cid}** — {desc}\n"
                      f"    - investiga: {investiga}\n"
                      f"    - fonte: `{repr(dado)[:70]}`\n"
                      f"    - wire REAL ({nb} B), linha-0: `{l0}`\n"
                      f"    - roundtrip: {'✅' if ok else '❌'}")

        dbg += ["", "-- AS 6 FORMAS DO OWNER (HIPOTÉTICO — não são saída do TCF) --"]
        dbg += _formas_hipoteticas(nome, ident)
        (INT / f"{cid}.debug.txt").write_text("\n".join(dbg) + "\n", encoding="utf-8")

    # ---------------- análise das 6 formas, ancorada nos wires reais ----------------
    an = ["ANÁLISE DAS 6 FORMAS — ancorada no que o TCF REALMENTE emite",
          "=" * 64, "",
          "Eixo-1 (índice 6, logo após '#TCF.8') JÁ OCUPADO por:",
          "  'M' = multi-col · 'H' = hierárquico · ' ' = single-col+spec · '\\n' = version-stamp",
          "", "Formas:", ""]
    an += [
        "(1) #TCF.8 {nome}:{id}  — *** REAL HOJE ***, com evidência nos wires:",
        "      A2 -> '#TCF.8 :cpf'      (nome vazio)",
        "      A3 -> '#TCF.8 doc:cpf'   (nome normal)",
        "      A4 -> '#TCF.8 b:cpf'     (nome 'b' = igual a uma TAG DE TIPO hipotética) -> FUNCIONA",
        "      A5 -> '#TCF.8 M:cpf'     (nome 'M' = igual ao discriminador multi-col)   -> FUNCIONA",
        "    POR QUE não quebra: o índice 6 é o ESPAÇO (a marca da rota), então o 1º char do NOME",
        "    nunca chega a competir com o Eixo-1; e o id é separado pelo ÚLTIMO ':'. Ou seja, a forma",
        "    (1) é ROBUSTA a nome colidente — provado, não suposto.",
        "",
        "(2) #TCF.8{nome}:{id}   — HIPOTÉTICA. Índice 6 = 1º char do NOME. COLIDE se o nome começar",
        "    com 'M'/'H' (viraria multi-col/hierárquico). Contraste direto com A5: em (1) o nome 'M'",
        "    é inofensivo; em (2) seria fatal. A fragilidade está em expor o índice 6 a dado do usuário.",
        "",
        "(3) #TCF.8 {nome}       — *** NÃO EXISTE HOJE ***: A6c prova que `name=` sem `nature=` é",
        "    REJEITADO ('name= so' tem efeito em single-col COM nature='). Rótulo sozinho não é uma",
        "    rota do formato. Como forma futura seria segura (índice 6 = ' ') mas não declara tipo —",
        "    não resolve a lacuna de A7/A8.",
        "",
        "(4) #TCF.8{nome}        — HIPOTÉTICA. Índice 6 = 1º char do nome: mesma fragilidade de (2),",
        "    E é INDISTINGUÍVEL de (6) — ambas são '#TCF.8' + token nu. A intuição do owner CONFIRMA-SE.",
        "",
        "(5) #TCF.8:{id}         — HIPOTÉTICA *sem espaço*. Atenção: o que existe hoje (A2) é",
        "    '#TCF.8 :cpf' — COM espaço. Uma forma (5) verdadeira (sem espaço) usaria ':' no índice 6,",
        "    que está LIVRE no Eixo-1 -> seria um discriminador NOVO válido, e economizaria 1 B.",
        "",
        "(6) #TCF.8{id}          — HIPOTÉTICA. Índice 6 = 1º char do ID. COLIDIRIA se um id começasse",
        "    com 'M'/'H'. MAS: diferente do nome, o ID vem de namespace FECHADO (whitelist do formato)",
        "    — basta EXCLUIR 'M','H',' ','\\n' do vocabulário e a colisão some por definição.",
        "    *** ESTA É A DIFERENÇA ENTRE (4) E (6) ***: como FORMA são idênticas; o que as separa é a",
        "    NATUREZA do token — nome é ABERTO (dado do usuário, não se pode restringir sem quebrar",
        "    contrato) e id é FECHADO (vocabulário do formato, restringível por definição).",
        "",
        "-" * 64,
        "ESCAPING: o formato PROÍBE, não escapa.",
        "  A6  -> name='a:b'  REJEITADO: \"name de single-col nao pode conter ':' nem '\\n'\"",
        "  A6b -> name='a\\nb' REJEITADO (idem)",
        "  Ou seja: o separador é protegido por CONTRATO (fail-loud), não por escape. Isso simplifica",
        "  o parse (não há sequência de escape a interpretar no nome) ao custo de restringir nomes.",
        "",
        "-" * 64,
        "COMBINAÇÕES COERENTES (a pergunta do owner):", "",
        "  (2)+(5): coerente entre si — (5) é (2) com nome vazio. Mas herda a fragilidade de (2):",
        "           o índice 6 passa a depender do 1º char de um NOME de usuário. Contraindicado",
        "           pela evidência de A5.",
        "",
        "  (1)+(6): COERENTE E SEGURA — o ESPAÇO marca 'tem nome' (rota 1, já real e robusta por A4/A5)",
        "           e a AUSÊNCIA de espaço marca 'token nu do namespace fechado' (rota 6). Como (6) só",
        "           admite ids da whitelist (sem M/H), não há ambiguidade. O espaço é o desambiguador.",
        "           É a combinação que a evidência favorece.",
        "",
        "  (1)+(2)+(5)+(6): a hipótese do owner de que ' ' e ':' desambiguam quando os 1ºs chars",
        "           competem com um primitivo é PARCIALMENTE verdadeira: ' ' e ':' de fato separam as",
        "           rotas, mas (2)/(4) continuam expondo o índice 6 a nome arbitrário. O conjunto só",
        "           fecha se (2) proibir nome iniciando em char reservado — o que reintroduz no NOME",
        "           a restrição que (1) evita de graça.",
        "",
        "CONCLUSÃO DA ANÁLISE (não é decisão):",
        "  - a forma (1) NÃO precisa falhar e NÃO falha: funciona hoje e é robusta a nome colidente",
        "    (A4/A5). CORRIGE a v2 deste lab, que a havia declarado 'refutada' — aquilo era um",
        "    enquadramento inventado (tipo e nature disputando um slot), não o comportamento real.",
        "  - o que (1) não faz é carregar TIPO e NATURE juntos no mesmo slot. Isso só é limitação se",
        "    os dois precisarem coexistir; com namespaces DISJUNTOS um slot basta.",
        "  - a lacuna real (A7/A8): bool e int não têm HOJE nenhuma forma single-col tipada — vão",
        "    para '#TCF.8H#V...' (envelope hierárquico) só para preservar o tipo.",
    ]
    (INT / "00-analise-6-formas.txt").write_text("\n".join(an) + "\n", encoding="utf-8")

    ct.append("\n## Análise das 6 formas\n")
    ct.append("Íntegra em [`intermediates/00-analise-6-formas.txt`](intermediates/00-analise-6-formas.txt). Resumo:\n")
    ct.append("| forma | status | índice 6 | evidência | veredito |")
    ct.append("|---|---|---|---|---|")
    ct.append("| (1) `#TCF.8 {nome}:{id}` | **REAL hoje** | `' '` | A2/A3/A4/A5 | **robusta** — nome `b` e `M` funcionam |")
    ct.append("| (2) `#TCF.8{nome}:{id}` | hipotética | 1º char do NOME | — | frágil (contraste c/ A5) |")
    ct.append("| (3) `#TCF.8 {nome}` | **não existe** | `' '` | A6c rejeita | rótulo sozinho não é rota |")
    ct.append("| (4) `#TCF.8{nome}` | hipotética | 1º char do NOME | — | **indistinguível de (6)** + frágil |")
    ct.append("| (5) `#TCF.8:{id}` | hipotética *sem espaço* | `':'` (livre) | A2 é a versão COM espaço | `:` livre no Eixo-1 → discriminador novo viável |")
    ct.append("| (6) `#TCF.8{id}` | hipotética | 1º char do ID | — | **defensável** — id é namespace FECHADO |")
    ct.append("\n### A diferença entre (4) e (6) — o cerne\n")
    ct.append("Como **forma** são idênticas (`#TCF.8` + token nu). O que as separa é a **natureza do "
              "token**: **nome** é ABERTO (dado do usuário — não dá pra restringir sem quebrar "
              "contrato) e **id** é FECHADO (vocabulário do formato — dá pra excluir `M`/`H` por "
              "definição). Por isso (6) é defensável e (4) não. A sua intuição de que 4 e 6 se "
              "confundem **se confirma**.")
    ct.append("\n### Por que a forma (1) NÃO quebra com nome colidente (evidência)\n")
    ct.append("- A4 → `#TCF.8 b:cpf` (nome `b`, igual a uma tag de tipo) — **funciona**\n"
              "- A5 → `#TCF.8 M:cpf` (nome `M`, igual ao discriminador multi-col) — **funciona**\n\n"
              "Porque o índice 6 é o **espaço** (a marca da rota), então o 1º char do nome nunca "
              "compete com o Eixo-1; e o id é separado pelo **último** `:`.")
    ct.append("\n### Escaping: o formato PROÍBE, não escapa\n")
    ct.append("A6 (`name='a:b'`) e A6b (`name='a\\nb'`) são **rejeitados**: *\"name de single-col nao "
              "pode conter ':' nem '\\n'\"*. O separador é protegido por **contrato fail-loud**, não por "
              "sequência de escape — simplifica o parse ao custo de restringir nomes.")
    ct.append("\n### Combinação que a evidência favorece: **(1)+(6)**\n")
    ct.append("O espaço marca 'tem nome' (rota 1, já real e robusta); a ausência marca 'token nu do "
              "namespace fechado' (rota 6). Sem ambiguidade. A sua hipótese de que ` ` e `:` "
              "desambiguam é **parcialmente** verdadeira: eles separam as rotas, mas (2)/(4) continuam "
              "expondo o índice 6 a nome arbitrário — o conjunto (1)+(2)+(5)+(6) só fecha se (2) "
              "proibir nome iniciando em char reservado, reintroduzindo no NOME a restrição que (1) "
              "evita de graça.")
    ct.append("\n### ⚠️ Correção da v2 deste lab\n")
    ct.append("A v2 declarou a forma (1) **'refutada'** — **estava errado**. Ela funciona hoje (A3) e é "
              "robusta a nome colidente (A4/A5). Aquela 'refutação' vinha de um enquadramento que eu "
              "inventei (tipo e nature disputando o mesmo slot), não do comportamento real. As v1/v2 "
              "também inventaram um escaping `esc()`/`unesc()` que **não existe** — o formato proíbe.")
    ct.append(f"\n---\n**Roundtrip: {rt_ok} OK, {rt_fail} falhas.** Artefatos: `inputs/*-fonte.json` · "
              "`intermediates/*-dataset-consumido.json` · `intermediates/*.debug.txt` · "
              "`intermediates/00-analise-6-formas.txt` · `outputs/*-wire.tcf` · "
              "`outputs/*-dataset.roundtrip.json`. Regenera: `python run.py`.\n")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · {len(casos())} casos · roundtrip {rt_ok} ok / {rt_fail} falhas")
    return rt_fail


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

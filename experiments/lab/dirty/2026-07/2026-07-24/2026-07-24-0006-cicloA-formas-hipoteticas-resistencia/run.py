#!/usr/bin/env python3
"""Ciclo A (cont.) — formas HIPOTÉTICAS: resistência a variações + a tipagem sobrevive?

Continua [`2026-07-23-2330`](../../2026-07-23/2026-07-23-2330-cicloA-cabecalho-tipo-nature-nome/),
que mediu o que o TCF emite HOJE. Aqui testamos as formas que NÃO existem, contra variações.

Direção do owner: "quanto mais implícito melhor pra formatos já pequenos; qualquer coisa intuída por
exclusão é vantagem" — MAS "a vantagem em arquivo não significa que as tipagens internamente somem".
⇒ o GATE deste lab é: por mais implícita que seja a moldura, `decode` tem que devolver o dataset
**TIPADO** (bool volta bool, int volta int). Economia é de MOLDURA, nunca de SEMÂNTICA.

DESENHO — **body REAL, header HIPOTÉTICO**:
  o corpo vem do `src/tcf` de verdade (`encode` dos valores renderizados) e fica CONGELADO;
  só a moldura varia. Assim a resistência é da moldura, sem inventar corpo.

CONVENÇÃO (aprendida no 2330): `outputs/` = só o que o TCF REALMENTE emite (âncora).
As formas hipotéticas são PROTÓTIPOS e vivem em `intermediates/*.tcfp`, marcadas como hipótese.

Zero toque em src/tcf. `python run.py`.
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
# Eixo-1: chars JÁ ocupados no índice 6 (o que uma forma nova NÃO pode sequestrar)
EIXO1 = {"M": "multi-col", "H": "hierárquico", " ": "single-col+spec", "\n": "version-stamp"}
# namespace FECHADO de tags de tipo (a whitelist que torna a forma (6) defensável)
TAGS = {"b": "bool", "n": "number", "s": "string"}


class Rejeita(Exception):
    pass


# ------------------------------------------------- render/parse de TIPO (a semântica NÃO some)
def render(valores, tag):
    """dataset tipado -> list[str] para o corpo. O tipo vira TAG, não desaparece."""
    if tag == "b":
        return ["true" if v else "false" for v in valores]
    if tag == "n":
        return [repr(v) if isinstance(v, float) else str(v) for v in valores]
    return [str(v) for v in valores]


def restaura(linhas, tag):
    """list[str] do corpo -> dataset TIPADO. É o gate: a tipagem tem que voltar."""
    if tag == "b":
        for x in linhas:
            if x not in ("true", "false"):
                raise Rejeita(f"valor fora do domínio bool: {x!r}")
        return [x == "true" for x in linhas]
    if tag == "n":
        out = []
        for x in linhas:
            out.append(float(x) if ("." in x or "e" in x.lower()) else int(x))
        return out
    return list(linhas)


# --------------------------------------------------------- as formas (encode do HEADER só)
def h1(nome, ident):                       # REAL hoje
    return f"{MAGIC} {nome or ''}:{ident}"


def h2(nome, ident):
    return f"{MAGIC}{nome or ''}:{ident}"


def h4(nome, ident):
    return f"{MAGIC}{nome or ''}"


def h5(nome, ident):
    if nome:
        raise Rejeita("forma (5) não tem lugar para nome")
    return f"{MAGIC}:{ident}"


def h6(nome, ident):
    if nome:
        raise Rejeita("forma (6) não tem lugar para nome")
    return f"{MAGIC}{ident}"


def p_generico(h, tem_dp, tem_espaco):
    """Parser genérico das formas. Devolve (nome, ident) ou levanta."""
    if not h.startswith(MAGIC):
        raise Rejeita("assinatura ausente")
    resto = h[len(MAGIC):]
    c6 = resto[:1]
    if tem_espaco:
        if c6 != " ":
            raise Rejeita(f"esperava espaço no índice 6, veio {c6!r}")
        resto = resto[1:]
    else:
        # SEQUESTRO: sem espaço, o índice 6 é o 1º char do token — pode colidir com o Eixo-1
        if c6 in EIXO1:
            raise Rejeita(f"SEQUESTRO do Eixo-1: {c6!r} = {EIXO1[c6]}")
    if tem_dp:
        if ":" not in resto:
            raise Rejeita("esperava ':' separando nome de id")
        nome, ident = resto.rsplit(":", 1)
        return (nome or None), ident
    return (resto or None), None


# namespace FECHADO = o vocabulário do FORMATO (tipos + natures). É o que torna F6 defensável:
# o token nu só é aceito se pertencer a ele.
NAMESPACE_FECHADO = set(TAGS) | {"cpf", "cnpj", "ip"}


def _p5(h):
    if not h.startswith(MAGIC + ":"):
        raise Rejeita("forma (5) exige ':' no índice 6")
    ident = h[len(MAGIC) + 1:]
    if not ident:
        raise Rejeita("id vazio")
    return None, ident


def _p4(h):
    """(4): token nu interpretado como NOME (namespace ABERTO — nada a validar)."""
    nome, _ = p_generico(h, False, False)
    return nome, None


def _p6(h):
    """(6): token nu interpretado como ID. Namespace FECHADO -> valida contra a whitelist."""
    tok, _ = p_generico(h, False, False)
    if tok is None:
        raise Rejeita("id vazio")
    if tok not in NAMESPACE_FECHADO:
        raise Rejeita(f"id {tok!r} fora do namespace fechado {sorted(NAMESPACE_FECHADO)}")
    return None, tok


FORMAS = {
    "F1 (real) #TCF.8 {nome}:{id}": (h1, lambda h: p_generico(h, True, True), True, True),
    "F2 #TCF.8{nome}:{id}":         (h2, lambda h: p_generico(h, True, False), True, False),
    "F4 #TCF.8{nome}":              (h4, _p4, False, False),
    "F5 #TCF.8:{id}":               (h5, _p5, True, False),
    "F6 #TCF.8{id}":                (h6, _p6, False, False),
}


# ---------------------------------------------------------------- datasets (TIPADOS, reais)
def datasets():
    return [
        ("D-bool", [True, False, True, True], "b"),
        ("D-int", [1, 2, 3, 42], "n"),
        ("D-float", [1.5, 2.25, 3.0], "n"),
        ("D-str", ["ana", "bruno", "carla"], "s"),
        ("D-n1", [True], "b"),
        ("D-n0", [], "b"),
    ]


NOMES = [None, "doc", "b", "M", "H", "", "a b", "9x", "ção"]
IDS = ["b", "n", "s", "cpf", "M", "zz", ""]


def rodar():
    ct = ["# Ciclo A (cont.) — formas HIPOTÉTICAS: resistência + a tipagem sobrevive?\n",
          "**Body REAL, header HIPOTÉTICO**: o corpo vem do `src/tcf` (congelado); só a moldura varia. "
          "`outputs/` = wire REAL do TCF (âncora). Formas hipotéticas = `intermediates/*.tcfp`.\n",
          "GATE do owner: *a vantagem em arquivo não faz a tipagem sumir internamente* — o decode "
          "tem que devolver o dataset **TIPADO**.\n"]

    # ---------------- PARTE B (primeiro, porque é o GATE) : a tipagem sobrevive? ----------------
    ct.append("## 1. GATE — a tipagem volta? (body real + moldura implícita)\n")
    ct.append("| dataset | tag | corpo REAL (do src/tcf) | wire hipotético F6 | RT tipado |")
    ct.append("|---|---|---|---|:---:|")
    gate_ok = gate_fail = 0
    comparacao = []
    for (did, dados, tag) in datasets():
        fonte = json.dumps(dados, ensure_ascii=False, indent=1)
        (INP / f"{did}-fonte.json").write_text(fonte, encoding="utf-8")
        dataset = json.loads(fonte)
        (INT / f"{did}-dataset-consumido.json").write_text(
            json.dumps(dataset, ensure_ascii=False, indent=1), encoding="utf-8")

        # âncora: o que o TCF REALMENTE faz com este dataset hoje
        wire_real = encode(dataset)
        (OUT / f"{did}-wire-real.tcf").write_text(wire_real, encoding="utf-8", newline="")
        (OUT / f"{did}-dataset.roundtrip.json").write_text(
            json.dumps(decode(wire_real), ensure_ascii=False, indent=1), encoding="utf-8")

        # corpo REAL a partir dos valores renderizados (congelado)
        linhas = render(dataset, tag)
        corpo = encode(linhas) if linhas else ""
        # wire hipotético mais IMPLÍCITO possível: forma (6)
        wire_hip = f"{h6(None, tag)}\n{corpo}"
        (INT / f"{did}-hipotetico-F6.tcfp").write_text(wire_hip, encoding="utf-8", newline="")

        # decode do hipotético: moldura -> tag -> corpo real -> restaura TIPO
        try:
            cab, resto = wire_hip.split("\n", 1)
            _n, ident = _p6(cab)                      # F6: token nu É o id (namespace fechado)
            volta = restaura(decode(resto) if resto else [], ident)
            ok = (volta == dataset)
        except Exception as e:
            ok, volta = False, f"erro: {e}"
        gate_ok += ok; gate_fail += (not ok)
        (INT / f"{did}-hipotetico-F6.roundtrip.json").write_text(
            json.dumps(volta if ok else str(volta), ensure_ascii=False, indent=1), encoding="utf-8")
        ct.append(f"| `{did}` | `{tag}` | `{corpo!r}` | `{wire_hip.splitlines()[0]}` | "
                  f"{'✅' if ok else '❌'} |")
        comparacao.append((did, tag, len(wire_real.encode()), len(wire_hip.encode())))

    if gate_fail == 0:
        ct.append(f"\n**Gate: {gate_ok}/{gate_ok} ✅.** O tipo viaja como TAG (1 char) e é reconstruído "
                  "no decode — a moldura encolhe, a semântica NÃO. `D-bool` volta `True/False` (bool), "
                  "não `'true'/'false'` (string). É a confirmação do alerta do owner.")
    else:
        ct.append(f"\n**⚠️ Gate: {gate_ok} ok / {gate_fail} FALHAS — a tipagem NÃO sobreviveu em "
                  f"{gate_fail} casos.** Enquanto isto não fechar, a forma implícita NÃO está provada: "
                  "economizar moldura às custas de perder tipo viola o requisito do owner.")

    # ---------------- comparação com o que o TCF gasta HOJE ----------------
    # CORREÇÃO (owner): a baseline tem que ter ao menos `#TCF.8`. O órfão sem header é caso
    # ESPECIAL (deveria exigir parâmetro explícito), não o default do estudo. Onde o dado aceita
    # `stamp=True`, a baseline justa é a ESTAMPADA.
    ct.append("\n## 1b. O que vale contra o TCF de HOJE — baseline com `#TCF.8` (corrigida)\n")
    ct.append("> **Correção do owner**: comparar contra o órfão *sem header* era injusto. Os formatos "
              "estudados têm no mínimo a declarativa `#TCF.8`; ficar abaixo disso deveria exigir "
              "parâmetro explícito. Onde o dado aceita `stamp=True`, a baseline é a estampada.\n")
    ct.append("| dataset | tag | TCF hoje (rota real) | baseline c/ `#TCF.8` | F6 | Δ vs baseline |")
    ct.append("|---|---|---:|---:|---:|---:|")
    tot_tip = n_tip = 0
    for (did, tag, br, bh) in comparacao:
        if did == "D-n0":
            continue
        dados = dict((d[0], d[1]) for d in [(x[0], x[1]) for x in comparacao])  # noqa
        # baseline estampada só existe pra rota flat (string); tipados vão pro .8H (stamp inválido)
        if tag == "s":
            base = br + len("#TCF.8\n".encode())
            rota = "órfão (0 B header)"
        else:
            base = br
            rota = ".8H (envelope)"
        d = bh - base
        if tag != "s":
            tot_tip += -d; n_tip += 1
        ct.append(f"| `{did}` | `{tag}` | {rota} | {base} B | {bh} B | **{d:+d} B** |")
    ct.append(f"\n- **Tipados (bool/int/float)**: hoje o TCF embrulha no `.8H` (`#V\\z#:N[]:…`) só pra "
              f"preservar o tipo — e `stamp` nem se aplica (é rota hierárquica). A forma implícita "
              f"economiza **~{tot_tip//max(1,n_tip)} B por coluna**: o envelope inteiro vira 1 char.")
    ct.append("- **String, com baseline JUSTA**: `#TCF.8\\n`+corpo = 23 B vs `#TCF.8s\\n`+corpo = 24 B "
              "⇒ a tag custa **+1 B**, não +8. A conclusão qualitativa se mantém (string é o default "
              "implícito, não vale declarar), mas a magnitude era artefato de baseline errada.")

    # ---------------- VAZIO: [] vs [""] — a "sugestão duvidosa" do owner, MEDIDA ----------------
    ct.append("\n## 1c. O VAZIO — `[]` vs `[\"\"]` (sugestão do owner, MEDIDA)\n")
    ct.append("| dataset | wire REAL | bytes | rota | decode | RT |")
    ct.append("|---|---|---:|---|---|:---:|")
    for rot, d, fn in [("[]", [], "vazia"), ('[""]', [""], "1vazia"), ('["",""]', ["", ""], "2vazias")]:
        w = encode(d)
        b = decode(w)
        rota = ".8H" if w.startswith("#TCF.8H") else "flat/órfão"
        ct.append(f"| `{rot}` | `{w!r}` | {len(w.encode())} | {rota} | `{b!r}` | "
                  f"{'✅' if b == d else '❌'} |")
        (INT / f"E-{fn}-real.tcf").write_text(w, encoding="utf-8", newline="")

    graf = ["#TCF.8\n", "#TCF.8\n\n"]
    decs = []
    for g in graf:
        try:
            decs.append(repr(decode(g)))
        except Exception as e:
            decs.append(f"ERRO {type(e).__name__}")
    ct.append(f"\n**Canonicidade (§S1.2)**: `{graf[0]!r}` → `{decs[0]}` · `{graf[1]!r}` → `{decs[1]}`")
    if decs[0] == decs[1]:
        ct.append("\n⚠️ **DUAS GRAFIAS, MESMO DATASET** — viola §S1.2 (*um dataset + uma config ⇒ uma "
                  "única grafia*). Corpo vazio e corpo com uma linha vazia colapsam em `['']`. "
                  "**Consequência**: a forma flat NÃO CONSEGUE expressar `[]` — por isso `[]` foge "
                  "pro `#TCF.8H#D0`.")

    ct.append("\n### Reavaliação da sugestão do owner\n")
    ct.append("O owner sugeriu: *quando está vazio não precisa de nada, nem o `b`*; e que `#TCF.8` sem "
              "tag (string implícita) com corpo vazio seria `[\"\"]`. **A medição sustenta e refina:**\n")
    ct.append("1. **A tag É dispensável no vazio** — e por motivo mais forte que economia: uma lista "
              "vazia **não tem elemento algum**, logo não há tipo a preservar. `[]` de bool e `[]` de "
              "int são o MESMO dataset. Declarar `b` ali é escrever informação que não existe.")
    ct.append("2. **A ambiguidade intuída é REAL e já está no formato de hoje**, não é hipotética: "
              "`#TCF.8\\n` e `#TCF.8\\n\\n` decodificam ambos para `['']`.")
    ct.append("3. **Saída natural** (a estudar, não decidida): fixar **0 linhas ⇒ `[]`** e **1 linha "
              "vazia ⇒ `[\"\"]`**. Isso (a) restaura a canonicidade, (b) deixa a forma flat expressar "
              "`[]` sem o `.8H#D0` — elimina uma rota inteira, e (c) dispensa a tag no vazio, "
              "exatamente como o owner propôs.")
    ct.append(f"4. **Custo atual do desvio**: `[]` gasta {len(encode([]).encode())} B via `.8H#D0` onde "
              "`#TCF.8\\n` (7 B) bastaria — e pior, obriga uma ROTA hierárquica só pra dizer 'nada'.")

    ct.append("\n## 2. Resistência da moldura a variações\n")
    ct.append("| forma | combos | ok | rejeitados | **sequestros do Eixo-1** | nome perdido |")
    ct.append("|---|---:|---:|---:|---:|---:|")
    det = []
    for fnome, (enc, par, tem_dp, tem_esp) in FORMAS.items():
        ok = rej = seq = perdido = 0
        for nome in NOMES:
            for ident in IDS:
                try:
                    h = enc(nome, ident)
                except Rejeita:
                    rej += 1
                    continue
                try:
                    n2, i2 = par(h)
                    # nome perdido: a forma não consegue devolver o nome que recebeu
                    if (nome or None) != n2:
                        perdido += 1
                        det.append(f"{fnome}: nome {nome!r} -> voltou {n2!r} (header {h!r})")
                    else:
                        ok += 1
                except Rejeita as e:
                    rej += 1
                    if "SEQUESTRO" in str(e):
                        seq += 1
        ct.append(f"| `{fnome}` | {len(NOMES)*len(IDS)} | {ok} | {rej} | {seq} | {perdido} |")
    (INT / "00-resistencia-detalhe.txt").write_text("\n".join(det) + "\n", encoding="utf-8")

    # ---------------- implicitude: escrito vs deduzido ----------------
    ct.append("\n## 3. Implicitude — o que é ESCRITO vs DEDUZIDO por exclusão\n")
    ct.append("| forma | bytes (tag `b`, sem nome) | rota single-col | presença de nome | tipo |")
    ct.append("|---|---:|---|---|---|")
    ct.append(f"| F1 `#TCF.8 :b` | {len(h1(None,'b').encode())} | **escrita** (espaço) | deduzida (vazio) | **escrito** |")
    ct.append(f"| F5 `#TCF.8:b` | {len(h5(None,'b').encode())} | **escrita** (`:`) | deduzida (não há) | **escrito** |")
    ct.append(f"| F6 `#TCF.8b` | {len(h6(None,'b').encode())} | **deduzida por exclusão** | deduzida (não há) | **escrito** |")
    ct.append("\n**F6 é a mais implícita**: a rota single-col é *intuída por exclusão* — não é `M`, "
              "não é `H`, não é espaço, não é `\\n`, logo é token de tipo. O único campo irredutível "
              "escrito é a TAG. É exatamente o 'intuído por exclusão é vantagem'.")
    ct.append("\n⚠️ **Mas F6 e F4 são a mesma forma** (`#TCF.8` + token nu): só é seguro porque a tag "
              "vem de namespace FECHADO. Se o token pudesse ser um NOME (aberto), a dedução por "
              "exclusão quebra — ver coluna 'sequestros' da §2.")

    ct.append("\n## 4. Leitura\n")
    if gate_fail == 0:
        ct.append("- **A tipagem NÃO some**: o gate da §1 mostra que, com moldura mínima (`#TCF.8b`), o "
                  "decode devolve bool/int/float corretos. O tipo deixa de ocupar envelope hierárquico "
                  "e passa a ocupar **1 char**; a semântica é idêntica.")
    else:
        ct.append(f"- **⚠️ A tipagem falhou em {gate_fail} casos** — ver §1. Nenhuma conclusão sobre "
                  "implicitude é válida enquanto o gate não fechar.")
    ct.append("- **F5 e F6 resistem** às variações de id porque não têm onde guardar nome — o que as "
              "torna estreitas mas robustas. F2/F4 perdem/deformam nome e sofrem sequestro do Eixo-1 "
              "quando o nome começa com `M`/`H`.")
    ct.append("- **Custo do nome**: nenhuma forma implícita (F5/F6) carrega nome. Se nome for "
              "necessário, é F1 — que a evidência do 2330 mostrou robusta. Isso reforça o par "
              "**(1)+(6)**: F1 quando há nome, F6 quando não há.")
    ct.append("- **Contra-indicação registrada**: a economia de F6 sobre F1 é de "
              f"{len(h1(None,'b').encode()) - len(h6(None,'b').encode())} B — relevante só em payload "
              "minúsculo, que é justamente o foco declarado do projeto.")
    ct.append(f"\n---\n**Gate de tipagem: {gate_ok}/{gate_ok+gate_fail}.** Artefatos: "
              "`inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` · "
              "`intermediates/*-hipotetico-F6.tcfp` (HIPÓTESE) · `outputs/*-wire-real.tcf` (REAL). "
              "Regenera: `python run.py`.\n")
    (AQUI / "result.md").write_text("\n".join(ct), encoding="utf-8", newline="\n")
    print(f"OK · gate tipagem {gate_ok} ok / {gate_fail} falhas")
    return gate_fail


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

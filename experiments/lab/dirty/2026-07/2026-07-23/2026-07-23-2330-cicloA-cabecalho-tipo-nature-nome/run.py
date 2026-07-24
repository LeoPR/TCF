#!/usr/bin/env python3
"""Ciclo A — cabeçalho single-col: como TIPO, NATURE/spec e NOME coexistem.

Executa a matriz declarada em MANIFESTO.md (protocolo `cicloA-v1`, declarado ANTES de medir).
BODY CONGELADO — só a moldura varia. `order_free` fora (adiado .9). Nada em src/tcf.

4 gramáticas candidatas × (tipo × nature × nome, incl. nomes adversariais) + contraprovas.
Avalia os critérios §S1 mecanicamente testáveis: autocontenção, canonicidade, dispatch local,
prefixo sem ambiguidade, fail-loud, extensibilidade (namespaces), custo em bytes.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parents[5]
sys.path.insert(0, str(ROOT / "src"))

INT, OUT = AQUI / "intermediates", AQUI / "outputs"
for d in (INT, OUT):
    d.mkdir(exist_ok=True)

PROTOCOLO = "cicloA-v2"

# formas EXISTENTES do .8 (registry Eixo 1) — nenhum candidato pode SEQUESTRAR
FORMAS_EXISTENTES = ["#TCF.8M", "#TCF.8H", "#TCF.8 ", "#TCF.8\n"]

# rota que cada gramática legitimamente ESTENDE (extensão != colisão) — v2
EXTENDE = {"G1-slot-unico": "#TCF.8 ", "G2-eixos-separados": None,
           "G3-tag-colada": None, "G4-sem-assinatura": None}

# v2: tags adversariais M/H materializam a hipótese "índice 6 é do Eixo-1"
TIPOS = [None, "b", "n", "M", "H"]
NATURES = [None, "cpf"]
NOMES = [
    ("ausente", None), ("simples", "idade"), ("vazio", ""),
    ("com-dois-pontos", "a:b"), ("com-espaco", "a b"), ("com-backslash", "a\\b"),
    ("com-lf", "a\nb"), ("igual-M", "M"), ("igual-H", "H"),
    ("igual-tag-tipo", "b"), ("igual-id-nature", "cpf"),
]


class Ambiguo(Exception):
    """A gramática não consegue representar/recuperar esta combinação."""


# ---------------------------------------------------------------- escaping de nome (comum)
def esc(n: str) -> str:
    return n.replace("\\", "\\\\").replace(":", "\\:").replace("\n", "\\n")


def unesc(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\":
            if i + 1 >= len(s):
                raise Ambiguo("escape solto no fim do nome")
            c = s[i + 1]
            out.append({"\\": "\\", ":": ":", "n": "\n"}.get(c, c))
            i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)


def _split_ult_dois_pontos(s):
    """Split no ÚLTIMO ':' NÃO-escapado (convenção do multi-col real)."""
    i, ult = 0, -1
    while i < len(s):
        if s[i] == "\\":
            i += 2; continue
        if s[i] == ":":
            ult = i
        i += 1
    return (s[:ult], s[ult + 1:]) if ult >= 0 else (s, None)


# --------------------------------------------------------------------------- G1: slot ÚNICO
def g1_enc(tipo, nature, nome):
    if tipo is not None and nature is not None:
        raise Ambiguo("G1 tem UM slot: tipo e nature não cabem juntos")
    ident = nature if nature is not None else tipo
    if ident is None:
        raise Ambiguo("G1 exige um id no slot")
    return f"#TCF.8 {esc(nome) if nome is not None else ''}:{ident}"


def g1_parse(h):
    if not h.startswith("#TCF.8 "):
        raise Ambiguo("G1: assinatura ausente")
    corpo = h[len("#TCF.8 "):]
    nome_r, ident = _split_ult_dois_pontos(corpo)
    if ident is None or ident == "":
        raise Ambiguo("G1: id vazio/ausente")
    # slot ÚNICO: impossível saber se `ident` é tipo ou nature -> ambiguidade estrutural
    return {"nome": unesc(nome_r) if nome_r != "" else None,
            "ident": ident, "tipo": "?", "nature": "?"}


# ------------------------------------------------- G2: tipo no discriminador, nature no sufixo
def g2_enc(tipo, nature, nome):
    if tipo is None:
        raise Ambiguo("G2 exige tipo no discriminador")
    s = f"#TCF.8:{tipo}"
    if nome is not None:
        s += " " + esc(nome)
    if nature is not None:
        if nome is None:
            s += " "                       # posição do nome fica explícita (vazia)
        s += f":{nature}"
    return s


def g2_parse(h):
    if not h.startswith("#TCF.8:"):
        raise Ambiguo("G2: assinatura/discriminador ausente")
    resto = h[len("#TCF.8:"):]
    if " " in resto:
        tipo, cauda = resto.split(" ", 1)
    else:
        tipo, cauda = resto, None
    if tipo == "":
        raise Ambiguo("G2: tag de tipo vazia")
    nome = nature = None
    if cauda is not None:
        nome_r, nature = _split_ult_dois_pontos(cauda)
        nome = unesc(nome_r) if nome_r != "" else None
    return {"nome": nome, "tipo": tipo, "nature": nature}


# ------------------------------------------------------------------- G3: tag colada (índice 6)
def g3_enc(tipo, nature, nome):
    if tipo is None:
        raise Ambiguo("G3 exige tipo colado")
    s = f"#TCF.8{tipo}"
    if nome is not None:
        s += " " + esc(nome)
    if nature is not None:
        if nome is None:
            s += " "
        s += f":{nature}"
    return s


def g3_parse(h):
    if not h.startswith("#TCF.8"):
        raise Ambiguo("G3: assinatura ausente")
    resto = h[len("#TCF.8"):]
    if resto == "" or resto[0] in (" ", "\n"):
        raise Ambiguo("G3: sem tag colada (é outra forma do .8)")
    tipo, cauda = (resto.split(" ", 1) + [None])[:2] if " " in resto else (resto, None)
    nome = nature = None
    if cauda is not None:
        nome_r, nature = _split_ult_dois_pontos(cauda)
        nome = unesc(nome_r) if nome_r != "" else None
    return {"nome": nome, "tipo": tipo, "nature": nature}


# ------------------------------------------------------------------- G4: sem assinatura
def g4_enc(tipo, nature, nome):
    if tipo is None:
        raise Ambiguo("G4 exige tipo")
    s = f":{tipo}"
    if nome is not None:
        s += " " + esc(nome)
    if nature is not None:
        if nome is None:
            s += " "
        s += f":{nature}"
    return s


def g4_parse(h):
    if not h.startswith(":"):
        raise Ambiguo("G4: prefixo ausente")
    resto = h[1:]
    tipo, cauda = (resto.split(" ", 1) + [None])[:2] if " " in resto else (resto, None)
    if tipo == "":
        raise Ambiguo("G4: tag vazia")
    nome = nature = None
    if cauda is not None:
        nome_r, nature = _split_ult_dois_pontos(cauda)
        nome = unesc(nome_r) if nome_r != "" else None
    return {"nome": nome, "tipo": tipo, "nature": nature}


GRAMATICAS = {
    "G1-slot-unico": (g1_enc, g1_parse),
    "G2-eixos-separados": (g2_enc, g2_parse),
    "G3-tag-colada": (g3_enc, g3_parse),
    "G4-sem-assinatura": (g4_enc, g4_parse),
}


def rota_confundida(h, gname):
    """v2: header gerado começa com o prefixo de uma rota existente DIFERENTE da que estende."""
    ext = EXTENDE.get(gname)
    for f in FORMAS_EXISTENTES:
        if f == ext:
            continue                       # extensão legítima, não colisão
        if h.startswith(f):
            return f
    return None


def hijacks(parse):
    """v2 (teste DECISIVO): o parser do candidato ENGOLE uma forma existente como header tipado?"""
    out = []
    for f in FORMAS_EXISTENTES:
        try:
            got = parse(f)
            out.append(f"{f!r}->tipo={got.get('tipo')!r}")
        except Exception:
            pass                            # rejeitar é o correto
    return out


def rodar():
    celulas = []
    for gname, (enc, parse) in GRAMATICAS.items():
        for tipo in TIPOS:
            for nature in NATURES:
                for nome_id, nome in NOMES:
                    cid = f"{gname}|t={tipo}|nat={nature}|nome={nome_id}"
                    try:
                        h = enc(tipo, nature, nome)
                    except Ambiguo as e:
                        celulas.append(dict(gramatica=gname, tipo=tipo, nature=nature,
                                            nome=nome_id, status="N/A", regra=str(e),
                                            header="", bytes=0, recupera="", colisao=""))
                        continue
                    try:
                        got = parse(h)
                        ok_nome = got["nome"] == (nome if nome != "" else None)
                        ok_tipo = (got["tipo"] == tipo) if tipo else True
                        ok_nat = (got["nature"] == nature) if nature else True
                        recupera = "sim" if (ok_nome and ok_tipo and ok_nat) else "NAO"
                        if got["tipo"] == "?":
                            recupera = "AMBIGUO(slot unico)"
                        status = "pass" if recupera == "sim" else "fail"
                    except Ambiguo as e:
                        recupera, status = f"erro: {e}", "fail"
                    col = rota_confundida(h, gname) or ""
                    if col:
                        status = "fail"
                    celulas.append(dict(gramatica=gname, tipo=tipo, nature=nature, nome=nome_id,
                                        status=status, regra="", header=h.replace("\n", "\\n"),
                                        bytes=len(h.encode()), recupera=recupera, colisao=col))

    # ---------- contraprovas: devem FALHAR ALTO ----------
    MALF = ["#TCF.8", "#TCF.8 ", "#TCF.8:", "#TCF.8: ", "#TCF.8:b\\", ":", ":b ", "#TCF.8M", "#TCF.8H"]
    malformados = []
    for gname, (_e, parse) in GRAMATICAS.items():
        for m in MALF:
            try:
                got = parse(m)
                rej = False
                det = f"ACEITOU: {got}"
            except Ambiguo as e:
                rej, det = True, f"rejeitou: {e}"
            except Exception as e:  # erro opaco = fail-loud ruim
                rej, det = True, f"rejeitou (OPACO {type(e).__name__}): {e}"
            malformados.append(dict(gramatica=gname, entrada=m.replace("\n", "\\n"),
                                    rejeitou=rej, detalhe=det))
    (OUT / "01-malformed-results.json").write_text(
        json.dumps(malformados, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- artefatos ----------
    with open(INT / "00-matrix.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(celulas[0].keys()))
        wr.writeheader(); wr.writerows(celulas)
    (INT / "01-cases.json").write_text(json.dumps(
        {"protocolo": PROTOCOLO, "gramaticas": list(GRAMATICAS),
         "tipos": TIPOS, "natures": NATURES, "nomes": [n for n, _ in NOMES],
         "formas_existentes": FORMAS_EXISTENTES, "malformados": MALF,
         "body": "CONGELADO (vigente)", "order_free": "FORA (adiado .9)"},
        ensure_ascii=False, indent=2), encoding="utf-8")

    # header byte a byte de um caso representativo por gramática
    brk = []
    for gname, (enc, _p) in GRAMATICAS.items():
        try:
            h = enc("b", "cpf", "idade")
        except Ambiguo as e:
            brk.append(f"{gname}: N/A — {e}"); continue
        brk.append(f"{gname}: {h!r}  ({len(h.encode())} B)")
        brk.append("  " + " ".join(f"{c!r}" for c in h))
    (INT / "02-header-breakdown.txt").write_text("\n".join(brk), encoding="utf-8")

    # ---------- resumo por gramática ----------
    resumo = {}
    for g, (_e, parse) in GRAMATICAS.items():
        cs = [c for c in celulas if c["gramatica"] == g]
        ap = [c for c in cs if c["status"] != "N/A"]
        ms = [m for m in malformados if m["gramatica"] == g]
        hj = hijacks(parse)
        resumo[g] = dict(
            aplicaveis=len(ap), passa=sum(1 for c in ap if c["status"] == "pass"),
            falha=sum(1 for c in ap if c["status"] == "fail"),
            na=sum(1 for c in cs if c["status"] == "N/A"),
            confundidas=sum(1 for c in cs if c["colisao"]),
            hijack=len(hj), hijack_det="; ".join(hj) or "—",
            malf_rejeitados=sum(1 for m in ms if m["rejeitou"]), malf_total=len(ms),
            bytes_min=min([c["bytes"] for c in ap], default=0),
        )

    L = ["# Ciclo A — cabeçalho single-col: tipo × nature × nome\n",
         f"Protocolo `{PROTOCOLO}` (matriz declarada em MANIFESTO.md ANTES de medir). BODY CONGELADO; "
         "só a moldura varia. `order_free` fora (adiado .9).\n",
         "## Resumo por gramática\n",
         "`hijack` = **teste decisivo**: o parser aceita uma forma EXISTENTE (`#TCF.8M/H/espaço/\\n`) "
         "como header tipado. Qualquer valor > 0 **refuta** o candidato — ele sequestra rotas do formato.\n",
         "| gramática | aplicáveis | pass | fail | N/A | **hijack** | rota confundida | malformados rejeitados | header mín (B) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for g, r in resumo.items():
        L.append(f"| {g} | {r['aplicaveis']} | {r['passa']} | {r['falha']} | {r['na']} | "
                 f"**{r['hijack']}** | {r['confundidas']} | {r['malf_rejeitados']}/{r['malf_total']} | "
                 f"{r['bytes_min']} |")
    L.append("\n**Detalhe dos hijacks:**\n")
    for g, r in resumo.items():
        L.append(f"- `{g}`: {r['hijack_det']}")

    L.append("\n## Headers representativos (tipo=b, nature=cpf, nome=idade)\n```")
    L += brk
    L.append("```")

    L.append("\n## Leitura\n")
    g1 = resumo["G1-slot-unico"]; g2 = resumo["G2-eixos-separados"]
    g3 = resumo["G3-tag-colada"]; g4 = resumo["G4-sem-assinatura"]
    L.append(f"- **G1 (slot único) — REFUTADA**: {g1['na']} células N/A porque tipo e nature NÃO CABEM "
             "JUNTOS num só slot; e quando só um cabe, o parser não sabe se o `{id}` é tipo ou nature "
             "(`AMBIGUO(slot unico)`). É exatamente a colisão tipo↔nature que o owner pediu pra ver. "
             "(Na v1 ela aparecia também com 33 'colisões' — era FALSO POSITIVO: G1 estende "
             "legitimamente a forma-espaço. A v2 separa extensão de colisão.)")
    L.append(f"- **G3 (tag colada) — REFUTADA pelo teste decisivo**: `hijack={g3['hijack']}` — o parser "
             "aceita as formas existentes como se fossem tipos (`#TCF.8M`→`tipo='M'`, `#TCF.8H`→"
             "`tipo='H'`). Pôr TIPO no índice 6 **sequestra o Eixo-1** (estrutura). Confirma a hipótese "
             "do manifesto — e só ficou visível com as tags adversariais `M`/`H` da v2.")
    L.append(f"- **G2 (eixos separados) — ÚNICA candidata que sobrevive**: {g2['passa']}/"
             f"{g2['aplicaveis']} recuperam a tripla (nome, tipo, nature), `hijack={g2['hijack']}`, "
             f"{g2['confundidas']} rotas confundidas. Tipo no discriminador `:`, nature no sufixo — "
             "namespaces distinguíveis (§S1.6). Custo: {0} B no caso com nome+nature.".format(g2['bytes_min']))
    L.append(f"- **G4 (sem assinatura)**: header mínimo ({g4['bytes_min']} B) e `hijack={g4['hijack']}`, "
             "mas **não identificável externamente** — perde §S1.1 (autocontenção) e §S1.7 (inspeção). "
             "Fica como PISO de comparação de bytes, não como candidata.")
    L.append("- **REQUISITO descoberto pelo lab (§S1.5 fail-loud)**: G2 é estruturalmente sã "
             "(`hijack=0`) mas aceita `#TCF.8:b\\` como `tipo='b\\'` — o escaping é validado no NOME, "
             "não na TAG. ⇒ a tag de tipo precisa de **namespace FECHADO (whitelist)**, não texto "
             "livre. É o único malformado que G2 aceita, e vira requisito da gramática, não detalhe "
             "de implementação.")
    L.append("- **Resposta à pergunta do owner (tipo × spec × nome)**: com **eixos separados**, um nome "
             "igual a uma tag de tipo (`b`) ou a um id de nature (`cpf`) **deixa de ser problema** — "
             "cada campo vive num namespace próprio e o escaping + split no último `:` não-escapado "
             "resolve nomes com `:`/espaço/`\\`/`\\n`. O conflito só existe quando os eixos são "
             "compartilhados (G1) ou quando o tipo invade o eixo de estrutura (G3).")
    L.append("- **Nome adversarial**: o escaping de `:`/`\\`/`\\n` + split no ÚLTIMO `:` não-escapado "
             "(convenção do multi-col real) sustenta nome `a:b`, `M`, `H`, `b` e `cpf` sem colisão nas "
             "gramáticas de eixos separados. **Nome igual a tag de tipo ou a id de nature deixa de ser "
             "problema quando os eixos são separados** — é o achado central pra pergunta do owner.")
    L.append(f"\n**{len(celulas)} células · {sum(1 for c in celulas if c['status']=='fail')} fail · "
             f"{sum(1 for c in celulas if c['status']=='N/A')} N/A · malformados: "
             f"{sum(1 for m in malformados if m['rejeitou'])}/{len(malformados)} rejeitados.** "
             "Artefatos: `intermediates/00-matrix.csv`, `01-cases.json`, `02-header-breakdown.txt`, "
             "`outputs/01-malformed-results.json`. Regenera: `python run.py`.")
    (AQUI / "result.md").write_text("\n".join(L), encoding="utf-8", newline="\n")
    print(f"OK · {len(celulas)} celulas · {sum(1 for c in celulas if c['status']=='fail')} fail · "
          f"{sum(1 for c in celulas if c['status']=='N/A')} N/A")
    return 0


if __name__ == "__main__":
    raise SystemExit(rodar())

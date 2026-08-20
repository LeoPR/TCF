"""REAVALIACAO do split (pedida pelo owner): e se os campos forem COLUNAS DE VERDADE
no meta, com uma marca de GRUPO — em vez de um #TCF.8M aninhado dentro de um slot?

A CRITICA (owner, 2026-08-17)
-----------------------------
1. "a estrutura nao precisa [do #TCF no meio] — ele poderia comprimir normalmente o
   algoritmo de duas colunas sem criar um #TCF de fato... nao faz sentido"
2. "e' mais facil pensar que sao realmente duas colunas, so' que indicar algo no header
   pra dizer que as duas colunas sao um grupo de uma coluna so'"
3. "o split me parece pouco stream, e so' faria sentido em colunas que tem um spec que
   peca pra avaliar isso antes"
4. a preocupacao: "um IF bem grande em vez de reaproveitar tudo que ja' esta' pronto —
   basta tratar como dois campos dict, sem nome, com a dica de um nome agrupador"

ESTE LAB constroi o formato-grupo COMO MOCK (dirty; src/tcf INTOCADO) reusando os
candidatos existentes como biblioteca, e compara wire-a-wire com o slot atual.

A GRAFIA DO MOCK (detalhe reversivel — memoria project_marcadores_abstratos_congelados:
o char e' so' a saida; o que se avalia aqui e' a ESTRUTURA, o achatamento):

    meta:  &<nf><template-esc>=<nome> , <campo1> , <campo2> , ... , <campoN>
           onde cada <campo> = [modo]<size-hex>   (coluna ANONIMA normal — sem =nome)
    corpo: os corpos dos campos, concatenados na ordem — como QUALQUER coluna do .8M

    O template viaja no meta (escapado), porque ele e' META de verdade: descreve como
    reintercalar. As partes nao-digito sao separadas por `|` com escape `\\`.

O QUE MUDA DE ESTRUTURA (nao de grafia):
  - ZERO recursao: nenhum #TCF.8M aninhado, nenhum sub-header, nenhuma moldura <ntmpl>.
  - Os campos sao colunas do PROPRIO meta -> o plano de fatias [ini:fim) de cada campo
    sai da linha 1, SEM decodar. (Hoje o slot e' caixa-preta: view.py:232,:438 — split
    "exige decode" e "cai em fallback".)
  - Nomes c0..cN somem por construcao (colunas anonimas ja' existem — ADR-0029).

§RT em tudo; evidencia obrigatoria em outputs/ (os DOIS formatos, lado a lado).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

IN = AQUI / "inputs"
OUT = AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                          # noqa: E402
from tcf.multi.core import _fallback_safe, _decode_raw_body   # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode, _decode_v2b       # noqa: E402
from tcf.multi.split import _struct_split_encode              # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE                     # noqa: E402


def B(x):
    return len(x.encode("utf-8")) if isinstance(x, str) else len(x)


# ── os candidatos POR CAMPO: exatamente os que o sub-table real usa ────────
def melhor_campo(vals):
    """min(tcf, raw, dict) por campo — o MESMO min() do sub-table do split real.
    (sem split: campo e' digito puro, o proprio ADR-0026 nota que nao recursa)"""
    corpo, modo = encode(vals, stamp=False).encode("utf-8"), ""
    if _fallback_safe(vals):
        rb = "\n".join(vals).encode("utf-8")
        if len(rb) < len(corpo):
            corpo, modo = rb, "!"
    vb = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if vb is not None and len(vb) < len(corpo):
        corpo, modo = vb, "@"
    return corpo, modo


def decoda_campo(corpo: bytes, modo: str):
    """O decoder de CAMPO e' o decoder de COLUNA que ja' existe — nenhum ramo novo.
    (o _decode_v2b deriva n do proprio stream: largura fixa por indice)"""
    if modo == "!":
        return _decode_raw_body(corpo)
    if modo == "@":
        return _decode_v2b(corpo)
    return decode(corpo.decode("utf-8"))


# ── template: extrai as partes nao-digito (mesma nocao do split real) ──────
def template_de(v: str):
    partes, campos, atual, digito = [], [], "", None
    for ch in v:
        d = ch.isdigit()
        if digito is None:
            digito = d
        if d != digito:
            (campos if digito else partes).append(atual)
            atual, digito = "", d
        atual += ch
    (campos if digito else partes).append(atual)
    # normaliza: partes = nf+1 (pode comecar/terminar com campo)
    out_p, out_c, i_p, i_c = [], [], 0, 0
    esperado_parte = not v[0].isdigit()
    seq = []
    # reconstroi em sequencia alternada comecando por parte (vazia se preciso)
    i, atual, digito = 0, "", None
    seq2 = []
    for ch in v:
        d = ch.isdigit()
        if digito is None:
            digito = d
            atual = ch
            continue
        if d != digito:
            seq2.append((digito, atual))
            atual, digito = ch, d
        else:
            atual += ch
    seq2.append((digito, atual))
    partes, campos = [], []
    if seq2[0][0]:                      # comeca com digito -> parte vazia na frente
        partes.append("")
    for eh_digito, tok in seq2:
        (campos if eh_digito else partes).append(tok)
    if not seq2[-1][0]:
        pass
    else:
        partes.append("")               # termina com digito -> parte vazia no fim
    return partes, campos


def separa(vals):
    """Aplica o template do 1o valor a todos; None se nao-uniforme (o gate)."""
    partes0, campos0 = template_de(vals[0])
    nf = len(campos0)
    colunas = [[] for _ in range(nf)]
    for v in vals:
        p, c = template_de(v)
        if p != partes0 or len(c) != nf:
            return None, None
        for k, tok in enumerate(c):
            colunas[k].append(tok)
    return partes0, colunas


# ── o MOCK do formato-grupo ────────────────────────────────────────────────
def esc(s):
    return s.replace("\\", "\\\\").replace("|", "\\|").replace(",", "\\,").replace("=", "\\=")


def unesc(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(s[i + 1]); i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)


def encode_grupo(nome, vals):
    """Wire completo de 1 coluna-grupo: campos como colunas REAIS do meta."""
    partes, colunas = separa(vals)
    assert partes is not None, "gate: template nao-uniforme"
    corpos, entradas = [], []
    for k, col in enumerate(colunas):
        corpo, modo = melhor_campo(col)
        corpos.append(corpo)
        ultima = (k == len(colunas) - 1)
        entradas.append(f"{modo}{'' if ultima else format(len(corpo), 'x')}")
    tmpl = "|".join(esc(p) for p in partes)
    meta = f"&{len(colunas):x}{tmpl}={esc(nome)}," + ",".join(entradas)
    return ("#TCF.8M" + meta + "\n").encode("utf-8") + b"".join(corpos)


def decode_grupo(wire: bytes):
    """Decoder do mock: fatia pelos sizes do meta (SEM abrir blob), reintercala."""
    l1, corpo = wire.split(b"\n", 1)
    meta = l1.decode("utf-8")[len("#TCF.8M"):]
    assert meta[0] == "&"
    # &<nf><template>=<nome>,<campos...>   (parse simples do mock; escapes de | , =)
    i = 1
    j = i
    while meta[j] in "0123456789abcdef":
        j += 1
    nf = int(meta[i:j], 16)
    # acha o '=' nao-escapado que fecha o template
    k, depth = j, 0
    while True:
        if meta[k] == "\\":
            k += 2; continue
        if meta[k] == "=":
            break
        k += 1
    tmpl_raw = meta[j:k]
    partes = [unesc(p) for p in _split_unesc(tmpl_raw, "|")]
    resto = meta[k + 1:]
    # nome ate' a 1a virgula nao-escapada; depois as entradas dos campos
    toks = _split_unesc(resto, ",")
    nome = unesc(toks[0])
    entradas = toks[1:]
    assert len(entradas) == nf
    # plano de fatias — SO' da linha 1
    plano, off = [], 0
    for e in entradas[:-1]:
        modo = e[0] if e[:1] in ("!", "@") else ""
        size = int(e[1:] if modo else e, 16)
        plano.append((modo, off, off + size))
        off += size
    e = entradas[-1]
    modo = e[0] if e[:1] in ("!", "@") else ""
    plano.append((modo, off, None))
    # decoda cada campo e reintercala — cada um e' autossuficiente
    campos = []
    for modo, ini, fim in plano:
        blob = corpo[ini:fim] if fim else corpo[ini:]
        campos.append(decoda_campo(blob, modo))
    n = len(campos[0])
    out = []
    for r in range(n):
        out.append("".join(partes[k] + campos[k][r] for k in range(nf)) + partes[nf])
    return nome, out, plano


def _split_unesc(s, sep):
    out, atual, i = [], "", 0
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            atual += s[i:i + 2]; i += 2; continue
        if s[i] == sep:
            out.append(atual); atual = ""; i += 1; continue
        atual += s[i]; i += 1
    out.append(atual)
    return out


# ── os casos (os 3 que o split VENCE no lab 1500 + o CEP real) ─────────────
def casos():
    precos = [f"{p}.{c:02d}" for p in
              [12, 45, 7, 103, 88, 45, 12, 250, 7, 61, 45, 12] for c in (0, 50, 99)][:24]
    datas = [f"2026-{m:02d}-{d:02d}" for m in (1, 2, 3) for d in (5, 12, 19, 26)] * 2
    import random
    rng = random.Random(7)
    fones = [f"(11) 9{rng.randrange(10**4):04d}-{rng.randrange(10**4):04d}" for _ in range(12)] + \
            [f"(21) 9{rng.randrange(10**4):04d}-{rng.randrange(10**4):04d}" for _ in range(12)]
    yield "c1-decimal", precos
    yield "c2-data-iso", datas
    yield "c6-telefone", fones
    # CEP real (Shaper, mesmo request do lab 1200)
    from shaper import Shaper, ShapeRequest
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj-enderecos", volume=20000,
                                    seed=42, stratify_by="uf"))
    rows = r.tables[list(r.tables)[0]]
    ceps = [f"{x['cep'][:5]}-{x['cep'][5:]}" for x in rows
            if x.get("cep") and len(x["cep"]) == 8 and x["cep"].isdigit()]
    yield "cep-real", ceps


def main():
    print("=" * 92)
    print("SPLIT COMO GRUPO NO META — o mock contra o slot atual")
    print("=" * 92)
    res = []
    for cid, vals in casos():
        # formato ATUAL: wire completo de 1 coluna (o min() escolhe; nesses casos, split)
        w_atual = encode({cid: vals})
        assert decode(w_atual) == {cid: vals}
        modo_atual = w_atual[7:8]

        # formato GRUPO (mock)
        w_grupo = encode_grupo(cid, vals)
        nome, volta, plano = decode_grupo(w_grupo)
        assert nome == cid and volta == vals, f"{cid}: RT do mock FALHOU"

        (IN / f"{cid}.json").write_text(json.dumps(vals[:60], ensure_ascii=False),
                                        encoding="utf-8", newline="")
        (OUT / f"{cid}.atual.tcf").write_text(w_atual, encoding="utf-8", newline="")
        (OUT / f"{cid}.grupo.mock-tcf").write_bytes(w_grupo)
        (OUT / f"{cid}.roundtrip.json").write_text(
            json.dumps(volta[:60], ensure_ascii=False), encoding="utf-8", newline="")

        ba, bg = B(w_atual), len(w_grupo)
        res.append({"caso": cid, "n": len(vals), "atual": ba, "grupo": bg,
                    "delta": bg - ba, "modo_atual": modo_atual,
                    "plano_fatias": [(m, i, f) for m, i, f in plano],
                    "rt_mock": True})
        print(f"\n### {cid}  (n={len(vals)}, modo atual={modo_atual!r})")
        print(f"  atual (slot aninhado) : {ba:>8,} B")
        print(f"  grupo (mock, plano)   : {bg:>8,} B   delta = {bg-ba:+,} B")
        l1a = w_atual.split(chr(10))[0]
        l1g = w_grupo.split(b"\n")[0].decode("utf-8")
        print(f"  meta atual : {l1a[:76]!r}")
        print(f"  meta grupo : {l1g[:76]!r}")
        print(f"  FATIAS dos campos, direto da linha 1 (sem decodar nada):")
        for k, (m, i, f) in enumerate(plano):
            print(f"    campo {k}: modo={m or 'tcf'!r:5} [{i}:{f if f else 'EOF'})")

    print("\n" + "=" * 92)
    print(f"{'caso':14} {'atual':>9} {'grupo':>9} {'delta':>8}   o que o grupo DESTRAVA")
    print("-" * 92)
    for r in res:
        print(f"{r['caso']:14} {r['atual']:>9,} {r['grupo']:>9,} {r['delta']:>+8,}"
              f"   fatias por campo na linha 1 (view/paralelo alcancam)")
    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    n_ev = len(list(OUT.glob("*.tcf"))) + len(list(OUT.glob("*.mock-tcf")))
    assert n_ev == 2 * len(res), f"evidencia incompleta: {n_ev}"
    print(f"\n-> {n_ev} wires em outputs/ (atual + grupo por caso), RT validado nos dois")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

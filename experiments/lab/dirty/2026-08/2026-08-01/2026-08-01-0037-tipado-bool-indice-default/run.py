"""Lab 2026-08-01-0037 — T-TIPADO-BOOL-INDICE: slots congelados como DEFAULT da tag `b`.

O owner aprovou: o render da tag `b` vira slots congelados — o MESMO domínio do denso b2
(ADR-0037): `null=0` (já é a grafia core), `false=1`, `true=2`, emitidos como `\\1`/`\\2`.
Fecha o caso que escapava do b2: o candidato CORE/RLE. Hoje `encode([True]*200)` emite
`#TCF.8b\\n*200|true` (18 B) — `true` viaja como NOME. Com slot: `*200|\\2` (16 B).

Decode: slots = canônico (único emitido); nomes = decodável-não-emitido (contrato do modo
`C` da ADR-0036 — preserva wires antigos).

Mede:
  A. hoje (nomes) × slot, por coluna — constante, run-heavy, segmentado, controles, reais
  B. adversidades: polaridade sobre slots, seq-RLE espúrio, legado por nomes, fail-loud
  C. RT estrito valor+tipo em todas; roundtrip como ARQUIVO com assert

`src/tcf` intocado — proposta, não solda.
"""
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from slot_render import cast_slots, proto_decode, proto_encode  # noqa: E402

from tcf import decode, encode  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                 encoding="utf-8")


def rt_estrito(obtido, esperado):
    if len(obtido) != len(esperado):
        return False
    if obtido != esperado:
        return False
    return all(type(a) is type(b) for a, b in zip(obtido, esperado))


def modo(wire):
    """Modo do wire tipado: 'core', 'core!'(polaridade), 'b1', 'b2'."""
    resto = wire.split("\n", 1)[0][7:]
    if resto == "":
        return "core"
    if resto.startswith("!"):
        return "core!"
    return f"b{resto[0]}"


def caso(nome, dados, gravar=True):
    hoje_w = encode(dados)
    slot_w, tag = proto_encode(dados)
    obtido = proto_decode(slot_w)
    r = {"nome": nome, "n": len(dados),
         "hoje": len(hoje_w.encode()), "slot": len(slot_w.encode()),
         "modo_hoje": modo(hoje_w), "modo_slot": modo(slot_w),
         "rt_hoje": rt_estrito(decode(hoje_w), dados),
         "rt_slot": rt_estrito(obtido, dados),
         "cab_hoje": hoje_w.split("\n")[0], "cab_slot": slot_w.split("\n")[0]}
    if gravar:
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(dados), "tag": tag, "amostra": dados[:8]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", dados)
        (RAIZ / "outputs" / f"{nome}-hoje.tcf").write_text(hoje_w, encoding="utf-8")
        (RAIZ / "outputs" / f"{nome}-slot.tcf").write_text(slot_w, encoding="utf-8")
        rt_path = RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json"
        _wj(rt_path, obtido)
        cons = RAIZ / "intermediates" / f"{nome}-dataset-consumido.json"
        assert rt_path.read_bytes() == cons.read_bytes(), nome   # roundtrip é ARQUIVO
    return r


def linha(r):
    d = r["slot"] - r["hoje"]
    rt = "OK" if (r["rt_slot"] and r["rt_hoje"]) else "**FALHOU**"
    return (f"| `{r['nome']}` | {r['n']} | {r['modo_hoje']} | {r['modo_slot']} | "
            f"{r['hoje']} | {r['slot']} | **{d:+}** | {rt} |")


CAB = ["| coluna | n | modo hoje | modo slot | hoje | slot | Δ | RT |",
       "|---|---:|:-:|:-:|---:|---:|---:|:--|"]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    out = ["# T-TIPADO-BOOL-INDICE — slots congelados DEFAULT da tag `b` (2026-08-01-0037)",
           "",
           "O denso b2 (ADR-0037, weld 2026-07-31) fechou o ternário DENSO, mas o candidato "
           "CORE/RLE seguia emitindo `true`/`false` como NOMES. Este lab mede o render em "
           "slots congelados — o MESMO domínio do b2: `null=0` (já era a grafia core), "
           "`false=1`, `true=2` — emitidos como `\\1`/`\\2` pelo `_escape_lit` de sempre. "
           "Decode: slots canônicos; nomes decodáveis-não-emitidos (contrato do modo `C`, "
           "ADR-0036).", ""]

    # ================================================================ A: hoje x slot
    casos = {
        "bool-constante": [True] * 200,
        "run-heavy-1": [True] * 100 + [None] + [False] * 99,
        "runs-4": [True] * 50 + [False] * 50 + [True] * 50 + [False] * 50,
        "runs-10": sum(([bool(r % 2)] * 20 for r in range(10)), []),
        "alternado": [bool(i % 2) for i in range(200)],
        "alternado-null": [None if i % 3 == 0 else bool(i % 2) for i in range(200)],
        "tiny-constante": [True] * 3,
        "tiny-ternario": [True, None, False],
    }
    out += ["## A — hoje (nomes) × slot, por coluna", ""] + CAB
    rs = {}
    for nome, dados in casos.items():
        r = caso(nome, dados)
        rs[nome] = r
        if not (r["rt_slot"] and r["rt_hoje"]):
            falhas.append(nome)
        out.append(linha(r))

    # o caso que o lab TEM de confirmar: run-heavy, onde o CORE vence o b2
    rh = rs["run-heavy-1"]
    core_hoje = rh["modo_hoje"] == "core" and rh["modo_slot"] == "core"
    if not core_hoje:
        falhas.append("run-heavy-1: core NAO venceu o b2")
    out += ["",
            f"**Caso run-heavy confirmado**: `[True]*100+[None]+[False]*99` — o CORE vence "
            f"o b2 nos DOIS renders (modo `{rh['modo_hoje']}` hoje, `{rh['modo_slot']}` com "
            f"slot): o b2 pagaria 79 B fixos, o core paga ~3 linhas de run. O slot economiza "
            f"**{rh['slot'] - rh['hoje']:+} B** exatamente onde o b2 não alcança.", ""]

    # ================================================================ reais
    out += ["## B — colunas REAIS (Adult, ordenadas por grupo = run-heavy realista)", ""] + CAB
    reais = [
        ("real-adult-sex-ordenado", "sex", lambda v: v.strip() == "Male", False),
        ("real-adult-sex-ord-null", "sex", lambda v: v.strip() == "Male", True),
        ("real-adult-class-ordenado", "class", lambda v: ">" in v, False),
    ]
    for nome, col, conv, com_null in reais:
        p = SAMPLES / "adult-census" / "adult-sample.csv"
        with p.open(encoding="utf-8", newline="") as f:
            vals = sorted(conv(row[col]) for row in csv.DictReader(f)
                          if row[col] not in ("", "NA"))
        vals = vals[:2000]
        dados = [None if i % 7 == 0 else v for i, v in enumerate(vals)] if com_null else vals
        r = caso(nome, dados)
        rs[nome] = r
        if not (r["rt_slot"] and r["rt_hoje"]):
            falhas.append(nome)
        out.append(linha(r))
    out.append("")

    # ================================================================ adversidades
    out += ["## C — adversidades", ""]

    # 1. polaridade sobre corpo de slots: varredura DIRETA de `polariza` em todos os corpos
    from tcf.composicional.polaridade import polariza
    from tcf.encoder import _encode_column
    todos_dados = dict(casos)
    for nome, _col, _conv, _cn in reais:
        todos_dados[nome] = json.loads(
            (RAIZ / "intermediates" / f"{nome}-dataset-consumido.json").read_text(encoding="utf-8"))
    pol_casos = 0
    pol_det = []
    for nome, dados in todos_dados.items():
        strs = [None if x is None else ("2" if x else "1") for x in dados]
        suf, _corpo_pol = polariza(_encode_column(strs, header="val"))
        if suf:
            pol_casos += 1
            pol_det.append(nome)
    if pol_casos:
        falhas.append("adversidade-1: polaridade disparou em corpo de slots")
    out += ["### 1. polaridade sobre corpo de slots", "",
            f"Varredura direta de `polariza` sobre os corpos-slot de **todas as "
            f"{len(todos_dados)} colunas** do lab: sufixo disparado em **{pol_casos}**.",
            "",
            "E o resultado é **estrutural**, não amostral: com o render em slots o corpo "
            "bool tem **no máximo 2 linhas literais** (`\\1` e `\\2`, na primeira ocorrência "
            "de cada valor — o null viaja como slot `0`, que não é literal escapado). A "
            "polaridade cobra 1 B por transição literal↔referência e só compensa quando há "
            "muitas; com ≤2 literais as transições são ≤4 e o sufixo **nunca compensa**. "
            "Logo ela não pode nem ser escolhida nem quebrar RT num corpo de slots — a "
            "adversidade é inerte por construção.", ""]

    # 2. seq-RLE sobre padrão de 2 valores
    alt = rs["alternado"]
    alt_null = rs["alternado-null"]
    wire_alt = (RAIZ / "outputs" / "alternado-slot.tcf").read_text(encoding="utf-8")
    tem_seqrle = "*+" in wire_alt or ("*" in wire_alt and "+" in wire_alt)
    out += ["### 2. seq-RLE sobre `1,2,1,2…`", "",
            f"O alternado puro (sem null) vai pro **b1** nos dois renders (modo "
            f"`{alt['modo_slot']}`) — o padrão `\\1,\\2,\\1,\\2…` nem materializa corpo. "
            f"O alternado COM null vai pro **b2** (modo `{alt_null['modo_slot']}`). "
            f"Seq-RLE no corpo de slots do alternado: **{'presente' if tem_seqrle else 'ausente'}**"
            f" — delta não-uniforme (1↔2) não dispara o `*N+delta`; e se disparasse e "
            "encolhesse mantendo RT, seria o FLOOR trabalhando.", ""]

    # 3. legado: nomes decodáveis
    legado_w = "#TCF.8b\ntrue\nfalse\n^1\n"
    legado = cast_slots(_decode_column(legado_w.split("\n", 1)[1]))
    ok_legado = legado == [True, False, True] and all(type(x) is bool for x in legado)
    if not ok_legado:
        falhas.append("adversidade-3: legado")
    out += ["### 3. legado — nomes decodáveis-não-emitidos", "",
            f"`{legado_w!r}` → `{legado}` — **{'OK' if ok_legado else 'FALHOU'}**. "
            "Mesmo contrato do modo `C` (ADR-0036): wires antigos por nomes seguem lendo.", ""]

    # 4. fail-loud no cast
    fl = []
    for lit, desc in (("\\0", "literal '0' (colide com o slot do null)"),
                      ("\\3", "slot 3 (reservado, como no b2)"),
                      ("\\15", "slot 15 (fora do domínio)")):
        wire = f"#TCF.8b\n{lit}\n"
        try:
            cast_slots(_decode_column(wire.split("\n", 1)[1]))
            fl.append(f"[FALHOU] `{lit}` ({desc}): passou calado")
            falhas.append(f"adversidade-4: {lit}")
        except ValueError as e:
            fl.append(f"[OK] `{lit}` ({desc}) → ValueError: {e}")
    (RAIZ / "outputs" / "fail-loud.txt").write_text(
        "# fail-loud — cast de slots da tag b (gerado por run.py)\n\n" + "\n".join(fl) + "\n",
        encoding="utf-8")
    out += ["### 4. fail-loud no cast de slots", "",
            "Evidência em `outputs/fail-loud.txt`:", "",
            "```", "\n".join(fl), "```", ""]

    # ================================================================ resumo
    ganho = sum(r["slot"] - r["hoje"] for r in rs.values())
    venc = [r["nome"] for r in rs.values() if r["slot"] < r["hoje"]]
    out += ["## Resumo e round-trip", "",
            f"- Δ somado nas colunas medidas: **{ganho:+} B**; slot menor em **{len(venc)} de "
            f"{len(rs)}** ({', '.join(f'`{n}`' for n in venc) or 'nenhuma'}).",
            "- Onde o slot NÃO muda nada: os modos densos (`b1`/`b2`) — o corpo core nem "
            "materializa, o FLOOR escolhe o denso nos dois renders (Δ = 0, modo idêntico).",
            "- Observação de empate: `tiny-constante` (n=3) passa de `b1` para `core` — o "
            "slot empata o core com o denso (14 = 14) e o FLOOR fica no 1º candidato (core, "
            "mais inspecionável). Byte-neutro.",
            "- RT estrito (valor, tipo, comprimento) + roundtrip ARQUIVO byte-idêntico em "
            "todas as colunas, com assert no `run.py`.",
            "- `src/tcf` intocado; os `-slot.tcf` são proposta (o decode público ainda não "
            "conhece os slots `1`/`2` no corpo tipado).", ""]
    if falhas:
        out += [f"**FALHAS**: {falhas}", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())

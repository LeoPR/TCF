"""Conformidade de FLUXO por tipo — onde o int diverge do bool. `python run.py`

## Por que este lab NÃO mede compressão

Direção do owner (2026-08-14):

> *"o fluxo tem que ser generalizado […] ter um código exclusivo pros tipos deixa o código
> mais engessado […] precisamos que isso seja uma OTIMIZAÇÃO, não um padrão do tcf. então
> como mesmo o bool respeita o fluxo, então é justo pensar no int também […] só vamos
> padronizar pro int também, ver o que de algoritmos já temos que se encaixa nele."*

Os ganhos já foram medidos (labs de 22h58 e 23h26). A pergunta agora é **estrutural**: o int
percorre o MESMO caminho que o bool? Onde diverge, a divergência é **justificada** (como o
denso, que tem razão escrita no código) ou é **lacuna**?

## Os 5 eixos de conformidade

    1. DISPATCH    o tipo é detectado? por qual função? qual tag sai?
    2. CANDIDATOS  quais o `min()` alcança — por REGIME que ativa cada um
    3. API         `nature=` é aceito, recusado fail-loud, ou IGNORADO CALADO?
    4. WIRE        a tag aparece? convive com `:id` de spec?
    5. RT          volta com o tipo certo? (comparado por `type()`, não por `==`)

Cada célula é medida, nunca inferida. `src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import json
import pathlib
import random
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402
from tcf.natures import SPEC_CPF, SPEC_DATA_ISO  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N = 600
rnd = random.Random(20260814)


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def _limpa():
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)


def tipo_igual(a, b) -> bool:
    if len(a) != len(b):
        return False
    return all(type(x) is type(y) and x == y for x, y in zip(a, b))


def disc(wire: str) -> str:
    """O discriminador do índice 7 em diante, até a 1a quebra — a 'assinatura de rota'."""
    l0 = wire.split("\n")[0]
    return l0[6:] if l0.startswith("#TCF.8") else "(sem magic)"


# ── os TIPOS sob teste, cada um com regimes que ativam candidatos diferentes ──
#    O MESMO regime conceitual em cada tipo: é isso que torna a matriz comparável.
TIPOS = {
    "bool": {
        "constante": [True] * N,                                   # RLE
        "duas-classes": [rnd.random() < 0.5 for _ in range(N)],    # denso/bN
        "com-nulo": [None if i % 37 == 0 else (i % 2 == 0) for i in range(N)],
    },
    "int": {
        "constante": [42] * N,
        "duas-classes": [rnd.choice([10, 20]) for _ in range(N)],
        "com-nulo": [None if i % 37 == 0 else i for i in range(N)],
        "progressao": list(range(1, N + 1)),                        # seq-RLE
        "baixa-card": [rnd.choice([10, 20, 30, 40, 50]) for _ in range(N)],  # bN
    },
    "float": {
        "constante": [4.2] * N,
        "duas-classes": [rnd.choice([1.5, 2.5]) for _ in range(N)],
        "com-nulo": [None if i % 37 == 0 else i + 0.5 for i in range(N)],
        "progressao": [i + 0.5 for i in range(1, N + 1)],
        "baixa-card": [rnd.choice([1.5, 2.5, 3.5, 4.5, 5.5]) for _ in range(N)],
    },
    "str": {
        "constante": ["x"] * N,
        "duas-classes": [rnd.choice(["a", "b"]) for _ in range(N)],
        "com-nulo": [None if i % 37 == 0 else str(i) for i in range(N)],
        "progressao": [str(i) for i in range(1, N + 1)],
        "baixa-card": [rnd.choice(["a", "b", "c", "d", "e"]) for _ in range(N)],
    },
}


def _vered(w, base, side):
    """Veredito OBJETIVO do eixo 3, via telemetria — não por diferença de bytes.

    DUAS versões anteriores erraram aqui, e o erro é instrutivo: "wire idêntico ao
    baseline" NÃO distingue *o FLOOR recusou o candidato* (comportamento correto) de
    *o parâmetro nem foi olhado* (o buraco). A 1a versão usou um spec que não mordia os
    dados; a 2a usou um que mordia, mas o FLOOR ainda podia recusar por não pagar.

    O critério que resolve: `SideOutputs.nature_apply` só é populado quando a nature é
    PROCESSADA — mas veja a ressalva abaixo.

    
    TERCEIRA correção, e a razão importa: telemetria ausente também não prova nada
    sozinha. Medido — a rota `.8H` PROCESSA a nature (wire 1841→1826 B, header ganha
    `:cpf`, RT ok) e mesmo assim deixa `nature_apply = None`. Ela não reporta essa
    telemetria; ausência ali é lacuna de INSTRUMENTAÇÃO, não de funcionalidade.

    Critério final, em ordem: o wire mudou ⇒ aceito (evidência direta, dispensa
    telemetria). Wire igual + telemetria ⇒ competiu e o FLOOR recusou. Wire igual +
    sem telemetria ⇒ sem efeito observável, e só a COMPARAÇÃO ENTRE TIPOS diz se isso é
    contrato (recusar) ou assimetria (calar).
    """
    if w != base:
        return "ACEITO e aplicado (wire mudou)"
    ap = getattr(side, "nature_apply", None)
    if ap:
        return "processado, FLOOR recusou (contrato correto)"
    return "sem efeito e SEM AVISO"


def eixo_api(vals, tipo):
    """Eixo 3: `nature=` é aceito, recusado fail-loud, ou IGNORADO CALADO?

    Distinguir os três importa: 'recusado' é contrato; 'ignorado calado' é o usuário
    pedir uma coisa e receber outra sem aviso — o que o projeto proíbe por regra.

    ARMADILHA DE MEDIÇÃO (corrigida 2026-08-14, 1a versão caiu nela): "wire idêntico ao
    baseline" NÃO prova que o parâmetro foi ignorado — pode ser o FLOOR recusando um
    candidato que não paga. A 1a versão usava `SPEC_CPF` numa coluna `['a','b']`, onde o
    spec não se aplica a valor nenhum, e classificou o FLOOR correto como "IGNORADO
    CALADO" para `str`. Agora: para a coluna de STRING usa-se um spec que REALMENTE
    transforma (CPFs válidos), e o veredito só é "ignorado" quando o spec se aplicaria.
    """
    out = {}
    if tipo == "str":
        # dados em que o spec MORDE — senão o FLOOR recusa e a leitura vira falso-positivo
        vals = ["529.982.247-25", "111.444.777-35"] * (len(vals) // 2)
        spec = SPEC_CPF
        aplica = True   # informativo: o spec MORDE estes dados
    else:
        spec = SPEC_CPF          # em coluna tipada nenhum spec se aplica; mede-se o TRATAMENTO
        aplica = False  # informativo: em coluna tipada nenhum spec morde
    base = encode(vals)
    # single: nature=
    try:
        so = SideOutputs(); w = encode(vals, nature=spec, side_outputs=so)
        out["single nature="] = _vered(w, base, so)
    except Exception as e:
        out["single nature="] = f"recusa fail-loud: {type(e).__name__}"
    # single: nature_per_col= (o buraco ao lado do portao)
    try:
        so = SideOutputs(); w = encode(vals, nature_per_col={"x": spec}, side_outputs=so)
        out["single nature_per_col="] = _vered(w, base, so)
    except Exception as e:
        out["single nature_per_col="] = f"recusa fail-loud: {type(e).__name__}"
    # multi
    tab = {"c": vals, "z": ["k"] * len(vals)}
    try:
        bm = encode(tab)
        so = SideOutputs(); wm = encode(tab, nature_per_col={"c": spec}, side_outputs=so)
        out["multi nature_per_col="] = _vered(wm, bm, so)
    except Exception as e:
        out["multi nature_per_col="] = f"recusa fail-loud: {type(e).__name__}"
    # .8H
    recs = [{"c": v} for v in vals]
    try:
        bh = encode(recs)
        so = SideOutputs(); wh = encode(recs, nature_per_col={"c": spec}, side_outputs=so)
        out[".8H nature_per_col="] = _vered(wh, bh, so)
    except Exception as e:
        out[".8H nature_per_col="] = f"recusa fail-loud: {type(e).__name__}"
    # decode com nature (o simetrico)
    # o decode so' pode ser cobrado se o wire CARREGA tag — sem tag, ignorar e'
    # comportamento DOCUMENTADO (ADR-0027: o parametro so' age quando ha' `:id`).
    tem_tag = ":" in base.split("\n")[0]
    try:
        got = decode(base, nature=SPEC_DATA_ISO)
        if not tem_tag:
            out["decode nature="] = "n/a (wire sem tag — ignorar e' documentado)"
        else:
            out["decode nature="] = ("IGNORADO CALADO" if tipo_igual(got, vals)
                                     else "aplicou")
    except Exception as e:
        out["decode nature="] = f"recusa fail-loud: {type(e).__name__}"
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _limpa()
    falhas, matriz = [], {}

    for tipo, regimes in TIPOS.items():
        linha = {"regimes": {}, "api": None, "rotas": {}}
        for reg, vals in regimes.items():
            _js(INP / f"{tipo}.{reg}.entrada.json", vals)
            # EIXO 1+2+4: dispatch e candidatos, lidos do wire emitido
            w = encode(vals)
            volta = decode(w)
            ok = tipo_igual(volta, vals)
            if not ok:
                falhas.append(f"{tipo}/{reg}: RT nao preservou tipo — "
                              f"entrou {type(vals[0]).__name__}, "
                              f"voltou {type(volta[0]).__name__}")
            corpo0 = w.split("\n")[1] if "\n" in w else ""
            linha["regimes"][reg] = {
                "disc": disc(w), "bytes": len(w.encode("utf-8")),
                "corpo_1a_linha": corpo0[:30],
                "rt_tipo": ok,
                # que MECANISMO venceu, lido da grafia (nao inferido)
                "venceu": ("denso" if disc(w)[:2] in ("b1", "b2")
                           else "bN" if "B" in disc(w)[:2]
                           else "lazy-bool" if disc(w).startswith("bB")
                           else "seq-RLE" if corpo0.startswith("*") and "+" in corpo0[:12]
                           else "RLE" if corpo0.startswith("*")
                           else "core/OBAT"),
            }
            _esc(OUT / f"{tipo}.{reg}.tcf", w)
            _js(OUT / f"{tipo}.{reg}.roundtrip.json", volta)

        # EIXO 3: API (uma vez por tipo, no regime 'duas-classes')
        linha["api"] = eixo_api(regimes["duas-classes"], tipo)

        # EIXO 4+5: a tag sobrevive nas 3 rotas?
        v = regimes["duas-classes"]
        for rota, feito in (
            ("single", lambda: (encode(v), decode(encode(v)))),
            ("multi", lambda: (encode({"c": v, "z": ["k"] * N}),
                               decode(encode({"c": v, "z": ["k"] * N}))["c"])),
            (".8H", lambda: (encode([{"c": x} for x in v]),
                             [d["c"] for d in decode([{"c": x} for x in v] and
                                                     encode([{"c": x} for x in v]))])),
        ):
            try:
                w, back = feito()
                linha["rotas"][rota] = {
                    "disc/meta": w.split("\n")[0][:34],
                    "rt_tipo": tipo_igual(back, v),
                }
                if not tipo_igual(back, v):
                    falhas.append(f"{tipo}/{rota}: RT nao preservou tipo")
            except Exception as e:
                linha["rotas"][rota] = {"erro": f"{type(e).__name__}: {str(e)[:60]}"}
        matriz[tipo] = linha

    _js(RAIZ / "resultado.json", {"matriz": matriz, "falhas": falhas})
    _js(INT / "matriz-completa.json", matriz)

    # ── relatório na tela ──
    print("EIXO 1+2+4 — dispatch, mecanismo vencedor e RT, por regime")
    regs = ["constante", "duas-classes", "com-nulo", "progressao", "baixa-card"]
    print(f"  {'tipo':6s} " + "".join(f"{r:22s}" for r in regs))
    for tipo, linha in matriz.items():
        cels = []
        for r in regs:
            d = linha["regimes"].get(r)
            cels.append(f"{d['disc'] or '(vazio)'}/{d['venceu']}" if d else "—")
        print(f"  {tipo:6s} " + "".join(f"{c:22s}" for c in cels))

    print("\nEIXO 3 — o que a API faz com `nature` (o mesmo spec, todos os tipos)")
    chaves = list(matriz["bool"]["api"].keys())
    for k in chaves:
        print(f"  {k:24s} " + " | ".join(f"{t}: {matriz[t]['api'][k][:24]}"
                                         for t in matriz))

    print("\nEIXO 5 — RT preserva o tipo, por rota")
    for tipo, linha in matriz.items():
        r = {k: (v.get("rt_tipo") if "erro" not in v else "ERRO") for k, v in linha["rotas"].items()}
        print(f"  {tipo:6s} {r}")

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

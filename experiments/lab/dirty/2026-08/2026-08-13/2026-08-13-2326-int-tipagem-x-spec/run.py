"""Inteiro: a MATRIZ tipagem × spec. `python run.py`

## O erro que este lab corrige

O lab das 22h58 mediu inteiro **só com fonte string**. O owner:

> *"porque os números estão como string em tudo? o json tem que colocar numeros como numeros,
> lembra da tipagem? [...] se a fonte é inteiro (como era boleano) e por algum motivo entra
> como string no dataset antes de entrar no tcf, se colocar um spec inteiro, o tcf internamente
> trata como inteiro, mas se o dataset estava string, então realmente volta string. se o dado
> era int [...] ele entra int, o spec é int, o tcf trata internamente como int, e devolve int."*

E, na correção seguinte: *"o caso de entrada string e spec int **também é válido**, mas o lab
só tem isso."*

**Não há caso primário e secundário — há dois, e o lab anterior cobria um.** Aqui a matriz
completa:

    FONTE      TRATAMENTO   o que o RT deve devolver
    string     core          string  (grafia byte-exata)
    string     spec int      string  (o spec transforma por DENTRO; a grafia volta)
    int        core          int     (a rota tipada `#TCF.8n` já faz)
    int        spec int      int     <- ESTA CÉLULA NÃO É EXPRESSÁVEL HOJE

A quarta célula é o achado: `nature=` recusa entrada tipada nas TRÊS rotas —
single (`kwargs ['nature'] so' valem no flat de STRING`), multi (`nature so' aplica a coluna
scalar-string`) e `.8H` (`é coluna TIPADA (number/bool), não string`). Ela é medida aqui por
SIMULAÇÃO honesta (transformação aplicada à mão + custo do header tipado), com o round-trip
verificado elemento a elemento **comparando TIPO, não só valor** — em Python `True == 1` e
`1 == 1.0`, e uma comparação ingênua mascararia exatamente o defeito que interessa.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import random
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
# os 3 alvos vêm do lab das 22h58 (mesma investigação, mesmo dia) — importados, não copiados,
# para que a definição tenha UMA fonte. Ver `../2026-08-13-2258-int-spec-faz-sentido/specs.py`.
sys.path.insert(0, str(RAIZ.parent / "2026-08-13-2258-int-spec-faz-sentido"))

from specs import alvos_para  # noqa: E402
from tcf import decode, encode  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N = 600
rnd = random.Random(20260813)


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def _limpa():
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)


def custo_parametro(alvo) -> int:
    """Bytes que o alvo precisaria ACRESCENTAR ao wire para ser AUTO-CONTIDO.

    ACHADO 2026-08-13 (o owner estranhou `gigante-64bit.str-spec.tcf`: *"o numero e'
    gigante mas o conteudo nao parece fazer sentido"*): o wire de 26 B era
    `#TCF.8 :xioff / *600+1|\\000` — o corpo e' 000..599 porque o OFFPAD subtraiu a base,
    e **a base de 19 digitos NAO esta' no wire**. O RT so' fechava porque eu passava o
    objeto do spec no decode. Prova do defeito: o MESMO wire devolve
    `['9223372036854775808']` com `base=2**63` e `['0']` com `base=0`, sem erro nenhum.

    Isto separa os alvos em duas classes, e a distincao e' de DESIGN, nao de medicao:

      AUTO-CONTIDO  o id no header basta; o decode deduz o resto do corpo.
                    - PAD: a largura e' visivel no corpo expandido (todas as linhas
                      tem o mesmo tamanho).
                    - B94: `int(b94)` da' o numero e a grafia canonica e' `str(n)`
                      (o spec ja' recusa zeros a' esquerda como nao-canonicos).
                    - E' a classe do `data-iso`/`cpf`/`cnpj`/`ip`: o ordinal e'
                      ABSOLUTO, nao relativo a nada.

      PARAMETRIZADO o id NAO basta — a base e' informacao PERDIDA, nao deduzivel.
                    - OFFPAD precisa da base. Isso **quebra o self-describing do
                      ADR-0027** (o decode nao resolve sozinho pelo registry).

    Retorna o custo de carregar o parametro no header, para a comparacao ser honesta.
    """
    base = getattr(alvo, "base", None)
    return 0 if base is None else len(str(base)) + 1   # o parametro + 1 separador


def igual_com_tipo(a, b) -> bool:
    """RT de verdade: `True == 1` e `1 == 1.0` em Python — comparar só valor MASCARA
    justamente o defeito de tipagem que este lab investiga."""
    if len(a) != len(b):
        return False
    return all(type(x) is type(y) and x == y for x, y in zip(a, b))


# (nome, gerador de INTEIROS, ideia)
REGIMES = [
    ("prog-passo1", lambda: list(range(1, N + 1)),
     "1..600: a largura varia (1->2->3 digitos) e quebra o marcador"),
    ("prog-passo7", lambda: [i * 7 for i in range(N)], "passo 7, largura de 1 a 4 digitos"),
    ("prog-largura-fixa", lambda: [100000 + i for i in range(N)],
     "largura JA' constante — o nucleo resolve sozinho"),
    ("prog-epoch", lambda: [1750000000 + i * 60 for i in range(N)],
     "timestamp: 10 digitos, passo 60"),
    ("prog-base-alta", lambda: [10**9 + i for i in range(N)],
     "1e9+i: so' os 3 ultimos digitos variam"),
    ("id-aleatorio-6", lambda: [rnd.randrange(100000, 999999) for _ in range(N)],
     "ids de 6 digitos, sem progressao"),
    ("id-aleatorio-11", lambda: [rnd.randrange(10**10, 10**11) for _ in range(N)],
     "ids de 11 digitos (regime do CPF sem mascara)"),
    ("faixa-0-100", lambda: [rnd.randrange(101) for _ in range(N)],
     "0..100: cardinalidade baixa, territorio do bN"),
    ("cardinalidade-5", lambda: [rnd.choice([10, 20, 30, 40, 50]) for _ in range(N)],
     "k=5: o bN de dominio ja' cobre"),
    ("quase-constante", lambda: [42] * (N - 3) + [43, 44, 45], "k=4 desbalanceado: RLE"),
    ("negativos", lambda: [rnd.randrange(-500, 501) for _ in range(N)], "com sinal"),
    ("com-nulos", lambda: [None if i % 37 == 0 else i for i in range(1, N + 1)],
     "slots NULOS no meio da progressao — o null e' do TIPO, nao da grafia"),
    ("gigante-64bit", lambda: [2**63 + i for i in range(N)],
     "acima de 2^63: fora do int64, so' Python/JSON aguentam"),
    ("misto-int-float", lambda: [i if i % 2 else i + 0.5 for i in range(N)],
     "int e float na MESMA coluna"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _limpa()
    falhas, tabela = [], []

    for nome, gen, ideia in REGIMES:
        ints = gen()
        strs = [None if v is None else str(v) for v in ints]
        _js(INP / f"{nome}.entrada-int.json", ints)
        _js(INP / f"{nome}.entrada-str.json", strs)
        _js(INP / f"{nome}.fonte.json", {
            "regime": nome, "ideia": ideia, "n": len(ints),
            "k_unicos": len(set(map(str, ints))), "primeiros_int": ints[:5],
            "primeiros_str": strs[:5],
            "hash_int": hashlib.sha256(json.dumps(ints, **JSON_KW).encode()).hexdigest()[:12],
            "CONSTANTE_na_comparacao": "os MESMOS valores nas 4 celulas; so' variam a FONTE "
                                       "(int x string) e o TRATAMENTO (core x spec). RT "
                                       "comparado com TIPO (type(x) is type(y)), nao so' valor.",
        })

        cel = {}

        # (1) fonte STRING + core
        w = encode(strs)
        cel["str+core"] = {"bytes": B(w), "header": w.split("\n")[0][:26],
                           "rt": igual_com_tipo(decode(w), strs), "wire": w}

        # (2) fonte STRING + spec  -> devolve STRING (a grafia volta)
        melhor = None
        for alvo in alvos_para([v for v in strs if v is not None]):
            try:
                ws = encode(strs, nature=alvo)
                volta = decode(ws, nature=alvo)
                if not igual_com_tipo(volta, strs):
                    falhas.append(f"{nome}/str+{alvo.name}: RT nao preservou (tipo ou valor)")
                    continue
                autoc = B(ws) + custo_parametro(alvo)   # honesto: wire AUTO-CONTIDO
                if melhor is None or autoc < melhor["auto_contido"]:
                    melhor = {"bytes": B(ws), "auto_contido": autoc,
                              "param_bytes": custo_parametro(alvo),
                              "header": ws.split("\n")[0][:26], "rt": True,
                              "alvo": alvo.name, "wire": ws}
            except Exception as e:
                falhas.append(f"{nome}/str+{alvo.name}: {type(e).__name__}: {str(e)[:50]}")
        cel["str+spec"] = melhor or dict(cel["str+core"], alvo="nenhum aplicavel",
                                         auto_contido=cel["str+core"]["bytes"], param_bytes=0)

        # (3) fonte INT + core  -> a rota tipada
        wi = encode(ints)
        volta_i = decode(wi)
        cel["int+core"] = {"bytes": B(wi), "header": wi.split("\n")[0][:26],
                           "rt": igual_com_tipo(volta_i, ints), "wire": wi}
        if not cel["int+core"]["rt"]:
            falhas.append(f"{nome}/int+core: RT NAO preservou tipo — "
                          f"entrou {type(ints[0]).__name__}, voltou {type(volta_i[0]).__name__}")

        # (4) fonte INT + spec  -> NAO EXPRESSAVEL. Registra a recusa e SIMULA o potencial.
        recusas = {}
        for rota, chamada in (
            ("single", lambda a=None: encode(ints, nature=alvos_para([str(v) for v in ints if v is not None])[0])),
            ("multi", lambda: encode({"c": ints, "x": ["a"] * N},
                                     nature_per_col={"c": alvos_para([str(v) for v in ints if v is not None])[0]})),
            (".8H", lambda: encode([{"c": v} for v in ints],
                                   nature_per_col={"c": alvos_para([str(v) for v in ints if v is not None])[0]})),
        ):
            try:
                chamada()
                recusas[rota] = "ACEITOU (mudou?)"
            except Exception as e:
                recusas[rota] = f"{type(e).__name__}: {str(e)[:70]}"
        # simulacao: corpo do spec + header tipado. RT verificado A MAO, com tipo.
        sim = None
        alvos = alvos_para([str(v) for v in ints if v is not None])
        for alvo in alvos:
            # O slot NULO tem de sobreviver: filtrar os None encolheria o corpo e INFLARIA
            # o ganho (erro que este lab cometeu na 1a execucao). O core representa null
            # com o slot 0 da tabela congelada, entao o corpo transformado tambem o carrega.
            pares = [(None, None) if v is None else alvo.encode_value(str(v)) for v in ints]
            transformado = [p for p, _ in pares]
            corpo = encode([("" if p is None else p) for p in transformado])
            custo = B(corpo) + 1 + len(f" :{alvo.wire_id}")   # +1 = o disc 'n' do tipado
            autoc = custo + custo_parametro(alvo)             # honesto: AUTO-CONTIDO
            # RT a mao, restaurando o TIPO DE ORIGEM: um spec de INT recusa float (vira
            # literal) e o valor volta como estava — por isso `type(orig)`, nao `int`.
            volta = [None if p is None else type(o)(alvo.decode_value(p))
                     for p, o in zip(transformado, ints)]
            ok = igual_com_tipo(volta, ints)
            if not ok:
                falhas.append(f"{nome}/int+{alvo.name} (simulado): RT nao fecha")
            if sim is None or autoc < sim["auto_contido"]:
                sim = {"bytes": custo, "auto_contido": autoc,
                       "param_bytes": custo_parametro(alvo),
                       "alvo": alvo.name, "rt": ok, "simulado": True}
        cel["int+spec(SIMULADO)"] = sim or {"bytes": None, "auto_contido": None,
                                           "param_bytes": 0, "alvo": "nenhum", "rt": None}
        cel["int+spec(SIMULADO)"]["recusas_reais"] = recusas

        _esc(OUT / f"{nome}.str-core.tcf", cel["str+core"]["wire"])
        _esc(OUT / f"{nome}.int-core.tcf", cel["int+core"]["wire"])
        _js(OUT / f"{nome}.int-core.roundtrip.json", volta_i)
        if "wire" in cel["str+spec"]:
            _esc(OUT / f"{nome}.str-spec.tcf", cel["str+spec"]["wire"])
        _js(INT / f"{nome}.matriz.json", {
            "ideia": ideia,
            "celulas": {k: {kk: vv for kk, vv in v.items() if kk != "wire"}
                        for k, v in cel.items()},
        })

        b = {k: v.get("bytes") for k, v in cel.items()}
        # A simulacao NAO passa pelo FLOOR — ela reporta o custo CRU do spec, inclusive
        # quando ele e' pior. O FLOOR real ficaria com o menor, e e' esse o numero que o
        # usuario veria. Reporto os DOIS pra nao induzir a erro.
        ac_s = cel["str+spec"].get("auto_contido") or b["str+spec"]
        ac_i = cel["int+spec(SIMULADO)"].get("auto_contido") or b["int+spec(SIMULADO)"]
        pb = cel["str+spec"].get("param_bytes", 0)
        b["str+spec(auto-contido)"] = ac_s
        b["int+spec(auto-contido)"] = ac_i
        b["param_bytes"] = pb
        # o FLOOR compara contra o que seria EMITIDO — logo contra o auto-contido
        b["int+spec(com FLOOR)"] = min(ac_i, b["int+core"])
        cel["int+spec(SIMULADO)"]["com_floor"] = b["int+spec(com FLOOR)"]
        cel["int+spec(SIMULADO)"]["floor_recusaria"] = ac_i >= b["int+core"]
        tabela.append({"regime": nome, "ideia": ideia, **b,
                       "alvo_str": cel["str+spec"].get("alvo"),
                       "alvo_int": cel["int+spec(SIMULADO)"].get("alvo"),
                       "rt_int_core": cel["int+core"]["rt"]})
        marca = f"+param {pb}B" if pb else ""
        recusa = " (FLOOR recusa)" if cel["int+spec(SIMULADO)"]["floor_recusaria"] else ""
        print(f"  {nome:18s} str/core {b['str+core']:6d}  str/spec {b['str+spec']:6d}"
              f"->{ac_s:6d} {marca:11s} int/core {b['int+core']:6d}  "
              f"int/spec* {b['int+spec(SIMULADO)']:6d}->{ac_i:6d}{recusa}")

    _js(RAIZ / "resultado.json", {"tabela": tabela, "falhas": falhas})
    idx = ["# INDEX — a matriz tipagem × spec", "",
           "| regime | str+core | str+spec | int+core | int+spec* | alvo(str) | alvo(int) |",
           "|---|---:|---:|---:|---:|---|---|"]
    for t in tabela:
        idx.append(f"| `{t['regime']}` | {t['str+core']} | {t['str+spec']} | {t['int+core']} "
                   f"| {t['int+spec(SIMULADO)']} | {t['alvo_str']} | {t['alvo_int']} |")
    idx += ["", "`int+spec*` é **simulado**: `nature=` recusa entrada tipada nas três rotas "
                "(as recusas literais estão em `../intermediates/<regime>.matriz.json`). O "
                "número é o custo do corpo transformado + header tipado + tag, com o "
                "round-trip verificado à mão comparando TIPO.", ""]
    _esc(OUT / "INDEX.md", "\n".join(idx))

    print(f"\n{len(tabela)} regimes · {len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

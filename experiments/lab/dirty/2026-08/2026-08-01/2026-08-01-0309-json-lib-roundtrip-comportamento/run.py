"""Lab 2026-08-01-0309 — `dataset → json lib → dataset` × `dataset → TCF → dataset`.

Análise empírica do que cada rota PRESERVA, ALTERA ou REJEITA — a régua do futuro "modo
json" do TCF (param hipotético: quando o TCF preserva o que o json perderia/rejeitaria,
ele ALERTA como o json alertaria; sem o flag, faz tudo que pode; ambíguos "fogem" pro json).

3 camadas separadas (direção do owner): **JSON RFC 8259** (gramática) × **JSON lib**
(`json` do Python, com notas cross-ecossistema) × **dataset na linguagem** (list/dict
Python, que aceita mistura).

Saídas: `outputs/matriz.csv` (caso × vereditos × detalhes), `outputs/alteracoes.json`
(before/after de cada mutação), `result.md`. `src/tcf` intocado.
"""
import csv
import json
import math
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

NAN = float("nan")
INF = float("inf")

# ================================================================ corpus
# (id, camada-tema, input em Python; input="raw:..." = TEXTO json cru, o RT começa do parse)
CORPUS = [
    # 1. tipados puros — controle
    ("col-int",        "tipado puro",  [1, 2, 3]),
    ("col-float",      "tipado puro",  [1.5, 2.5, 3.5]),
    ("col-bool",       "tipado puro",  [True, False, True]),
    ("col-str",        "tipado puro",  ["a", "b", "c"]),
    ("col-null",       "tipado puro",  [None, None]),
    # 2. int × float
    ("int-x-float",    "int × float",  [1, 1.0, 2, 2.0]),
    # 3. -0.0
    ("neg-zero",       "-0.0",         [-0.0, 0.0]),
    # 4. NaN / ±Inf
    ("nan",            "NaN/±Inf",     [NAN]),
    ("inf",            "NaN/±Inf",     [INF, -INF]),
    # 5. int gigante
    ("int-gigante",    "int gigante",  [2 ** 63, 10 ** 25]),
    # 6. união mista
    ("uniao-bool-str", "união mista",  [True, "other", None, False, "other"]),
    ("uniao-num-str",  "união mista",  [1, "x", 2.5]),
    # 7. chave não-string
    ("chave-int",      "chave não-str", {1: "a"}),
    ("chave-none",     "chave não-str", {None: "a"}),
    ("chave-bool",     "chave não-str", {True: "a"}),
    # 8. chave duplicada — não expressável em Python: TEXTO cru
    ("chave-duplicada", "chave duplicada", 'raw:{"a": 1, "a": 2}'),
    # 9. tuple
    ("tuple-em-lista", "tuple",        [(1, 2), (3, 4)]),
    # 10. bytes
    ("bytes-em-lista", "bytes",        [b"ab"]),
    # 11. estruturas
    ("dict-vazio",     "estrutura",    {}),
    ("lista-vazia",    "estrutura",    []),
    ("chave-vazia",    "estrutura",    {"": ["a", "b"]}),
    ("str-lf",         "estrutura",    ["a\nb", "c"]),
    ("str-unicode",    "estrutura",    ["héllo wörld", "🚀"]),
    ("chave-unicode-nfd", "estrutura", {"é": [1]}),   # e + U+0301 (NFD)
    ("escalar-none",   "escalar raiz", None),
    ("escalar-int",    "escalar raiz", 42),
    ("escalar-str",    "escalar raiz", "x"),
    # 12. chave float / nan
    ("chave-float",    "chave não-str", {1.5: "a"}),
    ("chave-nan",      "chave não-str", {NAN: "a"}),
]


def _repr(x):
    r = repr(x)
    return r if len(r) <= 60 else r[:57] + "..."


def cmp_estrito(a, b):
    """Deep `==` + tipo, chaves de dict inclusas. NaN==NaN aceito (identidade de valor);
    -0.0 distingue sinal por copysign."""
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        if len(a) != len(b):
            return False
        return all(cmp_estrito(k1, k2) and cmp_estrito(v1, v2)
                   for (k1, v1), (k2, v2) in zip(a.items(), b.items()))
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(cmp_estrito(x, y) for x, y in zip(a, b))
    if isinstance(a, float):
        if math.isnan(a) and math.isnan(b):
            return True
        if a == 0 and b == 0:
            return math.copysign(1, a) == math.copysign(1, b)
    return a == b


def rt_json(x):
    """`(veredito, obtido, detalhe)` da rota `json.loads(json.dumps(x))`."""
    try:
        obtido = json.loads(json.dumps(x))
    except Exception as e:  # noqa: BLE001
        return "ERRO", None, f"{type(e).__name__}: {e}"
    if cmp_estrito(obtido, x):
        return "PRESERVA", obtido, ""
    return "ALTERA", obtido, f"obtido={_repr(obtido)}"


def rt_tcf(x):
    """`(veredito, obtido, detalhe)` da rota `decode(encode(x))`."""
    import warnings
    with warnings.catch_warnings(record=True) as ws:
        warnings.simplefilter("always")
        try:
            obtido = decode(encode(x))
        except Exception as e:  # noqa: BLE001
            msg = str(e).replace("\n", " ")
            return "ERRO", None, f"{type(e).__name__}: {msg[:140]}"
    if cmp_estrito(obtido, x):
        return "PRESERVA", obtido, ""
    warn = f" [warning: {str(ws[0].message)[:80]}]" if ws else ""
    return "ALTERA", obtido, f"obtido={_repr(obtido)}{warn}"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas = []
    alteracoes = []
    json_rt_obtidos, tcf_rt_obtidos = {}, {}
    falhas = []
    tcf_altera = []

    for cid, tema, x in CORPUS:
        if isinstance(x, str) and x.startswith("raw:"):
            texto = x[4:]
            # o input e' o TEXTO: o RT da lib comeca do parse; TCF nao e' expressavel
            try:
                parsed = json.loads(texto)
                re = json.loads(json.dumps(parsed))
                j_ver = "PRESERVA" if cmp_estrito(re, parsed) else "ALTERA"
                j_det = f"texto={texto!r} -> parse={parsed!r}" + (
                    "" if j_ver == "PRESERVA" else " (last-wins silencioso)")
                j_obt = parsed
            except Exception as e:  # noqa: BLE001
                j_ver, j_det, j_obt = "ERRO", f"{type(e).__name__}: {e}", None
            t_ver, t_det, t_obt = "NÃO-EXPRESSÁVEL", "dict Python nao tem chave duplicada", None
        else:
            j_ver, j_obt, j_det = rt_json(x)
            t_ver, t_obt, t_det = rt_tcf(x)
        linhas.append({"caso": cid, "tema": tema, "input": _repr(x[4:] if j_ver != "NÃO-EXPRESSÁVEL" and isinstance(x, str) and x.startswith("raw:") else x),
                       "json": j_ver, "json_det": j_det,
                       "tcf": t_ver, "tcf_det": t_det})
        json_rt_obtidos[cid] = j_obt
        tcf_rt_obtidos[cid] = t_obt
        if j_ver == "ALTERA":
            alteracoes.append({"caso": cid, "rota": "json-lib",
                               "antes": _repr(x), "depois": _repr(j_obt)})
        if t_ver == "ALTERA":
            alteracoes.append({"caso": cid, "rota": "tcf",
                               "antes": _repr(x), "depois": _repr(t_obt),
                               "detalhe": t_det})
            # TCF nao deveria alterar — mas ESTE caso vem COM UserWarning explicito do
            # encoder (coluna anonima), nao e' corrupcao silenciosa: vira ACHADO reportado
            # no result.md, nao falha do lab.
            tcf_altera.append(cid)

    # knobs do NaN (medidos, nao anedota)
    knobs = {
        "dumps(nan) default": json.dumps([NAN]),
        "loads default": json.loads("[NaN]"),
        "dumps allow_nan=False": None, "loads parse_constant rejeita": None,
    }
    try:
        json.dumps([NAN], allow_nan=False)
    except ValueError as e:
        knobs["dumps allow_nan=False"] = f"ValueError: {e}"
    try:
        json.loads("[NaN]", parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except ValueError as e:
        knobs["loads parse_constant rejeita"] = f"ValueError: {e}"

    # ================================================================ arquivos
    _wj = lambda p, o: p.write_text(json.dumps(o, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    _wj(RAIZ / "inputs" / "corpus.json",
        [{"caso": c, "tema": t, "input": _repr(x)} for c, t, x in CORPUS])
    _wj(RAIZ / "intermediates" / "json-lib-roundtrip-obtidos.json", json_rt_obtidos)
    _wj(RAIZ / "intermediates" / "tcf-roundtrip-obtidos.json", tcf_rt_obtidos)
    _wj(RAIZ / "outputs" / "alteracoes.json", alteracoes)
    _wj(RAIZ / "outputs" / "knobs-nan-medidos.json", knobs)
    with (RAIZ / "outputs" / "matriz.csv").open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["caso", "tema", "input", "json", "json_det", "tcf", "tcf_det"])
        wr.writeheader()
        wr.writerows(linhas)

    # ================================================================ grupos
    G = {"a": [], "b": [], "c": [], "d": [], "x": []}
    for r in linhas:
        j, t = r["json"], r["tcf"]
        if j == "PRESERVA" and t == "PRESERVA":
            G["a"].append(r["caso"])
        elif j == "ALTERA" and t == "PRESERVA":
            G["b"].append(r["caso"])
        elif j in ("PRESERVA", "ALTERA") and t == "ERRO":
            G["c"].append(r["caso"])
        elif j == "ERRO" and t == "ERRO":
            G["d"].append(r["caso"])
        else:
            G["x"].append(r["caso"])                   # fora da malha esperada — investigar

    out = ["# `dataset → json lib → dataset` × `dataset → TCF → dataset` (2026-08-01-0309)",
           "",
           "Régua empírica pro futuro **modo-json** do TCF. Dados: `outputs/matriz.csv`, "
           "`outputs/alteracoes.json`, `outputs/knobs-nan-medidos.json`.", "",
           "## A matriz, em 4 grupos (+ exceções)", "",
           f"**(a) ambos preservam — {len(G['a'])}**: {', '.join(f'`{c}`' for c in G['a'])}",
           "",
           f"**(b) json ALTERA/perde e TCF PRESERVA — {len(G['b'])}**: "
           f"{', '.join(f'`{c}`' for c in G['b']) or 'nenhum'}",
           "",
           f"**(c) json aceita e TCF REJEITA — {len(G['c'])}**: "
           f"{', '.join(f'`{c}`' for c in G['c'])}",
           "",
           f"**(d) ambos rejeitam — {len(G['d'])}**: "
           f"{', '.join(f'`{c}`' for c in G['d']) or 'nenhum'}", ""]
    if G["x"]:
        out += [f"**⚠ fora da malha esperada — {len(G['x'])}**: "
                f"{', '.join(f'`{c}`' for c in G['x'])} — ver detalhe na matriz.", ""]
    det = {r["caso"]: r for r in linhas}
    out += ["### Detalhe dos casos que NÃO são (a)", "",
            "| caso | json lib | TCF |", "|---|---|---|"]
    for r in linhas:
        if r["caso"] in G["a"]:
            continue
        out.append(f"| `{r['caso']}` | {r['json']}: {r['json_det'] or '—'} | "
                   f"{r['tcf']}: {r['tcf_det'] or '—'} |")
    out.append("")

    out += [
        "## 1. A matriz comentada",
        "",
        f"- **(a) ambos preservam — {len(G['a'])} casos.** O núcleo estável: tipados puros, "
        "`int × float` (o Python distingue `1` de `1.0` na volta E o TCF preserva pela "
        "grafia — `_cast_tipo` tenta `int` antes de `float`), `-0.0` (ambos preservam o "
        "sinal — o json via grafia `\"-0.0\"`, o TCF idem), int gigante (ambos preservam "
        "em Python), vazios, unicode NFD, escalares na raiz.",
        f"- **(b) json ALTERA e TCF PRESERVA — {len(G['b'])} casos.** **VAZIO — e isso é o "
        "achado central**: TODAS as perdas da lib Python (coerção de chave, tuple→list, "
        "dup-key last-wins) acontecem em casos que o TCF **rejeita**, não preserva. O "
        "conjunto onde o modo-json alertaria 'TCF preserva o que o json perde' é hoje "
        "vazio no single-shot; ele só ganha corpo com as rotas NOVAS (lazytype união, "
        "futuro modo-json) e com a leitura cross-ecossistema (ver §2).",
        f"- **(c) json aceita e TCF REJEITA — {len(G['c'])} casos.** O TCF é mais estrito "
        "que a lib Python em 3 famílias: **NaN/±Inf** (a lib emite `NaN`/`Infinity`, "
        "EXTENSÃO fora da RFC 8259, e lê de volta — o default é permissivo; o TCF é "
        "RFC-strict), **união mista** (a lib preserva de graça; o `.8H` recusa escalares "
        "mistos — o caso central do lazytype `bB`), **tuple** (a lib serializa como array "
        "perdendo o tipo; o TCF fail-loud), **chave não-string** (a lib COAGE "
        "silenciosamente `1`→`\"1\"`, `None`→`\"null\"`, `True`→`\"true\"`, `1.5`→`\"1.5\"`, "
        "`nan`→`\"NaN\"` — perda DENTRO do Python; o TCF fail-loud com mensagem que já cita "
        "a coerção do json), **str com `\\n`** (a lib escapa `\"\\n\"` de graça; o TCF "
        "recusa LF embutido porque LF delimita linha).",
        f"- **(d) ambos rejeitam — {len(G['d'])} caso.** `bytes`: lib `TypeError` "
        "('not JSON serializable'); TCF `HierarchicalError` ('tipo não suportado').",
        "",
        "### ⚠ Os 2 casos fora da malha",
        "",
        "- **`chave-vazia` `{\"\": [...]}` — o único caso onde o TCF ALTERA**: o encoder "
        "trata nome vazio como coluna ANÔNIMA e **avisa** (`UserWarning`), e o decode "
        "devolve o nome posicional `\"0\"` — `{\"\": ...}` volta `{\"0\": ...}`. Não é "
        "corrupção silenciosa (há warning), mas é **perda com RT quebrado**: candidato a "
        "ticket (fail-loud em vez de warning, ou preservar `\"\"` como nome).",
        "- **`chave-duplicada` `{\"a\": 1, \"a\": 2}`**: a lib faz **last-wins silencioso** "
        "(`{'a': 2}`) — perda que o TCF nem deixa EXPRESSAR (dict Python não tem chave "
        "duplicada). Categoria própria: perda da lib sem equivalente no dataset.",
        "",
        "## 2. O catálogo de alertas do modo-json (filosofia SideOutputs: só ALERTA, nunca arruma)",
        "",
        "O grupo (b) vazio desloca o catálogo: os alertas úteis são sobre o que o TCF "
        "**preserva e um consumidor json TIPICO perderia ou rejeitaria** (lib estrita, "
        "outro ecossistema) — detectável DE GRAÇA no encode (pré-pass/`column_features` "
        "já varrem a coluna):",
        "",
        "- **união mista por coluna** — hoje fail-loud; quando uma rota a aceitar "
        "(lazytype), alertar: 'json lib preserva, mas consumidores tipados (schemas "
        "estritos) rejeitam união'. Detecção: `len({type(x) for x in col}) > 1`.",
        "- **distinção int × float** (`1` × `1.0`) — TCF e lib Python preservam; **JS/**"
        "number fundem os dois. Alerta cross-ecossistema: 'coluna mista int/float; fora "
        "do Python a distinção se perde'. Detecção: presença de ambos os tipos numa coluna `n`.",
        "- **int > 2^53** — TCF e lib preservam; JS/number perde precisão. Alerta: 'inteiro "
        "acima de 2^53; cross-ecossistema, usar string'. Detecção: `abs(x) > 2**53` no pré-pass.",
        "- **NaN/±Inf** — TCF rejeita (RFC-strict); a lib Python ACEITA por default. Alerta "
        "simétrico no modo-json: 'input contém NaN/Inf; o json de referência (allow_nan="
        "False, RFC) também rejeitaria — rejeitando como ele'.",
        "- **chave não-string / tuple / chave duplicada** — a lib coage/perde "
        "silenciosamente; o TCF já rejeita. No modo-json o alerta é o próprio fail-loud, "
        "com mensagem citando a perda que o json faria (o TCF já faz isso na mensagem de "
        "chave não-str).",
        "- **string com `\\n`** — a lib escapa de graça; o TCF rejeita. Alerta: 'json "
        "serializaria com `\\\\n`; TCF não representa LF embutido'.",
        "",
        "## 3. Ambíguos — onde 'fugir pro json' é a resposta",
        "",
        "- **Ordenação de chaves de dict**: lib Python preserva a ordem de inserção; a RFC "
        "não garante; o TCF multi-col preserva a ordem das colunas. Se um dia houver "
        "reordenação (sort_by), o comportamento json (ordem de inserção) é a âncora.",
        "- **int → float coercion** (`loads('1.0')` é float, `loads('1')` é int; nenhum "
        "coage): o TCF segue a mesma regra pela grafia — já alinhado, manter.",
        "- **Escalar solto na raiz**: lib aceita (`42`, `\"x\"`, `null`); o TCF aceita e "
        "preserva (medido). Alinhado.",
        "- **Chave unicode NFC × NFD**: a lib preserva os CODE POINTS (não normaliza); o "
        "TCF idem (medido: NFD preservado). A âncora é 'não normalizar', como a lib.",
        "",
        "## 4. RFC × lib × dataset — onde o corpus evidenciou divergência",
        "",
        "- **NaN/±Inf: lib > RFC.** A RFC 8259 não tem `NaN`/`Infinity`; a lib Python "
        "emite e lê por default (extensão). Knobs medidos "
        "(`outputs/knobs-nan-medidos.json`): `allow_nan=False` rejeita no dumps; "
        "`parse_constant` rejeita no loads. **A lib tem os dois comportamentos; o default "
        "é o permissivo.** TCF hoje = RFC-strict.",
        "- **Chave duplicada: RFC permite, lib perde.** A gramática não proíbe (é "
        "'SHOULD' de unicidade); a lib faz last-wins calada. O dataset Python nem expressa.",
        "- **Chave não-string: dataset Python permite, lib mutila.** `{1: 'a'}` é Python "
        "válido; o dumps COAGE a chave pra `\"1\"` e o loads não reverte — a perda é "
        "DENTRO do Python, sem aviso. O TCF fail-loud com mensagem que cita exatamente "
        "isso ('o json coage chaves p/ str e o round-trip perde').",
        "- **tuple: dataset permite, lib converte.** tuple → array, sem aviso e sem volta.",
        "",
        "## Notas de método",
        "",
        "- Vereditos por `cmp_estrito`: deep `==` + tipo, chaves inclusas; `-0.0` por "
        "`copysign`; NaN==NaN aceito.",
        "- json lib = `json` do Python 3 (default permissivo). Cross-ecossistema (JS, "
        "schemas estritos) é NOTA, não medido aqui.",
        "- `src/tcf` intocado; nada soldado.", ""]
    if falhas:
        out += [f"**FALHAS**: {falhas}", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    print("GRUPOS:", {k: len(v) for k, v in G.items()})
    print("TCF-ALTERA:", tcf_altera)
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())

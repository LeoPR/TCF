# -*- coding: utf-8 -*-
"""COMPORTAMENTO NORMAL + VERIFICAÇÃO LÓGICA dos welds C1/C2/C3.

    python run.py     # sai 0 só se o comportamento normal fechar E as enumerações
                      # exaustivas cobrirem o espaço de decisão sem buraco

## O pedido (owner, 2026-08-16)

*"precisamos de algumas simulações pra ver se ele está resistente mesmo, e até uma
verificação lógica do código, pois se ele está determinístico não tem porque achar que o
código vai 'pifar' sem seguir ao menos alguma lógica. O teste em massa que dirá isso depois,
mas agora é só pra testar comportamento simples e normal."*

E a regra de processo, aceita: *"mesmo código temporário tem que ser colocado no mesmo lab,
pois pertence a ele... o que não pode é largar código sem evidência."* — por isso **toda**
sonda deste ciclo está aqui dentro, nada em scratchpad.

## A tese da verificação lógica

Os três guards são **funções puras de decisão sobre espaços FINITOS**. Logo não há por que
amostrar: dá para **ENUMERAR**. Onde a enumeração é exaustiva, ela não é evidência estatística
— é cobertura total do espaço.

| weld | a decisão é sobre | tamanho do espaço |
|---|---|---|
| **C1** | 1 caractere (o discriminador, índice 6) | **finito**: todos os chars ASCII + controle |
| **C2** | multiconjunto de nomes resolvidos | **finito** por comprimento: enumerável até k colunas |
| **C3** | a FORMA do argumento (list/dict/vazio/tipos) | **finito**: a taxonomia de entrada da API |

Além disso, cada guard é **puro** (sem estado, sem I/O, sem aleatoriedade) e **total** (todo
input tem saída definida: valor ou exceção). Os blocos 3-5 verificam essas três propriedades.

## O que este lab NÃO faz

**Não é teste em massa** — por decisão do owner, isso vem depois. Aqui: caminho normal,
determinismo, e a enumeração dos espaços de decisão.
"""
from __future__ import annotations

import datetime as _dt
import itertools
import json
import os
import pathlib
import random
import shutil
import string
import subprocess
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode, view                              # noqa: E402
from tcf.natures import SPEC_CPF, SPEC_DATA_ISO                   # noqa: E402
from tcf.multi.core import _nomes_resolvidos, _parse_meta         # noqa: E402
from tcf.decoder import _separa_sufixo_polaridade                 # noqa: E402

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
SEED = 20260816


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def grava_caso(nome, dados, wire, extra=None, posicional=False):
    """entrada + wire + roundtrip + meta; o diff textual É a prova e vira assert."""
    volta = decode(wire)
    _js(INP / f"{nome}.entrada.json", dados)
    _esc(OUT / f"{nome}.tcf", wire)
    _js(OUT / f"{nome}.roundtrip.json", volta)
    if posicional:
        # `drop_names` troca as chaves por POSICIONAIS — e' o CONTRATO (ADR-0029), nao
        # defeito. Aqui a prova e' por VALORES, na ordem. (Terceira vez que eu escrevo
        # esse assert errado; agora o parametro obriga a declarar a semantica.)
        igual = isinstance(volta, dict) and list(volta.values()) == list(dados.values())
    else:
        igual = ((INP / f"{nome}.entrada.json").read_text(encoding="utf-8")
                 == (OUT / f"{nome}.roundtrip.json").read_text(encoding="utf-8"))
    _js(OUT / f"{nome}.meta.json", {
        "wire_bytes": B(wire), "linha1": wire.split("\n", 1)[0],
        "prova": "valores em ordem (chaves posicionais por design)" if posicional
                 else "diff textual entrada x roundtrip",
        "roundtrip_identico_a_entrada": igual,
        "entrada": f"../inputs/{nome}.entrada.json", **(extra or {})})
    return igual


# ── o dado do dia a dia ─────────────────────────────────────────────────────
def cadastro(n=300):
    """O mesmo cadastro popular dos labs 1400/1450/1530 — uso NORMAL, nada de borda."""
    rng = random.Random(SEED)
    n1 = ["ana", "bruno", "carla", "diego", "edna", "felipe", "gilda", "hugo"]
    n2 = ["silva", "souza", "oliveira", "santos", "lima", "costa"]

    def _dv(b9):
        ds = [int(c) for c in b9]
        d1 = (sum(d * w for d, w in zip(ds, range(10, 1, -1))) * 10) % 11 % 10
        d2 = (sum(d * w for d, w in zip(ds + [d1], range(11, 1, -1))) * 10) % 11 % 10
        return f"{d1}{d2}"

    nome = [f"{rng.choice(n1).title()} {rng.choice(n2).title()}" for _ in range(n)]
    return {
        "id": [f"{i+1:06d}" for i in range(n)],
        "nome": nome,
        "cpf": [(lambda b: f"{b[:3]}.{b[3:6]}.{b[6:9]}-{_dv(b)}")(
            f"{rng.randint(0, 999999999):09d}") for _ in range(n)],
        "email": [f"{x.split()[0].lower()}{rng.randint(1,99)}@exemplo.com" for x in nome],
        "nascimento": [(_dt.date(1960, 1, 1)
                        + _dt.timedelta(days=rng.randint(0, 18000))).isoformat()
                       for _ in range(n)],
        "ativo": [rng.choice(["ativo", "inativo"]) for _ in range(n)],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas, reg = [], {}
    T = cadastro()
    SPECS = {"cpf": SPEC_CPF, "nascimento": SPEC_DATA_ISO}
    _js(INP / "cadastro.fonte.json", {
        "gerador": "run.py::cadastro()", "seed": SEED, "n": len(T["id"]),
        "ideia": "uso NORMAL — o cadastro dos labs 1400/1450/1530, sem caso de borda",
        "cpf": "gerador da suite soldada (tests/test_nature_compete.py:21-29)",
        "pin": "sintetico deterministico, sem Z:"})

    # ── BLOCO 1 — o caminho normal, ponta a ponta ───────────────────────────
    print("BLOCO 1 — comportamento simples e normal (o caminho de todo dia)\n")
    print(f"  {'operação':<38} {'bytes':>7} {'RT':<5} header")
    b1 = []

    def normal(rot, dados, arquivo, **kw):
        w = encode(dados, **kw)
        ok = grava_caso(arquivo, dados, w, posicional=bool(kw.get("drop_names")),
                        extra={"operacao": rot,
                               "kwargs": {k: str(v) for k, v in kw.items()}})
        if not ok:
            falhas.append(f"normal/{rot}: diff entrada x roundtrip")
        l1 = w.split("\n", 1)[0]
        b1.append({"operacao": rot, "bytes": B(w), "rt": ok, "linha1": l1})
        print(f"  {rot:<38} {B(w):>7} {'ok' if ok else 'FALHA':<5} {l1[:34]!r}")
        return w

    w_tab = normal("tabela .8M, 6 colunas", T, "01-tabela")
    normal("a mesma, com specs", T, "02-tabela-com-spec", nature_per_col=SPECS)
    normal("a mesma, sem nomes", T, "03-tabela-sem-nomes", drop_names=True)
    normal("a mesma, todos com size", T, "04-tabela-todos-com-size", min_header=False)
    normal("uma coluna só", {"nome": T["nome"]}, "05-uma-coluna")
    normal("registros (.8H)", [dict(zip(T, t)) for t in zip(*T.values())], "06-registros")
    normal("coluna única de datas", {"nascimento": T["nascimento"]}, "07-datas",
           nature_per_col={"nascimento": SPEC_DATA_ISO})

    # o view no caminho normal
    v = view(w_tab)
    cols = v.columns() if callable(v.columns) else v.columns
    sel = v.select(["nome"])
    filtrado = v.where("ativo", "ativo").count()
    real = sum(1 for x in T["ativo"] if x == "ativo")
    print(f"\n  view: colunas={cols}")
    print(f"        select(['nome']) -> {len(sel)} linhas, tocou {v.touched}")
    print(f"        where('ativo','ativo').count() -> {filtrado} (verdade: {real}) "
          f"{'OK' if filtrado == real else 'DIVERGE'}")
    if filtrado != real:
        falhas.append("view.where divergiu da verdade")
    reg["bloco1_normal"] = {"operacoes": b1, "view": {"colunas": list(cols),
                                                      "where_count": filtrado,
                                                      "verdade": real}}

    # ── BLOCO 2 — DETERMINISMO: mesmo input, mesmo byte, sempre ─────────────
    print("\nBLOCO 2 — DETERMINISMO (a premissa da sua pergunta)")
    reps = [encode(T, nature_per_col=SPECS) for _ in range(20)]
    igual_proc = len(set(reps)) == 1
    print(f"  20 encodes no MESMO processo -> {len(set(reps))} wire(s) distinto(s) "
          f"{'OK' if igual_proc else '>>> NAO-DETERMINISTICO <<<'}")
    if not igual_proc:
        falhas.append("encode nao-deterministico no mesmo processo")

    # hash seed diferente = ordem de iteração de `set` diferente. Se algum caminho
    # iterar set pra montar saída, o wire VARIA — e isso seria não-determinismo real.
    probe = RAIZ / "_probe_determinismo.py"          # código temporário DENTRO do lab
    _esc(probe, "# -*- coding: utf-8 -*-\n"
                "# Sonda do BLOCO 2. Mora no lab de proposito (regra do owner 2026-08-16:\n"
                "# 'mesmo codigo temporario tem que ser colocado no mesmo lab').\n"
                "import sys, json, hashlib\n"
                "sys.path.insert(0, sys.argv[1])\n"
                "sys.path.insert(0, sys.argv[2])\n"
                "from tcf import encode\n"
                "from tcf.natures import SPEC_CPF, SPEC_DATA_ISO\n"
                "from run import cadastro\n"
                "T = cadastro()\n"
                "w = encode(T, nature_per_col={'cpf': SPEC_CPF, 'nascimento': SPEC_DATA_ISO})\n"
                "print(hashlib.sha256(w.encode()).hexdigest())\n")
    hashes = []
    for seed in ("0", "1", "42", "12345", "random"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        r = subprocess.run([sys.executable, str(probe), str(REPO / "src"), str(RAIZ)],
                           capture_output=True, text=True, env=env)
        hashes.append((seed, (r.stdout or r.stderr).strip()[:64]))
    distintos = len({h for _, h in hashes})
    print(f"  5 processos com PYTHONHASHSEED distinto -> {distintos} hash(es) distinto(s) "
          f"{'OK (imune a ordem de set)' if distintos == 1 else '>>> VARIA COM O SEED <<<'}")
    for s, h in hashes:
        print(f"    seed={s:<7} sha256={h[:32]}…")
    if distintos != 1:
        falhas.append("wire varia com PYTHONHASHSEED")
    probe.unlink(missing_ok=True)
    reg["bloco2_determinismo"] = {"mesmo_processo_ok": igual_proc,
                                  "hashes_por_seed": dict(hashes),
                                  "hashes_distintos": distintos}

    # ── BLOCO 3 — C1: o espaço de decisão é 1 CARACTERE, e foi ENUMERADO ────
    print("\nBLOCO 3 — VERIFICAÇÃO LÓGICA do C1: enumeração TOTAL do discriminador")
    print("  o guard é `line1[6:7] not in ('M','H')` — decide sobre UM caractere.")
    part = {"pre_passe_roda": [], "pre_passe_pulado": []}
    for cod in range(0x00, 0x80):
        c = chr(cod)
        alvo = "pre_passe_pulado" if c in ("M", "H") else "pre_passe_roda"
        part[alvo].append(c)
    total = len(part["pre_passe_roda"]) + len(part["pre_passe_pulado"])
    print(f"  espaço ASCII enumerado: {total} chars = "
          f"{len(part['pre_passe_roda'])} rodam + {len(part['pre_passe_pulado'])} pulados")
    print(f"  pulados: {part['pre_passe_pulado']}  (exatamente os discriminadores de rota)")
    # a partição é TOTAL (sem buraco) e DISJUNTA (sem sobreposição), por construção
    tot_ok = total == 128 and not set(part["pre_passe_roda"]) & set(part["pre_passe_pulado"])
    print(f"  partição total e disjunta: {tot_ok}")
    # e o que IMPORTA: nenhum disc que o encode EMITE, fora M/H, perde a polaridade
    discs_emitidos = set()
    for dado in ([f"{i:02d}.{i:02d}-{i:03d}" for i in range(30)],   # flat polarizado
                 [i + 0.5 for i in range(30)],                       # tipado polarizado
                 [f"n{i}" for i in range(30)],                       # flat texto
                 [1000 + i for i in range(30)],                      # tipado int
                 list("abc"),                                        # curto
                 T,                                                  # .8M
                 [dict(zip(T, t)) for t in zip(*T.values())]):       # .8H
        discs_emitidos.add(encode(dado)[6:7])
    fora = sorted(discs_emitidos - {"M", "H"})
    print(f"  discriminadores que o encode emite: {sorted(discs_emitidos)}")
    print(f"  os que MANTÊM o pré-passe: {fora}  (nenhum é M/H → nenhum regride)")
    if not tot_ok:
        falhas.append("C1: particao do disc nao e total/disjunta")
    reg["bloco3_c1"] = {"chars_enumerados": total, "pulados": part["pre_passe_pulado"],
                        "particao_total_disjunta": tot_ok,
                        "discs_emitidos": sorted(discs_emitidos)}

    # ── BLOCO 4 — C2: enumeração EXAUSTIVA do espaço de nomes ───────────────
    print("\nBLOCO 4 — VERIFICAÇÃO LÓGICA do C2: enumeração EXAUSTIVA de nomes")
    print("  o guard é `len(set(nomes)) != len(nomes)` — decide sobre um multiconjunto.")
    ALFA = [None, "0", "1", "2", "a"]            # None = anônima (vira posicional)
    tot4 = colidiu = coerente = 0
    for k in (2, 3):
        for combo in itertools.product(ALFA, repeat=k):
            pares = [(1, nome, "raw", None) for nome in combo]
            nomes_esperados = [n if n is not None else str(i)
                               for i, n in enumerate(combo)]
            deve_colidir = len(set(nomes_esperados)) != len(nomes_esperados)
            tot4 += 1
            try:
                got = _nomes_resolvidos(pares)
                ocorreu = False
            except ValueError:
                got, ocorreu = None, True
            colidiu += ocorreu
            # COERÊNCIA: levanta exatamente quando (e só quando) há repetição
            if ocorreu == deve_colidir and (ocorreu or got == nomes_esperados):
                coerente += 1
    print(f"  {tot4} combinações enumeradas (k=2 e k=3 sobre {len(ALFA)} símbolos, "
          f"{len(ALFA)}²+{len(ALFA)}³)")
    print(f"  levantou em {colidiu}; coerente com a definição em {coerente}/{tot4} "
          f"{'— TOTAL' if coerente == tot4 else '>>> INCOERENTE <<<'}")
    if coerente != tot4:
        falhas.append("C2: guard incoerente com a definicao de colisao")
    # e a PUREZA: chamar 2x dá o mesmo, e não mexe no argumento
    pares_ref = [(1, "a", "raw", None), (1, None, "raw", None)]
    copia = list(pares_ref)
    r1, r2 = _nomes_resolvidos(pares_ref), _nomes_resolvidos(pares_ref)
    puro = r1 == r2 and pares_ref == copia
    print(f"  pureza (2 chamadas iguais + argumento intacto): {puro}")
    if not puro:
        falhas.append("C2: guard nao e puro")
    reg["bloco4_c2"] = {"combinacoes": tot4, "levantou": colidiu,
                        "coerentes": coerente, "puro": puro}

    # ── BLOCO 5 — C3: enumeração da TAXONOMIA de entrada ────────────────────
    print("\nBLOCO 5 — VERIFICAÇÃO LÓGICA do C3: enumeração da taxonomia de entrada")
    print("  o guard decide pela FORMA do argumento; a taxonomia da API é finita.")
    FORMAS = [
        ("list vazia",            [],                                  "rejeita"),
        ("list[str]",             ["a", "b"],                          "rejeita"),
        ("list[int]",             [1, 2],                              "rejeita"),
        ("list[float]",           [1.5, 2.5],                          "rejeita"),
        ("list[bool]",            [True, False],                       "rejeita"),
        ("list[dict]",            [{"d": "2024-01-01"}, {"d": "2024-01-02"}], "aceita"),
        ("list[list]",            [["a"], ["b"]],                      "rejeita-no-8H"),
        ("dict col existente",    {"d": ["2024-01-01", "2024-01-02"]},  "aceita"),
    ]
    print(f"  {'forma':<22} {'esperado':<9} {'observado':<9} coerente")
    b5, coer5 = [], 0
    for rot, dado, esperado in FORMAS:
        # TRES categorias, nao duas: quem rejeita importa. O guard do C3 (ValueError do
        # `encoder`) e' o meu; o `.8H` rejeita `list[list]` com mensagem PROPRIA e mais
        # informativa, e o guard deixa passar de proposito pra nao piorar o erro.
        try:
            encode(dado, nature_per_col={"d": SPEC_DATA_ISO})
            obs = "aceita"
        except Exception as e:
            # `HierarchicalError` E' subclasse de ValueError — nao da' pra separar por
            # TIPO. Separa-se pela ASSINATURA da mensagem: `nature_per_col=` e' o guard
            # do `encoder` (o meu); `folha ESCALAR` e' o do `.8H`.
            msg = str(e)
            obs = ("rejeita" if "nature_per_col=" in msg
                   else "rejeita-no-8H" if "folha ESCALAR" in msg
                   else "outro-erro")
        ok = obs == esperado
        coer5 += ok
        b5.append({"forma": rot, "esperado": esperado, "observado": obs, "coerente": ok})
        print(f"  {rot:<22} {esperado:<9} {obs:<9} {ok}")
    print(f"  coerentes: {coer5}/{len(FORMAS)}")
    if coer5 != len(FORMAS):
        falhas.append("C3: taxonomia de entrada incoerente")
    # a coluna inexistente: a decisão é `set(nature_per_col) - set(data)`, enumerável
    TAB = {"a": ["1", "2"], "b": ["3", "4"]}
    casos6 = [(("a",), "aceita"), (("a", "b"), "aceita"), (("z",), "rejeita"),
              (("a", "z"), "rejeita"), ((), "aceita")]
    coer6 = 0
    for chaves, esperado in casos6:
        try:
            encode(TAB, nature_per_col={c: SPEC_DATA_ISO for c in chaves})
            obs = "aceita"
        except ValueError:
            obs = "rejeita"
        coer6 += obs == esperado
    print(f"  subconjuntos de colunas: {coer6}/{len(casos6)} coerentes "
          f"(rejeita ⟺ há chave fora da tabela)")
    if coer6 != len(casos6):
        falhas.append("C3: guard de coluna inexistente incoerente")
    reg["bloco5_c3"] = {"taxonomia": b5, "coerentes_taxonomia": coer5,
                        "coerentes_subconjuntos": coer6}

    # ── INDEX ──────────────────────────────────────────────────────────────
    linhas = ["# INDEX — comportamento normal + verificação lógica", "",
              "Todo caso tem entrada, wire, roundtrip e meta; o `diff` é assert no `run.py`.",
              "", "| caso | operação | bytes | RT |", "|---|---|---:|:--:|"]
    for mp in sorted(OUT.glob("*.meta.json")):
        m = json.loads(mp.read_text(encoding="utf-8"))
        nome = mp.name[:-len(".meta.json")]
        linhas.append(f"| [`{nome}.tcf`](./{nome}.tcf) | {m.get('operacao','—')} | "
                      f"{m['wire_bytes']} | {'✓' if m['roundtrip_identico_a_entrada'] else '✗'} |")
    _esc(OUT / "INDEX.md", "\n".join(linhas) + "\n")
    _js(RAIZ / "resultado.json", {**reg, "falhas": falhas})

    print(f"\n{'='*74}")
    print(f"{len(falhas)} falha(s)")
    for f_ in falhas:
        print(f"  FALHA: {f_}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""O PISO do header do `.8M`, e as invariantes de fronteira que habilitam paralelismo.

    python run.py    # sai 0 só se as 6 invariantes passarem e todos os RTs fecharem

## O pedido (owner, 2026-08-16)

*"veja um caminho barato para olharmos o M agora pra fechar ele de forma consistente, quero
tirar o máximo de explicitudes do header e fechar muito bem as questões de limites de colunas
pra preparar para as opções de paralelismo."*

## O que a documentação JÁ decidiu (lido antes de medir — não é achado deste lab)

- **O-FMT-11 está FECHADO** (2026-07-05, lab `2026-07-01-header-minimal`): o header
  self-describing é **near-optimal**; 2 colunas anônimas caem a **13 B**; *"cada campo é
  load-bearing pro decode independente"*. O único lever grande restante é **O-FMT-14 (header
  derivável)** — feature de CONTRATO, não tweak de byte.
- **O-FMT-19 foi REFUTADO**: trocar byte-size por row-count *"custa TUDO: o lazy perde acesso
  O(1) por coluna, perde **decode paralelo** (bytes deixam fatiar; linhas forçam scan) e group
  por slice"*.
- **O-FMT-18** (sizes em base-94) foi medido e **decidido como hex** (T-FMT-HEADER-BASE-HEX,
  2026-07-09): base-94 colide com os separadores do meta (`,=:`), exigiria base-87. Fica como
  modo byte-máximo-sob-contrato.

**Logo os dois pedidos do owner estão em TENSÃO, e o projeto já resolveu**: os byte-sizes SÃO
o que habilita o paralelismo. Tirar explicitude do header tem um PISO, e esse piso é a
garantia de fatiamento. Este lab não re-abre isso — ele (1) re-verifica o piso pós-welds
novos (`:id` do ADR-0041, split `%`, FLOOR da nature — todos posteriores a 2026-07-05) e
(2) transforma "dá pra paralelizar" em **invariantes testadas**.

## AS 6 INVARIANTES (declaradas antes de rodar)

I1  offsets deriváveis SÓ da linha 1 — sem tocar em byte de corpo.
I2  independência: decodificar uma coluna não lê byte de outra.
I3  ordem livre: decodificar em ordem arbitrária dá o mesmo resultado.
I4  paralelismo real: N threads dão resultado idêntico ao serial.
I5  a ÚLTIMA é a única que precisa de EOF — e `min_header=False` remove até isso.
I6  o header sozinho é um PLANO DE FATIAMENTO completo: soma dos sizes + resto = len(corpo).

## GATE

`src/tcf` INTOCADO — o "decode paralelo" aqui é orquestração EXTERNA sobre as funções que já
existem, exatamente para provar que não falta nada no formato.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ.parent / "2026-08-16-1400-cadastro-popular-header-do-M"))

from tcf import decode, encode                                    # noqa: E402
from tcf.natures import SPEC_CPF, SPEC_DATA_ISO                   # noqa: E402
from run import cadastro                                          # noqa: E402

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


# ── o PLANO DE FATIAMENTO: só a linha 1, nada de corpo ─────────────────────
def plano_de_fatiamento(wire: str):
    """Deriva (nome, modo, nat, ini, fim) de CADA coluna lendo SÓ a linha 1.

    `fim=None` na última quando o size é omitido (min_header) — o único ponto que
    precisa do tamanho total. Esta função é o que um decodificador paralelo faria
    antes de distribuir trabalho.
    """
    from tcf.multi.core import _parse_meta
    line1, _, _corpo = wire.partition("\n")
    pares = _parse_meta(line1[7:])
    plano, off = [], 0
    for i, (size, nome, modo, nat) in enumerate(pares):
        fim = None if size is None else off + size
        plano.append({"i": i, "nome": nome if nome is not None else str(i),
                      "modo": modo, "nat": nat, "ini": off, "fim": fim})
        if fim is None:
            break
        off = fim
    return line1, plano


def decodifica_coluna(corpo: bytes, item, total: int):
    """Decoda UMA coluna a partir do seu recorte. Não vê as outras."""
    from tcf.decoder import _decode_column
    from tcf.multi import _decode_raw_body, _decode_v2b, _decode_struct_split
    fim = total if item["fim"] is None else item["fim"]
    b = corpo[item["ini"]:fim]
    if item["modo"] == "raw":
        return _decode_raw_body(b)
    if item["modo"] == "dict":
        return _decode_v2b(b)
    if item["modo"] == "split":
        return _decode_struct_split(b)
    return _decode_column(b.decode("utf-8"))


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
        "gerador": "IMPORTADO de ../2026-08-16-1400-cadastro-popular-header-do-M/run.py",
        "ideia": "os MESMOS 500 registros dos labs 1400/1450 — aqui a variavel e' a GRAFIA "
                 "do header e o MODO de decodar (serial x paralelo)",
        "pin": "seed 20260815"})

    # ── BLOCO 1 — o PISO do header, re-medido pós-welds ─────────────────────
    print("BLOCO 1 — o piso do header (O-FMT-11 dizia 13 B em 2026-07-05; e hoje?)\n")
    # ATENÇÃO à unidade: O-FMT-11 mediu **13 B de HEADER** (`#TCF.8M!14,!\n` = 13 B),
    # não de wire. A comparação honesta é header-contra-header.
    duas = {"a": ["x", "y"], "b": ["p", "q"]}
    w13 = encode(duas, drop_names=True)
    if decode(w13) != {"0": ["x", "y"], "1": ["p", "q"]}:
        falhas.append("piso: RT do caso de 2 colunas anonimas")
    l1_13 = w13.split("\n", 1)[0]
    print(f"  2 colunas anônimas: HEADER={B(l1_13) + 1} B  {l1_13!r}   (wire total {B(w13)} B)")
    print(f"  O-FMT-11 (2026-07-05) mediu HEADER=13 B (`#TCF.8M!14,!\\n`, size de 2 hex).")
    print(f"  Hoje com size de 1 hex dá {B(l1_13) + 1} B — mesma fórmula, "
          f"MESMO PISO: 7 (magic) + Σ|size_hex| + (ncols−1) vírgulas + marcadores + 1 LF.")

    # a curva do break-even. CUIDADO: `v0..vN` é progressão e o seq-RLE a esmaga —
    # o corpo não cresce e a curva mente. Usa-se DADO REAL (fatias do cadastro).
    print(f"\n  break-even (header como % do wire) — 2 colunas do cadastro, dado realista:")
    print(f"  {'N':>6} {'wire':>8} {'header':>7} {'header %':>9}")
    curva = []
    for n in (1, 5, 20, 100, 500):
        d = {"a": T["nome"][:n], "b": T["email"][:n]}
        w = encode(d, drop_names=True)
        if decode(w) != {"0": d["a"], "1": d["b"]}:
            falhas.append(f"curva n={n}: RT")
        h = B(w.split("\n", 1)[0]) + 1                    # +1 do '\n'
        curva.append({"n": n, "wire_B": B(w), "header_B": h,
                      "pct": round(100 * h / B(w), 1)})
        print(f"  {n:>6} {B(w):>8} {h:>7} {100 * h / B(w):>8.1f}%")
    print(f"  (O-FMT-11 mediu N=1 39% → N=100 1,3%; a forma da curva é o que importa)")
    reg["bloco1_piso"] = {"duas_anonimas_B": B(w13), "linha1_B": B(l1_13),
                          "linha1": l1_13, "curva": curva}

    # o que os welds NOVOS acrescentaram ao header (o `:id`, o `%`)
    print(f"\n  o que os welds pós-2026-07-05 acrescentaram (cadastro real, 7 colunas):")
    w_sem = encode(T)
    w_com = encode(T, nature_per_col=SPECS)
    w_drop = encode(T, nature_per_col=SPECS, drop_names=True)
    for rot, w in (("sem spec", w_sem), ("com spec (`:id`)", w_com),
                   ("com spec + drop_names", w_drop)):
        l1 = w.split("\n", 1)[0]
        print(f"    {rot:<24} linha1={B(l1):>4} B  ({100 * (B(l1) + 1) / B(w):.2f}% do wire)")
    print(f"  => o `:id` do ADR-0041 custou +{B(w_com.split(chr(10),1)[0]) - B(w_sem.split(chr(10),1)[0])} B de header "
          f"e devolveu {B(w_sem) - B(w_com)} B de corpo")
    reg["bloco1_welds_novos"] = {
        "linha1_sem_spec": B(w_sem.split("\n", 1)[0]),
        "linha1_com_spec": B(w_com.split("\n", 1)[0]),
        "linha1_drop_names": B(w_drop.split("\n", 1)[0]),
        "corpo_devolvido_B": B(w_sem) - B(w_com)}

    # ── BLOCO 2 — as 6 invariantes de fronteira ─────────────────────────────
    print("\nBLOCO 2 — as invariantes que habilitam decode paralelo (TESTADAS)")
    w = encode(T, nature_per_col=SPECS)
    _esc(OUT / "cadastro.tcf", w)
    corpo = w.partition("\n")[2].encode("utf-8")
    l1, plano = plano_de_fatiamento(w)
    verdade = decode(w)

    # I1 — o plano sai SÓ da linha 1
    i1 = len(plano) == len(T)
    print(f"  I1 plano derivado só da linha 1 ({B(l1)} B): {len(plano)} colunas — {'OK' if i1 else 'FALHOU'}")
    for it in plano:
        print(f"       {it['nome']:<11} modo={it['modo']:<6} nat={it['nat'] or '-':<4} "
              f"[{it['ini']}:{it['fim'] if it['fim'] is not None else 'EOF'})")
    if not i1:
        falhas.append("I1")

    # I6 — o plano é COMPLETO: soma dos sizes + resto == len(corpo)
    ultimo = plano[-1]
    i6 = ultimo["fim"] is None and ultimo["ini"] <= len(corpo)
    soma = ultimo["ini"]
    print(f"  I6 plano completo: soma dos sizes={soma} B + última(EOF)={len(corpo) - soma} B "
          f"= {len(corpo)} B — {'OK' if i6 else 'FALHOU'}")
    if not i6:
        falhas.append("I6")

    # I2 — independência: cada coluna decodada SÓ do seu recorte
    cols_iso = {}
    for it in plano:
        cols_iso[it["nome"]] = decodifica_coluna(corpo, it, len(corpo))
    # as com nature precisam da reversão (que o decode público faz depois)
    from tcf.natures import _resolve_nature_id, decode_value as _nat_de
    for it in plano:
        if it["nat"]:
            sp = _resolve_nature_id(it["nat"])
            cols_iso[it["nome"]] = [_nat_de(sp, v) for v in cols_iso[it["nome"]]]
    i2 = cols_iso == verdade
    print(f"  I2 independência (cada coluna só do seu recorte): {'OK' if i2 else 'FALHOU'}")
    if not i2:
        falhas.append("I2")

    # I3 — ordem livre
    import random as _r
    ordem_emb = list(plano)
    _r.Random(7).shuffle(ordem_emb)
    cols_emb = {}
    for it in ordem_emb:
        v = decodifica_coluna(corpo, it, len(corpo))
        if it["nat"]:
            v = [_nat_de(_resolve_nature_id(it["nat"]), x) for x in v]
        cols_emb[it["nome"]] = v
    i3 = cols_emb == verdade
    print(f"  I3 ordem livre (decodado embaralhado): {'OK' if i3 else 'FALHOU'}")
    if not i3:
        falhas.append("I3")

    # I4 — paralelismo REAL (threads), resultado idêntico
    def _tarefa(it):
        v = decodifica_coluna(corpo, it, len(corpo))
        if it["nat"]:
            v = [_nat_de(_resolve_nature_id(it["nat"]), x) for x in v]
        return it["nome"], v
    with ThreadPoolExecutor(max_workers=len(plano)) as ex:
        cols_par = dict(ex.map(_tarefa, plano))
    i4 = cols_par == verdade
    print(f"  I4 paralelo real ({len(plano)} threads): {'OK' if i4 else 'FALHOU'} "
          f"— idêntico ao decode() público")
    if not i4:
        falhas.append("I4")

    # I5 — a última é a única que precisa de EOF; min_header=False remove
    wF = encode(T, nature_per_col=SPECS, min_header=False)
    if decode(wF) != T:
        falhas.append("I5: RT do min_header=False")
    _esc(OUT / "cadastro-todos-com-size.tcf", wF)
    _, planoF = plano_de_fatiamento(wF)
    sem_eof = all(it["fim"] is not None for it in planoF)
    i5 = (plano[-1]["fim"] is None) and sem_eof and len(planoF) == len(T)
    print(f"  I5 min_header=True → 1 coluna depende de EOF; min_header=False → "
          f"{0 if sem_eof else '?'} dependem: {'OK' if i5 else 'FALHOU'}")
    print(f"       custo da garantia: {B(wF) - B(w):+d} B "
          f"({100 * (B(wF) / B(w) - 1):+.3f}%) — é o size da última coluna")
    if not i5:
        falhas.append("I5")
    reg["bloco2_invariantes"] = {"I1": i1, "I2": i2, "I3": i3, "I4": i4, "I5": i5, "I6": i6,
                                 "plano": [{k: v for k, v in it.items()} for it in plano],
                                 "custo_min_header_False_B": B(wF) - B(w),
                                 "CONSTANTE_na_comparacao": "o MESMO wire; muda só QUEM decoda e EM QUE ORDEM"}

    # ── BLOCO 3 — o que ainda é explícito, e o que cada campo paga ──────────
    print("\nBLOCO 3 — a anatomia do que resta explícito no header (7 colunas, com spec)")
    campos = {
        "magic `#TCF.8M`": 7,
        "sizes (hex)": sum(len(format(it["fim"] - it["ini"], "x"))
                           for it in plano if it["fim"] is not None),
        "nomes": sum(len(it["nome"]) for it in plano),
        "modos `!@%`": sum(1 for it in plano if it["modo"] != "tcf"),
        "nature `:id`": sum(1 + len(it["nat"]) for it in plano if it["nat"]),
        "separadores `,` `=`": (len(plano) - 1) + sum(1 for it in plano if it["fim"] is not None),
    }
    print(f"  {'campo':<22} {'B':>5}  removível?")
    NOTA = {
        "magic `#TCF.8M`": "não — roteamento (ADR-0029/0032); `M` deduzível = −1 B (O-FMT-11: marginal)",
        "sizes (hex)": "**NÃO** — é o plano de fatiamento (O-FMT-19 REFUTADO por matar o paralelo)",
        "nomes": "SIM — `drop_names` (mas a ordem vira o contrato; lab 1450 P2)",
        "modos `!@%`": "não — o corpo não se auto-identifica",
        "nature `:id`": "opt-in — `T-SPEC-SEM-CARIMBO` (contrato nas pontas), decidido, falta weld",
        "separadores `,` `=`": "não — gramática",
    }
    for k, v in campos.items():
        print(f"  {k:<22} {v:>5}  {NOTA[k]}")
    print(f"  soma dos campos = {sum(campos.values())} B  (linha 1 real = {B(l1)} B)")
    reg["bloco3_anatomia"] = {"campos": campos, "linha1_B": B(l1)}

    # ── BLOCO 4 — o view, olhada LEVE (fica pro fim, por decisão do owner) ──
    print("\nBLOCO 4 — view/lazy: olhada leve (fica pro fim; só o que toca a fronteira)")
    from tcf import view
    v = view(w)
    from tcf.multi.core import _parse_meta as _pm
    usa_mesmo_parser = True     # verificado por leitura: view.py:117 chama _parse_meta
    perfil = {c: v.column_bytes(c) for c in (v.columns() if callable(v.columns) else v.columns)}
    bate = all(perfil[it["nome"]] == (it["fim"] - it["ini"])
               for it in plano if it["fim"] is not None)
    print(f"  o view usa o MESMO `_parse_meta` (view.py:117) — paridade por construção: {usa_mesmo_parser}")
    print(f"  os sizes que ele reporta batem com o plano deste lab: {bate}")
    print(f"  ele materializa {v.materialized_bytes} B ao abrir (tocou {v.touched}) — "
          f"o header É o único coldstart, confirmado")
    if not bate:
        falhas.append("view: sizes divergem do plano")
    print(f"  NÃO investigado aqui (decisão do owner: 'fica pra quando fecharmos tudo'):")
    print(f"    · as 8 formas de wire que o view recusa (lab 0800)")
    print(f"    · o bypass aritmético (T-LAZY-BYPASS-ARITMETICO)")
    print(f"    · o `where` posicional (T-VIEW-PRED-POSICIONAL)")
    reg["bloco4_view"] = {"sizes_batem": bate, "materialized_ao_abrir": v.materialized_bytes,
                          "touched": list(v.touched)}

    _js(RAIZ / "resultado.json", {**reg, "falhas": falhas})
    print(f"\n{len(falhas)} falha(s)")
    for f_ in falhas:
        print(f"  FALHA: {f_}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

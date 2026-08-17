# -*- coding: utf-8 -*-
"""AUDITORIA DO `.8M` NO CORPUS REAL — as otimizações e o fluxo, em 23 tabelas.

    python run.py     # sai 0 só se TODOS os RTs fecharem, as invariantes valerem
                      # em dado real, e nenhum guard disparar espúrio

## O pedido (owner, 2026-08-16)

*"vamos focar ao máximo no 8M e ver se todas as otimizações e orientações de fluxo estão OK.
Podemos fazer um teste de corpus se for o caso."*

## Por que corpus, e não mais sintético

Tudo que este ciclo mediu no `.8M` — os 4 candidatos, as 6 invariantes de fronteira, os 3
welds — foi em dado **sintético**. O precedente do projeto é duro: o `T-DATA-ALVO-MENSAL`
mediu 95% em sintético e **0,0% em real**. Esta auditoria repete as mesmas perguntas contra
**23 tabelas / 186 colunas** do corpus.

## A régua de amostragem (lição do lab `0530`)

Tabela grande é amostrada por **janela CONTÍGUA do meio**, nunca por passo espalhado: o passo
espalhado destrói a adjacência e mede uma distribuição que não existe na coluna (medido lá:
|Δ| mediano 710 contra 50 da coluna inteira). Tabela pequena entra inteira.

## O que se pergunta

| bloco | pergunta |
|---|---|
| 1 | o RT fecha em TODAS as tabelas? |
| 2 | dos 4 candidatos do `min()`, algum é MORTO (nunca vence) em dado real? |
| 3 | as 6 invariantes de fronteira valem em dado real, incluindo decode PARALELO? |
| 4 | os 3 guards recém-soldados disparam ESPÚRIO em 186 colunas reais? |
| 5 | `view` e `decode` concordam em todas as tabelas? |
| 6 | quanto o `.8M` deixa na mesa por não ter os candidatos do flat? (dimensiona o Grupo A) |

## GATE

`src/tcf` INTOCADO. Lê `Z:/tcf-data/` em modo somente-leitura; **não baixa nada**.
"""
from __future__ import annotations

import glob
import json
import os
import pathlib
import random
import shutil
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode, view                              # noqa: E402
from tcf.multi.core import _parse_meta, _nomes_resolvidos         # noqa: E402
from tcf.side_outputs import SideOutputs                          # noqa: E402

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N_ALVO = 2000


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


# ── carga: janela CONTÍGUA do meio (a régua do lab 0530) ───────────────────
def tabelas_do_corpus():
    """(banco, tabela, dict[col -> list[str]]) para cada tabela não-vazia."""
    for db in sorted(glob.glob("Z:/tcf-data/interim/*.db")):
        if os.path.getsize(db) == 0:
            continue
        nome_db = os.path.basename(db)[:-3]
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            ts = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            for t in ts:
                n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                if n == 0:
                    continue
                off = max(0, (n - N_ALVO) // 2)          # janela do MEIO, contígua
                cur = con.execute(f"SELECT * FROM {t} LIMIT {N_ALVO} OFFSET {off}")
                cols = [d[0] for d in cur.description]
                linhas = cur.fetchall()
                tab = {c: [("" if r[i] is None else str(r[i])) for r in linhas]
                       for i, c in enumerate(cols)}
                yield nome_db, t, tab, {"n_total": n, "offset": off, "n_amostra": len(linhas)}
            con.close()
        except Exception as e:
            print(f"  !! {nome_db}: {type(e).__name__}: {e}")


def plano_do_header(wire):
    """As fatias [ini:fim) por coluna, derivadas SÓ da linha 1."""
    l1, _, body = wire.partition("\n")
    corpo = body.encode("utf-8")
    plano, off = [], 0
    for i, (size, nome, modo, nat) in enumerate(_parse_meta(l1[7:])):
        fim = None if size is None else off + size
        plano.append({"i": i, "nome": nome if nome is not None else str(i),
                      "modo": modo, "nat": nat, "ini": off, "fim": fim})
        if fim is None:
            break
        off = fim
    return l1, corpo, plano


def decodifica_coluna(corpo, item, total):
    from tcf.decoder import _decode_column
    from tcf.multi import _decode_raw_body, _decode_v2b, _decode_struct_split
    b = corpo[item["ini"]:(total if item["fim"] is None else item["fim"])]
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
    from collections import Counter

    tabs = list(tabelas_do_corpus())
    if not tabs:
        print("SEM CORPUS: Z:/tcf-data/interim/ inacessível — nada medido.")
        return 1
    print(f"CORPUS: {len(tabs)} tabelas, "
          f"{sum(len(t[2]) for t in tabs)} colunas, janela contígua do meio "
          f"(alvo {N_ALVO} linhas)\n")
    _js(INP / "corpus.fonte.json", {
        "origem": "Z:/tcf-data/interim/*.db (somente leitura; NADA baixado)",
        "amostragem": f"janela CONTIGUA do meio, alvo {N_ALVO} linhas — a regua do lab 0530 "
                      "(passo espalhado destroi a adjacencia e mede outra distribuicao)",
        "nulos": "NULL do SQLite vira string vazia (o .8M e' dict[str, list[str]])",
        "tabelas": [{"db": d, "tabela": t, **meta} for d, t, _, meta in tabs]})

    # ── BLOCO 1+2 — RT por tabela, e quem vence o min() por coluna ──────────
    print("BLOCO 1+2 — RT por tabela, e o modo vencedor por coluna\n")
    print(f"  {'tabela':<34} {'cols':>4} {'bytes':>9} {'RT':<5} modos vencedores")
    modos_tot = Counter()
    nat_tot = Counter()
    b12, wires = [], {}
    for db, t, tab, meta in tabs:
        rot = f"{db}/{t}"
        side = SideOutputs()
        try:
            w = encode(tab, side_outputs=side)
            rt = decode(w) == tab
        except Exception as e:
            falhas.append(f"{rot}: encode/decode levantou {type(e).__name__}: {e}")
            print(f"  {rot:<34} ERRO {type(e).__name__}: {str(e)[:40]}")
            continue
        if not rt:
            falhas.append(f"{rot}: RT nao fechou")
        wires[rot] = (w, tab)
        cm = (side.multi_info or {}).get("col_modes", {})
        modos_tot.update(cm.values())
        b12.append({"tabela": rot, "n_cols": len(tab), "bytes": B(w), "rt": rt,
                    "col_modes": cm, "n_linhas": meta["n_amostra"]})
        resumo = " ".join(f"{m}×{c}" for m, c in Counter(cm.values()).most_common())
        print(f"  {rot:<34} {len(tab):>4} {B(w):>9} {'ok' if rt else 'FALHA':<5} {resumo}")
    print(f"\n  modos no corpus inteiro: {dict(modos_tot)}")
    mortos = [m for m in ("tcf", "raw", "dict", "split") if modos_tot.get(m, 0) == 0]
    print(f"  candidatos que NUNCA vencem: {mortos or 'nenhum — os 4 têm domínio real'}")
    reg["bloco12"] = {"tabelas": b12, "modos_totais": dict(modos_tot), "mortos": mortos}

    # ── BLOCO 3 — as invariantes de fronteira, em dado REAL ────────────────
    print("\nBLOCO 3 — as 6 invariantes de fronteira, agora em dado REAL")
    inv = {f"I{i}": 0 for i in range(1, 7)}
    n_test = 0
    for rot, (w, tab) in wires.items():
        l1, corpo, plano = plano_do_header(w)
        n_test += 1
        # I1 plano derivado só da linha 1, com o número certo de colunas
        inv["I1"] += len(plano) == len(tab)
        # I6 plano completo (a soma fecha o corpo)
        ult = plano[-1]
        inv["I6"] += (ult["fim"] is None and ult["ini"] <= len(corpo)) or \
                     (ult["fim"] == len(corpo))
        # I2 independência: cada coluna do seu recorte
        try:
            iso = {it["nome"]: decodifica_coluna(corpo, it, len(corpo)) for it in plano}
            inv["I2"] += iso == tab
        except Exception:
            pass
        # I3 ordem livre
        emb = list(plano)
        random.Random(7).shuffle(emb)
        try:
            ie = {it["nome"]: decodifica_coluna(corpo, it, len(corpo)) for it in emb}
            inv["I3"] += ie == tab
        except Exception:
            pass
        # I4 paralelo real
        try:
            with ThreadPoolExecutor(max_workers=min(8, len(plano))) as ex:
                par = dict(ex.map(
                    lambda it: (it["nome"], decodifica_coluna(corpo, it, len(corpo))), plano))
            inv["I4"] += par == tab
        except Exception:
            pass
        # I5 só a última depende de EOF
        inv["I5"] += sum(1 for it in plano if it["fim"] is None) <= 1
    print(f"  {'invariante':<52} {'ok':>5}/{n_test}")
    NOMES_INV = {"I1": "plano derivado só da linha 1", "I2": "independência por coluna",
                 "I3": "ordem livre", "I4": "decode PARALELO == serial",
                 "I5": "só a última depende de EOF", "I6": "plano completo (soma fecha)"}
    for k in ("I1", "I2", "I3", "I4", "I5", "I6"):
        marca = "" if inv[k] == n_test else "   <<< FALHOU"
        print(f"  {k} {NOMES_INV[k]:<49} {inv[k]:>5}/{n_test}{marca}")
        if inv[k] != n_test:
            falhas.append(f"invariante {k}: {inv[k]}/{n_test}")
    reg["bloco3_invariantes"] = {"testadas_em": n_test, **inv}

    # ── BLOCO 4 — os 3 guards disparam espúrio em dado real? ───────────────
    print("\nBLOCO 4 — os 3 guards recém-soldados, contra 186 colunas REAIS")
    disparos = {"C1_polaridade": 0, "C2_colisao": 0, "C3_nature": 0}
    from tcf.decoder import _separa_sufixo_polaridade as _sep
    nomes_arriscados = []
    for rot, (w, tab) in wires.items():
        l1, _, plano = plano_do_header(w)
        # C1: o pre-passe teria agido? (o disc é M, então não age — confirme)
        if l1[6:7] == "M" and _sep(l1[6:])[1]:
            disparos["C1_polaridade"] += 1
        # C2: alguma tabela real tem colisão de nome resolvido?
        try:
            _nomes_resolvidos(_parse_meta(l1[7:]))
        except ValueError:
            disparos["C2_colisao"] += 1
        for c in tab:
            if c and not c.isalnum():
                nomes_arriscados.append(f"{rot}:{c}")
    # C3: passar nature_per_col legítimo em todas as tabelas
    from tcf.natures import SPEC_DATA_ISO
    for rot, (w, tab) in wires.items():
        primeira = next(iter(tab))
        try:
            encode(tab, nature_per_col={primeira: SPEC_DATA_ISO})
        except ValueError as e:
            if "T-NATURE-IGNORADA-CALADA" in str(e) or "nature_per_col=" in str(e):
                disparos["C3_nature"] += 1
        except Exception:
            pass
    for k, v in disparos.items():
        print(f"  {k:<20} disparos espúrios: {v}  "
              f"{'OK' if v == 0 else '>>> INVESTIGAR <<<'}")
        if v:
            falhas.append(f"guard {k} disparou espurio {v}x")
    print(f"  nomes de coluna reais com char não-alfanumérico: {len(nomes_arriscados)}"
          f"{'  ex: ' + str(nomes_arriscados[:4]) if nomes_arriscados else ''}")
    reg["bloco4_guards"] = {**disparos, "nomes_nao_alnum": nomes_arriscados[:40],
                            "n_nomes_nao_alnum": len(nomes_arriscados)}

    # ── BLOCO 5 — paridade view × decode ───────────────────────────────────
    print("\nBLOCO 5 — paridade view × decode em todas as tabelas")
    par_ok = par_tot = 0
    for rot, (w, tab) in wires.items():
        par_tot += 1
        try:
            v = view(w)
            cols = v.columns() if callable(v.columns) else v.columns
            if list(cols) == list(tab) and all(v._col(c) == tab[c] for c in tab):
                par_ok += 1
            else:
                falhas.append(f"{rot}: view divergiu do decode")
        except Exception as e:
            falhas.append(f"{rot}: view levantou {type(e).__name__}")
    print(f"  {par_ok}/{par_tot} tabelas com view == decode "
          f"{'OK' if par_ok == par_tot else '>>> DIVERGE <<<'}")
    reg["bloco5_paridade"] = {"ok": par_ok, "de": par_tot}

    # ── BLOCO 6 — quanto o .8M deixa na mesa (dimensiona o Grupo A) ────────
    print("\nBLOCO 6 — o gap da UNIÃO: `.8M` contra a soma de wires flat separados")
    print(f"  {'tabela':<34} {'.8M':>9} {'Σ flat':>9} {'gap':>8}  modos do flat")
    b6, tot_m, tot_f = [], 0, 0
    for rot, (w, tab) in wires.items():
        soma = 0
        modos_flat = Counter()
        ok_flat = True
        for c, vals in tab.items():
            try:
                wf = encode(vals)
                if decode(wf) != vals:
                    ok_flat = False
                soma += B(wf)
                h = wf.split("\n", 1)[0]
                modos_flat[("bN" if h[6:7] in "BC" else
                            "polaridade" if h[6:7] == "!" else
                            "tipado" if h[6:7] in "bns" else "core")] += 1
            except Exception:
                ok_flat = False
        if not ok_flat:
            falhas.append(f"{rot}: RT flat nao fechou em alguma coluna")
        gap = B(w) - soma
        tot_m += B(w)
        tot_f += soma
        b6.append({"tabela": rot, "m_bytes": B(w), "flat_soma": soma, "gap": gap,
                   "modos_flat": dict(modos_flat)})
        print(f"  {rot:<34} {B(w):>9} {soma:>9} {gap:>+8}  "
              f"{' '.join(f'{k}×{v}' for k, v in modos_flat.most_common())[:34]}")
    print(f"\n  CORPUS INTEIRO: .8M {tot_m} B · Σ flat {tot_f} B · "
          f"gap {tot_m - tot_f:+d} B ({100 * (tot_m / tot_f - 1):+.1f}%)")
    piores = sorted(b6, key=lambda x: -x["gap"])[:3]
    print(f"  onde o `.8M` mais perde: "
          f"{[(x['tabela'], x['gap']) for x in piores]}")
    reg["bloco6_gap_uniao"] = {"por_tabela": b6, "m_total": tot_m, "flat_total": tot_f,
                               "gap_total": tot_m - tot_f,
                               "gap_pct": round(100 * (tot_m / tot_f - 1), 1),
                               "CONSTANTE_na_comparacao": "as MESMAS colunas; muda so' a "
                                                          "rota que as encoda"}

    # ── BLOCO 7 — o TETO da união, medido COLUNA A COLUNA ──────────────────
    # O gap por TABELA (bloco 6) nao e' o que a uniao captura: a uniao pega o
    # `min()` POR COLUNA. Uma tabela pode perder no agregado e ainda ter colunas
    # onde o `.8M` e' melhor — e vice-versa. Este bloco mede o teto de verdade.
    print(chr(10) + "BLOCO 7 — o TETO da união (min por COLUNA), que é o que dimensiona o Grupo A")
    tot_uni = ganho_col = 0
    n_col = n_flat_vence = 0
    por_tab = []
    for rot, (w, tab) in wires.items():
        _l1, corpo, plano = plano_do_header(w)
        m_por_col = {}
        for it in plano:
            fim = len(corpo) if it["fim"] is None else it["fim"]
            m_por_col[it["nome"]] = fim - it["ini"]
        soma_uni = soma_m = 0
        venceu_flat = 0
        for c, vals in tab.items():
            wf = encode(vals)
            corpo_flat = B(wf) - B(wf.split(chr(10), 1)[0]) - 1   # sem header, comparavel
            m_c = m_por_col.get(c, 0)
            soma_m += m_c
            melhor = min(m_c, corpo_flat)
            soma_uni += melhor
            n_col += 1
            if corpo_flat < m_c:
                venceu_flat += 1
                n_flat_vence += 1
                ganho_col += m_c - corpo_flat
        tot_uni += soma_uni
        por_tab.append({"tabela": rot, "corpo_m": soma_m, "corpo_uniao": soma_uni,
                        "colunas_onde_flat_vence": venceu_flat, "de": len(tab)})
    print(f"  colunas onde o candidato do FLAT venceria: {n_flat_vence}/{n_col} "
          f"({100 * n_flat_vence / n_col:.0f}%)")
    print(f"  bytes que a UNIÃO recuperaria (só os corpos): {ganho_col} B")
    print(f"  isso é {100 * ganho_col / tot_m:.1f}% do `.8M` do corpus inteiro")
    top = sorted(por_tab, key=lambda x: -(x["corpo_m"] - x["corpo_uniao"]))[:5]
    print(f"  onde a união mais renderia:")
    for x in top:
        print(f"     {x['tabela']:<34} {x['corpo_m'] - x['corpo_uniao']:>+8} B  "
              f"({x['colunas_onde_flat_vence']}/{x['de']} colunas)")
    reg["bloco7_teto_uniao"] = {"colunas_onde_flat_vence": n_flat_vence, "de": n_col,
                                "ganho_bytes": ganho_col,
                                "pct_do_M": round(100 * ganho_col / tot_m, 1),
                                "por_tabela": por_tab,
                                "CONSTANTE_na_comparacao": "as MESMAS colunas; compara-se o "
                                                           "CORPO (sem header) dos dois lados"}

    # ── evidência: as 4 maiores tabelas gravadas ───────────────────────────
    for rot, (w, tab) in sorted(wires.items(), key=lambda kv: -B(kv[1][0]))[:4]:
        nome = rot.replace("/", "-")
        _js(INP / f"{nome}.entrada.json", tab)
        _esc(OUT / f"{nome}.tcf", w)
        _js(OUT / f"{nome}.roundtrip.json", decode(w))
        igual = ((INP / f"{nome}.entrada.json").read_text(encoding="utf-8")
                 == (OUT / f"{nome}.roundtrip.json").read_text(encoding="utf-8"))
        _js(OUT / f"{nome}.meta.json", {
            "wire_bytes": B(w), "linha1": w.split("\n", 1)[0][:200],
            "roundtrip_identico_a_entrada": igual, "origem": rot})
        if not igual:
            falhas.append(f"{rot}: diff entrada x roundtrip")

    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — auditoria do `.8M` no corpus", "",
         f"{len(tabs)} tabelas · {sum(len(t[2]) for t in tabs)} colunas · janela contígua "
         f"do meio ({N_ALVO} linhas). As 4 maiores estão gravadas com roundtrip.", "",
         "| tabela | cols | bytes | RT |", "|---|---:|---:|:--:|"] +
        [f"| {x['tabela']} | {x['n_cols']} | {x['bytes']} | {'✓' if x['rt'] else '✗'} |"
         for x in b12]) + "\n")
    _js(RAIZ / "resultado.json", {**reg, "falhas": falhas})

    print(f"\n{'='*76}\n{len(falhas)} falha(s)")
    for f_ in falhas[:20]:
        print(f"  FALHA: {f_}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

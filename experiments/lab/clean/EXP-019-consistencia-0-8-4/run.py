"""EXP-019: a 0.8.4 e' consistente? Sete portoes sobre oito amostras reais estratificadas.

A 0.8.4 mexeu em roteamento (ADR-0049, o `#TCF.8R`) e em decisao de emissao (ADR-0050, o FLOOR
do `sort_by`), e junto em quatro defeitos de superficie e num laco quente da view. Os testes
unitarios cobrem cada peca; o que falta e' a pergunta do conjunto, em DADO REAL e em VOLUME:
as pecas concordam entre si?

Os sete portoes, e o que cada um reprovaria:

  G1  ROUND-TRIP           o contrato. Se cair, nada mais importa.
  G2  DOMINANCIA           `.8R` nunca maior que o `.8H` que a mesma entrada emitia. A premissa
                           do ADR-0049 e' estrutural, entao uma unica violacao a derruba.
  G3  EQUIVALENCIA         as duas grafias da MESMA tabela dao o mesmo corpo, e cada uma volta
                           NA FORMA EM QUE ENTROU. E' a ideia inteira do ADR-0049.
  G4  FLOOR NUNCA-PIOR     `sort_by` nao pode fazer o wire crescer, em coluna-chave nenhuma.
  G5  PARIDADE VIEW        `view.select()` == `decode()`, e `agg_by` == `group_sum` em toda
                           chave, inclusive nos blobs que o FLOOR deixou fora de ordem.
  G6  FRONTEIRA            o que deve ficar no `.8H` fica, e continua fazendo round-trip.
  G7  group_count          a leitura estrutural bate com contar o decode, valor a valor.

Roda da propria pasta. Grava `inputs/`, `intermediates/`, `outputs/` e `resultado.json`.
"""

from __future__ import annotations

import json
import sys
import time
import warnings
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[4]
sys.path.insert(0, str(RAIZ / "src"))

warnings.simplefilter("ignore")

import tcf  # noqa: E402
from casos import AMOSTRAS, colunas, carrega  # noqa: E402
from tcf import decode, encode  # noqa: E402
from tcf.hierarchical import _encode_hierarchical  # noqa: E402
from tcf.view import view  # noqa: E402


def b(w: str) -> int:
    return len(w.encode("utf-8"))


def cardinalidade(vals) -> int:
    try:
        return len(set(vals))
    except TypeError:
        return len({str(v) for v in vals})


def chaves_de_grupo(cols: dict, n: int, limite: int = 40) -> list[str]:
    """As colunas que alguem de fato usaria pra agrupar: poucas distintas, e nao constantes."""
    fora = []
    for nome, vals in cols.items():
        k = cardinalidade(vals)
        if 2 <= k <= limite and k < n:
            fora.append(nome)
    return fora


def colunas_numericas(cols: dict) -> list[str]:
    fora = []
    for nome, vals in cols.items():
        amostra = [v for v in vals if v is not None][:50]
        if amostra and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                           for v in amostra):
            fora.append(nome)
    return fora


def main() -> int:
    for d in ("inputs", "intermediates", "outputs"):
        (AQUI / d).mkdir(exist_ok=True)

    print("=" * 79)
    print(f"  EXP-019: consistencia da {tcf.__version__} em 8 amostras reais estratificadas")
    print("=" * 79)

    relato: dict = {"versao": tcf.__version__, "amostras": {}, "portoes": {}}
    falhas: list[str] = []
    dados: dict[str, tuple] = {}

    print(f"\n  {'amostra':<17} {'linhas':>7} {'cols':>5} {'estratos':>9} {'TVD':>8}")
    for rotulo, _ds, _tab, estrato, _nota in AMOSTRAS:
        linhas, trace = carrega(rotulo)
        cols = colunas(linhas)
        dados[rotulo] = (linhas, cols)
        met = next((t for t in trace if t.startswith("stratify_metrics")), "")
        tvd = met.split("TVD=")[1].split(",")[0] if "TVD=" in met else "?"
        n_estratos = cardinalidade(cols[estrato])
        print(f"  {rotulo:<17} {len(linhas):>7} {len(cols):>5} {n_estratos:>9} {tvd:>8}")
        relato["amostras"][rotulo] = {
            "linhas": len(linhas), "colunas": len(cols), "estrato": estrato,
            "n_estratos": n_estratos, "tvd": tvd,
        }
        (AQUI / "intermediates" / f"{rotulo}.shaper-trace.txt").write_text(
            "\n".join(trace) + "\n", encoding="utf-8", newline="\n")
    (AQUI / "inputs" / "amostras.entrada.json").write_text(
        json.dumps({r: v[0][:3] for r, v in dados.items()},
                   ensure_ascii=False, indent=1, default=str) + "\n",
        encoding="utf-8", newline="\n")

    # ---------------------------------------------------------------- G1 + G2 + G3
    print("\n" + "=" * 79)
    print("  G1 round-trip · G2 dominancia · G3 equivalencia das grafias")
    print("=" * 79)
    print(f"\n  {'amostra':<17} {'.8H (antes)':>12} {'.8R (hoje)':>12} {'ganho':>9}"
          f" {'RT':>4} {'DOM':>4} {'EQV':>4}")
    g1 = g2 = g3 = True
    total_h = total_r = 0
    for rotulo, (linhas, cols) in dados.items():
        w_r, w_m = encode(linhas), encode(cols)
        w_h = _encode_hierarchical(linhas)
        rt = decode(w_r) == linhas and decode(w_m) == cols
        dom = b(w_r) <= b(w_h)
        # o corpo depois do discriminador tem de ser IDENTICO nas duas grafias
        eqv = w_r[7:] == w_m[7:] and w_r[6] == "R" and w_m[6] == "M"
        g1, g2, g3 = g1 and rt, g2 and dom, g3 and eqv
        total_h += b(w_h)
        total_r += b(w_r)
        for nome, w in (("8R", w_r), ("8M", w_m), ("8H", w_h)):
            (AQUI / "outputs" / f"{rotulo}.{nome}.tcf").write_text(
                w, encoding="utf-8", newline="")
        print(f"  {rotulo:<17} {b(w_h):>10} B {b(w_r):>10} B "
              f"{100 * (b(w_r) - b(w_h)) / b(w_h):>+8.1f}%"
              f" {'ok' if rt else 'X':>4} {'ok' if dom else 'X':>4} {'ok' if eqv else 'X':>4}")
        relato["amostras"][rotulo].update(
            {"bytes_8h": b(w_h), "bytes_8r": b(w_r), "rt": rt, "dominancia": dom,
             "equivalencia": eqv, "header_8r": w_r.split("\n", 1)[0][:60]})
        if not rt:
            falhas.append(f"G1 round-trip em {rotulo}")
        if not dom:
            falhas.append(f"G2 dominancia em {rotulo}")
        if not eqv:
            falhas.append(f"G3 equivalencia em {rotulo}")
    print(f"\n  Somando as 8: {total_h} B no `.8H` contra {total_r} B no `.8R`, "
          f"{100 * (total_r - total_h) / total_h:+.1f}%.")
    relato["portoes"].update({"G1_round_trip": g1, "G2_dominancia": g2,
                              "G3_equivalencia": g3,
                              "bytes_8h_total": total_h, "bytes_8r_total": total_r})

    # ---------------------------------------------------------------------- G4
    print("\n" + "=" * 79)
    print("  G4: o FLOOR do `sort_by` e' nunca-pior, em TODA coluna-chave")
    print("=" * 79)
    print(f"\n  {'amostra':<17} {'chaves':>7} {'ordenou':>8} {'melhor ganho':>13}"
          f" {'pior saldo':>11}")
    g4 = True
    detalhe_g4 = {}
    for rotulo, (linhas, cols) in dados.items():
        n = len(linhas)
        chaves = chaves_de_grupo(cols, n)
        base = b(encode(cols))
        ordenou = 0
        melhor = pior = 0
        for k in chaves:
            com = b(encode(cols, sort_by=k))
            if com > base:
                g4 = False
                falhas.append(f"G4 sort_by cresceu em {rotulo}/{k}: {com} > {base}")
            if com < base:
                ordenou += 1
            melhor = min(melhor, com - base)
            pior = max(pior, com - base)
        print(f"  {rotulo:<17} {len(chaves):>7} {ordenou:>8} {melhor:>11} B {pior:>9} B")
        detalhe_g4[rotulo] = {"n_chaves": len(chaves), "ordenou": ordenou,
                              "melhor_ganho_bytes": melhor, "pior_saldo_bytes": pior,
                              "base_bytes": base}
    print("""
  `pior saldo` = 0 em toda linha e' o portao: com o FLOOR, pedir `sort_by` nunca cobra.
  `ordenou` conta em quantas chaves a ordenacao de fato VENCEU e foi emitida.""")
    relato["portoes"]["G4_floor_nunca_pior"] = g4
    relato["G4_detalhe"] = detalhe_g4

    # ---------------------------------------------------------------------- G5
    print("\n" + "=" * 79)
    print("  G5: a view concorda com o decode, e os dois caminhos de group-by concordam")
    print("=" * 79)
    print(f"\n  {'amostra':<17} {'select==decode':>15} {'pares agg/group':>16} {'iguais':>8}")
    g5 = True
    for rotulo, (linhas, cols) in dados.items():
        w = encode(linhas)
        v = view(w)
        sel_ok = v.select() == decode(w)
        if not sel_ok:
            g5 = False
            falhas.append(f"G5 view.select != decode em {rotulo}")
        chaves = chaves_de_grupo(cols, len(linhas))[:6]
        nums = colunas_numericas(cols)[:1]
        pares = iguais = 0
        for k in chaves:
            for c in nums:
                # o blob ORDENADO (quando o FLOOR o emite) e o NAO-ordenado, nos dois casos
                for wire in (w, encode(cols, sort_by=k)):
                    vv = view(wire)
                    pares += 1
                    if vv.agg_by(k, c, "sum") == vv.group_sum(k, c):
                        iguais += 1
                    else:
                        g5 = False
                        falhas.append(f"G5 agg_by != group_sum em {rotulo}/{k}/{c}")
        print(f"  {rotulo:<17} {'ok' if sel_ok else 'X':>15} {pares:>16} {iguais:>8}")
    relato["portoes"]["G5_paridade_view"] = g5

    # ---------------------------------------------------------------------- G6
    print("\n" + "=" * 79)
    print("  G6: a fronteira do `.8H` continua de pe'")
    print("=" * 79)
    print(f"\n  {'amostra':<17} {'ragged':>8} {'aninhado':>9} {'LF valor':>9}"
          f" {'CR valor':>9} {'LF nome':>8}")
    g6 = True
    for rotulo, (linhas, cols) in dados.items():
        base = [dict(r) for r in linhas[:40]]
        prim = list(base[0])[0]
        variantes = {
            "ragged": [{k: v for k, v in r.items() if not (i and k == prim)}
                       for i, r in enumerate(base)],
            "aninhado": [{**r, prim: {"v": r[prim]}} for r in base],
            "lf-valor": [{**r, prim: f"{r[prim]}\nx"} for r in base],
            "cr-valor": [{**r, prim: f"{r[prim]}\rx"} for r in base],
            "lf-nome": [{(f"{k}\nz" if k == prim else k): v for k, v in r.items()}
                        for r in base],
        }
        linha = []
        for nome, d in variantes.items():
            w = encode(d)
            fica = w.startswith("#TCF.8H")
            rt = decode(w) == d
            if not (fica and rt):
                g6 = False
                falhas.append(f"G6 {rotulo}/{nome}: fica_8H={fica} rt={rt}")
            linha.append("ok" if (fica and rt) else "X")
        print(f"  {rotulo:<17} {linha[0]:>8} {linha[1]:>9} {linha[2]:>9}"
              f" {linha[3]:>9} {linha[4]:>8}")
    print("""
  Estas cinco formas TEM de continuar no `.8H`, e nao por gosto: o hierarquico escapa
  folhas e nomes, o flat os recusa. Rotear qualquer uma tiraria uma capacidade que a
  entrada ja' tinha, trocando um round-trip que funciona por um erro.""")
    relato["portoes"]["G6_fronteira"] = g6

    # ---------------------------------------------------------------------- G7
    print("\n" + "=" * 79)
    print("  G7: `group_count` estrutural bate com contar o decode")
    print("=" * 79)
    print(f"\n  {'amostra':<17} {'chaves':>7} {'batem':>7} {'modo @dict':>11}"
          f" {'us/chamada':>11}")
    g7 = True
    for rotulo, (linhas, cols) in dados.items():
        w = encode(linhas)
        v = view(w)
        chaves = chaves_de_grupo(cols, len(linhas))[:8]
        batem = em_dict = 0
        t0 = time.perf_counter()
        for k in chaves:
            esperado = dict(Counter(cols[k]))
            if v.group_count(k) == esperado:
                batem += 1
            else:
                g7 = False
                falhas.append(f"G7 group_count divergiu em {rotulo}/{k}")
            if v._mode.get(v._resolve_col(k)) == "dict":
                em_dict += 1
        dt = (time.perf_counter() - t0) / max(1, len(chaves)) * 1e6
        print(f"  {rotulo:<17} {len(chaves):>7} {batem:>7} {em_dict:>11} {dt:>10.0f}")
    relato["portoes"]["G7_group_count"] = g7

    # ------------------------------------------------------------------ veredito
    print("\n" + "=" * 79)
    print("  VEREDITO")
    print("=" * 79)
    portoes = {k: v for k, v in relato["portoes"].items() if isinstance(v, bool)}
    for nome, ok in portoes.items():
        print(f"  {'PASSA' if ok else 'REPROVA':>8}  {nome}")
    todos = all(portoes.values())
    print(f"\n  {len(portoes)} portoes, {sum(portoes.values())} passam.")
    if falhas:
        print(f"\n  {len(falhas)} falha(s):")
        for f in falhas[:20]:
            print(f"    - {f}")
    relato["falhas"] = falhas
    relato["veredito"] = "consistente" if todos else "INCONSISTENTE"

    (AQUI / "resultado.json").write_text(
        json.dumps(relato, ensure_ascii=False, indent=1, default=str) + "\n",
        encoding="utf-8", newline="\n")
    print("\n  evidencia: inputs/ · intermediates/ (traces do Shaper) · outputs/ (24 wires)"
          " · resultado.json")
    return 0 if todos else 1


if __name__ == "__main__":
    sys.exit(main())

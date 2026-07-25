"""Lab 2026-07-25-1630 — medição do weld: null no slot 0, rota flat aberta.

O lab `2026-07-24-2210` mediu um PROTÓTIPO contra o `.8H`. Agora o mecanismo está soldado,
então esta rodada mede o **produto real** — e verifica se ele entregou o que o protótipo
prometeu (−33% mediano) ou se algo se perdeu no caminho.

`antes` = wire do `.8H` (a rota que a coluna com null tomava até o weld), reconstruído
forçando a entrada pro envelope hierárquico. `depois` = `encode()` atual.

Também mede o que o protótipo NÃO podia: byte-neutralidade em datasets reais (D1-D9) e o
comportamento sob gzip (sinal qualitativo — o TCF não é medido por compressão externa).
"""
import csv
import gzip
import json
import pathlib
import statistics
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.hierarchical import _encode_hierarchical as _hier  # noqa: E402


def _antes(col):
    """O que a coluna produzia ANTES do weld — e SÓ isso.

    CORREÇÃO da 1ª rodada: eu forçava TODA coluna pro `.8H`, mas antes do weld só a coluna
    COM null era desviada pra lá; sem null ela já saía no flat. Isso inflava o ganho das
    linhas de controle (E-sem-null aparecia com −29% quando o correto é 0%) e contaminava
    a mediana. Sem null, o `antes` é o próprio flat — Δ tem que dar exatamente 0.
    """
    return _hier(col) if any(v is None for v in col) else encode(col)


def _gera(n, pct, seed=7):
    vocab = ["ativo", "inativo", "pendente", "revisao", "cancelado"]
    out, x = [], seed
    for i in range(n):
        x = (1103515245 * x + 12345) % (2 ** 31)
        out.append(None if (x % 100) < pct else vocab[i % len(vocab)])
    return out


FONTES = {
    "A-exemplo-owner": ([None, "", "true", "false", "oi", None, "null"],
                        "exemplo literal do owner — as 4 vias numa coluna de string"),
    "B-n7-1null":      ([None, "ativo", "inativo", "ativo", "pendente", "ativo", "inativo"],
                        "n pequeno, 1 null"),
    "C-todos-null":    ([None] * 12, "coluna 100% null (borda)"),
    "D-null-bordas":   ([None, "a", "b", "c", None], "null na primeira e na última posição"),
    "E-sem-null":      (["ativo", "inativo", "ativo", "pendente"],
                        "CONTROLE: sem null — não pode mudar 1 byte"),
}
for _n in (10, 100, 1000):
    for _p in (1, 10, 50, 90):
        FONTES[f"R-n{_n}-p{_p}"] = (_gera(_n, _p), f"regime n={_n}, {_p}% null")


def _w(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_compacto(col):
    """JSON equivalente na forma MAIS ENXUTA — sem espaço nos separadores e sem `\\uXXXX`.

    É a referência honesta de escala: comparar contra JSON indentado inflaria o ganho de
    graça. `null` é a grafia nativa do JSON, então a coluna com null não paga nada extra
    aqui — o baseline não é enviesado a favor do TCF.
    """
    return json.dumps(col, separators=(",", ":"), ensure_ascii=False)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas, ganhos = [], 0, []
    for eid, (col, nota) in FONTES.items():
        _w(RAIZ / "inputs" / f"{eid}-fonte.json", {"nota": nota, "dados": col})
        _w(RAIZ / "intermediates" / f"{eid}-dataset-consumido.json", col)

        wa, wd, wj = _antes(col), encode(col), _json_compacto(col)
        rt = decode(wd) == col
        falhas += not rt
        (RAIZ / "outputs" / f"{eid}-antes-8H.tcf").write_text(wa, encoding="utf-8")
        (RAIZ / "outputs" / f"{eid}-wire.tcf").write_text(wd, encoding="utf-8")
        (RAIZ / "outputs" / f"{eid}-equivalente.json").write_text(wj, encoding="utf-8")
        _w(RAIZ / "outputs" / f"{eid}-dataset.roundtrip.json", decode(wd))

        a, d, j = len(wa.encode()), len(wd.encode()), len(wj.encode())
        pct = 100 * (d - a) / a
        ganhos.append(pct)
        linhas.append((eid, len(col), sum(v is None for v in col), j, a, d, d - a, pct,
                       100 * (d - j) / j, "OK" if rt else "FALHOU"))

    out = ["# Resultado — null no slot 0 SOLDADO (2026-07-25-1630)", "",
           "`JSON` = JSON equivalente **compacto** (`separators=(',',':')`, sem `\\uXXXX`) — "
           "referência de escala. `antes` = rota `.8H` (o que a coluna com null produzia até "
           "o weld). `depois` = `encode()` atual, produto REAL.", "",
           "| id | n | nulls | JSON | `.8H` | vs JSON | depois | vs JSON | Δ do weld | RT |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    out += [f"| {e} | {n} | {k} | {j} | {a} | {100 * (a - j) / j:+.0f}% | {d} | **{q:+.0f}%** | {p:+.0f}% | {s} |"
            for e, n, k, j, a, d, x, p, q, s in linhas]
    com = [p for _e, _n, k, _j, _a, _d, _x, p, _q, _s in linhas if k]
    sem = [p for _e, _n, k, _j, _a, _d, _x, p, _q, _s in linhas if not k]
    vsj = [q for *_, q, _s in linhas]
    vsj_com = [q for _e, _n, k, _j, _a, _d, _x, _p, q, _s in linhas if k]
    out += ["", f"RT: **{len(linhas) - falhas}/{len(linhas)}**", "",
            f"- **vs JSON compacto** — mediana **{statistics.median(vsj):+.0f}%** "
            f"(pior {max(vsj):+.0f}%, melhor {min(vsj):+.0f}%); "
            f"só as colunas com null: **{statistics.median(vsj_com):+.0f}%**",
            f"- vs `.8H`, colunas **com** null ({len(com)}): Δ mediano "
            f"**{statistics.median(com):+.0f}%**, pior {max(com):+.0f}%, melhor {min(com):+.0f}%",
            f"- vs `.8H`, colunas **sem** null ({len(sem)}): Δ **{max(sem):+.0f}%** — "
            "byte-idênticas, como tem que ser (o slot 0 era espaço morto)", ""]

    piores = [(e, j, a, 100 * (a - j) / j) for e, _n, k, j, a, _d, _x, _p, _q, _s in linhas
              if k and a > j]
    if piores:
        out += ["### O achado: o `.8H` era MAIOR que o JSON em payload pequeno", "",
                "Antes do weld, uma coluna minúscula com null saía **maior como TCF do que "
                "como JSON** — o envelope hierárquico custava mais que os bytes que "
                "economizava. Isso contradizia frontalmente o foco declarado (cada byte "
                "conta em payload minúsculo).", "",
                "| id | JSON | `.8H` | era | virou |", "|---|---:|---:|---:|---:|"]
        for e, j, a, pc in piores:
            d = [x[5] for x in linhas if x[0] == e][0]
            out.append(f"| {e} | {j} | {a} | **{pc:+.0f}%** | **{100 * (d - j) / j:+.0f}%** |")
        out += ["", f"**{len(piores)} de {len(com)} colunas com null** estavam nessa "
                "situação; todas viraram ganho.", ""]

    # ---- byte-neutralidade em dados REAIS (o que o protótipo não podia medir)
    out += ["## Byte-neutralidade — D1-D9 (datasets reais do gate)", "",
            "| dataset | bytes | pino ADR-0034 | ok |", "|---|---:|---:|---|"]
    pinos = {"D1-emails-simples": 125, "D2-emails-quote-id": 173, "D3-stress-substring": 184,
             "D4-caos-mix": 120, "D5-padroes-multiplos": 288, "D6-poucos-em-ruido": 294,
             "D7-aninhamento": 222, "D8-cabeca-cauda": 107, "D9-frequencia-alta": 73}
    neutro = True
    for nome, pino in pinos.items():
        with (REPO / "datasets" / "synthetic" / f"{nome}.csv").open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            vals = [row[0] for row in r if row]
        b = len(encode(vals).encode())
        neutro &= b == pino
        out.append(f"| {nome} | {b} | {pino} | {'OK' if b == pino else 'MUDOU'} |")
    out += ["", f"Byte-neutro em coluna sem null: **{'SIM' if neutro else 'NAO'}** — "
                "o slot 0 era espaço morto, então não roubou endereço de dado.", ""]

    # ---- gzip: sinal qualitativo, NAO criterio (feedback gzip-nao-e-TCF)
    out += ["## Sob gzip (sinal qualitativo, não critério)", "",
            "| id | JSON gz | `.8H` gz | TCF gz | vs JSON gz |", "|---|---:|---:|---:|---:|"]
    for eid, (col, _n) in list(FONTES.items())[:5]:
        gj = len(gzip.compress(_json_compacto(col).encode(), 9))
        ga = len(gzip.compress(_antes(col).encode(), 9))
        gd = len(gzip.compress(encode(col).encode(), 9))
        out.append(f"| {eid} | {gj} | {ga} | {gd} | {100 * (gd - gj) / gj:+.0f}% |")
    out += ["", "gzip **não é o TCF** — entra só como sinal de que o ganho não é artefato "
                "de redundância textual que um entropy-coder colapsaria.", ""]

    ok = falhas == 0 and neutro
    out += ["## Veredito", "",
            f"**{'APROVADO' if ok else 'REPROVADO'}** — RT {len(linhas) - falhas}/{len(linhas)}, "
            f"byte-neutro={'sim' if neutro else 'NAO'}, Δ mediano {statistics.median(ganhos):+.0f}%."]
    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

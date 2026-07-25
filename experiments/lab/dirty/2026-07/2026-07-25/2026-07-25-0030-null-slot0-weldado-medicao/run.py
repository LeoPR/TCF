"""Lab 2026-07-25-0030 — medição do weld: null no slot 0, rota flat aberta.

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


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas, ganhos = [], 0, []
    for eid, (col, nota) in FONTES.items():
        _w(RAIZ / "inputs" / f"{eid}-fonte.json", {"nota": nota, "dados": col})
        _w(RAIZ / "intermediates" / f"{eid}-dataset-consumido.json", col)

        wa, wd = _antes(col), encode(col)
        rt = decode(wd) == col
        falhas += not rt
        (RAIZ / "outputs" / f"{eid}-antes-8H.tcf").write_text(wa, encoding="utf-8")
        (RAIZ / "outputs" / f"{eid}-wire.tcf").write_text(wd, encoding="utf-8")
        _w(RAIZ / "outputs" / f"{eid}-dataset.roundtrip.json", decode(wd))

        a, d = len(wa.encode()), len(wd.encode())
        pct = 100 * (d - a) / a
        ganhos.append(pct)
        linhas.append((eid, len(col), sum(v is None for v in col), a, d, d - a, pct,
                       "OK" if rt else "FALHOU"))

    out = ["# Resultado — null no slot 0 SOLDADO (2026-07-25-0030)", "",
           "`antes` = rota `.8H` (o que a coluna com null produzia até o weld) · "
           "`depois` = `encode()` atual, medido no produto REAL.", "",
           "| id | n | nulls | antes `.8H` | depois | Δ | Δ% | RT |",
           "|---|---:|---:|---:|---:|---:|---:|---|"]
    out += [f"| {e} | {n} | {k} | {a} | {d} | {x:+} | {p:+.0f}% | {s} |"
            for e, n, k, a, d, x, p, s in linhas]
    com = [p for _e, _n, k, _a, _d, _x, p, _s in linhas if k]
    sem = [p for _e, _n, k, _a, _d, _x, p, _s in linhas if not k]
    out += ["", f"RT: **{len(linhas) - falhas}/{len(linhas)}**", "",
            f"- colunas **com** null ({len(com)}): Δ mediano **{statistics.median(com):+.0f}%**, "
            f"pior caso {max(com):+.0f}%, melhor {min(com):+.0f}%",
            f"- colunas **sem** null ({len(sem)}): Δ **{max(sem):+.0f}%** — byte-idênticas, "
            "como tem que ser (o slot 0 era espaço morto)", ""]

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
            "| id | antes gz | depois gz | Δ% |", "|---|---:|---:|---:|"]
    for eid, (col, _n) in list(FONTES.items())[:5]:
        ga = len(gzip.compress(_antes(col).encode(), 9))
        gd = len(gzip.compress(encode(col).encode(), 9))
        out.append(f"| {eid} | {ga} | {gd} | {100 * (gd - ga) / ga:+.0f}% |")
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

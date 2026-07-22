"""L3 — o trade da multiplicidade: EXPLÍCITA (independência/paralelismo) vs
DEDUZIDA (menos bytes, colunas se conversam). Mede a hipótese do owner e a mitigação.

Owner (2026-07-14): no L3 não há troca perfeita (cobertor curto). Mesmo a hierarquia
dizendo que o pai NÃO precisa expandir, o NÚMERO (multiplicidade) pode ser necessário:
- EXPLÍCITO (o `#count` do weld, ou o `*N|` como marcação): cada bloco se basta →
  assíncrono máximo / paralelismo total / estrutura separável do dado (lazy).
- DEDUZIDO (parent repete + RLE; a multiplicidade sai do run do pai): menos bytes,
  MAS a reconstrução tem que LER uma coluna de dado (o pai) → as colunas se conversam
  → menos paralelismo/independência.

Mede: (1) bytes das duas formas variando a LARGURA do registro; (2) caracteriza a
DEPENDÊNCIA (o que a montagem precisa ler); (3) a mitigação. Sem tocar src/tcf além
de USAR o encode_hierarchical weldado (a forma EXPLÍCITA) read-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from tcf import decode, encode, encode_hierarchical  # noqa: E402


# ---------- forma EXPLÍCITA = o weld (colunas-pai à granularidade + #count 1×) ----------
def explicit_bytes(records: list) -> int:
    return len(encode_hierarchical(records).encode("utf-8"))


# ---------- forma DEDUZIDA = tabelão (pai REPETE por filho; multiplicidade no RLE do pai;
#            sem coluna de count) — a reconstrução deduz agrupando o run do pai ----------
def deduced_bytes(records: list) -> int:
    """Uma raiz com UM array de escalares (telefones). Tabelão: pai repete, RLE colapsa.
    Colunas via encode() por-coluna (mesmo motor). SEM #count — a multiplicidade sai
    do run do pai (a reconstrução TEM que ler o(s) pai(s) e agrupar = conversa)."""
    parents = [k for k in records[0] if not isinstance(records[0][k], list)]
    arr = next(k for k in records[0] if isinstance(records[0][k], list))
    cols = {p: [] for p in parents}
    cols[arr] = []
    for rec in records:
        for e in rec[arr]:
            for p in parents:
                cols[p].append(str(rec[p]))   # PAI REPETE por filho
            cols[arr].append(str(e))
    return sum(len(encode(cols[c]).encode("utf-8")) for c in cols)


def count_only_bytes(records: list) -> int:
    """Só a coluna de count (o 'imposto de independência' isolado, já seq-RLE'd)."""
    arr = next(k for k in records[0] if isinstance(records[0][k], list))
    counts = [str(len(rec[arr])) for rec in records]
    return len(encode(counts).encode("utf-8"))


# ---------- geradores: registro ESTREITO (1 pai) .. LARGO (K pais) ----------
def make(n_records: int, k_parents: int, seed_mult=(2, 1, 3)):
    recs = []
    for i in range(n_records):
        rec = {f"campo{j}": f"valor-{j}-do-registro-{i:03d}" for j in range(k_parents)}
        m = seed_mult[i % len(seed_mult)]
        rec["telefones"] = [f"+55 11 9{i:04d}-{t:04d}" for t in range(m)]
        recs.append(rec)
    return recs


def main():
    out = ["L3 — multiplicidade EXPLÍCITA (independência) vs DEDUZIDA (menos bytes, conversa)",
           "", "Bytes por LARGURA do registro (nº de campos-pai), 6 registros:", "",
           f"{'K pais':>7} | {'EXPLÍCITA(#count)':>17} | {'DEDUZIDA(tabelão)':>17} | "
           f"{'Δ':>6} | {'só o count':>11} | vence"]
    out.append("-" * 82)
    rows = []
    for k in (1, 2, 4, 8, 16):
        recs = make(6, k)
        e = explicit_bytes(recs)
        d = deduced_bytes(recs)
        c = count_only_bytes(recs)
        assert decode(encode_hierarchical(recs)) == recs  # RT da forma explícita (weld)
        vence = "EXPLÍCITA (Pareto: -bytes E +independência)" if e <= d else "deduzida (só -bytes)"
        out.append(f"{k:>7} | {e:>17} | {d:>17} | {e-d:>+6} | {c:>11} | {vence}")
        rows.append((k, e, d, c))
    out += ["",
            "CARACTERIZAÇÃO DA DEPENDÊNCIA (o que a MONTAGEM precisa ler):",
            "- EXPLÍCITA: lê 1 coluna de controle DEDICADA e minúscula (#count). As colunas de",
            "  DADO (pai, filhos) decodificam INDEPENDENTES → paralelismo total; e dá pra ler a",
            "  ESTRUTURA (quantos filhos por registro) SEM materializar o dado (lazy-friendly,",
            "  como o view()).",
            "- DEDUZIDA: a montagem tem que DECODIFICAR a coluna de DADO do pai e analisar seus",
            "  runs pra achar as fronteiras → a estrutura fica ENTRELAÇADA com o dado do pai; o",
            "  bloco-filho DEPENDE do bloco-pai → menos assíncrono; não dá pra ler estrutura sem dado.",
            "",
            "MITIGAÇÃO / VEREDITO:",
            "- O 'imposto de independência' (a coluna de count) é MINÚSCULO e seq-RLE'd (col. 'só o",
            "  count' acima) — não é o gargalo.",
            "- A hipótese 'independência custa bytes' é VERDADE só p/ registro ESTREITO (K=1): aí a",
            "  deduzida economiza o count. Para registro LARGO (K>=2, o comum em transmissão —",
            "  cadastro é largo), a EXPLÍCITA é PARETO-melhor: MENOS bytes E MAIS independência",
            "  (a deduzida paga o `*N|` repetido em CADA coluna-pai; a explícita paga 1 count só).",
            "- Logo o default do weld (#count EXPLÍCITO) é o certo: independência quase-grátis no",
            "  caso comum. O 'cobertor curto' vira um PARÂMETRO só p/ o nicho estreito+min-bytes.",
            "",
            "OTIMIZAÇÃO (deixar pro fim, como o owner pediu): expor um knob de L3",
            "  `multiplicity='explicit'|'deduced'` (independência vs -bytes no nicho estreito).",
            "  min() por documento também é candidato (como o FLOOR). NÃO implementar agora."]
    (Path(__file__).resolve().parent / "outputs").mkdir(exist_ok=True)
    (Path(__file__).resolve().parent / "outputs" / "01-resultado.txt").write_bytes(
        ("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))


if __name__ == "__main__":
    main()

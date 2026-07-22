"""run.py — protótipo bN como 5º candidato do min() por-coluna (ver as possibilidades).

(1) ilustrativo: container misto (bool/enum/high-card) — mostra a linha de header com marcadores + RT.
(2) real: colunas adult (k=2..alto) — o min() escolhe por coluna; qual modo vence; RT.
(3) gate terminal: container com bN vs sem bN, pré e pós brotli — mostra que bN só ajuda TERMINAL.

`python run.py` regenera artifacts/. Dados: Z:/tcf-data/interim/adult-census.db. Não toca src/tcf.
"""
from __future__ import annotations
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import bn_codec as C                                     # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
DB = Path("Z:/tcf-data/interim/adult-census.db")


def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def load(cols):
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    out = {c: [str(r[0]) for r in con.execute(f'SELECT "{c}" FROM adult').fetchall()] for c in cols}
    con.close()
    return out


def thread_ilustrativo():
    cols = {
        "ativo":  ["true", "false", "true", "true", "false", "false", "true", "false"],   # k=2 -> b (1 bit)
        "status": ["A", "B", "C", "A", "B", "A", "C", "B"],                               # k=3 -> b2 (2 bits)
        "id":     [f"u{i:03d}" for i in range(8)],                                          # k=8 distinto -> high p/ N=8
    }
    blob, chosen = C.container_encode(cols)
    back = C.container_decode(blob)
    ok = back == {k: [str(x) for x in v] for k, v in cols.items()}
    head = blob.split(b"\n", 1)[0].decode()
    L = ["# (1) ILUSTRATIVO — container misto: o min() escolhe o modo por coluna", "",
         "colunas:", *[f"  {k}: {v}" for k, v in cols.items()], "",
         f"HEADER (linha 1): {head}",
         "  legenda de prefixo: (nenhum)=tcf/HCC · '!'=raw · '#'=bN",
         "", "modo escolhido por coluna (prefixo, bytes do body):",
         *[f"  {k:8s} -> {m[0]:4s}  {m[1]:4d}B" for k, m in chosen.items()],
         "", f"RT container: {'OK' if ok else 'FALHA'}",
         "", "LEITURA: cada coluna carrega seu próprio marcador de modo (char-prefixo no par do meta), igual",
         "ao mecanismo `!`/`@`/`%` do multi-col real. bN ('#') aparece só onde vence o min()."]
    w("01-ilustrativo.txt", "\n".join(L) + "\n")
    return head, ok


def thread_real():
    cols = load(["sex", "race", "education", "age", "fnlwgt"])   # k = 2, 5, 16, ~70, ~28k
    blob, chosen = C.container_encode(cols)
    back = C.container_decode(blob)
    ok = back == {k: v for k, v in cols.items()}
    L = ["# (2) REAL — adult: o min() por coluna (tcf/raw/bN) + RT", "",
         "| coluna | N | k (distintos) | modo vencedor | body bytes |", "|---|---|---|---|---|"]
    for name in cols:
        k = len(set(cols[name]))
        m = chosen[name]
        L.append(f"| {name} | {len(cols[name])} | {k} | **{m[0]}** | {m[1]} |")
    L += ["", f"container total: {len(blob)}B · RT: {'OK' if ok else 'FALHA'}",
          "", "LEITURA: bN ('#') vence nas de baixa-card (sex/race/education); em high-card (fnlwgt, k>256) bN",
          "nem se oferece (bn_encode->None) e o min() fica com tcf/raw. age (k~70 -> b8, 1 byte/linha) mostra a",
          "fronteira: bN ainda se aplica mas o ganho é menor. Heterogêneo por coluna — como o multi-col real."]
    w("02-real-min-por-coluna.txt", "\n".join(L) + "\n")
    return chosen, ok


def thread_gate_brotli():
    try:
        import brotli
    except ImportError:
        w("03-gate-terminal-brotli.txt", "brotli indisponível\n"); return
    cols = load(["sex", "race", "education"])
    com_bn, _ = C.container_encode(cols, allow_bn=True)
    sem_bn, _ = C.container_encode(cols, allow_bn=False)
    ok = C.container_decode(com_bn) == cols and C.container_decode(sem_bn) == cols

    def brz(b): return len(brotli.compress(b, quality=11))
    L = ["# (3) GATE TERMINAL — bN só ajuda se NÃO há brotli a jusante", "",
         f"container COM bN : {len(com_bn):7d}B  -> brotli-q11: {brz(com_bn):7d}B",
         f"container SEM bN : {len(sem_bn):7d}B  -> brotli-q11: {brz(sem_bn):7d}B",
         f"RT (ambos): {'OK' if ok else 'FALHA'}",
         "",
         f"  ganho de oferecer bN, PRÉ-brotli : {len(sem_bn)/len(com_bn):.2f}x",
         f"  ganho de oferecer bN, PÓS-brotli : {brz(sem_bn)/brz(com_bn):.2f}x",
         "",
         "LEITURA: oferecer bN encolhe MUITO pré-brotli, mas pós-brotli o ganho ~some (o brotli acha a mesma",
         "entropia — bN é irmão bit-packed do dict). Confirma H-TYPE-03: o candidato bN deve ser GATED por um",
         "flag de 'saída terminal' (opt-in), pra não ser escolhido quando há re-compressão a jusante.",
         "",
         "CAVEAT: este min() tem só {tcf, raw, bN} — NÃO o V2-B/dict real (fallback=True do src/tcf), irmão",
         "próximo do bN. Logo o 'SEM bN' aqui é mais fraco que produção e os ganhos SUPERESTIMAM. A margem",
         "real bN-vs-V2-B já medida: ~8/w pré-brotli, ~1.0-1.3x pós (colapsa). Aqui provamos o MECANISMO."]
    w("03-gate-terminal-brotli.txt", "\n".join(L) + "\n")
    return ok


def main():
    head, ok1 = thread_ilustrativo()
    chosen, ok2 = thread_real()
    ok3 = thread_gate_brotli()

    R = ["# Protótipo bN como 5º candidato do min() [resumo]", "",
         "## Encaixa? SIM — o par _bN_encode/_decode_bN roda como candidato do min() por-coluna",
         "- marcador = char-PREFIXO `#` no par do meta (ao lado de `!`/`@`/`%`); decoder ramifica por prefixo.",
         "- bN codifica DOMÍNIO + índices (irmão do dict), body auto-descritivo [w][domlen][dom][packed].",
         "- min(tcf, raw, bN) por coluna escolhe o menor; bN só aparece onde vence; k>256 -> não se oferece.",
         "",
         f"## Ilustrativo: header = {head}",
         "## Real (adult): modo vencedor por coluna",
         *[f"  {k:10s} -> {m[0]}" for k, m in chosen.items()],
         "",
         "## RT container: " + ("OK" if (ok1 and ok2 and ok3 is not False) else "FALHA")
         + ("" if ok3 is not None else "  (thread brotli pulado: módulo ausente neste python)"),
         "",
         "## Gate: bN só ajuda TERMINAL (pós-brotli o ganho ~some) -> candidato opt-in, não default.",
         "   CAVEAT: o min() aqui tem só {tcf,raw,bN}, não o V2-B/dict real -> ganhos SUPERESTIMAM;",
         "   margem real bN-vs-V2-B (já medida): ~8/w pré-brotli, ~1.0-1.3x pós. Aqui: só o MECANISMO.",
         "",
         "## Veredito (ver as possibilidades): a forma ENCAIXA no contrato do header sem mudar a arquitetura",
         "(char-prefixo + min() + decode ramificado já existem). Faltam, p/ produção: alocar o char, o ramo no",
         "min() real (multi/core.py), o par enc/dec byte-idêntico, e o gate terminal. Tudo gated por H-TYPE-02/03",
         "(N<5 fontes + colapso sob brotli) — protótipo, NÃO welding."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:28s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()

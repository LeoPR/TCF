"""Data: os ALVOS de transformação × como a GRAFIA é declarada. `python run.py`

Só **data** (sem hora) — recorte do owner.

## Parte 1 — os alvos: qual forma render mais, e em que regime

Sete alvos, cada um com a inversa, RT conferido. A pergunta não é "qual é o melhor" — o lab
anterior já mostrou que a resposta **inverte** entre regimes. A pergunta é **quantos alvos
são necessários** pra cobrir os regimes sem deixar dinheiro na mesa.

## Parte 2 — declarar a grafia: as três opções, e o que custam

    H1  spec nomeado no header      `#TCF.8 :data-iso`        custo fixo, medido
    H2  template no 1º registro     `%Y-%m-%d` como valor 0   custo = len(template)
    H3  inferir do 1º registro      nada no wire              custo 0 — **se desambiguar**

O H3 é o único de graça, e o lab mede **com que frequência ele funciona** — porque ele só
serve quando o primeiro valor tem uma leitura única.

> Nota de projeto: adivinhar a grafia **não substitui declará-la**. Se o encoder escolhe e
> não registra a escolha, o decode não tem como inverter. O sniff é front-end do H1/H2, não
> uma quarta opção.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from alvos import ALFA, ALVOS, GRAFIAS, LARG_DENSO, infere_do_primeiro  # noqa: E402

from tcf import decode, encode  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

for x in ("inputs", "intermediates", "outputs"):
    (RAIZ / x).mkdir(exist_ok=True)

BASE = _dt.date(2026, 1, 1)
N = 600


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


def _lcg(n, mod, semente=4242):
    x, out = semente, []
    for _ in range(n):
        x = (1103515245 * x + 12345) % (1 << 31)
        out.append(x % mod)
    return out


def higiene_json(vals) -> dict:
    """O input sobrevive a um round-trip por `json.dumps`/`json.loads`?

    E' a pergunta "este dado e' json-lib like, ou e' estrutura mais ampla que o JSON?".
    Se sobrevive IDENTICO, qualquer pipeline que passe por JSON entrega a mesma coisa —
    o lab nao esta medindo um artefato de serializacao.
    """
    volta = json.loads(json.dumps(vals))
    igual = volta == vals and [type(a) is type(b) for a, b in zip(volta, vals)].count(False) == 0
    return {"sobrevive_json": igual,
            "classe": "json-lib-like" if igual else "fora-do-json",
            "como_foi_testado": "json.loads(json.dumps(x)) == x, com tipo"}


def trilha(vals) -> dict:
    """De onde o dado passou DENTRO do codec — lido da telemetria real (`SideOutputs`).

    Nao e' narrativa: cada campo abaixo e' produzido pelo proprio encode.
    """
    so = SideOutputs()
    w = encode(vals, side_outputs=so)
    cf = so.column_features
    runs = so.seq_rle_runs or []
    return {
        "wire_bytes": len(w.encode()),
        "1_entrada": {
            "n_linhas": getattr(cf, "n_rows", None),
            "n_unicas": getattr(cf, "n_unicas", None),
            "cardinalidade": getattr(cf, "cardinality", None),
            "comprimento_medio": getattr(cf, "avg_len", None),
            "parece_numerico": getattr(cf, "is_numeric", None),
        },
        "2_pre_passe": {
            "cadencia_detectada": so.cadence_detected,
            "regra_que_bateu": (so.cadence_info or {}).get("rule_hit"),
            "min_len_escolhido": so.min_len,
        },
        "3_obat_tokenizer": {
            "usou_hint_de_forma": so.obat_used_hint,
            "log": (so.obat_log or "").strip().splitlines(),
        },
        "4_hcc_composicional": {
            "seq_rle_disparou": bool(runs),
            "n_corridas": len(runs),
            "corridas": [{"linhas": f"{r.get('start_line')}..{r.get('end_line')}",
                          "count": r.get("count"), "delta_uniforme": r.get("uniform_delta"),
                          "template": r.get("template")} for r in runs[:6]],
            "corridas_omitidas": max(0, len(runs) - 6),
        },
        "5_saida": {"body_bytes": so.body_bytes, "primeira_linha": w.split("\n")[0]},
    }


REGIMES = {
    "diario": [BASE + _dt.timedelta(days=i) for i in range(N)],
    "semanal": [BASE + _dt.timedelta(days=7 * i) for i in range(N)],
    "mensal": [BASE + _dt.timedelta(days=30 * i) for i in range(N)],
    "agrupado": [BASE + _dt.timedelta(days=i // 20) for i in range(N)],
    "repetido-k12": [BASE + _dt.timedelta(days=30 * (i % 12)) for i in range(N)],
    "espalhado": [BASE + _dt.timedelta(days=x) for x in _lcg(N, 3650)],
    "espalhado-ord": sorted(BASE + _dt.timedelta(days=x) for x in _lcg(N, 3650)),
    "decada-espalhada": [BASE + _dt.timedelta(days=x) for x in _lcg(N, 36500, 7)],
}


#: Regimes cujos artefatos vão pra disco. Os outros só entram nas tabelas — gravar 56×3
#: arquivos não ajuda ninguém a se orientar.
GRAVA = ("diario", "espalhado")


def parte1():
    linhas, falhas = [], []
    for reg, datas in REGIMES.items():
        iso = [d.isoformat() for d in datas]
        hig = higiene_json(iso)

        # ── INPUT: o dado de partida, com a HIGIENE declarada no arquivo E no nome ──
        _escreve(RAIZ / "inputs" / f"regime-{reg}--{hig['classe']}.input.json",
                 json.dumps({
                     "_o_que_e": f"coluna de {len(iso)} datas, regime '{reg}', grafia ISO",
                     "_higiene": hig,
                     "_por_que_este_regime": {
                         "diario": "passo +1 — o caso mais regular",
                         "semanal": "passo +7", "mensal": "passo +30 (o passo mais irregular em texto)",
                         "agrupado": "blocos de 20 iguais — o RLE simples domina",
                         "repetido-k12": "12 datas cicladas — baixa cardinalidade",
                         "espalhado": "10 anos sem ordem — nada a explorar",
                         "espalhado-ord": "o mesmo, ordenado — deltas pequenos",
                         "decada-espalhada": "100 anos sem ordem — domínio largo",
                     }.get(reg, ""),
                     "amostra_12_primeiros": iso[:12],
                     "n_total": len(iso),
                 }, ensure_ascii=False, indent=1) + "\n")

        for alvo, (para, de, porque) in ALVOS.items():
            vals = para(datas)
            w = encode(vals)
            if decode(w) != vals:
                falhas.append(f"{reg}/{alvo}: RT do wire quebrou")
                continue
            volta = de(decode(w))                       # a inversa do ALVO
            if volta != datas:
                falhas.append(f"{reg}/{alvo}: a inversa do alvo não devolve as datas")
                continue
            linhas.append({"regime": reg, "alvo": alvo, "porque": porque,
                           "bytes": len(w.encode()),
                           "chars_por_valor": round(len(vals[0]), 1)})

            if reg not in GRAVA:
                continue
            base = f"{reg}--{alvo}"
            # ── OUTPUT: o fio, e o round-trip pra inspecionar ────────────────
            _escreve(RAIZ / "outputs" / f"{base}.tcf", w)
            _escreve(RAIZ / "outputs" / f"{base}.roundtrip.json", json.dumps({
                "_o_que_e": f"round-trip de '{base}' — a CONTRAPROVA do lab",
                "_como_ler": [
                    "1. o TCF só vê `apos_o_alvo`: é isso que virou o .tcf",
                    "2. `decode_do_wire` tem de ser IGUAL a `apos_o_alvo` (RT do formato)",
                    "3. `depois_da_inversa` tem de ser IGUAL a `entrada_iso` (RT do alvo)",
                    "os dois níveis fecham = o alvo é reversível E o wire é fiel",
                ],
                "alvo": alvo, "o_que_o_alvo_faz": porque,
                "confere": {
                    "rt_do_formato": decode(w) == vals,
                    "rt_do_alvo": [d.isoformat() for d in volta] == iso,
                },
                "entrada_iso": iso[:8],
                "apos_o_alvo": vals[:8],
                "decode_do_wire": decode(w)[:8],
                "depois_da_inversa": [d.isoformat() for d in volta][:8],
                "_amostra": "8 primeiros de %d" % len(iso),
            }, ensure_ascii=False, indent=1) + "\n")
            # ── INTERMEDIATE: por onde o dado passou DENTRO do codec ─────────
            _escreve(RAIZ / "intermediates" / f"{base}.trilha.json", json.dumps({
                "_o_que_e": f"por onde '{base}' passou dentro do codec — telemetria REAL "
                            "(`SideOutputs`), não narrativa",
                "_ordem": "1 entrada → 2 pré-passe → 3 OBAT → 4 HCC/seq-RLE → 5 saída",
                **trilha(vals),
            }, ensure_ascii=False, indent=1, default=str) + "\n")
    return linhas, falhas


def parte2():
    """Quanto custa declarar a grafia, pelas três vias."""
    # H1: o header self-describing. Medido contra o mesmo wire sem nature.
    h1 = len("#TCF.8 :data-iso") - len("#TCF.8")
    # H2: o template como primeiro valor da coluna.
    h2 = {g: len(f) + 1 for g, f in GRAFIAS.items()}       # +1 do LF
    # H3: inferir do primeiro valor — funciona? mede-se sobre TODAS as datas do ano.
    amostra = [BASE + _dt.timedelta(days=i) for i in range(366)]
    stats = {}
    for g, fmt in GRAFIAS.items():
        unico = amb = 0
        exemplos_amb = []
        for d in amostra:
            v = d.strftime(fmt)
            cands = infere_do_primeiro(v)
            if len(cands) == 1:
                unico += 1
            else:
                amb += 1
                if len(exemplos_amb) < 3:
                    exemplos_amb.append((v, cands))
        stats[g] = {"total": len(amostra), "desambigua": unico,
                    "taxa": round(100 * unico / len(amostra), 1),
                    "exemplos_ambiguos": exemplos_amb}
    return h1, h2, stats


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas = parte1()
    h1, h2, stats = parte2()

    _escreve(RAIZ / "intermediates" / "medicoes.json",
             json.dumps({"alvos": linhas, "declaracao": {"h1_header": h1, "h2_template": h2,
                                                         "h3_inferencia": stats}},
                        ensure_ascii=False, indent=2, default=str) + "\n")

    L = ["# Data — alvos de transformação × declaração da grafia", "",
         f"`n={N}` por regime. RT conferido em dois níveis: o wire, e a **inversa do alvo** "
         "(as datas voltam iguais).", "",
         "## Parte 1 — os alvos", "",
         "Bytes por regime. **negrito = melhor do regime.**", ""]

    alvos = list(ALVOS)
    L += ["| regime | " + " | ".join(f"`{a}`" for a in alvos) + " |",
          "|---|" + "---:|" * len(alvos)]
    vencedores = {}
    for reg in REGIMES:
        row = {r["alvo"]: r["bytes"] for r in linhas if r["regime"] == reg}
        if not row:
            continue
        melhor = min(row, key=row.get)
        vencedores[reg] = melhor
        cels = [f"**{row[a]}**" if a == melhor else str(row.get(a, "—")) for a in alvos]
        L.append(f"| `{reg}` | " + " | ".join(cels) + " |")

    L += ["", "### Quem vence, e quantos alvos são necessários", "",
          "| regime | vence | ganho sobre `iso` |", "|---|---|---:|"]
    for reg, v in vencedores.items():
        row = {r["alvo"]: r["bytes"] for r in linhas if r["regime"] == reg}
        L.append(f"| `{reg}` | **{v}** | {row['iso'] / row[v]:.1f}× |")
    distintos = sorted(set(vencedores.values()))
    L += ["", f"**{len(distintos)} alvos distintos vencem em algum regime**: "
          + ", ".join(f"`{a}`" for a in distintos) + ".", ""]

    # ── Parte 1b: o mesmo quadro PAGANDO a declaracao ────────────────────────
    # `iso` nao transforma nada, entao nao ha' grafia a declarar: custo 0.
    # `delta-dias` guarda o 1o valor VERBATIM no wire (conferido:
    # `#TCF.8!!\n2026-01-01\n*599|1`), entao a grafia viaja de graca — o proprio
    # alvo paga o H3. Os demais destroem a grafia e precisam do header (H1).
    DECL = {a: (0 if a in ("iso", "delta-dias") else h1) for a in alvos}
    L += ["", "### O mesmo quadro, PAGANDO a declaração", "",
          "`iso` não transforma nada (nada a declarar). `delta-dias` guarda o 1º valor "
          "**verbatim**, então a grafia viaja de graça. Os outros destroem a grafia e "
          f"pagam os **{h1} B** do header.", "",
          "| regime | " + " | ".join(f"`{a}`" for a in alvos) + " |",
          "|---|" + "---:|" * len(alvos)]
    venc2 = {}
    for reg in REGIMES:
        row = {r["alvo"]: r["bytes"] + DECL[r["alvo"]] for r in linhas if r["regime"] == reg}
        if not row:
            continue
        melhor = min(row, key=row.get)
        venc2[reg] = melhor
        L.append(f"| `{reg}` | " + " | ".join(
            f"**{row[a]}**" if a == melhor else str(row.get(a, "—")) for a in alvos) + " |")
    from collections import Counter

    L += ["", "| vence | em quantos regimes |", "|---|---:|"]
    for a, c in Counter(venc2.values()).most_common():
        L.append(f"| `{a}` | {c} |")
    L += ["", "**A declaração inverte o quadro:**", "",
          "| regime | sem declarar | pagando |", "|---|---|---|"]
    for reg in REGIMES:
        if reg in vencedores:
            mudou = " ←" if vencedores[reg] != venc2[reg] else ""
            L.append(f"| `{reg}` | `{vencedores[reg]}` | `{venc2[reg]}`{mudou} |")
    L.append("")

    L += ["## Parte 2 — declarar a grafia", "",
          f"- **H1 — spec no header** (`#TCF.8 :data-iso`): **{h1} B** fixos, uma vez por coluna.",
          f"- **H2 — template no 1º registro**: {min(h2.values())}–{max(h2.values())} B "
          "(o `%Y-%m-%d` e afins), uma vez por coluna — e ocupa uma linha do corpo.",
          "- **H3 — inferir do 1º registro**: **0 B**, mas só funciona se o primeiro valor "
          "tiver leitura única. Medido abaixo, sobre as 366 datas de um ano:", "",
          "| grafia | 1º valor desambigua | taxa | exemplo ambíguo |", "|---|---:|---:|---|"]
    for g, s in stats.items():
        ex = s["exemplos_ambiguos"]
        amostra_ex = f"`{ex[0][0]}` → {ex[0][1]}" if ex else "—"
        L.append(f"| `{g}` | {s['desambigua']}/{s['total']} | **{s['taxa']}%** | {amostra_ex} |")

    L += ["", "---", "", f"**falhas de RT: {len(falhas)}**"]
    if falhas:
        L += ["", *(f"- {f}" for f in falhas)]
    L += ["", f"*(alfabeto denso: {len(ALFA)} chars, largura {LARG_DENSO})*"]
    _escreve(RAIZ / "outputs" / "medicoes.md", "\n".join(L) + "\n")

    print(f"{len(linhas)} medições · {len(falhas)} falhas · "
          f"{len(distintos)} alvos vencem em algum regime")
    for f in falhas:
        print("  FALHA:", f)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())

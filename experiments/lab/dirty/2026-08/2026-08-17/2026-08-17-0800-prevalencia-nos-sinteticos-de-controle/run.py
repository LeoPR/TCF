"""PREVALÊNCIA e GANHO RELATIVO nos sintéticos de controle do `.8H`.

O QUE ISTO É — E O QUE NÃO É
----------------------------
NÃO é julgamento. Os 12 casos são **enviesados de propósito** — o próprio gerador
declara: *"cada um isolando UM mecanismo do fluxo… Propósito: observar a NAVEGAÇÃO
do fluxo, não ganhar bytes."* Medir "quanto o TCF ganha" aqui não significaria nada.

É um **levantamento**: onde os bytes moram, quais mecanismos disparam e com que
frequência, e quanto CADA achado em aberto vale sobre este conjunto. Serve para
decidir o que levar ao lab clean com volume — onde aí sim a coleta virá pelo
**Shaper** (`src/shaper/`, estratificação honesta), não direto do sqlite.

FONTE ÚNICA
-----------
`tests/fixtures/control_synthetics_h.py` — o MESMO gerador que alimenta
`tests/test_hierarchical_control_synthetics.py` (12 pins de navegação). Nada de
sintético novo: se já existe conjunto de controle pinado, inventar outro só cria
uma segunda régua que diverge.

AS TRÊS LENTES
--------------
  A. PREVALÊNCIA  — quais mecanismos disparam, em quantos casos, ocupando quanto
  B. GANHO RELATIVO dos achados em aberto, sobre ESTE conjunto:
       B1. candidato único   (lab 0400) — o que raw/dict/split recuperariam
       B2. folha tipada      (lab 0500) — o que o denso recuperaria (bool/número)
       B3. contagem singleton (nota 0700) — níveis cuja contagem é constante-1
  C. RÉGUA EXTERNA — JSON compacto, só como referencial de ordem de grandeza

Round-trip é o assert em todo caso (§RT). `src/tcf` INTOCADO.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

OUT = AQUI / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                          # noqa: E402
from tcf.multi.core import _fallback_safe               # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode              # noqa: E402
from tcf.multi.split import _struct_split_encode        # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE               # noqa: E402
from fixtures.control_synthetics_h import gen_cases, decompose   # noqa: E402


def B(t: str) -> int:
    return len(t.encode("utf-8"))


def _num(s: str):
    """'30' -> 30 · '9.5' -> 9.5 · resto -> None. Canonico: so' conta se o
    json.dumps do resultado devolve a MESMA grafia (senao nao e' o mesmo dado)."""
    import json as _j
    try:
        v = _j.loads(s)
    except Exception:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v if _j.dumps(v) == s else None


def min_do_M(vals: list[str]) -> tuple[int, str]:
    """`_best_of` de multi/core.py:456 — closure, reimplementado igual (lab 0400)."""
    bb, bm = encode(vals, stamp=False).encode("utf-8"), "tcf"
    if _fallback_safe(vals):
        rb = "\n".join(vals).encode("utf-8")
        if len(rb) < len(bb):
            bb, bm = rb, "raw"
    vb = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if vb is not None and len(vb) < len(bb):
        bb, bm = vb, "dict"
    sb = _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if sb is not None and len(sb) < len(bb):
        bb, bm = sb, "split"
    return len(bb), bm


def corpos_por_coluna(wire: str) -> list[tuple[str, str, int, list[str]]]:
    """(caminho, kind, bytes_do_corpo, VALORES ORIGINAIS) de cada coluna.

    CUIDADO — o erro que este código já cometeu uma vez: o corpo da folha **não é**
    a lista de valores separada por `\\n`. Ele é um wire single-col ÓRFÃO, já
    passado pelo core (OBAT/HCC/refs/RLE) — `hierarchical.py:491` chama
    `_encode_col(vals, stamp=False)`. Fatiar por `\\n` devolve TOKENS CODIFICADOS
    (`^1`, `*3|true`), não valores. Comparar candidatos sobre tokens é medir lixo.

    O certo é **decodar** o corpo: `decode(body)` recupera exatamente a lista que
    o shredder entregou ao encoder de coluna. Sintoma que denunciou o bug: `c10`
    tem 150 bools em 203 B — literal seria ~825 B.
    """
    from tcf.hierarchical import MAGIC, _parse_meta
    l1 = wire.split("\n", 1)[0]
    _schema, order, _nat = _parse_meta(l1[len(MAGIC):])
    raw = wire[len(l1) + 1:].encode("utf-8")
    saida, off = [], 0
    for path, kind, size in order:
        b = size if size is not None else len(raw) - off
        corpo = raw[off:off + b].decode("utf-8")
        off += b
        try:
            vals = decode(corpo) if corpo else []
        except Exception:
            vals = None                      # coluna que o decode de 1 col nao abre
        saida.append(("/".join(path) or "<raiz>", kind, b, vals))
    assert off == len(raw), "fatiamento nao exauriu o corpo"
    return saida


def main() -> int:
    casos = gen_cases()
    print("=" * 92)
    print(f"PREVALENCIA NOS SINTETICOS DE CONTROLE DO .8H — {len(casos)} casos")
    print("  (vies DECLARADO pelo gerador: construidos p/ OBSERVAR mecanismo, nao p/ ganhar byte)")
    print("=" * 92)

    linhas, kinds_global = [], collections.Counter()
    bytes_por_kind = collections.Counter()

    print(f"\n{'caso':22} {'total':>7} {'meta':>5} {'ctrl':>6} {'folhas':>7} "
          f"{'ctrl%':>6} {'json':>7} {'rt':>3}")
    print("-" * 92)

    for cid, (desc, mecanismo, dados) in casos.items():
        wire = encode(dados)
        rt = decode(wire) == dados
        d = decompose(wire)
        bjson = len(json.dumps(dados, separators=(",", ":"),
                               ensure_ascii=False).encode("utf-8"))

        (OUT / f"{cid}.tcf").write_text(wire, encoding="utf-8", newline="")
        (OUT / f"{cid}.roundtrip.json").write_text(
            json.dumps(decode(wire), ensure_ascii=False), encoding="utf-8", newline="")

        # --- A. prevalencia dos mecanismos (kind de cada coluna) ---
        for _p, k, b in d["cols"]:
            base = ("mask" if k == "mask" else
                    "count" if k.startswith("count") else
                    "emask" if k.startswith("emask") else
                    k)
            kinds_global[base] += 1
            bytes_por_kind[base] += b

        # --- B1/B2/B3: os tres achados em aberto, sobre ESTE caso ---
        ganho_cand = ganho_tipo = ganho_single = ganho_uniao = 0
        det = []
        for caminho, kind, b_atual, vals in corpos_por_coluna(wire):
            if vals is None:                                    # nao abriu: nao conta
                det.append((caminho, kind, "nao-decodou", b_atual, b_atual))
                continue
            if kind == "mask" or kind.startswith(("count", "emask")):
                # B3: contagem constante-1 (nivel singleton) e' dedutivel da estrutura
                if kind.startswith("count") and vals and set(vals) == {"1"}:
                    ganho_single += b_atual
                    det.append((caminho, kind, "count-constante-1", b_atual, 0))
                continue

            # B1: o min() do M sobre os valores ORIGINAIS da folha
            try:
                b_min, modo = min_do_M(vals)
            except Exception:
                b_min, modo = b_atual, "?"
            if b_min < b_atual:
                ganho_cand += b_atual - b_min
                det.append((caminho, kind, f"cand:{modo}", b_atual, b_min))
            melhor = min(b_atual, b_min)      # p/ a UNIAO (B1 e B2 se SOBREPOEM)

            # B2: folha TIPADA — o shredder stringifica (hierarchical.py:227-229);
            #     o que o encoder TIPADO nativo daria sobre os mesmos valores?
            nativo = None
            if len(vals) >= 2 and set(vals) <= {"true", "false"}:
                nativo = [v == "true" for v in vals]
            elif len(vals) >= 2 and all(_num(v) is not None for v in vals):
                nativo = [_num(v) for v in vals]
            if nativo is not None:
                # `stamp=False` NAO vale em entrada tipada (encoder.py:161 recusa).
                # Comparacao justa: wire tipado MENOS a linha de header — a tag
                # (`b`/`n`) migraria pro meta do `.8H`, entao so' o CORPO compara.
                _w = encode(nativo)
                _l1 = _w.split(chr(10), 1)[0]
                b_tipado = B(_w) - B(_l1) - 1
                if b_tipado < b_atual:
                    ganho_tipo += b_atual - b_tipado
                    rot = "denso-bool" if isinstance(nativo[0], bool) else "tipado-num"
                    det.append((caminho, kind, rot, b_atual, b_tipado))
                melhor = min(melhor, b_tipado)

            # UNIAO — B1 e B2 competem pela MESMA coluna (numa coluna bool o `dict`
            # ganha em B1 e o denso em B2). Somar os dois INFLA. A uniao pega, por
            # coluna, o melhor dos dois: e' o teto real de recuperacao.
            ganho_uniao += b_atual - melhor

        marca = "ok" if rt else "**"
        print(f"{cid:22} {d['total']:>7} {d['meta']:>5} {d['controle']:>6} "
              f"{d['folhas']:>7} {d['controle']/d['total']*100:>5.1f}% "
              f"{bjson:>7} {marca:>3}")

        linhas.append({
            "caso": cid, "descricao": desc, "mecanismo_alvo": mecanismo,
            "total": d["total"], "meta": d["meta"], "controle": d["controle"],
            "folhas": d["folhas"], "n_cols_controle": d["n_cols_controle"],
            "json_compacto": bjson, "rt": rt,
            "ganho_candidato": ganho_cand, "ganho_tipado": ganho_tipo,
            "ganho_count_singleton": ganho_single,
            "ganho_uniao": ganho_uniao,
            "detalhe": [{"col": c, "kind": k, "achado": a, "atual": x, "seria": y}
                        for c, k, a, x, y in det],
        })

    tot = {k: sum(x[k] for x in linhas) for k in
           ("total", "meta", "controle", "folhas", "json_compacto",
            "ganho_candidato", "ganho_tipado", "ganho_count_singleton",
            "ganho_uniao")}

    print("-" * 92)
    print(f"{'TOTAL':22} {tot['total']:>7} {tot['meta']:>5} {tot['controle']:>6} "
          f"{tot['folhas']:>7} {tot['controle']/tot['total']*100:>5.1f}% "
          f"{tot['json_compacto']:>7}")

    print()
    print("=" * 92)
    print("A. PREVALENCIA — quais mecanismos disparam")
    print("=" * 92)
    print(f"  {'kind':14} {'colunas':>8} {'casos':>7} {'bytes':>9} {'% do total':>11}")
    for k, n in kinds_global.most_common():
        ncasos = sum(1 for x in linhas
                     if any(dd["kind"] == k or dd["kind"].startswith(k)
                            for dd in x["detalhe"]) or True)
        ncasos = sum(1 for cid in casos
                     if any((kk == k or kk.startswith(k))
                            for _p, kk, _b in decompose(encode(casos[cid][2]))["cols"]))
        print(f"  {k:14} {n:>8} {ncasos:>7} {bytes_por_kind[k]:>9} "
              f"{bytes_por_kind[k]/tot['total']*100:>10.1f}%")

    print()
    print("=" * 92)
    print("B. GANHO RELATIVO dos achados em aberto, SOBRE ESTE CONJUNTO")
    print("   (sem julgar: o conjunto e' enviesado p/ observar mecanismo)")
    print("=" * 92)
    for rot, chave, ref in (
        ("B1 candidato unico (raw/dict/split)", "ganho_candidato", "lab 0400"),
        ("B2 folha tipada -> denso bool", "ganho_tipado", "lab 0500"),
        ("B3 count constante-1 (singleton)", "ganho_count_singleton", "nota 0700"),
        ("UNIAO (melhor dos dois POR COLUNA)", "ganho_uniao", "teto real"),
    ):
        v = tot[chave]
        ncasos = sum(1 for x in linhas if x[chave] > 0)
        print(f"  {rot:36} {v:>7} B  = {v/tot['total']*100:>5.1f}% do total  "
              f"(em {ncasos}/{len(casos)} casos)  [{ref}]")

    print()
    print("=" * 92)
    print("C. REGUA EXTERNA — so' ordem de grandeza, NAO criterio")
    print("=" * 92)
    print(f"  TCF .8H {tot['total']:>8} B   JSON compacto {tot['json_compacto']:>8} B   "
          f"-> {(1-tot['total']/tot['json_compacto'])*100:.1f}% menor")

    (AQUI / "resultado.json").write_text(
        json.dumps({
            "fonte": "tests/fixtures/control_synthetics_h.py (gerador unico, seed fixa)",
            "vies_declarado": "casos construidos p/ OBSERVAR mecanismo, nao p/ ganhar byte",
            "coleta": "sintetica — sem corpus. O clean com volume usara' o Shaper (src/shaper/).",
            "total": tot,
            "prevalencia": {k: {"colunas": n, "bytes": bytes_por_kind[k]}
                            for k, n in kinds_global.most_common()},
            "por_caso": linhas,
        }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print(f"\n-> {AQUI / 'resultado.json'}")
    falhas = sum(1 for x in linhas if not x["rt"])
    print(f"   round-trip: {len(linhas)-falhas}/{len(linhas)} OK")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

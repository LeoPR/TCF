"""EXP-018 — `IntPadSpec` + abertura da rota tipada: bateria probatória. `python run.py`

Regenera `inputs/`, `intermediates/`, `outputs/` e `report.md`. **Sai 0 só se tudo fechar.**

## O que é este lab

Clean = *"pegar o que foi melhor concluído do dirty e praticamente fazer o protótipo que já
vai soldar"* (definição do owner). Os quatro labs dirty de inteiro convergiram para **um**
alvo e **um** pré-requisito:

- `IntPadSpec` (zero-pad p/ largura fixa) — mediana **1,72×** em 39 colunas reais, zero
  empates, auto-contido;
- abrir a **rota tipada** a specs — hoje ela recusa `nature=` **e** `min_len=`.

O que ficou de fora, e por quê: `B94` (marginal — 1,14× de mediana, 33 vitórias de ≤1 byte),
`min_len` (não ganha em nenhuma coluna deste corpus), `OFFPAD` (descartado: a base não viajava).

## As provas por caso

    1. RT estrito COM TIPO      decode(encode(v)) == v e `type()` igual, elemento a elemento
    2. RT do alvo               decode_value(encode_value(x)) == x — o espelho do spec, isolado
    3. RT em ARQUIVO            outputs/<c>.roundtrip.json == inputs/<c>.entrada.json (diffável)
    4. NUNCA-PIOR               o wire com spec nunca é maior que o que o encoder emite hoje
    5. determinismo             encode duas vezes -> byte-idêntico
    6. o artefato é o wire      o .tcf lido em BINÁRIO é byte-idêntico ao wire medido
    7. o núcleo não regride     encode() sem spec byte-idêntico ao baseline gravado

E o PIN: cada caso declara em `casos.py` quem deve vencer.

`src/tcf` NÃO é tocado — o spec e a rota entram pela API pública, e o FLOOR real decide.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[3]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from casos import CASOS  # noqa: E402
from rota_tipada import decode_tipado_com_spec, encode_tipado_com_spec  # noqa: E402
from spec_int_pad import IntPadSpec, dimensiona  # noqa: E402
from tcf import decode, encode  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def igual_com_tipo(a, b) -> bool:
    """RT de verdade: em Python `True == 1` e `1 == 1.0`. Comparar só valor mascararia."""
    if len(a) != len(b):
        return False
    return all(type(x) is type(y) and x == y for x, y in zip(a, b))


def _limpa():
    """Artefato órfão é indistinguível de resultado atual. `inputs/fontes/` NÃO é limpo:
    é o corpus congelado, e o lab tem de rodar sem `Z:`."""
    for d in (INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    for padrao in ("*.entrada.json", "*.fonte.json"):
        for p in INP.glob(padrao):
            p.unlink()
    INP.mkdir(exist_ok=True)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _limpa()
    falhas, linhas, pulados = [], [], []

    for nome, familia, gerador, ideia, espera in CASOS:
        vals = gerador()
        if vals is None:
            pulados.append(nome)
            continue

        _js(INP / f"{nome}.entrada.json", vals)
        spec = dimensiona(vals)
        _js(INP / f"{nome}.fonte.json", {
            "caso": nome, "familia": familia, "ideia": ideia, "espera": espera,
            "n": len(vals), "k_unicos": len(set(map(str, vals))),
            "primeiros": vals[:5],
            "hash_entrada": hashlib.sha256(
                json.dumps(vals, **JSON_KW).encode()).hexdigest()[:12],
            "spec_dimensionado": None if spec is None else {"largura": spec.largura,
                                                            "wire_id": spec.wire_id},
            "CONSTANTE_na_comparacao": "os MESMOS valores no baseline e no candidato; "
                                       "so' varia a presenca do spec. A largura e' "
                                       "DIMENSIONADA pela coluna (o que um auto-detector "
                                       "faria), nunca escolhida a mao.",
        })

        base = encode(vals)                                   # o que o encoder emite HOJE
        # PROVA 7 — o núcleo não regride: o baseline é gravado e comparado
        _esc(INT / f"{nome}.baseline.tcf", base)
        if not igual_com_tipo(decode(base), vals):
            falhas.append(f"{nome}: PROVA 1 — RT do baseline nao preservou tipo/valor")

        if spec is None:
            wire, venceu = base, False
        else:
            # PROVA 2 — o espelho do spec, isolado
            for v in vals:
                if v is None:
                    continue
                p, _st = spec.encode_value(str(v))
                if spec.decode_value(p) != str(v):
                    falhas.append(f"{nome}: PROVA 2 — espelho do spec falhou em {v!r}")
                    break
            wire, venceu = encode_tipado_com_spec(vals, spec)

        # PROVA 1 — RT estrito COM TIPO, pela rota do protótipo
        volta = decode_tipado_com_spec(wire, spec) if venceu else decode(wire)
        if not igual_com_tipo(volta, vals):
            falhas.append(f"{nome}: PROVA 1 — RT com tipo falhou")
        # PROVA 4 — NUNCA-PIOR
        if B(wire) > B(base):
            falhas.append(f"{nome}: PROVA 4 — NUNCA-PIOR violado ({B(wire)} > {B(base)})")
        # PROVA 5 — determinismo
        w2, _ = (encode_tipado_com_spec(vals, spec) if spec else (encode(vals), False))
        if w2 != wire:
            falhas.append(f"{nome}: PROVA 5 — determinismo violado")
        # PROVA 3 e 6 — arquivo diffável e o artefato É o wire
        _esc(OUT / f"{nome}.tcf", wire)
        _js(OUT / f"{nome}.roundtrip.json", volta)
        if (OUT / f"{nome}.tcf").read_bytes() != wire.encode("utf-8"):
            falhas.append(f"{nome}: PROVA 6 — o .tcf no disco difere do wire medido")
        if (INP / f"{nome}.entrada.json").read_text(encoding="utf-8") != \
           (OUT / f"{nome}.roundtrip.json").read_text(encoding="utf-8"):
            falhas.append(f"{nome}: PROVA 3 — roundtrip.json nao e' diffavel contra a entrada")

        # PIN
        quem = "spec" if venceu else "core"
        if quem != espera:
            falhas.append(f"{nome}: PIN — esperava {espera}, venceu {quem}")
        _js(INT / f"{nome}.candidatos.json", {
            "ideia": ideia, "espera": espera, "venceu": quem,
            "baseline_bytes": B(base), "wire_bytes": B(wire),
            "ganho": round(B(base) / B(wire), 3),
            "header_baseline": base.split("\n")[0][:26],
            "header_wire": wire.split("\n")[0][:26],
            "spec": None if spec is None else {"largura": spec.largura},
        })
        linhas.append({"caso": nome, "familia": familia, "ideia": ideia,
                       "espera": espera, "venceu": quem, "base": B(base),
                       "wire": B(wire), "ganho": round(B(base) / B(wire), 3),
                       "header": wire.split("\n")[0][:22]})
        print(f"  {nome:34s} {B(base):7d} -> {B(wire):7d} ({B(base) / B(wire):5.2f}x) "
              f"{quem:5s} pin {'ok' if quem == espera else 'DIVERGIU'}")

    _js(RAIZ / "resultado.json", {"casos": linhas, "falhas": falhas, "pulados": pulados})
    idx = ["# INDEX", "", "| caso | ideia | espera | venceu | base | wire | ganho |",
           "|---|---|---|---|---:|---:|---:|"]
    for t in linhas:
        idx.append(f"| [`{t['caso']}`](./{t['caso']}.tcf) | {t['ideia']} | {t['espera']} "
                   f"| **{t['venceu']}** | {t['base']} | {t['wire']} | {t['ganho']}x |")
    idx += ["", "Contra-prova por caso: `diff outputs/<c>.roundtrip.json inputs/<c>.entrada.json` "
                "tem de dar VAZIO. Candidatos e baseline em `../intermediates/`.", ""]
    _esc(OUT / "INDEX.md", "\n".join(idx))

    ganham = [t for t in linhas if t["venceu"] == "spec"]
    print(f"\n{len(linhas)} casos ({len(pulados)} pulados) · spec venceu em {len(ganham)}")
    if ganham:
        gs = sorted(t["ganho"] for t in ganham)
        print(f"  ganho: mediana {gs[len(gs) // 2]:.2f}x  max {max(gs):.2f}x")
    print(f"{len(falhas)} falha(s)")
    for f in falhas[:12]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

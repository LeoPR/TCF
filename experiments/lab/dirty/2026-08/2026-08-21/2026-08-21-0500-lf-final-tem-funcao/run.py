"""O ultimo LF: o que tem funcao e o que e' decoracao. (Reavaliacao pedida.)

O PEDIDO (owner, 2026-08-21)
----------------------------
*"reavalie a necessidade tecnica do ultimo '\\n' que nao tem funcao e o que tem
funcao. creio que nao precisamos de caracteres decorativos. ate' entao achei que
o ultimo linefeed tinha funcao pratica para programas como mimetype e programa
file para identificar precisavam do linefeed final."*

POR QUE ESTE LAB EXISTE
-----------------------
Eu ja' tinha respondido isto no lab `0400` — e a resposta estava IMPRECISA. Eu
disse "o LF final e' load-bearing, indecidivel tratar como opcional". O owner
apontou o buraco: isso so' vale se o LF for OPCIONAL. Sendo OBRIGATORIO, ele e'
PREVISIVEL — e pelo criterio do projeto (deduzivel = redundancia de 100%) nao
deveria viajar.

  T1  DROP + READD: o LF e' recuperavel? (se sim, nao carrega informacao)
  T2  O RECEPTOR SABE recolocar? O magic determina a convencao da rota?
  T3  DROP SEM READD: o que se perde?
  T4  ONDE ELE TEM FUNCAO DE VERDADE: o `.8H` conta o LF dentro do `size`?
  T5  QUANTO VALE, e o que se PERDE junto (o detector de truncamento)
"""

from __future__ import annotations

import json
import random
import sys
import warnings
from collections import defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                       # noqa: E402

LF = "\n"
_arquivos: set[Path] = set()


def grava(pasta: Path, nome: str, texto: str) -> None:
    p = pasta / nome
    p.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(p.resolve())


def main() -> int:
    res = {}
    print("=" * 96)
    print("O ULTIMO LF — o que tem funcao, e o que e' decoracao")
    print("=" * 96)

    # ── T1: drop + readd ─────────────────────────────────────────────────
    print("\nT1) DROP + READD — o LF e' recuperavel?")
    rng = random.Random(7)
    corpus = [["a", "b"], ["a", "b", ""], ["a", "b", "", ""], [""], ["", ""],
              ["a"], ["", "a"], ["a", "", "b"], ["r"] * 8, ["r"] * 5 + [""],
              {"a": ["1", "2"], "b": ["x", "y"]}, {"a": ["1", ""]},
              [{"a": 1, "b": [1, 2]}], {"x": {"y": 1}}, [1, 2, 3], [True, False]]
    for _ in range(40):
        n = rng.randint(1, 12)
        corpus.append(["".join(rng.choice("abc ") for _ in range(rng.randint(0, 6)))
                       for _ in range(n)])
    com_lf = ok = 0
    for d in corpus:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w = encode(d)
            if not w.endswith(LF):
                continue
            com_lf += 1
            ok += (w[:-1] + LF == w) and (decode(w[:-1] + LF) == d)
    print(f"  {com_lf} wires terminam em LF · drop+readd devolve o original em {ok}/{com_lf}")
    print("  => o LF final E' 100% RECUPERAVEL. Ele nao carrega informacao —")
    print("     meu 'load-bearing' do lab 0400 estava impreciso.")
    res["T1"] = {"com_lf": com_lf, "drop_readd_ok": ok}
    assert ok == com_lf

    # ── T2: o magic determina? ───────────────────────────────────────────
    print("\nT2) MAS O RECEPTOR SABE RECOLOCAR? — o magic determina a convencao?")
    tab, exemplo = defaultdict(set), defaultdict(dict)
    fuzz = []
    for n in range(1, 20):
        fuzz.append([bool(rng.getrandbits(1)) for _ in range(n)])
        fuzz.append([rng.randint(0, 10 ** 6) for _ in range(n)])
        fuzz.append([str(rng.randint(0, 99)) for _ in range(n)])
    for n in range(1, 9):
        fuzz.append({"a": [str(i) for i in range(n)]})
    for d in fuzz:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            w = encode(d)
        mag = w[:7]
        tab[mag].add(w.endswith(LF))
        exemplo[mag].setdefault(w.endswith(LF), d)
    ambiguos = []
    print(f"  {'magic':<12} emite LF?")
    for m, v in sorted(tab.items()):
        flag = "   <-- AMBIGUO" if len(v) > 1 else ""
        print(f"  {m!r:<12} {v}{flag}")
        if len(v) > 1:
            ambiguos.append(m)
            for e, d in exemplo[m].items():
                print(f"      emite={e}: {str(d)[:56]}")
    print(f"\n  magics ambiguos: {len(ambiguos)}")
    print("  => NAO. O mesmo magic emite em uns casos e nao em outros. Um receptor")
    print("     que le' so' o prefixo NAO sabe se deve recolocar.")
    res["T2"] = {"magics": {m: sorted(v) for m, v in tab.items()},
                 "ambiguos": ambiguos}
    assert ambiguos, "se o magic desambiguasse, o drop seria trivial"

    # ── T3: drop SEM readd ───────────────────────────────────────────────
    print("\nT3) DROP SEM READD — o que se perde?")
    d = ["a", ""]
    w = encode(d)
    perdido = decode(w[:-1])
    print(f"  original {d}  ->  wire {w!r}")
    print(f"  sem o LF final: {w[:-1]!r}  ->  decode = {perdido}")
    print(f"  PERDEU o valor vazio final, SEM erro e SEM warning de diferenca.")
    grava(IN, "vazio-no-fim.json", json.dumps(d, ensure_ascii=False, indent=1))
    grava(OUT, "vazio-no-fim.tcf", w)
    grava(OUT, "vazio-no-fim.roundtrip.json", json.dumps(decode(w), ensure_ascii=False, indent=1))
    grava(OUT, "vazio-no-fim.SEM-LF-decodifica-errado.json",
          json.dumps(perdido, ensure_ascii=False, indent=1))
    res["T3"] = {"original": d, "sem_lf_decodifica": perdido}
    assert perdido != d

    # ── T4: onde o LF TEM funcao ─────────────────────────────────────────
    print("\nT4) ONDE ELE TEM FUNCAO DE VERDADE — o `.8H`")
    h = encode([{"a": 1, "b": [1, 2]}, {"a": 2}])
    cab = h.split(LF, 1)[0]
    print(f"  cabecalho: {cab!r}")
    print("  o `:N` de cada bloco e' um COMPRIMENTO em bytes. Se o LF final")
    print("  estiver DENTRO dele, nao e' trailing decorativo — e' byte contado.")
    try:
        decode(h[:-1])
        situacao = "decodificou (o LF estaria FORA do size)"
    except Exception as e:                                           # noqa: BLE001
        situacao = f"{type(e).__name__}: {str(e)[:60]}"
    print(f"  tirar o LF final -> {situacao}")
    grava(IN, "hierarquico.json", json.dumps([{"a": 1, "b": [1, 2]}, {"a": 2}],
                                             ensure_ascii=False, indent=1))
    grava(OUT, "hierarquico.tcf", h)
    grava(OUT, "hierarquico.roundtrip.json", json.dumps(decode(h), ensure_ascii=False, indent=1))
    res["T4"] = {"cabecalho": cab, "sem_lf": situacao}

    # ── T5: quanto vale, e o que se perde junto ──────────────────────────
    print("\nT5) QUANTO VALE — e o que se PERDE junto")
    tam = []
    for rot, dd in (("1 CPF", ["529.982.247-25"]), ("3 curtos", ["ab", "cd", "ef"]),
                    ("10 valores", [f"v{i}" for i in range(10)]),
                    ("100 valores", [f"valor{i}" for i in range(100)])):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            n = len(encode(dd).encode("utf-8"))
        print(f"  {rot:<14} {n:>5} B   sem o LF: {n-1:>5} B   ({1/n*100:.2f}%)")
        tam.append({"caso": rot, "bytes": n, "pct": round(1 / n * 100, 2)})
    print("\n  E o que se perde junto: hoje o decode do single-col AVISA quando o LF")
    print("  terminador falta — *'grafia nao-canonica; wire possivelmente TRUNCADO'*.")
    print("  Esse warning e' um DETECTOR DE TRUNCAMENTO. Dropar sistematicamente")
    print("  transforma o detector em ruido: truncamento real deixa de se distinguir")
    print("  do normal. O 1 byte economizado custa a capacidade de perceber perda.")
    res["T5"] = tam

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    achados = {p.resolve() for pasta in (IN, OUT) for p in pasta.rglob("*") if p.is_file()}
    assert not (_arquivos - achados) and not (achados - _arquivos)
    print(f"\n-> {len(achados)} arquivos, portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

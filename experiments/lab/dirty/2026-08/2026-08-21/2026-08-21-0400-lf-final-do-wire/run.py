"""O `\\n` final do wire: convencao de arquivo, ou terminador load-bearing?

A PERGUNTA DO OWNER (2026-08-21)
-------------------------------
*"lembrando que o tcf, em termos de arquivo, precisa do \\n no final pois se nao
me engano e' coisa da formatacao para esse tipo de arquivo. so' confirme. ja' um
'\\n' no final na transmissao pode ser verificado para dispensar, salvo se tiver
algum valor vital na comunicacao. eu acho que nao."*

A CONVENCAO DOCUMENTADA (`docs/algorithms/output-convention.md` §3)
-------------------------------------------------------------------
*"O ultimo byte do arquivo PODE ser `\\n` (separador da ultima linha, estilo
POSIX), mas isso e' OPCIONAL. Decoder deve aceitar COM OU SEM."*

O QUE ESTE LAB MEDE
-------------------
  G1  cada rota EMITE o `\\n` final?
  G2  cada rota DECODIFICA sem ele?  (a convencao diz que sim)
  G3  cada rota DECODIFICA com um a mais? (a convencao diz que sim)
  G4  quanto vale dispensa-lo (o `.8` tem diretriz de byte em payload minusculo)

Nada e' soldado. E' verificacao pra decisao.
"""

from __future__ import annotations

import json
import sys
import warnings
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

ROTAS = [
    ("single-col flat", ["aaa", "bbb", "ccc"]),
    ("single-col n=1", ["so-um"]),
    ("single-col spec", ["2026-01-01", "2026-01-02", "2026-01-03"]),
    ("multi-col", {"a": ["1", "2"], "b": ["x", "y"]}),
    ("multi-col n=1", {"a": ["1"]}),
    ("hierarquico", [{"a": 1, "b": [1, 2]}, {"a": 2, "b": [3]}]),
    ("hierarquico obj", {"x": {"y": 1}}),
    ("tipado bool", [True, False, True]),
    ("tipado int", [10, 20, 30]),
    ("tipado misto", [1, None, 3]),
]


def grava(pasta: Path, nome: str, texto: str) -> None:
    p = pasta / nome
    p.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(p.resolve())


def tenta(fn):
    """Devolve (ok, rotulo). Captura warning pra distinguir 'aceita' de
    'aceita reclamando' — a convencao diz ACEITAR, nao aceitar com ressalva."""
    with warnings.catch_warnings(record=True) as capt:
        warnings.simplefilter("always")
        try:
            ok = fn()
        except Exception as e:                                   # noqa: BLE001
            return False, type(e).__name__
    if not ok:
        return False, "RT-diferente"
    return True, ("ok+warning" if capt else "ok")


def main() -> int:
    print("=" * 98)
    print("O `\\n` FINAL DO WIRE — convencao de arquivo ou terminador load-bearing?")
    print("=" * 98)
    print("\n  A convencao documentada (output-convention.md §3) diz: OPCIONAL,")
    print("  e o decoder deve aceitar COM OU SEM. Vamos ver o que o codigo faz.\n")
    print(f"  {'rota':<18} {'emite LF?':<10} {'decode SEM':<18} {'decode COM extra':<18} bytes")
    linhas, viola = [], []
    for rot, dado in ROTAS:
        w = encode(dado)
        emite = w.endswith(LF)
        sem = w[:-1] if emite else w
        com = w if emite else w + LF

        ok_sem, rot_sem = tenta(lambda: decode(sem) == dado)
        # "com um a mais" = sempre acrescentar um LF ao que a rota emitiu
        ok_com, rot_com = tenta(lambda: decode(w + LF) == dado)

        nome = rot.replace(" ", "-")
        grava(IN, f"{nome}.json", json.dumps(dado, ensure_ascii=False, indent=1))
        grava(OUT, f"{nome}.tcf", w)
        grava(OUT, f"{nome}.roundtrip.json",
              json.dumps(decode(w), ensure_ascii=False, indent=1))
        print(f"  {rot:<18} {str(emite):<10} {rot_sem:<18} {rot_com:<18} {len(w.encode()):>5}")
        linhas.append({"rota": rot, "emite_lf": emite, "decode_sem": rot_sem,
                       "decode_com_extra": rot_com, "bytes": len(w.encode("utf-8"))})
        if rot_sem != "ok" or rot_com != "ok":
            viola.append(rot)

    print("\n" + "=" * 98)
    print("VEREDITO")
    print("=" * 98)
    emitem = [x["rota"] for x in linhas if x["emite_lf"]]
    nao = [x["rota"] for x in linhas if not x["emite_lf"]]
    print(f"  EMITEM o LF final ({len(emitem)}): {', '.join(emitem)}")
    print(f"  NAO emitem      ({len(nao)}): {', '.join(nao)}")
    print(f"\n  A convencao promete 'aceitar COM OU SEM'. Rotas que NAO cumprem: "
          f"{len(viola)}/{len(linhas)}")
    for x in linhas:
        if x["decode_sem"] != "ok" or x["decode_com_extra"] != "ok":
            print(f"    {x['rota']:<18} sem-> {x['decode_sem']:<18} "
                  f"com-extra-> {x['decode_com_extra']}")

    print("\n  RESPOSTA A PERGUNTA:")
    print("  1) 'o TCF precisa do \\n no final?' — a CONVENCAO diz que e' OPCIONAL")
    print("     (estilo POSIX). Mas o CODIGO diverge: e' OBRIGATORIO no hierarquico")
    print("     (sem ele: 'size N excede o corpo ... blob truncado?') e PROIBIDO no")
    print("     multi-col e no tipado bool (um a mais: ValueError).")
    print("  2) 'da' pra dispensar na transmissao?' — NAO universalmente. No")
    print("     hierarquico ele e' TERMINADOR DE CORPO: sem ele o decode nao sabe")
    print("     onde o ultimo bloco acaba. No single-col e' tolerado, mas emite")
    print("     warning de grafia nao-canonica. So' seria seguro por-rota, e o")
    print("     ganho e' de 1 byte por wire.")

    econ = sum(1 for x in linhas if x["emite_lf"])
    tot = sum(x["bytes"] for x in linhas)
    print(f"\n  G4 CUSTO: dispensar o LF economizaria {econ} B em {tot:,} B "
          f"({econ/tot*100:.3f}%) neste conjunto — 1 B por wire que o emite.")

    # ── G5: o teste que DECIDE — o LF final e' separavel do dado? ────────
    print(LF + "=" * 98)
    print("G5) O TESTE QUE DECIDE — o LF final e' enchimento ou DADO?")
    print("=" * 98)
    com_vazio, sem_vazio = ["a", "b", ""], ["a", "b"]
    wa, wb = encode(com_vazio), encode(sem_vazio)
    print(f"  {com_vazio}  ->  {wa!r}")
    print(f"  {sem_vazio}       ->  {wb!r}")
    print(f"  wa == wb + LF ?  {wa == wb + LF}")
    assert wa == wb + LF, "a premissa do argumento caiu"
    assert decode(wa) == com_vazio and decode(wb) == sem_vazio
    print(LF + "  => uma coluna PODE terminar em valor vazio, e o wire dessa coluna e'")
    print("     EXATAMENTE o wire da coluna sem o vazio, mais um LF. Logo tratar o")
    print("     LF final como 'opcional' obrigaria o decoder a ADIVINHAR se o ultimo")
    print("     vazio e' enchimento ou dado — indecidivel por construcao.")
    print("     O LF final NAO e' convencao POSIX de arquivo: e' TERMINADOR do")
    print("     ultimo valor, num formato em que LF separa valores.")
    print("     A convencao documentada (§3) esta' ERRADA; o codigo esta' certo.")

    (AQUI / "resultado.json").write_text(json.dumps(
        {"convencao_documentada": "opcional; decoder aceita com ou sem "
                                  "(output-convention.md §3)",
         "rotas": linhas, "rotas_que_violam": viola,
         "economia_bytes": econ, "total_bytes": tot},
        ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    achados = {p.resolve() for pasta in (IN, OUT) for p in pasta.rglob("*") if p.is_file()}
    assert not (_arquivos - achados) and not (achados - _arquivos)
    print(f"\n-> {len(achados)} arquivos, portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

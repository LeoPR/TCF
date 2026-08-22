"""O `\n` final: tem ambiguidade? tem necessidade? — a resposta, e a correcao.

O CRITERIO DO OWNER (2026-08-21)
--------------------------------
*"foco, bastando nao ter ambiguidade, e nao necessidade, focamos nisso, se
alguma utilidade ortogonal, como arquivo, transporte, otimo, senao nao vale
discutir."*

Duas perguntas, so'. E a resposta cabe num par de valores.

O QUE ISTO CORRIGE
------------------
O lab `0500` concluiu "o LF final e' redundante, 100% recuperavel (55/55)". Essa
conclusao esta' ERRADA, e o erro foi de CORPUS: testei `drop + readd`, que e'
uma operacao que JA' SABE que o LF existia, e o corpus omitia o unico par que
decide — `[]` contra `['']`.
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

LF = chr(10)
_arquivos: set[Path] = set()


def grava(pasta: Path, nome: str, texto: str) -> None:
    q = pasta / nome
    q.write_text(texto, encoding="utf-8", newline="")
    _arquivos.add(q.resolve())


def main() -> int:
    print("=" * 92)
    print("O `\n` FINAL — tem ambiguidade? tem necessidade?")
    print("=" * 92)

    # ── O par que decide ─────────────────────────────────────────────────
    print(chr(10)+"1) O PAR QUE DECIDE — coluna VAZIA x coluna com UM valor vazio")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wa, wb = encode([]), encode([""])
    print(f"  []    -> {wa!r}   decode {decode(wa)!r}")
    print(f"  ['']  -> {wb!r}   decode {decode(wb)!r}")
    print(f"  diferem em exatamente: {wb[len(wa):]!r}")
    assert wa != wb and decode(wa) == [] and decode(wb) == [""]

    # ── Se fosse SEPARADOR ───────────────────────────────────────────────
    print(chr(10)+"2) SE O LF FOSSE SEPARADOR (n valores -> n-1 LFs)")
    for d in ([], [""], ["", ""], ["a"], ["a", ""]):
        print(f"  {str(d):<12} -> corpo {LF.join(d)!r}")
    print("  [] e [''] dariam o MESMO corpo vazio -> AMBIGUO.")
    assert LF.join([]) == LF.join([""])

    # ── A resposta ───────────────────────────────────────────────────────
    print(chr(10) + "=" * 92)
    print("A RESPOSTA")
    print("=" * 92)
    print("  AMBIGUIDADE : COM o terminador, nao ha'. SEM ele, ha' — [] e ['']")
    print("                colapsam no mesmo corpo vazio.")
    print("  NECESSIDADE : SIM. Ele carrega exatamente 1 bit, e so' no caso de")
    print("                borda: 'a coluna tem zero valores' x 'tem um valor")
    print("                vazio'. Nas demais posicoes e' redundante — mas a")
    print("                convencao tem de ser uniforme, senao o decoder")
    print("                precisaria de caso especial pro corpo vazio.")
    print(chr(10)+"  => pelo criterio do owner (basta nao ter ambiguidade E nao ter")
    print("     necessidade), o LF final NAO se qualifica: ele TEM necessidade.")
    print("     Discussao encerrada — sem precisar invocar arquivo nem transporte.")

    # ── O erro do lab 0500 ───────────────────────────────────────────────
    print(chr(10) + "=" * 92)
    print("A CORRECAO DO LAB 0500")
    print("=" * 92)
    corpus_0500 = [["a", "b"], ["a", "b", ""], ["a", "b", "", ""], [""],
                   ["", ""], ["a"], ["", "a"], ["a", "", "b"]]
    print(f"  o corpus do 0500 continha []? {[] in corpus_0500}")
    print("  Ele testou `drop + readd` — operacao que JA' SABE que o LF existia.")
    print("  Isso mede RECUPERABILIDADE, nao NECESSIDADE. E o corpus omitia o")
    print("  unico par em que a diferenca aparece. Conclusao do 0500: REVOGADA.")

    grava(IN, "par-que-decide.json", json.dumps([[], [""]], ensure_ascii=False))
    grava(OUT, "coluna-vazia.tcf", wa)
    grava(OUT, "coluna-vazia.roundtrip.json", json.dumps(decode(wa), ensure_ascii=False))
    grava(OUT, "um-valor-vazio.tcf", wb)
    grava(OUT, "um-valor-vazio.roundtrip.json", json.dumps(decode(wb), ensure_ascii=False))
    (AQUI / "resultado.json").write_text(json.dumps({
        "ambiguidade_sem_terminador": True,
        "necessidade": True,
        "par_que_decide": {"[]": wa, "['']": wb, "diferenca": wb[len(wa):]},
        "lab_0500": "REVOGADO — corpus omitia []",
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="")

    achados = {q.resolve() for pasta in (IN, OUT) for q in pasta.rglob("*") if q.is_file()}
    assert not (_arquivos - achados) and not (achados - _arquivos)
    print(f"{chr(10)}-> {len(achados)} arquivos, portao anti-orfao verde")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

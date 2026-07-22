"""Runner: fortifica a hierarquia (1:1 {} + 1:N [] recursivos) + estudo de
cardinalidade (1:1/1:N/N:1/N:N) aplicado à hierarquia. Sem tipos/nulos.

Estrutura (convenção): inputs/ intermediates/ outputs/. Rodar: python run.py
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

from hier import (
    AmbiguityError,
    NNError,
    decode_h,
    denormalize,
    derive_schema,
    encode_h,
    leaves,
)
from cardinality import classify, describe

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from tcf import encode as tcf_encode  # noqa: E402

HERE = Path(__file__).resolve().parent
INP, INTER, OUT = HERE / "inputs", HERE / "intermediates", HERE / "outputs"
INTER.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)


def w(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))  # LF-only (TCF), sem CRLF do Windows


def denorm_csv(cols: dict) -> str:
    n = len(next(iter(cols.values())))
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow([".".join(p) for p in cols])
    for i in range(n):
        wr.writerow([cols[p][i] for p in cols])
    return buf.getvalue()


def process(tag, src, canon, tcf, rt, log):
    records = json.loads((INP / src).read_text(encoding="utf-8"))
    schema = derive_schema(records[0])
    cols = denormalize(records, schema)
    w(INTER / f"{tag}-tabelao.csv", denorm_csv(cols))
    canon_txt = json.dumps(records, ensure_ascii=False, indent=2) + "\n"
    w(INTER / canon, canon_txt)

    blob = encode_h(records)
    w(OUT / tcf, blob)
    back = decode_h(blob)
    rt_txt = json.dumps(back, ensure_ascii=False, indent=2) + "\n"
    w(OUT / rt, rt_txt)

    assert back == records and rt_txt == canon_txt, f"RT falhou em {tag}"
    log.append(f"== {tag} ({src}) ==")
    log.append(f"  header: {blob.splitlines()[0]}")
    log.append(f"  tabelão {len(next(iter(cols.values())))}x{len(cols)}  |  "
               f"RT decode==original: True  |  roundtrip .json == canônico: True")
    log.append(f"  wire outputs/{tcf}: {(OUT / tcf).stat().st_size} B "
               f"(JSON {len((INP / src).read_text(encoding='utf-8').encode())} B)")
    log.append("")
    return records, cols


def cardinality_study() -> str:
    rows = list(csv.reader((INP / "03-cardinalidades-flat.csv").read_text(encoding="utf-8").splitlines()))[1:]
    by_case: dict[str, tuple[list, list]] = {}
    for caso, a, b in rows:
        by_case.setdefault(caso, ([], []))
        by_case[caso][0].append(a)
        by_case[caso][1].append(b)

    out = ["ESTUDO DE DIMENSIONALIDADE — cardinalidade -> mecânica -> hierarquia",
           "(teste de contagem de distintos = descoberta de FD; peça 7)", ""]
    out.append(f"{'par':16} {'dA':>3} {'dB':>3} {'dAB':>4}  {'classe':6} {'aninha?':16} mecânica TCF")
    out.append("-" * 92)
    for caso, (a, b) in by_case.items():
        d = describe("A", a, "B", b)
        out.append(f"{caso+' (A-B)':16} {d['dA']:>3} {d['dB']:>3} {d['dAB']:>4}  "
                   f"{d['classe']:6} {d['na_hierarquia']:16} {d['mecanica_tcf']}")
    out += ["",
            "Mapa (o que UNE as peças do grupo):",
            "  1:1  ambas FDs         -> `{}` objeto aninhado          (ANINHA na hierarquia)",
            "  1:N  só B->A (A repete)-> `[]` array = dual do RLE `*N|`(ANINHA na hierarquia)",
            "  N:1  só A->B (B repete)-> coluna @dict low-card          (NÃO é ramo — é coluna)",
            "  N:N  nenhuma FD        -> tabela-ponte (2 dicts + pares) (NÃO aninha)",
            "",
            "Refinamentos: CHAVE (d=n) != GRUPO (d<<n) — 1:1 de 2 chaves é dict bijetivo, não",
            "árvore. Cardinalidade ⊥ compressibilidade: multiplicidade (RLE↔fk) é separada de",
            "largura-de-valor (@dict encolhe). O ganho de bytes do N:1 é a LARGURA, não o ×N."]
    return "\n".join(out) + "\n"


def n1_demo(cols: dict, n_records: int) -> str:
    """N:1 na PRÁTICA. No tabelão TODA repetição colapsa via RLE/dict do motor — mas
    a cardinalidade explica a ORIGEM: (a) coluna com distintos < nº de registros =
    valor COMPARTILHADO entre registros = N:1 (dict real); (b) distintos == registros
    (com repetição) = coluna-PAI de um array = multiplicidade do 1:N (não é N:1)."""
    out = ["N:1 NA HIERARQUIA — coluna compartilhada = @dict/RLE (não vira ramo)",
           f"(nº de registros = {n_records}; distintos < isso = N:1 real; == isso = pai do 1:N)", ""]
    for p in cols:
        col = cols[p]
        d = len(set(col))
        if d >= len(col):
            continue  # sem repetição, nada a comprimir
        origem = "N:1 compartilhado (dict)" if d < n_records else "pai do 1:N (multiplicidade)"
        body = tcf_encode(col)
        out.append(f"coluna {'.'.join(p)!r}: {len(col)} linhas, {d} distintos -> {origem}")
        out.append("  tcf.encode: " + body.replace("\n", " | ").rstrip(" |"))
        out.append("")
    return "\n".join(out) + "\n"


def nn_demo() -> str:
    """N:N: 2 arrays no mesmo nível -> fail-loud. O caminho é tabela-ponte / dois 1:N."""
    out = ["N:N NA HIERARQUIA — não vira árvore simples (fail-loud) + o caminho", ""]
    caso = [{"aluno": "Ana", "cursos": ["Matematica", "Fisica"], "clubes": ["Xadrez"]}]
    try:
        encode_h(caso)
        out.append("ERRO: deveria falhar")
    except NNError as e:
        out.append(f"encode_h({{aluno, cursos[], clubes[]}}) -> NNError:")
        out.append(f"  {e}")
    out += ["",
            "Por quê: dois arrays irmãos = produto cartesiano (cursos × clubes) que INVENTA",
            "pares inexistentes — semanticamente errado. Caminhos válidos (não neste protótipo):",
            "  (a) tabela-ponte/junction: dict(aluno) + dict(curso) + lista de pares (aluno,curso);",
            "  (b) dois 1:N separados (aluno->cursos[] E aluno->clubes[]) em blocos/tabelas distintos.",
            "N:N é o caso que precisa de link posicional (a peça 9 do grupo), fora do escopo aqui.",
            "",
            "--- LIMITE FD/CHAVE (fail-loud, nunca corromper calado) ---",
            "Instâncias irmãs de MESMA chave abrigando array aninhado se fundiriam na re-nestação",
            "por chave contígua. encode SE AUTO-VERIFICA e recusa (não produz blob que não reverte):"]
    ambiguo = [{"cli": "Ana", "peds": [
        {"data": "2026-X", "itens": [{"p": "a"}]},
        {"data": "2026-X", "itens": [{"p": "b"}]}]}]  # 2 pedidos, MESMA data
    try:
        encode_h(ambiguo)
        out.append("  ERRO: deveria falhar")
    except AmbiguityError as e:
        out.append(f"  encode_h({{2 pedidos data='2026-X', cada um com itens[]}}) -> AmbiguityError:")
        out.append(f"    {e}")
    out += ["  (datas DISTINTAS revertem normal; o caminho geral = fronteira/repetition-level, peça 9.)"]
    return "\n".join(out) + "\n"


def main() -> None:
    log = ["FORTIFICAÇÃO — hierarquia recursiva {} 1:1 + [] 1:N + estudo de cardinalidade", ""]

    recs1, cols1 = process("01-endereco", "01-clientes-endereco-telefones.json",
                           "04-endereco-canonico.json", "01-endereco.tcf",
                           "06-endereco.roundtrip.json", log)
    process("02-pedidos", "02-clientes-pedidos-itens.json",
            "05-pedidos-canonico.json", "02-pedidos.tcf",
            "07-pedidos.roundtrip.json", log)

    w(INTER / "03-cardinalidade-estudo.txt", cardinality_study())
    w(OUT / "08-n1-coluna-compartilhada.txt", n1_demo(cols1, len(recs1)))
    w(OUT / "09-nn-fail-loud.txt", nn_demo())
    w(OUT / "10-contraprova.txt", "\n".join(log) + "\n")

    print("hierarquia-cardinalidade: all checks PASS")
    print("\n".join(log))
    print("--- 01-endereco.tcf ---")
    print((OUT / "01-endereco.tcf").read_text(encoding="utf-8"))
    print("--- 02-pedidos.tcf ---")
    print((OUT / "02-pedidos.tcf").read_text(encoding="utf-8"))
    print("--- estudo de cardinalidade ---")
    print(cardinality_study())


if __name__ == "__main__":
    main()

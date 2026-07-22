"""Dual do RLE na hierarquia: multiplicidade REPETIDA por coluna (tabelão) vs
carregada UMA vez (nível-aware) — reconciliação da conclusão da peça 9 (lab 2328).

O owner reapontou (2026-07-13): na hierarquia, como o header já diz que telefones
está aninhado em pessoa (1:N), o pai NÃO precisa expandir de fato — a multiplicidade
pode ser DEDUZIDA/carregada uma vez, com as colunas "sincronizadas" por nível. Já
tínhamos concluído isso:
  - peça 9 (2328): cardinalidade/rows é DEDUZÍVEL do nº de linhas dos filhos;
    "custo transmitido ZERO"; o header carrega só as arestas de hierarquia.
  - H-CARD-06: o RLE do pai exige o pai AGRUPADO; ordem livre → O(d) runs;
    ordem semântica → side-channel de permutação (= rep/def levels do Dremel).
  - teoria §1-4: (a) RLE `*N|pai` e (b) fk/counts são DUAIS; a ×N é conservada
    (~log N); o schema compra RECONSTRUÇÃO, não bytes de multiplicidade.

Aqui MEDE os dois no mesmo dado (spine: pessoa + endereco{} 1:1 + telefones[] 1:N):

  MODELO A (tabelão, protótipo 2301/2325): toda coluna-pai vai à granularidade FINA
    (telefone); o pai repete e RLE `*N|` colapsa. A multiplicidade [n_i] aparece no
    RLE de CADA coluna-pai (redundante entre irmãs).
  MODELO B (nível-aware, peça 9): cada coluna fica na SUA granularidade (pessoa-nível
    1x por pessoa; telefone achatado); a multiplicidade [n_i] é UM canal `counts`
    (a "sincronização"). Colunas-pai não carregam `*N|`.

Ambos RT-exatos e DUAIS. Sem tipos/nulos. Zero src/tcf.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from tcf import decode as D, encode as E  # noqa: E402

MAGIC = "#TCF.8H"


# --------- flat spine: colunas-pai (escalares + campos de objeto 1:1) + 1 array
def _spine(records: list[dict]):
    """Retorna (parent_paths, array_name, elem_kind, elem_fields)."""
    parents, array = [], None

    def walk(node, prefix):
        nonlocal array
        for k, v in node.items():
            p = prefix + (k,)
            if isinstance(v, list):
                if array is not None:
                    raise ValueError("um array por nível (N:N fora do escopo)")
                if v and isinstance(v[0], dict):
                    array = (k, "objects", list(v[0].keys()))
                else:
                    array = (k, "scalars", None)
            elif isinstance(v, dict):
                walk(v, p)
            else:
                parents.append(p)

    walk(records[0], ())
    return parents, array


def _get(rec: dict, path: tuple):
    for k in path:
        rec = rec[k]
    return str(rec)


# ============================================================ MODELO A (tabelão)
def encode_A(records: list[dict]) -> dict:
    parents, (aname, akind, afields) = _spine(records)
    cols = {p: [] for p in parents}
    if akind == "scalars":
        cols[(aname,)] = []
    else:
        for f in afields:
            cols[(aname, f)] = []
    for rec in records:
        arr = rec[aname]
        for elem in arr:
            for p in parents:
                cols[p].append(_get(rec, p))       # PAI REPETE por filho
            if akind == "scalars":
                cols[(aname,)].append(str(elem))
            else:
                for f in afields:
                    cols[(aname, f)].append(str(elem[f]))
    return {".".join(p): E(cols[p]) for p in cols}  # tcf.encode por coluna


# ============================================================ MODELO B (nível-aware)
def encode_B(records: list[dict]) -> dict:
    parents, (aname, akind, afields) = _spine(records)
    out = {}
    for p in parents:
        out[".".join(p)] = E([_get(rec, p) for rec in records])   # 1x por pessoa
    if akind == "scalars":
        flat = [str(e) for rec in records for e in rec[aname]]
        out[aname] = E(flat)
    else:
        for f in afields:
            out[f"{aname}.{f}"] = E([str(e[f]) for rec in records for e in rec[aname]])
    out["#counts"] = E([str(len(rec[aname])) for rec in records])  # multiplicidade 1x
    return out


def decode_B(bodies: dict, parents, aname, akind, afields, records_shape) -> list[dict]:
    """RT: reconstrói via counts (sincronização)."""
    counts = [int(x) for x in D(bodies["#counts"])]
    pcols = {p: D(bodies[".".join(p)]) for p in parents}
    if akind == "scalars":
        acol = D(bodies[aname]); off = 0
        recs = []
        for i, n in enumerate(counts):
            rec = _build(parents, pcols, i)
            rec[aname] = acol[off:off + n]; off += n
            recs.append(rec)
        return recs
    acols = {f: D(bodies[f"{aname}.{f}"]) for f in afields}
    off, recs = 0, []
    for i, n in enumerate(counts):
        rec = _build(parents, pcols, i)
        rec[aname] = [{f: acols[f][off + k] for f in afields} for k in range(n)]
        off += n
        recs.append(rec)
    return recs


def _build(parents, pcols, i):
    rec = {}
    for p in parents:
        cur = rec
        for k in p[:-1]:
            cur = cur.setdefault(k, {})
        cur[p[-1]] = pcols[p][i]
    return rec


def total(bodies: dict) -> int:
    return sum(len(b.encode()) for b in bodies.values())

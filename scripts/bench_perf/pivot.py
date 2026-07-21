"""O PIVO: o dataset e' a fonte, tudo o mais e' derivado dele.

Diretriz do owner (2026-07-21), e a razao dela:

    "os datasets hierarquicos sao maiores que o json lib implementada, e o
     jsonlib implementada tambem e' menor que o json RFC, logo, o roundtrip
     garante que so' veremos json possivel de tcf. pra isso ocorrer, o json tem
     que ser gerado pelo dataset primeiro, fazer o oposto pode cair num json que
     nao importa e exporta da mesma forma."

As classes se aninham:  .8H (o que o TCF representa)  ⊃  jsonlib (CPython)  ⊂  RFC 8259.

Partir de um TEXTO JSON arbitrario cai em coisas que a propria lib nao reproduz
identicas — ordem de chave, formato de numero, escape unicode, chave duplicada —
e o TCF nao deve ser cobrado por elas. Partindo do DATASET e gerando o JSON dele,
o roundtrip `dataset -> json -> dataset` faz duas coisas no mesmo ato:
  (a) da' o CUSTO DE REFERENCIA do JSON puro, e
  (b) PROVA que o dado esta' na classe alcancavel pelo TCF.

Por isso o gate G2 nao e' um teste separado: e' a mesma execucao, cronometrada.
Falhou G2 => a celula e' REJEITADA com motivo; nunca vira cobranca contra o TCF.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

# PIVO: retangular, tudo str, sem None.
Pivot = dict[str, list[str]]
Records = list[dict[str, Any]]


# ----------------------------------------------------------------- coercao


def coerce_str(cols: dict[str, list[Any]]) -> tuple[Pivot, int]:
    """`None -> ''`, resto via str(). Devolve (pivo, n_nulls_coerced).

    A coercao e' PARTE DA DEFINICAO do pivo e se aplica igualmente a todos os
    caminhos — nunca so' ao TCF. Se so' o TCF pagasse a coercao, a comparacao
    contra json/csv ja' nasceria torta.
    """
    out: Pivot = {}
    n_nulls = 0
    for nome, vals in cols.items():
        col: list[str] = []
        for v in vals:
            if v is None:
                n_nulls += 1
                col.append("")
            elif isinstance(v, str):
                col.append(v)
            else:
                col.append(str(v))
        out[str(nome)] = col
    return out, n_nulls


# ----------------------------------------------------------------- derivacoes


def to_records(p: Pivot) -> Records:
    """Pivo (col-major) -> registros (row-major). Inversa: to_columns."""
    nomes = list(p.keys())
    if not nomes:
        return []
    n = len(p[nomes[0]])
    return [{k: p[k][i] for k in nomes} for i in range(n)]


def to_columns(recs: Records) -> Pivot:
    """Registros -> pivo. Inversa de to_records (para dados retangulares)."""
    if not recs:
        return {}
    nomes = list(recs[0].keys())
    return {k: [r[k] for r in recs] for k in nomes}


def to_json_text(obj: Any) -> str:
    """Serializacao canonica do eixo de referencia. `allow_nan=False`: o json do
    Python EMITE NaN/Infinity por default (nao-RFC); a estrita rejeita — e uma lib
    compilada/de-outra-linguagem tambem rejeitaria. Congelada no manifesto."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _reject_const(tok: str):
    raise ValueError(f"constante nao-RFC no JSON: {tok!r}")


def from_json_text(txt: str) -> Any:
    # parse_constant rejeita NaN/Infinity/-Infinity tambem na ENTRADA
    return json.loads(txt, parse_constant=_reject_const)


# RFC 7493 (I-JSON): o range de inteiro que TODA implementacao round-trip sem
# perda e' o double-seguro. Fora dele, um parser int64/double de outra linguagem
# (ou o Rust do 1.0) perderia precisao — logo NAO esta' na classe portavel.
_MAX_SAFE_INT = 2 ** 53 - 1


def _assert_portavel(obj: Any, caminho: str = "$") -> None:
    """Anda o objeto e exige a classe que QUALQUER lib json round-trip:
    o TCF entende DATASET (dict/list/escalar); o JSON e' so' uma materializacao,
    e so' vale se sobrevive ao round-trip em toda implementacao — nao so' no
    Python permissivo."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ClasseRejeitada("G2", f"chave nao-string em {caminho}: {type(k).__name__} "
                                      f"(o Python coage int->str; a compilada nao)")
            _assert_portavel(v, f"{caminho}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_portavel(v, f"{caminho}[{i}]")
    elif isinstance(obj, bool):
        pass                                            # bool antes de int (bool ⊂ int)
    elif isinstance(obj, int):
        if not (-_MAX_SAFE_INT <= obj <= _MAX_SAFE_INT):
            raise ClasseRejeitada("G2", f"int fora do range I-JSON (±2^53-1) em {caminho}: {obj} "
                                  f"(um parser int64/double de outra linguagem perderia precisao)")
    elif isinstance(obj, float):
        import math
        if not math.isfinite(obj):
            raise ClasseRejeitada("G2", f"float nao-finito em {caminho}: {obj}")
    elif obj is None or isinstance(obj, str):
        pass
    else:
        raise ClasseRejeitada("G2", f"tipo fora da classe json em {caminho}: {type(obj).__name__}")


def to_csv_text(recs: Records) -> str:
    buf = io.StringIO(newline="")
    if not recs:
        return ""
    w = csv.DictWriter(buf, fieldnames=list(recs[0].keys()), lineterminator="\n")
    w.writeheader()
    w.writerows(recs)
    return buf.getvalue()


def from_csv_text(txt: str) -> Records:
    if not txt:
        return []
    return list(csv.DictReader(io.StringIO(txt, newline="")))


# ----------------------------------------------------------------- planos de aninhamento
# Cada plano tem INVERSA verificada por G6 — senao estariamos comparando bytes e
# tempo de conteudos diferentes entre o plano e o aninhado.


def nest_object_group(recs: Records, sep: str = "_") -> Records:
    """Colunas com prefixo comum viram sub-objeto: capital_gain -> capital:{gain}."""
    if not recs:
        return []
    campos = list(recs[0].keys())
    prefixos: dict[str, list[str]] = {}
    for c in campos:
        if sep in c:
            pre = c.split(sep, 1)[0]
            prefixos.setdefault(pre, []).append(c)
    agrupar = {p: cs for p, cs in prefixos.items() if len(cs) >= 2}
    if not agrupar:
        return [dict(r) for r in recs]
    dentro = {c for cs in agrupar.values() for c in cs}
    out: Records = []
    for r in recs:
        novo: dict[str, Any] = {k: r[k] for k in campos if k not in dentro}
        for pre, cs in agrupar.items():
            novo[pre] = {c.split(sep, 1)[1]: r[c] for c in cs}
        out.append(novo)
    return out


def unnest_object_group(recs: Records, sep: str = "_") -> Records:
    out: Records = []
    for r in recs:
        plano: dict[str, Any] = {}
        for k, v in r.items():
            if isinstance(v, dict):
                for sub, val in v.items():
                    plano[f"{k}{sep}{sub}"] = val
            else:
                plano[k] = v
        out.append(plano)
    return out


def nest_optional(recs: Records) -> Records:
    """Campo OMITIDO onde o valor e' '' — exercita a mascara de opcionalidade do .8H."""
    return [{k: v for k, v in r.items() if v != ""} for r in recs]


def unnest_optional(recs: Records, campos: list[str]) -> Records:
    return [{k: r.get(k, "") for k in campos} for r in recs]


def nest_typed(recs: Records, plano: dict[str, str]) -> Records:
    """Colunas declaradas viram int/float/bool — exercita as tags de tipo P2.

    O custo de TIPAR e' do dado, nao do TCF: por isso existe o caminho de
    referencia `json-ref-typed`, pra isolar esse custo do resto.
    """
    conv = {"int": int, "float": float,
            "bool": lambda s: {"true": True, "false": False}[s.lower()]}
    out: Records = []
    for r in recs:
        novo: dict[str, Any] = {}
        for k, v in r.items():
            if k in plano:
                novo[k] = conv[plano[k]](v)
            else:
                novo[k] = v
        out.append(novo)
    return out


def untyped(recs: Records, plano: dict[str, str]) -> Records:
    out: Records = []
    for r in recs:
        novo: dict[str, Any] = {}
        for k, v in r.items():
            if k in plano:
                novo[k] = "true" if v is True else "false" if v is False else str(v)
            else:
                novo[k] = v
        out.append(novo)
    return out


def nest_array_by_key(recs: Records, chave: str) -> Records:
    """Agrupa por chave -> {chave, items:[...]}. 1:N de verdade (ex: lineitem por orderkey)."""
    grupos: dict[str, Records] = {}
    ordem: list[str] = []
    for r in recs:
        k = r[chave]
        if k not in grupos:
            grupos[k] = []
            ordem.append(k)
        grupos[k].append({kk: vv for kk, vv in r.items() if kk != chave})
    return [{chave: k, "items": grupos[k]} for k in ordem]


def unnest_array_by_key(recs: Records, chave: str) -> Records:
    out: Records = []
    for g in recs:
        for it in g["items"]:
            r = {chave: g[chave]}
            r.update(it)
            out.append(r)
    return out


# ----------------------------------------------------------------- gates de classe
# Rodam ANTES de qualquer cronometro. Falhou => a celula nao e' medida.


class ClasseRejeitada(Exception):
    """O dado esta' fora da classe alcancavel. Nao e' erro do TCF."""

    def __init__(self, gate: str, motivo: str):
        self.gate, self.motivo = gate, motivo
        super().__init__(f"{gate}: {motivo}")


def g1_retangular(p: Pivot) -> None:
    if not p:
        raise ClasseRejeitada("G1", "pivo vazio")
    tam = {k: len(v) for k, v in p.items()}
    if len(set(tam.values())) != 1:
        raise ClasseRejeitada("G1", f"colunas de tamanhos distintos: {tam}")
    if to_columns(to_records(p)) != p:
        raise ClasseRejeitada("G1", "to_columns(to_records(P)) != P")


# Lib compilada/estrita, se existir no ambiente — confirma a classe por uma
# SEGUNDA implementacao (Rust/C), nao so' pelo Python. Ausente: a checagem
# manual _assert_portavel (RFC 8259 + I-JSON) ja' cobre o essencial.
_STRICT = None
for _m in ("orjson", "msgspec", "ujson"):
    try:
        _STRICT = __import__(_m)
        _STRICT_NOME = _m
        break
    except ImportError:
        continue


def g2_classe_json(obj: Any) -> str:
    """O CORACAO da diretriz do owner: prova de pertencimento + custo de referencia.

    "ter um json pra testar nao e' a mesma coisa que um json que aguente um
     roundtrip mesmo pelas libs json da linguagem (...) e a compilada tambem."

    O TCF entende DATASET (dict/list/escalar). O JSON e' so' uma materializacao.
    A classe valida e' a INTERSECAO das implementacoes — o que Python E uma lib
    compilada round-trip — nao o que so' o Python permissivo aceita. Fora dela:
    celula REJEITADA, nunca "consertamos o JSON" pra ele passar.

    Devolve o texto JSON (insumo do caminho de referencia).
    """
    _assert_portavel(obj)                               # RFC 8259 + I-JSON, manual
    try:
        txt = to_json_text(obj)                         # allow_nan=False (estrito)
    except (ValueError, TypeError) as e:
        raise ClasseRejeitada("G2", f"json.dumps estrito rejeitou: {e}")
    if from_json_text(txt) != obj:                      # round-trip identidade (Python)
        raise ClasseRejeitada("G2", "python json.loads(dumps(X)) != X — fora da classe")
    if _STRICT is not None:                             # segunda implementacao (compilada)
        try:
            if _STRICT.loads(_STRICT.dumps(obj)) != obj:
                raise ClasseRejeitada("G2", f"{_STRICT_NOME}(compilada) round-trip != X")
        except (TypeError, ValueError) as e:
            raise ClasseRejeitada("G2", f"{_STRICT_NOME}(compilada) rejeitou: {e}")
    return txt


def g3_classe_csv(recs: Records) -> str | None:
    """CSV nao tem classe aninhada nem tipos; devolve None quando nao se aplica."""
    try:
        txt = to_csv_text(recs)
        return txt if from_csv_text(txt) == recs else None
    except Exception:
        return None


def g6_aninhamento_sem_perda(recs: Records, nest, unnest) -> Records:
    """O aninhado tem que carregar EXATAMENTE a informacao do plano."""
    aninhado = nest(recs)
    if unnest(aninhado) != recs:
        raise ClasseRejeitada("G6", "unnest(nest(records)) != records")
    return aninhado


__all__ = [
    "Pivot", "Records", "coerce_str", "to_records", "to_columns",
    "to_json_text", "from_json_text", "to_csv_text", "from_csv_text",
    "nest_object_group", "unnest_object_group", "nest_optional", "unnest_optional",
    "nest_typed", "untyped", "nest_array_by_key", "unnest_array_by_key",
    "ClasseRejeitada", "g1_retangular", "g2_classe_json", "g3_classe_csv",
    "g6_aninhamento_sem_perda",
]

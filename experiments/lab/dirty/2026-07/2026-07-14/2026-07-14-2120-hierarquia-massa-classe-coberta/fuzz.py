"""FIXAR O ÓBVIO — testa EM MASSA a classe coberta do weld hierárquico (src/tcf).

Owner (2026-07-14): "vamos fixar o óbvio primeiro. fechar, testar em massa e ir fechando
os outros." O óbvio = o codec hierárquico weldado (a20ddf7) na classe que ELE cobre.
Aqui: fuzz DETERMINÍSTICO (seed fixa) gerando milhares de documentos aleatórios DENTRO
da classe coberta e exigindo RT byte-exato `decode(encode_hierarchical(recs)) == recs`.

Classe COBERTA (o que o gerador produz):
  - raiz = lista de objetos, MESMO schema em todos os registros (sem ragged)
  - escalares string; objetos aninhados `{}` (1:1); arrays `[]` de objetos ou de escalares
    (1:N) com #count; arrays VAZIOS; múltiplos arrays IRMÃOS; arrays ANINHADOS (profundidade)
Fora da classe (NÃO gerado aqui; é fail-loud, coberto em tests/test_hierarchical_rt.py):
  ragged (chave faltando), null, tipos mistos, N:N.

Zero mudança em src/tcf — só USA a API pública read-only.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from tcf import decode, encode_hierarchical  # noqa: E402


def _scalar(rng: random.Random) -> str:
    kind = rng.random()
    if kind < 0.25:                       # numérico-como-string
        return str(rng.randint(0, 999999))
    if kind < 0.45:                       # baixa cardinalidade (exercita @dict/RLE)
        return rng.choice(["ativo", "inativo", "pendente", "SP", "RJ", "MG"])
    if kind < 0.60:                       # com separadores (exercita escaping)
        return rng.choice(["a,b", "x|y", "l\\m", "p:q", "c#d"])
    # texto livre variável
    n = rng.randint(1, 24)
    return "".join(rng.choice("abcdefghij .-_0123456789") for _ in range(n))


def _make_schema(rng: random.Random, depth: int) -> dict:
    """Gera um SCHEMA (nomes→tipo), fixo p/ todos os registros do documento (sem ragged)."""
    schema: dict = {}
    n_fields = rng.randint(1, 4)
    for i in range(n_fields):
        name = f"f{i}"
        r = rng.random()
        if depth > 0 and r < 0.22:                       # objeto aninhado 1:1
            schema[name] = ("obj", _make_schema(rng, depth - 1))
        elif depth > 0 and r < 0.44:                     # array de objetos 1:N
            schema[name] = ("arr_obj", _make_schema(rng, depth - 1))
        elif r < 0.60:                                   # array de escalares 1:N
            schema[name] = ("arr_sca", None)
        else:                                            # escalar
            schema[name] = ("scalar", None)
    return schema


def _emit(rng: random.Random, schema: dict) -> dict:
    rec: dict = {}
    for name, (kind, sub) in schema.items():
        if kind == "scalar":
            rec[name] = _scalar(rng)
        elif kind == "obj":
            rec[name] = _emit(rng, sub)
        elif kind == "arr_obj":
            m = rng.choice([0, 1, 1, 2, 3])              # inclui array VAZIO
            rec[name] = [_emit(rng, sub) for _ in range(m)]
        elif kind == "arr_sca":
            m = rng.choice([0, 1, 1, 2, 4])
            rec[name] = [_scalar(rng) for _ in range(m)]
    return rec


def _make_doc(rng: random.Random) -> list:
    schema = _make_schema(rng, depth=rng.randint(0, 3))
    n = rng.randint(1, 8)
    return [_emit(rng, schema) for _ in range(n)]


def main():
    N = 8000
    rng = random.Random(20260714)   # seed fixa → determinístico/reproduzível
    ok = 0
    fails = []
    empty_arr = sibling_arr = nested = deep = 0
    for _ in range(N):
        recs = _make_doc(rng)
        # estatística de cobertura
        flat = str(recs)
        if "[]" in flat:
            empty_arr += 1
        rec0 = recs[0]
        n_arr = sum(1 for v in rec0.values() if isinstance(v, list))
        if n_arr >= 2:
            sibling_arr += 1
        if any(isinstance(v, list) and v and isinstance(v[0], dict)
               and any(isinstance(x, list) for x in v[0].values()) for v in rec0.values()):
            nested += 1
        try:
            got = decode(encode_hierarchical(recs))
            if got == recs:
                ok += 1
            else:
                fails.append(("RT-mismatch", recs))
        except Exception as exc:  # noqa: BLE001
            fails.append((f"{type(exc).__name__}: {exc}", recs))

    lines = [
        "FIXAR O ÓBVIO — fuzz em massa da classe coberta do weld hierárquico",
        "",
        f"documentos aleatórios (seed 20260714, determinístico): {N}",
        f"RT byte-exato decode(encode_hierarchical(recs))==recs: {ok}/{N}",
        f"falhas: {len(fails)}",
        "",
        "cobertura exercitada (documentos que contêm o caso):",
        f"  arrays vazios [] .............. {empty_arr}",
        f"  >=2 arrays irmãos no registro . {sibling_arr}",
        f"  arrays aninhados (arr>obj>arr)  {nested}",
    ]
    if fails:
        lines += ["", "PRIMEIRAS FALHAS:"]
        for msg, recs in fails[:5]:
            lines.append(f"  {msg}  <=  {recs!r}")
    else:
        lines += ["", "0 falhas — a classe coberta do weld está robusta neste fuzz."]

    outdir = Path(__file__).resolve().parent / "outputs"
    outdir.mkdir(exist_ok=True)
    (outdir / "01-fuzz.txt").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    print("\n".join(lines))
    if fails:
        sys.exit(1)


if __name__ == "__main__":
    main()

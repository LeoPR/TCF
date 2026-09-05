"""verifica_divulgacao.py: reconfere todo numero do material de `docs/divulgacao/`.

O README daquela pasta exige que nenhum numero seja estimativa e que cada um tenha um
comando que o reproduz. Este e' o comando.

Vale aqui a regra §RT do projeto, e ela e' o motivo de o script existir: **nao se reporta
byte sem roundtrip validado**. Todo tamanho impresso abaixo passou por `decode(encode(x)) ==
x` antes de aparecer. Se um roundtrip falhar, o script sai != 0 e o numero NAO pode ser
publicado.

    python scripts/verifica_divulgacao.py

`brotli` e `zstandard` sao opcionais: sem eles a tabela de canal sai com as colunas que der.
"""

from __future__ import annotations

import gzip
import json
import sys
import time

from tcf import decode, encode, view

try:
    import brotli
except ImportError:
    brotli = None
try:
    import zstandard
except ImportError:
    zstandard = None

FALHAS: list[str] = []

# O cadastro que aparece na capa do repo e nos textos de divulgacao. CPF de digito
# repetido de proposito: sao sentinelas, nao passam no DV, e nao colidem com pessoa.
TABELA = {
    "nome": ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha"],
    "email": ["ana@acme.com.br", "bruno@acme.com.br",
              "carla@acme.com.br", "diego@acme.com.br"],
    "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plano": ["Premium", "Premium", "Basic", "Premium"],
    "cpf": ["111.111.111-11", "222.222.222-22", "333.333.333-33", "444.444.444-44"],
}

ANINHADO = [
    {"nome": "Ana Souza", "cpf": "111.111.111-11", "ativo": True,
     "fones": ["11 98765-4321", "11 3555-0100"]},
    {"nome": "Bruno Lima", "cpf": "999.999.999-99", "ativo": False,
     "fones": ["21 99888-7766"]},
]


def rt(rotulo: str, dado, **kw) -> tuple[str, int]:
    """Codifica, VALIDA O ROUNDTRIP, e so' entao reporta o tamanho (regra §RT)."""
    wire = encode(dado, **kw)
    ok = decode(wire) == dado
    if not ok:
        FALHAS.append(rotulo)
    n = len(wire.encode("utf-8"))
    print(f"  {rotulo:<32} {n:>5} B   RT={'OK' if ok else 'FALHOU'}")
    return wire, n


def canal(rotulo: str, texto: str) -> None:
    """Uma linha da tabela de compressao de canal, em nivel maximo."""
    b = texto.encode("utf-8")
    g = len(gzip.compress(b, 9, mtime=0))
    br = len(brotli.compress(b, quality=11)) if brotli else 0
    zs = len(zstandard.ZstdCompressor(level=22).compress(b)) if zstandard else 0
    print(f"  {rotulo:<10} {len(b):>6} {g:>6} {br or '-':>6} {zs or '-':>6}")


def mediana_ms(fn, n: int = 5) -> float:
    fn()                                              # warmup descartado
    t = sorted(_cronometra(fn) for _ in range(n))
    return t[len(t) // 2] * 1000


def _cronometra(fn) -> float:
    a = time.perf_counter()
    fn()
    return time.perf_counter() - a


def main() -> int:
    registros = [dict(zip(TABELA, v)) for v in zip(*TABELA.values())]

    print("1. O cadastro de 4 registros")
    wire, _ = rt("TCF (#TCF.8M)", TABELA)
    rt("TCF + nature cpf", TABELA, schema={"cpf": "cpf"})

    csv = ("nome,email,cidade,plano,cpf\n"
           + "\n".join(",".join(r.values()) for r in registros))
    js = json.dumps(registros, separators=(",", ":"), ensure_ascii=False)
    jsonl = "\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False)
                      for r in registros)
    for rotulo, s in (("CSV", csv), ("JSON compacto", js), ("JSONL compacto", jsonl)):
        print(f"  {rotulo:<32} {len(s.encode()):>5} B")

    print("\n  sob compressao de canal, nivel maximo:")
    print(f"  {'formato':<10} {'cru':>6} {'gzip':>6} {'br':>6} {'zstd':>6}")
    for rotulo, s in (("JSON", js), ("JSONL", jsonl), ("TCF", wire), ("CSV", csv)):
        canal(rotulo, s)

    print("\n2. O mesmo dado aninhado")
    wire_h, _ = rt("TCF (#TCF.8H)", ANINHADO)
    rt("TCF (#TCF.8H) + nature cpf", ANINHADO, schema={"cpf": "cpf"})
    js_n = json.dumps(ANINHADO, separators=(",", ":"), ensure_ascii=False)
    print(f"  {'JSON compacto':<32} {len(js_n.encode()):>5} B")
    print(f"  header: {wire_h.splitlines()[0]}")

    print("\n3. A consulta sem descomprimir tudo")
    v = view(wire)
    print(f"  columns              {list(v.columns)}")
    print(f"  nrows                {v.nrows}")
    print(f"  distinct('cidade')   {sorted(v.distinct('cidade'))}")
    print(f"  group_count('plano') {dict(v.group_count('plano'))}")
    print(f"  column_bytes('cpf')  {v.column_bytes('cpf')} B de {v.total_bytes} B")

    print("\n4. A assimetria entre escrever e ler")
    grande = {f"col{c}": [f"valor-{(i * 7 + c) % 400:04d}" for i in range(3000)]
              for c in range(15)}
    wire_g = encode(grande)
    if decode(wire_g) != grande:
        FALHAS.append("tabela 3000x15")
    te = mediana_ms(lambda: encode(grande))
    td = mediana_ms(lambda: decode(wire_g))
    print(f"  tabela 3000 x 15, baixa cardinalidade (400 valores unicos)")
    print(f"  encode {te:8.1f} ms · decode {td:8.1f} ms · razao {te / td:.1f}x")

    print(f"\nfalhas de roundtrip: {FALHAS if FALHAS else 'nenhuma'}")
    return 1 if FALHAS else 0


if __name__ == "__main__":
    sys.exit(main())

"""Censo HONESTO das divergencias de status entre o CNPJ historico e o unificado.

Eu afirmei "0 divergencias, inclusive de status" — mas medi num corpus NUMERICO.
A revisao apontou (achado #21) que a troca de `\\d` por `[0-9A-Z]` na regex muda
status de valores com FORMA alfanumerica, que meu corpus quase nao tinha.

Aqui: varredura ampla, classificando CADA divergencia, e checando se alguma
muda BYTE (o que seria grave) ou so' ROTULO (telemetria).
"""
import random
import re
import sys
from collections import Counter

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[5] / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tcf.natures.templated_checked import (                     # noqa: E402
    BASE94, MARKER_LITERAL, SPEC_CNPJ, _cnpj_check_fn,
)

H_RE = re.compile(r'^(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})$')


def h_classify(v):
    """O classify_value do SPEC_CNPJ HISTORICO (numerico), verbatim."""
    if not v:
        return 'empty_value'
    if len(v) == 14 and v.isdigit():
        return 'format_unmasked'
    if not H_RE.match(v):
        return 'format_mismatch' if len(v) > 5 else 'length_wrong'
    ds = ''.join(c for c in v if c.isdigit())
    if len(ds) != 14:
        return 'length_wrong'
    body = [int(d) for d in ds[:12]]
    if _cnpj_check_fn(body) != [int(d) for d in ds[12:]]:
        return 'check_invalid'
    return 'compressible'


def h_encode(v):
    st = h_classify(v)
    if st != 'compressible':
        return MARKER_LITERAL + v, st
    n = int(''.join(c for c in v if c.isdigit())[:12])
    ch = []
    for _ in range(7):
        ch.append(BASE94[n % len(BASE94)])
        n //= len(BASE94)
    return ''.join(reversed(ch)), st


# ── corpus AMPLO, de proposito cobrindo as formas alfanumericas ─────────
rng = random.Random(7)
AL = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
casos = []
for _ in range(3000):                                   # numerico valido
    b = [rng.randint(0, 9) for _ in range(12)]
    s = ''.join(map(str, b + _cnpj_check_fn(b)))
    casos.append(f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}")
for _ in range(3000):                                   # alfanumerico valido
    c = ''.join(rng.choice(AL) for _ in range(12))
    d = ''.join(str(x) for x in _cnpj_check_fn([ord(x) - 48 for x in c]))
    s = c + d
    casos.append(f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}")
for _ in range(2000):                                   # mascarado, DV ERRADO
    c = ''.join(rng.choice(AL) for _ in range(12))
    s = c + f"{rng.randint(0,99):02d}"
    casos.append(f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}")
for _ in range(2000):                                   # SEM mascara, 14 chars
    casos.append(''.join(rng.choice(AL) for _ in range(14)))
casos += ["", "1", "abc", "12.abc.345/01de-35", "12.ABC.345/01DE-3A",
          "AB.CDE.FGH/IJKL-99", "0614756300019A", "12ABC34501DEAB"]

print("=" * 96)
print("CENSO DE STATUS — historico (numerico) x unificado (alfanumerico)")
print("=" * 96)
div_status = Counter()
div_bytes = 0
exemplos = {}
for v in casos:
    sa = h_classify(v)
    sb = SPEC_CNPJ.classify_value(v)
    pa, _ = h_encode(v)
    pb, _ = SPEC_CNPJ.encode_value(v)
    if pa != pb:
        div_bytes += 1
        if 'BYTE' not in exemplos:
            exemplos['BYTE'] = (v, pa, pb)
    if sa != sb:
        div_status[(sa, sb)] += 1
        exemplos.setdefault((sa, sb), v)

print(f"  corpus: {len(casos):,} valores")
print(f"\n  divergencias de BYTE  : {div_bytes:,}")
print(f"  divergencias de STATUS: {sum(div_status.values()):,}")
print(f"\n  {'historico':>18} -> {'unificado':<18} {'n':>7}   exemplo")
for (sa, sb), n in div_status.most_common():
    print(f"  {sa:>18} -> {sb:<18} {n:>7}   {exemplos[(sa,sb)]!r}")

# a pergunta que decide: alguma divergencia de status muda BYTE?
print("\n  Toda divergencia de status acima muda o BYTE emitido?")
muda = 0
for (sa, sb) in div_status:
    v = exemplos[(sa, sb)]
    pa, _ = h_encode(v)
    pb, _ = SPEC_CNPJ.encode_value(v)
    if pa != pb:
        muda += 1
        print(f"    MUDA: {v!r}  {pa!r} -> {pb!r}")
print(f"    classes que mudam byte: {muda}/{len(div_status)}")

if div_bytes:
    v, pa, pb = exemplos['BYTE']
    print(f"\n  1o caso de divergencia de BYTE: {v!r}\n    historico {pa!r}\n    unificado {pb!r}")
    print("  (esperado: sao os CNPJ ALFANUMERICOS — o historico nao os comprimia,")
    print("   caia em literal. Nao e' regressao: e' a capacidade nova.)")

# e o RT, que e' o que nao pode quebrar
rt = sum(1 for v in casos if SPEC_CNPJ.decode_value(SPEC_CNPJ.encode_value(v)[0]) == v)
print(f"\n  ROUNDTRIP no corpus inteiro: {rt:,}/{len(casos):,}")
assert rt == len(casos), "RT QUEBROU"

"""O CNPJ unificado (ADR-0044) e' byte-neutro pro dominio NUMERICO?

O diferencial anterior lia `spec.encoded_length` do spec VIVO — que agora e' 10 —
e por isso simulava "algoritmo antigo com parametro novo". Aqui os parametros
HISTORICOS sao pinados: regex numerica, encoded_length=7, formatter decimal.

Compara, no dominio que o spec historico cobria:
  E) encode: payload byte a byte
  D) decode: payloads validos E adulterados de 7 chars
  S) status (telemetria)
E confirma que o CPF, que nao foi tocado por este weld, segue identico.
"""
import random
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tcf.natures.templated_checked import (                       # noqa: E402
    BASE94, MARKER_LITERAL, SPEC_CNPJ, SPEC_CPF, _cnpj_check_fn,
)

# ── o SPEC_CNPJ historico, reconstruido com os parametros de ANTES ──────
H_RE = re.compile(r'^(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})$')
H_LEN = 7


def h_formatter(digits):
    s = ''.join(str(d) for d in digits)
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


def h_classify(v):
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
    for _ in range(H_LEN):
        ch.append(BASE94[n % len(BASE94)])
        n //= len(BASE94)
    return ''.join(reversed(ch)), st


def h_decode(p):
    if p.startswith(MARKER_LITERAL):
        return p[1:]
    if len(p) == H_LEN and all(c in BASE94 for c in p):
        n = 0
        for c in p:
            n = n * len(BASE94) + BASE94.index(c)
        d = [int(x) for x in str(n).zfill(12)]
        d.extend(_cnpj_check_fn(d))
        return h_formatter(d)
    return p


# ── corpus: so' o que o spec HISTORICO cobria (numerico) + adversariais ──
rng = random.Random(20260821)
casos = []
for _ in range(4000):
    b = [rng.randint(0, 9) for _ in range(12)]
    d = _cnpj_check_fn(b)
    s = ''.join(map(str, b + d))
    casos.append(f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}")
casos += ["", "1", "12345", "11.222.333/0001-81", "11.222.333/0001-99",
          "11222333000181", "00.000.000/0000-00", "abc.def.ghi/jklm-no",
          "11.222.333/0001-81 ", " 11.222.333/0001-81", "1.1.1/1-1"]

print("=" * 92)
print("ADR-0044 — o unificado vs o SPEC_CNPJ historico, no dominio NUMERICO")
print("=" * 92)
dbytes = dstatus = 0
ex = []
for v in casos:
    pa, sa = h_encode(v)
    pb, sb = SPEC_CNPJ.encode_value(v)
    if pa != pb:
        dbytes += 1
        if len(ex) < 5:
            ex.append(("BYTE", v, pa, pb))
    elif sa != sb:
        dstatus += 1
        if len(ex) < 5:
            ex.append(("STATUS", v, sa, sb))
print(f"  encode: {len(casos):,} valores  ->  divergencias de BYTE: {dbytes}  ·  "
      f"de STATUS: {dstatus}")

# decode: payloads de 7 chars, validos e ADULTERADOS
alvos = [h_encode(v)[0] for v in casos[:500]]
alvos += [''.join(rng.choice(BASE94) for _ in range(7)) for _ in range(3000)]
alvos += [BASE94[-1] * 7, BASE94[0] * 7, "_x", "curto", ""]
ddec = 0
for p in alvos:
    if h_decode(p) != SPEC_CNPJ.decode_value(p):
        ddec += 1
        if len(ex) < 8:
            ex.append(("DECODE", p, h_decode(p), SPEC_CNPJ.decode_value(p)))
print(f"  decode: {len(alvos):,} payloads de 7 chars (3.000 adulterados)  ->  "
      f"divergencias: {ddec}")

for tipo, v, a, b in ex:
    print(f"    [{tipo}] {v!r}\n        historico : {a!r}\n        unificado : {b!r}")

# CPF: nao tocado por este weld
dcpf = 0
for _ in range(2000):
    b = [rng.randint(0, 9) for _ in range(9)]
    d = SPEC_CPF.check_fn(b)
    s = ''.join(map(str, b + d))
    v = f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"
    if len(SPEC_CPF.encode_value(v)[0]) != 5 or SPEC_CPF.decode_value(
            SPEC_CPF.encode_value(v)[0]) != v:
        dcpf += 1
print(f"  CPF (intocado): 2.000 valores, RT e largura 5  ->  divergencias: {dcpf}")

assert dbytes == 0 and ddec == 0 and dstatus == 0 and dcpf == 0, "REPROVADO"
print("\n  => BYTE-NEUTRO no dominio numerico: encode, decode (inclusive adulterado)")
print("     e status. O unificado le' e emite EXATAMENTE o wire `:cnpj` historico.")

"""Piloto H-NAT-SPEC: CPF nas duas vias (normalizar-pipeline vs base94 vs raw).
Read-only. Mede o eixo de COMPRESSAO do fluxo de duas vias em 2 regimes."""
import random
from tcf import encode
from tcf.natures import SPEC_CPF
random.seed(7)

def dvs(b):  # digitos verificadores do CPF (body de 9 digitos)
    def d(ds, w0):
        s = sum(int(x) * w for x, w in zip(ds, range(w0, 1, -1))); r = s % 11
        return '0' if r < 2 else str(11 - r)
    d1 = d(b, 10); return d1 + d(b + d1, 11)

def cpf(b): c = dvs(b); return f"{b[:3]}.{b[3:6]}.{b[6:9]}-{c}"

N = 2000
rb = [''.join(random.choice('0123456789') for _ in range(9)) for _ in range(N)]
sb = [str(100000000 + i) for i in range(N)]          # cadenciado
B = lambda x: len(encode(x).encode('utf-8'))
Bn = lambda x: len(encode(x, nature=SPEC_CPF).encode('utf-8'))
print(f"{'regime':12}{'raw':>9}{'base94':>9}{'9dig-OBAT':>11}{'11dig+DV':>10}")
for lbl, bodies in [("ALEATORIO", rb), ("CADENCIADO", sb)]:
    cpfs = [cpf(b) for b in bodies]
    full = [b + dvs(b) for b in bodies]
    print(f"{lbl:12}{B(cpfs):>9}{Bn(cpfs):>9}{B(bodies):>11}{B(full):>10}")

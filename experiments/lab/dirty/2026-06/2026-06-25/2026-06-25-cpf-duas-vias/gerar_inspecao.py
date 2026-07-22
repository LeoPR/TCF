"""Gera CPFs sinteticos realistas (regiao-ponderada por populacao) + amostra de 50
nos 3 casos do fluxo, pra inspecao. Read-only sobre o TCF (so' encode)."""
import random, gzip
from tcf import encode
from tcf.natures import SPEC_CPF
try:
    import brotli; comp = lambda b: len(brotli.compress(b)); CN = "brotli"
except ImportError:
    comp = lambda b: len(gzip.compress(b, 9)); CN = "gzip"
random.seed(42)

# 9o digito do body = Regiao Fiscal. Peso ~ populacao (milhoes, aprox 2024):
POP = {1: 18.0, 2: 17.2, 3: 19.3, 4: 20.1, 5: 16.3,
       6: 20.5, 7: 20.0, 8: 44.0, 9: 19.0, 0: 10.9}   # 8=SP (maior)
REG, W = list(POP), list(POP.values())

def dvs(b):                       # 2 digitos verificadores (mod-11) do body de 9
    def d(ds, w0):
        s = sum(int(x) * w for x, w in zip(ds, range(w0, 1, -1))); r = s % 11
        return '0' if r < 2 else str(11 - r)
    d1 = d(b, 10); return d1 + d(b + d1, 11)

def gen():                        # body9 = serial(8 uniforme) + regiao(ponderada)
    serial = ''.join(random.choice('0123456789') for _ in range(8))
    region = str(random.choices(REG, weights=W)[0])
    return serial + region
def fmt(b9): return f"{b9[:3]}.{b9[3:6]}.{b9[6:9]}-{dvs(b9)}"

def save(name, text):
    with open(name, "w", encoding="utf-8", newline="") as f:
        f.write(text)
def sz(t): b = t.encode("utf-8"); return len(b), comp(b)

# dataset realista (5000) salvo p/ uso futuro
N = 5000
full = [fmt(gen()) for _ in range(N)]
save("cpfs-sinteticos-realistas.txt", "\n".join(full))

# amostra de 50 (MESMOS 50 nos 3 casos)
random.seed(7)
bodies50 = [gen() for _ in range(50)]
cpfs = [fmt(b) for b in bodies50]
digits = bodies50[:]              # modo-1: normalizado (sem mascara, sem DV)

c1 = encode(cpfs)                 # CASO 1 raw (sem nature)
c2 = encode(cpfs, nature=SPEC_CPF)  # CASO 2 base94 (#TCF.8 single; = no-obat/bypass)
c3 = encode(digits)               # CASO 3 digitos (modo-1 input p/ o OBAT)
save("caso1-raw.tcf.txt", c1)
save("caso2-base94.tcf.txt", c2)
save("caso3-digitos.tcf.txt", c3)

# ilustracao: CPFs CADENCIADOS (NAO realista) -> mostra o seq-RLE no caso digitos
seqb = [str(100000000 + i) for i in range(50)]
save("caso3b-digitos-cadenciado.tcf.txt", encode(seqb))

print(f"DATASET realista: {N} CPFs -> cpfs-sinteticos-realistas.txt")
print(f"AMOSTRA 50 CPFs realistas (single-col; brotli = regua p/ 1-coluna-sem-lazy):")
for lbl, t in [("1 raw", c1), ("2 base94", c2), ("3 digitos", c3)]:
    b, cb = sz(t); print(f"  caso {lbl:10} textual={b:5}  {CN}={cb:4}")
print(f"  (ilustr) 3b cadenciado textual={len(encode(seqb).encode()):5}  -> seq-RLE")

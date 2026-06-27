"""EI (escape-invertido) GLOBAL - prototipo pos-filtro + medicao de ALCANCE.
Pergunta: a estrutura "ideal" (flip global) tem alcance? (a) varios formatos
digit-heavy; (b) sobrevive ao brotli ou so' regime textual/lazy?
Read-only sobre o TCF (so' encode + transform de texto). Pos-filtro = nao toca o core."""
import re, random, gzip, csv, glob, os
from tcf import encode
try:
    import brotli
    bz = lambda b: len(brotli.compress(b))
    CN = "brotli"
except ImportError:
    bz = lambda b: len(gzip.compress(b, 9))
    CN = "gzip"

HDR = "#TCF.8 EI\n"
_strip = re.compile(r"\\(\d)")        # '\' antes de digito (escape literal)
_readd = re.compile(r"(\d+)")          # digit-run -> re-escapa


def ei_measure(values):
    out = encode(values)
    ei = _strip.sub(r"\1", out)                       # remove os '\' de digito
    safe = (_readd.sub(r"\\\1", ei) == out)           # all-literal -> reversivel
    bo = out.encode("utf-8")
    be = (HDR + ei).encode("utf-8")
    return {
        "safe": safe, "n": len(values),
        "txt_out": len(bo), "txt_gain": 100 * (len(bo) - len(be)) / len(bo),
        "br_out": bz(bo), "br_gain": 100 * (bz(bo) - bz(be)) / bz(bo),
        "n_esc": out.count("\\"),
    }


# ---- geradores realistas digit-heavy ----
random.seed(11)
DIG = "0123456789"


def cpf():
    POP = {1: 18, 2: 17, 3: 19, 4: 20, 5: 16, 6: 20, 7: 20, 8: 44, 9: 19, 0: 11}
    R, W = list(POP), list(POP.values())

    def dv(b):
        def d(ds, w0):
            r = sum(int(x) * w for x, w in zip(ds, range(w0, 1, -1))) % 11
            return "0" if r < 2 else str(11 - r)
        d1 = d(b, 10)
        return d1 + d(b + d1, 11)

    b = "".join(random.choice(DIG) for _ in range(8)) + str(random.choices(R, weights=W)[0])
    return f"{b[:3]}.{b[3:6]}.{b[6:9]}-{dv(b)}"


def rnd_num(w):
    return "".join(random.choice(DIG) for _ in range(w))


def date_rand():
    return f"{random.randint(1950, 2025)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"


def date_seq(i):
    return f"2026-{1 + (i // 28) % 12:02d}-{1 + i % 28:02d}"


def phone():
    return f"({random.randint(11, 99)}) 9{rnd_num(4)}-{rnd_num(4)}"


def nfe(i):
    return f"NFe-2026-{i:06d}"


N = 1000
GER = {
    "cpf-regiao (aleatorio)":     [cpf() for _ in range(N)],
    "id-num-9 (aleatorio)":       [rnd_num(9) for _ in range(N)],
    "id-num-16 (aleatorio)":      [rnd_num(16) for _ in range(N)],
    "data (aleatoria)":           [date_rand() for _ in range(N)],
    "data (sequencial)":          [date_seq(i) for i in range(N)],
    "telefone (aleatorio)":       [phone() for _ in range(N)],
    "nfe-seq (formatado-seq)":    [nfe(i) for i in range(N)],
    "decimal (aleatorio)":        [f"{random.randint(0, 99999)}.{rnd_num(2)}" for _ in range(N)],
}
# + colunas digit-heavy dos sinteticos
seen = set()
for path in sorted(glob.glob("datasets/synthetic/D1[1346]*.csv")):
    if path in seen:
        continue
    seen.add(path)
    try:
        with open(path, encoding="utf-8") as f:
            r = csv.reader(f)
            hdr = next(r)
            rows = list(r)
    except Exception:
        continue
    for ci, h in enumerate(hdr):
        col = [row[ci] for row in rows if ci < len(row)]
        if col and sum(c.isdigit() for v in col[:5] for c in v) >= 5:
            GER[f"{os.path.basename(path)[:13]}:{h[:9]}"] = col

print(f"compressor de referencia: {CN}\n")
print(f"{'coluna':33}{'n':>5}{'esc':>7}{'safe':>6}{'txt-gain':>10}{CN + '-gain':>12}")
print("-" * 73)
for name, vals in GER.items():
    m = ei_measure(vals)
    print(f"{name:33}{m['n']:>5}{m['n_esc']:>7}{('SIM' if m['safe'] else '-'):>6}"
          f"{m['txt_gain']:>9.1f}%{m['br_gain']:>11.1f}%")

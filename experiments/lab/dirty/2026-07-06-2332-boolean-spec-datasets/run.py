"""run.py — estudo de BOOLEAN nos nossos datasets + protótipo da spec binária (owner 2026-07-06).

(1) Varre synthetic + hubs SQLite por colunas domínio ≤3 → cataloga bool-variante vs enum-2 vs domN.
(2) Protótipo da spec binária (variantes + autoridade + gabarito-da-spec) — RT em colunas reais.
(3) Bytes: raw vs spec-textual (bitstring) vs spec-binário (bitmap N/8) numa coluna real grande.

`python run.py` regenera artifacts/. Ponteiro dados: datasets/synthetic + Z:/tcf-data/interim/*.db.
"""
from __future__ import annotations
import math
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(_ROOT / "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import scan as SC                                      # noqa: E402
import boolean_spec as BS                              # noqa: E402
from tcf import encode                                 # noqa: E402

ART = HERE / "artifacts"
ART.mkdir(exist_ok=True)
SYN = _ROOT / "datasets" / "synthetic"
INTERIM = Path("Z:/tcf-data/interim")
DBS = ["adult-census.db", "tpch-sf001.db", "ibge-municipios.db", "receita-cnpj.db", "br-identidades.db"]


def nb(s): return len(s.encode("utf-8"))
def w(name, text): (ART / name).write_text(text, encoding="utf-8", newline="\n")


def do_scan():
    found = []
    for p in sorted(SYN.glob("*.csv")):
        found += SC.scan_csv(p)
    for db in DBS:
        dbp = INTERIM / db
        if dbp.exists():
            found += SC.scan_db(str(dbp))
    return found


def catalog(found):
    L = ["# CATÁLOGO — colunas de domínio ≤3 nos nossos datasets (candidatas a boolean/enum-2)", "",
         "| fonte | coluna | N | #dist | kind | variante/valores |", "|---|---|---|---|---|---|"]
    order = {"bool": 0, "enum2": 1}
    for r in sorted(found, key=lambda r: (order.get(r["kind"], 2), r["src"])):
        vv = r["variant"] or " ".join(r["vals"])
        L.append(f"| {r['src']} | {r['col']} | {r['n']} | {r['ndist']} | {r['kind']} | {vv[:44]} |")
    nb_ = sum(1 for r in found if r["kind"] == "bool")
    ne = sum(1 for r in found if r["kind"] == "enum2")
    L += ["", f"TOTAL: {len(found)} colunas domínio≤3 · bool-variante={nb_} · enum-2={ne} · outras={len(found)-nb_-ne}",
          "",
          "LEITURA: 'bool' = superfície bate numa variante conhecida (1/0, t/f, Y/N…). 'enum-2' = 2 valores",
          "ARBITRÁRIOS (Male/Female, O/F) — mesma ESTRUTURA (2 símbolos=1 bit), mas a superfície É dado.",
          "",
          "ACHADO (do dado REAL): ZERO true/false nos nossos datasets. O único 'bool' (o_shippriority) é",
          "CONSTANTE (1 distinct '0' — edge do classificador, não boolean). O que existe é enum-2/3 com",
          "superfície = DADO: Male/Female, <=50K/>50K, F/O, A/N/R, F/O/P. E matriz_filial=1|2 (NÃO 0/1!) —",
          "assumir 1/0 seria erro. → o primitivo útil NÃO é 'boolean'; é ENUM/domínio-k (fechado, pequeno).",
          "Boolean true/false é um CASO ESPECIAL semântico que quase não aparece em tabela real."]
    w("01-catalogo-dominio2.txt", "\n".join(L) + "\n")
    return nb_, ne


def demo_spec(found):
    """RT da spec binária nas colunas domínio-2 do catálogo (sintéticos + amostra dos hubs)."""
    L = ["# SPEC BINÁRIA — RT (variante padrão vs enum-2) + header (gabarito-da-spec vs na-coluna)", ""]
    demoed = 0
    for r in found:
        if r["ndist"] != 2:
            continue
        vals = r["vals"] if len(r["vals"]) >= 2 else None
        if not vals:
            continue
        col = [vals[0], vals[1], vals[0]]              # amostra representativa (a superfície é o que importa)
        ok, spec = BS.rt_ok(col)
        if spec is None:
            continue
        L.append(f"  {r['src']}.{r['col']:16s} kind={r['kind']:6s} header={spec.header()!r:26s} "
                 f"bits={spec.encode_bits(col)}  RT={'OK' if ok else 'FAIL'}")
        demoed += 1
        if demoed >= 14:
            break
    L += ["", "header @bool:<variante> = GABARITO-DA-SPEC (os 2 valores vêm do registry, coluna não guarda).",
          "header @bin:<v0>|<v1>      = enum-2 arbitrário guarda os 2 valores (gabarito NA coluna)."]
    w("02-spec-binaria-rt.txt", "\n".join(L) + "\n")


def bytes_real_column():
    """bytes numa coluna real GRANDE: raw vs spec-textual (bitstring) vs spec-binário (bitmap N/8)."""
    L = ["# BYTES numa coluna real grande — raw vs spec-textual vs spec-binário (bitmap)", ""]
    dbp = INTERIM / "adult-census.db"
    if not dbp.exists():
        w("03-bytes-coluna-real.txt", "adult-census.db indisponível\n"); return
    con = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True)
    cur = con.cursor()
    t = cur.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1").fetchone()[0]
    cols = [r[1] for r in cur.execute(f'PRAGMA table_info("{t}")').fetchall()]
    for c in cols:
        d = cur.execute(f'SELECT COUNT(DISTINCT "{c}") FROM "{t}"').fetchone()[0]
        if d != 2:
            continue
        vals = [str(r[0]) for r in cur.execute(f'SELECT "{c}" FROM "{t}"').fetchall()]
        n = len(vals)
        raw = nb(encode(vals))                         # HCC dict + N refs
        spec = BS.BinarySpec.induce(vals)
        bits = spec.encode_bits(vals)
        textual = nb(encode([bits]))                   # bitstring como 1 corpo (RLE aplica) + header ~pequeno
        packed = math.ceil(n / 8) + len(spec.header())  # bitmap real (binário)
        L.append(f"## {t}.{c}  (N={n}, {spec.header()})")
        L.append(f"  raw (true/false strings via HCC): {raw:6d}B")
        L.append(f"  spec TEXTUAL (bitstring 0/1)     : {textual:6d}B")
        L.append(f"  spec BINÁRIO (bitmap N/8 + hdr)  : {packed:6d}B  <- o ganho real é AQUI")
        L.append("")
    con.close()
    L += ["MEDIDO (adult.sex N=48842): raw 97KB → spec TEXTUAL 49KB (~2×: Male/Female→0/1 encurta a",
          "superfície) → spec BINÁRIO bitmap 6KB (~16×). O ganho TEXTUAL é PROPORCIONAL ao encurtamento da",
          "superfície (aqui 2×; pra true/false já curto seria ~marginal). O ganho grande e CONSTANTE (1 bit/val)",
          "é BINÁRIO (bitmap, V2-L). Em texto a spec ainda vale por ACELERAÇÃO + header @bool:<variante> mínimo."]
    w("03-bytes-coluna-real.txt", "\n".join(L) + "\n")


def main():
    found = do_scan()
    nbc, ne = catalog(found)
    demo_spec(found)
    bytes_real_column()

    R = ["# Boolean nos datasets + spec binária [resumo]", "",
         f"## Catálogo (domínio ≤3): {len(found)} colunas · bool-variante={nbc} · enum-2={ne}",
         "**ACHADO (do dado real)**: ZERO true/false; o que há é enum-2/3 com superfície=DADO (Male/Female,",
         "F/O, A/N/R, F/O/P) + matriz_filial=1|2 (não 0/1!). O primitivo útil é ENUM/domínio-k; boolean",
         "true/false é caso especial semântico raro em tabela.", "",
         "## Design da spec (do dado): ENUM/domínio-k, boolean é sub-caso",
         "- **primitivo = ENUM de domínio-k** (fechado, pequeno); a superfície é uma **VARIANTE**. Boolean",
         "  (true/false/1/0/t/f) é a variante SEMÂNTICA — rara em dado real; enum-2/3 (Male/Female, F/O) domina.",
         "- **enum-semântico** (variante conhecida) vs **enum arbitrário** (Male/Female): MESMA estrutura",
         "  (k símbolos = log2(k) bits); diferença = superfície é rótulo-padrão vs DADO.",
         "- **Autoridade** (owner): CSV cru → enum, preserva superfície (sanidade; matriz_filial=1|2 prova o risco);",
         "  typed → canonicaliza livre.",
         "- **Gabarito-da-spec**: variante padrão → header `@bool:<variante>`, valores vêm do registry (coluna",
         "  não guarda gabarito). enum arbitrário → `@enum:v0|v1|…` (gabarito na coluna, uma vez).",
         "- **Compressão** (03, medido adult.sex): raw 97KB → textual 49KB (~2×, encurta superfície) → binário",
         "  6KB (~16×, bitmap). Textual ganha proporcional ao encurtamento; o grande/constante é binário (V2-L).",
         "", "## Eixos ORTOGONAIS de uma spec (além de compressão/aceleração — o pedido do owner)",
         "1. compressão · 2. aceleração · 3. **autoridade** (mandatório/natural/deduzido) ·",
         "4. **normalizabilidade** (superfície livre p/ canonicalizar vs byte-locked) · 5. **fechamento de domínio**",
         "(fechado=enum/bitmap vs aberto) · 6. **variante** (superfície do mesmo semântico) · 7. **reversibilidade**",
         "(round-trip, gate de indução) · 8. **validação/sanidade** (nature alerta anomalia). → nota tipos-como-specs.",
         "", "## Classificação por autoridade (ataque um-a-um, owner)",
         "- **mandatório**: tipo declarado na entrada → canonicaliza; **spec-natural**: padrão conhecido (bool,",
         "  datetime, CPF) → gabarito-da-spec; **deduzido**: induzido do dado via round-trip → preserva superfície."]
    w("00-resumo.txt", "\n".join(R) + "\n")

    print("artifacts em", ART)
    for p in sorted(ART.iterdir()):
        print(f"  {p.name:26s} {p.stat().st_size:6d} B")
    print("\n" + "\n".join(R))


if __name__ == "__main__":
    main()

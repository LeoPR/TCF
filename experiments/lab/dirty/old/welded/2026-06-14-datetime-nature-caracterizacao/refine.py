"""H-STRUCT-01 — refinamento antes do weld (pedido do owner).

Responde 4 perguntas de desenho:
A. COBERTURA/robustez: quantas colunas reais sao split-eligiveis (template
   uniforme)? E quantas sao "near-miss" (1 template domina 90-99.9%, mas ha'
   excecoes) -> precisariam de mecanismo de excecao?
B. BREAKDOWN por tipo: quanto do ganho e' decimal (`.`) vs data vs id?
C. OVERLAP com natures CPF/CNPJ (ADR-0015): split generico subsume ou complementa?
D. BORDAS: negativos, vazios, estrutura mista -> o detector faz o seguro?

FORK exploratorio — NAO toca src/tcf.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, SPEC_CPF, SPEC_CNPJ  # noqa: E402

EXT = Path("Z:/tcf-data/external")
ROWS = 5000
_DIGITS = re.compile(r"(\d+)")


def load(path, limit):
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f)
                header = next(r)
                cols = {h: [] for h in header}
                for n, row in enumerate(r):
                    if n >= limit:
                        break
                    if len(row) != len(header):
                        continue
                    for h, v in zip(header, row):
                        cols[h].append(v)
            return cols
        except UnicodeDecodeError:
            continue
    return {}


def signature(v):
    """template-signature de um valor = tupla das partes nao-digito."""
    parts = _DIGITS.split(v)
    return tuple(parts[::2]), (len(parts) // 2)


def nbytes(s):
    return len(s.encode("utf-8"))


def split_by_sig(values, sig, nfields):
    """split assumindo o template `sig`; valores fora viram None (excecao)."""
    fields = [[] for _ in range(nfields)]
    keep_idx = []
    for i, v in enumerate(values):
        parts = _DIGITS.split(v)
        if tuple(parts[::2]) == sig and len(parts) // 2 == nfields:
            for fi in range(nfields):
                fields[fi].append(parts[1 + 2 * fi])
            keep_idx.append(i)
    return fields, keep_idx


def kind(sig):
    t = "".join(sig)
    if t == ".":
        return "decimal"
    if any(c in t for c in "-/:") or " " in t:
        return "date/dt"
    return "id/other"


DATASETS = ["adult-census/adult.csv", "online-retail/online_retail.csv",
            "tpch-sf001/lineitem.csv", "br-identidades/pessoas.csv",
            "receita-cnpj/estabelecimentos.csv", "ibge-municipios/municipios.csv",
            "beijing-pm25/beijing_pm25.csv", "wine-quality/wine.csv"]


def main():
    print(f"ROWS={ROWS}\n=== A. COBERTURA do detector de template (todas as colunas) ===")
    n_total = n_exact = n_near = n_low = n_nostruct = 0
    near_cols = []
    gain_by_kind = Counter()
    base_by_kind = Counter()
    for rel in DATASETS:
        path = EXT / rel
        if not path.exists():
            continue
        label = rel.split("/")[0].split("-")[0]
        cols = load(path, ROWS)
        for c, vals in cols.items():
            if not vals or len(set(vals)) < 3:
                continue
            n_total += 1
            sigs = Counter()
            for v in vals:
                sig, nf = signature(v)
                if nf >= 2:
                    sigs[(sig, nf)] += 1
            if not sigs:
                n_nostruct += 1
                continue
            (dom_sig, dom_nf), dom_cnt = sigs.most_common(1)[0]
            cov = dom_cnt / len(vals)
            if cov >= 0.999:
                n_exact += 1
                # mede ganho (exact -> weldavel hoje)
                base = nbytes(encode(vals))
                fields, _ = split_by_sig(vals, dom_sig, dom_nf)
                if all(len(set(f)) <= 1 for f in fields):
                    continue
                tmpl_cost = nbytes("".join(dom_sig)) + 2 * len(dom_sig)
                v2b = nbytes(encode({f"c{i}": f for i, f in enumerate(fields)})) + tmpl_cost
                k = kind(dom_sig)
                gain_by_kind[k] += max(0, base - v2b)
                base_by_kind[k] += base
            elif cov >= 0.90:
                n_near += 1
                near_cols.append((f"{label}.{c}", cov, "".join(dom_sig)))
            else:
                n_low += 1
    print(f"colunas (>=3 unicos): {n_total}")
    print(f"  exact-uniform (>=99.9%): {n_exact}  <- weldavel hoje (sem excecao)")
    print(f"  near-miss (90-99.9%):    {n_near}   <- precisa mecanismo de excecao")
    print(f"  baixa cobertura (<90%):  {n_low}")
    print(f"  sem estrutura digito:    {n_nostruct}")
    if near_cols:
        print("  near-miss detalhe:")
        for name, cov, t in near_cols[:12]:
            print(f"    {name:28.28s} cov={cov*100:5.1f}% tmpl={t!r}")

    print("\n=== B. BREAKDOWN do ganho por tipo (exact-uniform) ===")
    for k in ("decimal", "date/dt", "id/other"):
        b = base_by_kind[k]
        g = gain_by_kind[k]
        pct = 100 * g / b if b else 0
        print(f"  {k:10s}: gain={g:7d}  base={b:8d}  ({pct:.1f}% das do tipo)")
    tg = sum(gain_by_kind.values())
    print(f"  TOTAL gain (exact): {tg}")

    print("\n=== C. OVERLAP com natures CPF/CNPJ (ADR-0015) ===")
    brp = load(EXT / "br-identidades/pessoas.csv", ROWS)
    rec = load(EXT / "receita-cnpj/estabelecimentos.csv", ROWS)
    for name, vals, spec in [("br.cpf", brp.get("cpf"), SPEC_CPF),
                             ("receita.cnpj", rec.get("cnpj"), SPEC_CNPJ)]:
        if not vals:
            print(f"  {name}: SKIP")
            continue
        base = nbytes(encode(vals))
        try:
            nat = nbytes(encode(vals, nature=spec))
        except Exception as e:
            nat = None
            nat_err = f"{type(e).__name__}: {e}"
        sig, nf = signature(vals[0])
        fields, _ = split_by_sig(vals, sig, nf)
        tmpl_cost = nbytes("".join(sig)) + 2 * len(sig)
        spl = nbytes(encode({f"c{i}": f for i, f in enumerate(fields)})) + tmpl_cost
        natdisp = str(nat) if nat is not None else f"ERRO({nat_err})"
        print(f"  {name:14s} base={base:6d}  nature={natdisp:>8s}  split={spl:6d}")

    print("\n=== D. BORDAS (detector faz o seguro?) ===")
    cases = {
        "negativos": ["-1.5", "-2.7", "-3.9", "-1.5"],
        "sinais mistos": ["-1.5", "2.7", "-3.9", "4.1"],
        "vazios mistos": ["1.5", "", "2.7", ""],
        "estrutura mista": ["1.5", "12.34.56", "2.7", "8"],
        "zero-pad": ["01.02", "03.04", "05.06"],
        "datas ok": ["2010-01-02", "2011-03-04", "2012-05-06"],
    }
    for nm, vals in cases.items():
        sigs = Counter()
        for v in vals:
            sig, nf = signature(v)
            sigs[(sig, nf)] += 1
        (dsig, dnf), dcnt = sigs.most_common(1)[0]
        cov = dcnt / len(vals)
        fields, keep = split_by_sig(vals, dsig, dnf)
        # RT dos que casam
        rt = True
        for j, i in enumerate(keep):
            rec_v = "".join(dsig[fi] + fields[fi][j] for fi in range(dnf)) + dsig[dnf]
            if rec_v != vals[i]:
                rt = False
        print(f"  {nm:16s} domTmpl={''.join(dsig)!r:12s} cov={cov*100:5.0f}% "
              f"nf={dnf} RT_casados={'OK' if rt else 'X'}")


if __name__ == "__main__":
    main()

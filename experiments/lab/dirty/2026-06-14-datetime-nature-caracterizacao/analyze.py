"""datetime-nature (Pacote 9, H-DT-01) — caracterizacao do split estrutural.

Sinal do V2-D: colunas DATETIME ganham (InvoiceDate 15%) porque o afixo longo do
timestamp escapa do OBAT. Hipotese: um encoder estrutural (split em campos) ganha
MUITO mais, porque divide 1 coluna high-card em N colunas low-card — e cada campo
low-card e' exatamente o que o V2-B esmaga.

Split GENERICO (format-agnostic): tokeniza cada valor em runs de DIGITOS vs
NAO-digitos. Se todos os valores tem o MESMO template (mesmos separadores, mesma
contagem de campos), os grupos de digitos viram colunas-campo e o template e'
guardado 1x. Generaliza datas, horas, datetimes, CPF, telefone, CEP...

  base       = encode(values)                          # OBAT atual (1 coluna)
  fields_sc  = sum encode(campo_i) single-col + tmpl   # campos isolados
  fields_v2b = encode({campo_i: ...}) multi-col + tmpl # campos COM V2-B (sinergia)
  + RT: template + campos reconstroi os valores

FORK exploratorio — NAO toca src/tcf.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402

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


def split_struct(values):
    """(template, fields) ou None se a estrutura nao for uniforme.
    template = lista de partes nao-digito; fields = lista de colunas (digit groups).
    """
    toks = [_DIGITS.split(v) for v in values]   # ['', '2010', '-', '12', ...]
    L = len(toks[0])
    if L < 3:
        return None  # sem grupo de digito util
    template = toks[0][::2]
    n_fields = L // 2
    if n_fields < 2:
        return None  # 1 campo so' -> nada a ganhar com split
    for t in toks:
        if len(t) != L or t[::2] != template:
            return None  # estrutura nao-uniforme
    fields = [[t[1 + 2 * fi] for t in toks] for fi in range(n_fields)]
    return template, fields


def reconstruct(template, fields):
    out = []
    n = len(fields[0])
    for i in range(n):
        parts = []
        for fi in range(len(fields)):
            parts.append(template[fi])
            parts.append(fields[fi][i])
        parts.append(template[len(fields)])
        out.append("".join(parts))
    return out


def nbytes(s):
    return len(s.encode("utf-8"))


DATASETS = ["adult-census/adult.csv", "online-retail/online_retail.csv",
            "tpch-sf001/lineitem.csv", "br-identidades/pessoas.csv",
            "receita-cnpj/estabelecimentos.csv", "ibge-municipios/municipios.csv",
            "beijing-pm25/beijing_pm25.csv", "wine-quality/wine.csv"]


def main():
    print(f"ROWS={ROWS}  (so' colunas com estrutura digito/separador uniforme, >=2 campos)\n")
    print(f"{'dataset.col':30s} {'base':>7s} {'fldSC':>7s} {'fldV2B':>7s} "
          f"{'bestGain':>8s} {'%':>6s} {'tmpl':>16s} {'RT':>3s}")
    print("-" * 92)
    tot_base = tot_best = tot_base_all = 0
    any_rt_fail = False
    for rel in DATASETS:
        path = EXT / rel
        if not path.exists():
            continue
        label = rel.split("/")[0].split("-")[0]
        cols = load(path, ROWS)
        for c, vals in cols.items():
            if not vals or len(set(vals)) < 3:
                continue
            base = nbytes(encode(vals))
            tot_base_all += base
            sp = split_struct(vals)
            if sp is None:
                continue
            template, fields = sp
            # so' interessa quando ha' variacao real nos campos
            if all(len(set(f)) <= 1 for f in fields):
                continue
            rt = reconstruct(template, fields) == vals
            any_rt_fail = any_rt_fail or not rt
            tmpl_cost = nbytes("".join(template)) + 2 * len(template)
            fields_sc = sum(nbytes(encode(f)) for f in fields) + tmpl_cost
            ftable = {f"c{i}": f for i, f in enumerate(fields)}
            fields_v2b = nbytes(encode(ftable)) + tmpl_cost
            best = min(fields_sc, fields_v2b)
            gain = base - best
            pct = 100 * gain / base if base else 0
            if abs(gain) < 1:
                continue
            tot_base += base
            tot_best += best
            mark = " <<" if pct >= 5 else (" REG" if gain < 0 else "")
            tdisp = repr("".join(template))[:16]
            print(f"{label+'.'+c:30.30s} {base:7d} {fields_sc:7d} {fields_v2b:7d} "
                  f"{gain:8d} {pct:5.1f}% {tdisp:>16s} {'OK' if rt else 'X':>3s}{mark}")
    print("-" * 92)
    print(f"RT: {'OK' if not any_rt_fail else 'FALHOU'}")
    if tot_base:
        print(f"soma base(afetadas)={tot_base}  best={tot_best}  gain={tot_base-tot_best} "
              f"({100*(tot_base-tot_best)/tot_base:.1f}% das afetadas)")
        print(f"weighted sobre TODAS as colunas: "
              f"{100*(tot_base-tot_best)/tot_base_all:.2f}% (base_all={tot_base_all})")


if __name__ == "__main__":
    main()

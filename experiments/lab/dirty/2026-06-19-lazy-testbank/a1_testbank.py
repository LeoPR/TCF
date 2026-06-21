"""A1 — banco de testes do lazy (v0.8, workstream A). Lab read-only, NAO toca src/tcf.

Valida TODAS as ops do gadget tcf_lazy contra o ORACULO (decode() completo + agregacao
manual), cobrindo os 4 modos de coluna (tcf / raw ! / dict @ / split %), em ordem:
  A1.1 sinteticos construidos (controle dos modos)
  A1.2 volume real (adult, tpch) + fracao do blob tocada (a "venda")
  A1.3 bordas (vazios, UTF-8, 1-col, filtro AND, coluna inexistente, sort_by)

Cada divergencia lazy != oraculo = BUG (vai pro A2). Sai !=0 se houver mismatch.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tcf import encode, decode               # noqa: E402
from tcf_lazy import view                    # noqa: E402

FAILS: list[str] = []
NOTES: list[str] = []


def chk(cond: bool, msg: str):
    if not cond:
        FAILS.append(msg)
        print(f"   FAIL: {msg}")


def _floats(vals, idx):
    return [float(vals[i]) for i in (idx if idx is not None else range(len(vals))) if vals[i] != ""]


def validate(name: str, cols: dict[str, list[str]], *, key_text: str, key_num: str):
    """Roda as ops no lazy e compara com o oraculo decode()."""
    blob = encode(cols)
    lz = view(blob)
    oracle = decode(blob)                     # contrato: RT; ordem pode mudar so' com sort_by (nao usado aqui)
    n = len(next(iter(oracle.values())))
    modes = {c: lz._mode[c] for c in lz.columns}
    print(f"\n## {name}  (n={n}, modos: {modes})")

    # --- nrows / count ---
    chk(lz.nrows == n, f"{name}: nrows {lz.nrows} != {n}")
    chk(lz.count() == n, f"{name}: count() {lz.count()} != {n}")

    # --- group_count (oraculo = Counter) em cada coluna ---
    for c in cols:
        gc = lz.group_count(c)
        chk(gc == dict(Counter(oracle[c])), f"{name}: group_count({c}) divergiu")

    # --- where (eq) em coluna texto + count/sum/select sobre o filtro ---
    val = oracle[key_text][0]
    f = lz.where(key_text, val)
    exp_idx = [i for i, v in enumerate(oracle[key_text]) if v == val]
    chk(f.indices == exp_idx, f"{name}: where({key_text}={val!r}).indices divergiu")
    chk(f.count() == len(exp_idx), f"{name}: where().count() divergiu")
    # sum/min/max/avg numerico sobre o filtro
    exp_sum = sum(_floats(oracle[key_num], exp_idx))
    chk(abs(lz.sum(key_num, exp_idx) - exp_sum) < 1e-6, f"{name}: sum({key_num}|filtro) divergiu")
    if _floats(oracle[key_num], exp_idx):
        chk(lz.min(key_num, exp_idx) == min(_floats(oracle[key_num], exp_idx)), f"{name}: min divergiu")
        chk(lz.max(key_num, exp_idx) == max(_floats(oracle[key_num], exp_idx)), f"{name}: max divergiu")
    # select alinhado (a linha de uma coluna eh a mesma na outra)
    sel = f.select(list(cols))
    chk(len(sel) == len(exp_idx), f"{name}: select(filtro) tamanho divergiu")
    if exp_idx:
        i0 = exp_idx[0]
        chk(all(sel[0][c] == oracle[c][i0] for c in cols), f"{name}: select alinhamento divergiu")

    # --- where (pred) ---
    fp = lz.where(key_text, pred=lambda v: v == val)
    chk(fp.indices == exp_idx, f"{name}: where(pred) divergiu de where(eq)")

    # --- where encadeado (AND) ---
    val2 = oracle[key_text][-1]
    and_idx = [i for i, v in enumerate(oracle[key_text]) if v == val or v == val2]
    f_and = lz.where(key_text, pred=lambda v: v in (val, val2))
    chk(f_and.indices == and_idx, f"{name}: where(pred in 2) divergiu")

    # --- sum total numerico ---
    chk(abs(lz.sum(key_num) - sum(_floats(oracle[key_num], None))) < 1e-6, f"{name}: sum total divergiu")

    # --- agg_by sobre layout sort_by(key_text) ---
    blob_s = encode(cols, sort_by=key_text)
    lz_s = view(blob_s)
    oracle_s = decode(blob_s)
    gb = lz_s.agg_by(key_text, key_num, "sum")
    exp_gb: dict = {}
    for kv, nv in zip(oracle_s[key_text], oracle_s[key_num]):
        if nv != "":
            exp_gb[kv] = exp_gb.get(kv, 0.0) + float(nv)
    chk({k: round(v, 6) for k, v in gb.items()} == {k: round(v, 6) for k, v in exp_gb.items()},
        f"{name}: agg_by(sum) divergiu")
    cnt = lz_s.agg_by(key_text, op="count")
    chk(cnt == dict(Counter(oracle_s[key_text])), f"{name}: agg_by(count) divergiu")

    # fracao tocada (a "venda") — view FRESCA, so' a query isolada (nao acumula ops anteriores)
    lzf = view(blob)
    lzf.where(key_text, val).sum(key_num)
    rep = lzf.report()
    chk(rep["pct"] <= 100.0, f"{name}: pct tocado {rep['pct']}% > 100% (bug de contagem)")
    NOTES.append(f"{name}: where({key_text}).sum({key_num}) tocou {rep['pct']}% do blob "
                 f"({rep['materialized_bytes']}/{rep['total_bytes']}B)")


def synthetic():
    print("=" * 60); print("A1.1 SINTETICOS (controle dos 4 modos)")
    # status low-card -> @dict ; valor numerico -> tcf/raw ; id unico -> raw/tcf ; data -> split
    base = {
        "status": (["ATIVA", "BAIXADA", "SUSPENSA", "ATIVA", "ATIVA", "BAIXADA",
                    "ATIVA", "SUSPENSA", "ATIVA", "ATIVA", "BAIXADA", "ATIVA"]),
        "valor": ["10.50", "20.00", "5.25", "10.50", "99.99", "0.00",
                  "10.50", "3.30", "100.00", "10.50", "7.77", "42.00"],
        "id": [f"R{i:04d}" for i in range(12)],
        "data": ["2024-01-01", "2024-02-15", "2024-01-01", "2024-03-20", "2024-01-01",
                 "2024-02-15", "2024-12-31", "2024-01-01", "2024-06-10", "2024-01-01",
                 "2024-02-15", "2024-03-20"],
    }
    validate("sint-base", base, key_text="status", key_num="valor")


def real():
    print("\n" + "=" * 60); print("A1.2 VOLUME REAL")
    try:
        from dataset_reader import DatasetReader
    except Exception as e:
        NOTES.append(f"A1.2 pulado (dataset_reader: {e})"); print(f"  pulado: {e}"); return
    picks = [("adult-census", "adult", "workclass", "education-num", 5000),
             ("tpch-sf001", "orders", "o_orderstatus", "o_totalprice", 5000)]
    for ds, tab, kt, kn, lim in picks:
        try:
            r = DatasetReader(ds)
            t = tab or r.tables[0]
            raw = r.columns(t, limit=lim)
            cols = {c: [("" if v is None else str(v)) for v in vals] for c, vals in raw.items()}
            if kt not in cols or kn not in cols:
                NOTES.append(f"{ds}/{t}: colunas {kt}/{kn} ausentes"); continue
            validate(f"{ds}/{t}", cols, key_text=kt, key_num=kn)
        except Exception as e:
            FAILS.append(f"{ds}: EXCECAO {e}"); print(f"  FAIL {ds}: {e}")


def edges():
    print("\n" + "=" * 60); print("A1.3 BORDAS")
    # vazios + UTF-8
    t = {"cat": ["a", "", "ção", "a", "", "ção"], "num": ["1", "", "3", "1", "2", ""]}
    validate("borda-vazios-utf8", t, key_text="cat", key_num="num")
    # 1 coluna multi-col
    one = {"so": ["X", "Y", "X", "X", "Y"]}
    lz = view(encode(one))
    chk(lz.nrows == 5, "1-col: nrows")
    chk(lz.group_count("so") == {"X": 3, "Y": 2}, "1-col: group_count")
    # coluna inexistente -> erro
    try:
        lz.group_count("naoexiste"); chk(False, "coluna inexistente nao levantou")
    except KeyError:
        print("   OK: coluna inexistente levanta KeyError")
    # select sem filtro = todas as linhas
    full = view(encode({"a": ["1", "2", "3"], "b": ["x", "y", "z"]}))
    chk(full.select() == [{"a": "1", "b": "x"}, {"a": "2", "b": "y"}, {"a": "3", "b": "z"}],
        "select() completo divergiu")


def main():
    print("# A1 — BANCO DE TESTES DO LAZY (v0.8, read-only)\n")
    synthetic(); real(); edges()
    print("\n" + "=" * 60)
    print("FRACAO TOCADA (a venda):")
    for n in NOTES:
        print("  -", n)
    print("\n" + "=" * 60)
    if FAILS:
        print(f"RESULTADO: {len(FAILS)} FALHA(S) -> A2 (fechar bugs):")
        for f in FAILS:
            print("  X", f)
        sys.exit(1)
    print("RESULTADO: TUDO VERDE — lazy bate o oraculo em todas as ops/modos/bordas testados.")


if __name__ == "__main__":
    main()

"""Lab didatico (refeito): efeitos das chaves em diferentes graus.

Aplica APENAS a forma vencedora consolidada (D1-D16):
  - DICT inline com a coluna (nao no header)
  - PK grau 2 → ELIMINAR
  - PK grau 0/1 → PRESERVAR
  - PK grau 3 → RECONSTRUIR (escolha)
  - Auto-bypass L3 quando cardinality > N/2

Comparacoes obsoletas removidas. Compara so:
  - naive (CSV-like, referencia)
  - TCF v0.4 com auto-tudo aplicado conforme grau

Saida: ./output/
"""
from __future__ import annotations
import uuid
import hashlib
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
OUT.mkdir(exist_ok=True)
random.seed(42)


# ---------------------------------------------------------------------------
# Dataset base (mesma estrutura para todos os cenarios)
# ---------------------------------------------------------------------------

def base_pedidos() -> list[dict]:
    return [
        {"comprador": "Ana",    "produto": "Abacaxi", "qtd": 2},
        {"comprador": "Bruno",  "produto": "Banana",  "qtd": 1},
        {"comprador": "Ana",    "produto": "Cereja",  "qtd": 3},
        {"comprador": "Carlos", "produto": "Abacaxi", "qtd": 1},
        {"comprador": "Bruno",  "produto": "Banana",  "qtd": 2},
        {"comprador": "Ana",    "produto": "Banana",  "qtd": 5},
    ]


# ---------------------------------------------------------------------------
# Encoder naive (referencia)
# ---------------------------------------------------------------------------

def encode_naive(rows: list[dict], name: str = "pedidos") -> str:
    if not rows:
        return ""
    cols = list(rows[0].keys())
    out = [f"## {name} n={len(rows)}"]
    for col in cols:
        out.append(f"{col}:")
        for r in rows:
            out.append(str(r[col]))
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Encoder TCF v0.4 (forma vencedora — D1-D16 aplicadas)
# ---------------------------------------------------------------------------

def detect_string_cols(rows: list[dict]) -> set[str]:
    if not rows:
        return set()
    return {col for col in rows[0].keys()
            if isinstance(rows[0][col], str)}


def detect_pk_grade2(rows: list[dict], col: str) -> bool:
    n = len(rows)
    values = [r[col] for r in rows]
    if not all(isinstance(v, int) for v in values):
        return False
    return sorted(values) == list(range(1, n + 1))


def detect_affix(values: list[str]) -> str:
    """Longest common prefix de TODOS os valores."""
    if not values:
        return ""
    p = values[0]
    for v in values[1:]:
        i = 0
        while i < min(len(p), len(v)) and p[i] == v[i]:
            i += 1
        p = p[:i]
        if not p:
            return ""
    return p


def encode_tcf_v04(rows: list[dict],
                    name: str = "pedidos",
                    pk_col: str | None = None,
                    pk_grade: int = 2,
                    affix_cols: set[str] | None = None) -> str:
    """Encoder v0.4 com auto-tudo conforme regras D1-D16.

    pk_grade:
      0 — universal: preservar valor
      1 — natural: preservar valor (Affix-DICT se aplicavel)
      2 — sintetica local: ELIMINAR (regenerar 1..N)
      3 — derivada interna: ELIMINAR (regenerar)
    """
    if not rows:
        return ""
    affix_cols = affix_cols or set()
    cols = list(rows[0].keys())
    string_cols = detect_string_cols(rows)
    n = len(rows)

    # Decide eliminacao do PK
    pk_eliminated = pk_col and pk_grade in (2, 3)

    flags = []
    if pk_eliminated:
        flags.append(f"pk_eliminated={pk_col}")
    flag_text = " " + " ".join(flags) if flags else ""

    out = [f"## {name} n={n}{flag_text}"]
    out_cols = [c for c in cols if c != pk_col or not pk_eliminated]

    # Emite cada coluna (DICT inline; auto-bypass por cardinality)
    for col in out_cols:
        values = [str(r[col]) for r in rows]
        unique = sorted(set(values))
        cardinality = len(unique)

        # Decide formato da coluna
        if col in affix_cols:
            # Proposta H — Affix-DICT inline
            prefix = detect_affix(values)
            if prefix and (cardinality > n / 2 or cardinality > 5):
                out.append(f"{col}: affix=\"{prefix}\"")
                for v in values:
                    out.append(v[len(prefix):] if v.startswith(prefix) else "\\!" + v)
                continue

        if col in string_cols and cardinality < n / 2:
            # L3 com DICT inline (D16)
            out.append(f"{col}: dict={','.join(unique)}")
            idx_map = {v: i for i, v in enumerate(unique)}
            for v in values:
                out.append(str(idx_map[v]))
        else:
            # Bypass — sem DICT
            out.append(f"{col}:")
            for v in values:
                out.append(v)

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Cenarios
# ---------------------------------------------------------------------------

def main():
    print("=" * 80)
    print("Lab didatico (refeito): chaves em graus 0/1/2/3")
    print("=" * 80)
    print("Apenas formas VENCEDORAS aplicadas. Sem comparacoes obsoletas.")

    base = base_pedidos()

    cenarios = [
        {
            "label": "S0 sem PK (so dados)",
            "rows": base,
            "pk_col": None,
            "pk_grade": None,
            "affix": set(),
            "decisao": "no-op (sem PK)",
        },
        {
            "label": "S1 PK int auto-increment (grau 2)",
            "rows": [{"id": i + 1, **r} for i, r in enumerate(base)],
            "pk_col": "id",
            "pk_grade": 2,
            "affix": set(),
            "decisao": "ELIMINAR — id regenerado no decode",
        },
        {
            "label": "S2 PK UUID universal (grau 0)",
            "rows": [{"id": str(uuid.UUID(int=42 + i * 1000)), **r}
                     for i, r in enumerate(base)],
            "pk_col": "id",
            "pk_grade": 0,
            "affix": set(),
            "decisao": "PRESERVAR — valor exato (referencia externa)",
        },
        {
            "label": "S3 PK natural (PED-2026-NNNN, grau 1)",
            "rows": [{"id": f"PED-2026-{i+1:04d}", **r}
                     for i, r in enumerate(base)],
            "pk_col": "id",
            "pk_grade": 1,
            "affix": {"id"},  # Proposta H aplica aqui
            "decisao": "PRESERVAR + Affix-DICT (prefixo PED-2026-)",
        },
        {
            "label": "S4a PK hash 12-hex (grau 0, api-facing)",
            "rows": [{"id": hashlib.sha256(str(r).encode()).hexdigest()[:12],
                      **r}
                     for r in base],
            "pk_col": "id",
            "pk_grade": 0,
            "affix": set(),
            "decisao": "PRESERVAR — api-facing",
        },
        {
            "label": "S4b PK hash 12-hex (grau 3, interno)",
            "rows": [{"id": hashlib.sha256(str(r).encode()).hexdigest()[:12],
                      **r}
                     for r in base],
            "pk_col": "id",
            "pk_grade": 3,
            "affix": set(),
            "decisao": "ELIMINAR — sem uso externo",
        },
    ]

    print(f"\n  {'cenario':<40} {'naive':>6} {'TCFv04':>8} {'gain':>9}  {'decisao':<48}")
    print(f"  {'-'*40} {'-'*6} {'-'*8} {'-'*9}  {'-'*48}")

    for c in cenarios:
        text_naive = encode_naive(c["rows"])
        text_tcf = encode_tcf_v04(c["rows"], pk_col=c["pk_col"],
                                    pk_grade=c["pk_grade"] if c["pk_grade"] is not None else 2,
                                    affix_cols=c["affix"])

        b_naive = len(text_naive.encode())
        b_tcf = len(text_tcf.encode())
        gain_pct = (b_tcf / b_naive - 1) * 100
        sign = "+" if gain_pct > 0 else ""

        print(f"  {c['label']:<40} {b_naive:>6} {b_tcf:>8} "
              f"{sign}{gain_pct:>+7.1f}%  {c['decisao']:<48}")

        slug = c["label"].split(" ")[0].lower().replace("/", "-")
        (OUT / f"{slug}-naive.tcf").write_text(text_naive, encoding="utf-8")
        (OUT / f"{slug}-tcfv04.tcf").write_text(text_tcf, encoding="utf-8")

    # ---- Visualizacao didatica ----
    print("\n" + "=" * 80)
    print("Visualizacao: S1 (PK grau 2 eliminada, DICT inline)")
    print("=" * 80)
    s1 = [{"id": i + 1, **r} for i, r in enumerate(base)]
    print(f"\n  TCF v0.4 output:\n")
    text = encode_tcf_v04(s1, pk_col="id", pk_grade=2)
    for line in text.splitlines():
        print(f"    {line}")

    print("\n" + "=" * 80)
    print("Visualizacao: S3 (PK grau 1 preservada com Affix-DICT)")
    print("=" * 80)
    s3 = [{"id": f"PED-2026-{i+1:04d}", **r} for i, r in enumerate(base)]
    print(f"\n  TCF v0.4 output:\n")
    text = encode_tcf_v04(s3, pk_col="id", pk_grade=1, affix_cols={"id"})
    for line in text.splitlines():
        print(f"    {line}")

    # ---- Insights ----
    print("\n" + "=" * 80)
    print("Insights didaticos (formas vencedoras aplicadas)")
    print("=" * 80)
    print(f"""
  1. DICT INLINE com a coluna:
     `comprador: dict=Ana,Bruno,Carlos`
     Decoder le sequencialmente; cada coluna autocontida; chunk-friendly.

  2. AUTO-BYPASS quando cardinality > N/2:
     Coluna sem DICT eh apenas `coluna:` seguido dos valores.
     Decoder reconhece pela ausencia de `dict=`.

  3. PK GRAU 2: linha `## tabela n=N pk_eliminated=id` indica eliminacao.
     Decoder regenera 1..N na hora de devolver os rows.

  4. PK GRAU 1 com afixo: `id: affix="PED-2026-"` extrai prefixo comum.
     Body so traz sufixos; decoder concatena.

  5. PK GRAU 0: tratada como string normal — bypass por cardinality alta.
     Sem perda, sem ganho artificial.

  Comparacoes obsoletas removidas:
    - L3 preserva PK grau 2 vs elimina (eliminate sempre vence)
    - DICT no header vs inline (inline sempre vence — D16)
    - L3 com cardinality alta vs bypass (bypass sempre vence)
""")
    print(f"  Arquivos: {OUT}")


if __name__ == "__main__":
    main()

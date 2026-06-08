"""SideOutputs quality hook — Fase 3 do schema/quality gadget.

Consome o que o TCF JA' computou (TableSchema via build_schema, ou um
SideOutputs de um encode) e emite **alertas de qualidade zero-custo** —
sem recomputar nada caro e sem tocar `src/tcf/`.

ALERT-ONLY: cada detector retorna um QualityAlert (sinal + razao). Nunca
modifica dados. O dev/arquiteto decide o que fazer.

## O que é genuinamente ZERO-CUSTO (já em ColumnFeatures/SideOutputs)

- `cardinality` (n_unicas/n_rows): duplicate-key, useless-id, constante
- `is_numeric` + `sample` (já capturados): type_drift (re-parsear o sample
  de 20 valores é trivial — o sample já está na mão)
- `cadence_detected` / `seq_rle_runs_count`: proxies de estrutura/cadência

## O que NÃO é zero-custo (fora do escopo desta fase — ver design doc)

- null/empty count, length stddev: exigiriam acumulador novo em
  analyze_column → TOCA o pre-pass → gated por T-REGRESSION-REAL-WORLD.
- type_drift ALEM do sample[:20]: exigiria varrer todos os valores.
  Aqui detectamos só drift VISIVEL no sample (zero-custo). Drift no
  tail é honestamente declarado como nao-coberto.
"""

from __future__ import annotations

from dataclasses import dataclass


def _is_numeric_string(v: str) -> bool:
    if not v:
        return False
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class QualityAlert:
    """Um alerta de qualidade (alert-only — não implica correção)."""
    column: str
    kind: str        # 'duplicate_key' | 'constant' | 'type_drift'
    severity: str    # 'baixa' | 'media' | 'alta'
    detail: str
    zero_cost: bool = True  # este detector leu só o que o TCF já computou

    def alert(self) -> str:
        return f"[{self.severity}|{self.kind}] {self.column}: {self.detail}"


# Limiar pra type_drift por fração numérica do sample. Se 50%–99% do sample
# parseia como número, é provável coluna numérica "contaminada" por sentinelas
# (N/A, NULL, etc) — sinal de drift. <50% provavelmente é categórica de fato.
_DRIFT_MIN_NUM_FRACTION = 0.5


def _from_columnschema(col, single_pk: bool) -> list[QualityAlert]:
    """Alertas zero-custo derivados de um ColumnSchema (do build_schema).

    single_pk: True só se a coluna é uma PK de UMA coluna (não componente de
    chave composta — esses repetem por design e não são duplicate_key).
    """
    alerts: list[QualityAlert] = []
    name = col.name
    card = col.cardinality
    n = col.n_rows

    # 1) duplicate_key — PK single-column com repetição (ZERO-CUSTO)
    #    Só para chaves de UMA coluna; componentes de PK composta repetem
    #    por design (verificar unicidade da tupla NÃO é zero-custo).
    if single_pk and n > 0 and card < 1.0:
        n_dups = n - col.n_unicas
        alerts.append(QualityAlert(
            column=name, kind="duplicate_key", severity="alta",
            detail=(f"PK single-column esperada única mas cardinality={card:.4f} "
                    f"(~{n_dups} valores repetidos em {n} linhas)"),
        ))

    # 2) constante / degenerada — 1 valor único (ZERO-CUSTO).
    #    Único detector sem falso positivo observado (validacao adversarial
    #    2026-06-03: TP em tpch o_shippriority, 0 FP em 7 datasets).
    if n >= 2 and col.n_unicas == 1:
        alerts.append(QualityAlert(
            column=name, kind="constant", severity="media",
            detail=f"coluna constante (1 valor único em {n} linhas) — possível dead column",
        ))

    # 3) type_drift por FRAÇÃO NUMÉRICA do sample (ZERO-CUSTO: sample já em mão).
    #    Substitui a versão antiga (que era codigo morto: dependia de
    #    is_numeric=True, contraditorio com ter nao-numerico no mesmo sample).
    #    Agora dispara quando o sample é MAIORIA numérico mas tem minoria
    #    nao-numerica — coluna numerica contaminada por sentinela (N/A/NULL).
    #    LIMITACAO declarada: vê só o sample[:20]; drift no tail é invisível
    #    (exigiria scan full = nao zero-custo, gated T-REGRESSION-REAL-WORLD).
    if col.sample and len(col.sample) >= 4:
        num = sum(1 for v in col.sample if _is_numeric_string(v))
        frac = num / len(col.sample)
        if _DRIFT_MIN_NUM_FRACTION <= frac < 1.0:
            bad = [v for v in col.sample if not _is_numeric_string(v)]
            alerts.append(QualityAlert(
                column=name, kind="type_drift", severity="alta",
                detail=(f"{frac:.0%} do sample é numérico mas há não-numérico(s) "
                        f"{bad[:3]} — possível coluna numérica com sentinela"),
            ))

    return alerts


def analyze_quality(
    schema,
    *,
    expected_unique=None,
) -> list[QualityAlert]:
    """Emite alertas de qualidade zero-custo de um TableSchema.

    Detectores (todos ZERO-CUSTO — leem só o que build_schema já produziu):
    - duplicate_key (PK single-column com repetição)
    - constant (coluna de 1 valor único)
    - type_drift (sample maioria-numérico com minoria não-numérica)

    NÃO cobre (fora do zero-custo, por design — ver design doc): null/empty
    count, length stddev, drift no tail (além do sample[:20]), format-mix,
    range/datas impossíveis. O detector `useless_id` foi REMOVIDO (validação
    adversarial 2026-06-03: 12/12 falsos positivos em tpch — disparava em
    qualquer string all-distinct como nomes/comentários).

    Args:
        schema: TableSchema (de `from tcf import build_schema`).
        expected_unique: PKs **single-column** que deveriam ser únicas.
            Aceita: set/list de nomes, ou string única. Componentes de PK
            COMPOSTA NÃO devem ser passados (repetem por design — passar a
            tupla inteira é ignorado pra duplicate_key, evitando FP).
            Tuplas/frozensets em expected_unique são tratadas como chaves
            compostas e seus membros são EXCLUÍDOS do duplicate_key single.

    Returns:
        Lista de QualityAlert (alert-only). Ordenada por severidade desc.
    """
    # Type guard: string vira set de 1 nome (não vira set de chars);
    # tuplas/frozensets = chaves compostas (membros excluídos do single-pk).
    single_pks: set[str] = set()
    composite_members: set[str] = set()
    if isinstance(expected_unique, str):
        single_pks = {expected_unique}
    elif expected_unique:
        for item in expected_unique:
            if isinstance(item, (tuple, frozenset, list, set)):
                composite_members.update(item)  # chave composta
            else:
                single_pks.add(item)
    single_pks -= composite_members  # membro de composta nunca é single-pk

    alerts: list[QualityAlert] = []
    for name, col in schema.columns.items():
        alerts.extend(_from_columnschema(col, single_pk=name in single_pks))

    rank = {"alta": 0, "media": 1, "baixa": 2}
    alerts.sort(key=lambda a: (rank.get(a.severity, 9), a.column))
    return alerts


def _self_demo() -> None:
    """Demo sem Z: — constrói schema na hora e emite alertas."""
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))
    from tcf import build_schema

    data = {
        "id": ["1", "2", "3", "2", "5"],            # PK single → dup (2) = duplicate_key
        "status": ["A", "A", "A", "A", "A"],         # constante
        "valor": ["10", "20", "N/A", "40", "50"],    # 80% num + 'N/A' = type_drift
        "nome": ["ana", "bia", "cris", "duda", "eva"],  # all-distinct string: NÃO deve alertar (useless_id removido)
    }
    schema = build_schema(data)
    alerts = analyze_quality(schema, expected_unique={"id"})
    for a in alerts:
        print(" ", a.alert())
    print(f"  (total {len(alerts)} alertas; 'nome' all-distinct corretamente silencioso)")


if __name__ == "__main__":
    _self_demo()

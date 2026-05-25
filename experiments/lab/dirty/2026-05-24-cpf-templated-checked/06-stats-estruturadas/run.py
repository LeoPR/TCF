"""Sub-exp 06 — NatureApplyStats com dimensoes ISO/IEC 25012.

Implementa coleta estruturada de estatisticas alinhada com framework
academico (ISO 25012 + Kim et al. 2003):

- Apply-time: apply_rate, fallback_reasons (Kim 2003 taxonomy)
- Quality dimensions (ISO 25012 inherent):
  - accuracy_rate: % strictly valid (regex + check)
  - completeness_rate: % non-empty
  - consistency_rate: % no formato dominante
  - compliance_rate: % adere spec rigida

Reusa encoder/decoder do sub-exp 05; foco eh a coleta de stats.

Outputs heavy (auditoria + literatura mapping):
- `out_tcf/<dataset>.tcf` — encode (mesmo de 05)
- `out_tcf/<dataset>-stats.json` — NatureApplyStats serializado
- `out_stats/SUMMARY.md` — comparacao tabular cross-dataset
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

THIS = Path(__file__).parent
LAB = THIS.parent
ROOT = LAB.parents[3]
sys.path.insert(0, str(ROOT / "src"))

# Reusa classifier do sub-exp 05
SUBEXP_05 = LAB / "05-fallback-per-value"
sys.path.insert(0, str(SUBEXP_05))
from run import (  # type: ignore  # noqa: E402
    encode_cpf_v05, decode_cpf_v05, classify_fallback,
    CPF_RE, MARKER_LITERAL, BASE94,
)
from tcf import encode, decode  # noqa: E402


# ===========================================================================
# NatureApplyStats — dataclass aderente ISO/IEC 25012
# ===========================================================================

@dataclass
class NatureApplyStats:
    """Estatisticas estruturadas pra encoder por natureza (ISO 25012 + Kim 2003).

    Campos apply-time + dimensoes de qualidade inerente.
    """
    nature: str
    n_total: int
    n_applied: int                          # comprimido com sucesso
    n_fallback: int                         # caiu em literal

    # Apply-time
    apply_rate: float                       # n_applied / n_total

    # Fallback taxonomy (Kim et al. 2003)
    fallback_reasons: dict[str, int] = field(default_factory=dict)

    # Quality dimensions (ISO/IEC 25012 inherent)
    accuracy_rate: float = 0.0              # % strictly valid (regex + check)
    completeness_rate: float = 0.0          # % non-empty
    consistency_rate: float = 0.0           # % no formato dominante
    compliance_rate: float = 0.0            # % adere spec (== apply_rate)

    # Confidence — heuristica "isto eh mesmo CPF?"
    confidence_score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def compute_nature_stats(nature: str, values: list[str], statuses: list[str]) -> NatureApplyStats:
    """Computa NatureApplyStats a partir de classificacao per-valor.

    Args:
        nature: nome ("cpf" / "cnpj" / etc.)
        values: lista original
        statuses: lista paralela com status de classify_fallback per valor

    Returns:
        NatureApplyStats com todas dimensoes preenchidas.
    """
    n = len(values)
    if n == 0:
        return NatureApplyStats(nature=nature, n_total=0, n_applied=0,
                                n_fallback=0, apply_rate=0.0)

    counts = Counter(statuses)
    n_applied = counts.get('compressible', 0)
    n_fallback = n - n_applied
    apply_rate = n_applied / n

    # Quality dimensions (ISO 25012)
    n_non_empty = sum(1 for v in values if v)
    completeness = n_non_empty / n

    # Accuracy: % que passa regex + check (== compressible)
    accuracy = n_applied / n

    # Consistency: % no formato dominante (moda das classificacoes)
    if counts:
        most_common_count = counts.most_common(1)[0][1]
        consistency = most_common_count / n
    else:
        consistency = 0.0

    # Compliance: % strictly aderente a spec rigida (== accuracy)
    compliance = accuracy

    # Confidence: heuristica composta — accuracy ponderado por completeness
    confidence = accuracy * (0.5 + 0.5 * completeness)

    # Fallback reasons: tudo que NAO eh 'compressible' (Kim 2003 taxonomy)
    fallback_reasons = {k: v for k, v in counts.items() if k != 'compressible'}

    return NatureApplyStats(
        nature=nature,
        n_total=n,
        n_applied=n_applied,
        n_fallback=n_fallback,
        apply_rate=round(apply_rate, 4),
        fallback_reasons=dict(fallback_reasons),
        accuracy_rate=round(accuracy, 4),
        completeness_rate=round(completeness, 4),
        consistency_rate=round(consistency, 4),
        compliance_rate=round(compliance, 4),
        confidence_score=round(confidence, 4),
    )


# ===========================================================================
# Sub-exp 06 measure
# ===========================================================================

def load_cpfs(name: str) -> list[str]:
    path = LAB / "data" / f"{name}.csv"
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] if row else '' for row in r]


def measure(name: str) -> tuple[NatureApplyStats, dict]:
    values = load_cpfs(name)
    statuses = [classify_fallback(v) for v in values]
    stats = compute_nature_stats("cpf", values, statuses)

    # Encode pra validar RT (reusa pipeline sub-exp 05)
    encoded_values = []
    for v in values:
        enc, _ = encode_cpf_v05(v)
        encoded_values.append(enc)

    rt_ok = True
    tcf_bytes = 0
    if encoded_values:
        text = encode(encoded_values)
        tcf_bytes = len(text.encode("utf-8"))
        decoded_raw = decode(text)
        reconstructed = [decode_cpf_v05(d) for d in decoded_raw]
        rt_ok = (reconstructed == values)

        # Salva .tcf + stats.json em out_tcf/ (visibilidade)
        out_dir = THIS / "out_tcf"
        out_dir.mkdir(exist_ok=True)
        (out_dir / f"{name}.tcf").write_bytes(text.encode("utf-8"))
        (out_dir / f"{name}-stats.json").write_text(
            json.dumps(stats.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    summary = {
        "dataset": name,
        "n_total": stats.n_total,
        "tcf_bytes": tcf_bytes,
        "rt_ok": rt_ok,
        "stats": stats.to_dict(),
    }
    return stats, summary


def main():
    datasets = [
        "D-CPF-uniform",
        "D-CPF-clustered",
        "D-CPF-mixed",
        "D-CPF-corrupt",
        "D-CPF-edge-single",
        "D-CPF-edge-allsame",
        "D-CPF-edge-allcorrupt",
        "D-CPF-extra-large10k",
        "D-CPF-extra-hostile",
    ]

    results = []
    print("=== Sub-exp 06 — NatureApplyStats (ISO/IEC 25012) ===\n")
    print(f"{'dataset':26s} {'rows':>6} {'apply_rate':>11} {'accuracy':>9} "
          f"{'complete':>9} {'consist':>8} {'comply':>7} {'confid':>7} {'rt':>3}")
    print("-" * 110)
    for name in datasets:
        stats, summary = measure(name)
        results.append(summary)
        print(f"{name:26s} {stats.n_total:>6} "
              f"{stats.apply_rate:>10.4f} "
              f"{stats.accuracy_rate:>9.4f} "
              f"{stats.completeness_rate:>9.4f} "
              f"{stats.consistency_rate:>8.4f} "
              f"{stats.compliance_rate:>7.4f} "
              f"{stats.confidence_score:>7.4f} "
              f"{'OK' if summary['rt_ok'] else 'FAIL':>3}")

    print("\nFallback breakdown (Kim et al. 2003 taxonomy):")
    for s in results:
        fb = ', '.join(f"{k}={v}" for k, v in sorted(s['stats']['fallback_reasons'].items()))
        if fb:
            print(f"  {s['dataset']:26s}: {fb}")
        else:
            print(f"  {s['dataset']:26s}: (none — 100% compressible)")

    # Salva manifest + summary markdown
    out = THIS / "manifest.jsonl"
    out.write_text("\n".join(json.dumps(s) for s in results) + "\n", encoding="utf-8")

    # SUMMARY.md tabular
    summary_lines = [
        "# Sub-exp 06 — NatureApplyStats SUMMARY (ISO/IEC 25012)",
        "",
        "Estatisticas estruturadas por dataset, alinhadas a framework",
        "academico (ISO/IEC 25012 dimensions + Kim et al. 2003 taxonomy).",
        "",
        "## Tabela cross-dataset",
        "",
        "| Dataset | n | apply | accuracy | complete | consist | comply | confid | RT |",
        "|---|---:|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for s in results:
        d = s['stats']
        summary_lines.append(
            f"| {s['dataset']} | {s['n_total']} | "
            f"{d['apply_rate']:.4f} | {d['accuracy_rate']:.4f} | "
            f"{d['completeness_rate']:.4f} | {d['consistency_rate']:.4f} | "
            f"{d['compliance_rate']:.4f} | {d['confidence_score']:.4f} | "
            f"{'OK' if s['rt_ok'] else 'FAIL'} |"
        )

    summary_lines.extend([
        "",
        "## Interpretacao (mapeamento literatura)",
        "",
        "- **apply_rate alto + accuracy alto** (uniform/clustered/extra-large10k):",
        "  dataset 'happy path' (Myers equivalence class). Encoder aplica em massa.",
        "- **apply_rate baixo + accuracy baixo** (edge-allcorrupt/extra-hostile):",
        "  dataset adversarial/fuzz (Miller 1990). Encoder fallback em massa,",
        "  bytes nao compensam — heuristica de aplicacao deveria rejeitar nature aqui.",
        "- **mixed**: 2 equivalence classes coexistindo (Rahm & Do multi-source).",
        "  apply_rate ~0.5, consistency baixa.",
        "- **corrupt**: mutation testing (DeMillo) com 4 tipos sistematicos.",
        "  fallback_reasons mostra distribuicao das mutacoes.",
        "- **edge-allsame**: cardinalidade=1 boundary (Beizer). Stats validos mas",
        "  ratio TCF (RLE HCC) eh quem brilha — stats sozinhas nao capturam.",
        "",
        "## Heuristica de aplicacao proposta",
        "",
        "Schema_builder Fase 3 deve ativar nature CPF apenas se:",
        "",
        "```",
        "apply_rate >= 0.5  AND  consistency_rate >= 0.5",
        "```",
        "",
        "Caso contrario, M10 puro (sem pre-tx CPF) eh melhor — sub-exp 01",
        "demonstrou que M10 piora bytes mas mantem RT 100% sempre.",
        "",
    ])
    (THIS / "SUMMARY.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"\nManifest: {out}")
    print(f"SUMMARY:  {THIS / 'SUMMARY.md'}")
    print(f"Outputs:  {THIS / 'out_tcf'}/")


if __name__ == "__main__":
    main()

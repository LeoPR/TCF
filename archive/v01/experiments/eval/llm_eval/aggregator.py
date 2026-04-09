import json
from pathlib import Path
from typing import Dict, Any, List

from .metrics import score_results


def load_plan(path: str) -> Dict[str, Any]:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def consolidate(plan_path: str, results_root: str) -> Dict[str, Any]:
    plan = load_plan(plan_path)
    models = plan.get('models', [])
    formats = plan.get('formats', [])
    summary: List[Dict[str, Any]] = []

    for m in models:
        name = m if isinstance(m, str) else m.get('name')
        for fmt in formats:
            rdir = Path(results_root) / name.replace(':','_') / fmt
            report_file = rdir / 'report.json'
            if not report_file.exists():
                continue
            report = json.loads(report_file.read_text(encoding='utf-8'))
            summary.append({
                'model': name,
                'format': fmt,
                'accuracy': report['accuracy'],
                'avg_latency_s': report['avg_latency_s'],
                'avg_prompt_chars': report.get('avg_prompt_chars'),
                'composite_score': report.get('composite_score'),
            })

    # Ranking per model per format by composite_score
    ranked = sorted(summary, key=lambda r: (-(r.get('composite_score') or 0), r.get('avg_latency_s') or 0))
    return {'summary': summary, 'ranked': ranked}


def save_consolidated(data: Dict[str, Any], out_json: str, out_md: str | None = None) -> None:
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if out_md:
        lines = ["# Consolidado de Avaliações", "", "| Modelo | Formato | Acc | Lat (s) | Prompt chars | Score |"]
        lines.append("|--------|---------|-----|--------|-------------|-------|")
        for row in data['ranked']:
            lines.append(
                f"| {row['model']} | {row['format']} | {row['accuracy']:.2f} | {row['avg_latency_s']:.2f} | {row['avg_prompt_chars']:.0f} | {row['composite_score']:.3f} |"
            )
        Path(out_md).parent.mkdir(parents=True, exist_ok=True)
        with open(out_md, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

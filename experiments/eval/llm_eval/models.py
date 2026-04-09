import json
import time
import requests
from typing import List, Dict, Any, Tuple

DEFAULT_ENDPOINT = "http://localhost:11434"


def fetch_local_models(endpoint: str = DEFAULT_ENDPOINT, timeout: int = 30) -> List[Dict[str, Any]]:
    url = endpoint.rstrip('/') + '/api/tags'
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    models = data.get('models', [])
    out: List[Dict[str, Any]] = []
    for m in models:
        details = m.get('details', {})
        out.append({
            'name': m.get('name'),
            'size_bytes': m.get('size'),
            'family': details.get('family'),
            'parameter_size': details.get('parameter_size'),
            'quantization': details.get('quantization_level'),
            'format': details.get('format'),
            'modified_at': m.get('modified_at'),
        })
    return out


def rank_models(models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Simple heuristic: prioritize medium parameter_size and smaller size_bytes (fast) then name
    def parse_param(ps: str | None) -> float:
        if not ps:
            return 0.0
        try:
            return float(ps.lower().replace('b','').replace('x','').replace('m',''))
        except Exception:
            return 0.0
    ranked = sorted(models, key=lambda m: (parse_param(m.get('parameter_size')), m.get('size_bytes', 0)))
    for i, m in enumerate(ranked):
        m['rank'] = i + 1
    return ranked


def save_models(models: List[Dict[str, Any]], path: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'fetched_at': time.time(), 'models': models}, f, ensure_ascii=False, indent=2)


def _param_float(ps: str | None) -> float:
    if not ps:
        return 0.0
    s = ps.strip().lower()
    # remove common suffixes
    s = s.replace('b','').replace('m','').replace('x','')
    try:
        return float(s)
    except Exception:
        return 0.0


def _size_category(pf: float) -> str:
    if pf < 4:
        return 'tiny'
    if pf < 8:
        return 'small'
    if pf < 14:
        return 'medium'
    if pf < 30:
        return 'large'
    return 'xl'


def auto_select_models(models: List[Dict[str, Any]], desired: int = 5, require_family_diversity: bool = True) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Select a representative subset of model names.

    Strategy:
      1. Annotate each model with param_float and size_category.
      2. Bucket by size_category.
      3. Round-robin pick across buckets (tiny->small->medium->large->xl) until desired reached.
      4. If require_family_diversity, avoid picking duplicate families early; relax if insufficient count.
    Returns (names, annotated_models_subset).
    """
    annotated = []
    for m in models:
        pf = _param_float(m.get('parameter_size'))
        cat = _size_category(pf)
        am = dict(m)
        am['param_float'] = pf
        am['size_category'] = cat
        annotated.append(am)
    # buckets maintain original order (ranked earlier externally if desired)
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    order = ['tiny','small','medium','large','xl']
    for am in annotated:
        buckets.setdefault(am['size_category'], []).append(am)
    picks: List[Dict[str, Any]] = []
    used_families = set()
    # primary pass enforcing family diversity
    while len(picks) < desired:
        progressed = False
        for cat in order:
            if len(picks) >= desired:
                break
            lst = buckets.get(cat, [])
            if not lst:
                continue
            # find first candidate respecting family diversity (if enabled)
            idx = None
            for i, cand in enumerate(lst):
                fam = cand.get('family')
                if not require_family_diversity or fam not in used_families:
                    idx = i
                    break
            if idx is None:
                continue
            chosen = lst.pop(idx)
            picks.append(chosen)
            fam = chosen.get('family')
            if fam:
                used_families.add(fam)
            progressed = True
        if not progressed:
            break
    # secondary pass (relax family constraint) if still short
    if len(picks) < desired:
        for cat in order:
            lst = buckets.get(cat, [])
            while lst and len(picks) < desired:
                picks.append(lst.pop(0))
    names = [p['name'] for p in picks]
    return names, picks

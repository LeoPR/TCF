"""Introspeccao RAPIDA (sem encode) — K/N/NK por coluna dos hubs, pra curar o sweep de encode.
Lista so' colunas com repeticao (2<=K<N). Marca as high-card (K>1024). READ-ONLY."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))
from dataset_reader import DatasetReader   # noqa: E402

LIMIT = 20000

for hub in ["adult-census", "tpch-sf001", "receita-cnpj", "br-identidades", "ibge-municipios"]:
    try:
        r = DatasetReader(hub)
    except Exception as e:
        print(f"# {hub}: indisponivel ({e})")
        continue
    print(f"\n### {hub}  tabelas={list(r.tables)}")
    for t in r.tables:
        try:
            cols = r.columns(t, limit=LIMIT)
        except Exception as e:
            print(f"  {t}: erro {e}")
            continue
        for cn, vals in cols.items():
            if not vals:
                continue
            vals = [str(v) for v in vals]
            N = len(vals); K = len(set(vals))
            if 2 <= K < N:
                tag = "  <<< HIGH-CARD" if K > 1024 else ""
                print(f"  {t[:14]:14} {cn[:22]:22} N={N:6} K={K:6} N/K={N/K:6.1f}{tag}")
    r.close()

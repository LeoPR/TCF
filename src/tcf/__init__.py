"""TCF — Tabular Compact Format (v0.6).

API publica:

    from tcf import encode, decode

    tcf_text = encode(["abc", "abcd", "abcde"])
    values = decode(tcf_text)
    assert values == ["abc", "abcd", "abcde"]

## Componentes canonicos

- `tcf.core.online`: **OBAT** (Online Bidirectional Affix Tokenizer).
  Camada 1 do TCF. Tokeniza strings via LCP + LCS contra anteriores.
  Codnome de origem: `alg16` (intocado de M0/online.py do dirty lab).
- `tcf.core.syntax_base`: interface `Syntax` (encode + decode).
- `tcf.composicional.syntax`: **HCC** (Hierarchical Compositional
  Coding). Camada 2 do TCF. Detector unificado + emit composicional
  (`~` cria ref auto-nomeado, `,` concat efemero). Codnome de origem:
  `M8.A`.
- `tcf.encoder` / `tcf.decoder`: API publica de alto nivel.

Ver `docs/algorithms/` para documentacao tecnica detalhada de cada
camada (OBAT, HCC, TCF-format).

## Validacao

Validado em 9 datasets sinteticos (D1-D9):
- RT 9/9 OK
- Total 1615 bytes em 2981 raw = 54.2% ratio
- Cadeia byte-canonica de checkpoints: M9 → M10 → M11 → M12 → M13 → M14

## Estado v0.6

Single-column. Multi-column / multi-dataset sera adicionado em fase
posterior (encoder/organizador). Para historia do desenvolvimento,
ver `experiments/lab/dirty/notas/historia-dirty-lab.md`.

Ciclo v0.5 (formato columnar com RLE/dict para LLM benchmark) em
`old/tcf/` — acessorio ao foco atual.
"""

from tcf.encoder import encode
from tcf.decoder import decode

__all__ = ["encode", "decode"]

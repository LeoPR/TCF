"""tcf.natures — pre-tx por natureza (CAMADA 0 do funil).

Welded canonical 2026-05-24 via ADR-0015 (T-CODE-NATURES-WELD).

Cobre categoria "Templated + Checked + Unique-Discrete":
- SPEC_CPF (NNN.NNN.NNN-DD, mod-11)
- SPEC_CNPJ (NN.NNN.NNN/NNNN-DD, mod-11 dupla)

Outras categorias (TCU-NoCheckVarLength, TCU-Delta, Lossy, Composite)
nao welded — registradas em
`experiments/lab/dirty/notas/naturezas-templated-2026-05-24.md`.

Filosofia:
- Opt-in per-value: cada valor decide se vale comprimir; fallback literal
- TCF nao valida semantica (nao checa "este CPF existe")
- Decoder precisa do mesmo spec usado no encode (out-of-band; futuro:
  header carry spec id)
- RT byte-canonical preservado em todos casos

API publica:

    from tcf.natures import SPEC_CPF, SPEC_CNPJ, encode_value, decode_value

    # Single value
    encoded, status = encode_value(SPEC_CPF, "123.456.789-09")
    original = decode_value(SPEC_CPF, encoded)

    # Em coluna (via tcf.encode com nature param)
    from tcf import encode, decode
    text = encode(cpfs_list, nature=SPEC_CPF)
    cpfs_back = decode(text, nature=SPEC_CPF)
"""

from tcf.natures.templated_checked import (
    TemplatedCheckedSpec,
    SPEC_CPF,
    SPEC_CNPJ,
    BASE94,
    MARKER_LITERAL,
    encode_value,
    decode_value,
    classify_value,
)
from tcf.natures.templated_padded import (
    TemplatedPaddedSpec,
    SPEC_IP,
)

__all__ = [
    # Templated + Checked (CPF, CNPJ)
    "TemplatedCheckedSpec",
    "SPEC_CPF",
    "SPEC_CNPJ",
    # Templated + Padded (IP)
    "TemplatedPaddedSpec",
    "SPEC_IP",
    # Compartilhados
    "BASE94",
    "MARKER_LITERAL",
    "encode_value",
    "decode_value",
    "classify_value",
]

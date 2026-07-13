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
- Decoder precisa do mesmo spec usado no encode (out-of-band). O "header carry
  spec id" (self-describing) foi desenhado como H-NAT-MARK-01 e PARADO em (A) —
  ADR-0027 `proposed` (nao implementar agora; rota zero-core via registry gadget)
- RT byte-canonical preservado em todos casos

API publica:

    from tcf.natures import SPEC_CPF, SPEC_CNPJ, encode_value, decode_value

    # Single value
    encoded, status = encode_value(SPEC_CPF, "123.456.789-09")
    original = decode_value(SPEC_CPF, encoded)

    # Em coluna (via tcf.encode com nature param). O header e' SELF-DESCRIBING
    # (#TCF.8 :cpf, ADR-0027): o decode resolve sozinho pelo registry — passar
    # nature= no decode e' redundante (header vence; sem dupla aplicacao).
    from tcf import encode, decode
    text = encode(cpfs_list, nature=SPEC_CPF)
    cpfs_back = decode(text)
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

# --- Self-describing nature (ADR-0027, #TCF.8): resolucao CORE-ONLY ---
# Vocabulario FECHADO dos 3 ids core, ancorado no `name` dos specs frozen
# welded (ADR-0015). A STRING do nome viaja no header (:id no meta-line); o
# decode resolve por este dict FIXO — ZERO eval, zero codigo vindo do header.
SPEC_REGISTRY = {
    SPEC_CPF.name: SPEC_CPF,
    SPEC_CNPJ.name: SPEC_CNPJ,
    SPEC_IP.name: SPEC_IP,
}


def _resolve_nature_id(nature_id: str):
    """Resolve a STRING de um nature-id (header #TCF.8) -> spec, ou None se
    desconhecido. A funcao interna permanece total; o decoder publico converte
    `None` em ValueError fail-loud para ids fora do registry fechado. NAO reusar
    `scripts/natures_compiler/registry.py:get()` aqui (esse faz raise)."""
    return SPEC_REGISTRY.get(nature_id)


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

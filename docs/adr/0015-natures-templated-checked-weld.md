# 0015 — TemplatedCheckedSpec welded canonical em src/tcf/natures

**Status**: accepted + welded
**Date**: 2026-05-24
**Deciders**: project owner
**Tags**: welding, natures, pre-tx, cpf, cnpj, layered-pipeline, camada-0

## Context and Problem Statement

Sub-exps 05-07 (2026-05-24) em dirty lab validaram categoria
"Templated + Checked + Unique-Discrete" via `TemplatedCheckedSpec`
parametrico:

- 18 datasets D-CPF/D-CNPJ testados, RT 100%
- CPF uniform/clustered: -55 a -64% vs M10 puro
- CNPJ uniform/clustered: -54 a -61% vs M10 puro
- Mesma maquina parametrica serve CPF e CNPJ (H3 confirmada)
- Fallback marker `_<literal>` preserva RT em valores nao-compressible
- Stats ISO/IEC 25012 viaveis (sub-exp 06)

Owner aprovou (2026-05-24) welding canonical apos discussao arquitetural
sobre funil de camadas:
- CAMADA 0 (filtro nature) — esta sendo welded agora
- CAMADAS 1-3 (pre-pass, OBAT, HCC) ja' welded em ADRs anteriores

## Considered Options

### Opcao A — Manter so' em dirty lab

Pros: zero risco canonical
Contras: feature comprovada nao acessivel via API publica; usuarios
copiam codigo dirty

### Opcao B — Weld como modulo opcional opt-in (escolhida)

Pros:
- API publica clara: `encode(values, nature=SPEC_CPF)`
- Default `encode(values)` inalterado (M10 INVARIANT preservado)
- Strategy pattern (zero `if name == X`)
- Pre-tx por nature CAMADA 0 alinhado com arquitetura funil
Contras:
- Decoder precisa de spec out-of-band (futuro: header carry spec id)
- Adiciona surface area (3 imports novos: SPEC_CPF, SPEC_CNPJ, TemplatedCheckedSpec)

### Opcao C — Weld com auto-detect

Encoder auto-detecta nature via heuristica (apply_rate threshold).

Pros: zero usuario configuration
Contras:
- Heuristica de selecao eh complexa (schema_builder Fase 3 trabalho)
- Risco de falsos positivos
- Quebra M10 INVARIANT (mesmo input pode dar output diferente)

## Decision Outcome

**Opcao B** — opt-in via nature param.

### Implementacao

Novo package `src/tcf/natures/`:
- `__init__.py` — exports publicos
- `templated_checked.py` — TemplatedCheckedSpec + SPEC_CPF + SPEC_CNPJ
  + encode_value/decode_value/classify_value genericos

API publica:
```python
from tcf import encode, decode, SPEC_CPF, SPEC_CNPJ, TemplatedCheckedSpec

# Single-column
text = encode(cpfs_list, nature=SPEC_CPF)
back = decode(text, nature=SPEC_CPF)

# Multi-column
text = encode(table, nature_per_col={"cpf": SPEC_CPF, "cnpj": SPEC_CNPJ})
back = decode(text, nature_per_col={...})

# Default (sem nature) inalterado — M10 INVARIANT
text = encode(values)  # comportamento atual preservado
```

### Arquitetura

- `TemplatedCheckedSpec` @dataclass(frozen=True) — descritor puro
  (name, regex, body_length, check_length, check_fn, formatter,
  encoded_length)
- `encode_value(spec, v)` / `decode_value(spec, payload)` —
  funcoes genericas polimorficas (strategy pattern)
- `classify_value(spec, v)` — taxonomy Kim et al. 2003
  ('compressible' / 'check_invalid' / 'format_mismatch' / etc.)
- BASE94 alfabeto safe TCF (94 - 14 reserved chars - `_` marker = 80 chars)
- MARKER_LITERAL = `_` distingue literal de compressed

Zero `if name == 'cpf'` em qualquer lugar — polimorfismo via spec param.

### Outras categorias

NAO welded nesta ADR:
- TCU-NoCheckVarLength (IP) — sub-exps 08/09/12 mostraram que padding+M10
  ou base94 vencem; SlotBehavior nao agregou (sub-exp 13 refutado)
- Lossy-recoverable, Composite, Hierarchical — registradas em
  `experiments/lab/dirty/notas/naturezas-templated-2026-05-24.md`,
  aguardando datasets dedicados

Categorias acima podem adicionar specs novas seguindo mesmo padrao
(novo TemplatedCheckedSpec ou novo subtipo) sem mudar API publica.

## Consequences

**Positivas**:
- API publica enxuta (default inalterado, nature opt-in)
- Pre-tx por nature acessivel sem copiar codigo dirty
- Strategy pattern facilita adicionar specs futuras (Luhn, IBAN, etc.)
- Decoder simetrico — mesma API, mesmo spec
- D17a 322B INVARIANT preservado byte-canonical
- Suite completa: 176 passed (+21 novos) + 1 pre-existing fail (nao
  relacionado)

**Neutras**:
- Decoder precisa receber spec out-of-band — usuario responsabilidade
- Multi-col nature_per_col so' funciona com dict input (consistent com
  ADR-0014)

**Negativas**:
- Surface area API cresce (3 novos exports)
- Documentacao adicional necessaria

## Validacao

### Byte-canonical preservado
- D17a sint (sem nature): 322B INVARIANT
- D1-D9 sint (sem nature): comportamento M10 inalterado (tests passam)

### Compressao real-world
- CPF 50 vals com SPEC_CPF: 942B (M10 puro) -> 337B (nature) = **-64%**
- CNPJ 50 vals com SPEC_CNPJ: similar ganho
- Multi-col cpf+cnpj 10 vals cada: 181B (vs ~470B M10 puro = -61%)

### Tests
- 21 tests novos em `tests/test_natures.py` (TestSpecs/TestCPF/TestCNPJ/
  TestEncodeIntegration/TestPolymorphism)
- Suite completa: 176 passed (era 155, +21) + 1 xfailed + 1 pre-existing
  fail (test_shaper, nao relacionado)
- D17a 322B INVARIANT preservado em test `test_d17a_invariant_without_nature`

## Links

- [Sub-exp 05 fallback marker CPF](../../experiments/lab/dirty/2026-05-24-cpf-templated-checked/05-fallback-per-value/report.md)
- [Sub-exp 06 NatureApplyStats](../../experiments/lab/dirty/2026-05-24-cpf-templated-checked/06-stats-estruturadas/SUMMARY.md)
- [Sub-exp 07 CNPJ generalization](../../experiments/lab/dirty/2026-05-24-cpf-templated-checked/07-generalizar-CNPJ/report.md)
- [Naturezas templated catalogacao](../../experiments/lab/dirty/notas/naturezas-templated-2026-05-24.md)
- [Arquitetura funil de camadas](../../experiments/lab/dirty/notas/arquitetura-funil-camadas-2026-05-24.md)
- [ADR-0014 API unificada](0014-unified-api-side-outputs.md) — base
- [T-CODE-SCHEMA-BUILDER](../../tickets/T-CODE-SCHEMA-BUILDER.md) — Fase 3
  consumira specs registradas pra auto-detect
- [META-TYPE-ENCODERS](../../tickets/META-TYPE-ENCODERS.md) — outras
  naturezas (T02-T07) adiadas

## Futuro

1. **Header carry spec id** (futuro): decoder auto-detecta nature via
   header sem precisar out-of-band. Requer marker syntax change.
2. **Schema_builder Fase 3**: auto-detect nature por coluna; popula
   `column.natures` baseado em apply_rate threshold.
3. **Mais specs**: Luhn (cartao credito), IBAN, MAC, CEP — quando
   datasets reais disponiveis.
4. **CAMADA 0 toggle infrastructure**: T-CODE-LAYERED-PIPELINE
   integrara nature filter com online adaptive fallback.

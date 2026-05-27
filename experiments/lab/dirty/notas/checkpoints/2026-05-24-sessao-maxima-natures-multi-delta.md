# Checkpoint — Sessao maxima 2026-05-24 (natures + multi-delta)

**Data**: 2026-05-24
**Tipo**: pausa apos sessao mega-produtiva
**Motivo**: 3 ADRs welded canonical em uma sessao + benchmark consolidado;
pausa pra consolidar antes de avancar pra proximas direcoes.

> **PRECISO LEMBRAR DESSA CONVERSA NESSE PONTO**. Este eh o ponto
> exato pra retomada. Quando user disser "vamos voltar para o
> checkpoint", este eh o doc a abrir.

## Sumario executivo

**Sessao 2026-05-24** foi uma das mais produtivas do projeto:
- **3 ADRs welded canonical** (0014, 0015, 0016)
- **14 sub-experiments dirty** (CPF/CNPJ/IP + debug + multi-segment)
- **5 sub-exps em paralelo** (benchmark, gating refutado, base-aware
  refutado, cross-subnet diagnosed, hex IP abandonado)
- **5 tickets P2/P3 novos** criados; 2 fechados (welded/superseded)
- **Suite tests**: 96 -> **211** (+115 novos)
- **Benchmark consolidado**: TCF venceu em **5/6 datasets** (vs csv+brotli)

## O que foi welded canonical (src/tcf)

### ADR-0014 — API unificada + SideOutputs (commit `ad5afeb`)

```python
from tcf import encode, decode, SideOutputs

# Dispatch automatico por tipo
text = encode(list_or_dict)
result = decode(text)  # roteia pelo shebang
side = SideOutputs(); encode(data, side_outputs=side)
```

- `encode(list)` -> body single-col (sem shebang)
- `encode(dict)` -> #TCF.6 M + header + bodies
- `decode(text)` dispatch automatico
- `SideOutputs` captura column_features, cadence_info, OBAT log,
  HCC trace/rede, seq_rle_runs, multi_info, per_col
- `encode_table`/`decode_table` viraram aliases deprecated

### ADR-0015 — Natures pre-tx CAMADA 0 (commits `d1164dd` + `0b858cb`)

`src/tcf/natures/` package novo:
- `TemplatedCheckedSpec` + SPEC_CPF + SPEC_CNPJ (TCU-CheckedFixedLength)
- `TemplatedPaddedSpec` + SPEC_IP (TCU-NoCheckVarLength)
- Protocol uniforme (zero `isinstance`):
  ```python
  spec.encode_value(v) -> tuple[str, str]
  spec.decode_value(payload) -> str
  spec.classify_value(v) -> str
  ```

```python
text = encode(cpfs, nature=SPEC_CPF)  # opt-in
text = encode(table, nature_per_col={"cpf": SPEC_CPF, "ip": SPEC_IP})
```

Resultados:
- CPF 50 vals: 942B -> 337B (-64%)
- IP subnet 1000: 15747B -> **229B (1.71%)**

### ADR-0016 — HCC seq-RLE multi-delta (commit `5a02ebc`)

`src/tcf/composicional/hcc_seqrle.py` — Bug #2 sub-exp 14 fix:
- `compare_for_seq` retorna `list[int]` (sempre per-run)
- Marker novo `*N+d1,d2,...|template` (CSV opcional) quando misto
- M10 single delta marker `*N+delta|template` preservado (uniform cases)

Resultados:
- D-IP-subnet 1000 sem nature: 117% -> **4.18% (-96.4%)**
- **D1-D9 byte-canonical preservado** (test_m10_baseline_invariant PASS)
- D17a 322B INVARIANT preservado

## Benchmark final consolidado

| Dataset | Vencedor | Bytes | vs CSV raw |
|---|---|---:|---:|
| D17a-sint (13×4) | csv + brotli | 194 | 32.28% |
| D-CPF-uniform-1k | **tcf+nature + brotli** | 4552 | 30.34% |
| D-CPF-clustered-1k | **tcf+nature + brotli** | 3525 | 23.49% |
| D-IP-subnet-1k | **tcf + brotli** | **174** | **1.30%** |
| adult-5k | **tcf + brotli** | 42243 | 7.83% |
| tpch-customer-1500 | **tcf + brotli** | 70644 | 29.29% |

**TCF venceu em 5/6 datasets**. Unico outlier: D17a tiny (header overhead).

## Sub-experiments do lab `2026-05-24-cpf-templated-checked/`

14 sub-exps numerados:
- 01-04: caracterizacao + variantes A/B/C (CPF)
- 05: fallback marker (RT 100% em corrupt) — base pra welding
- 06: NatureApplyStats ISO 25012
- 07: generalizacao CNPJ (H3 validada)
- 08: IP TCU-Delta (achado C subnet 1.71%)
- 09: padding-aware fallback (RT 100% em 27 medicoes)
- 10: debug OBAT/HCC visivel (6 cases)
- 11: gating ADR-0010 — REFUTADO
- 12: IP hex variant D — abandonada
- 13: base-aware seq-RLE — parcialmente refutado
- 14: cross-subnet investigation — **2 bugs reais identificados**

3 lessons META consolidadas:
1. **Diagnosticar antes de generalizar** (sub-exps 11, 13, 14)
2. **Fix no lugar certo > generalizacao downstream**
3. **Outputs visiveis padrao em TODO dirty** (memoria salva)

## Sub-experimento separado: benchmark grande

Lab `2026-05-24-benchmark-formats-compression/`:
- 96 medicoes (6 datasets × 4 formats × 4 transports)
- Re-rodado pos ADR-0016 fix
- TCF venceu em 5/6 (era 4/6 pre-fix)

## Tickets state

### Closed nesta sessao
- T-EXP-MULTI-COL-SCALING (CLOSED-WELDED 2026-05-23, sessao anterior)
- T-CODE-HCC-MULTI-DELTA-FIX -> CLOSED-WELDED-CANONICAL via ADR-0016
- T-CODE-HCC-ATOM-DETECTION-REFINE -> CLOSED-SUPERSEDED-BY-ADR-0016

### Abertos pra futuro
- T-CODE-ENCODER-MANAGER (P2 Fases 1+1b WELDED; Fases 2-4 abertas)
- T-CODE-OUTPUT-SINKS (P2)
- T-CODE-PLAN-CONTRACT (P3)
- T-CODE-SCHEMA-BUILDER (P3 Fases 1+2 WELDED; Fase 3 abertas)
- T-CODE-LAYERED-PIPELINE (P3)
- T-DATA-1 (datasets UCI/OpenML, download pendente owner)

### Hipoteses registradas
- Pacote 7 (Templated/Checksummed/Lossy/Composite) em roadmap-hipoteses.md
- META-TYPE-ENCODERS T02-T07 + L01-L05 (adiados)

## Suite de testes — 211 passed

| Arquivo | Tests | Foco |
|---|---:|---|
| test_core_rt.py | 47 | D1-D9, ColumnFeatures, detect_min_len, edges |
| test_multi_col_rt.py | 28 | Multi-col + deprecated aliases |
| test_side_outputs.py | 17 | SideOutputs single/multi/overhead |
| test_schema.py | 24 | TableSchema + build_schema |
| test_parallel.py | 14 | Encoder parallel + RT |
| test_natures.py | 21 | TemplatedCheckedSpec CPF/CNPJ |
| test_natures_ip.py | 16 | TemplatedPaddedSpec SPEC_IP |
| test_hcc_multi_delta.py | 19 | Multi-delta fix ADR-0016 |
| **Total novo welded sessoes 2026-05-23/24** | **+115 vs commit base 2026-05-22** |

## Estado src/tcf canonical pos-sessao

```
src/tcf/
├── __init__.py              (API publica: encode, decode, SideOutputs,
│                              build_schema, TableSchema, ColumnSchema,
│                              TemplatedCheckedSpec, TemplatedPaddedSpec,
│                              SPEC_CPF, SPEC_CNPJ, SPEC_IP,
│                              encode_table/decode_table deprecated)
├── encoder.py               (encode dispatcher + _encode_column + nature/parallel)
├── decoder.py               (decode dispatcher + nature/per-col)
├── multi.py                 (interno _encode_multi/_decode_multi + alias deprecated)
├── schema.py                (build_schema + TableSchema + ColumnSchema)
├── side_outputs.py          (SideOutputs dataclass)
├── auto_cadence.py          (detect_cadence ADR-0008)
├── auto_min_len.py          (detect_min_len ADR-0010)
├── column_features.py       (ColumnFeatures + analyze_column ADR-H-DA-11c)
├── obat_shape.py            (processar_with_hint ADR-0011)
├── core/online.py           (OBAT canonical ADR-0009 trigram)
├── composicional/
│   ├── syntax.py            (HCC M8.A canonical + Pacote 3 fix ADR-0007)
│   └── hcc_seqrle.py        (HCC seq-RLE M10 + ADR-0016 multi-delta)
└── natures/                 (NOVO 2026-05-24 ADR-0015)
    ├── __init__.py
    ├── templated_checked.py  (TemplatedCheckedSpec + CPF + CNPJ)
    └── templated_padded.py   (TemplatedPaddedSpec + IP)
```

## Filosofia confirmada empiricamente

1. **"Viavel agora > otimo eventual"**: cada welding incremental, manteve
   M10 invariant
2. **Separacao responsabilidades**: Protocol pattern nas specs, strategy
   pattern em layered pipeline
3. **Outputs visiveis em dirty**: padrao agora; salva pra auditoria
4. **Decode obrigatorio pra validar compressao**: feedback owner salva
   no momento certo (sub-exp 05 onwards)
5. **Fix no lugar certo > generalizacao downstream**: confirmado em 3
   sub-exps consecutivos

## Estado memoria/feedback (user scope)

3 memorias novas salvas nesta sessao em
`C:/Users/leona/.claude/projects/.../memory/`:
- `feedback_outputs_visiveis_para_auditoria.md`
- `feedback_decode_obrigatorio_validar_compressao.md`
- `feedback_dirty_lab_outputs_e_progressao_dados.md`

## Pra retomar — proximas direcoes (ordem sugerida)

### Alta prioridade (foundational work)
1. **T-CODE-LAYERED-PIPELINE Fase 1** (toggle infrastructure)
   - Funil de camadas com toggle declarativo
   - Online adaptive + fallback
   - Nota arquitetural ja' escrita

2. **Schema_builder Fase 3** (auto-detect nature)
   - Consume NatureApplyStats
   - Heurıstica apply_rate >= 0.5 AND consistency >= 0.5
   - Auto-aplica SPEC_CPF/CNPJ/IP quando detectado

### Media prioridade (extension)
3. **Mais specs natures**:
   - SPEC_LUHN (cartao credito)
   - SPEC_IBAN
   - SPEC_MAC
   - SPEC_CEP

4. **T-DATA-1 owner**: roda setup_*.py pra Online Retail/Beijing PM2.5/
   Wine Quality. Habilita T-EXP-NATUREZAS-RARAS-V2.

### Baixa prioridade (optimization)
5. **T-CODE-ENCODER-MANAGER Fase 2+ (sinks + per-channel)**
6. **T-CODE-PLAN-CONTRACT** (Plan dataclass)
7. **H-PERF-06 Cython/Rust port** (lcp_len/lcs_len)

### Pesquisa adicional
8. **Canterbury/Silesia corpus benchmark** (debito academico declarado)
9. **Multi-delta Fase 2** ([1,2,3] support em compare_for_seq)
10. **DOI/Zenodo + paper** (v1.0)

## Quando retomar

Owner pode dizer:
- "Vamos voltar para o checkpoint" → abrir este doc
- "Continuar de X" → buscar X em "Pra retomar" acima
- "Comecar X novo" → ver tickets P2/P3 abertos

Sessao consolidada. Pronto pra continuar quando aplicavel.

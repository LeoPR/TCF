---
title: CPF templated+checked — destilar categoria via dirty
type: dirty-experiment
status: in-progress
tags: [tcf, natureza, templated, checksummed, cpf, pacote-7, fase-1]
created: 2026-05-24
related:
  - experiments/lab/dirty/notas/naturezas-templated-2026-05-24.md
  - tickets/META-TYPE-ENCODERS.md
  - tickets/T-CODE-SCHEMA-BUILDER.md
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
---

# CPF templated+checked — primeira natureza estrutural

## Contexto

Pacote 7 (registrado 2026-05-24, ver
[`naturezas-templated-2026-05-24.md`](../notas/naturezas-templated-2026-05-24.md))
cataloga sub-naturezas TM-CPF/CNPJ/IP/etc. Owner aprovou iniciar
dirty lab pelo **CPF como caso concreto** pra destilar metodologia
genérica.

## Filosofia (acordada 2026-05-24)

- **Opt-in per-value**: cada valor decide se vale comprimir; senão
  fallback literal. RT byte-canonical preservado em todos casos.
- **TCF nao valida semantica**: nao valida "este CPF existe na
  Receita". Apenas detecta formato + check digit derivavel.
- **Estatisticas estruturadas (dimensoes ISO/IEC 25012)**:
  - Genericas (qualquer natureza): apply_rate, accuracy, completeness,
    consistency, compliance
  - Especificas (do tipo): fallback_reasons taxonomy Kim et al. 2003
- **Categoria > instancia**: CPF eh instancia de "Templated + Checked
  + Unique-Discrete". Mesma maquina serve CNPJ/IBAN/Luhn variando
  template + check_fn.

## Mapeamento academico (ver `notas/metodologia-avaliacao-dados-2026-05-24.md`)

Cada dataset segue framework estabelecido na literatura:

| Dataset | Framework | Referencia |
|---|---|---|
| D-CPF-uniform | Equivalence class "happy path" | Myers 1979 |
| D-CPF-clustered | Sintetico-realista | TPC benchmarks |
| D-CPF-mixed | Multi-source schema conflict | Rahm & Do 2000 |
| D-CPF-corrupt | **Mutation testing** (4 mutacoes sistematicas) | DeMillo et al. 1978 |
| D-CPF-edge-* | **Boundary Value Analysis** | Beizer 1995 |
| D-CPF-extra-hostile | **Fuzzing** | Miller et al. 1990 |

Dimensoes de qualidade (NatureApplyStats sub-exp 06): **ISO/IEC 25012**
(accuracy, completeness, consistency, compliance).

Fallback reasons (taxonomia especifica do tipo CPF): adopta Kim et al.
2003 taxonomy of dirty data (format violation, integrity violation,
wrong value).

## Hipoteses

| ID | Hipotese | Esperado | Resultado (2026-05-24) |
|---|---|---|---|
| **H1** | Base-encoding **mascara** padroes substring detectaveis por OBAT | Variante C vence em clustered | **REFUTADA** (com ressalva RT): Variante B vence em RT-OK (-64% uniform, -53% clustered). Compressao matematica densa >> ganho residual de padrao substring. MAS B nao roda RT em corrupt — sub-exp 05 obrigatorio antes de usar em real-world. |
| **H2** | Estatisticas estruturadas (genericas + especificas) viaveis sem overhead | apply_rate + fallback_reasons populados corretamente | A medir em sub-exp 06 |
| **H3** | Categoria "Templated+Checked+Unique" generaliza pra CNPJ + IP via SlotBehavior | Mesmo codigo, 3 instancias funcionam | A medir em sub-exps 07/08 |

## Resultados sub-exps 01-04 (2026-05-24, **RT validado per-row**)

Tabela de compressao **separada por validade de RT** (compressao so'
tem significado se decode reproduz o original — feedback 2026-05-24):

### RT OK (compressao lossless valida)

| Dataset | Raw | M10 (A) | B (base-94) | C (hibrido) | Vencedor RT-OK |
|---|---:|---:|---:|---:|---|
| D-CPF-uniform | 15000 | 18936 (126%, RT 1000/1000) | **6823 (45%, RT 1000/1000)** | 11892 (79%, RT 1000/1000) | **B (-64%)** |
| D-CPF-clustered | 15000 | 18042 (120%, RT 1000/1000) | **6978 (47%, RT 1000/1000)** | 10406 (69%, RT 1000/1000) | **B (-53%)** |
| D-CPF-mixed | 13500 | 16304 (121%, RT 1000/1000) | **10220 (76%, RT 1000/1000)** | 12619 (93%, RT 1000/1000) | **B (-24%)** |

### RT FAIL (compressao comprometida — NAO eh lossless)

| Dataset | Raw | M10 (A) | B (base-94) | C (hibrido) | Sub-exp 05 (B+fallback) |
|---|---:|---:|---:|---:|---:|
| D-CPF-corrupt | 14985 | 18959 (127%, RT 1000/1000) ✓ | 7190 (48%, **RT 989/1000**) ❌ | 12106 (81%, **RT 989/1000**) ❌ | **7356 (49%, RT 1000/1000)** ✓ |

**Os 11 mismatches** em B/C sao exatamente os `corrupt_check` (CPFs
com formato OK mas check digit errado). Pre-tx B e C removem o check
e regen no decode -> reconstrucao **muda** o valor original. Lista
completa em
[`03-.../out_tcf/D-CPF-corrupt-mismatches.txt`](03-variante-B-base-encoded/out_tcf/D-CPF-corrupt-mismatches.txt).

**Sub-exp 05 resolve**: marker prefix `_` distingue literal de
compressed. Encoder STRITTA rejeita check_invalid (e outros tipos
de erro) — caem em fallback literal. RT 1000/1000 com overhead
minimo (~166B vs B sem fallback). B+fallback **substitui** B pura.

### Etapas 3+4 (bordas + extrapolacao, sub-exp 05)

| Dataset | Etapa | rows | tcf | ratio | RT | Observacao |
|---|---|---:|---:|---:|:---:|---|
| edge-single | 3 | 1 | 6 | 40% | OK | 6B pra 1 CPF |
| edge-allsame | 3 | 1000 | **12** | **0.08%** ⚡ | OK | HCC RLE captura repeticao perfeita |
| edge-allcorrupt | 3 | 1000 | 19718 | **134%** ⚠ | OK | 100% literal — pre-tx nao deve aplicar |
| extra-large10k | 4 | 10000 | 68044 | 45.36% | OK | Escala linear |
| extra-hostile | 4 | 1000 | 11356 | **104%** ⚠ | OK | 75% fallback — pre-tx nao deve aplicar |

**Implicacao**: schema_builder Fase 3 precisa detectar
`n_compressible / n_total >= ~50%` antes de ativar pre-tx CPF.
Caso contrario M10 puro eh melhor.

### Achados criticos

1. **Baseline M10 PIORA CPFs em bytes** (120-127% ratio) — mas mantem
   RT 1000/1000 em TODOS os datasets, incluindo corrupt. Eh lossless;
   so' nao comprime.
2. **Variante B (base-94) vence** em **datasets com 100% formato
   valido** (uniform/clustered/mixed): -45% a -64%. Compressao
   matematica vence visibilidade de padrao. **H1 refutada**.
3. **Variante C (hibrido)** intermediaria, nunca vence B onde RT OK.
4. **B e C nao podem ser usadas em datasets dirty** (com check
   invalido) sem sub-exp 05 — geram **silent data corruption** dos
   ~1% corruptos. M10 puro (variante A) seria a unica opcao lossless
   pra dataset corrupt.
5. **Conclusao**: B eh vencedor **condicional** — requer dados
   higienizados OU fallback marker (sub-exp 05) pra ser seguro.

## Variantes a testar (H1 — 3 estrategias competitivas)

| Variante | Estrategia | Bom em | Resultado |
|---|---|---|---|
| **A. Raw + M10** | Sem pre-tx, OBAT/HCC trabalham com strings cruas | (esperado) clustering | **PIOR** (M10 amplifica overhead em CPF) |
| **B. Strip+base+M10** | Remove marcadores + check + base-94 encode | (esperado) aleatorios | **VENCEDOR** (-53 a -64%) |
| **C. Strip+M10 (hibrido)** | Remove marcadores + check, preserva digitos visiveis | (esperado) caso geral | Intermediario; nunca vence B |

## Variantes a testar (H1 — 3 estrategias competitivas)

| Variante | Estrategia | Bom em |
|---|---|---|
| **A. Raw + M10** | Sem pre-tx, OBAT/HCC trabalham com strings cruas | Clustering administrativo (mesmo escritorio, familia) |
| **B. Strip+base+M10** | Remove marcadores + check + base-94 encode | CPFs uniformemente aleatorios |
| **C. Strip+M10 (hibrido)** | Remove marcadores + check, preserva digitos visiveis | Caso geral (hipotese vencedora) |

## Estrutura

```
2026-05-24-cpf-templated-checked/
├── README.md (este)
├── data/
│   ├── gen_dcpf.py          # gerador dataset sintetico reprodutivel
│   ├── D-CPF-uniform.csv    # 1k CPFs uniformes formatados
│   ├── D-CPF-clustered.csv  # 1k com clustering administrativo
│   ├── D-CPF-mixed.csv      # 1k mistos (50% formatados / 50% sem mascara)
│   └── D-CPF-corrupt.csv    # 1k com 5% corruptos (4 tipos de erro)
├── 01-caracterizacao/       # baseline M10 nos 4 datasets
├── 02-variante-A-raw/       # H1 contra-prova A
├── 03-variante-B-base-encoded/  # H1 contra-prova B
├── 04-variante-C-hibrido/   # H1 hipotese vencedora
├── 05-fallback-per-value/   # opt-in com 5% corrupt
├── 06-stats-estruturadas/   # NatureApplyStats genericas + especificas
├── 07-generalizar-CNPJ/     # H3 — mesma maquina, CNPJ
└── 08-IP-tcu-delta/         # H3 — SlotBehavior delta no IP
```

## Sub-experimentos

### 01-caracterizacao (CONCLUIDO 2026-05-24)
- Gerou 4 datasets D-CPF; mediu baseline M10
- **Achado**: M10 PIORA CPFs (120-126% ratio). Pre-tx necessario.

### 02-variante-A-raw (CONCLUIDO via 01)
- Aliase do 01. Baseline pra comparacao com B/C.

### 03-variante-B-base-encoded (CONCLUIDO 2026-05-24)
- Strip + check elide + base-94 + M10
- **Achado**: VENCEDOR. -64% em uniform, -53% em clustered.
- RT OK em uniform/clustered/mixed. FAIL em corrupt (esperado).

### 04-variante-C-hibrido (CONCLUIDO 2026-05-24)
- Strip + check elide + M10 (preserva digitos visiveis)
- **Achado**: Intermediario. Nunca vence B. H1 refutada.

### 05-fallback-per-value (CONCLUIDO 2026-05-24)
- Marker prefix `_` distingue literal vs compressed
- Encoder STRITTA: rejeita check_invalid + format_mismatch +
  chars_invalid + length_wrong + empty
- **RT 100% em TODOS os 9 datasets** (1 + 3 etapa-bordas + 2 etapa-extrap)
- Compressao mantida em compressible-heavy: uniform 45%, clustered 46%
- edge-allsame: 0.08% (RLE HCC explosivo)
- edge-allcorrupt: 134% (todos literal — pre-tx nao deve aplicar)
- extra-hostile: 104% (75% fallback — idem)
- **Conclusao**: B+fallback substitui B pura como vencedora segura;
  heuristica de aplicacao por % compressible eh pre-requisito.

### 06-stats-estruturadas
- `NatureApplyStats` dataclass: apply_rate, confidence_score,
  fallback_reasons (`format_mismatch`, `check_invalid`, `chars_invalid`,
  `length_wrong`)
- Integrar como campo opcional em SideOutputs (`nature_stats`)
- Validar custo desprezivel sem `side_outputs=`

### 07-generalizar-CNPJ
- `TemplatedCheckedEncoder(template="NN.NNN.NNN/NNNN-DD",
  check_fn=mod11_cnpj_dupla)`
- Mesma maquina, params diferentes
- Validar ganho em D-CNPJ sintetico (esperado similar a CPF)

### 08-IP-tcu-delta
- SlotBehavior: 3 slots discrete + 1 slot kind="delta"
- D-IP sintetico com sub-redes (clustering em octetos altos, delta em
  ultimo)
- Validar SlotBehavior gera ganho extra vs todos-discrete

## Criterio de aceite

- [ ] Variante vencedora (A/B/C) identificada empiricamente
- [ ] RT byte-canonical 100% em todos sub-exps
- [ ] NatureApplyStats prontas pra integrar em SideOutputs
- [ ] CNPJ + IP validam categoria abstraida
- [ ] Subsidios pro schema_builder Fase 3 (detect_templated_checked)

## Conexao

- [Naturezas templated](../notas/naturezas-templated-2026-05-24.md) — catalogacao
- [META-TYPE-ENCODERS](../../../../tickets/META-TYPE-ENCODERS.md) — T02 + T04
- [T-CODE-SCHEMA-BUILDER](../../../../tickets/T-CODE-SCHEMA-BUILDER.md) — Fase 3 consumidora
- [Roadmap H-TM-CPF/CNPJ](../notas/roadmap-hipoteses.md) — Pacote 7

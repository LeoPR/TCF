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
- **Estatisticas estruturadas**:
  - Genericas (qualquer natureza): apply_rate, confidence_score
  - Especificas (do tipo): fallback_reasons (format_mismatch /
    check_invalid / chars_invalid / length_wrong)
- **Categoria > instancia**: CPF eh instancia de "Templated + Checked
  + Unique-Discrete". Mesma maquina serve CNPJ/IBAN/Luhn variando
  template + check_fn.

## Hipoteses

| ID | Hipotese | Esperado | Resultado (2026-05-24) |
|---|---|---|---|
| **H1** | Base-encoding **mascara** padroes substring detectaveis por OBAT | Variante C vence em clustered | **REFUTADA**: Variante B vence mesmo em clustered (46.52% vs C 69.37%). Compressao matematica densa >> ganho residual de padrao substring no caso CPF. |
| **H2** | Estatisticas estruturadas (genericas + especificas) viaveis sem overhead | apply_rate + fallback_reasons populados corretamente | A medir em sub-exp 06 |
| **H3** | Categoria "Templated+Checked+Unique" generaliza pra CNPJ + IP via SlotBehavior | Mesmo codigo, 3 instancias funcionam | A medir em sub-exps 07/08 |

## Resultados sub-exps 01-04 (2026-05-24)

| Dataset | Raw | M10 (A) | B (base-94) | C (hibrido) | Vencedor |
|---|---:|---:|---:|---:|---|
| D-CPF-uniform | 15000 | 18936 (126%) | **6823 (45%)** | 11892 (79%) | **B (-64%)** |
| D-CPF-clustered | 15000 | 18042 (120%) | **6978 (47%)** | 10406 (69%) | **B (-53%)** |
| D-CPF-mixed | 13500 | 16304 (121%) | 10220 (76%) | 12619 (93%) | B (com cuidado) |
| D-CPF-corrupt | 14985 | 18959 (127%) | 7190 (48%) ⚠ | 12106 (81%) ⚠ | RT FAIL em ambas |

**Achados criticos**:

1. **Baseline M10 PIORA CPFs** (126% ratio em uniform). Marcadores fixos
   `.` `.` `-` viram overhead estatico; alta entropia dos digitos nao
   ajuda OBAT. Sem pre-tx, TCF eh **anti-compressor** pra CPF.
2. **Variante B (base-94) vence** com larga margem: -64% em uniform,
   -53% em clustered. H1 refutada — compressao matematica vence
   visibilidade de padrao.
3. **Clustered nao salva variante C**: ganho apenas residual (-10pp
   vs uniform). OBAT acha algum padrao no prefixo mas nao compensa
   a densidade que B oferece.
4. **Mixed (50% sem mascara) penaliza B** (76% vs 45% uniform) —
   fallback inline dos 500 sem-mascara explode. Sub-exp 05 deve
   tratar isto com marker explicito (em vez de inline raw).
5. **Corrupt RT FAIL em B e C**: corrupt_check gera CPFs que casam
   regex mas tem check digit errado; pre-tx remove check + regen
   corrige, mudando o valor. Comportamento aceitavel se documentado
   como "data quality fix"; sub-exp 05 implementa policy estrito
   (literal pra check_invalid) como alternativa.

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

### 05-fallback-per-value (PROXIMO — critico)
- Marker explicito no encoded: `<5char>` = base-encoded valido,
  qualquer outro tamanho = literal
- D-CPF-corrupt + D-CPF-mixed como inputs
- Validar RT byte-canonical 100% (sem "data quality fix" implicito)
- Policy configuravel: estrito (literal pra check_invalid) vs loose
  (regen + flag)

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

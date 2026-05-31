# Sub-exp 03 — Cadence-break recovery (H-DA-04)

**Data**: 2026-05-17
**Estado**: ativo
**Macro pai**: [`../README.md`](../README.md)
**Hipotese**: H-DA-04 (`../../notas/roadmap-hipoteses.md`)

## Hipotese a validar

**H-DA-04**: Apos transicao de cardinalidade (ex: `\\9` → `\\10` em
datetime/min), as linhas pos-transicao podem formar sub-pattern
agrupavel. HCC sozinho consegue recuperar?

## Insumo (do fork da tentativa 02)

Body fork do D11d (73 bytes pos-compactacao):

```
\2026-\05-\15 \09:*\0*\0*:\00       (linha 1)
1~2\1*4                              (linha 2)
*8+1|5\2*4                           (linha 3 — agrupa orig 3-10)
1\1*3,4                              (linha 4 — orig 11 = minuto 10)
1~15,6,4                             (linha 5 — orig 12 = minuto 11)
16,7,4                               (linha 6 — orig 13 = minuto 12)
```

Linhas 4-6 cobrem 3 minutos sequenciais ("10", "11", "12") mas tem
estruturas de body **completamente diferentes**:
- length: 8, 9, 7 chars
- estruturas: `R\L*R,R`, `R~R,R,R`, `R,R,R`

Diferenca origem:
- OBAT escolhe maior LCP/LCS greedy a cada string
- s11 ("...09:10:00") quebra a serie porque LCS cresce de 3 pra 4
- s12, s13 referenciam s11 (nova base) + s2, s3 (caudas)
- Cada uma cria seu proprio conjunto de fragmentos

## Plano: audit primeiro, decidir depois

### Fase 1 — Audit (sempre faz)

Script `audit.py`:
- Carrega fork bodies dos 8 datasets
- Identifica pares/triplas consecutivas NAO-compactadas
- Classifica oportunidade residual:
  - **Tipo A**: mesmo length, diffs em digit (escape ou ref) — pode
    ser tratavel
  - **Tipo B**: lengths diferem, mas tokens sobrepostos — complexo
  - **Tipo C**: completamente diferentes — fora de alcance grammar atual
- Reporta bytes residuais por tipo, por dataset

### Fase 2 — Decisao

Apos audit:
- **Se Tipo A tem ganho significativo (>= 30 bytes total)**: implementar
  extensao de detector (allowing ref-digit shifts)
- **Se Tipo A insignificante**: documentar refutacao + apontar pra
  H-DA-02 (precisa OBAT cooperar)
- **Se Tipo B/C dominante**: documentar limite arquitetural

### Fase 3 — Implementar OU concluir

Caminho fork (se tratavel):
- Estender `hcc_fork.py` com novo detector
- Validar RT em D11a-h
- Comparar com tentativa 02

Caminho doc (se refutado):
- Documentar por que HCC sozinho atinge limite
- Marcar H-DA-04 como `refutada (com grammar atual)`
- Apontar dependencia em H-DA-02 (OBAT precisa manter shape)

## Restricoes herdadas

- src/tcf intocado
- Vertice triplice respeitado
- Sem mistura com escape-deduction (Pacote 2)
- Sem mistura com OBAT modification (deixa pra H-DA-02 separado)

## Estrutura prevista

```
03-cadence-break-recovery/
├── README.md          ← este doc
├── audit.py           ← Fase 1
├── audit.md           ← resultado da auditoria
├── (decisao registrada inline em audit.md)
└── [se Fase 3 fork:]
    ├── hcc_fork_v2.py  ← extensao
    ├── run.py
    ├── outputs/
    └── result.md
```

## Critierio de fechamento

H-DA-04 marcado como `confirmada`, `refutada` ou `parcial` no roadmap.
Resultado integrado ao `result.md` deste sub-exp + entrada no diario.

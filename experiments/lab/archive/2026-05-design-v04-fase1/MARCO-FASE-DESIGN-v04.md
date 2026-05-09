# Marco — Fase Design TCF v0.4 Fase 1 (2026-04-27 → 2026-05-08)

Snapshot final da fase de design v0.4. Este documento registra o que
foi produzido, decidido e aprendido. Pode ser lido sem contexto
para reabrir o trabalho no futuro.

## Periodo

**Inicio**: 2026-04-27 (apos M-Acomm + M-schema-scope concluidos)
**Fim**: 2026-05-08 (bancada arquivada)
**Duracao**: ~12 dias de discussao + design

## O que foi produzido

### Labs dirty (8) — todos arquivados nesta pasta

| Data | Lab | Tema |
|------|-----|------|
| 04-27 | flow-pessoas | header v0.4 minimal, encoding implicito |
| 04-28 | flow-categoricos | sort vs grouped, SQL como otimizador externo |
| 04-29 | affix-dict-mesa | Proposta H validada |
| 04-30 | cross-column-dict-mesa | Proposta E reaberta |
| 05-01 | key-graus-mesa | Proposta I (4 graus de chave) |
| 05-02 | chaves-didatico | visualizacao didatica + obsolescencias |
| 05-03 | caminho-feliz-auto | banco didatico com auto-tudo |
| 05-04 | mesa-ampla | escala N1..N4 + reflexao hipotetica |

### Documentos durables (em docs/workbench/research-notes/)

- `2026-05-05-v04-design-recap.md` — D1-D18, propostas, escalabilidade
- `2026-05-05-hipoteses-ativas.md` — 10 hipoteses pendentes
- `2026-05-05-fluxo-experimentos.md` — passos com criterio de pivot
- `2026-05-05-nomenclatura-v04.md` — modos macro + siglas tecnicas
- `2026-05-05-sigla-tcf.md` — Tabular Compact Format
- `2026-05-05-stream-vs-standalone.md` — pendencias HTTP real

### Tickets criados / atualizados

- M-chunks-v04 (novo) — meta de chunks, prioridade #1
- M-llm-integration-future (novo) — categoria LLM separada ⚫
- H-compression-v04-roadmap (atualizado) — Propostas E, H, I + porens
- H-advanced-compression-v03 → movido para closed/ (superseded)
- README de tickets — fase atual atualizada, prefixo `L-` adicionado

### Codigo / API

- `src/tcf/__init__.py` — docstring atualizada com TCF=Tabular Compact Format

### Labs clean

- `experiments/lab/clean/EXP-003a-calibration/` — calibracao gzip(CSV) + extensao sort
- `experiments/lab/clean/EXP-003b-tcf-vs-gzip/` — HP-T1 decisor

## 18 decisoes consolidadas (D1-D18)

**Formato**:
- D1 modelo unico: tudo eh chunk
- D2 RLE nao atravessa boundary (rebreak)
- D3 menor chunk = 1 grupo completo
- D4 default monolitico (sem `chunks=`)
- D6 sintaxe `@chunk`/`@end`/`n=`/`chunks=`
- D16 DICT inline com a coluna

**Camadas**:
- D5 sync vs async eh transporte, nao formato
- D11 batch eh unidade de TRANSPORTE
- D12 TCF "imune ao transporte"
- D13 EncodeManager coordena saidas

**Filosofia**:
- D14 TCF eh fundamentalmente arquivo de transporte
- D15 implementacoes modulares testadas em lab dirty primeiro

**Escopo**:
- D7 multi-canal adiado v0.5+
- D8 SQL como gerador de Plan adiado v0.5+
- D9 LLM fora desta fase (escopo separado ⚫)
- D10 execucao sincrona em passos

**Identidade**:
- D17 TCF = **Tabular Compact Format**
- D18 nomenclatura: `raw/compact/smart/extreme` + siglas tecnicas

## 3 propostas validadas

| Proposta | Lab | Ganho medido |
|----------|-----|---------------|
| **E** Cross-column DICT | 04-30 | -22% medio em vocabs compartilhados |
| **H** Affix-aware DICT | 04-29 | -50 a -80% em prefixos limpos |
| **I** Lossless key elimination | 05-01 | -10 a -12% em FK grau 2 |

## Achados experimentais (clean labs)

### EXP-003a — Baseline gzip

```
gzip(CSV) ganha 54-88% sobre CSV bruto, media 70%
```

### EXP-003a extensao — Sort sozinho

```
CSV ordenado + gzip vs CSV naive + gzip: -2.31% medio
NAO substitui TCF (perde para compact em todos os 5 datasets)
```

### EXP-003b — HP-T1 decisor

```
TCF smart+gz vs compact+gz: -14% medio (intermediario)
2 clusters claros:
  - Estrutural (relacional/categorico): -12% a -29% — smart vale
  - Numerico/unico: -0.1% a -3.8% — compact basta
Decisao: caminho hibrido com auto-bypass apos gzip
```

### Verificacao stream vs standalone

```
gzip stream sem flush ≈ standalone (0% diff)
gzip stream com flush por 1KB: +5 a +22% pior
Implica: HP-T2 chunks pequenos prejudicam canal
```

## Obsolescencias categorizadas

DEFAULT REMOVIDO (mas pode voltar via flag para ablacao):
- DICT no header da tabela
- L3 ativando em cardinality > N/2
- L3 per-column quando cross vence
- Header verboso

BANIDO (nunca emitir):
- Sort lexicografico em ints
- `sorted_by=` quando eh grouped
- RLE atravessa chunk

## Pendencias herdadas

Ja registradas em research-notes:

1. **Implementar Plan + chunks** no core (M-chunks-v04 Bloco 1)
2. **EXP-005 + 006** — Propostas B (types) e F (auto-sortedness) ainda
   sem lab dirty
3. **EXP-007** — chunks × batch × gzip (HP-T2) — bloqueado por #1
4. **EXP-008** — sintese end-to-end (HP-T3) — bloqueado por #1+#3
5. **Auto-bypass apos gzip** — atual mede bytes antes; pendente
6. **HTTP real** — testes P1-P7 com servidor (Apache/Nginx/Caddy)
7. **brotli/zstd** — instalar e re-rodar EXP-003a com cobertura completa

## Como reabrir o contexto

Para retomar o trabalho:

1. Ler este marco
2. Ler `2026-05-05-v04-design-recap.md` (recap consolidado)
3. Ler `2026-05-05-hipoteses-ativas.md` (o que falta testar)
4. Ler `2026-05-05-fluxo-experimentos.md` (proxima ordem)
5. Ler `EXP-003a/README.md` e `EXP-003b/README.md` (achados clean)

## Nota especial

A fase teve **8 labs dirty + 2 labs clean + 6 documentos durables +
3 tickets criados/atualizados + 18 decisoes**. Foi extensa mas
metodica.

A pergunta-bloqueadora HP-T1 foi respondida: nao eh binaria, ha
clusters. Caminho hibrido com auto-bypass agressivo eh o
recomendado.

Proximo bloco: EXP-005/006 ou implementacao do core. Decidir caso
a caso conforme prioridades.

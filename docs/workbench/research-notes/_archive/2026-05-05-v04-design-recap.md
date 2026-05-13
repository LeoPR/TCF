# Recap consolidado — design TCF v0.4 (2026-04-27 → 2026-05-05)

Documento de fechamento de uma fase de design. Captura o que foi
discutido, validado em lab dirty, registrado em ticket, e o que esta
pronto para implementacao.

## Linha do tempo

| Data | Lab dirty | Resultado |
|------|-----------|-----------|
| 2026-04-27 | flow-pessoas (3 ciclos) | header v0.4 minimal, encoding implicito, line-ending detect |
| 2026-04-28 | flow-categoricos (3 ciclos) | sort vs grouped, SQL como otimizador externo |
| 2026-04-29 | affix-dict-mesa | Proposta H validada matematicamente |
| 2026-04-30 | cross-column-dict-mesa | Proposta E reaberta (-22% vs L3) |
| 2026-05-01 | key-graus-mesa | Proposta I validada (-10% a -12%) |
| 2026-05-02 | chaves-didatico | tensao bytes vs semantica visualizada |

## Decisoes congeladas (D1-D18)

Documentadas em [M-chunks-v04](../tickets/open/M-chunks-v04.md):

**Formato:**
- D1 Modelo unico: tudo eh chunk
- D2 RLE nao atravessa boundary (rebreak)
- D3 Menor chunk = 1 grupo completo
- D4 Default monolitico = ausencia de `chunks=`
- D6 Sintaxe: `@chunk`, `@end`, `n=N|?`, `chunks=N|?`

**Camadas:**
- D5 Sync vs async eh transporte, nao formato
- D11 Batch eh unidade de TRANSPORTE
- D12 TCF "imune ao transporte"
- D13 EncodeManager coordena 1+ saidas

**Filosofia:**
- D14 TCF eh fundamentalmente arquivo de transporte (CSV/JSON-like)
- D15 Implementacoes modulares testadas em lab dirty primeiro

**Escopo:**
- D7 Multi-canal adiado v0.5+
- D8 SQL como gerador de Plan adiado v0.5+
- D9 LLM fora desta fase
- D10 Execucao sincrona em passos (modulos prontos para async)

**Sintaxe (consolidada 2026-05-05):**
- D16 **DICT inline com a coluna** (nao no header da tabela)
  - Razao: leitura sequencial do decoder e LLM; cada coluna autocontida;
    facilita chunks/multi-canal futuros
  - Forma: `coluna: dict=v1,v2,v3` na primeira linha da coluna
  - Quando bypass: `coluna:` sem `dict=`
  - Quando cross-DICT: `coluna: dict=GLOBAL_1` (referencia)

**Identidade e nomenclatura (consolidada 2026-05-05):**
- D17 **TCF = Tabular Compact Format**
  - T = Tabular (lógico, multi-tabela; cobre Proposta I)
  - C = Compact (todas tecnicas de compressao integradas)
  - F = Format (especificacao)
  - Mantem sigla; redefinicao do significado no v0.4
- D18 **Modos macro + siglas tecnicas**
  - Modos: `raw` / `compact` / `smart` / `extreme` (default = smart)
  - Tecnicas: RLE / DICT / XDICT / AFFIX / KEY-ELIM / SORT / STRAT-STATS / TYPE / CHUNK
  - Modificadores: `auto` (default) / `force` / `off`
  - L0/L1/L2/L3 saem da API publica

## Comparacoes obsoletas — categorizadas

Reclassificadas em 3 niveis (2026-05-05):

- **DEFAULT REMOVIDO**: forma vencedora eh padrao; antiga sai do auto-tudo
- **DISPONIVEL P/ ABLACAO**: pode ser ativada via flag para experimento cientifico
- **BANIDO**: nunca emitir, nem em ablacao (eh bug ou mentira semantica)

| Comparacao | Vencedor | Status |
|-----------|----------|--------|
| L3 preserva PK grau 2 vs elimina | eliminar | DEFAULT REMOVIDO; ablacao OK |
| DICT no header vs inline | inline | DEFAULT REMOVIDO; ablacao OK (chunks podem mostrar valor) |
| L3 ativando em cardinality > N/2 vs bypass | bypass | DEFAULT REMOVIDO; ablacao OK |
| L3 per-column vs cross-DICT quando overlap > 50% | cross | DEFAULT REMOVIDO; ablacao OK |
| Header verboso vs minimal | minimal | DEFAULT REMOVIDO; ablacao OK |
| Sort lexicografico em ints | numerico | **BANIDO** (eh bug) |
| `sorted_by=` quando eh grouped | `grouped_by=` | **BANIDO** (mentira semantica) |
| RLE atravessa chunk | rebreak | **BANIDO** (quebra autocontencao) |

Labs futuros aplicam **default vencedor automaticamente**. Para ablacao
cientifica, encoder aceita `legacy_mode={...}` opcional.

## Escalabilidade (medida 2026-05-05)

Lab `2026-05-04-mesa-ampla` mediu TCF v0.4 caminho-feliz vs naive:

| Nivel | Rows | naive | TCFv04 | Ganho |
|-------|------|-------|--------|-------|
| N1 (1 tabela, 5 rows) | 5 | 74 | 109 | **+47.3% (perde)** |
| N2 (1 tabela, 50 rows) | 50 | 1617 | 1027 | **-36.5%** |
| N3 (3 tabelas com FKs) | 110 | 1895 | 1232 | **-35.0%** |
| N4 (5 tabelas, 1100 rows) | 1100 | 20077 | 11672 | **-41.9%** |

**Ponto de equilibrio**: ~N=20-30 rows. Abaixo, overhead dos markers
domina; TCF deveria fallback automatico para forma minimal (ou CSV
puro). Acima, ganho consistente -35% a -42%.

Mais tabelas + mais relacoes = mais ganho relativo (cross-DICT, key
elimination e affix se reforcam mutuamente).

## Propostas de compressao (status)

### Selecionadas Sprint 1+2 (com ganho mensurado em M-Acomm)

| Id | Proposta | Status | Lab dirty? |
|----|----------|--------|------------|
| A | Stratified STATS | selecionada | NAO testada |
| B | Type-preserving decode | selecionada | NAO testada |
| F | Auto-detect sortedness | selecionada | parcial (flow-categoricos ciclo 2) |

**Pendencia**: A, B, F nao tem lab dirty dedicado. Vale criar antes
de implementar.

### Registradas com poréns (validadas em lab dirty)

| Id | Proposta | Ganho medido | Status |
|----|----------|---------------|--------|
| E | Cross-column DICT | -21% a -26% (5/7 cenarios) | reaberta 2026-05-05 |
| H | Affix-aware DICT | -50% a -80% (3/7 cenarios) | registrada |
| I | Lossless key elimination | -10% a -12% (2/3 cenarios) | registrada |

### Descartadas

| Id | Proposta | Razao |
|----|----------|-------|
| C | Delta encoding | adiar (alto custo, util em time-series) |
| D | Frame-of-Reference | baixo impacto |
| G | Schema_qualifier | separar em packages/tcf-extras |
| Nivel 3 (n-gram) | substring DICT generico | sobrepoe gzip |

## Conceitos novos consolidados

### EmissionPlan (`Plan`)

Estrutura central que descreve "como emitir":

```python
@dataclass
class Plan:
    group_by: list[str] | None = None
    order: str = "input"          # "input" | "lex" | "numeric" | "frequency_desc"
    batch_size: int | None = None
    batch_unit: str = "groups"    # "groups" | "rows"
```

Plan eh **contrato estavel**. Otimizadores (Counter, SQL futuro,
heuristica) produzem Plans. Encoder consome Plans.

### Hierarquia de DICT em niveis

```
Nivel 0 — sem DICT          (L0/L1/L2 atuais)
Nivel 1 — DICT por valor    (L3 atual)
Nivel 2 — DICT por afixo    (Proposta H — condicional)
Nivel 3 — DICT por substr   (n-gram — DESCARTADO, gzip resolve)
```

### Graus de chave (Proposta I)

```
Grau 0 — UUID, hash external-facing      → PRESERVAR
Grau 1 — Natural com semantica externa   → PRESERVAR
Grau 2 — Sintetica local                 → ELIMINAR + regenerar
Grau 3 — Derivada/composta interna       → RECONSTRUIR
```

### 3 camadas independentes

```
1. ENCODER TCF         (formato fixo, chunks autocontidos)
        │
        ▼
2. BATCHER             (agrupa N chunks; v0.5+)
        │
        ▼
3. COMPRESSOR generico (gzip/brotli/zstd; HTTP/3 nativo)
```

TCF nao reimplementa o que ja existe (camadas 2 e 3). HTTP/3 + brotli
oferecem nativamente.

## Tickets criados/atualizados

| Ticket | Status |
|--------|--------|
| [M-chunks-v04](../tickets/open/M-chunks-v04.md) | criado, prioridade #1 |
| [M-llm-integration-future](../tickets/open/M-llm-integration-future.md) | criado, categoria ⚫ separada |
| [H-compression-v04-roadmap](../tickets/open/H-compression-v04-roadmap.md) | atualizado: Propostas E/H/I |
| [README dos tickets](../tickets/README.md) | atualizado com prefixo `L-` |

## O que esta pronto para implementar

### Bloco 1 — Implementacoes opt-in (auto-bypass garante seguranca)

| # | Feature | Tickets | Lab dirty? |
|---|---------|---------|-----------|
| 1 | Plan (dataclass + fluxo basico) | M-chunks-v04 (Bloco 1) | nao precisa (eh estrutura) |
| 2 | Chunk format (`@chunk`, `@end`) | M-chunks-v04 (Bloco 1) | precisa antes |
| 3 | Encoder/decoder chunked sincrono | M-chunks-v04 (Bloco 2) | depende #1+#2 |
| 4 | Auto-bypass agressivo (todas as propostas) | H-roadmap (varias) | parcial |

### Bloco 2 — Propostas com ganho mensurado

| # | Feature | Lab dirty completo? |
|---|---------|---------------------|
| 5 | Affix-DICT (H) | sim |
| 6 | Cross-column DICT (E) | sim |
| 7 | Key elimination (I) | sim |
| 8 | Stratified STATS (A) | NAO — falta lab |
| 9 | Type-preserving decode (B) | NAO — falta lab |
| 10 | Auto-detect sortedness (F) | parcial |

### Bloco 3 — Adiados v0.5+

- SQL como gerador de Plan
- Multi-canal (colunas em transports separados)
- Coordinator paralelo
- EncodeManager multi-saida
- Self-batching com page/ranking
- Streaming live

## Hipoteses ainda nao testadas (lab dirty pendente)

| H | Descricao | Onde |
|---|-----------|------|
| H-A1 | Stratified STATS sobe Linha A em filter+agg | Proposta A |
| H-B1 | Type-preserving preserva int/float/bool exato | Proposta B |
| H-F1 | Auto-detect sortedness escolhe coluna correta | Proposta F |
| H-chk-1..6 | Chunks em varias granularidades | M-chunks-v04 |

## Caminho feliz proposto (proximo passo)

Banco sintetico didatico expandido aplicando TODAS as compactacoes
automaticas:
- pessoas (PK grau 2 + nome + categoria)
- produtos (PK grau 2 + nome + categoria)
- pedidos (PK grau 2 + 2 FKs grau 2 + status enum)
- categorias (DICT compartilhado entre pessoas e produtos — Proposta E)

Aplicar simultaneamente:
- L3 (DICT por valor)
- Proposta E (cross-column DICT em categorias)
- Proposta I (eliminate PKs grau 2 e FKs)
- Proposta H (se houver afixos)
- Auto-bypass em tudo
- Header minimal v0.4
- Chunks (1 implicito por enquanto)

Comparar:
- naive (CSV)
- L3 atual (sem novas propostas)
- L3 + auto-tudo (caminho feliz)

Lab proposto: `2026-05-03-caminho-feliz-auto`.

## Conclusao da fase de design

A fase de design (2026-04-27 → 2026-05-05) entregou:
- Filosofia clara (D1-D16)
- 3 propostas novas validadas (E, H, I)
- 3 propostas pre-existentes ainda sem lab (A, B, F)
- Conceitos arquiteturais consolidados (Plan, chunks, camadas)
- 7 labs dirty rodados com matematica formal
- Tickets organizados (M-chunks-v04 prioridade #1)
- Bancada arquivada: `experiments/lab/archive/2026-05-design-v04-fase1/`

## Hipoteses ativas pendentes

Rastreadas em [2026-05-05-hipoteses-ativas.md](2026-05-05-hipoteses-ativas.md):

- **3 propostas tecnicas**: A (stratified STATS), B (type-preserving), F (auto-sortedness)
- **3 hipoteses operacionais (HP-T1/T2/T3)**: interacao com gzip/brotli no transporte
- **4 hipoteses arquiteturais**: schema, multi-canal, telemetria, LLM

**HP-T1 e bloqueadora**: se gzip do transporte saturar a compressao,
todo esforco em compressao estrutural avancada (E, H, I) pode ser
desperdicio.

Proxima fase: **EXP-003 primeiro** (TCF vs transporte) → decide se
investimos no caminho feliz ou ficamos com mode=compact + gzip externo.

## Outros documentos de fase

- [2026-05-05-nomenclatura-v04.md](2026-05-05-nomenclatura-v04.md) — proposta `raw/compact/smart/extreme` + siglas tecnicas
- [2026-05-05-sigla-tcf.md](2026-05-05-sigla-tcf.md) — reflexao sobre TCF como Textual vs Tabular
- [2026-05-05-hipoteses-ativas.md](2026-05-05-hipoteses-ativas.md) — 10 hipoteses pendentes

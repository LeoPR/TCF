---
title: M-chunks-v04 — chunks como modelo unificado de emissao TCF v0.4
type: meta
status: OPEN
priority: HIGH
created: 2026-05-05
origin: Conversas 2026-04-28..2026-05-05 sobre formato v0.4, lotes e plano de emissao
user_quotes:
  - "tudo é chunk; mandar tudo de uma vez é só um chunk implicito monolitico"
  - "RLE nao atravessa boundary; chunks autocontidos vencem 1-2 bytes a mais"
  - "nao precisamos de paralelismo real agora; modulos consistentes chamados em ordem"
  - "foco no formato e no suporte pra poder manter ele depois"
see_also:
  - docs/workbench/tickets/open/H-compression-v04-roadmap.md
  - docs/workbench/tickets/open/M-architecture-v03.md
  - experiments/lab/dirty/2026-04-27-flow-pessoas/
  - experiments/lab/dirty/2026-04-28-flow-categoricos/
---

# Meta-ticket: chunks como modelo unificado v0.4

## Visao

**Tudo no TCF v0.4 e um chunk.** Arquivo monolitico (caso v0.2 atual)
e simplesmente "1 chunk implicito". Batch eh "N chunks numerados".
Stream/live eh "chunks=? + @end". Um modelo unico, decoder unico,
formato estavel.

Compressao (RLE/DICT/sort) **nunca atravessa boundary de chunk**:
cada chunk decodifica autocontido. Custo aceito: 1-5% bytes a mais
nas fronteiras. Beneficio: chunks podem chegar fora de ordem,
descartar parcial, ou ser projetados em transporte futuro.

## Por que isso importa AGORA (mesmo sem paralelismo real em v0.4)

A decisao do **formato de chunk** nao pode ser adiada para v0.5:
introduzir delimitadores depois sera breaking change. Ja em v0.4:

1. **Definir formato** completo (sintaxe @chunk, @end, n=, chunks=)
2. **Implementar encoder/decoder** suportando 1..N chunks
3. **Backward compat**: arquivo sem `chunks=` continua valendo (= 1 chunk)
4. **Adiar paralelismo real**: estrutura modular sincrona em passos

Quando v0.5 introduzir transporte assincrono, o formato ja estara
pronto e os modulos prontos para virar paralelos sem reescrita.

## Decisoes ja tomadas (consolidadas em conversas)

| # | Decisao | Justificativa |
|---|---------|---------------|
| D1 | Modelo unico: tudo e chunk | elimina dois caminhos no decoder |
| D2 | RLE nao atravessa boundary (estrategia "rebreak") | autocontencao > -1% bytes; perda recuperada via D11 |
| D3 | Menor chunk = 1 grupo completo (todas colunas alinhadas) | unidade decodavel real |
| D4 | Default monolitico = ausencia de `chunks=` | zero overhead p/ caso comum |
| D5 | Sync vs async eh transporte, NAO formato | formato suporta ambos transparentemente |
| D6 | Sintaxe: `@chunk` + `@end` + `n=N\|?` + `chunks=N\|?` | tendencia (D1 desta task confirma) |
| D7 | Multi-canal (colunas paralelas) adiado para v0.5+ | TCF ja eh colunar por construcao |
| D8 | SQL como gerador de Plan adiado para v0.5+ | core fica leve |
| D9 | LLM fora desta discussao | concerns separados (ver M-llm-integration-future) |
| D10 | Execucao sincrona em passos (v0.4) com modulos prontos para async | estrutura prepara, nao implementa |
| D11 | **Batch eh unidade de TRANSPORTE, nao de formato** | recupera bytes via compressao generica sem mexer no formato TCF |
| D12 | **TCF "imune ao transporte"**: gera blocos; camada superior coordena | preserva separacao de concerns; encoder nao sabe quem consome |
| D13 | **EncodeManager** (camada acima do encoder) coordena 1+ saidas | v0.4 = 1 saida simples; v0.5+ = multi-saida possivel |
| D14 | **TCF e fundamentalmente arquivo de transporte (como CSV/JSON)** | nao se pode exigir camadas externas; pode ser usado standalone |
| D15 | **Implementacoes modulares testadas em lab dirty primeiro; experimentos formais decidem o que sobrevive** | em cenario complexo desconhecido, alguma feature pode nao caber |
| D16 | **DICT inline com a coluna** (nao no header) | leitura sequencial; chunk-friendly; multi-canal futuro |
| D17 | **TCF = Tabular Compact Format** (sigla mantida, significado redefinido v0.4) | T=Tabular, C=Compact, F=Format — cobre escopo expandido |
| D18 | **Nomenclatura: modos macro + siglas tecnicas** | `raw/compact/smart/extreme` + RLE/DICT/XDICT/AFFIX/KEY-ELIM/SORT etc |

## Filosofia de desenvolvimento (consolidada D14+D15)

TCF NAO assume client-server, transporte HTTP/3, ou compressor
generico disponivel. **Pode ser usado como arquivo standalone**,
igual a CSV/JSON. Tudo que adicionamos eh:

> "padrao para guiar um possivel client/server a ter o maximo
> desempenho com os dados, **quando esse contexto existir**"

Quando NAO existir contexto rico (ex: TCF rodando dentro de um
script Python isolado, lendo de arquivo, sem rede), as camadas
2 e 3 (batcher, compressor generico) simplesmente nao se aplicam.
O formato deve continuar valido e util como portador de dados.

### Estrategia de implementacao

```
1. LAB DIRTY (mesa)        ──▶  intuicao matematica + exemplos
                                (formulas validadas em dados variados)
2. PROTOTIPOS MODULARES    ──▶  cada feature em modulo isolado, opt-in
3. EXPERIMENTOS FORMAIS    ──▶  todas as camadas implementadas
                                rodam em cenarios de escala real
4. CORTE                   ──▶  o que tiver evidencia INDUTIVA sobrevive;
                                resto vira frozen ticket ou descarte
```

Cada feature segue esse pipeline. Affix-DICT, chunks, batches, plan,
EmissionPlan: todos passam pela mesma trilha.

## Camadas: chunk (formato) vs batch (transporte)

**Insight chave (consolidado 2026-05-05)**: o conceito de batch
**nao muda o formato TCF**. Recupera bytes (ex: cross-chunk RLE
patterns como `5*abacaxi + 2*abacaxi` → `7*abacaxi` implicito)
via **compressao generica do batch inteiro**, sem o RLE TCF
atravessar boundaries.

```
3 camadas independentes:

  1. ENCODER TCF         formato fixo, chunks autocontidos
        │                (escopo do M-chunks-v04)
        ▼
  2. BATCHER             agrupa N chunks (unidade de buffer/transporte)
        │                (escopo de v0.5+ ou camada externa)
        ▼
  3. COMPRESSOR generico gzip/brotli/zstd aplicado ao batch
        │                (HTTP/3 + Content-Encoding: br ja oferece)
        ▼
       rede / arquivo
```

**Por que essa separacao importa:**

- Camada 1 (TCF) garante "chunk decodifica autocontido"
- Camada 2 (batcher) define quanto buffer transmitir junto
- Camada 3 (gzip/brotli) acha padroes cross-chunk SEM mexer no formato
- HTTP/3 moderno ja oferece camadas 2 e 3 nativamente
- TCF nao reimplementa nada que ja existe

**Telemetria de batch** (ex: "batch de 10 chunks comprime -30% em
80ms; batch de 50 leva 200ms mas comprime -45%") fica na camada 2/3
fora do TCF. Cliente/servidor negociam dinamicamente sem o formato
saber.

**Princípio "TCF imune ao transporte"**: enquanto encoder gera,
assim que um "bloco" termina, a camada superior (EncodeManager)
decide o destino — file, multi-saida, multiplexed channels. O
encoder nao sabe nem se importa.

## Principio arquitetural — "map-reduce sincrono simulado"

Ao inves de paralelismo real, v0.4 implementa modulos consistentes
chamados sequencialmente, com interfaces que **suportariam** paralelo:

```
Plan ──▶ ChunkPlanner ──▶ [chunk_1, chunk_2, ..., chunk_N]
                              │
                              ▼ (chamado em ordem agora; pode ser
                                 paralelo no futuro sem mudar API)
                          Encoder.emit_chunk(i)
                              │
                              ▼
                          EncodeManager.handle(chunk_bytes)
                              │
                              ▼ (1 saida em v0.4; multi em v0.5+)
                          formato final (bytes)
```

Cada chunk e independente — o `EncodeManager` apenas concatena com
delimitadores em v0.4 (1 saida), mas a interface ja suporta multi-saida
(disparar canais separados para batches diferentes em v0.5+).

v0.4 eh **execucao sequencial**; v0.5+ pode trocar o manager por
versao paralela ou multi-output sem mexer nos outros modulos.

Mesma simetria no decoder: `ChunkParser` -> `ChunkDecoder` ->
`Reducer` (junta colunas/grupos em rows). O decoder tambem e
"imune ao transporte" — recebe blocos, monta saida.

## Sub-tickets (a criar conforme avancarmos)

### Bloco 1 — Especificacao do formato (foco do v0.4)

| Sub-ticket | Descricao | Status |
|-----------|-----------|--------|
| T-plan-spec | Definir dataclass `Plan(group_by, order, batch_size, batch_unit)` | nao criado |
| T-chunk-format-spec | Gramatica formal: `@chunk [N/total]`, `@end`, `chunks=`, `n=` | nao criado |
| T-chunk-rebreak-rule | Regra: compressao nao cruza boundary; testes | nao criado |
| T-monolithic-implicit | Backward compat: ausencia de `chunks=` -> 1 chunk | nao criado |

### Bloco 2 — Implementacao sincrona em modulos

| Sub-ticket | Descricao | Status |
|-----------|-----------|--------|
| T-chunk-planner | Modulo que recebe `Plan + rows` -> lista de chunks | nao criado |
| T-chunk-emitter | Modulo que pega 1 chunk + emite bytes (RLE local ao chunk) | nao criado |
| T-coordinator-sync | Coordinator sequencial que concatena chunks | nao criado |
| T-decoder-chunked | Decoder que parseia 1..N chunks e remonta rows | nao criado |

### Bloco 3 — Validacao via dirty labs

| Sub-ticket | Descricao | Status |
|-----------|-----------|--------|
| E-chunk-loss-measurement | Medir perda de compressao por chunk size em datasets reais | nao criado |
| E-chunk-granularity-study | Regra "chunk size = f(cardinality, n_rows)" | nao criado |
| E-orderless-decoding | Validar chunks fora de ordem (preparacao async) | nao criado |
| E-small-tables-regression | Voltar a tabelas pequenas com chunks (regressao) | nao criado |

### Bloco 4 — Adiados para v0.5+ (mencionados para nao perder)

| Adiado | Por que adiar |
|--------|---------------|
| Multi-canal (colunas em transports separados) | precisa transporte real |
| Plan via SQL (otimizador alternativo) | core fica leve em v0.4 |
| Chunks fora de ordem REAIS na rede | requer transporte |
| Coordinator paralelo | estrutura ja preparada em v0.4 |
| **Batcher (camada 2)** + telemetria dinamica | unidade de transporte, nao de formato |
| **Compressor generico no batch** (gzip/brotli/zstd) | HTTP/3 oferece nativo; nao reimplementar |
| **EncodeManager multi-saida** (varios canais simultaneos) | v0.4 e single-output; interface ja suporta |
| **Self-batching de chunks via page/ranking** | "agrupamento de agrupamentos"; v0.5+ se vier |

## Hipoteses a testar (dirty labs)

| H | Hipotese | Lab |
|---|----------|-----|
| H-chk-1 | Chunks por grupo: perda <5% vs monolitico | flow-pessoa-categoria-chunks |
| H-chk-2 | Cada chunk decodifica em qualquer ordem | flow-async-orderless |
| H-chk-3 | Granularidade otima depende de cardinality | flow-chunk-granularity |
| H-chk-4 | `batch_size=N` produz N+1 chunks deterministicamente | flow-batch-determinism |
| H-chk-5 | Tabelas pequenas (5-20 rows) sobrevivem com chunks | flow-small-tables-regression |
| H-chk-6 | Compressor generico (gzip/brotli) no batch recupera 70-90% da perda de rebreak | flow-batch-transport-compress |

## Estrategia de execucao proposta

**Diretriz consolidada 2026-05-05 (user)**: voltar ao cenario inicial
de pessoas (flow-pessoas, 10 nomes unicos) e **forcar TODAS as
combinacoes do formato v0.4** ali. Cenario adverso para compressao
(nomes unicos = RLE/DICT inuteis) eh ideal para validar que o
**formato funciona** independente da eficiencia.

> Principio: "vai ficar horrivel em compressao se forcarmos o formato,
> mas ao mesmo tempo testariamos do mesmo jeito."
>
> Se o formato sobrevive ao cenario MIN (pessoas), sobrevive em qualquer
> lugar. Compressao e metrica secundaria nesta fase.

### Ordem de validacao (foco em formato, nao em bytes)

1. **Lab F1 — flow-pessoas-formato-v04**: re-rodar pessoas com
   TODAS as combinacoes do formato v0.4
   - monolitico (= 1 chunk implicito; baseline)
   - chunked com `chunks=N` numerado
   - chunked com `chunks=?` + `@end`
   - chunk de 1 row, 5 rows, 10 rows
   - levels 0/1/2/3 dentro de cada um
   - **Criterio**: roundtrip exato em todas as combinacoes;
     bytes podem ser piores que CSV — nao eh problema aqui.

2. **Lab F2 — flow-categoricos-formato-v04**: replicar todas as
   combinacoes em cenario MAX (s_nationkey)
   - **Criterio**: mesmo que F1; agora bytes podem ser melhores

3. **Lab F3 — flow-pessoa-categoria-formato-v04**: mix
   (s_nationkey + s_name)
   - **Criterio**: chunk-por-grupo deve manter coerencia entre colunas

4. **Lab F4 — flow-async-orderless** (H-chk-2):
   - Embaralhar chunks pre-decode em todos os casos acima
   - Decoder remonta resultado correto

Apos F1-F4 fechados: **revisar formato**, ajustar arestas, e so entao
decidir implementacao (sub-tickets do Bloco 1+2).

### Diferenca para a estrategia anterior

Antes: priorizar cenarios onde TCF brilha (categoricos, mix).
Agora: priorizar **robustez do formato em cenarios adversos primeiro**.
Se passa em pessoas (10 nomes unicos), passa em qualquer lugar.

Hipoteses de compressao (H-chk-1, H-chk-3, H-chk-6) ficam para
**depois** de fechar o formato — sao otimizacoes mensuraveis sobre
um formato que ja funciona.

## Decisoes pendentes

| Q | Pergunta | Tendencia |
|---|----------|-----------|
| Q-delim | `@chunk` ou `---` ou `--` para delimitador? | `@chunk` (visivel, hard to confuse) |
| Q-name | `Plan` ou `EmissionPlan`? | `Plan` (curto) |
| Q-batch-unit | `batch_size` em grupos ou rows? | grupos default; flag p/ rows |
| Q-numbering | Numerar chunks em sync (`@chunk 2/4`)? | sim quando `chunks=N` (ajuda recovery) |
| Q-stats | STATS por chunk ou globais (rodape)? | adiar; testar nos labs |

## Riscos

- **Perda de compressao** desconhecida em datasets reais — medir antes
- **Complexidade do decoder** aumenta (parsear delimitadores, gerenciar estado entre chunks)
- **Regressao em tabelas pequenas**: chunk overhead pode comer ganho de TCF
- **Granularidade errada**: chunks muito pequenos = overhead delim > dado;
  chunks muito grandes = perde paralelismo de uso futuro
- **Tentar paralelismo cedo demais**: distrai do formato

## Criterio de aceite

- [ ] Formato `@chunk`, `@end`, `n=`, `chunks=` documentado
- [ ] `Plan` dataclass definido com campos congelados para v0.4
- [ ] Encoder/decoder suportam 1..N chunks (testes passam)
- [ ] Backward compat: arquivos v0.2 lidos como 1 chunk implicito
- [ ] Lab 1 + 2 + 3 fechados com findings
- [ ] Documentacao no `docs/theory/components/` atualizada
- [ ] CHANGELOG entry v0.4-chunks

## Impacto estimado

- Especificacao + dirty labs: 1-2 semanas
- Implementacao do encoder chunked: 1 semana
- Implementacao do decoder chunked: 1 semana
- Backward compat + regressao: 3-5 dias
- Documentacao: 2-3 dias

Total: **~4-5 semanas focadas**, podendo ser fatiado em sprints.

## Como este meta-ticket interage com outros

- **H-compression-v04-roadmap**: chunks complementam (auto-detect sort,
  type-preserving, stratified STATS continuam validos)
- **M-architecture-v03**: split em packages/tcf nao precisa esperar chunks;
  pode rodar em paralelo
- **M-llm-integration-future**: nao tocado
- **E-format-comparison-bench**: ganha cenarios "chunked vs monolitico"

## Notas para revisar este meta-ticket

Quando reabrir:

- Snapshot deste arquivo no commit `<ts>`
- Estado dos labs: `experiments/lab/dirty/2026-04-*` ja roodaram
- Ja decidido: D1-D10 (ver tabela acima)
- Foco do v0.4: **formato + modulos sincronos**, nao paralelismo
- Se algo ja estiver implementado: ver `src/tcf/encoder.py` por mencao
  a `Plan`, `Chunk`, `@chunk`
- Ticket relacionado: H-compression-v04-roadmap (Sprint 1+2 deve
  rodar em conjunto com este)

# 0018 — Roadmap de formato v2.0 (fallback identity, dicionario, lossy)

**Status**: proposed
**Date**: 2026-05-27
**Deciders**: project owner
**Tags**: v2.0, format, roadmap, low-cardinality, lossy, dictionary, fallback

## Context and Problem Statement

A auditoria profunda de 2026-05-27 (workflow 6 dimensoes) revelou um "limbo"
de hipoteses propostas e nunca concluidas. O subconjunto empiricamente
tratavel — naturezas raras (#5 range, #8 arredondamento), Pacote 7 (H-LR-*
lossy), e o ponto cego de baixa-cardinalidade — foi investigado no lab
[`2026-05-27-naturezas-reais-uci`](../../experiments/lab/dirty/2026-05-27-naturezas-reais-uci/).

Tres achados motivam este ADR:

1. **A estrutura-alvo EXISTE** em dados financeiros/cientificos (UCI: wine,
   beijing, online-retail), ao contrario de Adult/TPC-H onde as hipoteses
   foram refutadas. A refutacao anterior foi por dataset inadequado.
2. **TCF tem ponto cego de baixa-cardinalidade**: colunas numericas curtas
   e repetitivas inflam ate' 2.3x (ex: beijing `hour`, 24 unicos → 228.8%).
   Toggles (PipelineConfig) nao corrigem — e' o nucleo OBAT+HCC.
3. **Todas as solucoes exigem mudanca de formato** → por [ADR-0017](0017-format-spec-v1-frozen.md)
   (freeze #TCF.6 em v1.0), sao material de **v2.0**, nao v1.x.

Este ADR registra o roadmap v2.0 com a evidencia empirica, pra que o limbo
deixe de ser limbo (caracterizado + decidido em vez de esquecido).

## Decision Drivers

- v1.0 congela formato #TCF.6 (ADR-0017). Otimizacoes que mudam o body ou
  o header sao breaking → v2.0.
- Evidencia empirica de valor (ja medida no lab) deve guiar prioridade.
- Cada candidato tem trade-off proprio (lossless vs lossy, complexidade
  do decoder).

## Considered Options (candidatos v2.0, ordenados por evidencia)

### V2-A — Fallback identity por coluna (lossless)

"Se o TCF de uma coluna fica maior que o raw, guarda raw."

- **Evidencia** (prototipo `proto_fallback.py`): ganho 0.8% (wine), 10.2%
  (beijing), 2.0% (retail-50k). RT preservado.
- **Por que v2.0**: body raw nao decodifica com decoder atual (verificado:
  `_decode_column` lanca KeyError). Exige marcador de modo por coluna
  (prototipo usou `!name` na meta line).
- **Propriedade forte**: garante "nunca pior que raw+delimitadores".
- **Custo**: marcador novo no header multi-col; decoder ramifica por modo.

### V2-C-Patricia — Patricia trie / GST como indice OBAT (H-TH-02)

Substitui hash trigrama (ADR-0009) por Patricia/Generalized Suffix Tree.

- **Evidencia**: estudo de viabilidade completo em
  [docs/theory/patricia-trie-exploration.md](../theory/patricia-trie-exploration.md)
  (workflow 4 dimensoes, 2026-05-27). H-TH-02 (registrada 2026-05-13, nunca
  testada) tem design concreto + protocolo de validacao.
- **Por que v2.0**: byte-canonical depende de tie-break por ordem de insercao
  no hash dict — Patricia drop-in precisa preservar exatamente. Risco real de
  divergencia bytes (mesmo problema que afundou H-PERF-04).
- **Ganho esperado**: 5-50x speedup em colunas com prefixos populares variados
  (URLs, factory IDs, datas multi-decada). Em colunas categoricas dispersas,
  overhead de tree pode anular ganho.
- **Ortogonalidade com H-PERF-06 (Cython)**: independentes — Cython acelera
  cada lcp/lcs call; Patricia reduz numero de calls. Ganhos multiplicam.
- **Effort estimado**: 10-30h (proto fork + validacao multi-camada).
- **Acceptance criteria**: D1-D9 1615B EXATO + RT 100% multi-camada +
  speedup >= 1.5x em coluna com prefixo popular.

### V2-B — Encoder dicionario/categorico (lossless)

Para baixa-cardinalidade: mapear valor→indice pequeno + tabela de valores.

- **Evidencia**: nao prototipado (owner optou por fallback primeiro), mas
  caracterizacao sugere teto alto: beijing `hour` (24 unicos em 43824
  linhas, entropia ~5 bits/linha) poderia ir de 228.8% pra <15%.
- **Por que v2.0**: novo sub-formato (tabela + indices); decoder novo.
- **Relacao**: subsume a hipotese "enumerated" (Pacote 5 T03) que foi
  **refutada prematuramente** ("M10 ja cobre via dedup+seq-RLE" — falso
  pra valores curtos, conforme medido).
- **Custo**: maior que fallback; mas resolve a RAIZ do ponto cego.

### V2-C — Naturezas lossy / precisao reduzida (H-LR-*)

Para decimais de alta precisao quase-incompressiveis losslessly.

- **Evidencia**: wine chemical features (volatile_acidity 102%,
  residual_sugar 124.5%) sao decimais 2-3 casas quase-unicos. Lossless
  nao ajuda; lossy (ex: 0.27583 → 0.276) com erro controlado abriria espaco.
  Lossless parcial: strip `.0` em free/total_sulfur_dioxide (sempre `.0`),
  CustomerID (sempre `.0`).
- **Por que v2.0**: lossy quebra round-trip exato — precisa de contrato
  explicito de tolerancia (erro maximo, erro distribuido). Marcador no
  formato indicando precisao.
- **Risco**: lossy e' opt-in por natureza; round-trip vira "recuperavel
  dentro de tolerancia", nao exato. Filosofia diferente — precisa decisao
  conceitual do owner.

### V2-D — Strip de sufixo redundante (lossless, subconjunto de C)

Caso particular barato: colunas onde todos os valores terminam igual
(`.0`, zero-padding). Strip + restaura no decode.

- **Evidencia**: free/total_sulfur_dioxide (99% `.0`), CustomerID (100% `.0`).
- **Por que v2.0**: marcador de sufixo comum no header da coluna.
- **Custo**: baixo; lossless; subconjunto de C que nao precisa de tolerancia.

## Decision Outcome

**Registrar V2-A/B/C/D como roadmap v2.0**, sem implementar em v1.x.
v1.0 mantem #TCF.6 congelado (ADR-0017) e e' HONESTO sobre seus limites
(baixa-cardinalidade, lossy) — documentado no README/format spec.

Prioridade sugerida quando v2.0 abrir:
1. **V2-A (fallback)** — rede de seguranca universal, ganho garantido
   nao-negativo, prototipo pronto. Menor risco.
2. **V2-B (dicionario)** — maior teto, resolve a raiz; subsume "enumerated".
3. **V2-D (strip sufixo)** — barato, lossless, ganho direto em `.0`.
4. **V2-C (lossy)** — maior ganho potencial mas precisa decisao conceitual
   sobre round-trip recuperavel-dentro-de-tolerancia.

### Gatilho de abertura do v2.0

v2.0 abre quando o owner decidir priorizar. Pre-requisitos tecnicos:
- Bump #TCF.6 → #TCF.7 + tcf 2.0.0
- Migration doc v1→v2 (decoder v2 le' #TCF.6 legacy)
- Cada candidato exige test suite proprio + RT (ou RT-dentro-de-tolerancia
  pra V2-C)

## Consequences

### Positive

- Limbo fechado: itens caracterizados + decididos + agendados (nao esquecidos)
- v1.0 fica limpa: freeze honesto, v2.0 com roadmap fundamentado em dados
- Evidencia empirica preservada (lab + prototipo reproduzivel)

### Negative

- Ganhos reais (ate' 10% fallback, mais em dicionario) ficam adiados pra v2.0
- Acumula pressao pra v2.0 (varios candidatos esperando)

### Neutral

- B-tier resolvido em paralelo (ver lab): H-DA-01 seq-RLE CONFIRMADO forte
  em sensores (beijing -29.5% se removido) — sai de "A-revalidar" pra A.

## Links

- [Lab 2026-05-27-naturezas-reais-uci](../../experiments/lab/dirty/2026-05-27-naturezas-reais-uci/result.md) — evidencia
- [ADR-0017 — Format freeze v1.0](0017-format-spec-v1-frozen.md)
- [futuras-otimizacoes-formato.md](../../experiments/lab/dirty/notas/futuras-otimizacoes-formato.md) — O-FMT-* registry
- [roadmap-hipoteses.md](../../experiments/lab/dirty/notas/roadmap-hipoteses.md)

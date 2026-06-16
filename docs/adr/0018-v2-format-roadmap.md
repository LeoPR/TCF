# 0018 — Roadmap de formato v2.0 (fallback identity, dicionario, lossy)

**Status**: accepted (parcialmente realizado — V2-A/V2-B/split welded; V2-D refutado; V2-C/V2-J/V2-K/V2-L defer v2.0). Referencia de fechamento do ciclo 0.7.
**Date**: 2026-05-27
**Deciders**: project owner
**Tags**: v2.0, format, roadmap, low-cardinality, lossy, dictionary, fallback

> **Update 2026-06-13**: o owner decidiu abrir a v2.0. **V2-A (fallback
> identity) welded** via [ADR-0022](0022-v2a-fallback-identity-weld.md) —
> opt-in (`fallback=True`), `#TCF.7 M`, marcador `!<size>=<name>`,
> caracterizado em 9 fontes (7.85% weighted). V2-B/C/D seguem como roadmap
> abaixo (nao implementados). A prioridade sugerida na secao "Decision
> Outcome" continua valendo pros restantes.
>
> **Update 2026-06-14**: **V2-B (dicionario/categorico) welded** via
> [ADR-0025](0025-v2b-dictionary-categorical-weld.md) — 3o candidato do
> fallback (`min(tcf, raw, v2b)`), `#TCF.7 M`, marcador `@<size>=<name>`,
> caracterizado em 8 datasets reais (13.9% weighted, RT 42/42). Restam V2-C
> (lossy) e V2-D (strip sufixo) no roadmap.
>
> **Update 2026-06-15 — estado de fechamento do ciclo 0.7**: este ADR vira
> `accepted` e serve de referencia unica do roadmap de formato. Estado:
> - **V2-A** (ADR-0022) — **DONE** (fallback identity, `!`, 7.85% weighted).
> - **V2-B** (ADR-0025) — **DONE** (dicionario, `@`, 13.9% weighted).
> - **Split estrutural** (ADR-0026) — **DONE** (4o candidato `min(tcf,raw,dict,split)`,
>   `%`, 19.39% weighted; generaliza datetime/decimal/CPF/CNPJ → campos → V2-B).
>   Subsume a antiga V2-D-como-datetime-nature.
> - **V2-D** (strip de afixo) — **REFUTADO** (subsumido pelo OBAT, 0.11% weighted;
>   o sinal real era split estrutural). Ver `2026-06-14-v2d-strip-afixo-caracterizacao/`.
> - **V2-C** (lossy-round) — **caracterizado, NAO welded**. Decisao do owner
>   (2026-06-15): **0.7 permanece lossless-puro**; round-puro (nicho ~1.5%, so' wine)
>   nao justifica quebrar a pureza. Lossy amplo (Pacote 10) vira roadmap v2.0,
>   priorizando a vertente **cross-coluna** (`valor=soma(parcelas)`), nao round simples,
>   sob GATE real-world N>=5. Ver `loss-taxonomia.md` + roadmap Pacote 10 (H-LOSS-*).
> - **V2-J / V2-K / V2-L** (streaming / disk zero-copy / binarizacao em camadas) —
>   **defer v2.0**: exigem decisao de arquitetura (I/O) + escopo, fora do foco de
>   bytes textuais do 0.7.

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

### V2-L — Binarizacao em camadas (Parquet-like, INTERNO ao TCF)

**Requisito registrado pelo owner 2026-05-27** (clarificacao escopo).

TCF tem um formato canonical TEXTUAL (#TCF.6) — pilar de explicabilidade
(CLAUDE.md filosofia). V2-L propoe **camada interna de binarizacao
opcional**, integrada ao TCF (NAO ferramenta externa), inspirada em como
Parquet, csv e json fazem decisoes internas de representacao:

- **Parquet**: row groups + column chunks + page headers + dictionary
  pages, tudo binario, com metadata estruturada em camadas
- **csv/json**: tem suas proprias decisoes (delimitadores, quoting,
  escape, encoding) — sao formatos com escolhas internas, nao "puramente
  textual"
- **TCF v2-L**: HCC body (e talvez outros niveis) podem ter representacao
  binaria opt-in como **camada de transport**, mantendo a opcao textual
  como canonical observavel

Concretamente:
- **HCC body binarizado**: marcadores RLE/seq-RLE/refs em bytes packed
  em vez de ASCII. Reduz IO mas preserva semantica (RLE conta de N items
  continua deduzivel sem expandir, igual ao textual).
- **Header textual mantido** (pra inspecao + roteamento): `#TCF.6 M` ou
  `#TCF.7 MB` (M=multi, B=binary body) — decoder ramifica.
- **Decoder unificado**: le qualquer um dos modos pelo shebang.
- **Encoder opcional**: usuario escolhe `encode(table, body_format="text"|"binary")`
  default="text" pra preservar filosofia.

Por que **INTERNO** ao TCF (e nao external tool):
- E' decisao de **representacao do mesmo dado**, igual Parquet decide
  page encoding
- Preserva semantica (RLE continua mostrando grupos sem expandir)
- E' otimizacao de IO/disk/web (V2-K territory), nao mudanca de algoritmo
- Coerencia: TCF tem multiplos modos de representacao, todos sob mesma
  filosofia (explicabilidade + grupos visiveis)

Por que NAO competir com gzip/brotli/zstd:
- V2-L NAO e' compressor binario generico — e' representacao binaria
  da MESMA estrutura logica do TCF
- Aplicar brotli sobre TCF-binary continua sendo opcao (transport layer
  composto)
- O posicionamento "areas explicaveis vs areas cinzas" se mantem: TCF
  explica O QUE comprimiu (refs, RLE, naturezas), mesmo em binary

**Conecta com**:
- V2-J streaming (V2-L binary e' transport eficiente pra stream)
- V2-K disk zero-copy (V2-L binary mmap-friendly)
- HCC core (subsistema 02-hcc-core.md) — maior beneficio da binarizacao
- ADR-0017 freeze v1.0 — V2-L e' v2.0 (format change opt-in)

**Bloqueador atual**: precisa fechar V2-J/V2-K primeiro (streaming + disk
definem REQUISITOS de binary representation). Sem isso, binarizar HCC
isolado nao tem caso de uso forte.

### V2-J — Pipeline streaming online (low-latency seriado)

**Requisito registrado pelo owner 2026-05-27**.

Mecanismo de envio seriado dos processos onde cada etapa do pipeline (pre-pass
→ OBAT → HCC → seq-RLE → multi-col header/body) libera saida o mais rapido
possivel pra etapa seguinte, otimizando **latencia** (time-to-first-byte e
time-between-bytes) ao inves de throughput puro.

Caso de uso: envio online (HTTP streaming, websocket, gRPC stream), onde o
consumidor comeca a processar antes do encode completo terminar.

Diferencas vs paralelismo atual (T-CODE-ENCODER-MANAGER Fase 1b, ProcessPool):
- Atual: paraleliza COLUNAS (throughput); cada coluna espera todas etapas
- V2-J: paraleliza ETAPAS pipeline da MESMA coluna; cada etapa emite chunks
  conforme processa

Implementacao plausivel:
- Generators ou async iterators em vez de listas completas
- HCC seq-RLE precisa janela deslizante (atualmente full body em memoria)
- Multi-col header com sizes "ainda nao conhecidos" (length-prefix por chunk?
  trailer com sizes finais? ou header re-escrito ao fim?)
- Output sink protocol: yields chunks bytes, consumidor pode flush conforme chegam

Bloqueador formato: header `# size=name,...` atual exige saber sizes ANTES
do body. Streaming exigiria sub-formato (length-prefixed chunks, ou trailer,
ou size deferred) → v2.0 format change.

Conecta com: O-FMT-08 (Streaming encoder, design v0.4 mencionado em workbench),
T-CODE-OUTPUT-SINKS (P2), T-CODE-ENCODER-MANAGER Fases 2+ (sinks compostos).

### V2-K — Disk write + fast recovery, minimo de buffer-over-buffer

**Requisito registrado pelo owner 2026-05-27**.

Mesmo pipeline de V2-J otimizado pra escrita em disco + recuperacao rapida,
**sem duplicacao de camadas de memoria** (anti-pattern buffer-over-buffer /
cache-over-cache).

Caso de uso: persistencia local de tabelas grandes, leitura preguicosa de
colunas selecionadas (column-pruning sem ler tudo).

Tecnicas plausiveis:
- Layout multi-col com **offsets fixos no header** (CSV-like seek; ja' temos
  `size=name` mas atualmente exige ler header inteiro pra mapear)
- mmap pra leitura zero-copy (cada coluna e' um slice mmap, decoder opera
  direto no buffer mapeado)
- Write: io.RawIOBase/BufferedWriter unico (sem `text.encode()` que copia tudo)
- Compatibilidade gzip/brotli/zstd como transport: stream-compress no fly
  (compressed offset != logical offset; trailer ou block-aligned)

Bloqueador: `_encode_multi` atualmente concatena bytes em memoria; `decode`
le tudo. Refactor pra streaming I/O com offsets pra column-pruning.

Conecta com: O-FMT-08 (streaming), O-FMT-14 (header desacoplavel — owner
admitia "se contenta com atual"), T-CODE-OUTPUT-SINKS (FileSink/MMapSink).

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

> **REFUTADA-REAL-WORLD 2026-06-14** ([lab](../../experiments/lab/dirty/2026-06-14-v2d-strip-afixo-caracterizacao/result.md)):
> **subsumida pelo OBAT** (bidirecional ja' compartilha o afixo comum como 1
> fragmento). Ganho weighted = **0.11%** em 8 datasets reais; strip de prefixo
> ainda REGRIDE (desancora a tokenizacao OBAT: datas -155 a -286B). Mesmo gated
> (zero regressao) ~0.15%. NAO welder. Sinal real = colunas DATETIME (InvoiceDate
> 15%, data_cadastro 3.5%) -> **datetime-nature** (encoder proprio, linha ADR-0015),
> nao strip generico.

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

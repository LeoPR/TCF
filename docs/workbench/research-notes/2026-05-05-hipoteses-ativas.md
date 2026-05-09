# Hipoteses ativas TCF v0.4 — para testar

Indice de tudo que falta testar/validar antes de implementar
seriamente. Organizadas em 3 grupos.

## Grupo 1 — Propostas tecnicas com lab dirty pendente

Propostas selecionadas no roadmap original (Sprint 1+2) sem lab dirty:

| HP | Proposta | Hipotese | Lab proposto |
|----|----------|----------|--------------|
| **HP-A1** | A — Stratified STATS | STATS condicionados sobem Linha A em filter+agg | `flow-stratified-adult` |
| **HP-B1** | B — Type-preserving | int/float/bool/None preservados em roundtrip | `flow-types-roundtrip` |
| **HP-F1** | F — Auto-detect sortedness | algoritmo escolhe sort_by certo em datasets variados | `flow-sortedness-auto` |

## Grupo 2 — Hipoteses operacionais (interacao com transporte)

**Levantadas 2026-05-05 pelo user**: TCF nao opera no vacuo —
canal HTTP/3 + brotli/gzip eh o cenario real. Algumas combinacoes
podem mudar a decisao.

### HP-T1 — TCF L0 + sort vs CSV no canal gzip

**Hipotese**: o ato de organizar valores colunarmente + ordena-los
oferece ao gzip um padrao muito melhor para comprimir, mesmo sem
TCF aplicar compressao propria.

**Por que pode valer**:
- CSV row-oriented: `A1,B1,C1\nA2,B2,C2\n...` — gzip ve padroes mistos
- TCF colunar: `A:\nA1\nA2\n...\nB:\nB1\n...` — valores similares juntos
- Com sort: cada coluna ordenada → repeticoes contiguas → gzip vence

**O que medir**:
- naive CSV + gzip
- TCF L0 (colunar puro) + gzip
- TCF L0 + sort + gzip
- TCF compact (RLE+sort) + gzip
- TCF smart (tudo) + gzip

**Hipotese forte**: pode haver sweet spot onde TCF faz **so o
essencial** (colunar + sort) e gzip aproveita melhor que TCF
compactando muito (saturado).

**Implicacao se verdadeira**: `mode="compact"` minimal pode ser
melhor que `mode="smart"` quando ha gzip no canal.

### HP-T2 — Chunks pequenos prejudicam canal gzip/brotli

**Hipotese**: chunks pequenos transmitidos em paralelo perdem
vantagem de compressao porque gzip aplicado a cada um isoladamente
nao amortiza overhead.

**Por que pode valer**:
- gzip overhead fixo ~10B por stream
- Janela deslizante 32KB-64KB acha padroes
- Chunk de 200B: gzip adiciona ~10B = 5% overhead, sem encontrar muitos padroes
- Chunk de 32KB+: gzip amortiza overhead bem

**Sweet spot estimado**: batches de **~32KB-64KB** por canal gzip,
contendo varios chunks autocontidos.

**O que medir**:
- TCF chunks de varios tamanhos: 1KB, 4KB, 16KB, 64KB, 256KB
- Cada batch passa por gzip
- Bytes finais + tempo de processamento simulado

**Implicacao se verdadeira**:
- `EncodeManager` deve ter conceito de "batch alvo" antes de aplicar gzip
- Trade-off explicito: chunks pequenos = streaming/paralelismo;
  batch grande = compressao melhor

### HP-T3 — Caminho feliz vs minimo + transporte (qual vence end-to-end)

**Hipotese**: caminho feliz (TCF smart com auto-tudo) saturou a
compressao estrutural; gzip nao tem mais o que fazer. Em contraste,
TCF compact (RLE+sort apenas) deixa redundancia que gzip economiza.

**Cenarios a comparar**:
- TCF smart + gzip vs TCF compact + gzip
- Em datasets variados (pessoas, categoricos, mix, banco)

**Resultado possivel**: smart + gzip ≈ compact + gzip em bytes
finais, mas smart custou mais CPU para encode. Conclusao: 
**nao vale comprimir TCF demais** se gzip esta no transporte.

**Implicacao**:
- Default `mode="smart"` quando NAO ha transporte comprimido
- Default `mode="compact"` quando ha transporte comprimido
- Auto-detect via header HTTP `Accept-Encoding`?

## Grupo 3 — Hipoteses arquiteturais (deriva das anteriores)

| HP | Hipotese | Onde |
|----|----------|------|
| HP-arch-1 | Schema explicito reduz overhead em -5 a -10% adicional | proximo lab com schema |
| HP-arch-2 | Multi-canal (cols separadas) ajuda projecao do client | v0.5+ |
| HP-arch-3 | Telemetria dinamica de batch ajusta sweet spot por dataset | v0.5+ |
| HP-arch-4 | LLM ganha legibilidade com `verbose_llm=True`; bytes ↑ | escopo separado ⚫ |

## Como o ambiente deveria estar para testar isso

### Estrutura sugerida

```
experiments/lab/
  framework/                       # ja existe, reutilizar
    pipeline.py                    # encode → compress → decompress → decode
    encoders.py                    # adicionar TCFEncoder com mode= novo
    compressors.py                 # gzip, brotli, zstd, none
    metrics.py                     # bytes, tempo
  
  dirty/                           # bancada de exploracao
    (vazia para os nossos labs; tem outros do user)
  
  clean/
    EXP-003-tcf-vs-transport/     # NOVO — testa HP-T1, HP-T2, HP-T3
      README.md                    # hipoteses formais
      run.py                       # usa framework/
      datasets/                    # ou referencia canonical:tpch-sf001
      results/                     # CSVs/JSONs reproduziveis
    EXP-004-stratified-stats/     # NOVO — testa HP-A1
    EXP-005-types-roundtrip/      # NOVO — testa HP-B1
    EXP-006-auto-sortedness/      # NOVO — testa HP-F1
  
  archive/
    2026-05-design-v04-fase1/      # ja arquivamos
```

### Ordem sugerida de execucao

1. **EXP-003 (transporte)** primeiro: HP-T1, T2, T3 sao **decisivas**.
   Se transporte comprimir tudo, nao vale implementar Propostas
   sofisticadas (E, H, I) — bastaria L0+sort.
2. **EXP-004/005/006 (Propostas A, B, F)**: validar antes de
   implementar.
3. Apenas APOS evidencia, mexer no core (M-chunks-v04 Bloco 1+2).

### Criterios de "ambiente organizado"

- [ ] Framework `pipeline.py` aceita `mode=` da nova nomenclatura
- [ ] Compressores genericos (gzip, brotli, zstd) integrados
- [ ] Datasets reproduziveis (load_dataset com seed)
- [ ] Metrics estaveis (mediana de N iteracoes)
- [ ] Results em format reproduzivel (CSV/JSON em results/)
- [ ] README de cada EXP-* descreve hipotese, metodo, criterio de sucesso

## Decisoes pendentes que afetam todas as hipoteses

| Q | Pergunta | Aguarda |
|---|----------|---------|
| Q1 | Aceitar nomenclatura `raw/compact/smart/extreme`? | user |
| Q2 | Aceitar siglas tecnicas (RLE/DICT/XDICT/etc)? | user |
| Q3 | Sigla TCF: manter `Textual` ou redefinir `Tabular`? | user |
| Q4 | Implementar HP-T1/T2/T3 ANTES das Propostas? | depende Q5 |
| Q5 | Aceitar que transporte (gzip/brotli) muda decisao? | user |

Q4+Q5 sao especialmente importantes: se aceito, ordem de
implementacao se inverte — primeiro testa interacao com transporte,
depois decide quais Propostas valem.

## Resumo executivo

Total de hipoteses ativas: **10**
- 3 propostas selecionadas sem lab (A, B, F)
- 3 hipoteses operacionais (HP-T1/2/3)
- 4 hipoteses arquiteturais (HP-arch-1/2/3/4)

Bloqueador real para implementacao do core: HP-T1 (TCF L0+sort
vs caminho feliz no canal gzip). **Se transporte comprimir tudo,
todo o esforco em compressao estrutural avancada eh desperdicio.**

Recomendacao: rodar **EXP-003 primeiro**. Resultado define se
investimos em E/H/I ou se ficamos com mode=compact + transporte.

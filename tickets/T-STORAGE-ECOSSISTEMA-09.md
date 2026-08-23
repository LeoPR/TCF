---
title: T-STORAGE-ECOSSISTEMA-09 — rodar em armazenamento real (HDFS/Parquet/object store): composição de compressão e leitura com índice
status: open
priority: P1
created: 2026-08-23
updated: 2026-08-23
target: ".9 — segundo eixo do ciclo (o primeiro é T-PERF-BORDAS-E-MODOS-09)"
blocked-by: []
related:
  - tickets/T-PERF-BORDAS-E-MODOS-09.md
  - tickets/T-HTTP-QUERY-E-VIEW.md
  - docs/reference/lazy-view.md
  - docs/adr/0002-vertice-triplice-restricao.md
  - tickets/T-STUDY-USE-PROFILES.md
---

# T-STORAGE-ECOSSISTEMA-09

**[dispositivo → registro. Nada em `src/tcf` sem aprovação.]**

Direção do owner (2026-08-23): *"o que eu queria fechar no `.9` não é apenas performance, mas
as questões de conseguir colocar pra rodar num sistema de armazenamento do tipo HDFS, parquet
e afins, usando as camadas de compressão dele, compressão extra (brotli) além da leitura com
índice de suporte."*

**Isto reenquadra o `.9`**: ele tem **dois eixos**, e este não é performance — é
**integração com o ecossistema**. Um formato que não roda onde o dado vive é um formato de
laboratório.

## O que já está medido (e não pode ser ignorado)

O lab de compressores HTTP × Parquet
(`2026-07-13-0156-compressores-http-parquet`) já achou o padrão, e ele **corta nos dois
sentidos** — está no README:

> Na família de compressores do Parquet (snappy, lz4, zstd): numa **coluna densa de texto
> livre**, o compressor binário sozinho vence e **pôr TCF embaixo costuma piorar** (até
> **−41%** — a reescrita de referências do TCF atrapalha o modelo de entropia dele). Numa
> **tabela estruturada multi-coluna**, o TCF vence sozinho (−72% vs CSV) **e** compõe
> (`tcf+brotli` −30% vs `brotli(raw)`). **Quem decide é a estrutura, não o container.**

Então a pergunta deste ticket **não** é "TCF é melhor que Parquet?" — é **onde na pilha ele
entra sem atrapalhar**, e o que a estrutura do dado diz sobre isso.

## As quatro frentes

### 1. Composição de compressão — não empilhar por empilhar

Parquet/ORC já comprimem por coluna (snappy/zstd/gzip/lz4/brotli). Pôr TCF por baixo é
**dupla compressão**, e o achado acima diz que às vezes piora. A entregar:

- uma **régua de decisão** por característica de coluna (cardinalidade, texto livre vs
  estruturado, largura) dizendo: TCF+codec do container · só o codec · só TCF
- medir em ambos os sentidos: TCF **dentro** de uma coluna Parquet, e TCF **como formato
  do arquivo** com o codec por cima
- o eixo cardinalidade já é conhecido como o quente
  ([`T-PERF-BORDAS-E-MODOS-09`](T-PERF-BORDAS-E-MODOS-09.md)) — provavelmente é ele aqui também

### 2. Leitura com índice — o `view()` num sistema de arquivos distribuído

O `view()` já materializa só o que a pergunta toca (medido: 7,9% do blob). Num object store
ou HDFS isso vira **range request**: ler só os bytes daquela coluna. Falta:

- **mapa de offsets** por coluna — o meta já traz os `size`, então a informação **existe**;
  falta expô-la como índice consultável sem ler o corpo
- casar com o que o container oferece (Parquet tem row-group + column chunk + page index)
- `T-CODE-OUTPUT-SINKS` e `T-CODE-PLAN-CONTRACT` estão *parked v2.0* e podem ser os
  portadores naturais — reavaliar

### 3. Blocos e paralelismo — a granularidade do sistema

HDFS/object store trabalham em blocos. Um wire TCF é hoje **um artefato inteiro**. A questão:
dá para produzir blocos independentes (split-able) sem perder o que o TCF ganha justamente por
ver a coluna toda? **Cuidado medido**: concatenar wires independentes **corrompe em silêncio**
(299/600 valores errados) — a operação "cortar wire pronto" é segura, "concatenar
independentes" não é. Qualquer desenho de bloco esbarra nisso.

### 4. Onde o TCF *não* deve entrar

Entregar isto explicitamente é tão valioso quanto o resto: coluna densa de texto livre com
codec binário na frente é caso **medido** de piora. O ticket tem de dizer *"aqui não"* com o
mesmo rigor com que diz *"aqui sim"*.

## Perguntas abertas (nenhuma respondida)

- Vale um **writer/reader de Parquet** que use TCF como codec de coluna, ou o TCF vive melhor
  **ao lado** (arquivo `.tcf` no mesmo store, com índice próprio)?
- `pyarrow` é dependência aceitável **para o lab**? (o pacote publicado tem
  `dependencies = []` e isso **não muda** — seria extra opcional, como `[datasets]`)
- O `sort_by` (layout L5) interage com row-group do Parquet? Ordenar para agrupar é a mesma
  ideia dos dois lados.

## Critério de aceite

- [ ] Régua de decisão por característica de coluna, **medida** — incluindo os casos de piora
- [ ] PoC de leitura por range/offset usando o meta como índice
- [ ] Resposta explícita sobre blocos: viável ou não, com o risco do concat documentado
- [ ] Nada de `src/tcf` sem aprovação; se exigir mudança de formato, vira ADR próprio
- [ ] `dependencies = []` preservado no pacote publicado

## Não fazer agora

Escolher container antes de medir. E não repetir o erro que o próprio projeto registrou: o
ganho em sintético **não** transfere para real (anti-incidente 2026-05-21) — dado real,
Shaper (**I3**), gates verdes.

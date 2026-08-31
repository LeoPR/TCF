---
title: Compressão por representação de índice (alfabeto, packing) — estudo deferido
type: study
status: open
priority: low
created: 2026-05-08
defer-reason: distinção conceitual validada, ganho em bytes modesto em datasets pequenos
---

## Contexto

A compressão tem dois eixos ortogonais que descobrimos ao longo das
mesas de trabalho de maio/2026:

1. **Compressão por repetição** — explora padrões NA forma do dado
   (RLE, dict, delta, prefix elision, line-RLE)
2. **Compressão por representação** — empacota mais significado por byte
   (densidade do alfabeto, bit-packing)

A dirty lab cobriu o eixo 1 nas mesas de 2026-05-07 e 2026-05-08. O eixo 2
foi tocado em `experiments/lab/dirty/2026-05-08-indices-alfabeto/` mas o
ganho em bytes nos datasets pequenos foi trivial (~1B). O estudo é
**deferido** até que datasets ricos justifiquem revisitar.

## O que foi achado

- Decimal já é denso suficiente para cardinalidade ≤ 9
- Letras (a-z) eliminam o discriminador `:` em colunas numéricas
  (ganho de 1B/ref independente de cardinalidade)
- Hex/base32/base64 dão índice de 1 char para cardinalidades 17-94
- Binário (1 byte/idx) e bit-packing (múltiplos idx/byte) violam a
  meta de legibilidade ASCII do TCF
- A flag `A` (alfabeto adaptativo) já está reservada na hierarquia
  Lxxx (`SRDMA` é o default proposto para v0.5)

## Distinção crítica vs compressão por repetição

> Não estamos aplicando uma compressão por repetição. Estamos comprimindo
> por **representar mais coisa em menos espaço**. As técnicas de escape
> para colisão e a regra para saber quando precisamos ou não ter o índice
> independem do formato compacto dele.

Logo: a escolha do **formato do índice** é decoupled da decisão de **usar
ou não índice**. A regra unificada decide o segundo; o alfabeto decide
o primeiro.

## Perguntas em aberto (a investigar quando revisitar)

1. **Ganho real com cardinalidade média/alta**: em datasets com cardinalidade
   50-1000 e muitas refs por coluna, qual o ganho líquido de letras vs
   decimal?
2. **Interação com gzip downstream**: TCF + gzip absorve o ganho do
   alfabeto denso, virando zero-soma? Em que contexto?
3. **Dialeto TCF-binary**: vale definir um dialeto opcional não-legível
   (1 byte/idx, bit-packing) para casos não-LLM (storage, network bulk)?
4. **LLM e base64**: LLMs parseiam base64 como índices estruturados, ou
   alucinam vendo aquilo como ruído? Tem que medir.
5. **Descoberta de alfabeto pelo decoder**: a inferência por varredura de
   chars usados é robusta para qualquer dataset? Casos patológicos?

## Quando revisitar

- Quando dataset real (TPC-H, logs estruturados, etc.) mostrar refs > 30%
  do total de bytes após aplicar L3+S
- Após existir o protótipo do encoder (mesa de implementação)
- Depois de fechar o estudo de extensões (δ, P, L')

## Relacionado

- `experiments/lab/dirty/2026-05-08-indices-alfabeto/` — exploração completa
- `experiments/lab/dirty/2026-05-08-sintese-formato/03-lxxx-proposta.md` —
  flag `A` na hierarquia Lxxx
- `experiments/lab/dirty/2026-05-09-delta-datas/` — próxima mesa, foca em
  compressão por repetição (delta)

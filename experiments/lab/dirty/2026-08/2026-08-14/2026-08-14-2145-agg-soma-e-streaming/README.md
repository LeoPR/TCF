# `agg="soma"` e streaming — três formas de prometer a mesma coisa

> **Owner (2026-08-14)**: *"o agg soma, creio que matematicamente dá pra fazer uma inferência
> de comportamento para uma possível soma, no caso, isso é útil porque **dependendo da forma
> que eu peça, tem que ver se ele fica stream compatível**."*

**Uma pergunta**: preservar a soma é compatível com streaming?

**Resposta curta**: depende da forma — e há três. Ver [`result.md`](result.md).

## As duas noções de streaming, separadas de propósito

| noção | pergunta | quem a ataca |
|---|---|---|
| **prefixo do encoder** | quantos valores da fonte preciso ler para emitir o primeiro do wire? | é o que o `agg` afeta |
| **prefixo do decoder** | quantos bytes do wire preciso bufferizar para emitir o primeiro valor? | é a métrica do lab [`2026-07-27-2211`](../../../2026-07/2026-07-27/2026-07-27-2211-dominio-primeiro-streaming/) |

Misturá-las esconde o efeito: neste lab o prefixo do **decoder** é 19 B nas três formas
(idêntico), e toda a diferença está no **encoder** — 2000 leituras contra 1.

## Estado — era / foi / é / será

- **Era**: o `Tolerancia(agg="soma")` do lab [`…-2110`](../2026-08-14-2110-parametro-de-tolerancia-float/)
  usava maior resto, sem perguntar se streamava.
- **Foi**: o owner apontou que a forma do pedido decide a compatibilidade.
- **É**: 3 formas × 3 casos, 0 falhas. A **difusão de erro entrega a soma exata sendo
  streamável**, por 62 B (2,0%) e o dobro do erro por linha.
- **Será**: `agg` precisa de um segundo eixo (`agg_forma`), porque "preservar a soma" não
  determina como.

## Contrato deste lab

O valor muda de propósito — RT contra a origem não se aplica. Valem: (1) o contrato declarado
(a soma fecha na escala de `d`?), (2) o formato continua lossless sobre os ajustados, (3) o
instrumento de **passe único** (um wrapper que conta leituras da fonte).

⚠️ Os `.tcf` que não são `.baseline` contêm valores **ajustados de propósito**.

## Como rodar

```
python run.py     # sai 0 só se o formato preservar os ajustados em todas as formas
```

Roda **sem `Z:`** (o sintético do rateio basta para ver a mecânica).

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<caso>.entrada.json` · `.fonte.json` | os originais e a procedência |
| `outputs/<caso>.<forma>.tcf` · `.roundtrip.json` · `.meta.json` | o wire de cada forma |
| `intermediates/formas.json` | as medições, com `streaming` e `CONSTANTE_na_comparacao` |

## Vínculo

`H-LOSS-00` (contrato) · `H-LOSS-01` (resíduo redistribuído) ·
lab do parâmetro: [`…-2110`](../2026-08-14-2110-parametro-de-tolerancia-float/) ·
métrica de prefixo: [`2026-07-27-2211`](../../../2026-07/2026-07-27/2026-07-27-2211-dominio-primeiro-streaming/) ·
nota [`…-2010-perda`](../../../notas/2026-08/2026-08-14-2010-perda-propagacao-de-erro.md)

# Macro M2 — Redundancia entre linhas

## Manifesto

Macro **complementar** ao M1 (marcacao de ambiguidade). M1 atacou
redundancia LOCAL (dentro da linha). M2 ataca **redundancia entre
linhas** — padroes que se repetem em multiplas linhas e podem
ser substituidos por alias compartilhado.

Identificado na revisao critica de M1.E como "Camada 2 de
redundancia visivel mas nao tocada pelo macro M1":

> D1 linhas 6-8 tem sufixo `,3,11,5,6` repetido 3x. Atacavel por
> aliases de tupla ou templates de refs.

M2 testa se essa observacao se traduz em ganho de bytes
proporcional ao numero de repeticoes.

## Principios

1. **Reaproveita exp 16** (`online.py`) como algoritmo raiz, sem
   modificacao.
2. **Reaproveita sintaxe M1.E** (range + escape escopo) como base.
3. **Adiciona camada de aliases** sobre o output do M1.E.
4. **Cada micro M2 e' autocontido** — mesma metodologia M1.
5. **Datasets canonicos D1-D4** (mesmos do M1) — para comparacao
   direta com M1.E (baseline 676 bytes).

## Estrutura

```
M2/
  online.py             raiz (copia de M1, intocado)
  syntax_base.py        interface (copia de M1)
  data/
    D1-D4.csv           mesmos canonicos de M1
  M2-A-alias-tupla/
    syntax.py           micro: aliases de tupla de refs
    README.md
  notas/                analise teorica + insights
  resultados/           outputs do run_lote
  run_lote.py           script unificado
```

## Micros planejados

| Codigo | Tecnica | Status |
|---|---|---|
| M2.A | Alias de tupla de refs | proximo |
| M2.B? | RLE nao-adjacente (linhas inteiras identicas) | a avaliar |
| M2.C? | Template + slot (linhas com estrutura igual, valor diff) | a avaliar |

Prioridade M2.A — tem caso visivel nos datasets atuais.
M2.B e M2.C dependem de existir caso nos datasets canonicos.

## Comparacao com M1

| Camada de redundancia | Macro | Status |
|---|---|---|
| Local (dentro da linha) | M1 | fechado (M1.A,A',B,E,C,D) |
| Entre linhas (tuplas) | M2 | em andamento |
| Estrutural (declaracao de no fonte) | parcialmente M1.D | aberto |
| Multi-coluna | macro futuro | nao iniciado |

## Limitacoes herdadas

- Datasets sinteticos viesados (mesmos D1-D4)
- Apenas 4 datasets (mesma coverage limitada)
- Foco em camada 2 (entre linhas) — outras camadas continuam
  abertas

## Decisao apos M2

Se M2.A revelar economia escalavel (proporcional a R repeticoes),
considerar incorporar em prototipo. Se ganho for marginal nos
canonicos mas analise mostrar escala boa, ainda vale.

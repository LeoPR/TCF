# Macro M3 — Encadeamento de declaracoes

**Status**: em curso (2026-05-13)
**Local**: `experiments/lab/dirty/2026-05-13-M3-encadeamento-declaracoes/`
**Predecessores**: M1 (marcacao local, fechado), M2 (entre linhas, fechado)
**Background**: hipotese antiga (Labs 20-21 do `Mobsolete/` antigo `old/`)
recapitulada com metodologia atual.

## Manifesto

Macro complementar a M1 e M2. Ataca **Camada 3 de redundancia** —
declaracoes de nos fonte compartilham prefixos longos que poderiam
ser declarados uma vez e referenciados.

**Hipotese do user (2026-05-13)**:
> "se eu tenho uma sequencia de nos, eu usaria o no pai deles pra
> gerar mais um no. Logo se eu tiver nos agrupados usados com
> frequencia, eu tiraria a carga das referencias agrupadas."

## Camadas de redundancia atacadas pelo macros do dirty

| Camada | Onde aparece | Macro | Sintaxe |
|---|---|---|---|
| 1 — local | dentro da linha | M1 | escape escopo, range, sumida |
| 2 — entre linhas | tuplas de refs repetidas | M2 | alias `$N` |
| **3 — declaracao** | **prefixos compartilhados em multiplos eids** | **M3** | **`&N=conteudo`** |

## Diferenca vs M2.A

M2.A agrupa **refs** (lista de indices). M3 agrupa **nos inteiros**
(substring textual que serve de base para multiplos eids).

Sao **ortogonais** — podem coexistir num formato final.

## Micros planejados

| Codigo | Tecnica | Status |
|---|---|---|
| **M3.A** | No compartilhado simples (`&N=conteudo`) | proximo |
| M3.B | Encadeamento `&N=&P+ext` (Lab 20 antigo) | apos M3.A |
| M3.C | Heuristica meta single vs multi-afixo | se M3.B revelar trade-off |

## Padrao de organizacao (novo em M3)

Diferente de M1/M2 onde TCFs viviam em `resultados/<sintaxe>/`
central, M3+ tem **tudo dentro de cada micro** (autocontido):

```
M3-A-no-compartilhado/
  README.md          principio + tecnica
  syntax.py          implementacao
  conclusoes.md      analise pos-rodagem
  output/            TCFs (.tcf por dataset)
  decoded/           contra-prova (.csv)
  debug/             detalhado (.txt)
```

A pasta `resultados/` central contem apenas matriz consolidada
md/csv comparando os micros entre si.

## Datasets

D1-D4 canonicos (copia de M1/M2):
- D1 emails-simples
- D2 emails-quote-id
- D3 stress-substring
- D4 caos-mix

Stress-test rodada-3 (favoravel/adversarial pra encadeamento)
sera adicionado em `data_extra/` apos M3.A inicial.

## Limitacoes herdadas

- Mesmos 4 datasets pequenos
- `&` reservado em literais (datasets D1-D4 nao tem `&`)
- Encadeamento profundo (M3.B) requer infra adicional no detector

## Comparacao com baseline

Baseline para M3 sera **M1.E + M2.A combinados** quando possivel,
ou apenas M1.E se M2.A nao for trivialmente integravel.

Para a primeira rodada, baseline = M1.E (676 bytes em D1-D4).

## Estrutura

```
2026-05-13-M3-encadeamento-declaracoes/
  README.md            (este)
  online.py            (raiz exp 16, intocado)
  syntax_base.py       (interface Syntax)
  data/
    D1-D4.csv          (canonicos)
  M3-A-no-compartilhado/
    README.md
    syntax.py
    conclusoes.md
    output/
    decoded/
    debug/
  M1-E-range-baseline/  (a adicionar quando rodar)
    syntax.py           (copia para comparar)
  notas/               (insights teoricos)
  resultados/          (matriz consolidada apenas)
  run_lote.py          (script unificado, escreve em output/decoded/debug por micro)
```

## Rastreamento

Memoria persistente: `project_macro_M3_encadeamento` no auto-memory.

Estado atual: M3 aberto, M3.A pendente de implementacao.

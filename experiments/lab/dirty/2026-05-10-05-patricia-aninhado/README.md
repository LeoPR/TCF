# 05 — patricia com decl aninhada

## Princípio / motivação

Continua a serialização inline do exp 03, levando a ideia mais
fundo. No exp 03 a decl de um pai Patricia (nó interno sem
ocorrência própria) ficava como **decl tardia** ao final do body —
ainda como "header solto", só que dentro do `<body>`. Exemplo do
exp 04:

```
no3: filho_de(no4) + "ina"     ← Marina (forward ref para no4)
...
no4: decl folha "Mar"          ← decl tardia, no fim do body
```

Aqui o pai é **embutido na própria decl do filho** que primeiro o
referencia. Quando o avô também não existe, é embutido recursivamente:

```
no1: filho_de(no2=decl folha "Mar") + "ina"
```

Decls subsequentes que precisem do mesmo pai usam apenas a referência:

```
no5: filho_de(no2) + "cio"     ← Mar já foi declarado dentro de no1
```

A ferramenta é atemporal: a estratégia de "decl embutida na 1ª que
precisa" funciona para qualquer árvore Patricia, independente de
versão.

A numeração dos nós (`no1`, `no2`, ...) continua por ordem de
aparição (alocação) — o user pediu para não nos preocuparmos com
isso ainda; depois evoluímos para uma simbologia melhor.

## Propósito

Responde a duas perguntas:

1. **Viabilidade**: dá pra serializar decls aninhadas recursivamente
   (pai dentro do filho, avô dentro do pai) e ainda ter roundtrip?
2. **Comportamento**: como a árvore se distribui visualmente quando
   toda decl aparece no ponto onde é primeiro necessária?

## Comparação

- **Compara com**: [03-patricia-inline](../2026-05-10-03-patricia-inline/)
  e [04-formato-normalizado](../2026-05-10-04-formato-normalizado/).
- **É comparável?** Parcialmente. Usa serialização inline (do 03)
  com a mesma régua de formato (do 04, sem comentários, count=1
  omitido), mas com a diferença qualitativa de **eliminar decls
  tardias** ao embutir os pais.
- O que muda em relação ao 03/04: zero decls tardias. Pais
  intermediários aparecem em pontos do body — dentro da decl do
  primeiro filho que precisa deles.

## Cenários e valores possíveis

4 datasets didáticos, 30 linhas cada:

| Dataset | Conteúdo | N_unique | N_pat_int | Patricia |
|---|---|---:|---:|---|
| D1 — sem-prefixo | Ana, Bob, Carlos, Diana, Edu | 5 | 0 | inativo |
| D2 — um-prefixo | Marina, Marcio, Marcelo + Ana, Bob | 5 | 2 | 2 níveis (`Mar`/`Marc`) |
| D3 — hierarquico | USR0001..USR0005 | 5 | 1 | 1 nível (`USR000`) |
| D4 — duas-familias | Marina, Marcio + Paulinho, Paula + Bob | 5 | 2 | 2 prefixos separados |

CSVs escritos manualmente com mistura controlada de runs e
dispersão.

## Resultado observado

Roundtrip OK em **4/4 cenários**. Saídas em
[`encoded/`](encoded/) e [`decoded/`](decoded/).

### Estatísticas

| Dataset | linhas | nós | top-level | filhos | body RLE | bytes |
|---|---:|---:|---:|---:|---:|---:|
| D1 | 30 | 5 | 5 | 0 | 27 | 344 |
| D2 | 30 | 7 | 3 | 4 | 30 | 431 |
| D3 | 30 | 6 | 1 | 5 | 30 | 420 |
| D4 | 30 | 7 | 3 | 4 | 30 | 434 |

### Comportamento qualitativo

- **D1** (sem Patricia): nenhuma decl aninhada. Output essencialmente
  igual ao exp 03/04 inline normalizado.
- **D2** (1 prefixo profundo): aninhamento de 2 níveis acionou.
  Marcio é declarado como `filho_de(no5=decl filho_de(no2) + "c") + "io"`
  — cadeia recursiva onde no5 (`Marc`) é decl aninhada dentro da
  decl de Marcio, e dentro dela está a ref para no2 (`Mar`) que já
  havia sido declarado pela 1ª ocorrência de Marina.
- **D3** (hierárquico raso): apenas 1 nível Patricia (USR000). 1ª
  linha embute a decl de USR000.
- **D4** (2 prefixos separados): 2 decls aninhadas independentes,
  cada uma na 1ª folha do seu prefixo.

Ver [conclusoes.md](conclusoes.md) para o TCF completo de cada
cenário, com leitura linha a linha.

## Limitações

- Numeração de nós (`no1`, `no2`, ...) sequencial por ordem de
  aparição. **Não é otimizada** — pode-se usar índices mais curtos
  ou implícitos por ordem de declaração. Próximo experimento.
- Marcadores ainda verbosos por design (`filho_de`, `decl folha`,
  `+`, aspas). Não é teste de byte-economy.
- 4 datasets pequenos (30 linhas, cardinalidade 5). Não fala sobre
  escala ou cardinalidade alta.
- Parser do decode é manual e específico para esta sintaxe; não foi
  testado contra inputs malformados.
- Algoritmo Patricia (`patricia.py`) é byte-idêntico ao dos exps
  02–04 — nenhuma diferença vem dele.
- Não há comparação numérica de bytes vs 04. A diferença pertence
  qualitativamente à camada 2 (marcadores): o aninhado elimina
  decls tardias, mas adiciona caracteres dentro de decls externas.
  Medição comparativa fica para experimento posterior.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-05-patricia-aninhado
python run.py
```

Saída imprime estatísticas + árvore Patricia + TCF completo para
cada cenário. Arquivos gerados em `encoded/*.tcf` e `decoded/*.csv`.

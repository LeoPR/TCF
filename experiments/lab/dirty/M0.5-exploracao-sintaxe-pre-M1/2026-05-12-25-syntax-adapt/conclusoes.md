# Conclusões — bug corrigido, substituição não compensa em pequena escala

Roundtrip OK em todas as sintaxes válidas (v3 e v2 falham em
datasets que não suportam, como esperado).

## Achado 1 — sua intuição estava correta sobre v4-quote

> "lembre que o conflito TEM que existir, não é para ficar usando
> aspas e ai se tiver aspas ai faz scape isso nào faz sentido"

Em v3 base, `'` não é marcador. v4-q antigo (exp 24) forçava
aspas indevidamente. v4-q-fix corrige isso:

| Dataset | v4-q antigo | v4-q-fix | Mudança |
|---|---:|---:|---|
| nomes-com-aspas | 181 | **161** | **-20 bytes (-11%)** |
| emails-com-id | 213 | 214 | +1 (regra de separador mais conservadora) |
| codigos-com-arroba | 92 | 93 | +1 |
| caos-mix | 158 | 160 | +2 |

A regra correta de `_precisa_aspas`: dispara apenas se houver
**char que mudaria modo do parser** (dígito ou `*`). `'` no
literal é char comum.

## Achado 2 — substituição global tem ROI mínimo

Em todos os 4 datasets testados, **substituição global perdeu**
para v4-escape ou v4-quote.

Análise matemática:

```
ganho_substituição = N × C
custo_substituição = 4 (header `~*+\n`)

vale_se: N × C > 4
```

Onde:
- N = ocorrências do char substituído em **fragmentos literais
  distintos**
- C = custo por escape no método alternativo (1 byte para `\*`,
  2 para `'*'`)

Para C=1 (escape): N > 4 ocorrências
Para C=2 (quote): N > 2 ocorrências

Em **codigos-com-arroba**: o `*` aparece em **1 fragmento literal
distinto** (`@2026*00`). N=1. Substituição perde.

Em **caos-mix**: `*` aparece em **2 fragmentos distintos** (vários
literais curtos com `*`). N=2. Empate com escape. Perde com aspas.

## Achado 3 — fragmentação concentra chars ambíguos

O algoritmo do online.py **fatora padrões**. Strings que
compartilham o padrão `@2026*00` em codigos viram refs ao mesmo
fragmento. O `*` aparece **1 vez** no body (no fragmento
declarado), não 12 vezes.

Em datasets do regime A (fatorização forte), chars ambíguos
ficam **concentrados em poucos fragmentos**. Substituição
global tem N pequeno e overhead do header.

Substituição global brilharia em datasets onde:
- Cada nome único contém `*` (não fatorável)
- Datasets do regime B (uuids, cpfs) — mas esses falham por
  outras razões

## Achado 4 — separador entre literais consecutivos é necessário

v4-q-fix força `*` entre 2 literais consecutivos quando o
anterior não tem aspas (mesmo se atual tem aspas). Custo: 1-2
bytes em alguns datasets. Razão: parser sem ambiguidade em
casos onde literal sem aspas é seguido de literal com aspas.

Alternativa explorada no exp 23: o parser distingue por
contexto (`'` no início de elemento abre modo aspas). Mas isso
exige flag `expectando_elemento` que adiciona complexidade.

Trade-off: v4-q-fix prefere **simplicidade do parser** vs **1-2
bytes**. Decisão consciente.

## Síntese matemática — quando cada técnica vence

| Técnica | Custo | Vence se |
|---|---|---|
| **Escape** (`\X`) | 1 byte por char | K_ambíguos ≤ 1 e K_ambíguos < N_substituídos − 4 |
| **Quote** (`'X'`) | 2 bytes por literal | K_ambíguos ≥ 3 |
| **Substitution** (header `~*+`) | 4 bytes uma vez | N_fragmentos_com_char > 4 |

Datasets do regime A (fatorização forte): escape ou quote local
ganham. Substituição não compensa.

Datasets do regime B (uuids/cpfs): fatorização é fraca, mas
chars ambíguos no literal são poucos por nó. Substituição
ainda não compensa.

**Substituição global brilharia em**: dataset com many fragmentos
distintos contendo o mesmo char ambíguo. Esse cenário não
apareceu nos 4 datasets testados.

## Validação das hipóteses do user

> "uma é ter um default pra os marcadores, assim eles são gerados
> implicivamente e a versão do TCF garante o padrão, caso mude o
> padrão, poderiamos gastar 'alguns bytes' orientando sobre uma
> nova variação de syntaxe"

Implementado em v5-adapt-* (header `~*+`). **Funciona** mas o
overhead do header (4 bytes) raramente compensa nos datasets
atuais.

> "OU colocando algum marcador especial na linha que exista a
> aambiguidade"

Equivalente a v4-quote local (aspas só nos literais com
ambiguidade). **Implementado e funciona**. Trade-off vs escape:
limiar K=2.

> "Enfim, pesquise técnicas de escape usados no csv por exemplo"
> "sei que ele permite, inclusive, colocar caracteres esquisitos
> ou sequencias estranhas como escape, bastando começar com ele,
> pode ser qualquer coisa."

Em CSV (RFC 4180): aspas duplas delimitam campos com vírgulas,
e `""` dentro representa `"`. Análogo ao v4-quote para `'`.

CSV custom delimiter: usa TAB, `;`, `|` em vez de `,` — análogo
à substituição global v5-adapt. Mas em CSV é declarado **fora do
arquivo** (no header HTTP ou similar), sem custo dentro do dado.

Para TCF, declarar fora do dado teria custo zero. Algo a
considerar: incluir versão/marcadores no header HTTP ou nome de
arquivo, e omitir do conteúdo. Mas isso quebra autocontenção.

## Pontos a registrar

1. **Bug v4-q corrigido**: `'` não dispara aspas. Ganho de 20
   bytes em nomes-com-aspas.

2. **Substituição global não compensa em datasets atuais**:
   header de 4 bytes raramente se paga com a economia local.

3. **Fatorização concentra chars ambíguos**: o algoritmo do
   online.py faz cada padrão aparecer **1 vez** em fragmento
   literal, então N_ocorrências é pequeno.

4. **Para um dataset onde substituição valeria**: precisaria
   estrutura com muitas variações distintas contendo o mesmo
   char ambíguo. Não emergiu nos 4 testados.

5. **v4-q-fix é a sintaxe segura padrão** para datasets com `'`,
   dígitos ou `*` no literal. v4-escape é equivalente em maioria,
   melhor em literais com K=1 ambíguo.

## O que este experimento não mostra

- Dataset onde substituição realmente brilharia (alta densidade
  de char ambíguo em fragmentos distintos)
- Versão fora-do-dado (declaração de marcadores via header HTTP
  ou nome de arquivo)
- Sintaxes binárias (chars Unicode reservados para marcadores)
- Comparação com gzip downstream

## Próximos passos sugeridos

**Direção A — fechar a investigação de sintaxe**:
- Testar v4-q-fix nos 21 datasets do exp 19 para ver se generaliza
- Comparar com v3 + escape onde aplicável

**Direção B — benchmark externo** (recomendada):
- TCF (v4-q-fix ou v4-escape) + gzip vs CSV + gzip
- Saber se o ganho de 50% sobrevive a compressão estatística

**Direção C — abandonar refinamento de sintaxe textual**:
- Saltar para sintaxe binária (chars Unicode reservados)
- Ou parar de mexer em sintaxe e voltar para o algoritmo (com
  exp 16 modular já validado)

A sequência natural me parece **B antes de tudo** — depois das
20+ sintaxes testadas, é hora de medir se TCF compete
externamente. Sem isso, refinar mais é otimização sem norte.

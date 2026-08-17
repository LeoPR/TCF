# Procedência — corpus real + 14 capacidades sintéticas

## As duas fontes

**1. Corpus** (`Z:/tcf-data/interim/*.db`, somente leitura, nada baixado): as mesmas 23
tabelas da auditoria do `.8M` ([lab `2130`](../2026-08-16-2130-auditoria-do-M-no-corpus/)),
com a **mesma amostragem** — janela contígua do meio, alvo 2000 linhas (régua do lab `0530`).
Isso torna os dois labs **diretamente comparáveis**, que é o ponto do bloco 4.

**2. Capacidades sintéticas** (14 casos no `run.py`): objeto aninhado, array de escalares,
array de objetos, array de arrays, null, ragged, raiz-objeto, raiz-escalar, vazios. São
mínimos de propósito — servem para **ler a gramática**, não para medir bytes.

## A CONSTANTE do bloco 4

Os **mesmos valores** viram `dict[str, list[str]]` (rota `.8M`) e `list[dict]` (rota `.8H`).
Muda só a forma de chamada, portanto a rota. É o que permite atribuir a diferença à rota e não
ao dado.

## Vieses declarados — e um deles é grande

- **O `.8H` está sendo medido em dado RETANGULAR.** É o caso onde ele é mais desfavorecido: um
  dado retangular não usa nada do que justifica o `.8H` (aninhamento, ragged, tipo, null). **Os
  +23% são o custo de usar o `.8H` onde o `.8M` daria conta**, não o custo do `.8H` no domínio
  dele. Um corpus com aninhamento real **não existe** em `Z:` — é lacuna declarada.
- **`NULL` vira string vazia** nas duas rotas. A comparação é justa, mas nenhuma das duas está
  exercitando nulo de verdade — e o `?` do `.8H` é justamente o glifo para isso.
- **Amostra de 2000 linhas/tabela** (0,3–0,4% nas maiores).
- **`tpch-sf001` é prefixo do `sf01`**: o TPC-H tem peso dobrado (16 de 23 tabelas).
- **A contagem de bytes de "nomes" no bloco 5 é aproximada** — soma o comprimento dos nomes de
  coluna, sem descontar escapes. Serve para a proporção (61% do header), não como número exato.

# Combinatória simples — teste de mesa

**Data:** 2026-05-07
**Princípio:** sem cabeçalho, sem manifest, sem motor. Só dado e transformação.

A ideia: antes de pensar em como o TCF se descreve, primeiro entender como
ele se *transforma* sob diferentes pressões (comprimir, quebrar). O cabeçalho
vem depois — é função do que escolhemos aqui.

## Arquivos

| Arquivo | O que tem |
|---|---|
| `00-dados.md`       | Os dados crus (12 linhas, 4 colunas) + cenário-alvo |
| `01-compressao.md`  | 9 hipóteses de compressão, com bloco vazio para preencher |
| `02-quebra.md`      | 6 hipóteses de quebra, com bloco vazio para preencher |
| `03-matriz.md`      | Tabela combinatória C × B, marcar quais combinações testar |

## Como usar

1. Abrir `03-matriz.md`, marcar 8-12 combinações de interesse.
2. Para cada combinação marcada, preencher o bloco correspondente em
   `01-compressao.md` (a parte de compressão) e em `02-quebra.md` (a parte
   de quebra).
3. Anotar bytes e observações nos campos `_____`.
4. Quando terminar, voltar para `PLANO-formato-adaptativo.md` (pasta irmã)
   e revisar as primitivas de cabeçalho à luz do que aprendeu aqui.

## Regra do exercício

Não inventar header. Não escrever `# TCF v0.4`. Não usar `@chunk`. A pergunta
é apenas: **quando eu reescrevo esses dados dessa forma, quanto fica? quanto
do "início" do arquivo já é útil? a quebra preservou o que a compressão fez?**

O cabeçalho aparece depois, quando soubermos o que ele precisa carregar.

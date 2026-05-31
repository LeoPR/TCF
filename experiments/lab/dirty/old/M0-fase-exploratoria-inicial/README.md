# M0 — Fase exploratoria inicial v0.6

**Periodo**: 2026-05-10 a 2026-05-11 (16 experimentos)
**Estado**: fechado (16 exps que culminaram no algoritmo limpo)
**Marco final**: exp 16 (`online-cleanup`) — raiz da cristalizacao

## Proposito desta fase

Preparo do v0.6: amostras de dados, exploracao de tecnicas
(Patricia forward, reverse, bidir, aninhado), Re-Pair bottom-up,
motor online incremental, e refinamentos ate' chegar num algoritmo
limpo e estavel — o **exp 16** que se tornou o `online.py` raiz
usado em M1, M2 e M3.

**Esta fase NAO e' canonica** — e' a sequencia de tentativas que
levou a' formacao. Cada experimento responde a uma pergunta
especifica de viabilidade ou comportamento.

## Marco — exp 16

Exp 16 e' o ponto onde:
- Algoritmo online incremental (TokLit + TokRefPref + TokRefSuf)
  ficou em forma estavel
- Sem revisao de selecoes anteriores
- 4 candidatos reduzidos para 2 em `_escolher_par`
- RLE adjacente em funcao propria
- Codigo limpo, sem ruido

Esse `online.py` foi copiado para M1, M2 e M3 sem modificacao.

## Lista de experimentos

| Ord | Tema | Tipo |
|---|---|---|
| 01 | amostras-iniciais | paralelo (fundacao) |
| 02 | patricia-nomes | viabilidade + comportamento |
| 03 | patricia-inline | comparacao serializacao |
| 04 | formato-normalizado | comparacao justa + formula |
| 05 | patricia-aninhado | viabilidade (decl recursiva) |
| 06 | aninhado-emails-urls | viabilidade dados realistas |
| 07 | patricia-reverso | viabilidade do espelho |
| 08 | patricia-bidir-composto | composicao pref+mid+suf |
| 09 | debug-bidir-d2 | instrumentacao |
| 10 | decomposicao-com-avos | decomp na cadeia ancestral |
| 11 | padroes-no-encode | instrumentacao padroes |
| 12 | debug-hierarquia-decl | analise decl hierarquica |
| 13 | repair-bottomup | Re-Pair substring qualquer pos |
| 14 | online-sem-revisao | online incremental sem revisao |
| 15 | online-com-fix | fix exp 14 (overlap) |
| **16** | **online-cleanup** | **refatoracao estrutural — marco** |

## O que ficou

- **Algoritmo raiz**: `online.py` do exp 16
- **Aprendizados sobre Patricia, Re-Pair, online**: registrados nos
  conclusoes.md de cada exp
- **Datasets sinteticos**: amostras de varios tipos (catalog em
  exp 01)

## O que NAO ficou

- Decisoes especificas de sintaxe (ficaram para M0.5)
- Marcacao de ambiguidade (ficou para M1)
- Redundancia entre linhas (M2)
- Encadeamento de declaracoes (M3)

## Como referenciar

Estes experimentos sao **historicos** — base da formacao do v0.6.
Citar por:
- Conceito que foi testado (Patricia, online, Re-Pair)
- Aprendizado registrado em `conclusoes.md`
- NAO por bytes/numeros absolutos (formato muda entre exps)

Para detalhes, ver `README.md` de cada subexperimento.

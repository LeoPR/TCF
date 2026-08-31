---
title: RLE textual e util ou gzip ja faz o trabalho? Pesquisa + teste
type: research
status: OPEN
priority: HIGH
created: 2026-04-10
origin: Hipotese de que gzip interno ja faz RLE, tornando o RLE textual do TCF redundante
---

# RLE Textual e Util ou Redundante com gzip?

## Pergunta central

gzip usa DEFLATE = LZ77 + Huffman. LZ77 ja identifica repeticoes
consecutivas e comprime. Entao: o RLE textual do TCF (`3*Ana`) e
**redundante** quando a saida passa por gzip?

Possibilidades:
1. **RLE e redundante:** gzip comprime igual com ou sem RLE prefix → so complicacao
2. **RLE ajuda gzip:** formato pre-processado comprime melhor (LZ77 tem menos trabalho)
3. **RLE atrapalha gzip:** introduz caracteres `*` que nao aparecem no texto, quebrando runs naturais
4. **RLE e util para LLMs mas neutro para gzip:** o valor do RLE e legibilidade, nao compressao

## Evidencia da literatura

- **LZW > RLE** para dados tipicos (Quora, benchmarks lzbench)
- **zstd-19 > gzip > RLE simples** em texto geral
- **Hibrido RLE+LZW+Huffman** atinge 2.42x ratio — combinacao ajuda
  (Arxiv 2504.20747, Devanagari text)
- gzip DEFLATE e essencialmente LZ77 que **ja faz RLE** como caso
  degenerado (match com distance=1)

**Implicacao:** para compressao BINARIA pura, RLE textual e inutil.
O valor do TCF seria outro (legibilidade LLM, interpretabilidade).

## Evidencia dos nossos testes (P-transport-compression)

Ja temos dados parciais:

| Scale | csv+gz | L0+gz | L2+gz | L3+gz |
|-------|--------|-------|-------|-------|
| 50 | 1479 | **1470** | 1420 | 1467 |
| 200 | 5626 | **5028** | 5147 | **4752** |
| 1000 | 25209 | **21572** | 22179 | **19859** |
| 5000 | 125948 | **96643** | 100963 | **89472** |

**Observacao:** L0+gz (SEM RLE) e menor que L2+gz (COM RLE) em escalas
intermediarias (50, 200, 1000). Isso sugere que **RLE textual pode
atrapalhar o gzip** em alguns casos — gzip ja faria um trabalho melhor
sem a notacao `N*val`.

L3+gz vence por causa do DICT, nao do RLE.

## Hipotese testavel

**H-rle-transport:** RLE textual do TCF (notacao `N*val`) NAO agrega
valor de compressao quando o saida passa por gzip. O valor do L2 e
o **sort** (que ajuda o LZ77), nao o RLE em si.

**Teste:**
- Criar variante TCF L2-without-rle: sorted mas sem RLE (repete valores)
- Comparar L2 (sort+RLE) vs L2-no-rle (so sort) apos gzip
- Se L2-no-rle + gzip ≤ L2 + gzip → RLE e inutil para transporte
- Se L2 + gzip < L2-no-rle + gzip → RLE ajuda (investigar por que)

**Variacoes:**
- So RLE, sem sort (L1 atual) — ja testado
- Sort sem RLE — novo, testar
- Sort + RLE — L2 atual
- Dict + sort + RLE — L3 atual
- Dict + sort sem RLE — novo, testar

## Por que manter RLE mesmo se nao ajuda compressao?

**Se H-rle-transport for confirmada**, RLE ainda pode ser valioso para:

1. **Legibilidade humana** — `3*Ana` e mais conciso que 3 linhas iguais
2. **LLM interpretation** — `3*Ana` pode ajudar LLM a entender estrutura
3. **Token count LLM** — menos tokens no prompt (cada linha = mais tokens)

Entao o paper pode separar duas narrativas:
- **Transporte HTTP:** RLE opcional, sort+gzip suficiente
- **LLM input:** RLE util (legibilidade + tokens)

Isso reforca E-http-protocol (alternativas sem RLE para transporte)
e diferencia os casos de uso.

## Relacao com outros tickets

- **P-transport-compression** (CLOSED): so testou 5 formatos, nao isolou RLE
- **E-http-protocol**: precisa incluir variante "sort-only"
- **H-compression-layers**: niveis podem ter flag `--rle=false`
- **T-multi-lang**: decoder tem que suportar a variante se for adicionada

## Tarefas

- [ ] Implementar flag `--no-rle` no encoder
- [ ] Gerar variantes L2-sort-only, L3-dict-sort
- [ ] Rodar compression benchmark expandido
- [ ] Se RLE nao ajuda: documentar como "RLE e para LLMs, nao transporte"
- [ ] Testar accuracy LLM com/sem RLE (separado)

# Result — TCF estagiado × brotli + ordenação × compressão [probatório]

**Data**: 2026-06-16 · **Tipo**: [probatório] · FORK (não toca src/tcf) ·
4 datasets reais (Z:), 3000 linhas. `analyze.py`.

Duas perguntas do owner. Revisão prévia confirmou que **nenhuma** tinha sido medida:
EXP-008 mediu TCF-cheio × compressores (single-col); 2026-06-14-ordering mediu ordenação
× TCF-sozinho. Aqui: multi-col, estagiado, e ordenação × TCF+brotli.

## C — "Aplicar MENOS TCF deixa o brotli comprimir mais?" → **REFUTADO**

Sweep de intensidade de TCF, cada etapa sozinha e +brotli (q11). Bytes +brotli:

| dataset | csv | tcf-lite | tcf-M10 (#6) | **tcf-0.7** | menor |
|---|---:|---:|---:|---:|---|
| adult | 30390 | 30050 | 26329 | **21841** | tcf-0.7 |
| online-retail | 29489 | 31393 | 28914 | **28833** | tcf-0.7 |
| receita | 31533 | 37868 | 36112 | **27111** | tcf-0.7 |
| tpch-lineitem | 84406 | 96983 | 84949 | **67519** | tcf-0.7 |

- **Mais TCF → +brotli MENOR, em 4/4.** O TCF mais agressivo (0.7, com fallback/dict/split)
  dá o **menor** resultado pós-brotli em todos. A hipótese ("menos TCF ajuda o brotli") é
  refutada em escala real.
- **Meio-termo é o pior**: `tcf-lite` (OBAT só, sem seq-RLE/delta/V2) +brotli chega a ser
  **pior que csv+brotli** (online 31.4k vs 29.5k; receita 37.9k vs 31.5k). TCF pela metade
  adiciona estrutura/escape sem o payoff do dedup → atrapalha o brotli. Ou pouco TCF, ou TCF cheio.
- **Corrige a impressão do cadastro minúsculo** (README): lá CSV+brotli vencia (162 vs 185) —
  artefato de payload de 4 linhas (moldura + nada pra fatorar). Em tabela real, **TCF-0.7+brotli
  vence o CSV+brotli** com folga (adult −28%: 21.8k vs 30.4k).

## E — Ordenação × {TCF, TCF+brotli} no multi-col

`sort_by` por chave low-card, vs `none`:

| dataset | melhor p/ TCF | melhor p/ TCF+brotli | iguais? |
|---|---|---|---|
| adult | sort:race (94.8%) | sort:sex (95.9%) | **não** |
| online-retail | none (100%) | sort:CustomerID (98.9%) | **não** |
| receita | sort:matriz_filial (96.9%) | sort:matriz_filial (98.3%) | sim |
| tpch-lineitem | sort:l_returnflag (98.5%) | sort:l_linestatus (99.2%) | **não** |

- **Ganho modesto**: TCF-sozinho até −5% (adult), ~1-3% no resto; +brotli 1-4%. Consistente
  com 2026-06-14-ordering (5-15% só onde há chave low-card forte; 3k linhas mistas → menos).
- **Achado novo**: a **melhor chave de ordenação para TCF-sozinho ≠ a melhor para TCF+brotli**
  em 3/4. Ex.: adult — TCF prefere `race`, TCF+brotli prefere `sex`. Ou seja, se um brotli vai
  rodar por cima, a escolha ótima de `sort_by` muda. Um seletor de ordenação ideal precisaria
  saber se haverá compressão binária a jusante.

## Leitura / próximos

1. **TCF e brotli são complementares de verdade — e o TCF cheio é o melhor pré-processo**
   (em escala). Atualizar o discurso do README (hoje subvende com o cadastro minúsculo).
2. Ordenação: lever pequeno (≤5%) e dependente do codec a jusante. Baixa prioridade; se welder
   um auto-`sort_by`, considerar o modo (com/sem brotli). Registrar, não atacar agora.
3. Nada toca src/tcf; estudo exploratório.

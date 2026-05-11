# Síntese — algoritmos de compressão textual v0.6 (exps 01-15)

Data: 2026-05-11
Escopo: ciclo de experimentos dirty/v0.6 (reset 2026-05-10).
Objetivo: consolidar o que foi descoberto, com vocabulário sóbrio
e bidirecionalidade entre conceito abstrato e implementação.

> Convenção: o ciclo anterior (v0.5, em `dirty/old/`) foi tratado
> como obsoleto. Esta síntese resume apenas o v0.6, que se baseou
> em teoria/literatura, não no código antigo.

---

## 1. Problema

TCF (Textual Columnar Format) precisa comprimir colunas de strings
relacionais (nomes, emails, URLs, IDs) em formato textual legível
para LLMs lerem em contexto. Requisitos:

- **Roundtrip lossless** — decodificação reproduz o input
  caractere por caractere
- **Densidade razoável** — competitivo com CSV/JSON/HTFC
- **Estrutura inspecionável** — texto inteligível pelo LLM

A coluna típica tem 20-1000+ strings com **padrões compartilhados**
(domínios de email, base de URLs, prefixos de nomes). O algoritmo
deve fatorar esses padrões.

---

## 2. Trade-off triangular

Compressão de coluna tem 3 eixos em tensão:

```
          Compressão
             /\
            /  \
           /    \
      Latência──Memória
```

- **Compressão** — densidade bytes/string
- **Latência** — tempo até primeiro byte de output (streaming-friendly)
- **Memória** — quanto da entrada precisa caber em memória ao processar

Algoritmos clássicos ocupam vértices isolados:

| Algoritmo | Vértice principal |
|---|---|
| LZ77 streaming | Latência baixa |
| Re-Pair batch (Larsson & Moffat 2000) | Compressão alta |
| Cache de strings já vistas | Memória ↑ velocidade |

A proposta v0.6 é **um algoritmo parametrizável** que desliza pelos 3
eixos via:
- Quando "soltar output" (latência ↓ ↔ compressão ↑)
- Quanto revisar retroativamente (compressão ↑ ↔ latência ↑)
- Quanto cachear vs reconstruir (memória ↑ ↔ velocidade ↑)

---

## 3. Caminho exploratório

### Fase A — Patricia bidirecional (exps 02-12)

Hipótese inicial: comprimir cada string como
`prefixo_comum + meio + sufixo_comum`, usando duas árvores Patricia
(uma forward, uma reverse sobre strings invertidas).

- **exps 02-06** construíram Patricia, encoder com decl aninhada
  recursiva, decodificador.
- **exp 07** introduziu árvore reverse para detectar sufixos.
- **exp 08** combinou as duas em decomposição `pref + middle + suf`.
- **exp 09** identificou que decomposição usava só pai imediato,
  ignorando avôs.
- **exp 10** corrigiu — escolha entre níveis da cadeia.
- **exps 11-12** mediram potencial de fatorização adicional
  (`mid+suf`, decl hierárquica). Conclusão: sintaxe verbosa
  consume os ganhos.

Patricia bidirecional **funciona** mas a abordagem é complexa
(2 árvores, decomposição com cadeia, heurística de overlap) e
não captura padrões "no meio" das strings.

### Fase B — Re-Pair (exp 13)

Pivô para abordagem batch global. Re-Pair (Larsson & Moffat 2000)
extrai a substring de maior `len × count` e substitui em todas as
strings. Repete.

- Detecta padrões em **qualquer posição** (não só borda)
- **Elimina necessidade** de árvore reverse separada
- Sintaxe mais limpa (sem `pref:`/`suf:`)

Resultado: **-31.8% em D2-completo, -16% em D4** em bytes literais
vs exp 10.

### Fase C — Online incremental (exps 14-15)

Re-Pair é batch — precisa de todas as strings antes de processar.
Para streaming, é necessário algoritmo **online** que processa uma
string por vez e pode emitir output incremental.

- **exp 14** — online sem revisão. Para cada nova string, busca
  melhor LCP e LCS entre todas as anteriores. Vence Re-Pair em
  D4 (-25 bytes) mas perde em D2 (+6, +16).
- **exp 15** — online com fix. Quando overlap entre pref/suf
  identificados, considera **alternativas com sufixo/prefixo
  menores que caibam**. Vence Re-Pair em ambas as métricas:
  -33% a -37% em unidades de informação.

---

## 4. Algoritmo final (exp 15) em descrição abstrata

Para cada string `s` na ordem de entrada:

```
SE é primeira string:
    emitir s como literal puro
    PARAR
PARA cada string anterior s_prev:
    LCP_prev := comprimento do prefixo comum mais longo de s e s_prev
    LCS_prev := comprimento do sufixo comum mais longo de s e s_prev
melhor_pref := max(LCP_prev) onde LCP_prev >= min_len
melhor_suf  := max(LCS_prev) onde LCS_prev >= min_len

SE melhor_pref + melhor_suf <= len(s):
    usar diretamente
SENÃO (overlap):
    candidato_A := (melhor_pref, maior sufixo de qualquer s_prev
                    que caiba em len(s) - melhor_pref)
    candidato_B := (maior prefixo simétrico, melhor_suf)
    candidato_C := (melhor_pref, 0)
    candidato_D := (0, melhor_suf)
    escolher candidato de maior cobertura (tie: maior prefixo)

emitir: TokRefPref + TokLit(meio) + TokRefSuf
        (omitir tokens vazios)
```

Características:

- **Sem revisão retroativa** — strings já emitidas não são
  modificadas
- **Streaming-friendly** — cada string pode ser emitida assim que
  processada
- **Decode em 1 passada** — sem forward refs nem decls tardias
- **Sem árvore reversa** — LCS calculado bidirecionalmente sobre
  strings já cacheadas
- **Memória O(N × max_len)** — strings reconstruídas cacheadas
- **Tempo O(N² × max_len)** — comparação com todas as anteriores

---

## 5. Sintaxe de saída

Cada string vira uma sequência de tokens separados por ` + `:

```
no1: "maria.silva@gmail.com"          # literal puro (1ª string)
no2: no1[0:12] + "hot" + no1[-8:]     # pref(12) + literal + suf(8)
no5: no4[0:11] + no2[-11:]            # pref + suf (zero literal)
```

Notação:
- `noN[0:K]` — primeiros K chars de noN
- `noN[-K:]` — últimos K chars de noN
- `"X"` — literal
- `+` — concatenação

**Esta sintaxe é verbosa por design** (didática). Sintaxe compacta
para fase prototype substituiria `noN[0:K]` por marcadores de 1-2
bytes.

---

## 6. Duas métricas — bytes literais vs unidades de informação

**Bytes literais** medem o TCF como saída atual, em chars. Útil
para inspeção visual, mas distorce comparação porque `noN[0:K]`
ocupa 9 chars na sintaxe verbosa e `RN` (Re-Pair) ocupa 3 chars
— sem que isso reflita diferença estrutural.

**Unidades de informação** medem a estrutura intrínseca:
- 1 ref a um nó/símbolo = **1 unidade**
- 1 char literal = **1 unidade**
- Em Re-Pair, um símbolo declarado conta `len(text) + 1` unidades
- Marcadores macro (`<body>`) e comentários: ignorados

Esta métrica aproxima o que o formato compacto custaria — onde
refs viram 1-2 bytes. Veja
`experiments/lab/dirty/notas/2026-05-11-custo-de-marcadores.md`
para a teoria por trás.

---

## 7. Resultados consolidados (exps 13-15)

### Bytes literais (sintaxe verbosa atual)

| Dataset | exp 10 (Patricia bidir) | exp 13 (Re-Pair) | exp 14 (online v1) | exp 15 (online+fix) |
|---|---:|---:|---:|---:|
| D2-mini | — | 192 | 198 | 193 |
| D2-completo | 655 | 447 | 463 | **441** |
| D4 | 505 | 424 | 399 | **399** |

### Unidades de informação

| Dataset | exp 13 (Re-Pair) | exp 15 (online+fix) | redução |
|---|---:|---:|---:|
| D2-mini | 70 | **47** | -33% |
| D2-completo | 124 | **78** | -37% |
| D4 | 105 | **75** | -29% |

**Exp 15 é o melhor algoritmo até agora em ambas as métricas.**

Roundtrip 3/3 OK em todos os experimentos. Decode em 1 passada.

---

## 8. Por que o online vence

O algoritmo online com fix produz, em D2-completo:

- 4 strings com **literal completo** (introduções genuínas das 4
  famílias: maria, joao, ana, pedro)
- **8 das 12 strings** viram `ref + ref` = 2 unidades cada

Re-Pair declara símbolos compartilhados, mas cada declaração custa
`len(text) + 1` unidades. Para padrões que aparecem em poucas
strings (3-4 ocorrências), esse overhead supera o ganho de
substituição.

Online evita declarações explícitas — referencia sub-partes de
strings já existentes (`noN[0:K]`). Funciona melhor quando há
**similaridade local** entre strings consecutivas/próximas.

---

## 9. Direções abertas

1. **Escala** — testar exp 15 em N=100, 1000, 10000+ strings
2. **Reordenação prévia** — ordenar input para agrupar strings
   similares reduz os "literais de introdução"
3. **Sintaxe compacta** — implementar e medir bytes reais (não
   só estimativa em unidades)
4. **Comparação com HTFC** (Martínez-Prieto et al. 2016) — baseline
   da literatura para dicionários de strings comprimidos
5. **Revisão retroativa** (exp 16 ainda em aberto) — pode trazer
   ganho marginal mas custa latência de flush
6. **Janela deslizante** — limita memória para streaming real

---

## 10. Sobre potencial de publicação

A combinação implementada no exp 15 — **online incremental com
busca de par alternativo em overlap, sem árvore reversa** — não
tem precedente publicado direto, segundo duas rodadas de
pesquisa anterior:

- Sequitur (Nevill-Manning & Witten 1997) opera em sequência
  linear, não em coleção de strings
- Re-Pair (Larsson & Moffat 2000) é batch global, sem variante
  online clássica que use estrutura semelhante
- Front coding (Witten/Moffat/Bell) só usa vizinho lex-adjacente
- Affix tree (Maaß 2003) é para busca, não codificação

**Possível artigo** se acompanhar de:

- Datasets de tamanho realista (não 6-20 strings)
- Comparação empírica com HTFC, RPFC, FSST, Re-Pair, BPE
- Análise de complexidade formal (O(N²·L) é tractable mas
  precisa quantificar)
- Implementação de referência limpa (não dirty)
- Sintaxe compacta validada

É um caminho viável. O conceito está consistente; falta validação
em escala e benchmark formal.

---

## Bidirecionalidade conceito ↔ código

| Conceito abstrato | Implementação |
|---|---|
| Trade-off triangular | Não há código — é o frame conceitual |
| Online incremental sem revisão | `online.py:processar()` itera 1 string por vez |
| LCP/LCS entre s e prev_s | `online.py:lcp_len`, `lcs_len` |
| Busca par alternativo em overlap | `online.py:_escolher_par`, gera 4 candidatos |
| Token = Literal \| RefPref \| RefSuf | dataclasses em `online.py` |
| Sintaxe `noN[a:b]` | `encode_online.py:render_token` |
| Decode em 1 passada | `decode_online.py` com cache linear |
| Unidades de informação | `run.py:unidades_de_tokens` |

Cada conceito mapeia para 1-3 funções/classes. Implementação em
outra linguagem (Rust, C, ou mesmo assembly) é possível mantendo
a mesma estrutura.

---

## Referências citadas

- Larsson, J. J., & Moffat, A. (2000). *Off-line dictionary-based
  compression*. Proceedings of the IEEE, 88(11), 1722-1732.
- Nevill-Manning, C. G., & Witten, I. H. (1997). *Identifying
  hierarchical structure in sequences: A linear-time algorithm*.
  Journal of Artificial Intelligence Research, 7, 67-82.
- Witten, I. H., Moffat, A., & Bell, T. C. (1999). *Managing
  Gigabytes*.
- Maaß, M. (2003). *Linear Bidirectional On-Line Construction of
  Affix Trees*. Algorithmica, 37, 43-74.
- Fraenkel, A. S., Mor, M., & Perl, Y. (1983). *Is text
  compression by prefixes and suffixes practical?*. Acta
  Informatica, 20, 371-389.
- Martínez-Prieto, M. A., Brisaboa, N., Cánovas, R., Claude, F.,
  & Navarro, G. (2016). *Practical compressed string
  dictionaries*. Information Systems, 56, 73-108.
- Ukkonen, E. (1995). *On-line construction of suffix trees*.
  Algorithmica, 14, 249-260.

Notas adicionais em
[`experiments/lab/dirty/notas/2026-05-11-custo-de-marcadores.md`](../../experiments/lab/dirty/notas/2026-05-11-custo-de-marcadores.md).

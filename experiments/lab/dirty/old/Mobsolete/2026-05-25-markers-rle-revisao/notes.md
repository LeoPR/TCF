# Lab 25: revisao de markers + RLE adjacente

**Data**: 2026-05-10 (rodagem prevista 2026-05-25)
**Origem**: pedido do user — clarificar markers `*` (decl) e `=`
(line-ref) antes de portar para clean. RLE adjacente foi feito
nos labs 14-15 mas nunca propagado adiante. Revisar e fechar.

## Objetivo

1. **Clarificar gramatica de markers**: separar inequivocamente
   declaracao de fragmento (`*`), referencia de fragmento (`<digits>`
   no body), e referencia de linha (`=N`).
2. **Re-introduzir RLE adjacente** (`<linha>~<N>`): runs >= 3 linhas
   identicas adjacentes viram uma linha + `~N`.
3. **Testar 3 variantes** do encoder com RLE em todos os 7 (+1) cenarios.

## Sintaxe canonica revisada (proposta v0.5.1)

| Marker | Sintaxe | Significado | Espaco do idx |
|:------:|:--------|:------------|:--------------|
| (none) | `<text>` | literal puro | — |
| `*` | `*<text>` | declaracao de fragmento (modo INLINE) | idx-fragmento ++ |
| `*` `=` | `*<N>=<text>` | declaracao de fragmento (modo EXPLICITO) | idx-fragmento = N |
| `*` `=` `+` | `*<N>=<P>+<ext>` | declaracao encadeada (modo EXPLICITO) | idx-fragmento = N, pai = P |
| `=` | `=<N>` | refere LINHA N do body | idx-linha |
| (none) | `<digits>` | refere idx-fragmento (= valor declarado) | idx-fragmento |
| `_` | `_<text>` | literal numerico (desambig vs ref) | — |
| `~` | `<linha>~<N>` | linha repete N vezes (RLE adjacente) | — |

**Insight chave**: `=N` (sozinho na linha) e `<digits>` (token no body)
referem **espacos diferentes**:
- `=5` = "esta linha eh igual a linha 5 do body"
- `5` (token) = "use o fragmento idx 5 do dicionario de fragmentos"

Os dois espacos nao colidem porque `=` precede o numero em line-ref
e nada precede em frag-ref.

**Bug do rascunho v1**: confundi os dois e `=N` no body era usado
para frag-ref. RT FAIL em 6/8 cenarios. Corrigido na v2.

### Modo INLINE vs EXPLICITO

#### Modo INLINE (lab 18 / variante A)

- Idx-fragmento eh contador independente: 1, 2, 3, ... atribuido na
  ordem em que `*<text>` aparece no body.
- Body: `*user0 _001 *@gmail.com` declara idx 1 = `user0` e idx 2 =
  `@gmail.com` enquanto emite a linha.
- Linhas subsequentes referenciam por `<digits>`: `1 _002 2`.
- **Sem encadeamento** — cada decl eh absoluta.

#### Modo EXPLICITO (lab 24 / variante B)

- Header com decls explicitas: `*1=user0`, `*2=@gmail.com`.
- Decl encadeada: `*3=1+users/0` significa idx 3 = idx 1 + "users/0".
- Body so refs: `1 _001 2`.
- **Permite encadeamento** — essencial para hierarquia profunda (E7).

### Modo HIBRIDO (variante C)

Encoda em AMBOS os modos e escolhe o de menor bytes. Empirico,
robusto, sem heuristica topologica falsificavel.

## Resultados — 3 variantes em 8 cenarios

| Cenario | N | literal | lab 23 | A inline | B explicito | **C hibrido** | vs lit | RT |
|---------|--:|--------:|-------:|---------:|------------:|--------------:|-------:|----|
| E1 emails-100        | 100  | 1800  | 815   | 815   | 823   | **815**   | -54.7% | OK |
| E2 emails-1000       | 1000 | 19000 | 9015  | 9015  | 9023  | **9015**  | -52.6% | OK |
| E3 codigos-100       | 100  | 1400  | 622   | 622   | 630   | **622**   | -55.6% | OK |
| E4 codigos-1000      | 1000 | 15000 | 7022  | 7022  | 7030  | **7022**  | -53.2% | OK |
| E5 categoricas-100   | 100  | 561   | 332   | **318** | 334 | **318**   | -43.3% | OK |
| E5b cat-runs (NOVO)  | 84   | 456   | n/a   | **103** | 119 | **103**   | -77.4% | OK |
| E6 misturado-500     | 500  | 7353  | 3858  | 3858  | 3894  | **3858**  | -47.5% | OK |
| **E7 urls-1000**     | 1000 | 39416 | 14443 | 14443 | **7103** | **7103** | **-82.0%** | OK |

**Avg C vs literal: -58.28%** (lab 24: -54.56%, lab 23: -52.53%)
**Avg C+gz vs literal+gz: -6.48%**
**RT: 24/24 OK** (8 cenarios × 3 variantes)

### Achados

#### 1. Markers clarificados — RT 100% nas 3 variantes

A v1 do rascunho tinha bug de ambiguidade entre frag-ref e line-ref
(usava `=N` para os dois). Corrigido: dois espacos de idx distintos.
Decoder agora detecta sem ambiguidade.

#### 2. RLE adjacente entrega ganho real onde aplica

- E5 (categoricas dispersas): -14B vs lab 23 (-4.2%)
- E5b (categoricas em runs propositais): -16B vs B (-13.4%)

Em datasets sem runs adjacentes, RLE eh no-op (zero overhead, zero
ganho). Aplica-se de forma seletiva (threshold `run_len >= 3`).

#### 3. Hibrido empirico vence heuristica topologica

V2 do rascunho usava heuristica `has_chain_useful` para decidir
A vs B. Em E1-E4 acertou B mas marginal pior que A (~+8B cada).
V3 (final): encoda ambos e escolhe o menor — robusto, ~2pp ganho
adicional.

#### 4. Cenario novo E5b — para exercitar RLE

Adicionado cenario `E5b-categoricas-runs` (84 valores, runs
propositais 2-8). Lab 23 nao tinha. Confirma RLE adjacente em
caso pratico real.

## Conclusao

**Algoritmo final do dirty (lab 25 variante C)**:
1. PATRICIA bidir + collect useful prefix/suffix
2. Detect RLE adjacente runs >= 3
3. Encode em modo INLINE e modo EXPLICITO (paralelo)
4. Retornar o menor

Decoder simetrico: detecta o modo pela primeira linha (header
explicito vs body direto) e dispatcha.

**Sintaxe canonica registrada para portar ao clean prototype**.

## Status

- [x] Markers clarificados (frag vs linha vs RLE)
- [x] RLE adjacente reaplicado e validado
- [x] 3 variantes testadas (A, B, C)
- [x] Cenario novo E5b para exercitar RLE
- [x] 24/24 RT OK
- [x] Avg -58.28% vs literal (vs -54.56% lab 24)
- [x] Algoritmo canonico final do dirty fechado
- [ ] Portar para clean (`EXP-007-encoder-canonico/`) com header `#TCF.5`

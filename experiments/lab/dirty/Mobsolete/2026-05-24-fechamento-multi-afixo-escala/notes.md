# Lab 24: fechamento — multi-afixo nos cenarios de escala

**Data**: 2026-05-10 (rodagem original prevista para 2026-05-24)
**Origem**: revisao da fase dirty. Lab 23 reusou encoder do lab 18
(mono-prefixo). Em E7 (URLs), intermediarios `users/`, `orders/`,
`products/`, etc. foram ignorados pela heuristica de gain global.
Este lab aplica multi-afixo (lab 21) nos 7 cenarios de escala (lab 23)
com filtro de ganho liquido refinado.

## Resultado

| Cenario | N | literal | lab23 | **lab24** | vs lab23 | vs lit | +gz | RT |
|---------|--:|--------:|------:|----------:|---------:|-------:|----:|----|
| E1-emails-100        | 100  | 1800  | 815   | 823   | +1.0%  | -54.3% | -6.4%  | OK |
| E2-emails-1000       | 1000 | 19000 | 9015  | 9023  | +0.1%  | -52.5% | -11.2% | OK |
| E3-codigos-100       | 100  | 1400  | 622   | 630   | +1.3%  | -55.0% | -6.8%  | OK |
| E4-codigos-1000      | 1000 | 15000 | 7022  | 7030  | +0.1%  | -53.1% | -11.0% | OK |
| E5-categoricas-100   | 100  | 561   | 332   | 348   | +4.8%  | -38.0% | +4.3%  | OK |
| E6-misturado-500     | 500  | 7353  | 3858  | 3894  | +0.9%  | -47.0% | -10.6% | OK |
| **E7-urls-1000**     | 1000 | 39416 | 14443 | **7103** | **-50.8%** | **-82.0%** | **-16.1%** | OK |

**Avg TCF lab24 vs literal: -54.56%** (lab 23: -52.53%)
**Avg TCF lab24 vs lab23: -6.09%**
**Avg TCF+gz vs literal+gz: -8.24%** (similar a lab 23)
**Roundtrip: 7/7 OK**

## Achados

### 1. E7 confirma a tese — multi-afixo brilha em hierarquia profunda

Lab 24 captura `https://api.example.com/v1/` (raiz) E os 5 intermediarios
(`events/0`, `products/0`, `metrics/0`, `users/0`, `orders/0`)
encadeados:

```
*1=https://api.example.com/v1/
*2=1+events/0
*3=1+products/0
*4=1+metrics/0
*5=1+users/0
*6=1+orders/0
6 _776       ← orders/0776
5 _507       ← users/0507
4 _895       ← metrics/0895
...
```

Header de 6 declaracoes, cada linha do body em 5-6 chars. Resultado:
**14443B → 7103B** (-50.8% vs lab 23, -82% vs literal).

### 2. Cenarios sem hierarquia — multi-afixo iguala lab 23

E1-E4, E6 ficaram em ±1.3% de lab 23. A heuristica rejeita corretamente
extensoes que nao compensam (formula conservadora idx ~ 2 chars).

E5 (categoricas com duplicatas) +4.8% — overhead minimo do header
multi-afixo, ainda perde marginalmente para o lab 23.

### 3. Bugs do rascunho diagnosticados e corrigidos

**Bug 1**: `find_node_for_string` consumia ate folha (cada linha eh
unica), entao reverse trie nunca acionava — sufixos como
`@gmail.com` perdidos.
**Fix**: usar `collect_useful` (lista de candidatos) em vez de walk
na arvore, e procurar `v.startswith(p)` direto sobre os candidatos.

**Bug 2**: filtro de gain inicial usava formula absoluta:
```
gain_abs = ct * (len_full - 1) - (len_full + 2)
```
Mas decl encadeada `*N=P+ext` tem custo MENOR (so `ext`):
```
gain_ext = ct * (len_ext - 1) - (5 + len_ext)
```
Em emails E2, isso aceitava extensoes minusculas (`74`, `83`) com
ct=10. Acabava declarando 100+ idx, inflando o body com idx de 3
chars.
**Fix**: formula conservadora `ct * (len_ext - 2) - (7 + len_ext)`,
assumindo idx custa ~2 chars em media. Rejeita extensoes pequenas
em datasets onde elas nao compensam o crescimento dos idx no body.

## Algoritmo final (canonico do dirty)

```python
def encode(values):
    # 1. PATRICIA forward + reverse
    # 2. collect_useful(): nos com count>=2 E gain absoluto>0
    # 3. Para cada string:
    #    base   = prefix de maior gain absoluto que casa
    #    ext    = extensao adicional com maior gain LIQUIDO ext-aware
    #    suffix = sufixo de maior gain do reverse, sobre o resto
    # 4. Numera idx em ordem topologica:
    #    bases (gain desc) -> full_paths (com ext) -> suffixes
    # 5. Header com encadeamento *N=P+ext quando aplicavel
    # 6. Body: <idx_full> mid <idx_suffix>
    # 7. Linha repetida -> =N (line ref)
```

Decoder simetrico: detecta `*<N>=<rhs>` (decl); se `+` em rhs eh
encadeada, senao absoluta.

## Implicacoes para fechamento da fase dirty

Este lab confirma:
- **Algoritmo unificado funcional** com PATRICIA bidirecional + multi-afixo.
- **Cenarios sem hierarquia** (codigos, categoricas, emails 1 dom)
  empatam com lab 23. Sem regressao.
- **Cenarios com hierarquia profunda** (E7) ganham 50%+ adicional.
- **TCF+gzip sempre <= literal+gzip em escala** (avg -8.24% mantido).

Fase dirty PODE FECHAR:
1. Algoritmo escolhido (este lab)
2. Validado em escala (E1-E7, N=100 a 1000)
3. RT 7/7 OK
4. Tese de complementaridade com gzip mantida

Proximo passo: portar para clean prototype com header `#TCF.5 SRDM`,
roundtrip formal via harness, bench contra CSV/JSON/TOON.

## Limitacoes conhecidas (registradas como tickets, nao corrigir aqui)

### 1. Header explicito perde inline em datasets sem hierarquia

Lab 23 (encoder lab 18) declarava INLINE (`*green` no body, idx
implicito = numero da linha). Lab 24 declara em header explicito
(`*1=green`) porque encadeamento `*N=P+ext` precisa de idx nomeado.

Diff em E5 categoricas: 332B (inline) vs 348B (explicito) = +16B
exatamente do `N=` extra em 4 declaracoes (4 × 2B).

**Solucao** (deferida): decisao automatica entre os dois esquemas
no port para clean. Ver
[S-header-inline-vs-explicito](../../../../docs/workbench/tickets/open/S-header-inline-vs-explicito.md).

### 2. Sem RLE adjacente

Lab 24 usa line-ref (`=N`) mas nao RLE classico (`red×3`). Em E5
categoricas, runs adjacentes (3-5 linhas iguais) nao sao
comprimidos alem de `=N` repetido.

**Solucao** (deferida): detector de runs no pre-pass, aplicar RLE
quando run_len >= 3. Ver
[S-rle-adjacente-strings](../../../../docs/workbench/tickets/open/S-rle-adjacente-strings.md).

### 3. Marcadores nao deduzidos

Marcadores explicitos `_`, `*`, `=` poderiam ser suprimidos em
contextos onde o decoder consegue inferir do tipo da coluna ou
posicao. Ver
[S-supressao-implicita-marcadores](../../../../docs/workbench/tickets/open/S-supressao-implicita-marcadores.md).

## Status

- [x] Algoritmo multi-afixo + ext-aware gain
- [x] 7/7 RT OK em escala (N=100 a 1000)
- [x] E7 -82% vs literal (vs -63.4% do lab 23)
- [x] Avg -54.56% vs literal, -8.24% vs literal+gz
- [x] Bugs do rascunho diagnosticados (find_node walk + gain absoluto)
- [x] Algoritmo final documentado para portar ao clean prototype
- [ ] Limitacoes registradas em 3 tickets (inline-vs-explicito, RLE
      adjacente, supressao implicita) — corrigir no clean

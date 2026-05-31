# Macro M4 — Desfragmentacao da arvore

**Estado**: parcialmente fechado (M4.A, C1, C1' concluidos)
**Aberto em**: 2026-05-13
**Predecessores**: M1, M2 (fechados), M3 (mapeado sem ganho)
**Hipotese-motor**: responsabilidade da compressao na arvore, nao
em pos-otimizacao.

---

## Estado por micro (era / foi / e' / sera)

| Micro | Estado | Tecnica | Resultado | Ativo? |
|---|---|---|---|---|
| **M4.A** | **foi** (fechado) | Instrumentacao da arvore (mede oportunidades sem mexer) | Mapeou limites teoricos: 17B realocacao densa, 114B intermediario implicito. Inline marginal (1B). | manter como referencia |
| **M4.C1 v1** | **foi** (fechado) | Batch greedy com idx implicito, runs INTEIRAS | -10B vs M1.E (== M2.A). Limitacao: nao captura subsequencias internas. | manter como validacao (= M2.A por caminho diferente) |
| **M4.C1'** | **e'** (atual lider) | Batch greedy + subsequencias contiguas internas | **-40B vs M1.E (-5.9%)**. Captura ~35% do limite teorico do M4.A. | **mantem ativo** |
| M4.B | **sera** (nao implementado) | Realocacao densa + inline (sem mexer arvore) | Limite teorico 18B (vai abaixo do M4.C1') | descartado — M4.C1' supera |
| M4.C2 | **sera** (adiado) | Online com janela deslizante | Nao testado | adiar para protótipo (caso real de streaming) |
| M4.C3 | **sera** (adiado) | Online com refragmentacao | Nao testado | adiar para protótipo (complexidade alta) |

## Resultado canonico do M4

```
M1.E baseline:    676 bytes
M4.C1 v1:         666 bytes (-10, -1.5%)
M4.C1' atual:     636 bytes (-40, -5.9%)  ← lider
```

Limite teorico (M4.A intermediario implicito): 114B. Restam ~74B em
conflitos greedy que ILP resolveria — fora do escopo dirty.

## Camadas de redundancia mapeadas (consolidado do dirty)

| Camada | Mecanismo | Macro vencedor |
|---|---|---|
| 1 — local (dentro da linha) | escape escopo, range | M1.E |
| 2 — entre linhas (sufixos de runs) | alias com preambulo | M2.A |
| 3 — declaracao de no fonte | substring textual | M3 (mapeado, sem ganho) |
| 4 — subsequencias de runs (com idx implicito) | greedy iterativo + marker `~`/`&` | **M4.C1'** |

M2.A e M4.C1' atacam padroes DIFERENTES (sufixos completos vs
subsequencias internas). Possivelmente ortogonais — combinacao
testada como proximo passo do dirty.

## Notas registradas em M4

| Nota | Estado | Conteudo |
|---|---|---|
| [`buffer-e-refragmentacao.md`](notas/buffer-e-refragmentacao.md) | foi | analise D4, estrategias de buffer (online/medio/batch/hibrido), conceito "gasta processamento pra refragmentar" |
| [`indice-incremental-de-padroes.md`](notas/indice-incremental-de-padroes.md) | sera | abstracao de armazenamento+indexacao tipo Patricia generalizada — aplicar em M4.C2/C3 e protótipo |
| [`arvore-da-arvore-vs-regex.md`](notas/arvore-da-arvore-vs-regex.md) | foi (orientou M4.C1') | tese "ramos diferentes nao se enxergam"; comparacao com regex (padrao + medida + balanceamento) |
| [`conclusoes_M4_C1.md`](notas/conclusoes_M4_C1.md) | foi | analise consolidada M4.C1 v1 + M4.C1' |
| [`../../notas/comparacao-modular-camadas.md`](../../notas/comparacao-modular-camadas.md) | sera (transversal) | comparacao como parametro modular; nome formal TCF-CORE/OAS |
| [`../../notas/quebra-de-linha-como-marcador.md`](../../notas/quebra-de-linha-como-marcador.md) | sera (transversal) | quebras como marcadores opcionais |

## O que **NAO** vamos fazer dentro de M4 (registrado e fechado)

1. **M4.B (idx por demanda + inline)** — limite teorico 18B vai
   abaixo do M4.C1' (40B ja' obtido). Marginal e ortogonal.
   Descartado.
2. **M4.C2 (online)** — risco de complexidade vs ganho duvidoso.
   Cabe melhor no protótipo (streaming e' caso real).
3. **M4.C3 (refragmentacao)** — complexidade alta. Protótipo.
4. **Slice central REAL** (estender alg16) — fora do escopo M4.
   Pode virar macro futuro se valer.

## Estrutura

```
2026-05-13-M4-desfragmentacao-arvore/
  README.md                              (este — Index com estado)
  online.py                              raiz (TCF-CORE / OAS)
  syntax_base.py
  data/                                  D1-D4 canonicos
  data_extra/
    DE7-hierarquia-profunda.csv          (do M3, reusado)

  M1-E-range-baseline/                   foi (baseline)
  M4-A-instrumentacao/                   foi (script de medicao)
  M4-C1-batch-greedy-implicito/          foi (runs inteiras)
  M4-C1p-batch-subsequencias/            e' (atual)

  notas/                                 4 notas
  resultados/                            matriz consolidada
  run_lote.py
  run_lote_extra.py
```

## Proximo passo do dirty (apos M4)

**Combinar M2.A + M4.C1' em uma pilha** e' o experimento residual
do dirty antes do protótipo. Se ganho aditivo:
- ortogonalidade confirmada
- ambos vao pro protótipo

Se ganho nao-aditivo:
- competem pelo mesmo regime
- escolher um (M4.C1' provavelmente)

Apos esse experimento, dirty fecha e migra pro protótipo com:
- **TCF-CORE** (alg16 intocado)
- Sintaxe core: M1.E + M4.C1' [+ M2.A se aditivo]
- Camada de pre-tx (delta, estrutural) como plugin opcional

## Como rodar

```bash
cd 2026-05-13-M4-desfragmentacao-arvore
python run_lote.py          # canonicos
python run_lote_extra.py    # DE7 (compartilhado com M3)
```

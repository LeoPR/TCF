# Conclusoes M4.A — Instrumentacao da arvore

## Numeros consolidados

| Dataset | Frags | Usados 2+ | Usados 1x | Nao-ref | Inline (B) | Realoc densa (B) | Intermed impl (B) | Intermed expl (B) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D1 | 12 | 12 | 0 | 0 | 0 | 2 | 56 | 0 |
| D2 | 18 | 9 | 5 | 4 | 0 | 1 | 16 | 0 |
| D3 | 15 | 10 | 5 | (?) | 0 | 6 | 22 | 0 |
| D4 | 14 | 8 | 2 | 4 | 1 | 8 | 20 | 0 |
| **TOTAL** | 59 | 39 | 12 | — | **1** | **17** | **114** | **0** |

Baseline: M1.E = 676 bytes nos canonicos.

## Achados objetivos

### 1. Inline de frags 1x: marginal

Apenas 1 byte total (D4). Maior parte dos frags 1x tem texto maior
que o idx (>1 char), entao inline NAO compensa.

Conclusao: **inline isoladamente nao justifica implementacao**.

### 2. Realocacao densa: pequena mas existente

17 bytes total (~2.5% sobre 676). Distribuida desigualmente:
D4 (-8), D3 (-6), D1 (-2), D2 (-1).

Mecanismo: M1.E aloca idx sequencialmente conforme aparece. Idx
1-9 vao pros 9 primeiros frags. Mas alguns desses primeiros frags
sao usados POUCAS vezes, enquanto frags 10+ sao usados MUITO.
Realocar por frequencia leva idx baixos pros mais usados.

Exemplo D4: idx 10-99 tem 5 frags (2 chars cada); se realocados,
alguns viram 1-9 (1 char). Cada uso desses economiza 1 byte.

Conclusao: **realocacao densa vale implementar** (ganho modesto
mas garantido).

### 3. Nao-referenciados: estrutura curiosa

D2 tem 4 frags **alocados mas nunca referenciados** (criados pelo
no fonte quando quebras foram propagadas, mas nenhum descendente
usa). Idem D4 (4 frags). Sao "fragmentacao desnecessaria" da
arvore.

Causa: alg16 fragmenta no fonte por TODAS as quebras propagadas
de descendentes. Mas se um descendente nao USA o frag especifico
(usa range vizinho), o frag e' criado a toa.

Conclusao: **alg16 fragmenta a mais. Custo pequeno (so' aumenta
idx subsequentes 1 unidade) mas existe.**

### 4. No intermediario implicito: 114 bytes potenciais (17%)

Limite teorico se substrings compartilhadas (eid_origem, P|S, len)
com R>=2 virassem refs implicitos (decoder cria idx ao ver).

Distribuicao:
- D1: 56B (familia compartilha "joao@", "maria@", etc.)
- D3: 22B (URLs compartilham paths)
- D4: 20B (mesmo @-foo-bar)
- D2: 16B

**Mas e' limite SUPERIOR** — varios candidatos competem (sufixo
e prefixo se sobrepoem ao mesmo eid). Implementacao real captura
fracao.

### 5. No intermediario explicito: 0 bytes

Confirma M3: declaracao explicita custa mais que o ganho. Idx
implicito e' a chave.

## Diagnostico estrutural

O conceito do user de **idx por demanda** (frag s/ ganho nao
recebe idx) tem mais dimensoes do que pensei:

| Dimensao | Mecanismo | Ganho potencial |
|---|---|---|
| (a) Inline frags 1x onde texto < idx | sem mexer arvore | 1B (marginal) |
| (b) Realocar idx por frequencia | sem mexer arvore | 17B (pequeno) |
| (c) Evitar fragmentacao a toa (no-ref) | mexer alg16 | nao medido |
| (d) Idx implicito p/ substrings compartilhadas | mexer arvore | ate' 114B (significativo) |
| (e) Declaracao explicita estilo M3 | sem mexer arvore | 0B (confirmado) |

(a)+(b) sao ortogonais e nao tocam alg16 — somam ~18B garantidos.
(c) requer mexer alg16, ganho nao quantificado.
(d) e' o grande potencial mas mais arriscado.
(e) confirmado nao-viavel.

## Plano refinado para M4.B e M4.C

### M4.B — Realocacao + inline (sem mexer arvore)

Ganho teorico: 18B (~2.7%). Implementacao simples — apenas reordenar
alocacao de idx e omitir idx de frags 1x quando vale.

Decisor: para cada frag, escolhe entre idx (1-9 ou 10+) e inline
(texto direto). Idx por frequencia decrescente.

Risco baixo. Conclusao propria garantida (mesmo que pequena).

### M4.C — Idx implicito (substring compartilhada)

Ganho teorico: 114B (~17%) — limite superior. Implementacao mais
complexa: decoder precisa rastrear sub-runs e criar idx automatico.

Risco maior. Mas potencial significativo.

## Insight para M4.B

Realocacao densa funciona porque ALG16 ALOCA POR ORDEM DE APARICAO,
NAO POR USO. Os 9 idx baratos (1 char) vao pros primeiros frags
alocados, que nao sao necessariamente os mais usados.

Em D4: idx 1-9 tem frags de eid 1 (apenas 5 sao usados em outros).
Frags mais usados (refs ao eid 1 que sao prefix de v2 famílias)
podem estar em idx 10+. Realocar resolve.

## Decisao

Seguir com **M4.B (realocacao densa + inline opcional)** primeiro.
Ganho modesto mas garante implementacao funcional sem mexer alg16.

Depois M4.C (idx implicito) — onde esta o potencial real (114B).

Se M4.C for muito complexo, fica registrado como pendencia e
voltamos para pos-otimizacao tipo M2.

## Limitacoes M4.A

- Limites teoricos ignoram conflitos entre tecnicas
- Datasets pequenos (12 strings) — em escala maior, R cresce e
  intermediarios ganham mais
- Realocacao densa depende de distribuicao de usos — pode ser
  diferente em datasets reais
- Nao medi efeito da fragmentacao a toa (no-referenciados) sobre
  bytes finais

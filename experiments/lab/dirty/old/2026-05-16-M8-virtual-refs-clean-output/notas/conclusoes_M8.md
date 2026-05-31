# Conclusoes M8 — Detector unificado + convencao output

**Data**: 2026-05-16
**Vem de**: critica do user (2026-05-15) sobre M7:
1. Pair (15, 16) em D3 nao detectado — algoritmo precisa generalizar.
2. Brackets `[`/`]` no output e CRLF eram scaffolding, nao TCF
   oficial — embutir convencao para nao esquecer.

## Resultado (apos refinamento da restricao 2026-05-16 segunda rodada)

| Sintaxe | D1 | D2 | D3 | D4 | Total |
|---|---:|---:|---:|---:|---:|
| M1.E-clean | 145 | 176 | 202 | 137 | 660 |
| M7.A-clean | 124 | 171 | 190 | 118 | 603 |
| **M8.A** | **118** | **166** | **177** | **113** | **574** |

RT 16/16 OK. M8.A **-29 bytes vs M7.A-clean**. Vs M6.C original (619
com brackets): -45 bytes (-7.3%; **-13.0% acumulado vs M1.E ate' aqui**).

Primeira rodada (restricao estrita "virtual em pos 0"): 584 bytes.
Segunda rodada (restricao refinada, abaixo): **574 bytes** (-10
adicional).

Decomposicao do ganho vs M6.C:
- **16 bytes** dos brackets `[`/`]` removidos (4/dataset).
- **19 bytes** do detector unificado.

## Refactor algoritmico — detector unificado

### Antes (M7.A)

Pieces tinham 3 tipos:
- `('lit', text, atom_id)`
- `('refs', [atom_ids])`
- `('alias_marker', alias_temp, sub_prov)` — separado, opaco ao detector

Detector iterava SO' em `'refs'` pieces. Pairs (atom, alias_anterior)
ou (alias, alias) ficavam invisiveis. Em D3: pair (15, 16) =
(comp_15, atom_16) nunca consideravel.

### Depois (M8.A)

Pieces simplificados:
- `('lit', text, atom_id)`
- `('refs', [ref_ids])` — onde `ref_id > 0` = atom prov, `ref_id < 0` = virtual alias

Apos detector substituir K refs por -alias_temp, o virtual ID
participa naturalmente em sub-tuplas das iters seguintes. Sem fase
'alias_marker' separada.

### Emit: inline expansion + restricao pairwise

Pairwise left-assoc (decoder rule) corrompe valor de inner alias se
nao esta em position 0 da chain do outer. Exemplo:
- linear = [M, P, Q, X]; pairwise allocates 3 IDs:
  - ID 1 = M+P
  - ID 2 = (M+P)+Q
  - ID 3 = ((M+P)+Q)+X
- Inner alias Y = (P, Q) completaria em ID 2. Mas ID 2 = M+P+Q, NAO P+Q.

Solucao: **detector filtra candidatos**. Sub-tupla aceita se:
- 0 virtuais (todo atomico), OU
- 1 virtual EM POSITION 0 (resto atomico).

Sub-tupla com virtual em meio/fim, ou 2+ virtuais: rejeitada.

Com restricao, inline expansion funciona corretamente:
- Inner alias (em position 0) ocupa o INICIO da chain.
- Pairwise pa primeira parte da chain = inner alias's value exato.
- Inner alias's final id = base + index_of_inner_last_elem.

### Capturas algoritmicas

D1 ganho 6 bytes:
- Antes: alias 3 = (3, 4, 5) detectada. alias_3 sub linhas 2-4 [..., 6]
  ficavam como `,10,6` (2 chars + sep) ou similar.
- Depois: detector ve o pair (alias_3_virtual, 6) na MESMA iter. Pick
  uma alias maior (3, 4, 5, 6) = comp K=4. Linhas 3, 4 viraram `,11`
  (uso direto da nova alias) em vez de `,10,6`.

D3 ganho 13 bytes:
- Pair (15, 16) e similares capturados via composicoes mais amplas.
- Detector itera com refs mixtos, decide compoes maiores quando vale.

D2/D4 sem ganho extra:
- Os pares missed nao tinham R alto suficiente OU o detector ja'
  pegava equivalente em M7.A.

## Convencao output

Adotada em M8 e futuro (ver
[`../../notas/convencao-output-tcf.md`](../../notas/convencao-output-tcf.md)):

1. **Sem brackets** `[`/`]` no encode. Decoder mantem skip para
   back-compat com M5/M6/M7.
2. **LF only** (`\n`). `run_lote.py` usa `write_bytes(content.encode())`
   para evitar CRLF do Windows text-mode.

Validado em disco: D3 = 177 bytes, 12 LF, 0 CRLF.

## Refinamento da restricao (segunda rodada 2026-05-16)

Apos rodada 1, user notou que pairs como (10, 7) em D4 (lines 5, 6)
e (10, 18) em D4 (lines 9, 10) ainda nao detectados. Restricao
"virtual em pos 0 only" era estrita demais.

### Diagnostico

Pair (10, 7) em body = `(atom_8, alias_2)` em provisional (alias_2 =
(2,3,4) substituida em iter 2). Virtual em pos 1.

Mas alias_2 tem **standalone occurrence em lines 2, 3, 4** ANTES da
sub (8, -2) first match (line 5). Body order: 2 < 5. Quando emit
chegar em line 5, alias_2 ja' tem final_id atribuido (de line 2).

Inline expansion em emit pega `state['alias_to_final'][inner]` direto
— SEM corrupcao.

### Restricao refinada

Allow sub-tupla com virtual em pos > 0 SE:
- `alias_first_line[virt_alias] < sub_first_line[sub]`

Onde:
- `alias_first_line[X]`: primeiro li onde -X aparece em body
- `sub_first_line[sub]`: primeiro li onde sub matches em body

Implementacao no detector:

```python
if virt_pos > 0:
    virt_alias = -sub[virt_pos]
    if alias_first_line.get(virt_alias, inf) >= sub_first_line[sub]:
        continue  # virt nao resolvida antes; rejeitar
```

### Capturas adicionais

- D4 iter 3: `(8, a2)` → captura pair (10, 7). -5 bytes.
- D4 iter 5: `(8, a1)` → captura pair (10, 18). (incluido em -5 total)
- D2 ganho similar: -5 bytes.

Rejeicoes corretas:
- D4 candidate `(1, -1)`: -1 first em line 8, sub (1, -1) tambem
  primeiro em line 8 → REJEITADO (correto; inline corromperia alias_1).

## Limitacoes restantes

### Case `2~13` reuse (apontado pelo user)

D4 line 8 emit `1,2~14~15~4,8` (alias_1 = (2,11,12,4) prov). O
INTERMEDIARIO do chain (= prov (2, 11)) tem valor "]*'ba" mas nao
ganha alias separada.

Line 11 emit `1,2~14z16` — onde `2~14` e' alias_4 = (2, 11) prov
nova alias. Valor "]*'ba" e' computado SEGUNDO ID — duplicacao.

Para capturar: detector teria que **decompor** alias_1 em
(alias_inner=(2,11), 12, 4) ou similar. Requer pos-passagem que
decompoe aliases largas em menores.

**Direcoes futuras**:
- Decomposicao pos-detector: identifica aliases grandes que contem
  pairs reusados em outros lugares. Decompor para nested alias.
- Detector global (nao greedy) com priorizacao "smaller first" pra
  expor intermediarios.
- Multiplos virtuais via right-assoc binarization.

## Conexoes

- [[../../notas/convencao-output-tcf.md]] — convencao output
- [[../../2026-05-15-M7-refactor/notas/conclusoes_M7.md]] — refactor
- [[../../2026-05-14-M6-sintaxe-composicional/notas/conclusoes_M6.md]] — base composicional

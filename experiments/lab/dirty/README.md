# dirty/ — workbench sujo

Pasta livre para experimentos em andamento, esboços, exploracoes do
algoritmo de compressao TCF. **Esta pasta nao faz parte do TCF**
(formato publicado) — eh laboratorio de pesquisa.

## Regras

1. **Sem cerimonia**: qualquer estrutura de subpasta serve
2. **Nomeacao**: `<YYYY-MM-DD>-<tema-curto>/` recomendado
3. **Nao referenciar em paper, ticket fechado ou finding**
4. **Pode ser deletado a qualquer momento** (mas a estrutura deste
   README serve como rastreio historico minimo)

## Quando promover para clean/

Quando um experimento sujo:
- Producir resultado reproduzivel
- Tiver pergunta cientifica clara
- Justificar lugar permanente

Mover para `clean/EXP-NNN-<tema>/` com estrutura padrao.

---

## Mapa cronologico — fases e labs

A exploracao dirty ocorreu em **3 fases** entre 2026-05-07 e
2026-05-10. Cada fase tem proposito distinto e resulta em decisoes
ou hipoteses validadas.

### Fase A — design v0.4 (2026-05-07 a 2026-05-09)

Mesas de design: explorar tipos de compressao, formato do header,
combinatorias. Sem encoder ainda — racicocinio + esboco em texto.
Sem `notes.md` formal (os arquivos da epoca eram mesa de trabalho).

| Lab | Tema |
|-----|------|
| 2026-05-07-combinatoria-simples | Combinatorias de marcadores e separadores |
| 2026-05-07-hipoteses-transporte | Hipoteses sobre layer de transport (depois descartado) |
| 2026-05-07-mesa-compressao-maxima | Limite teorico de compressao |
| 2026-05-08-indices-alfabeto | Eixo 2 (representacao): a-z, base32, base64 — deferido |
| 2026-05-08-multisort-e-cabecalho | Multi-sort, header design |
| 2026-05-08-rle-dict-unificado | Tese: RLE+DICT como mesma operacao |
| 2026-05-08-sintese-formato | Sintese das mesas anteriores |
| 2026-05-08-tipos-restantes-v05 | Tipos: data, tempo, fracao |
| 2026-05-09-delta-datas | Delta encoding para datas |
| 2026-05-09-gramatica-densidade | Densidade gramatical maxima |
| 2026-05-09-tempo-fracoes | Tempo e fracoes especificas |

**Outputs da fase A** (consolidados em
`docs/workbench/PROGRESSO-formato-v05-2026-05-09.md`):
- 18 decisoes locked-in (column-major, regra unificada, sort header,
  alfabeto adaptativo, delta, packing, inline, shorthand)
- 6 decisoes deferidas (representacao de idx, prefix elision, line-RLE,
  count-recycling, multi-scale time, delta-validation)
- Default proposto: `flags=SRDMA` (-54% vs CSV)

### Fase B — DICT maleavel + PATRICIA (2026-05-10 a 2026-05-19)

Exploracao do **algoritmo de compressao de strings**. Cada lab tem
`notes.md` com resultado e RT.

| Lab | Tema | Achado principal |
|-----|------|------------------|
| 2026-05-10-numeros-compressao | Numeros (delta, packing) | Delta + alfabeto base32 |
| 2026-05-11-affix-implicit-bidir | Affix prefix+suffix implicito | 6 cenarios, avg -0.07% — ainda fraco |
| 2026-05-12-affix-trie | Trie de prefixos compartilhados | 4/6 ganham, 2/6 perdem — heuristica falha |
| 2026-05-13-motor-variavel | Motor parametrizado (7 vars, 16 configs) | Tese **1 funcao = N tecnicas** validada |
| 2026-05-14-rle-dict-combinado | RLE-linhas + DICT-partes (4 sintaxes) | -44.6% bidir; 3 layers ortogonais |
| 2026-05-15-marcador-deducao | Marcadores implicitos por frequencia | Cobertura 100% dificil — bug em alguns casos |
| 2026-05-16-multi-index-direcao-implicita | Multi-idx + direcao deduzida | Gramatica auto-descritiva |
| 2026-05-17-arvore-patricia | PATRICIA trie (label de string) | Captura hierarquia naturalmente |
| 2026-05-18-patricia-inline-combinado | PATRICIA + emit inline | Sem header verboso, encoder limpo |
| 2026-05-19-patricia-bidir-refinado | Heuristica gain (nao length) + reverse trie | Avg -38.85% vs literal |

**Achados consolidados** em
`docs/workbench/research-notes/2026-05-12-dict-maleavel-unificado.md`
e `2026-05-12-teoria-compressao-strings.md`.

### Fase C — encadeamento + escala + fechamento (2026-05-20 a 2026-05-24)

Refinamentos finais; validacao de escala; fechamento.

| Lab | Tema | Achado |
|-----|------|--------|
| 2026-05-20-hierarquia-profunda | Sintaxe `*N=P+ext` (decl encadeada) | Funcional, 5/5 RT, mas heuristica nao acionou |
| 2026-05-21-multi-afixo | Pre-declaracao topologica + encadeamento ativo | C7 -29% vs lab 20, C9 -61% vs literal |
| 2026-05-22-deducoes | D1/D2/D3 (idx por contagem, alfabeto, omit eq) | Avg -0.62% — **deducoes nao escalam**; D2 tem ambiguidade |
| 2026-05-23-escala | 7 cenarios N=100 a 1000 | **TCF+gz vence literal+gz em escala** (-8.47% avg) |
| **2026-05-24-fechamento-multi-afixo-escala** | Multi-afixo (lab 21) + escala (lab 23) | **E7 -82% vs literal**; algoritmo canonico definido |

**Algoritmo canonico do dirty** (lab 24):
- PATRICIA forward + reverse
- Para cada string: `base` (prefix maior gain) + `ext` (encadeada com
  ganho liquido positivo, ext-aware) + `suffix` (do reverse)
- Header: bases (gain desc) → full_paths (com ext encadeada) → suffixes
- Body: `<idx_full> mid <idx_suffix>`, repetidas via `=N`

---

## Tickets relacionados

### Diretamente derivados destes labs (criados ou atualizados)

- [H-compression-v04-roadmap](../../../docs/workbench/tickets/open/H-compression-v04-roadmap.md) — roadmap v0.4 (3 propostas validadas: E, H, I)
- [S-representacao-de-indice](../../../docs/workbench/tickets/open/S-representacao-de-indice.md) — eixo 2 (alfabeto idx) — deferido
- [S-idx-universal-linha-fragmento](../../../docs/workbench/tickets/open/S-idx-universal-linha-fragmento.md) — unificar namespace `*` + `=` (epifania 2026-05-10)
- [B-homonyms-key-collision](../../../docs/workbench/tickets/open/B-homonyms-key-collision.md) — colisao de key elimination

### Bloqueia / proximos para fase clean

- [T-test-harness-mvp](../../../docs/workbench/tickets/open/T-test-harness-mvp.md) — meta-programa para benchmark formal
- [E-compression-combinations](../../../docs/workbench/tickets/open/E-compression-combinations.md) — bench combinacoes de transformacoes
- [E-format-comparison-bench](../../../docs/workbench/tickets/open/E-format-comparison-bench.md) — TCF vs CSV/JSON/TOON formal
- [E-min-max-scenarios](../../../docs/workbench/tickets/open/E-min-max-scenarios.md) — edge cases (datasets minusculos vs gigantes)

### Bugs conhecidos a fixar antes do clean prototype

- [29-B-decoder-freetext-bug](../../../docs/workbench/tickets/open/29-B-decoder-freetext-bug.md) — decoder confunde texto livre com `:` como header de coluna
- [B-homonyms-key-collision](../../../docs/workbench/tickets/open/B-homonyms-key-collision.md) — eliminacao de PK pode juntar linhas com mesma natural key

### Bugs descobertos durante o dirty (registrados nos notes, nao em ticket)

- **Lab 16 sync bug** (corrigido no proprio lab): encoder/decoder
  divergiam — `update_dict` adicionava literais automaticos, decoder
  so contava decls explicitos. Fixed: ambos so contam `*`.
- **Lab 17 prefix declaration bug** (corrigido): declarava todos
  candidates `count >= 2`, incluindo ancestrais nao usados. Fixed:
  filtra para apenas USED apos pass de selecao.
- **Lab 22 D2 alphabet ambiguity** (deferido): com letras como idx,
  `b` no body pode ser ref ou literal. Decisao registrada: deducoes
  ficam opt-in, nao default.
- **Lab 24 rascunho v1** (corrigido durante o lab): `find_node_for_string`
  consumia ate folha (cada linha eh unica); reverse trie nao acionava.
  Fixed: usar `collect_useful` (lista) em vez de walk na arvore.
- **Lab 24 rascunho v2** (corrigido): formula de gain ext-aware usava
  idx ~1 char; em E2 explodiu a 100+ idx (3 chars). Fixed: formula
  conservadora `ct*(len_ext-2) - (7+len_ext)`.

---

## Status de fechamento da fase dirty

**FECHAMENTO RECOMENDADO** apos lab 24 (2026-05-10).

Criterios atendidos:
- [x] Algoritmo unificado funcional (PATRICIA bidir + multi-afixo)
- [x] 7/7 RT OK em escala (N=100 a 1000)
- [x] -54.56% vs literal medio; E7 -82%
- [x] Tese de complementaridade com gzip (-8% vs literal+gz em escala)
- [x] Bugs do dirty diagnosticados ou deferidos formalmente

Proximo passo: portar lab 24 para
`experiments/lab/clean/EXP-007-...` com:
- Header `#TCF.5 SRDM`
- Roundtrip via test harness
- Bench formal contra CSV/JSON/TOON

---

## Conteudo atual

26 sub-pastas (datas 2026-05-07 a 2026-05-24).

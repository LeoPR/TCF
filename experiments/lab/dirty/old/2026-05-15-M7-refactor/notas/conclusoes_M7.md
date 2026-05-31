# Conclusoes M7 — Refactor + nova estrutura de debug

**Data**: 2026-05-15
**Vem de**: critica do user sobre M5/M6 — remendos inflavam codigo, debug
empilhado dificultava leitura.

## Resultado

| Sintaxe | D1 | D2 | D3 | D4 | Total |
|---|---:|---:|---:|---:|---:|
| M1.E baseline | 149 | 180 | 206 | 141 | 676 |
| M6.C baseline | 128 | 175 | 194 | 122 | 619 |
| **M7.A (refactor)** | **128** | **175** | **194** | **122** | **619** |

**M7.A == M6.C byte-a-byte.** RT 12/12 OK. Refactor preservou comportamento.

## Sobre o refactor de codigo

Linhas de codigo:
- M6.C: 674 linhas (com trace inline)
- M7.A: 636 linhas (com trace + rede)

So' ~5% menos linhas absolutas mas estrutura significativamente melhor:

- **Phase A** (`_tokenize_pieces`): tokeniza alg16 → pieces por linha
- **Phase B** (`_detect_compositions`): greedy iterativo, modifica pieces
- **Phase C** (`_emit_body`): single pass, IDs decoder-style interleaved
- **Builders** (`_build_trace`, `_build_rede`): separados, geram saidas

Vs M6.C que tinha 6 fases (Phase 1, 2-4, 5, 6) com mapping prov→final
acumulado como remendo. M7 unifica Phase 5+6 em Phase C (single pass).

Helpers simplificados:
- `_runs(refs)` extrai runs de consecutivos (compartilhado entre `_emit_refs_range`, `_emit_composition`, `_count_ids_in_refs`).
- `_escape_lit` mais curto.
- `_coletar_quebras` reorganizado.

## Sobre a nova estrutura de debug

Layout:
```
resultados/
  tokens/<dataset>.txt           # alg16 raw (1x por dataset, compartilhado)
  matriz_bytes.csv
  matriz_comparativa.md

<micro>/
  output/<dataset>.tcf           # encode
  decoded/<dataset>.csv          # contra-prova
  debug/<dataset>.txt            # INPUT + TCF + DECODE (sem tokens duplicados)
  detector_trace/<dataset>.txt   # iteracoes do detector (se aplicavel)
  redes/<dataset>.txt            # atomos + composicoes + freq uso
```

Beneficios:
- **tokens/ compartilhado**: alg16 e' deterministico, output identico
  pra cada dataset. Antes era duplicado em cada micro/debug/.
- **detector_trace/ separado**: percurso da otimizacao isolado do
  resultado final. Facil de comparar entre micros.
- **redes/ novo**: snapshot da rede de atomos + composicoes (com
  freq de uso). Ajuda a visualizar a estrutura sem ler TCF.
- **debug/ enxuto**: so' INPUT/TCF/DECODE; sem repetir tokens (lembrar
  que estao em resultados/tokens/).

## Sobre o algoritmo (reanalise)

A semantica do M6.C esta correta. Limitacao conhecida (registrada
em [`../../2026-05-14-M6-sintaxe-composicional/notas/conclusoes_M6.md`](../../2026-05-14-M6-sintaxe-composicional/notas/conclusoes_M6.md)):

**Detector greedy NAO ve alias_markers** apos substituicao. Pairs como
(atom, alias_anterior) ficam invisiveis. Em D1-D4: ~28 bytes adicionais
potenciais.

**Implementacao da visibilidade (virtual refs)** seria significativo:
- Alias_markers viram refs virtuais (id negativo ou em outra faixa)
- Detector itera com refs mixtos atomicos+virtuais
- Emit precisa resolver recursivamente: composicao de composicao com
  pairwise binarization tracking IDs intermediarios

Complexidade alta (~100+ linhas adicionais) pra ganho de ~4-5%.
**Decisao**: NAO no M7. Registrar como direcao M8 ou direto pro
prototipo se valer a pena.

## Exemplo do arquivo redes/

D1-emails-simples:
```
=== ATOMS (final IDs) ===
  final 1: 'joa'  ...  final 22: 'yahoo'  (12 atomos)

=== COMPOSITIONS (final IDs, ordem body) ===
  final 10 = composicao[3, 4, 5]  (emit `3..5`)        # @gmail
  final 14 = composicao[1, 2, 3]  (emit `1..3`)        # joao@
  final 16 = composicao[7, 8]     (emit `7~8`)         # maria
  final 19 = composicao[3, 15, 5, 6] (emit `3~15~5~6`) # @hotmail.com
  ...

=== USO POR REF ===
  ref 6 (.com): 5x  ← muito reusado
  ref 10 (@gmail): 3x
  ref 19 (@hotmail.com): 3x
  ref 24 (@yahoo.com): 3x
```

Visivel:
- 12 atomos + 7 composicoes = rede de 19 nos.
- '.com' (ref 6) tem 5 usos — candidato a virar parte de comp mais ampla.
- Compositions intermediarias (`7~8`, `11~2`, `12~8`) — names de pessoas.

## Pendencias / proximo passo

Dirty fechado (de novo). M7.A e' o canonico atualizado.

**Protótipo**:
- Sintaxe core: M1.E + M7.A composicional (idem M6.C, codigo melhor)
- Pre-tx opcionais: delta, estrutural (ver
  [`../../notas/comparacao-modular-camadas.md`](../../notas/comparacao-modular-camadas.md))

**Direcoes futuras registradas**:
- Virtual refs detector (visibility de aliases nas iters) → ~4-5% adicional
- Nos pos-construcao com literal+ref (ver
  [`../../notas/marcadores-multiplo-proposito.md`](../../notas/marcadores-multiplo-proposito.md))
- Trace/debug expandido para outros aspectos (simplificacao,
  ambiguidade, redundancia) — base estabelecida em M6, extensivel.

## Conexoes

- [[../../2026-05-14-M6-sintaxe-composicional/notas/conclusoes_M6.md]] — M6 estabeleceu composicional
- [[../../notas/marcadores-multiplo-proposito.md]] — analise algebrica
- [[../../notas/vetores-de-comparacao-alem-de-bytes.md]] — vetores nao-byte

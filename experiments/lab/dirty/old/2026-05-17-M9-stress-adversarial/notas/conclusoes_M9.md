# Conclusoes M9 — Stress adversarial M8.A

**Data**: 2026-05-17
**Foco**: testar M8.A em 5 datasets adversariais novos (D5-D9) +
revalidar D1-D4. Identificar limites do algoritmo atual.

## Resultados

RT 9/9 OK.

| Dataset | bytes | raw | ratio | observacao |
|---|---:|---:|---:|---|
| D1 emails-simples | 118 | 191 | 62% | medio |
| D2 emails-quote-id | 166 | 248 | 67% | medio |
| D3 stress-substring | 177 | 348 | 51% | bom |
| D4 caos-mix | 113 | 157 | 72% | **alto caos** — pouca redundancia explorável |
| D5 padroes-multiplos | 281 | 419 | 67% | medio |
| D6 poucos-em-ruido | 287 | 528 | 54% | **timestamps difíceis** (literais escapados) |
| D7 aninhamento | 215 | 335 | 64% | medio |
| **D8 cabeca-cauda** | **100** | **384** | **26%** | **otimo** (prefix/suffix estaveis) |
| D9 frequencia-alta | 158 | 363 | 43% | bom |

Total bytes D1-D9: **1615**. Raw total: **2973**. **Ratio medio: 54.3%**.

## Limites identificados por dataset

### D6 (poucos-em-ruido) — timestamps escape-hell

Linha 1 do TCF emite muitos `\` escapes pra digits da timestamp:
```
log[\2026-\05-\17T\08:*\2*\3:\01.\1*\82*]error[mod=auth]
```

Cada `\X` consome 2 bytes pra emitir um digit literal. Timestamps tem
4+2+2+2+2+2+2+3 = 19 digits. Alg16 nao consegue substring-matchar
porque cada timestamp e' unico.

**Pre-tx delta** (subtrair timestamp base) renderia maioria dos
timestamps como pequenos deltas — drasticamente reduzindo bytes
literais. **Direcao registrada pro protótipo**.

### D9 (frequencia-alta) — variavel entre wrappers

Linhas como `@@@KEY=value-x1@@@`, `@@@KEY=value-x2@@@`. O wrapper
`@@@KEY=value...@@@` repete; o "middle" varia (`x1`, `x2`, ..., `bb`, `cc`).

Algorithm:
- Captura prefix `@@@KEY=value-x` como ref 7 (line 2 def).
- Lines 3-9: `7\N*5` (7 = prefix, \N = digit literal, 5 = suffix).
- 7 chars body por linha — eficiente.

Mas se houvesse PRIMITIVO de "wrapper com slot", poderia ser ainda mais
compacto. Tipo `7{}5` onde `{}` indica slot variavel preenchido
posicionalmente. Ganho hipotetico.

### D4 (caos-mix) — ratio alto (72%)

D4 inclui 12 linhas de 12 padroes distintos `[X]*'YYY'@4Z`. Alta
variabilidade reduz redundancia. Ratio 72% reflete dificuldade real
de compressao quando cada linha e' quase unica.

### D8 (cabeca-cauda) — ratio 26%, prova de eficacia

`common/prefix/XXX/common/suffix` em 12 linhas, so' XXX varia. Algoritmo
captura prefix e suffix como ref 1 e ref 3, emit `1bbb3`, `1ccc3` etc.
5 bytes/linha. Ratio 26%. Comportamento esperado/ideal.

## Pontos de over-patch (revisao critica M8)

Apos refinamento da restricao na sessao anterior, M8.A tem ~736 linhas.
Pontos potencialmente over-patched:

### `_estimate_baseline_chars` (linha ~232)

Estima virtual como "9"*n_est (chars de 9s). Heuristica simples mas
imprecisa para datasets grandes onde ids variam muito. NAO afeta
correcao; afeta priorizacao em ambiguidades de net.

**Verdict**: aceitavel pra dirty (datasets pequenos); refinar pro
protótipo.

### Body-order check (linha ~272)

```python
if alias_first_line.get(virt_alias, inf) >= sub_first_line[sub]:
    continue
```

Adicionada na rodada 2 do M8. Recomputa `alias_first_line` e
`sub_first_line` por iteracao. Custo O(N_lines * N_pieces) por iter.

**Verdict**: necessaria para correcao; nao e' over-patch. Pode ser
otimizada (cache parcial), mas custo absoluto baixo.

### Inline expansion em `_emit_alias`

Recursao com closure para flat-expand. Position-tracking via
`completions` list. Funciona corretamente sob a restricao.

**Verdict**: codigo correto mas tricky. Refatoracao pra protótipo: usar
arvore explicita ao inves de closure.

### Pieces representation

Pieces sao tuplas heterogeneas: `('lit', text, atom_id)` ou
`('refs', [ref_ids])`. Discriminacao por `p[0]`. Funciona mas verboso.

**Verdict**: usar dataclasses no protótipo para clareza.

## Sobre fugas (e como nao fugir mais)

Os principais "patches" do M5/M6 (preambulo M2.A, mapping prov→final
em M6.C) foram refatorados em M7.A. M8 manteve a estrutura limpa e
adicionou um check de body-order. Codigo nao explodiu (~700 linhas
plausivel para syntax + trace + rede).

Padroes de risco a observar:
- Estado mutavel acumulado em `_emit_alias` via closure.
- Recomputo de estruturas por iter no detector.
- Quando essas duas combinam, refactor.

## Pendencias pra rodadas futuras

1. **Caso `2~13` reuse** (apontado em sessao anterior): intermediario
   de chain `2~13~14~4` nao exposto como alias separada. Requer
   decomposicao pos-detector.
2. **Pre-tx delta** (D6): subtrair base de timestamps/IDs sequenciais
   antes de alg16. Camada modular pro protótipo.
3. **Pre-tx estrutural** (CPF, UUID, IP): mascara fixa, codificacao
   compacta por slot.
4. **Slot variavel em wrapper** (D9): primitivo `7{}5` onde `{}` e' slot.
   Aumenta grammar; experimental.

## Conexoes

- [[../../2026-05-16-M8-virtual-refs-clean-output/notas/conclusoes_M8.md]] — M8 detalhado
- [[../../notas/historia-dirty-lab.md]] — narrativa consolidada (a escrever)
- [[../../notas/roadmap-hipoteses.md]] — hipoteses futuras (a escrever)

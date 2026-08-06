# ADR-0039 — lazytype bool: cabeça congelada + extras declarados (`#TCF.8bB<w><n>`)

- **Status**: aceito (weld 2026-08-01)
- **Escopo**: single-col, união {bool, None, str}. **Fora**: tag `n` e outros tipos
  (`T-LAZYTYPE-OUTROS`), `.8M`, `.8H`, param de estrito (`T-FORCAR-MECANISMO-PARAM`),
  modo-json (`T-MODO-JSON-IMITADOR`).
- **Interage com**: ADR-0036 (bN de domínio — mecânica reusada: domínio comprimido pelo
  próprio core, marcador `=`, `[:-1]` da linha vazia final), ADR-0037 (a cabeça congelada
  `null=0/false=1/true=2`), ADR-0038 (slots no core), ADR-0029 (dispatch posicional: `B`
  no índice 7 sob a tag `b` — namespace livre; `#TCF.8B…` da rota flat intacto).

## Contexto

A união bool+str (coluna concentrada em true/false/null **com exceções string** — "other",
" ?", "N/A") era **fail-loud**: o `.8H` recusa escalar misto (medido no lab
`2026-08-01-0309-json-lib-roundtrip-comportamento`). A única saída era o flat-string, que
perde o tipo — `True` voltava `"true"`.

A armadilha decisiva (lab `2026-08-01-0229`): declarar o domínio **inteiro** (incluindo
true/false/null) **funde `"true"` str com `True`** — os dois viram o mesmo slot e o decode
não tem como separar. Perda silenciosa de tipo, a pior classe de bug do formato. A cabeça
congelada elimina as duas coisas de uma vez: os tipos puros do JSON não viajam (já são
conhecidos a priori — ADR-0037) e os extras declarados são **sempre str**, sem colisão.

## Decisão

Grafia `#TCF.8bB<w><n>` — tag `b` no índice 6, `B` (domínio-primeiro, streaming) no
índice 7, `w` de 1 dígito, `n` em hex mínimo canônico:

- **Cabeça CONGELADA implícita** `null=0, false=1, true=2` (`TABELA_B2` de
  `tcf/tipos_internos.py`) — a MESMA tabela do denso b2 e do core-com-slots. A cabeça
  **NUNCA se declara**: `0` cru no domínio = redeclaração, fail-loud.
- **Extras str declarados a partir do slot 3**, por 1ª aparição; o domínio viaja 1x,
  comprimido pelo próprio core — a disciplina do `dominio_bn` (`_grafa`, `[:-1]`, escape
  `\=` de linha começando com `=`). Extra `""` é válido (domínio = linha vazia).
- `w = max(2, ceil(log2(3+k)))` ≤ 8; b64 sem padding; índices empacotados com o mesmo
  `bitpack` dos densos.
- **Detecção**: vals ⊆ {bool, str, None}, ≥1 bool E ≥1 str. O lazy é o **único** candidato
  que preserva o tipo (o que não é lazy cai no fluxo antigo) — emite o wire direto, sem
  `min()`.
- **Recusas silenciosas do candidato** (devolve None, cai no `.8H` que fail-loud na
  união): LF embutido em extra — achado da fiação `2026-08-01-0322`: o fail-loud de LF
  mora no `encode` público flat, NÃO no `_encode_column` (que devolve `['a\nb']` calado),
  então o check é explícito na rota — e `w > 8` (extras > 253).
- **CONTRATO UNIÃO**: o decode emite lista mista `[bool | None | str]` — a **primeira
  rota que emite união por construção**. Decisão do owner: lazy = default; o modo estrito
  (fail-loud na união) fica para param futuro (`T-FORCAR-MECANISMO-PARAM`).

## Medição

Labs `experiments/lab/dirty/2026-08/2026-08-01/2026-08-01-0229-lazytype-bool-extras/` e
`.../2026-08-01-0322-lazybool-fiacao-rota-real/`:

- **Ganho da cabeça**: 9–14 B × domínio completo, por coluna (a cabeça não viaja).
- **Real-world** Adult `sex` + exceção `" ?"` (n=100): **50 B** lazy vs 64 B domínio
  completo vs 61 B flat-string — e só o lazy preserva o tipo.
- **Detecção**: 8/8 casos de borda corretos, 0 falsos-positivos/falsos-negativos
  (str+null sem bool → flat; bool puro → b1/b2; bool+str+int → fail-loud `.8H`).
- **Gates da fiação**: 12/12 colunas inalteradas (a rota só captura ex-fail-loud).

## Consequências

- Suíte **1105 passed** (1087 + 18 novos, classe `TestLazyBool`); baselines intactos
  (D1-D9 1545, D17a 300, real-world 89430 — a rota só captura o que era fail-loud).
- **Pins alterados: nenhum.**
- **Desvios registrados do lab**: decode implementado **dedicado** (`_decode_lazy_bool`),
  não reusando `decode_bn` — o reuso esconderia a distinção cabeça/extra e um
  pós-mapeamento `"true"→True` fundiria a armadilha; b64 decodado com `validate=True`
  (postura de integridade do denso b1/b2).
- Cross-check com o lab de fiação: os 9 wires de referência decodam e re-encodam
  **byte-exato** no código weldado.
- **Fios**: `T-LAZYTYPE-OUTROS` (o mesmo padrão para `n` e natures — o bool é a
  referência soldada); `T-MODO-JSON-IMITADOR` (com este weld o grupo "TCF ⊃ json" passa
  a existir — a união bool+str que o json-lib aceita e o TCF recusava agora round-tripa;
  os alertas do catálogo ganham trabalho real).

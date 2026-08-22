# ADR-0046 — Nome vazio no `.8M`: porta o `\z` do `.8H` (definição superada, não bug)

- **Status**: **aceito — SOLDADO** (2026-08-21, aprovação do owner: *"aprovo, apenas revise a
  documentação sobre o `\z` porque ele já foi bastante discutido. Veja se foi um bug atual ou
  alguma coisa que faltou por definição."*). Suíte intacta nos gates byte-canônicos (D17a=300,
  D1–D9, real-world) — **nenhum wire sem coluna `''` muda**, por construção e pinado.
- **Supersede**: a decisão do owner de **2026-07-10** (BUG-01, T-QA-8 F0) — *"`''` = coluna SEM
  nome (anônima)"*. Ela nunca teve ADR próprio: vivia em comentários do `multi/core.py` e no
  docstring de `tests/test_f0_boundary_fixes.py`. Fica registrada aqui como **superada**.
- **Estende**: [ADR-0033](0033-hierarchical-codec-weld.md) (o sentinela `\z` do `.8H`) ao `.8M`.
  **Não re-deriva nada** — adota.
- **Fecha**: [`BUG-CHAVE-VAZIA-POSICIONAL`](../../tickets/BUG-CHAVE-VAZIA-POSICIONAL.md).
- **Escopo**: `src/tcf/multi/core.py` (`_esc_name`, `_unesc_name_strict`, `_parse_meta`,
  `_encode_multi`) + docstring em `encoder.py`. **Não** toca encoder/decoder de corpo, `.8H`,
  single-col, nem `_ESC_OK`.

---

## A pergunta do owner: bug atual, ou algo que faltou por definição?

**Faltou por definição — e de um tipo preciso: uma definição feita deliberadamente numa rota,
superada por uma melhor na rota vizinha, e não portada de volta.** Nada regrediu. A cronologia
está toda em código e commits:

| data | onde | o que |
|---|---|---|
| **2026-07-10** | `multi/core.py` (BUG-01, T-QA-8 F0, **decisão do owner**) | `''` → coluna **anônima** (mesmo mecanismo do `drop_names`), com warning e guarda de colisão com o posicional. Razão à época, no próprio comentário: *"o meta NUNCA emite escape-vazio (**evita o `\` solto que fundia tokens**). Internamente não faz diferença: o tcf lida com nomes OU com a numeração em ordem."* Pinado em 6 testes. **Foi decisão, não acidente.** |
| 2026-07-15 | `40a7e10d` | o `.8H` **porta do `.8M`** a convenção de escaping de nomes. Nome vazio ali = `HierarchicalError` (fail-loud). |
| **2026-07-17** | `da1aa73a`, **ADR-0033** | weld D_json no `.8H`: `{"": v}` é JSON válido, logo tem de ser representável. Nasce o `\z`, com o rationale: *"'nome vazio no header' é o SENTINELA DE CORRUPÇÃO do parse; emitir nada tornaria `{"":1}` indistinguível de meta corrompido. `\z` é inemitível por dado: o `\` de dado é sempre dobrado antes."* **Escopo deliberado: L1/flat INTOCADO** — era o ponto daquele weld ser barato. |
| 2026-08-01 | lab `json-lib-roundtrip-comportamento` | acha que o `.8M` muta `{"": ...}` → abre o ticket, rotulado **BUG**. |

Então: o `.8M` carregava a definição de 10/07; o `.8H` a de 17/07. **A razão original do `.8M`
(o `\` solto) não se aplica ao `\z`** — ele é escape completo, não dangling. Ou seja, a definição
do `.8M` ficou obsoleta por construção **no dia em que o `\z` nasceu**, e ninguém voltou lá.

O rótulo "BUG" no ticket é impreciso. É **divergência de definição entre rotas** — a mesma
classe das assimetrias já registradas neste arco (o LF final, H-15-08). E o conserto é
literalmente o espelho do commit `40a7e10d`: aquele portou `.8M` → `.8H`; este porta `.8H` → `.8M`.

## O `\z` já foi bastante discutido — onde (para não re-derivar)

| portador | o que carrega |
|---|---|
| [ADR-0033](0033-hierarchical-codec-weld.md) §tabela de escape | *"nome (meta): idem + **vazio → `\z`**"* · invariante de injetividade (backslash sempre dobrado primeiro) · *"`\z` (e não 'emitir nada')"* com o rationale do sentinela · alfabeto final `\` · `\n` · `\r` (+ `\z`) · gramática `#V<meta>` usa `\z` como campo do envelope |
| [`json-equivalence.md`](../reference/json-equivalence.md) | rows *raiz = array / escalar* (`#V\z…`) e *chave `""`* (`\z` no meta) |
| `src/tcf/hierarchical.py:92–115` | o comentário do sentinela e o unescape **estrito** (só como token inteiro) |
| commit `da1aa73a` | a mensagem com o mecanismo e o porquê |

**Este ADR adota exatamente esse `\z`**, com as mesmas três propriedades: sentinela de
corrupção checado no **token cru**; **inemitível por dado**; válido **só como nome inteiro**.

## A causa raiz, medida

```
encode({"": [...]})                    →  '#TCF.8M!\na\nb'
encode({"x": [...]}, drop_names=True)  →  '#TCF.8M!\na\nb'    ← IDÊNTICO
```

O formato não distinguia "nome vazio" de "sem nome". E o slot estava **livre**: `z ∉ _ESC_OK`
(`,=:\!@%`), e nenhum de 7 nomes reais testados emitia `\z` (o literal `\z` sai `\\z`).

## Decisão

No `.8M`, espelhando o `.8H`:

1. `_esc_name('')` → `\z`.
2. `_unesc_name_strict('\z')` → `''` — **só como token inteiro**; `\z` embutido segue erro
   (`z ∉ _ESC_OK`, inalterado).
3. `_parse_meta` checa o sentinela de corrupção (`'<size>='`) no **token cru**, antes do
   unescape — *"o parse passou a checar o TOKEN CRU"*, ADR-0033.
4. `_encode_multi` **deixa de transformar** `''`: some o warning e some a guarda de colisão
   encode-side — `{"": …, "0": …}` passa a ser legal (dois nomes distintos).
5. `drop_names=True` dropa `''` como qualquer nome — o posicional é o **pedido**, não mutação.
6. **Anônima (posicional) existe só via `drop_names`.**

## Consequências (medidas)

| | |
|---|---|
| RT de `{"": …}` | exato em qualquer posição (1ª, meio, última), com `nature_per_col`, com `min_header=False`, e na `view()` (paridade por construção — `_parse_meta`/`_nomes_resolvidos` são fonte única) |
| wires **sem** coluna `''` | **byte-idênticos**: os três pontos tocados estão guardados por `name == ""`; D1–D9, D17a, real-world intactos |
| wire **antigo** com `''` (emitido como anônima) | continua decodificando → posicional. É tolerante e é honesto: aquele wire **era** indistinguível de `drop_names` — a prova de que o marcador fazia falta |
| custo | `+2 B` (`\z`) por coluna de nome vazio; `+3 B` se não-última (`=\z`) |
| corrupção | segue fail-loud: `'<size>='` cru e `\z` embutido |
| CSV RFC 4180 | `a,b,` · `a,,b` · `,a,b` — **3/3** fazem round-trip (antes: 3/3 quebravam) |
| testes | **6 re-pinados de propósito** (os pins da decisão de 10/07 — cada um diz o que ERA) + classe nova `TestNomeVazioPreservadoADR0046` |
| o que **não** muda | single-col (`name=` só com nature; decode devolve lista — não há chave a mutar) · `.8H` (já fazia) · `_ESC_OK` |

## Alternativas rejeitadas

- **fail-loud** (opção 1 do ticket) — recusaria CSV válido por RFC 4180 (campo vazio é legal).
- **manter** — único caso em que o TCF alterava o dado.
- **marcador diferente de `\z`** — divergir da rota vizinha sem motivo; o slot estava livre.

## Evidência

[`2026-08-21-0900-chave-vazia-posicional`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0900-chave-vazia-posicional/)
(colisão reproduzida · `.8H` como prova de conceito · slot livre · protótipo · CSV) ·
ADR-0033 · commits `40a7e10d`, `da1aa73a`.

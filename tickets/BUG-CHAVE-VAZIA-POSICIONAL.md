---
title: BUG-CHAVE-VAZIA-POSICIONAL — dict {"": [...]} volta {"0": [...]} — único caso onde o TCF ALTERA
status: closed
priority: P2
severity: R1 (avisa, não é silencioso — mas o RT quebra)
created: 2026-08-01
updated: 2026-08-21
gate: byte-canonical (toca rota flat/multi — precisa aprovação + test_real_world_snapshots)
blocked-by: []
related:
  - src/tcf/encoder.py
  - experiments/lab/dirty/2026-08/2026-08-01/2026-08-01-0309-json-lib-roundtrip-comportamento/
---

# BUG-CHAVE-VAZIA-POSICIONAL — `{"": ["a","b"]}` → `{"0": ["a","b"]}`

Achado do lab `2026-08-01-0309-json-lib-roundtrip-comportamento` (matriz json × tcf, 29 casos):
o **único** caso em que o TCF altera o dataset em vez de preservar ou falhar alto.

## Comportamento observado

```python
decode(encode({"": ["a", "b"]}))   # -> {"0": ["a", "b"]}  (com UserWarning)
```

O encoder trata nome de coluna vazio `""` como **coluna anônima** e avisa (`UserWarning`);
o decode devolve o nome **posicional** `"0"`. O RT `{"": ...}` → `{"0": ...}` quebra tipo
e valor da chave. Não é silencioso (há warning), mas é **mutação** — e o TCF não altera,
ou preserva ou fail-loud; este caso foge do contrato.

## Contraste

- `.8H` já resolve chave `""` **com escape** (weld 2026-07-17, `da1aa73`+`d72b9eb` — escape
  D_json cobre chave vazia/LF/CR em valor e nome, ~57k RT adversarial). A rota que perde é a
  flat/multi (coluna sem nome = anônima posicional).
- json lib: preserva `""` de graça (grupo "ambos preservam" quebrado só por este caso no TCF).

## Opções (a decidir)

1. **fail-loud** na rota flat/multi para chave `""` (alinhado ao contrato "não altera"); ou
2. **preservar** `""` via o mesmo escape do `.8H` (custo: grafia nova na rota flat — verificar
   se há slot livre no name-guard).

## FECHADO 2026-08-21 — ADR-0046 (opção 2, `\z`)

**Veredito sobre a natureza do problema** (pergunta do owner: *"bug atual ou algo que faltou por
definição?"*): **definição superada, não bug.** A decisão de 2026-07-10 (`''` = anônima) foi
deliberada e tinha razão à época (um `\` solto fundia tokens); em 2026-07-17 o `.8H` criou o `\z`
(ADR-0033) com L1/flat *deliberadamente* intocado, e a convenção nunca foi portada de volta. O
título "BUG" deste ticket é impreciso: é divergência de definição entre rotas.

**Soldado**: `.8M` espelha o `.8H` — `_esc_name('')` → `\z`; unescape só como token inteiro;
sentinela de corrupção (`'<size>='`) checado no token cru; some a transformação/warning/guard.
RT exato em qualquer posição, `nature_per_col`, `view()`; CSV RFC 4180 3/3; nenhum wire sem `''`
muda; 6 testes re-pinados + classe nova. Detalhes e cronologia:
[ADR-0046](../docs/adr/0046-nome-vazio-8m-porta-o-z-do-8h.md).

## MEDIDO 2026-08-21 — a decisão entre as duas opções, com número

Lab [`2026-08-21-0900-chave-vazia-posicional`](../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0900-chave-vazia-posicional/).

**Causa raiz**: `encode({"": [...]})` produz **o mesmo wire** que
`encode({"x": [...]}, drop_names=True)` — o formato não distingue *nome vazio* de *sem nome*,
e no decode "sem nome" vira posicional.

**A solução já existe na rota vizinha**: o `.8H` usa o sentinela `\z` (`hierarchical.py:114`) e
preserva `{"": ...}` com RT=True. O comentário no próprio código explica a escolha ("por que um
marcador e não emitir nada"). A rota flat/multi não adotou.

**Slot verificado livre**: `z` não está na whitelist de escape do multi (`,=:\!@%`), e nenhum
de 7 nomes reais testados (`z`, `\z`, `az`, `z `, `\`, `\z`, `Z`) emite `\z` no header.

**Protótipo medido** (no lab; `src/tcf` intocado):

| | wire | decode | RT |
|---|---|---|---|
| hoje | `'#TCF.8M!
a
b'` | `{'0': [...]}` | False |
| com `\z` | `'#TCF.8M!\z
a
b'` | `{'': [...]}` | **True** |

Custo **2 bytes**, só na coluna afetada. **7/7 wires de nome não-vazio ficam idênticos.**

**Por que NÃO a opção 1 (fail-loud)**: o nome vazio nasce do próprio CSV (RFC 4180 — campo vazio
é campo legal). Três formas comuns quebram o RT hoje: `a,b,` · `a,,b` · `,a,b`. `fail-loud`
recusaria CSV válido.

> **RECOMENDAÇÃO: opção 2 (preservar via `\z`).** Aguarda aprovação do owner — toca `src/tcf`,
> e o gate é byte-canonical + `test_real_world_snapshots`.

**Não medido**: interação com `drop_names=True`; coluna vazia em posição arbitrária numa tabela
de N colunas (o protótipo cobre coluna única); nome só-com-espaços.

## Evidência

`outputs/matriz.csv` do lab (caso `chave-vazia`) + `result.md` §surpresas.

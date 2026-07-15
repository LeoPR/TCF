---
title: T-SHAPER-NESTED-OUTPUT — saída HIERÁRQUICA nativa no Shaper (aninhar via FK, inverso do flat)
status: open
priority: P3
created: 2026-07-15
updated: 2026-07-15
target: até 1.0 (ferramental; não bloqueia .8)
blocked-by: []
related:
  - scripts/shaper/strategies/join.py
  - scripts/shaper/strategies/fk_preserving.py
  - tickets/T-CODE-TCF8H-WELD.md
  - tickets/T-SHAPER-CODE-HARDENING.md
  - experiments/lab/dirty/2026-07-14-2231-hierarquia-massa-shaper-tpch/
  - experiments/lab/dirty/2026-07-14-2336-hierarquia-amostra-populacao-honesta/
---

# T-SHAPER-NESTED-OUTPUT — o Shaper aninhando (hierarquia como saída de 1ª classe)

**[dispositivo→registro]** Owner (2026-07-15): o Shaper foi feito pra modelar experimentos de forma
**elástica e estatisticamente controlada** sem nos preocuparmos — mas ele **não produz hierarquias
nativamente** (confirmado: `JOIN_LEVELS = ("normalized", "flat")`; o `join.py` só ACHATA via FK).
Nos testes em massa da hierarquia (`#TCF.8H`), os labs tiveram que aninhar **à mão**
(`nest_customers` no lab 2231/2336) — duplicação que este ticket elimina: *"ter a ferramenta
adequada pra situação economiza nossos scripts de teste, que não precisam ter essa capacidade
neles; basta pedir pro Shaper e ele daria bem feito."*

**Prioridade**: NÃO é prioridade agora ("não nos perdermos"); é ferramental a deixar bem feito
**até a 1.0**. Registrado + esboço de alinhamento; implementação espera.

## Esboço de design (alinhamento, não implementação)

O inverso do `flat`: um modo de saída que usa a MESMA metadata de FK (`tables[name].fk` do
`metadata.json`) pra **aninhar** em vez de achatar.

- **API**: `join_level="nested"` (3º valor de `JOIN_LEVELS`) OU parâmetro próprio
  (`nest_root="customer"`); reusar `fact_table`→ raiz. Explícito e direto no request, como o owner pediu.
- **Semântica**: raiz = tabela escolhida; cada FK **entrante** (filho→raiz) vira array aninhado
  (`customer → [orders] → [lineitem]`), recursivo em cadeia — a mesma projeção que os labs fizeram
  à mão. FK **saínte** da raiz (dim lookup, ex. `c_nationkey`) fica como escalar (ou opt-in de embed).
- **Compõe com o que já existe**: `fk_preserving` (amostra honesta estratificada + integridade) roda
  ANTES; o nest é um passo de APRESENTAÇÃO, como o `join_resolver`. Estratificação/volume/seed
  continuam valendo → amostras hierárquicas honestas de graça.
- **Fronteira honesta**: multi-pai/N:N (partsupp) não é árvore — o nest escolhe UMA raiz (projeção
  1:N da N:N); documentar que isso é projeção, não a junção completa (essa é a super-hierarquia,
  H-HIER-MULTITABELA-01, fora do Shaper).
- **Saída**: `list[dict]` (records) — exatamente o contrato do `encode_hierarchical` (DatasetH
  source-agnostic). Tipos: manter os valores como vêm do SQLite; a coerção all-string é do
  consumidor/teste (classe coberta), não do Shaper.
- **Gate**: como toda mudança de shaper, precisa de validação estatística assertada
  (T-SHAPER-SCIENTIFIC-GATING como gabarito) antes de uso em validação científica.

## Critério de aceite

- [ ] Modo nested no request (parâmetro explícito, validado) + estratégia registrada no pipeline.
- [ ] `customer→[orders]→[lineitem]` do TPC-H reproduz byte-igual o aninhamento manual dos labs
  2231/2336 (contra-prova: os labs viram consumidores do Shaper).
- [ ] Compõe com `fk_preserving`/`stratify_by`/`volume`/`seed` (amostra hierárquica honesta).
- [ ] Fronteira multi-pai/N:N documentada (projeção por raiz escolhida; não junção).
- [ ] Testes no padrão dos existentes (`tests/test_shaper*.py`).

# Arquiteturas futuras — Parquet / ferramenta de schema / ferramenta de IA [plano, "depois"]

**Data**: 2026-07-08. **Owner** (2026-07-08): "quero arquitetar **depois** alguma coisa do parquet, da
ferramenta de schema e a de IA." Registrado pra ter âncora quando chegar a vez — **não é pra agora**.
Nenhum dos três toca `src/tcf` sem gate; os dois gadgets são **auxiliares externos** (CLAUDE.md: "só
alertam, nunca arrumam; paralelos; spin-off quando crescer").

## 1. Parquet — inspiração de arquitetura (binarização em camadas)

Já ancorado: **V2-L** ([ADR-0018](../../../../docs/adr/0018-v2-format-roadmap.md)) = "binarização em camadas,
Parquet-like, INTERNO ao TCF" (row-groups/column-chunks/page-headers → header textual roteia + body binário
opt-in, mantendo semântica). **Deferido v2.0** (exige decisão de I/O — V2-J streaming / V2-K disk zero-copy).
O bN (bit-packing) e o cross-dict são candidatos que viveriam sob V2-L. **A arquitetar**: o layout em camadas
(o que é textual-roteável vs binário-empacotável), sem competir com gzip/brotli/zstd (pilar de design).

## 2. Ferramenta de SCHEMA (gadget multi-tabela, alert-only)

Já ancorado: **T-RECOVER-SCHEMA-MULTI-TABLE** (CLAUDE.md §gadgets) — analisa FK/relacionamentos/qualidade
cross-table, **emite alertas, NUNCA arruma**. Não existe ainda; viveria em `scripts/schema_gadget/`.
**Distinto** do `src/tcf/schema.py` (core, `build_schema` per-tabela — mesma palavra, coisas diferentes).
Consome **SideOutputs** (zero-custo). **A arquitetar**: o que detecta (FD/near-FD via g3, chaves, tipos),
como surfaça (relatório), e o acoplamento com o TCF (alimenta prep limpa OU consome output pós-compressão).

## 3. Ferramenta de IA (gadget LLM, spin-off)

Já ancorado: **T-RECOVER-LLM-SCHEMA-MODE** (CLAUDE.md §gadgets) — coleta schema/stats, formata em
"LLM-binary" (token-otimizado, não human-friendly), gera SQL a partir de pergunta de negócio, executa,
output vai pro TCF. **NÃO toca TCF, NUNCA arruma dados**. Spin-off recomendado. Histórico acessório: o
LLM benchmark v0.5 (Q01-Q38) em `llm-benchmark/` + `docs/findings/`. **A arquitetar**: o formato
"LLM-binary" (o que é token-ótimo pra um LLM ler schema+stats) + o loop pergunta→SQL→exec→TCF.

## Fio comum (a arquitetar junto?)

Os três se tocam: o **schema gadget** produz o schema/qualidade que a **ferramenta de IA** formata pro LLM;
o **Parquet/V2-L** é a camada de representação (binária interna) onde o TCF entrega o resultado. Possível
arco: *schema → (IA gera consulta) → TCF/V2-L entrega*. Mas cada um é **spin-off/gadget paralelo** (não
platform play), consumindo SideOutputs, sem dependência bidirecional com o core. Decidir escopo quando retomar.

## Âncoras

- Parquet/V2-L: [ADR-0018](../../../../docs/adr/0018-v2-format-roadmap.md) · filosofia de design (CLAUDE.md pilar 3).
- Schema/IA gadgets: CLAUDE.md §"NÃO é TCF (gadgets auxiliares)" · SideOutputs (`src/tcf/side_outputs.py`).
- LLM v0.5 histórico: `llm-benchmark/` · `docs/findings/`.
- Estratégias por camada: [docs/theory/strategies/INDEX.md](../../../../docs/theory/strategies/INDEX.md).

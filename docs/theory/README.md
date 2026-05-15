# docs/theory — Teoria do TCF v0.6

> **Reset 2026-05-17**: o conteudo anterior de `docs/theory/`
> (architecture, components, methodology, research-lines) descrevia
> v0.4/v0.5 (formato columnar com RLE/dict, LLM Linha A vs B, etc.)
> e foi arquivado em `docs/archive/theory_*_v05/`.
>
> Teoria v0.6 esta sendo reconstruida a partir do dirty lab welded.

## Onde esta a teoria canonica v0.6

**Algoritmos** (camadas do TCF):
- [`../algorithms/OBAT.md`](../algorithms/OBAT.md) — Online Bidirectional Affix Tokenizer (camada 1)
- [`../algorithms/HCC.md`](../algorithms/HCC.md) — Hierarchical Compositional Coding (camada 2)
- [`../algorithms/TCF-format.md`](../algorithms/TCF-format.md) — Formato + posicionamento na literatura

**Narrativa do desenvolvimento**:
- [`../../experiments/lab/dirty/notas/historia-dirty-lab.md`](../../experiments/lab/dirty/notas/historia-dirty-lab.md)
  — historia M0-M14 do dirty lab

**Direcoes futuras / hipoteses**:
- [`../../experiments/lab/dirty/notas/roadmap-hipoteses.md`](../../experiments/lab/dirty/notas/roadmap-hipoteses.md)

## Conceitos pendentes para reconectar

Pendencias conceituais identificadas pelo user para futura
documentacao teorica:

1. **Multi-coluna**: TCF v0.6 atual e' single-column. Como estender
   para multi-coluna (organizer/encoder)? Como dispatch por tipo de
   coluna?
2. **Tipos de dados**: pre-filtro tipo-aware. Numericos, datas,
   estruturados (CPF/UUID/IP) podem ter pre-tx especificos antes
   do OBAT.
3. **Pre-tx layers**: delta (timestamps), estrutural (mascaras),
   aproximado (numericos com tolerancia). Ortogonais ao TCF-CORE.
4. **Storage**: estrategia de 3 camadas (v0.5 tinha em
   `docs/archive/theory_architecture_v05/storage.md`) — revisitar
   quando datasets grandes virarem relevantes.

Estes ficam como **direcoes teoricas** para preencher conforme o
v0.6 evoluir (multi-coluna, pre-tx, escala). Ver
`../algorithms/TCF-format.md` para o que ja esta consolidado.

## Material historico

`docs/archive/theory_*_v05/` contem teoria do ciclo v0.5. Use para:
- Localizar conceitos que possam ser **rebatizados como hipoteses
  novas** no v0.6.
- Rastreabilidade historica de decisoes.

NAO citar como evidencia viva para v0.6 sem re-validar.

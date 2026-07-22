# Conclusão — header-minimal [probatório]

Números: `artifacts/` (`python run.py`). Fecha a pergunta "quanto o header pode ser mais economizado?".

## O header self-describing já está perto do ótimo

Para 2 colunas anônimas, o header desce a **13B** (`#TCF.8M!14,!\n`) — magic + flag + sizes, **sem nomes**,
magic+meta **fundidos**, última coluna **sem size**. Tudo isso **já é 0.7** (`drop_names` + ADR-0022/0023).
Não há um "corte grande" de bytes self-describing restante: cada campo (magic, flag, sizes, markers `!`/`@`/`%`)
é load-bearing pro decode independente.

## Duas levers ortogonais (eco da teoria de cardinalidade)

- **`drop_names`** corta o **header** (os nomes das colunas): 23B → 13B.
- **`nature`** (SPEC_CPF) corta o **body** (cpf 14→5B via pre-tx), não o header.
- São **ortogonais** — a menor combinação real é `drop_names + nature` = **31B** (de 47B). (Mesma
  ortogonalidade cardinalidade⊥compressibilidade da peça 8.)

## O ganho só importa em payload MINÚSCULO (break-even)

Header ~fixo (13–14B); body cresce. Header como % do total: N=1 **39%** · N=5 9.8% · N=20 4.6% · N=100 **1.3%**.
→ encolher o header só move a agulha em **1-poucos registros**. Para N≥~20 o header é <5% — não vale
complexidade de formato.

## O que resta (frontier) e o caminho de protótipo

Dois candidatos, do marginal ao real:

1. **implícito-M** (deduzir `multi` de ≥2 colunas → dropar o byte `M`): **hipotético 12B** (−1B vs 13B).
   Achado das peças hierárquicas P5/P6 (M/N são deduzíveis). **Baixo risco** (o decoder deduz M do meta ter
   ≥2 sizes), mas **1B** — marginal. **Não vale sozinho.**
2. **header DERIVÁVEL** (O-FMT-14): quando o schema é **pré-acordado** (contrato), o header vira só a
   assinatura (**6B**, magic p/ roteamento) ou **0B** (fora de banda). É o **único lever grande** que resta
   (−13 a −23B), mas é uma **feature de contrato/API**, não um tweak de byte do formato. Liga com
   T-CODE-SCHEMA-BUILDER (schema que substitui o header), O-FMT-13 (per-channel) e T-CODE-OUTPUT-SINKS
   (header cacheado/separado do body).

**Recomendação (fecha o estudo)**: o header self-describing está **near-optimal**; nenhum corte de byte
barato resta. O frontier real é o **header derivável (O-FMT-14)** — um recurso de contrato, opt-in, que só
paga em payload minúsculo. **Ligação com o estudo hierárquico**: a declaração de cardinalidade/hierarquia
(peças 5-8) É parte desse "contrato/schema pré-acordado" — o header derivável e a hierarquia declarativa
são a mesma camada. Próximo passo formal (exige aprovação — toca formato/src): decidir se O-FMT-14 vira
feature, e nesse caso o contrato reusa a linguagem de cardinalidade/agrupamento das peças 5-8.

**Gate**: qualquer mudança de formato passa `test_real_world_snapshots.py` + re-pina baselines (ADR-0024);
levers opt-in (default inalterado) não mexem baselines.

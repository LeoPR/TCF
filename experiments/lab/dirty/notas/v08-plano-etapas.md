# v0.8 — Plano em etapas [plano]

**Data**: 2026-06-19 · plano (decidido com o owner). **Meta do 0.8**: shipar o **lazy básico**
endurecido (bugs/correção/performance/otimização, **API atual**) **+ incluir o cross dict
(H-GDICT)**. **Deferir pro 0.9**: a parte avançada do H-QUERY-04. Cross-links no fim.

## Escopo

| | item |
|---|---|
| **INCLUI no 0.8** | Lazy básico shipado (`tcf.view`) + endurecido; **cross dict / H-GDICT** (se caracterização pagar) |
| **DEFERE pro 0.9** | H-QUERY-04 avançado (`execute()`/pushdown, índices escondidos, unificação não-dura); H-INTRA; F2/H-NAT-MARK; filtros populares; V2-RLE nicho |
| **Formato** | `#TCF.7` default; **`#TCF.8` entra SE** o cross-dict (opt-in) for weldado (B). Default sempre byte-idêntico. |

> **Decoupling (ADR-0024)**: pacote **0.8.0** ≠ formato **#TCF.8**. O lazy não muda formato. O #TCF.8
> só aparece se o cross-dict weldar — e como opt-in (default off preserva #TCF.7).

## Workstream A — Lazy: endurecer e shipar
*(ordem do owner: testar → volume → otimizar → repetir. Roda no gadget atual primeiro — read-only —
e só promove pro pacote depois de sólido.)*

- **A1 — Banco de testes em ORDEM** (gadget atual, read-only, oráculo = `decode()` completo):
  - **A1.1 sintéticos** (D1–D17): rodar TODAS as ops (`count/sum/min/max/avg/where/group_count/
    group_ranges/agg_by/select`) em cada dataset; validar resultado contra `decode()` + agregação manual.
  - **A1.2 volume maior** (reais: adult, tpch, receita, br-identidades): correção + medir a **fração
    do blob tocada** por query (a "venda": descomprimir só o necessário).
  - **A1.3 bordas**: colunas `tcf`/`split` (fallback total — confirmar que cai certo), vazios, UTF-8,
    1 coluna, filtro encadeado (AND), coluna inexistente.
- **A2 — Fechar bugs/funcionamento** achados em A1 (no gadget; correção de comportamento).
- **A3 — Performance**: medir tempo + memória por op (vs `decode()` completo); **otimizar com a API
  atual** (sem o Q-04 avançado); **repetir A1** após otimizar (o "otimizar e repetir o teste").
- **A4 — Promover** o gadget endurecido → **`src/tcf/view.py`** (aditivo, read-only; `from tcf import
  view`; shim em `scripts/tcf_lazy/`; export no `__init__`; pyproject auto-empacota). **Toca src/tcf —
  sob aprovação; risco baixo** (não muda encode/decode; rodar suíte + 27 testes lazy).
- **A5 — Reference Diátaxis** da API do lazy (`docs/reference/`) + marcar **estável vs experimental**
  (`agg_by`/L5 podem evoluir no Q-04 → marcar experimental).

## Workstream B — Cross dict (H-GDICT): caracterizar → (se pagar) weldar opt-in
*(o owner acha barato porque os índices já existem — H-REF; mas é format change → caracterizar antes.)*

- **B1 — Caracterizar** (lab read-only): medir **dedup cross-column** em tabelas reais com colunas que
  **compartilham valores** (enums, UF, SIM/NÃO, códigos). Medir **textual-puro E sob brotli E** o ganho
  de **latência no lazy** (dict no header = leitura única). **Gate**: ≥15%/2-reais **OU** justificativa
  **estrutural** (lazy/latência, já que o payoff não é só bytes). Pré-req conceitual: H-REF-02 (índices
  globais) + H-REF-03 (alfabeto livre-de-conflito) na medida necessária.
- **B2 — Design + decisão** (se B1 pagar): formato **#TCF.8 opt-in** (default off = #TCF.7 byte-
  idêntico, padrão V2-A/B/split). ADR novo. **Reconferir L0 (Strata) — é mudança grande.**
- **B3 — Implementar** (sob aprovação): encode opt-in (dict global no header) + decode + **GATE
  real-world** + re-pin de baselines. **Toca src/tcf + formato.**
- **B4 — Integrar com o lazy** (A): `tcf.view` lê o dict global do header (leitura única) — sinergia A×B.
- **Se B1 falhar o gate** → cross-dict **sai do 0.8** (vira 0.9/estudo), como o V2-RLE-STREAM. Honesto.

## Workstream C — Release 0.8
- **C1** bump pacote **0.8.0** (pyproject). Formato: #TCF.7; #TCF.8 só se B entrou.
- **C2** CHANGELOG + STATUS + ROADMAP + MAP + reference atualizados (cross-ref).
- **C3** tag `v0.8.0` (o `release.yml` publica via Trusted Publishing).

## Sequência / dependências

```
A1 -> A2 -> A3 (loop testar/otimizar) -> A4 (promover, ja' endurecido) -> A5
B1 (caracterizar, PARALELO a A) --(se pagar)--> B2 -> B3 -> B4   (B3/B4 dependem de A4)
                                                                 \-> C (release)
```
- **A roda primeiro** (read-only, baixo risco). **B1 em paralelo** (lab independente).
- **B2–B4 só depois** de A4 (lazy shipado) **e** B1 passar. **C por último.**

## Invariantes (guardião)
- `src/tcf` só com aprovação. Toques: **A4** (aditivo, read-only) e **B3** (format change, gated).
- **GATE real-world** + D1-D9=1523B / D17a=303B intactos no caminho default.
- Antes de **B3** (mudança grande/formato): reconferir **L0** ([[feedback-strata-l0-check-before-big-changes]]).
- **Cross-reference** tudo (registry, MAP, STATUS) — [[feedback-sempre-cross-reference]].
- Anti-incidente 2026-05-21 em B1: medir incremento real + sob brotli; sintético não basta.

## Cross-links
- Lazy: gadget [`scripts/tcf_lazy/`](../../../../scripts/tcf_lazy/), [H-QUERY-01](roadmap-hipoteses.md)
  (Pacote 12), design da expansão (0.9) [`hquery01-decode-dag-indices-design.md`](hquery01-decode-dag-indices-design.md).
- Cross dict: [H-GDICT-01](roadmap-hipoteses.md) (Pacote 11-ter) + [H-REF](dict-referencia-hipoteses.md)
  (Pacote 11-quater) + [estudo RLE×DICT](rle-familia-estudo.md).
- Versão: [ADR-0024](../../../../docs/adr/0024-pre-1.0-versioning-git-as-compat.md). Tier: [ROADMAP](../../../../ROADMAP.md).

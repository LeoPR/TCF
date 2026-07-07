---
title: T-FLOW-ENCODE-STRATEGIES-TELEMETRY — Estratégias de encode (speed/mem) + telemetria sugestiva de ordem
status: open
priority: P2
created: 2026-07-05
updated: 2026-07-05
blocked-by: []
related:
  - tickets/T-FMT-TCF8H-HEADER.md
  - experiments/lab/dirty/notas/tcf8h-header-checklist.md
  - src/tcf/side_outputs.py
  - experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/
  - experiments/lab/dirty/notas/tcf8h-proximas-ideias.md
---

# T-FLOW-ENCODE-STRATEGIES-TELEMETRY — o vetor speed/memória (ortogonal aos bytes)

**[dispositivo]** Terceiro vetor de análise (owner 2026-07-05), **ortogonal** a bytes e a RT: **velocidade
e/ou memória**. A questão: a otimização de ordem (reorder, que economiza bytes de header — ver
[T-FMT-TCF8H-HEADER](T-FMT-TCF8H-HEADER.md)) tem CUSTO de tempo/memória. **Onde/quando pagá-lo?**

## Fronteira: o JSON é ALHEIO ao TCF

A camada JSON (parse/serialize) tem encode/decode próprios e **não conta na contabilidade do TCF** — o TCF
consome o **dataset "jsonlike"** (colunar), não o JSON. Logo o hot-path do TCF é o encode/decode do dataset;
a ordem dos dados (chaves) é decidível **fora** do TCF (no produtor). Consumo tem combinações: **export**
(reconstruir JSON, materializa) vs **query/lazy** (navegar a estrutura, toca 0,2–7,9% do blob).

## As três estratégias (o trade speed/mem × ganho de bytes)

| # | estratégia | quando reordena | custo speed/mem | ganho | quando |
|---|---|---|---|---|---|
| **S1** | as-is + omit-closes | nunca (só omite closes) | **O(N) streaming, mem ~1 coluna, zero extra** | omit-closes (grátis) | **DEFAULT — sempre** |
| **S2** | reorder-at-encode | por payload | O(folhas) análise + O(f·log f) sort; **materializa a árvore** (quebra streaming) | + reorder (marginal; só se argmax≠natural) | raro — payload minúsculo, árvore cabe, cada byte conta |
| **S3** | **telemetria sugestiva** | OFFLINE, por AMOSTRAS | **amortizado** (1× por schema, não por payload); consome SideOutputs (grátis) | + reorder **sem custo por-encode** (dados entram já ótimos) | muitos payloads do mesmo schema |

**Insight (o que fecha o arco)**: **S3 move a otimização pra OFFLINE.** Analisa AMOSTRAS (não cada payload),
aprende a forma ótima, e **sugere ao produtor** emitir os dados já na ordem ótima → o encode por-payload fica
barato (S1) E colhe o ganho do reorder (dados já ordenados). Amortiza o custo. **Não pagar o reorder por
encode (S2); pagá-lo 1× offline (S3).**

## A camada de telemetria sugestiva (o novo componente)

- **Consome SideOutputs** (`src/tcf/side_outputs.py`) — já computado, **zero-custo** (filosofia "só o que já
  se calcula"). Extrai: distribuição de sizes/depth por coluna, cardinalidade, near-FD (g3).
- **Sugere** a ordem ótima (argmax digits+depth por folha; base dec/hex) e a forma (normalizar? @dict?).
- Pode ser **ATIVA**: emitir **warning** quando detecta forma subótima ("a ordem de chaves X é subótima pro
  TCF; reordenar pra Y economiza ~kB"). Alinha com os **gadgets alert-only** ("só detecta, nunca arruma").
- Serve também pra **ordem dos dados antes do TCF** (pré-ordenar linhas/colunas p/ economizar tempo do encode).

## Escopo / não-escopo

- **É**: análise offline/sampling + sugestão/warning; NÃO altera `src/tcf` no hot-path; é gadget paralelo.
- **NÃO é**: reorder obrigatório por-payload (S2 é opt-in, medido caro); nem tocar o JSON (alheio).

## Critério de aceite

- [ ] Documentar S1/S2/S3 como a lógica de fluxo (S1 default; S2 opt-in; S3 recomendado p/ lote).
- [ ] Protótipo de telemetria que lê SideOutputs e reporta a ordem sugerida + estimativa de economia.
- [ ] Modo ATIVO (warning) — decidir threshold ("classe fica em pé" = padrão detectado).
- [ ] Medir o custo real de S2 (reorder-at-encode) vs o ganho, pra confirmar "raro que compensa".

# Fila de estudos #TCF.8 — consolidada (3 baldes + ordem) [plano]

**Data**: 2026-06-25. Síntese da varredura (workflow read-only: registry de hipóteses +
tickets + futuras-otimizações + artefatos da sessão). Objetivo do owner: *arrumar o que der
pro #TCF.8*. Fonte da família: [tcf8-estrutura-plano.md](tcf8-estrutura-plano.md).

## (A) ACIONÁVEL pro #TCF.8 agora (aditivo/opt-in, baixo risco)
| estudo | status | nota |
|---|---|---|
| **esqueleto #TCF.8** (discriminador + natures :spec + anônimas + version-stamp) | **WELDED** (ADR-0027/0029) | espinha estrutural; só falta POPULAR com desvios |
| **congelar single-col body @1.0** | ✅ FEITO (ADR-0030, 2026-06-25) | linchpin do órfão default; política decidida (efeito no 1.0; pré-1.0 ainda refinável) |
| **EI global** (escape-invertido por header) | 🔻 ENCOSTADA (alcance estreito) | [lab 06-27](../2026-06-27-EI-alcance/result.md): textual real só em random-digit incompressível (CPF 21%); **brotli-neg** (CPF −19.4%); filtro cego nem round-trip faz → exige **encoder-staging**. Deferido p/ Estágio 1 se surgir uso textual/lazy-puro |
| **T-CI-3** (gate Cython byte-canônico) | open P2 | barato/aditivo; **BLOQUEANTE** antes de mexer em `_detect_compositions` |
| **H-GDICT-01 / cross-dict B2** | B1 PASSA real-world (**−19.3%** SNAP) → B2 | ⭐ melhor candidato MEDIDO; dict global no header; sinergia com lazy |

## (B) ESTUDAR/MEDIR antes (gate read-only antes de codar)
| estudo | status | nota |
|---|---|---|
| fluxo modo-1 (normalizar ID formatado) + **formatado-sequencial / ISO-date** nature | H5 fechou consumidor; H1/H2 abertas | medir normalizar-vs-base94 + overlap com detect_cadence (pode ser redundante) |
| **H-REF-03** alfabeto livre-de-conflito / base94 conflict-free | aberta ("estudar 1º, barato") | pré-req do GDICT + liga ao EI; ⚠️ muda BASE94 global (quebra RT frozen) |
| **H-REF-02** índices globais/contínuos | aberta | pré-req estrutural do dict global; medir net por grau de compartilhamento |
| **T-DATA-1** datasets financeiros/científicos | open (download pendente owner) | **gate-opener**: destrava Pacote 7/natures (sem massa real, nature fica sem gate) |
| O-FMT-18 header byte-size base-94 | baixa prioridade | nicho transmissão-minúscula (~3% do blob); medir se vale |
| no-obat / brotli-aware routing | meta-critérios (lentes de gate) | aplicar como LENTE, não construir (no-obat já derrubado p/ CPF) |

## (C) RESERVADO / deferido (v2.0, caro, ou sem-consumidor)
- **Pacote 7 / META-TYPE-ENCODERS** (natures IP4/MAC/CEP/EAN/FONE/DATA, Luhn/IBAN) — os
  `:spec` futuros, **bloqueados por T-DATA-1 + gate ≥15%/2-reais**. Multi-semana.
- **H-INTRA** (repetição intra-valor, O-FMT-17) — format change caro; medir incremento antes.
- **H-REF-01/04/05** (unificar refs, micro-opts) — caros/risco; tendem a sumir sob brotli.
- **H-V2RLE-02**, **H-CODEBOOK-01** — nichos não-medidos; morrem sob brotli.
- **Pacote 10 LOSS** — fora do 0.7 (lossless-puro); v2.0.
- **tcfx index** / H-QUERY-04d — deferido 0.9; in-blob vs sidecar a decidir.
- **EI serializado/preditivo** — teto do EI; caro/exploratório; só após o piso global provar.
- **perf/IO/streaming** (H-PERF-*, V2-J = modo-3 bypass, OUTPUT-SINKS) — byte-idêntico,
  ortogonal à família self-describing; v2.0.

## Ordem recomendada (arrumar pro #TCF.8 primeiro)
1. **T-CI-3** — rede de segurança ANTES de tocar o detector pra qualquer nature.
2. **congelar single-col @1.0** — decisão/ADR, zero-risco, destrava single-col self-describing.
3. ~~**EI global**~~ ✅ MEDIDO ([lab 06-27](../2026-06-27-EI-alcance/result.md)) → **ENCOSTADO**: alcance estreito (textual-niche, brotli-neg, exige encoder-staging).
4. **H-GDICT-01 B2** — único com ganho real-world JÁ medido (−19.3%); maior payoff confirmado.
5. **H-REF-03** (escape-free) read-only — barato, pré-req do GDICT + sinergia EI.
6. **T-DATA-1** (owner roda download) — gate-opener que destrava Pacote 7/natures.

## Honestidade sobre gates (anti-incidente 2026-05-21)
Sintético NÃO basta (escape-deduction: 15.7% sint → 0.13% real). **H-NAT-MARK-01 está
PARADO** porque o gate ≥15%/2-reais não bate. **Só GDICT-01 cruzou o gate real-world.** EI
tem só sintético ainda. Todo weld de formato exige `test_real_world_snapshots` + D1-D9=1523B
+ D17a=303B + re-pin + L0 Strata, medindo **INCREMENTO** sobre o que OBAT/HCC/seq-RLE/split
já fazem, e **sob brotli**.

## Cross-links
[tcf8-estrutura-plano.md](tcf8-estrutura-plano.md), [roadmap-hipoteses.md](roadmap-hipoteses.md),
hipóteses da sessão ([fluxo](hipotese-filtro-natureza-especulativo.md), [EI](hipotese-escape-invertido-EI.md),
[anotações](anotacoes-caso1-caso2-escape-dv-pipeline.md)), [tickets](../../../../tickets/README.md).

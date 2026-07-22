# Revisao: tecnicas implicitas vs. controles explicitos (2026-06-14)

> **ENCERRADA (2026-07-09, T-CLEAN-3 T3-b)** — checklist de trabalho do ciclo 0.7, FECHADO em
> 2026-06-15 (STATUS "FECHAMENTO DO CICLO 0.7"): itens #1-3/#5/#7 welded (knobs, sort_by, V2-B
> ADR-0025, split ADR-0026); remanescentes re-registrados em `futuras-otimizacoes-formato.md`
> (O-FMT-06/07/14/15) e `roadmap-hipoteses.md` (Pacote 8 H-HCC adiado; H-GDICT-01). Registro histórico.

**Pedido do owner**: revisao geral pra continuar atacando o **0.7**. Inventario
do que o TCF faz **automaticamente** (implicito) vs. o que ja' e' **controlavel**
(explicito), e **o que dar' pra expor** pra modificar o comportamento. Mais os
**detalhes de compressao que passaram batido**.

Escopo: pré-1.0 (ADR-0024), foco byte / payload pequeno
([[project-byte-level-compression-focus]]).

---

## 1. Tecnicas IMPLICITAS (automaticas, sem knob hoje)

| Camada | Tecnica | Onde | Controle hoje |
|---|---|---|---|
| 0 pre-pass | `analyze_column` (features: cardinality, is_numeric, lengths, sample) | `column_features.py` | nenhum (sempre roda) |
| 0 pre-pass | `detect_cadence` (regras 1+2, decide shape-preserve) | `auto_cadence.py` (ADR-0008) | so' via `layers.pre_pass=False` |
| 0 pre-pass | `detect_min_len` (heur v3, gating n>=100) -> min_len/coluna | `auto_min_len.py` (ADR-0010) | so' via `layers.pre_pass=False` (-> min_len=3) |
| 1 OBAT | tokenizacao por afixo LCP+LCS | `core/online.py` | nao-toggleavel |
| 1 OBAT | indice de trigramas (acelera busca) | (ADR-0009) | nao-toggleavel |
| 1 OBAT | `processar` vs `processar_with_hint` | `obat_shape.py` | `layers.obat_shape_preserve` |
| 2 HCC | `_detect_compositions` (greedy + weight model) | `composicional/syntax.py` | nao-toggleavel |
| 2 HCC | seq-RLE near-identical (`*N+delta`), RLE (`*N\|`), whole-value ref (`^N`) | `hcc_seqrle.py` / `syntax.py` | `layers.hcc_seq_rle` (so' seq-RLE) |
| 3 multi | **fallback por coluna** (min(tcf,raw), `!`) | `multi.py` (ADR-0022) | **default-on 0.7**; toggle so' interno |
| 3 multi | **header minimo** (sem prefixo, ultima sem size) | `multi.py` (ADR-0023) | **default-on 0.7**; toggle so' interno |
| — | acelerador Cython de `_detect_compositions` | `_core/detect.pyx` (ADR-0020) | auto se compilado (fallback byte-identico) |

**Observacao**: o pre-pass e o detector HCC sao 100% automaticos. O usuario
nao tem como dizer "use min_len=5 aqui" ou "nao componha agressivo".

## 2. Controles EXPLICITOS hoje (API publica)

- `encode(list)` vs `encode(dict)` — dispatch single/multi.
- `nature=` / `nature_per_col=` — pre-tx CPF/CNPJ/IP (ADR-0015), opt-in.
- `layers=PipelineConfig(pre_pass, obat_shape_preserve, hcc_seq_rle)` — 3 toggles.
- `parallel=` — paralelismo de encode (multi-col).
- `side_outputs=` — introspeccao (features, traces, multi_info).
- **Removidos da API publica** (0.7 default-on): `fallback`, `min_header`
  (toggles seguem internos em `_encode_multi`, p/ comparacao/teste).

## 3. Candidatos a EXPLICITO (o que o owner pode expor p/ modificar comportamento)

Ordenado por valor/baixo-risco:

1. ~~**Forcar formato legado `#TCF.6`**~~ **FEITO (Segment 1, 2026-06-14)**: via
   `encode(table, fallback=False, min_header=False)`. (decoder ja' le ambos.)
2. ~~**`fallback` / `min_header` como opt-OUT**~~ **FEITO (Segment 1)**: re-expostos
   em `encode()` como knobs default-True (zero-param 0.7 preservado). 7 testes
   `TestExplicitControls`. Semantica: #TCF.7 (qualquer feature v2) dispensa o
   prefixo; `min_header` controla a ultima-sem-size; `fallback` controla os `!`.
3. ~~**`min_len` override**~~ **FEITO (Segment 2, 2026-06-14)**: `encode(..., min_len=N)`
   GLOBAL (mesmo min_len p/ todas as colunas). Default None = auto (inalterado);
   guard min_len>=1; threaded ate' o worker paralelo. 9 testes (single + multi +
   parallel byte-identico). **Per-coluna (dict) fica como extensao futura.**
4. **Modo "legivel" vs "byte-minimo"** — ex.: separador `\n` pra colunas raw
   (resolve a emenda byte-delimitada do README), header verboso, etc. Um dial
   trocando bytes por inspecao. Casa com a filosofia (explicabilidade).
5. **Ordering** (O-FMT-01..04) — **CARACTERIZADO + O-FMT-02 IMPLEMENTADO**
   (Segment #5, 2026-06-14). Caracterizacao: `2026-06-14-ordering-characterizacao/`.
   **O-FMT-02 welded como knob `encode(table, sort_by="col")`** (order-free,
   default None; 6 testes TestSortBy). O-FMT-01 (reversivel) perde pro custo do
   mapa -> skip. **Nota**: a redundancia low-card que o sort expoe e' melhor
   capturada por **V2-B dicionario** order-free -> V2-B fica como prioridade da
   revisao multi-col.
6. **Agressividade da composicao** (detector) — ligado a H-HCC-02 (custo
   dinamico). Expor um dial seria consequencia de resolver o detector dinamico.
7. ~~**Dicionario low-card (V2-B)**~~ **WELDED (2026-06-14, ADR-0025)**: 3o
   candidato do fallback `min(tcf, raw, v2b)`, marcador `@`. Caracterizado em 8
   datasets reais (13.9% weighted, RT 42/42). Lab `2026-06-14-v2b-dicionario-
   caracterizacao`. **Futuro**: lossy (V2-C/Pacote7), strip sufixo (V2-D).

## 4. Detalhes de compressao que "passaram batido" (atacar no 0.7)

- **H-HCC-01/02** (composicao perdida + custo dinamico) — Pacote 8, prateleira,
  atacar juntos. `2026-06-14-hcc-composicao-perdida/result.md`.
- **O-FMT-15 deferred-sizing / streaming** (O-FMT-08, V2-J) — a ultima-coluna-sem-size
  ja' welded e' o degrau zero; streaming real e' maior.
- **O-FMT-01..04 ordering** — ganho potencial GRANDE, nunca testado. Reversivel
  (mapeamento no header) vs natural (ordem livre, decisao do owner).
- **O-FMT-06 cross-column dictionary** — compartilhar fragmentos entre colunas
  com schema redundante. Pouco explorado.
- **Single-char ref cosmetico** — referenciar fragmento de 1 char e' byte-neutro;
  sintoma de composicao decomposta (ver H-HCC-01).
- **Emenda byte-delimitada** (coluna raw sem `\n` final) — decisao byte-minimo
  vs legivel (candidato #4 acima).
- **O-FMT-14 header derivavel** — header reduzido a assinatura quando schema
  e' pre-acordado.

## 5. Ordem sugerida pra atacar (0.7, pré-1.0, small-payload first)

1. **Controles explicitos baratos** (#1, #2, #3 da secao 3): legacy toggle,
   fallback/min_header opt-out, min_len override. Dao controle sem risco de
   formato; uteis pra os proprios experimentos seguintes.
2. **Modo legivel vs byte-minimo** (#4) — alinhado a filosofia + resolve a emenda.
3. **Ordering O-FMT-02** (#5) — ganho potencial, precisa decisao de ordem.
4. **H-HCC dinamico** (#6) — maior trabalho conceitual (a "matemagica"), junto
   com H-HCC-02. Por ultimo (mais risco, toca detector + gate).

**Gate**: qualquer mudanca em pre-pass/OBAT/HCC passa `test_real_world_snapshots.py`
+ re-pina baselines (intencional, ADR-0024). Controles que so' ADICIONAM knob
opt-in (default inalterado) nao mexem nos baselines.

## Conexoes
- [[project-byte-level-compression-focus]] (foco byte / small-payload)
- [[project-pre-1.0-versioning-policy]] (baselines re-pinaveis)
- `roadmap-hipoteses.md` Pacote 8 (H-HCC), O-FMT em `futuras-otimizacoes-formato.md`
- ADR-0022/0023 (V2-A/header), ADR-0024 (versionamento)

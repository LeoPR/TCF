# TCF — Roadmap

> Visão **organizada por tier** do que fazer (sem ordem fixa dentro de cada tier).
> Registro granular de hipóteses: [`experiments/lab/dirty/notas/roadmap-hipoteses.md`](experiments/lab/dirty/notas/roadmap-hipoteses.md).
> Estado atual sempre em [`STATUS.md`](STATUS.md).
>
> **Critério recorrente do owner**: preferir o que é **barato** e **não afeta o núcleo
> com severidade** (exceto bug fix). Invariantes: `src/tcf` só muda com aprovação
> explícita; **lossless por default**; **GATE real-world** (`tests/test_real_world_snapshots.py`)
> obrigatório pra qualquer mudança em HCC / pre-pass / prune; nada de weld de natureza/lossy
> sem medir o **incremento** em ≥2 datasets reais (anti-incidente 2026-05-21).

## Estado — 0.7 fechado

Bytes-core welded: **V2-A** fallback (ADR-0022, `!`), **V2-B** dicionário (ADR-0025, `@`,
13.9% weighted), **split estrutural** (ADR-0026, `%`, 19.39% weighted), **header mínimo**
(ADR-0023), **sort_by** (O-FMT-02). Natures CPF/CNPJ/IP (ADR-0015). Pacote `tcf-format 0.7.1`
publicado no PyPI. Suíte 398 passed; D1-D9=1523 B, D17a=303 B.

---

## Tier 1 — PRÉ-1.0 (organizável agora)

Tudo opt-in / gadget / knob; impacto no núcleo nenhum/leve (ou atrás de GATE).

| id | item | custo | impacto núcleo | nota |
|---|---|---|---|---|
| **H-QUERY-01** | Lazy/queryable `view()` — descompressão seletiva por coluna/linha (`count/sum/min/max/avg` + `where`) | M | nenhum | **PoC pronto** ([`2026-06-16-lazy-query/`](experiments/lab/dirty/2026-06-16-lazy-query/)), fora de `src/tcf`. Tese central da 1.0. Promover PoC → gadget. |
| LAZY-QUERY-RUNS | Follow-up: agregar **runs** (`*N|`, seq-RLE) sem expandir a coluna | M | nenhum | Soma/conta grupos lendo os marcadores. Depende de H-QUERY-01. |
| **FILTRO-NUMERO** | Filtro/nature básico de **número** (além de CPF/CNPJ/IP) | S | leve | Caracterizar antes: o delta-aware já cobre incrementais simples? Se sim, vira atalho, não nature nova. |
| FILTROS-POPULARES | CEP, telefone, MAC, data-BR — barato-primeiro | S | nenhum | Reusa `TemplatedPaddedSpec`/`TemplatedCheckedSpec`. Um por vez, weld só com ganho ≥15% em 2+ reais. |
| **H-NAT-MARK-01** | Marcador de nature **auto-descritivo** no header (o SPEC viaja com o TCF) | M | leve | Hoje natures são opt-in *out-of-band*. Header carrega tag por coluna → decode reconhece sozinho. Format change menor (alvo 0.8/`#TCF.8`). |
| V2-RLE-STREAM | RLE no stream de índices do V2-B (follow-up do 0.7) | S | nenhum | Extensão natural do dicionário welded. |
| H-INTRA-01/02/03 | Repetição **intra-valor** (fatorar `111.` dentro de um valor) | M | **médio** | Pacote 11 / O-FMT-17, alvo 0.8. Decidir engine (OBAT×HCC), **medir net** com escape de dígito e **overlap** com nature/split. GATE obrigatório — *não atropelar*. |

### Cheap-wins (baratos, sem mexer no núcleo — exceto bug)
- **release.yml** + Trusted Publishing (automatizar `uv publish`). [S]
- Documentar os knobs explícitos (`fallback`/`min_header`/`min_len`) + trade-offs. [S]
- **O-FMT-12**: auto-detect dialect/tipos do CSV + `encode_file()` conveniente. [S]
- Higiene de header compacto (O-FMT-11, byte-precise). [S]
- Atualizar docstring de SPEC em `natures/__init__.py` (após H-NAT-MARK-01). [S]

### Plano dos filtros (sem atropelar)
Ordem barata-primeiro: **(1)** `FILTRO-NUMERO` — caracterizar se o delta-aware já resolve antes
de criar nature; **(2)** demais populares (CEP/telefone/MAC/data-BR) reusando o framework
existente, **um por vez**; **(3)** `H-NAT-MARK-01` (marcador no header) como camada ortogonal
que faz o decode reconhecer a nature sozinho. Critério de weld por candidato: **ganho ≥15% em
2+ datasets reais**; todos opt-in, sem tocar HCC/pre-pass/prune. Nada avança sem medir incremento.

---

## Tier 2 — 2.0 (depois de uma 1.0 sólida)

- **Lossy** (Pacote 10, [`loss-taxonomia.md`](experiments/lab/dirty/notas/loss-taxonomia.md)) — 0.7 fica lossless-puro:
  - `H-LOSS-00` meta-camada de **contrato** (pré-requisito de toda perda).
  - `H-LOSS-02` **cross-coluna / DERIVED-DROP** (`valor = soma(parcelas)`) — maior teto, owner prioriza.
  - `H-LOSS-01` resíduo-redistribuído (perda por-linha, **soma exata** no agregado). PoC OK.
  - `V2-C-LOSSY` round/quantização/truncamento + naturezas lossy (nicho ~1.5%). Sob GATE N≥5.
- **Streaming / binário** (ADR-0018): `V2-J` streaming low-latency, `V2-K` disco zero-copy + column-pruning, `V2-L` binarização interna (header textual mantido, ainda explicável).
- `META-TYPE-ENCODERS` Pacote 7 (templated/checksummed/composite) + schema-builder Fase 3 — reabre com caracterização real-world (ganho ≥15% em 2+).
- Infra de streaming: output-sinks + encoder-manager Fases 2-4 + plan-contract + per-channel headers (pré-req de V2-J).
- Perf residual: counter incremental HCC (H-PERF-05d, divergência byte-canonical em datetime); Patricia trie como índice OBAT.
- Bundles de menor prioridade: ordenação avançada (O-FMT-01/03/04), cross-column dict + type-aware (O-FMT-06/07) + header desacoplável (O-FMT-14).
- Suporte: fixtures de dados edge (T-DATA-3) pro schema gadget; shaper hardening (>100k).

---

## Tier 3 — Pesquisa / spin-off (talvez 2.0+, muita pesquisa)

Big bets, custo XL, **paralelos** ao Python (não substituem o canonical no curto prazo).
Pré-requisitos comuns: **API pública estável + 1.0 sólida** antes de portar, e **equivalência
byte-canonical** como critério de aceite. Spin-off em repo separado recomendado.

- **TCF-RUST** — core nativo (speed-first dentro do espaço textual). Base dos demais.
- **TCF-WASM-WEB** — codec no browser; queries client-side em `.tcf` local (sinergia com H-QUERY-01). Depende do Rust.
- **TCF-PARQUET-POLARS** — embutir como camada estilo Parquet **ou** módulo no Polars pra acelerar leitura; TCF como backend de I/O. Integração externa ao core.

### Ferramentas auxiliares (gadgets — integração leve, sem dependência dura)
Consomem `SideOutputs`, **nunca arrumam dados**. Podem andar juntas ou separadas, pra terceiros usarem.
- **Qualidade/Schema** (owner #4): o schema gadget multi-tabela **já está completo**
  (`scripts/schema_gadget/`, ALERT-ONLY). O elo novo pedido — *identifica dado → gera SPEC
  automático → marca no header* — **é exatamente o H-NAT-MARK-01** (Tier 1) acoplado ao gadget:
  o gadget vira fonte do SPEC, o header vira veículo.
- **LLM→SQL** (owner #5, spin-off `tcf-llm-tools`): duas tools independentes (schema + geração de
  consulta); a LLM gera SQL e o **SQL roda na camada lazy** (H-QUERY-01). Não toca `src/tcf`.
  Sequência: consolidar H-QUERY-01 primeiro (dá onde o SQL rodar).

---

## Fechados / não retomar (têm veredito)
- **V2-D** strip de afixo — refutado (subsumido pelo OBAT, 0.11%); o ganho real era o split estrutural.
- **H-PERF-04** trigrama de meio — não preserva byte-canonical; coberto por Patricia (Tier 2).
- **H-HCC-01/02** detector de subconta (Re-Pair) — closed-insufficient-gain (teto 1.30%, cauda longa, risco alto no core).
- **H-LOSS-03** round isolado — nicho ~1.5% (só wine); absorvido em V2-C-LOSSY.
- **O-FMT-10 / Pacote 2** escape-dedução — refutada real-world (<1.13%). Manter fechada salvo demanda.

---

*Reorg crítica de 2026-06-16 (132 itens → ~55 únicos). Detalhe granular e proveniência:
[`roadmap-hipoteses.md`](experiments/lab/dirty/notas/roadmap-hipoteses.md).*

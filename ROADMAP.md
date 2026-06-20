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
publicado no PyPI. Suíte **425 passed** (inclui o gadget `tcf_lazy`); D1-D9=1523 B, D17a=303 B.

---

## Tier 1 — PRÉ-1.0 (organizável agora)

Tudo opt-in / gadget / knob; impacto no núcleo nenhum/leve (ou atrás de GATE).

| id | item | custo | impacto núcleo | nota |
|---|---|---|---|---|
| **H-QUERY-01** | Lazy/queryable `view()` — descompressão seletiva por coluna/linha (`count/sum/min/max/avg` + `where`) | M | nenhum | **GADGET** [`scripts/tcf_lazy/`](scripts/tcf_lazy/) (**27 testes; L1–L5 funcional**: pruning, dimensões, contar/agrupar/filtrar sem expandir, group-by por layout). Lê `#TCF.7`, fora de `src/tcf`. Tese central da 1.0. PoC: [`2026-06-16-lazy-query/`](experiments/lab/dirty/2026-06-16-lazy-query/). |
| **H-QUERY-04** | Expansão (design 2026-06-17): **decode-como-DAG**, decode parametrizado (`execute()` pushdown), **índices escondidos** pra grouping | M | nenhum (gadget) | **DESIGN FEITO** ([nota](experiments/lab/dirty/notas/hquery01-decode-dag-indices-design.md)). Princípio: índices = **derivável > {in-file inerte / sidecar `.tcfx`} > formato**, nunca in-blob por default; decisão de índice **por perfil de uso** (transmissão = sem índice; at-rest = index-on-arrival). Unificação **não-dura** (fazer cada→otimizar→fatorar o comum, não monólito); paralelismo por coluna. Plano fases A/B/C + transversal, barato no gadget. Limite duro: coluna `tcf` é entrelaçada → fallback total (o lazy vive em `@dict`/raw). |
| LAZY-QUERY-RUNS (=L3) | agregar/contar grupos sem expandir a coluna | — | nenhum | **FEITO via dicionário/raw** (`group_count`/`nrows`). **Achado**: o `*N|` do modo-tcf é entrelaçado (OBAT+HCC, refs entre linhas) — **não separável**; o ganho limpo vive no dict/raw. |
| **FILTRO-NUMERO** | Filtro/nature básico de **número** (além de CPF/CNPJ/IP) | S | leve | **CARACTERIZADO → PARK** ([`2026-06-16-number-nature-caracterizacao/`](experiments/lab/dirty/2026-06-16-number-nature-caracterizacao/)): **weighted na tabela NÃO atinge ≥15% em 2+** (adult 14,5%, receita 7,1%, tpch 3,4%, beijing 1,3%) e **some sob brotli** (≤6%). Ganho per-coluna (fnlwgt −41%) dilui na tabela. dict/seq-RLE/split já cobrem. Reabrir só como **nature opt-in estrita** se houver caso de transporte cru integer-heavy. Variantes (padded-int / scaled-decimal-lossy) → Pacote 10/v2.0. |
| FILTROS-POPULARES | CEP, telefone, MAC, data-BR — barato-primeiro | S | nenhum | Reusa `TemplatedPaddedSpec`/`TemplatedCheckedSpec`. Um por vez, weld só com ganho ≥15% em 2+ reais. |
| **H-NAT-MARK-01** | Marcador de nature **auto-descritivo** no header (o SPEC viaja com o TCF) | M | leve | **DESIGN FEITO → PARADO em (A)** (owner 2026-06-17): [ADR-0027 `proposed`](docs/adr/0027-nature-mark-header-self-describing.md) + [design](experiments/lab/dirty/notas/f2-nature-mark-header-design.md). Format change `#TCF.7→#TCF.8` (tag `:` no nome, resolução **core-only**, id desconhecido→cru+flag). **Não vale o magic permanente agora** — gate ≥15%/2-reais não bate (só CNPJ/receita) e a DX já tem rota zero-core (registry gadget). Revisitar com 2º nature real. |
| V2-RLE-STREAM | RLE no stream de índices do V2-B (follow-up do 0.7) | S | nenhum | **CLOSED-INSUFFICIENT-GAIN** (caracterizado 2026-06-19, [lab](experiments/lab/dirty/2026-06-19-v2rle-stream-caracterizacao/result.md)): **+1,19% weighted** em 7 reais, **0/7 ≥15%** (melhor adult 7,34%; upper bound sort_by 13%) e **−1,39% sob brotli** (some/inverte). Ganho por-stream real (race +54%, situacao +55%) mas stream é minoria do blob. Reabrir só p/ transmissão textual-pura de low-card clusterizado (nicho estreito). |
| H-INTRA-01/02/03 | Repetição **intra-valor** (fatorar `111.` dentro de um valor) | M | **médio** | Pacote 11 / O-FMT-17, alvo 0.8. Decidir engine (OBAT×HCC), **medir net** com escape de dígito e **overlap** com nature/split. GATE obrigatório — *não atropelar*. |

**Lazy-view, em etapas** (a "venda": descomprimir só o suficiente pra responder): L1
column-pruning + agregadores (PoC) · **L2 medido** — `where(CustomerID=X).sum(Quantity)`
("qtd comprada por um usuário") toca **7,9%** do blob, `count()` 0,2%, vs `decode()` 100%
(online-retail 5k×8) · L3 agregar runs (`*N|`) sem expandir · L4 filtro por índice (`@`) ·
L5 **layout p/ baixa latência** (organizar pra uma query-alvo tocar o mínimo; dimensões
**memória/velocidade/latência/compressão**). **Não é versão de formato** — lê o `#TCF.7` existente.
**L3, L4 e L5 já feitos** no gadget. L3/L4 (via dict/raw): `nrows`/`group_count`/`where`
contam/agrupam/filtram **sem expandir as N linhas** — varrendo o stream do dicionário
(`where(workclass='Private')` em 5k toca ~5% do blob, sem cachear a coluna). L5 (`group_ranges`/
`agg_by`): com `sort_by=key` os grupos ficam contíguos → group-by por slice (o "qtd por usuário"
= `agg_by('CustomerID','Quantity','sum')`, verificado). Achados: (1) agregar `*N|` direto no
modo-tcf não é separável (OBAT+HCC entrelaçados) — o ganho limpo vive no dicionário/raw; (2) o
layout L5 é **trade-off de compressão** (adult `sort_by=education` −10%; online-retail `sort_by=
CustomerID` +2,3%) — o ganho de **latência da query** é sempre presente.

**Filtros modulares (H-NAT-MARK-02, ideia do owner)**: `natures/` vira **pasta de plugins** —
cada filtro um módulo spec auto-contido (regex + transform + id), com um registry que descobre
os de terceiros (drop-in), pra outros desenvolverem os seus. **A API/pasta não é versão** (output
idêntico); só o *spec viajar no header* pra auto-decode por terceiros **é versão (0.8)** = H-NAT-MARK-01.
**Plano completo (DSL textual → "compilador" → registry → header)**: [`filtros-dsl-plano.md`](experiments/lab/dirty/notas/filtros-dsl-plano.md).
As natures já são paramétricas (`TemplatedCheckedSpec`/`TemplatedPaddedSpec` = dados + `check_fn`), então o
compilador é um gerador de instâncias (1:1). Fluxo faseado: **F1 ✅ FEITO** (`scripts/natures_compiler/`,
DSL flat→spec, round-trip obrigatório, **9 testes, zero src/tcf**; regenera CPF/CNPJ/IP do DSL == à mão;
achado: CEP/MAC precisam spec novo) → **F1.5 ✅ FEITO** (registry gadget, lookup de nature por nome, semeado com cpf/cnpj/ip; 5 testes) →
**F2 ⏸ DESIGN FEITO, PARADO** (spec viaja no header #TCF.8 = H-NAT-MARK-01; [ADR-0027 `proposed`](docs/adr/0027-nature-mark-header-self-describing.md);
owner 2026-06-17 escolheu **não implementar agora** — o magic permanente não se justifica só por DX, que o registry gadget já cobre quase de graça) → **F4** builder visual (2.0, front-end
do mesmo compilador). Ressalva: o DSL vale como **infra/DX/explicabilidade**, não garante bytes — gate de ganho antes de weldar.

### Cheap-wins (organizados 2026-06-17)

**Tier A — zero core (infra/docs), feitos:**
- ✅ **CW-1 release.yml** + Trusted Publishing (tag `v*` → `uv build`+`uv publish` via OIDC, sem
  token; gate byte-canonical antes de publicar). Pré-req 1x no PyPI: cadastrar o repo como Trusted
  Publisher de `tcf-format`. [`.github/workflows/release.yml`](.github/workflows/release.yml)
- ✅ **CW-2 Reference dos knobs** (`fallback`/`min_header`/`min_len`/`sort_by` + trade-offs medidos).
  [`docs/reference/encode-knobs.md`](docs/reference/encode-knobs.md)
- ✅ **CW-3 Higiene de comentário CI**: `D17a 322B` → **303B** (322B = `#TCF.6` legado).
  [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

**Tier B — toca `src/tcf`, exige aprovação (NÃO são cheap-wins puros):**
- ✅ **CW-4 FEITO** (owner OK, 2026-06-19): docstrings stale alinhados em `src/tcf` —
  `__init__.py` "#TCF.6 default" → **#TCF.7 default** (era erro); `D17a=322B` → 303B/§5-ponteiro em
  `__init__.py`/`encoder.py`/`syntax.py`/`detect.pyx`; `natures/__init__.py` aponta ADR-0027 (F2
  parado); `syntax_base.py` dropa "v0.6". **Só docstring/comentário, zero código** (diff verificado);
  suíte 379 passed, byte-canonical intacto.
- ~~**CW-5** "Higiene de header compacto" (O-FMT-11, byte-precise)~~ — **FECHADO/subsumido**
  (verificado 2026-06-19): as reduções concretas já estão welded — O-FMT-16 (dispensa prefixo `# `)
  + O-FMT-15 (última coluna sem size) via `min_header` (ADR-0023); escaping via name-guard (ADR-0026);
  flag `M` existe. Single-col já é mínimo (sem header; shebang *adicionaria* bytes). Não sobra byte
  barato no header multi-col; o restante (espaço do magic, sizes decimais) seria **mudança de
  formato**, não higiene — fora de escopo cheap-win.

**Parked:**
- ~~**O-FMT-12**: auto-detect CSV + `encode_file()`~~ — **PARK** (owner 2026-06-16): leitura-de-input
  é fora-do-core por design; `encode(dict)`+`DictReader` bastam (0 bytes). [levantamento](experiments/lab/dirty/notas/ofmt12-encode-file-levantamento.md)

### Plano dos filtros (sem atropelar)
Ordem barata-primeiro: **(1)** `FILTRO-NUMERO` — **caracterizado 2026-06-16**: nicho restrito
(integer alta-card, ganho cru que some sob brotli; decimais exigem variante lossy). Weld só se
houver caso de transporte cru integer-heavy; senão o dict/seq-RLE já cobrem; **(2)** demais populares (CEP/telefone/MAC/data-BR) reusando o framework
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

## Notas de pesquisa (medidas, 2026-06-16)

- **TCF + brotli são complementares em ESCALA** ([`2026-06-16-staged-and-ordering-brotli/`](experiments/lab/dirty/2026-06-16-staged-and-ordering-brotli/)):
  em multi-coluna real (3k linhas, 4 datasets), `tcf-0.7+brotli` **vence** `csv+brotli`
  (Adult −28%), e **quanto mais TCF, menor o pós-brotli**. Refuta "menos TCF ajuda o brotli";
  TCF cheio é o melhor pré-processo. (O cadastro minúsculo do README vendia o contrário —
  artefato de 4 linhas; corrigido.) "TCF pela metade" (`tcf-lite`) chega a ser pior que CSV+brotli.
- **Ordenação é codec-dependente**: a melhor chave de `sort_by` p/ TCF-sozinho ≠ a melhor p/
  TCF+brotli em 3/4 datasets. Ganho ≤5%. Lever pequeno; se welder auto-`sort_by`, considerar o
  modo (com/sem compressão a jusante). Baixa prioridade (2.0).

---

*Reorg crítica de 2026-06-16 (132 itens → ~55 únicos). Detalhe granular e proveniência:
[`roadmap-hipoteses.md`](experiments/lab/dirty/notas/roadmap-hipoteses.md).*

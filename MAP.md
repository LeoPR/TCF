# MAP — TCF project wayfinding

> 1-pagina mapa visual. Se voce sabe O QUE quer, encontre AONDE aqui.
> Se nao sabe o que quer, comece em `STATUS.md`.

## Mapa de alto nivel

```
TCF/
├── CLAUDE.md ............. guia pra Claude Code (project scope)
├── MAP.md ................ este arquivo
├── STATUS.md ............. ponto de entrada bibliografico
├── README.md, CHANGELOG.md
├── ROADMAP.md ........... o que fazer, em tiers (pré-1.0 / 2.0 / pesquisa-spinoff)
│
├── src/tcf/ .............. ALGORITMO CANONICO (M10 baseline; intocado sem aprovacao)
│   ├── core/online.py .... OBAT (canonical)
│   ├── obat_shape.py ..... OBAT shape-preserve hint (ADR-0011)
│   ├── composicional/syntax.py ... HCC M8.A
│   ├── composicional/hcc_seqrle.py ... HCC + seq-RLE near-identical (ADR-0011)
│   ├── auto_cadence.py ... detect_cadence (ADR-0008/0011)
│   ├── auto_min_len.py ... detect_min_len (ADR-0010, H-DA-11)
│   ├── column_features.py  ColumnFeatures + analyze_column (H-DA-11c)
│   ├── encoder.py, decoder.py .... API publica (pipeline delta-aware)
│   ├── hierarchical.py .......... codec #TCF.8H (shredding blocos+counts; L2/L3; reusa L1) — WELD 2026-07-14
│   ├── multi/ ................... encode/decode multi-coluna (core.py + dict_v2b.py; #TCF.8M default)
│   ├── schema.py ................. build_schema per-tabela (CORE)
│   ├── side_outputs.py ........... SideOutputs (efeito colateral opt-in)
│   ├── tipos_internos.py ......... FONTE ÚNICA das tabelas congeladas de slots (bool: 0=null,1=false,2=true; ADR-0037/0038)
│   ├── view.py .................. view lazy/consultavel read-only (A4, `from tcf import view`)
│   ├── natures/ .................. pre-tx por natureza (CPF/CNPJ/IP, ADR-0015)
│   ├── _core/detect.pyx .......... acelerador Cython opcional (ADR-0020)
│   └── __init__.py
│
├── src/shaper/ .......... GADGET auxiliar (nao-core): sampler multidim. (movido de scripts/, 2026-07-19)
│
├── scripts/ .............. FERRAMENTAS DE SUPORTE (nao e' TCF-CORE)
│   ├── dataset_reader.py . le SQLite hubs em Z: (usado pelo shaper via sys.path)
│   ├── _paths.py ......... resolve storage via config
│   ├── setup_adult.py, setup_tpch.py
│   ├── benchmark_*.py
│   └── writers/
│
├── datasets/
│   ├── synthetic/ ........ CSVs pequenos no repo (D1-D17)
│   └── canonical/ ........ metadata only (dados em Z:)
│
├── config/
│   └── storage.json ...... aponta pra Z:/tcf-data/
│
├── Z:/tcf-data/ .......... DADOS GRANDES (fora do repo)
│   └── interim/{adult-census,tpch-sf001}.db
│
├── docs/                  # mapeamento Diataxis local (ver ADR-0012)
│   ├── algorithms/ ....... specs canonicos (OBAT, HCC, TCF-format) [reference]
│   ├── adr/ .............. Architecture Decision Records
│   ├── theory/ ........... fundamentos teoricos [explanation]
│   ├── how-to/ ........... guias tarefa
│   ├── vocabulary.md ..... termos controlados
│   ├── findings/ ......... findings consolidados
│   ├── workbench/ ........ research notes (algumas em _archive/)
│   └── archive/ .......... v0.5 obsoleto (NAO USAR)
│
├── experiments/lab/
│   ├── clean/EXP-NNN-*/ .. prototypes consolidados
│   └── dirty/
│       ├── notas/ ........ registries + <YYYY-MM>/ notas + diario/ + checkpoints/
│       ├── <YYYY-MM>/<YYYY-MM-DD>/<lab>/  .. macros aninhados por data (conv. §Naming AGENTS.md)
│       └── old/ .......... labs historicos (layout proprio, nao aninhado)
│           ├── M0-M14/ ... pre-canonical (NAO USAR salvo historia)
│           ├── welded/ ... pos-canonical welded em src/tcf/
│           └── refuted/ .. pos-canonical refutados/insufficient-gain
│
└── tickets/, tests/
```

## "Quero fazer X" — onde olhar

| Quero... | Va para |
|---|---|
| Entender o projeto | `STATUS.md` -> aqui (`MAP.md`) -> `docs/algorithms/TCF-format.md` |
| **API pública do dev** (o que usar + dispatch de `encode`) | `docs/reference/api.md` (fonte única; `encode`/`decode` únicos; sem `encode_hierarchical`) |
| Saber o estado atual | `STATUS.md` |
| Ver historico do dia | `experiments/lab/dirty/notas/diario/YYYY-MM-DD.md` |
| Retomar de uma pausa | `experiments/lab/dirty/notas/checkpoints/2026-07-12-revisao-roi-fechamento-08.md` (vigente) + diretório `checkpoints/` (histórico) |
| Adicionar/usar dataset real | `scripts/dataset_reader.py` + `scripts/shaper/` |
| Adicionar dataset sintetico | `datasets/synthetic/` + `README.md` la |
| Entender OBAT (tokenizer) | `docs/algorithms/OBAT.md` |
| Entender HCC (composicional) | `docs/algorithms/HCC.md` |
| **Portar o CORE pra C/Rust** (estruturas + fronteira CORE↔HOST) | `docs/algorithms/core-data-model.md` |
| **Capacidade dos SPECS/natures** (mapa único + EnumSpec no-go + self-describing) | `experiments/lab/dirty/notas/2026-06/specs-capacity-map.md` |
| **Estrutura + plano do #TCF.8** (família self-describing, features, sequência, cross-dict, tcfx) | `experiments/lab/dirty/notas/2026-06/tcf8-estrutura-plano.md` (**fonte única**; a `tcf8-vista-o-que-falta.md` da sessão 07-08 é subordinada) |
| **Tolerancia x erro em wire nao-canonico** (taxonomia do recuperavel-com-prova; levantamento gzip/xz/zstd/PNG/protobuf/JSON/CSV/HTML5 + RFC 4648) | `experiments/lab/dirty/notas/2026-08/2026-08-06-2329-tolerancia-vs-erro-politica-de-wire-nao-canonico.md` |
| **Incidente 2026-07-31 — 4 bugs no weld bN + analise critica** (a assimetria de escape apareceu 5x; o invariante de canonicidade existia e nao foi aplicado) | `experiments/lab/dirty/notas/2026-07/2026-07-31-incidente-bn-4-bugs-e-a-analise-critica.md` |
| **Balanco 2026-07-28** (o que foi soldado, o que falta soldar, o que falta revisar antes do float) | `experiments/lab/dirty/notas/2026-07/2026-07-28-balanco-soldado-pendente-revisar.md` |
| **Guia de encaixe pro `.9`** (censo dos ~29 pontos de decisao; o que da' pra antecipar; specs em camadas com CPF piloto) | `experiments/lab/dirty/notas/2026-07/2026-07-27-guia-de-encaixe-para-o-dot9.md` (**vivo**; usa o mapa descritivo `2026-07-27-mapa-do-pipeline-e-o-que-falta-pro-float.md`) |
| **Tipos como specs** (round-trip = indução; 8 eixos; meta-grupo H-TYPE-00..06; bN irmão do dict) | `experiments/lab/dirty/notas/2026-07/tipos-como-specs.md` (estende `specs-capacity-map.md`) + `tipos-meta-grupo-fluxo.md` |
| **Família bN** (bit-packing enum baixa-card) + **gate real-world** + **3 fluxos medidos** | roadmap H-TYPE-02/07 (status vivo; números = cópia, fonte = labs) + gate D3 `experiments/lab/dirty/2026-07/2026-07-08/2026-07-08-1938-bn-gate-realworld-5fontes/` (N=8; terminal 8.8%* / 1.7% pós-brotli — *w≤4 honesto = 5.9%, ver F3) + F1 latência `2026-07-08-2302-f1-bypass-latencia/` (bypass 2.4×) + F3 seletivo `2026-07-08-2355-f3-bn-seletivo/` (5.9%/0.5%; reforça o EnumSpec no-go) |
| **Contrato de omissão** (deduzir/convenção-default/declarar + fail-loud, pré-1.0) | `tickets/T-FMT-OMIT-OR-DECLARE.md` |
| **Hierarquia completa / DatasetH** (fonte-agnóstica; JSON é só adaptador) + escalares especiais `null`/`NaN`/infinitos | `experiments/lab/dirty/notas/2026-07/dataseth-hierarquia-completa-plano.md` + mapa `experiments/lab/dirty/notas/2026-07/estudo-tcf-hierarquico-mapa.md`; EXP-015 CSV↔JSON é prior art de notação, não contrato |
| **Hierarquia — INVENTÁRIO de hipóteses** (exaustão: heterogêneo=TCFs concatenados JÁ provado p/ classe coberta; taxonomia contenção/presença/repetição/normalização; 30 hipóteses; corrida de 3 vias = próximo) | `experiments/lab/dirty/notas/2026-07/hierarquia-inventario-hipoteses.md` |
| **Registry de chars do header .8** (discriminador + marcadores por-coluna + reserva; fecha os fluxos, evita colisão tipo `#TCF.8H`) | `experiments/lab/dirty/notas/2026-07/tcf8-header-char-registry.md` |
| **Arquiteturas futuras** (Parquet/V2-L · gadget schema · gadget IA — "depois", âncoras) | `experiments/lab/dirty/notas/2026-07/arquiteturas-futuras-parquet-schema-ia.md` |
| **Primitivas com nomes diferentes = coisa parecida** (audit p/ consolidar: dict/índice, RLE, spec/nature/tipo, omitir/declarar…) | `experiments/lab/dirty/notas/2026-07/primitivas-consolidacao-audit.md` |
| **Bases/radix em cada parte do TCF** (mapa: header→hex, índices base-94, refs LOCKED decimal, bN bits; fechar aos poucos) | `experiments/lab/dirty/notas/2026-07/bases-radix-usos-tcf.md` + ticket `tickets/T-FMT-HEADER-BASE-HEX.md` |
| **bN × @dict (2 perspectivas) + dict interno clássico** (reativa vs preemptiva; true/false/null congelado; H-TYPE-07) | `experiments/lab/dirty/notas/2026-07/bn-dict-perspectivas-e-dict-interno.md` |
| **Bibliografia / literatura** (column-store Abadi/Parquet/Dremel, bitpacking, DSL — 24 refs) | `docs/reference/bibliografia.md` |
| **Arquitetura share × header × lazy** (balanço compressão↔lazy; cross-dict FECHADO; header=índice) | `experiments/lab/dirty/notas/2026-07/arquitetura-share-header-lazy.md` |
| Ver hipoteses ativas/fechadas | `experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md` (registry **ativo**; homônimo em `docs/theory/` é histórico) |
| Entender a **familia RLE** (linha/stream/intra-valor) | `experiments/lab/dirty/notas/2026-06/rle-familia-estudo.md` |
| **V2-RLE-STREAM** (follow-up V2-B) | `experiments/lab/dirty/old/refuted/2026-06-19-v2rle-stream-caracterizacao/result.md` + registry Pacote 11-bis |
| **Lazy/queryable view** (descomprimir o minimo) | `src/tcf/view.py` (`from tcf import view`; A4) · reference `docs/reference/lazy-view.md` · design 0.9 `experiments/lab/dirty/notas/2026-06/hquery01-decode-dag-indices-design.md` |
| Knobs de encode + view (reference) | `docs/reference/encode-knobs.md`, `docs/reference/lazy-view.md` |
| **TCF ↔ JSON — equivalências** (o que traduz, o que faz a mais, a fronteira) | `docs/reference/json-equivalence.md` (semente do manual; wires confirmados por execução) |
| **Família bN — bits densos de domínio** (wire `#TCF.8B`/`C`, marcador `=`, slot nulo, quando ativa, integridade b64, canonicidade) | `docs/reference/familia-bn-bits.md` (**manual preliminar**; wires medidos) · contraprova `experiments/lab/clean/EXP-016-bn-familia-bits/` (72 casos, 0 falhas) · ADR-0035/0036 |
| **O caminho do dado até o TCF** (arquitetura: as 9 fronteiras onde o dado é reescrito; o TCF ocupa 2; só **grafia** e **ordem** atravessam) | `docs/theory/tipos-o-caminho-do-dado-ate-o-tcf.md` — data como caso trabalhado; casos particulares (SQL/REST/planilha/Parquet/log); e a lente para os próximos tipos (**decimal** é o mais urgente: sem default de indústria) |
| **O ônus do fluxo total, o flag hard, e o formato interno** (a conta honesta: normalizar é 15% do fluxo, o FLOOR é 58% do encode) | `experiments/lab/dirty/notas/2026-08/2026-08-08-onus-do-fluxo-total-flag-hard-e-formato-interno.md` — flag hard poupa **−61% do encode** (risco medido: 4,2× em bytes); separar **parse** de **alvo** vira "1 spec, N parsers" |
| **Nature de data ISO** (`#TCF.8 :data-iso`) — pre-tx data->ordinal decimal | `src/tcf/natures/data_iso.py` · testes `tests/test_natures.py::TestDataIsoSpec` · guia `docs/how-to/normalizar-data-antes-do-tcf.md` — entra como CANDIDATO: recusa onde o OBAT já resolve |
| **Data — triagem das 7 hipóteses restantes** (o que a rodada não cobriu: delta de coluna, spec→bN, dias-úteis, sentinelas, quase-null, resolução mista, colunas irmãs) | `experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0024-data-hipoteses-restantes/` — **alvo DELTA = a maior oportunidade (5,8–6,8×)**; H7 colunas-irmãs MORTA (3%); H1 spec→bN = weld pequeno (até 298 B) |
| **Data — o alvo DELTA: transform de coluna × seq-RLE periódico** (lab próprio do vencedor da triagem; a ideia do periódico é do owner) | `experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/` — **complementares, não concorrentes**: período EXATO paga UMA vez (`uteis` 1590→**41 B**, n=6000→42, O(1); ids não-data 1959→33, nível CORE); delta-coluna ganha alfabeto-pequeno/irregular (345–644 B, robusto a ruído, compõe com bN); **forma-lista degenerada morre**; tickets `T-DATA-ALVO-DELTA`/`T-SEQRLE-PERIODICO` |
| **Spec em três planos** (ADR-0041: `name` de código × `wire_id` de dado × o carimbo) | `docs/adr/0041-spec-id-tres-planos.md` — o **comprimento do id FLIPA o FLOOR** (em N≥11 o nome longo suprime a própria nature); regra `^[a-z][a-z0-9]{0,7}$` fail-loud; a resolução passa a comparar `wire_id`; **modo sem-carimbo** 32→15 B (hoje quebrado nas duas pontas). Mapa de ids = escolha **revisável até o 1.0**; a estrutura é o que congela |
| **Três frentes — ONDE ATACAR** (pesquisa profunda medida: nome de spec · view · pulsos×estrutura) | `experiments/lab/dirty/notas/2026-08/2026-08-12-tres-frentes-onde-atacar.md` — **o comprimento do id FLIPA o FLOOR** (nome longo suprime a nature em N=11-15); **BUG silencioso no view** (nature+dict responde pelo payload: 0 vs 133); single-col no view = dispatch-only e **lê pulsos de graça**; conflito nature-plena×pulso **resolvido de graça** (FLOOR já recusa sufixo em série monotônica → constraint de perfil batch); `.8M` sem bN = **13,8% na mesa** (5ª ocorrência da classe). Menu de 8 ataques com tier |
| **Nomes de spec · lazy com bypass · encode em pulsos** (revisão medida das 3 frentes) | `experiments/lab/dirty/notas/2026-08/2026-08-10-nomes-lazy-e-pulsos-revisao.md` — `:data-iso` é **28% do artefato** (format change, barato só até o 1.0); o **spec CRIA o "run limpo"** que o lazy procurou em 2026-06 e não achou (filtro de data vira intervalo aritmético); e **o wire já aceita pulsos** (RT em 1/2/4/6/12/60) — o bloqueio do V2-J é multi-col, não cobre o single-col |
| **Spec orienta, não manda — a TRIAGEM `.8`/`.9`/`2.0`** (o doc de decisão da direção do owner) | `docs/theory/spec-orienta-nao-manda-triagem.md` — nenhum conjunto FIXO de alvos cobre (folha NEGATIVA nos 3 alvos; eixo **dia-ÚTIL** recupera 99%); `.8` = 2 correções aprováveis; `.9` = guarda-chuva "orienta" (parse×eixos+gates); `2.0` = raiz (nós de proximidade, Patricia, segmentação no motor) |
| **EXP-017 — alvos mensais de data em corpus REAL** (clean, probatório: 26 casos, 5 provas, PINs fixados) | `experiments/lab/clean/EXP-017-data-alvos-mensais/` — **não paga nas colunas de fato cruas** (0% no n amostrado; a caçada mostrou que é instável em n — 18,7% em n=4000 — e que o regime mensal é alcançável como AGREGADO derivado, 1,8–9,8×), porque **nenhuma das 10 colunas reais tem cadência mensal**; e o método corrigido expôs o achado maior: o candidato da nature soldada **não passa pela rota plena** (sem polaridade, sem bN) = **mediana 6,7% desperdiçado** em dado real, geral a QUALQUER nature (CPF 7,0%) |
| **Bateria multi-vetor dos encaixes** (bytes × CPU × mem × online; a regra default+variantes aplicada) | `experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-2228-bateria-multivetor-encaixes/` — **SPEC mensal A4 é o único win-win-win** (679→34 B E 2× mais rápido → default por mérito); E2 sem-dedup = encoder-only (decodável HOJE) mas +84-93% CPU → **variante**; E1 split = +47-54% CPU sempre E não-streama → **variante/perfil**; `T-MAX-PERIODO-31` (teto 24 barra períodos de calendário 28-31) aguarda OK |
| **As duas similaridades do núcleo** (doc de DECISÃO: a tese, a evidência, o espaço de escolha e as 4 perguntas em aberto) | `docs/theory/duas-similaridades-igualdade-e-proximidade.md` — igualdade e proximidade **não competem no mesmo `min()`**; **o spec escolhe um domínio onde a aritmética sobrevive ao dedup** (reenquadra o papel da semântica); 3 encaixes com custo/risco (`T-SPLIT-SINGLE-COL` barato · `T-CANDIDATO-SEM-DEDUP` · Patricia `H-TH-02`); tudo `.9`, nada bloqueia o `.8` |
| **O fluxo do núcleo: IGUALDADE × PROXIMIDADE** (sondas estruturais: o que cada mecanismo consegue ENXERGAR) | `experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-1943-fluxo-igualdade-x-proximidade/` — **a leitura aritmética morre na linha `k`** (1ª repetição aciona o dedup): coluna cíclica `01..12` = 11 deltas legíveis e 423 B, mesma aritmética sem repetir = 20 B; **não existe Patricia no core** (hash de trigrama, e em ISO dá 1 bucket p/ 100% dos únicos); o split que corta `ano\|mês\|dia` existe e **não está na rota single-col**. Tickets `T-CANDIDATO-SEM-DEDUP` · `T-SPLIT-SINGLE-COL` · evidência p/ `H-TH-02`/`H-PERF-04` |
| **Data — o alvo MENSAL (olhar pelo mês)** (direção do owner; 8 regimes × 5 alvos, RT 2 níveis) | `experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-1853-data-alvo-mensal/` — no eixo do mês o mensal colapsa: **679→31 B** (21,9×), faltas **2799→41** (68×), fecho **655→31**, `YYYY-MM` **826→31**; **A4 `mês×31+dia` é o alvo geral sem convenção**; A3 YYYYMM morre; per-valor puro, zero mudança de core; `T-SPEC-PARSE-X-ALVO` atingiu o critério (2 grafias × 3 alvos) |
| **Revisão dos tipos do ciclo — bool → date** (matriz de conformidade re-executável: rota + RT + teto por caso, 32 casos) | `experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-1710-revisao-tipos-bool-a-date/` — **nada fora do lugar**; 2 efeitos do ADR-0040 de graça: **`mensal` INVERTEU** (spec recusava 1085 → aceita **679 B**) e CNPJ constante é da nature (payload menor por valor); fail-louds (`date`/`Decimal`/`datetime`/misto) falam alto |
| **Os dois designs do alvo DELTA — custo real e qual é o barato** (a nota que o owner pediu pra analisar) | `experiments/lab/dirty/notas/2026-08/2026-08-09-designs-do-alvo-delta-custo-e-recomendacao.md` — **recomenda o periódico**: UM arquivo (`hcc_seqrle.py`), sem dependência de outro weld, vale pra qualquer coluna numérica, **os dois gates byte-idênticos** com a camada ligada; o delta-coluna é mudança de PROTOCOLO (4 specs + decoder + registry) e depende do `T-NATURE-CANDIDATO-BN`. Sonda: `design_probe.py` no lab `0042` |
| **DATA — consolidado** (fecha a rodada: o que o OBAT já faz sozinho, o custo de detectar, as perguntas respondidas, e o caminho simples) | `experiments/lab/dirty/notas/2026-08/2026-08-08-data-consolidado-o-que-sabemos-e-o-caminho-simples.md` — **o spec vale onde o OBAT é fraco e PIORA onde ele é forte** (`agrupado` −123%); `fromisoformat` custa o mesmo que olhar 3 chars e é **44× mais barato que `strptime`** |
| **Como entregar data ao TCF** (guia pra quem PRODUZ o dado: a regra em caracteres, as exceções nominais, e as 3 coisas que valem tanto quanto a grafia) | `docs/how-to/normalizar-data-antes-do-tcf.md` — `YYYY-MM-DD` (RFC 3339 `full-date`, **não** "ISO 8601"); Oracle e .NET exigem ação; JSON/CSV/YAML **não têm default** |
| **O custo da ambiguidade de data** (a tese "ambiguidade custa compressão, não integridade" — testada) | `experiments/lab/dirty/2026-08/2026-08-08/2026-08-08-1854-custo-da-ambiguidade/` — **8/8 RT byte-exato com o spec ERRADO**; custo de **+497% a 0%**, proporcional à regularidade destruída; **com FLOOR o prejuízo é ZERO** |
| **Data — alvos × declaração** (7 alvos, 8 regimes; **a declaração inverte metade do quadro**; `delta-dias` carrega a própria grafia) | `experiments/lab/dirty/2026-08/2026-08-08/2026-08-08-0235-data-alvos-e-declaracao/` — `epoch-seg` e `ordinal-b64` NUNCA vencem; pagando os 10 B do header o `ordinal-dec` (campeão a 275×) cai a zero vitórias; inferir a grafia do 1º valor = **100% no ISO** |
| **Data como SPEC — análise crítica** (cabe na FORMA; a ESTRATÉGIA precisa de DOIS alvos: decimal p/ regime regular, denso p/ espalhado) | `experiments/lab/dirty/notas/2026-08/2026-08-08-data-como-spec-analise-critica.md` — decimal ganha até **236×** no regular, denso ganha **27%** no espalhado; header self-describing custa **5 B** (era o número que faltava) |
| **Origem HARD × SOFT — modelo × implementado** (a regra real é *o que o **JSON** aceita*, não *o que o dataset* aceita; existe uma TERCEIRA caixa: hard-RECUSADO) | `experiments/lab/dirty/notas/2026-08/2026-08-08-origem-hard-e-soft-modelo-vs-implementado.md` — simetria de origem confirmada; `date`/`Decimal`/`UUID`/`NaN` são fail-loud; `nature_per_col` já é o embrião do schema |
| **"Aproveita o tipo, não corrige o tipo"** + **onde mora o profiler** (o `status` é taxonomia de PERDA, não de erro → canal é telemetria; profiler = acessório, S3, já decidido) | `experiments/lab/dirty/notas/2026-08/2026-08-08-aproveita-o-tipo-nao-corrige-e-onde-mora-o-profiler.md` — o canal **já existe** (`SideOutputs.nature_apply` com `apply_rate`/`by_status`); **data nativa é fail-loud hoje** |
| **Data LAZY (spec ISO)** — pré-tx no molde da nature do CPF; a ambiguidade BR×US **não precisa ser resolvida** (inversível ≠ correta) | `experiments/lab/dirty/2026-08/2026-08-08/2026-08-08-0016-data-lazy-iso/` — RT **19/19**, até −99,5%; **a válvula de escape não mata o ganho** (50% de lixo e ainda ganha 3,1%); pior perda +4,9% |
| **DATA como tipo — exploração** (formato × precisão × regime × escala; o `*N+M|` já esmaga data e a grafia ISO não alcança; nenhuma representação ganha sempre) | `experiments/lab/dirty/2026-08/2026-08-07/2026-08-07-2311-datas-exploracao/` — 90 medições; 120 datas diárias: **97 B em ISO vs 22 B em ordinal**; regime mensal n=1200 chega a **620×** |
| **Flags do modo bN + perfis macro** (o `C` não é decisão aberta: `B` default stream, `C` declarado; esboço de `stream`/`lote`/`rapido`/`memoria`/`compacto`/`auto`) | `experiments/lab/dirty/notas/2026-08/2026-08-07-flags-modo-bn-e-perfis-macro.md` — `.9`; `encode()` já tem 13 knobs e `PipelineConfig` é o precedente de agrupador |
| **Triagem da auditoria do weld `nB`** (9 achados -> 6 distintos; **zero alcançável por `encode→decode`**; o que é E3 barato e o que fica registrado) | `experiments/lab/dirty/notas/2026-08/2026-08-07-triagem-auditoria-nB-pela-escala.md` — 15 agentes, 5 lentes, saída 100% E4/E5 |
| **Escala de verificação E0–E5** (ingênuo → round-trip → assimetria → fail-loud → canonicidade → adulteração; o que é `.8` e o que é `.9`) + **lista finita de fechamento do bN** | `experiments/lab/dirty/notas/2026-08/2026-08-07-escala-de-verificacao-e-fechamento-do-bn.md` — **4 de 6 bugs reais do ciclo eram E1/E2**; as checagens do bN são 10×E3, 4×E4, 3×E5 |
| **Fechamento do bN — inventário de EXISTÊNCIA** (as 9 facetas de bits: emitida / decodável-não-emitida / fail-loud / ausente; o único buraco é o tipado NUMÉRICO) | `experiments/lab/dirty/notas/2026-08/2026-08-07-fechamento-bn-inventario-de-existencia.md` — critério `.8`=completude, `.9`=otimização; a gramática do `T-BN-TIPADO` **já existe** e está provada pelo `bB` |
| **Vetores ortogonais por mecanismo** (bytes × CPU × memória × **online-ness**, encode vs decode; win-win × troca; a escada foco→variação→escolha→automático) | `experiments/lab/dirty/2026-08/2026-08-07/2026-08-07-2055-vetores-ortogonais-por-mecanismo/` — **online-ness não existe no `bench_perf`**; bN = troca favorável, polaridade = troca ruim (−1 B por +25–42% CPU). Sinal firme, magnitude NÃO (CV ±14–24%) |
| **Descompressão O(1) — quem faz, quem diluiu, quem morreu** (os 4 regimes de acesso; por que largura fixa compra endereço e entropia variável não; onde o bN cai; o que o crítico derrubou) | `experiments/lab/dirty/notas/2026-08/2026-08-07-descompressao-o1-levantamento-e-onde-o-bn-cai.md` — **levantamento, não lab**; nada medido por terceiros vira afirmação do TCF sem replicação (§RT) |
| Entender uma decisao tomada | `docs/adr/` (numerada) ou `experiments/lab/dirty/notas/diario/` |
| Continuar um sub-experimento | `experiments/lab/dirty/<YYYY-MM>/<YYYY-MM-DD>/<lab>/<sub-exp>/README.md` |
| Comparar EXP-010 ao baseline | `experiments/lab/clean/EXP-010-*/report.md` |
| Format do .tcf | `docs/algorithms/TCF-format.md` |
| Convencao de header | `docs/algorithms/TCF-format.{pt-BR,en}.md` (#TCF.8 default, discriminador 5-valores c/ `H`, hex, escaping) + ADRs (0029/0031/0032) + **registry de chars** `experiments/lab/dirty/notas/2026-07/tcf8-header-char-registry.md` (`H` já no spec via ADR-0031; `#`/`&` research) |
| Welding pra src/tcf | `experiments/lab/dirty/notas/2026-05/welding-plan.md` |
| Ideias futuras de formato | `experiments/lab/dirty/notas/2026-05/futuras-otimizacoes-formato.md` |
| Adicionar novo lab | `experiments/lab/dirty/<YYYY-MM>/<YYYY-MM-DD>/<YYYY-MM-DD-HHMM-name>/` (conv. §Naming AGENTS.md) |
| Adicionar EXP clean | `experiments/lab/clean/EXP-NNN-name/` |

## Pontos cegos (evitar confusao)

- `docs/archive/` — v0.5 OBSOLETO. **Nao use.**
- `experiments/lab/dirty/old/` — labs historicos antigos. **Nao use** salvo
  pra entender historia.
- `old/tcf/` — motor v0.5 (niveis L0–L3), **congelado-historico**. Existe
  definitivamente; `src/tcf/` (canonical `#TCF.8`/v0.8, ADR-0032) tem acoplamento ZERO com ele.
  Semantica dos niveis revista em
  [`old/tcf/LEVELS-REVIEW.md`](old/tcf/LEVELS-REVIEW.md). **Nao use** salvo historia.
- `src/llm_query/` — **gadget** geracao de QUERY por LLM (Linha-B: LLM gera SQL/
  polars/pandas, runner executa). Produto vivo do antigo `llm-benchmark/` (dissolvido
  2026-07-19). **Nao e' TCF-core** (fora do wheel). v0.6-quebrado hoje (API v0.5).
- `old/llm-benchmark/` — Linha-A (data-into-LLM, refutada) + mortos + benchmark_*,
  **congelado-historico**. Era `llm-benchmark/` (era `experiments/eval/`).

## Entradas de lab atualmente ativas

Faxina 2026-06-21: 17 labs movidos pra `old/welded/` ou `old/refuted/`
(inclui naturezas-e-camada e cpf-templated-checked). Labs vivos:

- `experiments/lab/dirty/2026-05/2026-05-24/2026-05-24-benchmark-formats-compression/` —
  benchmark csv/json/tcf x gzip/brotli/zstd (TCF vence 4/6); `out_files/` removidos
- **`experiments/lab/dirty/2026-05/2026-05-27/2026-05-27-baseline-consolidado/`** —
  baseline de referencia (METRICS + ADRs-INDEX + lessons-learned + run-baseline.py)
- `experiments/lab/dirty/2026-06/2026-06-19/2026-06-19-lazy-testbank/` — banco de testes lazy A1/A2/A3
- `experiments/lab/dirty/2026-06/2026-06-21/2026-06-21-gdict-caracterizacao/` — B1 cross-dict (H-GDICT) + B2 design/revisao
- `experiments/lab/dirty/2026-06/2026-06-27/2026-06-27-gdict-b2-prototype/` — B2 prototype (formato `&<G>` RT-lossless) + gate N≥5 (FALHOU)
- `experiments/lab/dirty/2026-07/2026-07-01/2026-07-01-crossdict-emprestimo-indices/` — reabertura cross-dict + teste-teto (FECHADO)
- `experiments/lab/dirty/2026-07/2026-07-01/2026-07-01-dict-highcard/` + `2026-07-01-descapar-v2b/` — DICT-HIGHCARD → descapar V2-B (byte-safe)
- `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/` —
  prototype antigo (referencia historica)
- `experiments/lab/clean/EXP-011-multi-column-basic/` — multi-col basico
- **`experiments/lab/dirty/2026-07/2026-07-13/2026-07-13-dataseth-json-bridge/`** — **DatasetH** (intermediário
  source-agnostic p/ hierarquia; JSON = adaptador de prova). R0/R1: `dataset_h.py` (árvore tipada +
  from_json/from_python) + `run.py`. **Stage 1 (codec TCF.H, topologia-primeiro)**: `codec_h.py` +
  `run_codec.py` — `DatasetH↔#TCF.8H` RT-exato (22/22 + fail-loud), fecha `\n`-em-string; tipos/compressão
  = stage 2. Plano: `notas/dataseth-hierarquia-completa-plano.md`; weld: `tickets/T-CODE-TCF8H-WELD.md`.
- **`experiments/lab/dirty/2026-07/2026-07-13/2026-07-13-1835-dataseth-special-scalars/`** — **stage 2 (P1+P2)**:
  escalares especiais `NaN`/`±Inf`/`-0.0` — oráculo `semantic_key` + matriz 21×2 + 2 origens.
  **A (folha tipada) confirmada** (nunca perde bytes, wire inspecionável); C (string escapada)
  refutada-parcial (imposto de escape global). Ver `result.md`. (1955 def-levels + 2019 formatos
  lado-a-lado seguem esta trilha de TIPOS — camada SEGUINTE, ver o lab da base abaixo.)
- **`experiments/lab/dirty/2026-07/2026-07-13/2026-07-13-2301-tcf8h-tabelao-recuperado/`** — **A BASE (volta à prancheta)**:
  hierarquia = tabelão denormalizado (pai repete, RLE `*N|pai` = multiplicidade) + header de colchetes
  `#TCF.8H nome:sz,cidade:sz,telefones[`; motor multi-col REAL, RT-exato (263 B vs 452 JSON, + array de
  objetos). Modelo do lab 1509 + contrato 1830/EXP-015/ADR-0031. **Tipos/nulos = camada sobre esta base.**
- **`experiments/lab/dirty/2026-07/2026-07-13/2026-07-13-2325-hierarquia-cardinalidade/`** — **FORTIFICA a base**: header
  recursivo firme `{}` 1:1 + `[]` 1:N (aninhados, chaveado por CAMINHO), fail-loud (N:N + ambiguidade
  FD/chave — encode auto-verifica, nunca corrompe calado). + **estudo de cardinalidade** (1:1→`{}`,
  1:N→`[]` ANINHAM; N:1→coluna @dict; N:N→ponte); cardinalidade⊥compressibilidade. Tipos/nulos ortogonais.
- **`experiments/lab/dirty/2026-07/2026-07-13/2026-07-13-2356-rle-dual-multiplicidade-deduzida/`** — **dual do RLE MEDIDO**
  (recupera peça 9/2328 + H-CARD-06): multiplicidade repetida por coluna (tabelão A) vs carregada 1×
  (nível-aware B, o "sincronismo"). **Crossover por largura**: estreito→A, largo→B (423<466 em 11
  campos-pai). RLE↔counts↔fk duais; A e B = candidatos de `min()`. RT-exato nos dois.
- **`experiments/lab/dirty/2026-07/2026-07-14/2026-07-14-0111-hierarquico-fechar-fluxo/`** — **FECHA funcionalidade+fluxo**:
  codec por SHREDDING (blocos + counts) faz RT-exato nos clássicos de transmissão (cadastro c/ 2 listas
  irmãs, pedido aninhado, telemetria). Fecha o que o tabelão não fechava (múltiplas listas, ambiguidade,
  array vazio). Dois fluxos: funcional + transmissão simulada (encode→gzip/brotli→decode). Perf real = `.9`.
- **`experiments/lab/dirty/2026-07/2026-07-14/2026-07-14-2043-l3-multiplicidade-independencia/`** — **L3 medido**: multiplicidade
  EXPLÍCITA (`#count`, independência/lazy) vs DEDUZIDA (−bytes, colunas conversam). Crossover: estreito→deduzida,
  **largo (comum)→explícita PARETO** (−bytes E independência). Default do weld (explícito) confirmado; knob = `.9`.
- **Sessao 2026-07-05..08 (specs/tipos/bN/hierarquico — research-track)**: indexados nos mapas
  `experiments/lab/dirty/notas/2026-07/estudo-tcf-hierarquico-mapa.md` (P1-P9 + EXP-015 CSV↔JSON `#TCF.8H`) +
  `tipos-como-specs.md` (reframe + labs 2026-07-06/07 do bN) + `2026-07-08-1938-bn-gate-realworld-5fontes/`
  (gate D3) + `2026-07-08-2302-f1-bypass-latencia/` (F1, 2.4×) + `2026-07-08-2355-f3-bn-seletivo/` (F3,
  5.9%/0.5%). **Tudo fora de `src/tcf`**; relacao com o release em `tcf8-vista-o-que-falta.md`
  (research-track). Consolidacao do dia: `notas/diario/2026-07-08.md`

Referencia (old/, mas ainda consultado):
- `experiments/lab/dirty/old/welded/2026-05-24-cpf-templated-checked/` — CPF/IP
  lab que gerou ADR-0015 + ADR-0016 (14 sub-exps)

Pos-0.7 (2026-06, ainda referencia):
- `experiments/lab/dirty/old/welded/2026-06-16-lazy-query/` — PoC lazy view (gadget
  `scripts/tcf_lazy/`, H-QUERY-01)
- `experiments/lab/dirty/old/refuted/2026-06-16-staged-and-ordering-brotli/` — TCF+brotli em
  escala + ordenacao codec-dependente
- `experiments/lab/dirty/old/refuted/2026-06-16-number-nature-caracterizacao/` — number-nature (PARK)
- `experiments/lab/dirty/old/refuted/2026-06-19-v2rle-stream-caracterizacao/` — RLE no stream
  V2-B (CLOSED-geral / nicho textual-puro ABERTO)
- `experiments/lab/dirty/2026-06/2026-06-19/2026-06-19-lazy-testbank/` — A1/A2/A3 do lazy (banco de
  testes vs oraculo + bug de contagem + otimizacao do caminho do algoritmo)
- `experiments/lab/dirty/old/refuted/2026-06-19-header-rows-vs-bytes/` — teste de proporcao
  header linhas-vs-bytes (row-count REFUTADO; base-94 candidato)
- Notas de design recentes (em `notas/`): `v08-plano-etapas.md` (HISTÓRICO/encerrado — ver tcf8-estrutura-plano),
  `rle-familia-estudo.md`, `dict-referencia-hipoteses.md` (H-REF),
  `hquery01-decode-dag-indices-design.md`, `transmissao-api-onde-tcf-importa.md`
  (guia de transmissao), `f2-nature-mark-header-design.md`, `cep-outer-dict-codebook-pesquisa.md`

Labs **historicos** (NAO modificar, NAO continuar):
- `experiments/lab/dirty/old/M0-M14/` — fase v0.6 inicial pre-canonical
- `experiments/lab/dirty/old/welded/` — 10 labs welded apos M14 (ADRs
  0008/0010/0011/0012/0013/0014 etc.)
- `experiments/lab/dirty/old/refuted/` — 7 labs refutados ou
  closed-insufficient-gain

## Manutencao deste mapa

- Update quando criar lab/EXP novo
- Update quando mover/remover entrada importante
- Single-source: este arquivo NAO duplica conteudo, so' aponta
- Cross-links sao "information scent" (Morville)

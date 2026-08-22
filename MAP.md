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
| **Date: o processo de compressão** (formato fixo, todos no mesmo `min()`, 2026-08-15) | `experiments/lab/dirty/2026-08/2026-08-15/2026-08-15-0400-date-processo-de-compressao/` — 6 transformações × 14 regimes, 0 falhas. **A partição é limpa e nenhum candidato domina**: `ordinal` (welded) ganha em **8 de 14** (progressão regular), `delta` onde ela **quebra** (mensal-faltas **80,1%**, cíclica **63,3%**), **`delta2` — nunca medido antes — onde os saltos são irregulares mas crescentes** (esparsa-ordenada **84,3%**), e `componentes` onde a **ordem some** (45,5%). A decisão que destrava os 6: **protocolo de transformação de COLUNA** (a nature é per-valor). → `H-DA-12` |
| **O encode pode sustentar a entrada tipada?** (ciclo de avaliação, 2026-08-15) | `experiments/lab/dirty/notas/2026-08/2026-08-15-0320-encode-entrada-tipada-avaliacao.md` — a preocupação do owner **junta duas coisas que se subtraem**: objeto `date` tem **0 grafias a validar e não pode ser inválido** (10× mais barato que a string canônica de hoje), enquanto *string livre* é o risco real e continua vetado. E **deixar com o dev não é mais seguro no datetime**: `str()` dá espaço e `isoformat()` dá `T` — ele erra **sem saber que escolheu**. Desenho de menor risco: **normalização na porta**, wire **byte-idêntico**, sem tag nova, 1,7% do encode |
| **Decode direto ao tipo** (proposta do owner, medida, 2026-08-15) | `experiments/lab/dirty/2026-08/2026-08-15/2026-08-15-0200-decode-direto-ao-tipo/` — o objeto `date` **já existe no meio do decode** (`data_iso.py:107`) e é jogado fora; o cliente re-parseia. Cortar as duas pontas economiza **17,5–19,3% do decode completo** (protótipo de 9 linhas, `src/` intocado). União `['date','str']` herda o **CONTRATO UNIÃO** do ADR-0039. Desenho: kwarg `saida=` da API do host, **wire byte-idêntico**, string continua default. Linha vermelha: escolhe **tipo**, nunca grafia → `T-DECODE-SAIDA-TIPADA` |
| **Datetime: os CINCO planos** (ciclo de avaliação, 2026-08-15) | `experiments/lab/dirty/notas/2026-08/2026-08-15-0230-datetime-os-cinco-planos.md` — o owner separou *o que o dataset entrega* de *o que o decode promete*, e eu os colapsava. **O TCF recusa `datetime`/`date`/`time`** — só os 4 escalares do JSON entram. A premissa de velocidade se confirma (`fromisoformat` 1,48× o do date, 61× mais barato que `strptime`), **mas o guard de re-emissão custa 4,6× o parse** e uma regex o substitui por 2,4× menos. E **aceitar 16 grafias e devolver 1 deixa só 3 sobreviverem ao RT byte-exato**. Três caminhos: **A** string canônica (cabe no `.8`), **B** timestamp (já funciona, é manual), **C** objeto datetime (tipo novo, bloqueado) |
| **Spec de datetime — a receita do padrão** (protótipo, 2026-08-15) | `experiments/lab/dirty/2026-08/2026-08-15/2026-08-15-0130-spec-datetime-receita-do-padrao/` — a decisão do owner (*datetime é pré-formatado; variantes viram string*) elimina as 13 grafias. O spec **ganha em 7 de 8 regimes** (14,3% a 99,8%) e nunca perde. **O payload não se escolhe por 'menos dígitos'**, e sim por quantos ficam **invariantes** — o OBAT fatora o número e o seq-RLE perde a corrida (→ `T-OBAT-COME-O-SEQRLE`). **Errar o separador custa ZERO** (byte-idêntico ao sem-spec), e **nenhuma das duas grafias é RFC 3339** — o argumento de norma do `data_iso` não transfere |
| **Datetime: 13 grafias × 8 regimes × 9 mecanismos** (o 1º lab do tipo, 2026-08-15) | `experiments/lab/dirty/2026-08/2026-08-15/2026-08-15-0020-datetime-grafias-regimes-mecanismos/` — cada candidato medido **isolado** (o `encode()` só mostra o vencedor). **O split VIVE DA ORDEM**: embaralhado ele vai de 842 a **6331 B (+651,9%)** e perde para o `dict`; só `bN` e `dict` são imunes. Isso põe ressalva no **7,13×** do `T-SPLIT-SINGLE-COL`. A **grafia compacta e a de 12h não splitam** (1 grupo; `AM`≠`PM`). No batimento, `epoch-s` bate o split em **56×**. E há regime em que o núcleo **infla 9,9%** — falta `raw` no `min()` do single-col |
| **Float e hora nas vertentes RESTANTES** (a reavaliação cobrada, 2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2350-float-hora-vertentes-restantes/` — os 5 eixos estruturais não bastavam: **nenhum fechamento tinha passado latência/memória/velocidade/transporte**. Medido: o **`view` não abre coluna tipada nenhuma** (só `.8M` de strings — 5ª divergência da solda dupla); fatiar custa por **classe** (bN 2,62×, literal 1,11×, polaridade **0,96×**); hora custa **21× o int** em CPU e **126× a entrada** em pico (dev-run); e **pós-gzip o sinal inverte nas 6 colunas** — o ganho é terminal. O ritual de fechamento ganha +4 vertentes |
| **Hora binarizada pelo ESPAÇO DO TIPO** (a pergunta do owner, 2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2320-hora-binarizada-pelo-tipo/` — **tem nicho, e ele é um limite de NAMESPACE**: a virada cai exatamente onde o núcleo para de usar o `bN` (`MAX_W=8` → 256 distintos, porque a largura é **um dígito** no header). Acima disso não há candidato denso nenhum — e a coluna real (k=564) ganha **−46,5%**. Mas **binarizar destrói a estrutura**: onde há progressão, o ordinal **decimal** vence por **77× a 114×**. `5+6+6` e o ordinal de 17 bits custam o mesmo (5682 vs 5683 B) — `2^5·2^6·2^6 = 2^17`. → `H-DENSE-MODE-03` |
| **Fechamento do tipo HORA** (7 regimes + 9 bordas + ciclicidade, 2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2230-fechamento-hora/` — **0 falhas**, conforme nos 5 eixos, 7 peculiaridades. **A peculiaridade registrada estava INVERTIDA**: a ciclicidade **ajuda** (7 dias **−73,0%** do cíclico contra o absoluto), porque ciclar é repetir e o dedup pega o que o seq-RLE perde. O ordinal é **complementar** (94,4% sem wrap, 6,9% com). E achou a **4ª situação** do `T-NATURE-IGNORADA-CALADA`: um spec que aplica em **0%** vence o FLOOR e **carimba `:cpf` numa coluna de horas** |
| **Float e suas variantes — CONSOLIDADO** (o que fecha, grafia × valor, o parâmetro de tolerância, o aviso, e a fila) | `docs/theory/float-e-variantes-consolidado.md` (**fonte única do ciclo de 2026-08-14**) |
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
| **Resposta aos poréns da semana** (crítica medida da avaliação de 2026-08-13) | `experiments/lab/dirty/notas/2026-08/2026-08-13-0430-resposta-aos-parens.md` — 6 poréns testados com encode/decode reais: **#6 é mais forte do que ele argumentou** (6 inversões em 77 colunas reais, 4 fora do empate, até 7 B) e **absorve o #2**; **#1 corrige o meu ADR-0040** (o +35% é pior caso; corpus real = **1,37%**); **#3 tem premissa errada** (a classe está fechada por construção — sweep 4/4 modos limpo); e ele **não viu** o `T-UM-CAMINHO-SO`, que muda a ordem. Fila revisada |
| **Single-col é convenção humana** (a direção que explica 4 tickets de uma vez) | `experiments/lab/dirty/notas/2026-08/2026-08-12-single-col-e-multi-col-de-uma.md` — no código, um multi-col de UMA coluna; as 4 divergências achadas (bN no `.8M` 13,8% · split no single −35/−63% · `view` que só abre `.8M` · rota plena da nature ~5,7%) são **uma causa só**: dois caminhos ⇒ solda dupla ⇒ na prática solda simples. **Estudo depois dos tipos** |
| **EXP-018 — `IntPadSpec` + abertura da rota tipada** (CLEAN, protótipo do weld, 2026-08-14) | `experiments/lab/clean/EXP-018-int-pad-e-rota-tipada/` — 18 casos, **0 falhas**, 7 provas por caso (RT com **tipo**, nunca-pior, determinismo, artefato-é-o-wire). O spec vence em 6 (mediana **1,79×**, máx **2,80×**) e **recusa nos outros 12**, com wire byte-idêntico ao de hoje. **SOLDADO 2026-08-14** — `natures/int_pad.py` + a porta tipada aberta (`nature=` e `min_len=`); wire `#TCF.8n :ipad`, auto-contido, decode resolve pelo registry. Suíte 1252 → **1260**, gates verdes |
| **Fechamento do tipo FLOAT** (12 bordas + 5 colunas reais, 2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-1616-fechamento-float/` — **0 falhas**. Conforme em tudo; **6 peculiaridades declaradas**, com destaque para a **tag-união** `int|float` (o tipo vem da grafia, não da tag) e para **`-0.0`, que `==` não detecta** — só `copysign`. NaN/±Inf recusados fail-loud; max-float e subnormal atravessam |
| **Lab: RLE intra-valor medido** (2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2010-rle-intra-valor-medida/` — 4 blocos, 0 falhas. Par de contra-prova prova que o núcleo **não aproveita run** (29 B = 29 B); curva com coeficiente **exato 1,0**; e o **Bloco 3 inverte o fluxo** — 4 wires do `*0\|` escritos à mão em `inputs/`, para perguntar o que o **decoder** aceita. Contra-prova real = `c_name` **+6,90%** |
| **Lab: a perda por cinco lentes** (2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2010-perda-propagacao-de-erro/` — a mesma perda dá **66,67%** por valor, **0,00029%** na soma, **passa intacta** pelo produto e **825,9%** numa diferença de próximos, com **203 de 500** margens trocando de sinal. Contrato diferente: valida o **formato sobre os arredondados**, não o RT contra a origem |
| **RLE intra-valor: dá para fazer barato?** (estudo + análise crítica, 2026-08-14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-2010-rle-intra-valor.md` — **já discutíamos desde 2026-06-16** (H-INTRA-01/02/03 · O-FMT-17), mas **nunca houve lab**. O núcleo captura **zero** run intra-valor (o OBAT só compara extremidades); curva **1,000 B/char, sem amortização**. A grafia inline esbarra no `*` (já é separador) e no escape de dígito → desbloqueio é **H-REF-03**. E o **`*0|` já produz o RLE fantasma hoje, sem guarda** (`T-RLE-COUNT-ZERO`). Contra-prova: `c_name` **+6,90%**, porque o run ali sustenta a progressão do seq-RLE |
| **Lab: `agg=soma` e streaming** (2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2145-agg-soma-e-streaming/` — 3 formas × 3 casos, 0 falhas. **`agg="soma"` É stream-compatível, mas só na forma de DIFUSÃO DE ERRO**: lê 1 valor, emite 1, mantém 1 float de estado, e a soma sai exata — por **+2,0% de bytes** e o dobro do erro por linha. O maior resto precisa de **2000 leituras antes do 1º valor**. A âncora é a mais barata e é **outro contrato** (as linhas não somam). Separa **prefixo de encoder** de **prefixo de decoder** — este último ficou 19 B nas três |
| **Lab: um parâmetro de tolerância para float** (protótipo, 2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2110-parametro-de-tolerancia-float/` — 12 pedidos × 3 colunas, **0 falhas**. `Tolerancia(quantum/abs/rel/agg, mode)` com três estágios **derivar → aplicar → verificar** e fail-loud. **Prior art**: o `H-smart-rounding` (2026-04-10, congelado) desenhou e nunca testou — as 4 tarefas seguem desmarcadas. **Achado**: o `mode` muda a **fórmula** da derivação, não só o viés (`down` erra 1 passo, `half-*` meio) — e **a verificação recusou** antes de eu perceber. `wine.density` cai **93%** com `rel=1%`; `rel` é **inútil em money** (a cauda inferior amarra) |
| **Perda orientada a erro: o que a tolerância significa** (2026-08-14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-2010-perda-propagacao-de-erro.md` — a mesma perda dá **66,67%** por valor, **0,00029%** na soma, **passa intacta** pelo produto e **825,9%** numa diferença de próximos (**203 de 500** margens trocam de sinal). Vocabulário de **4 eixos + `mode`** (`quantum`/`abs`/`rel`/`agg-exact`), com justificativa por área (HMRC/GUM/SZ3/controlled rounding). Achado sem cobertura na literatura: **preservar um agregado pode degradar outro** |
| **Grafia fracional e escala com exceções** (o lab da pesquisa, 2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-1745-grafia-fracional-e-escala-com-excecoes/` — 4 mecanismos × (7 sintéticos + 8 bordas + 5 colunas reais), **0 falhas**. **A escala pura falha de DUAS maneiras** (recusa; e *pior que nada* — 188 vs 124 B); a escala **com exceções** resolve as duas e tira 109 B da coluna que recusava. **O núcleo já tem o mecanismo**: `MARKER_LITERAL='_'` e `int_pad.py:73-74` são o patching do ALP. A grafia fracional é sólida (126/126, auto-protegida por re-emissão) mas o corpus tem **n=1** de dízima. E **3 defeitos meus** que o lab pegou — todos *mecanismo que não verifica engana* |
| **Loss mode e lossless-alterado em float: pesquisa** (interna + literatura, 2026-08-14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-1739-loss-e-lossless-alterado-pesquisa.md` — o estudo interno **já existia** (`loss-taxonomia.md` + PoC do maior-resto, Pacote 10); a literatura confirma os dois lados: **ALP** (SIGMOD 2024) faz escala decimal-como-inteiro lossless **com exceções por-valor** — o que enfraquece a razão "precisão suja inviabiliza a escala" do `T-FLOAT-SPEC` — e o **controlled rounding** da estatística oficial é o método do PoC. Nova: **H-FLOAT-GRAFIA-01** (fração `1/3…12`, lossless por grafia, sem gate) |
| **Fechar TODOS os tipos no `.8`** (correção de critério do owner, 2026-08-14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-0430-fechar-todos-os-tipos-no-08.md` — **um tipo não fecha porque compensa, fecha porque foi verificado**. Eu recomendara float p/ o `.9` e hora p/ o fim, por ROI de bytes — repetindo o erro que o owner já corrigira. A tabela de estado dos 7 tipos por 7 eixos, e a peculiaridade estrutural que só apareceu agora: há **duas famílias de spec** (sobre tipo nativo × sobre string), e fechar float/hora/datetime é o teste de se o fluxo é um só |
| **Float: avaliação** (30 colunas reais, 2026-08-14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-0400-avaliacao-float.md` — **não precisou de literatura**: o corpus já tem as variações (float com `1.`, casas variadas, entre 0 e 1, formatados) **+1 não prevista** (precisão suja de médias, que **quebra a escala**). Agregado **8,0%**, melhor caso 1,16× — outra ordem de grandeza contra int e data. E o **`IntPadSpec` não é reaproveitável** aqui. Fica para o `.9` |
| **Spec de HORA (sem data): avaliação** (2026-08-14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-0330-avaliacao-spec-de-hora.md` — **não se justifica agora**: 1,03× no único dado real, e hora pura não existe no corpus. Hora é **cíclica** (volta a zero), diferente do ordinal absoluto da data. O caso real é datetime — e ali o **split estrutural que já existe** dá **7,13×** (61.856 → 8.675 B), batendo epoch (2,30×) e separar à mão (3,52×). Reforça o `T-SPLIT-SINGLE-COL` |
| **Os gatilhos do int em corpus REAL** (39 colunas de `Z:`, 2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-0112-gatilhos-int-em-corpus-real/` — fecha a lacuna dos três labs sintéticos. Agregado **11,2% menor**; o **PAD é o que vale** (mediana **1,72×**, zero empates), o **B94 é marginal** (1,14×, 33 vitórias de ≤1 B) e o **`min_len` não ganha em nenhuma** — este corpus não tem timestamps. **Meus gatilhos estão mal calibrados** (o do B94 disparou 2× e ele venceu 28×), o que reprova a auto-detecção proposta. Viés declarado: 25/39 são TPC-H |
| **O OFFPAD detalhado — e o int embutido no date** (2026-08-14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-0210-offpad-detalhado-e-o-int-no-date.md` — a observação do owner resolve o dilema: o `data-iso` **é** um offset com base **convencionada** (a época), e o seq-RLE é um offset com **âncora emitida** — as duas fazem a informação viajar. O OFFPAD era a única que não. **E é dispensável**: onde ganhava, ou o PAD dá o mesmo, ou só ajustar `min_len` resolve melhor **sem spec** (epoch 40→27 B). A decisão A/B/C desapareceu |
| **Conformidade de fluxo por tipo** (lab, 2026-08-14) | `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-0032-conformidade-de-fluxo-por-tipo/` — **o fluxo é conforme**: int, float e str são idênticos nos 5 regimes (muda a tag, não o mecanismo); o **bool diverge só no denso**, com razão escrita no código. RT preserva tipo em **12/12**. Falta 1 peça (spec na rota tipada) e sobra 1 assimetria (`nature_per_col` silencioso em tipado, recusado em string). **3 correções do próprio instrumento** antes de valer |
| **Tipos como FLUXO, não como ramo** (ciclo de análise, 2026-08-14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-0100-tipos-como-fluxo-nao-como-ramo.md` — a generalização que o owner pede **já está feita** (`_tipo_single_col` devolve `(tag, render)`; cada tipo é uma linha). Os 3 planos dele mapeados: **core não vê tipo**, a API é onde está o buraco, o wire declara. O bool não tem rota própria — tem **um candidato a mais** no mesmo `min()`, e o int já herda **5 de 7** algoritmos. Triagem `.8` estrutura × `.9` atalho |
| **Onde o spec encaixa na rota tipada** (investigação de código, 2026-08-13/14) | `experiments/lab/dirty/notas/2026-08/2026-08-14-0010-onde-o-spec-encaixa-na-rota-tipada.md` — responde o "onde" com file:line (`encoder.py:539` no encode, `decoder.py:410-411` no decode, FLOOR em `:549-600`, header `#TCF.8n [nome]:id` com slot livre). **Corrige uma afirmação minha**: a tag tipada não é custo vazio — ela seleciona a família de cast. E o `.8H` **não** é apagar um check: a gramática do meta é mutuamente exclusiva entre tag e id, então apagar faria coluna int voltar string sem erro |
| **Inteiro: a matriz tipagem × spec** (correção do owner, 2026-08-13) | `experiments/lab/dirty/2026-08/2026-08-13/2026-08-13-2326-int-tipagem-x-spec/` — o lab anterior media inteiro **só como string**; aqui a matriz (14 regimes × 4 células, RT comparado com **tipo**). A rota tipada custa **+1 byte em todos os regimes e não entrega otimização**, e a célula `int+spec` **não existe em nenhuma das 3 rotas** (`nature` recusa entrada tipada). O **bool** já faz o que falta ao int — é o modelo pronto. **+correção pega pelo owner**: o wire de 26 B do `gigante-64bit` omitia a base de 19 dígitos (o mesmo wire decodifica para dois resultados sem erro) — separa spec **auto-contido** (PAD, B94, e todos os soldados) de **parametrizado** (OFFPAD, que quebra o self-describing do ADR-0027) |
| **Um spec de INTEIRO faz sentido?** (lab, ritual clássico, 2026-08-13) | `experiments/lab/dirty/2026-08/2026-08-13/2026-08-13-2258-int-spec-faz-sentido/` — **sim, em três regimes nomeáveis**, e nenhum alvo é ideia nova: PAD (do IP) 1,38–1,78×, OFFPAD (do ordinal de data) **2,50–2,79×**, B94 (do CPF) 1,31–1,52×. **9 dos 16 casos são recusa correta** — incluindo a armadilha `000001` ≠ `1`. 0 falhas de RT, 16 pins verdes. Falta medir a frequência dos gatilhos em corpus real antes de soldar |
| **Ciclo: a coluna primeiro, M/H como consequência** (correção do owner, 2026-08-13) | `experiments/lab/dirty/notas/2026-08/2026-08-13-2115-ciclo-ordem-coluna-antes-de-MH.md` — **a tese "atender a coluna e o resto é consequência" foi VERIFICADA**: um spec novo atravessa single e multi sem tocar em M. Minha proposta de otimizar M/H antes **aumentaria a solda dupla** (candidatos de single e multi são quase disjuntos). A ordem do owner — tipos → caminho único → M/H — está certa |
| **Próximo tipo e ordem por ROI** (levantamento medido, 2026-08-13) | `experiments/lab/dirty/notas/2026-08/2026-08-13-2030-proximo-tipo-e-ordem-por-roi.md` — **data está fechada** (com spec, varrer `min_len` rende 0,2%; sem spec rendia 1,19-1,39×, e essa era a medição errada). A oportunidade maior **não** é o próximo tipo: é **baixa cardinalidade dentro de M/H** — bool nativo custa **12,8×** mais dentro de tabela que sozinho, e o mecanismo denso já existe soldado. Recomendação: M/H antes de número |
| **Auditoria: o núcleo suporta streaming?** (4 lentes sobre o código, 2026-08-13) | `experiments/lab/dirty/notas/2026-08/2026-08-13-1900-auditoria-streaming-do-nucleo.md` — o critério do owner ("só falha se tiver algo no final") **já está soldado** em `encoder.py:484-489` (o modo bN `C` é 1 B menor e foi recusado por não streamar). O wire permite prefixo; o `decode()` é que recusa. **Armadilha verificada**: concatenar corpos independentes na rota core corrompe calado (299/600 errados) — cortar um wire pronto é seguro |
| **Entrega incremental do núcleo — o que já sai em pedaços** (modelo de streaming do owner, 2026-08-13) | `experiments/lab/dirty/2026-08/2026-08-13/2026-08-13-1820-entrega-incremental-do-nucleo/` — o wire encodado UMA vez, entregue em prefixos de linhas: **nada fica no final** (dicionário do bN vem na frente, referências `^1` apontam pra trás), mas a granularidade varia de **1 a 5 pontos de entrega** conforme o mecanismo. Booleano em blocos entrega 200/400/600 de graça; data com spec colapsa em 1 linha e não dá meio-caminho |
| **Latência é o eixo; o período é acessório** (correção do owner, 2026-08-13) | `experiments/lab/dirty/2026-08/2026-08-13/2026-08-13-1740-latencia-como-eixo/` — **refuta** um registro meu anterior ("um modo de baixa latência não pode cortar em qualquer lugar": 40 de 40 cortes fora de fase são legais). Régua medida: o custo de fatiar não é propriedade da data (a mesma coluna custa 2,69× sem spec e 16,46× com), e sim **de onde vem a compressão** — ganho global morre no corte, local se reconstrói. Fatia ∈ **[piso, teto]**: piso = menor slice que mantém o mecanismo (100 valores p/ data diária), teto = o que cabe no deadline (200 ms = 1.425 a 13.428 valores conforme o tipo) |
| **Inspeção do tipo DATA — o wire aberto e explicado** (demonstração pedida pelo owner, 2026-08-13) | `experiments/lab/dirty/2026-08/2026-08-13/2026-08-13-1650-inspecao-data-estado-atual/` — 29 casos, 0 falhas de RT; cada wire DECOMPOSTO em `intermediates/<c>.anatomia.txt` (header, marcadores, âncora). Cobre as 4 modificações acumuladas no tipo data: spec ordinal · seq-RLE periódico · fix do view · `wire_id` curto. Corpus real: spec vence em **9 de 12** colunas (−24,8%); as 3 restantes **não são `YYYY-MM-DD`** (`YYYYMMDD` e datetime) — o spec nem se aplica |
| **Spec em três planos** (ADR-0041: `name` de código × `wire_id` de dado × o carimbo) | `docs/adr/0041-spec-id-tres-planos.md` — o **comprimento do id FLIPA o FLOOR** (em N≥11 o nome longo suprime a própria nature); regra `^[a-z][a-z0-9]{0,7}$` fail-loud; a resolução passa a comparar `wire_id`; **modo sem-carimbo** 32→15 B (hoje quebrado nas duas pontas). Mapa de ids = escolha **revisável até o 1.0**; a estrutura é o que congela. **Weld A soldado 2026-08-13** (`:dt` no wire; suite 1247) |
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
| **CNPJ alfanumérico (IN 2.229/2024, vigente) — o split morre em k=1; a nature é plana** (letra é número por DOIS mapeamentos: legal ASCII−48 c/ gap → só DV; denso 0–35 → base, 10 chars não 11; dois wire_ids `cnpj`/`cnpja`) | `experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0030-cnpj-alfa-controle/` — controle n=2000 real + k injetados; máquina real roda o spec via subclasse+`nature=` sem tocar src; weld = 3 métodos com `\d` + registry. Descoberta: `2026-08-20/2026-08-20-2350-cnpj-alfanumerico/` (split −38%→core/raw; posicional bate split até no numérico; placa Mercosul = lacuna preexistente). Registro: Pacote 15 |
| **Nome vazio `''` no `.8M`** (era o único caso em que o TCF alterava o dado; agora `\z`, espelho do `.8H`) | [`docs/adr/0046`](docs/adr/0046-nome-vazio-8m-porta-o-z-do-8h.md) + lab `2026-08-21-0900-chave-vazia-posicional/` — definição superada (07-10 → 07-17), não bug; causa = colisão de grafia com `drop_names`; o `\z` é o de ADR-0033, não re-derivado |
| **As 4 camadas do wire** (entrada · roundtrip · arquivo · transporte) — e o que cada uma pode omitir | `experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0600-quatro-camadas/` — o omissível do transporte é o **cabeçalho (7–8 B, 22–71% do wire pequeno)**, não o LF (1 B); `drop_names` já é o 1º membro da família; transformações são funções puras sobre o wire (0 linha de encode/decode tocada). Teto, não ganho líquido: só compensa amortizado |
| **CNPJ: um `cnpj` SÓ** (alfa é o padrão; numérico é caso dele, 7 chars byte-idênticos ao wire histórico; sem segundo spec, sem chooser) | [`docs/adr/0044`](docs/adr/0044-cnpj-um-so-alfanumerico.md) + lab `2026-08-21-0230-cnpj-unificado/` — o compacto é **load-bearing** (sem ele o `:cnpj` legado corrompe em silêncio), não otimização; ganho decai +27,6%→0% sem nunca ficar negativo |
| **Performance do `.8` — o baseline pinado, e onde o tempo REALMENTE vai** (o canto R×C **não** é penhasco: 80× de células por 75× de tempo; o eixo quente é **cardinalidade**) | `experiments/lab/dirty/2026-08/2026-08-20/2026-08-20-2330-baseline-perf-08-probatoria/` — rodada probatória `6f04f3ae`; modelo `t = a·células + b·bytes + c·únicos` com R²=0,9996 e **c ≈ 3,7× a**; encode custa **10–59×** o `json.dumps` emitindo **12% dos bytes**. Instrumento: os calibradores **super-corrigem +16,6%** (a stdlib é o controle). Snapshot: `experiments/results/evidencia-0.8/perf-baseline/` |
| Entender uma decisao tomada | `docs/adr/` (numerada) ou `experiments/lab/dirty/notas/diario/` |
| Continuar um sub-experimento | `experiments/lab/dirty/<YYYY-MM>/<YYYY-MM-DD>/<lab>/<sub-exp>/README.md` |
| Comparar EXP-010 ao baseline | `experiments/lab/clean/EXP-010-*/report.md` |
| Format do .tcf | `docs/algorithms/TCF-format.md` |
| Convencao de header | `docs/algorithms/TCF-format.{pt-BR,en}.md` (#TCF.8 default — carimbo em 100% do single-col, ADR-0034; discriminador de **9 valores**: `\n M H` espaço `b n s B C`, com `s`/`C` decode-only; hex, escaping) + ADRs (0029/0031/0032/0033/0034/0036) + **registry de chars** `experiments/lab/dirty/notas/2026-07/tcf8-header-char-registry.md` |
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

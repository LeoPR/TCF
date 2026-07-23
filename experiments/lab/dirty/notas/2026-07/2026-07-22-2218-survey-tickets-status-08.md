# Survey de tickets + estado do closeout do #TCF.8 — 2026-07-22 [referência]

**Data**: 2026-07-22 22:18. Snapshot de status dos 82 tickets (survey automatizado, 14 readers) +
reconciliação do [`T-REL-08-CLOSEOUT`](../../../../../tickets/T-REL-08-CLOSEOUT.md) com o estado
atual (feature-complete 2026-07-17, suíte ~853). Fonte viva = os próprios tickets; isto é foto datada.

## Panorama

**82 tickets** — status: 50 fechado · 19 aberto · 6 adiado · 3 parcial · 3 em-andamento · 1 superseded.
Escopo: 22 0.8 · 16 research · 14 infra · 12 0.9 · 10 meta · 5 2.0 · 3 1.0.

## Estado do closeout do `.8` (T-REL-08-CLOSEOUT, reconciliado)

O `.8` é **feature-complete** (reescopo 2026-07-13: `.8` = "o 1.0 com tudo que funciona"). Os dois
pré-requisitos de capacidade estão FECHADOS: TCF.8H welded + contratos de borda JSON congelados
(2026-07-17). **Não há feature pendente.** O que resta é a fila de release por ROI:

| passo | o que é | estado |
|---|---|---|
| R0 — integridade | BUG-14 (decoder LF-only + gates canônicos) | ✅ FEITO |
| F1 (2a) | runner de telemetria (`bench_evidencia.py` + probes portáveis) | ✅ FEITO |
| F2 (2b) | 29 casos RT controle (`evidencia-0.8/f2/`) | ✅ FEITO |
| F3 (2c) | sintéticos + curva de escala (amostral; população → janela pós-release) | ~ AMOSTRAL |
| F4-mínimo (2d) | 9 casos nos hubs reais (RT 9/9); **achado**: nature CNPJ PIORA em receita real | ~ FEITO (mínimo) |
| **perf-baseline** | grandeza + hot-spots + escala (linear O(n); penhasco cantoRC 75x) — 2026-07-22 | ✅ FEITO (novo; alimenta F6) |
| **F5 (2e)** | otimização extra | ⏸ NO-ACTION (default; só se telemetria apontar blocker) |
| **F6 (2f)** | **README EN/PT com números MEDIDOS** (embarca na wheel; hoje mostra 0.7.1/#TCF.7 stale) + re-build wheel + clean-room smoke | ⬜ PENDENTE |
| **C3 (2g)** | bump 0.7.1→0.8.0 + CHANGELOG + tag v0.8.0 + Trusted Publishing | ⬜ PENDENTE (GO do owner) |

**Buraco real do `.8` = F6 (docs+wheel+smoke) + C3 (publicar).** Zero feature. F5 é NO-ACTION.
O perf-baseline recém-registrado fornece parte dos números medidos que o F6/DOC-01 pede.

Caveat obrigatório do F6 (do F4): **nunca claimar nature CNPJ como ganho em dado real** — piora +7339B
na receita real (split→raw), só ajuda no sintético. Reforça a Opção A do T-SPEC-STATUS-08.

## Abertos/pendentes por escopo (32)

### `0.8` (8)
- **T-CODE-TCF8H-JSON-PARITY** [aberto] ★v1 — Fechar paridade JSON do codec hierárquico .8H (RT lossless de JSON real); escalares+estrutura+raiz (P1/P2/P3/P4a/P4b) WELDED e D_json completo, P5/union ratificado fora do .8; aberto: suíte de corpus real, congelar contratos de borda (pré-1.0) e capacidade exclusiva shared-ref/grafo (diferenciação pós-paridade).
- **T-CODE-TCF8H-WELD** [aberto] — Weld do codec hierárquico #TCF.8H em src/tcf como feature do .8 (gate de capacidade, não de compressão); codec welded (W0-W5 feitos, ADR-0033, src/tcf aprovado arquivo-a-arquivo, flat byte-idêntico, fuzz 8000/8000); resta o teste em massa via shaper, declarado explicitamente como não-bloqueante do .8.
- **T-DIST-RELEASE-0.8.0** [aberto] ⛔REL — Ticket do release do pacote 0.8.0 (#TCF.8 default por ADR-0032); open e bloqueado por T-REL-08-CLOSEOUT — bump de versao/CHANGELOG/suite/smoke local ja' prontos, mas faltam BUG-14 + F3/F4/F6 e a tag v0.8.0 depende de go explicito do owner (PyPI segura em 0.7.1).
- **T-FMT-NAME-ESCAPING** [parcial] — Escape de nomes no meta: interim backslash (escapa ,=:\ + prefixo !@% inicial, split em separador nao-escapado) WELDED como entrega do .8, desbloqueou o :-no-.8-default (RT exato, 530 passed, byte-neutro), endurecido no F0; ENCERRADO PARCIAL — estudo smart (quoting-implicito vs escape-por-char) + cobertura de chars de hierarquia {}[] movidos ao ticket-filho T-FMT-QUOTING-STUDY (alvo .9).
- **T-QA-8-material-comprobatorio** [aberto] ⛔REL — Material comprobatório do 0.8.0 (telemetria portável, 3 dicts welded, paralelismo, datasets) em 6 fases; F0-F4 feitos (F3/F4 amostrais), 16 bugs registrados/quase todos fixados exceto BUG-12, F5(NO-ACTION)/F6(pacote+doc/wheel/publish) pendentes; status open.
- **T-REL-08-CLOSEOUT** [aberto] ⛔REL — Ticket-guia da ordem por ROI (R0-R3) pra fechar o núcleo #TCF.8 e publicar 0.8.0; reescopo 2026-07-13 = .8 é feature-complete (TCF.8H + boundary-contracts FECHADOS), R0/F1/F2/F4-mínimo feitos e F3 amostral, restam F6(docs+wheel) e C3(publish/go do owner); status open.
- **T-SPEC-DEEPDIVE-08** [aberto] ★v1 — Investigacao de fundo dos specs (o que comprime, CNPJ alem do basico, nature-delta/field-split, compilador un-weld); aberto — o FLOOR nature-compete ja foi welded no .8 (F4 resolvido, 634 passed), restam caveat obrigatorio do F6 e direcoes CNPJ registradas p/ .9/pre-1.0.
- **T-SPEC-STATUS-08** [em-andamento] — Status dos specs e decisao do que fecha no .8 (Opcao A decidida: so CPF/CNPJ welded, nenhum spec novo; classicos BR e DateSpec ISO registrados p/ .9); in-progress apos revisao cadastral — pendente o caveat obrigatorio do F6 (nature CNPJ piora a tabela em dado real).

### `0.9` (6)
- **META-PERF-PHASE2** [parcial] — Meta-ticket de perf fase 2 (OBAT/HCC): sub-pacote 1 (hash trigrama, ADR-0009) welded com 2.70x, sub-pacotes 2/3/4 (H-PERF-04/05/06) adiados com justificativa; CLOSED-PARCIAL 2026-05-20, so criterio 'atualizar STATUS.md' aberto.
- **T-CODE-CORE-CONSOLIDATE** [aberto] ★v1 — Consolidacao do core (fonte unica de logica anti-BUG-14, rename M8A->HCC, achatar decode de 2 passadas): open/P1, C0 (dedup D1-D3) feito byte-neutro 2026-07-12; C1/C2/C3 sao ciclo pos-release 0.8.x rumo ao port Rust do 1.0 — nao bloqueia publicar o 0.8.
- **T-CODE-DESCAPAR-V2B** [parcial] — Descapar o cap do dict V2-B pra ele entrar no min() em high-card espalhado; forma A (cap _V2B_MAX_CARD 1024->8192) WELDED no .8 byte-safe sem re-pin (gate verde), formas B (descapar+skip cadence-aware) e C (descapar puro) DEFERIDAS ao .9 (ROADMAP Tier 1). Estado: parcial.
- **T-CODE-PARALLEL-BUDGET** [aberto] — Registro (dispositivo->registro) de flag p/ controlar paralelismo/uso de CPU: env TCF_MAX_WORKERS como teto do host, parallel=True mais educado (cpu_count-1), telemetria workers pedidos vs concedidos — aberto, design decidido pos-F3 (medir speedup antes), doc pos-.8/F6; knob de host, bytes sempre identicos.
- **T-FMT-ESCAPE-COMBINATORIAL-STUDY** [aberto] ★v1 — Estudo do escape: matriz combinatoria char×posicao×contexto (onde o backslash quebra/custo) + benchmark vs >=3 mecanismos de armazenamento (escape in-band vs length-prefix); ABERTO, SO REGISTRAR (escaping .8M/.8H fica como esta), gate .9/pre-1.0; recomendacao pode manter backslash ou mudar wire (re-pin ADR-0024 + toca freeze pre-1.0 dos contratos de borda).
- **T-FMT-QUOTING-STUDY** [aberto] — Estudo (gate .9) de quoting/escaping de nomes alem do backslash interim do .8 — barra vs CSV-quote vs smart-quote, pressionado pelas chaves {}[] da hierarquia; aberto, primeiro passo e medir frequencia de nomes 'sujos' em headers reais pra decidir se avanca.

### `1.0` (3)
- **T-FMT-META-STRICT** [aberto] ★v1 — Integridade do meta por deducao do canone (so aceita o que o encoder emite, zero bytes novos); lotes 1-4 welded (F0, 590 passed), ABERTO; residuais deferidos e vinculados — checksum (fusao geom. consistente) -> trilho tcfx/O-FMT-20, BUG-12 hang HCC -> 0.8.1, item 8 orcamento defensivo de expansao -> ticket proprio pre-1.0, KeyError cru em ref inexistente de blob estrangeiro -> re-tipar quando owner aprovar mexer no decode flat.
- **T-FMT-OMIT-OR-DECLARE** [aberto] ★v1 — Contrato de o-que-pode-ser-omitido vs o-que-vira-declaracao-obrigatoria em 4 categorias (sempre-presente/deduzivel/convencao-default/supressivel-c-declaracao) com invariantes fail-loud e proveniencia; aberto, frontmatter gate=pre-1.0, criterios de aceite ainda por classificar/especificar antes do freeze 1.0.
- **T-OPT-INFERENCE** [aberto] ★v1 — Classe de otimizacoes por inferencia/deducao (valor deduzido, nao escrito) — hex-default dos byte-sizes, framework specs-induzidas-por-round-trip, bitwidth bN; aberto, Item 1 (hex) ja desmembrado p/ T-FMT-HEADER-BASE-HEX (decided-weld-gated), bN NAO e weld-candidate (colapsa pos-brotli), restante e decisao de formato pre-1.0.

### `2.0` (3)
- **META-TYPE-ENCODERS** [adiado] — Meta-plano de pre-tx por natureza (8 naturezas T01-T07 + estudos L01-L06); T01 absorvido no Pacote 1 (welded), resto PARKED pos-0.7 rumo a v2.0 aguardando evidencia real-world (T-DATA-1).
- **T-CODE-OUTPUT-SINKS** [adiado] — Interface Sink pluggable (File/MultiFile/Memory + streaming HTTP/TCP + side-output sinks; refactor de scripts/writers) — status deferred, PARK v2.0, bloqueado pela Fase 2 do T-CODE-ENCODER-MANAGER; infra pos-1.0, sem plano executado.
- **T-CODE-PLAN-CONTRACT** [adiado] — Contrato Plan (group_by/order/batch_size) para ordering reversível (O-FMT-01..04) + futuro SQL->Plan; deferred e parkeado explicitamente para v2.0, não crítico ao release (sort_by welded já cobre reordenação simples).

### `infra` (3)
- **T-SHAPER-CODE-HARDENING** [adiado] — Hardening do codigo do shaper (5+ acoes A1-A6: escala filter-before-load, bug lstrip, dedup, ImportError silencioso, lazy-load fragil); deferred/parked pos-0.7 com reabertura parcial so do A1, condicionada ao tier XL de transmissao — gadget externo, nao TCF-core.
- **T-SHAPER-NESTED-OUTPUT** [aberto] ★v1 — Saida hierarquica nativa no Shaper (aninhar via FK, inverso do flat) para eliminar o aninhamento manual dos labs; aberto, ferramental a deixar bem feito ate 1.0, so esboco de design — nao bloqueia .8, implementacao adiada.
- **T-TOOL-TCF-FIX-CORRUPTION** [aberto] — Ideia registrada (dispositivo->registro) de ferramenta/gadget fora do src/tcf p/ recuperar .tcf corrompido consumindo os ganchos fail-loud do decode; saída = relatório + blob-candidato auditável, nunca sobrescreve; explicitamente fora do escopo .8, a priorizar após a publicação 0.8.

### `meta` (2)
- **META-STRATA-GOVERNANCE** [aberto] — Ticket de cadencia para governanca recorrente do metodo Strata (G-1 maturacao de itens, G-2 rotulo dispositivo/probatorio, G-3 re-verify camada ferramentas, G-4 auditoria 60-90d); status open como lembrete vivo, janelas ago-set/2026.
- **T-DOC-3-shebang-terminology** [aberto] — Termo canonico 'assinatura de formato / magic number' ja setado em vocabulary.md, ADR-0001 e spec; prosa viva sincronizada. Historico NAO se corrige (Strata §3); fica aberto so como LEMBRETE de errata, nao backlog acionavel.

### `research` (6)
- **T-DATA-3-EDGE-QUALITY-FIXTURES** [adiado] — Plano (deferred) de fixtures de dados de borda/defeituosos para testar os gadgets de qualidade/schema que so' alertam e nunca arrumam; catalogo de 11 classes de defeito pronto mas bloqueado por T-RECOVER-SCHEMA-MULTI-TABLE (gadget ainda nao existe).
- **T-FLOW-ENCODE-STRATEGIES-TELEMETRY** [aberto] — Vetor speed/mem ortogonal a bytes: 3 estrategias de encode (S1 default streaming / S2 reorder-at-encode opt-in medido caro / S3 telemetria offline sugestiva amortizada) + gadget que le SideOutputs e sugere/avisa ordem otima; ABERTO, so registrado, prototipo e medicao de S2 pendentes; gadget paralelo, nao toca src/tcf no hot-path.
- **T-RECOVER-LLM-SCHEMA-MODE** [adiado] — Gadget externo LLM (coleta schema → formato 'LLM-binary' → gera/executa SQL → dado pro TCF); só planejado, nada implementado, PARK/spin-off pós-0.7 (Opção A pacote separado); status deferred, não toca src/tcf nem bloqueia roadmap.
- **T-STUDY-DATASETH-COMPLETE-SEMANTICS** [em-andamento] ★v1 — Estudo (dispositivo->pesquisa, zero src/tcf) que fecha a semântica hierárquica JSON/DatasetH via codec-oráculo preorder antes do wire; S0-S1 feitos (20/20 RT, 8/8 fail-loud, confirmada-conceitual), aberto p/ corpus realista, política numérica pública e integração.
- **T-STUDY-HIERARCHICAL-TCF** [aberto] ★v1 — Guarda-chuva probatório da hierarquia completa em TCF (JSON=1a fonte, DatasetH independente da fonte); feasibility MEDIDA P1-P9 (RT OK, confirmada-conceitual, nada em src/tcf); hierarquia promovida ao .8 mas o weld em src/tcf foi delegado a ticket separado (T-CODE-TCF8H-WELD); inclui trilha futura P10-P11.
- **T-STUDY-HIERARCHY-LINK-ALGEBRA** [em-andamento] ★v1 — Estudo que trata header/busca/estrutura como planos físicos sobre um IR único e prova equivalência counts<->offsets<->parent_index<->steps + insuficiência do bit first-child; S2-S3 feitos (20/20, contraprova de pai vazio), S4-S7 (wires/custos/default/weld) pendentes; confirmada-conceitual.

## Candidatos a `v1.0` (marcados no survey)

- **T-CODE-TCF8H-JSON-PARITY** (0.8) — Fechar paridade JSON do codec hierárquico .8H (RT lossless de JSON real); escalares+estrutura+raiz (P1/P2/P3/P4a/P4b) WELDED e D_json completo, P5/union ratificado fora do .8; aberto: suíte de corpus real, congelar contratos de borda (pré-1.0) e capacidade exclusiva shared-ref/grafo (diferenciação pós-paridade).
- **T-SPEC-DEEPDIVE-08** (0.8) — Investigacao de fundo dos specs (o que comprime, CNPJ alem do basico, nature-delta/field-split, compilador un-weld); aberto — o FLOOR nature-compete ja foi welded no .8 (F4 resolvido, 634 passed), restam caveat obrigatorio do F6 e direcoes CNPJ registradas p/ .9/pre-1.0.
- **T-CODE-CORE-CONSOLIDATE** (0.9) — Consolidacao do core (fonte unica de logica anti-BUG-14, rename M8A->HCC, achatar decode de 2 passadas): open/P1, C0 (dedup D1-D3) feito byte-neutro 2026-07-12; C1/C2/C3 sao ciclo pos-release 0.8.x rumo ao port Rust do 1.0 — nao bloqueia publicar o 0.8.
- **T-FMT-ESCAPE-COMBINATORIAL-STUDY** (0.9) — Estudo do escape: matriz combinatoria char×posicao×contexto (onde o backslash quebra/custo) + benchmark vs >=3 mecanismos de armazenamento (escape in-band vs length-prefix); ABERTO, SO REGISTRAR (escaping .8M/.8H fica como esta), gate .9/pre-1.0; recomendacao pode manter backslash ou mudar wire (re-pin ADR-0024 + toca freeze pre-1.0 dos contratos de borda).
- **T-FMT-META-STRICT** (1.0) — Integridade do meta por deducao do canone (so aceita o que o encoder emite, zero bytes novos); lotes 1-4 welded (F0, 590 passed), ABERTO; residuais deferidos e vinculados — checksum (fusao geom. consistente) -> trilho tcfx/O-FMT-20, BUG-12 hang HCC -> 0.8.1, item 8 orcamento defensivo de expansao -> ticket proprio pre-1.0, KeyError cru em ref inexistente de blob estrangeiro -> re-tipar quando owner aprovar mexer no decode flat.
- **T-FMT-OMIT-OR-DECLARE** (1.0) — Contrato de o-que-pode-ser-omitido vs o-que-vira-declaracao-obrigatoria em 4 categorias (sempre-presente/deduzivel/convencao-default/supressivel-c-declaracao) com invariantes fail-loud e proveniencia; aberto, frontmatter gate=pre-1.0, criterios de aceite ainda por classificar/especificar antes do freeze 1.0.
- **T-OPT-INFERENCE** (1.0) — Classe de otimizacoes por inferencia/deducao (valor deduzido, nao escrito) — hex-default dos byte-sizes, framework specs-induzidas-por-round-trip, bitwidth bN; aberto, Item 1 (hex) ja desmembrado p/ T-FMT-HEADER-BASE-HEX (decided-weld-gated), bN NAO e weld-candidate (colapsa pos-brotli), restante e decisao de formato pre-1.0.
- **T-SHAPER-NESTED-OUTPUT** (infra) — Saida hierarquica nativa no Shaper (aninhar via FK, inverso do flat) para eliminar o aninhamento manual dos labs; aberto, ferramental a deixar bem feito ate 1.0, so esboco de design — nao bloqueia .8, implementacao adiada.
- **T-STUDY-DATASETH-COMPLETE-SEMANTICS** (research) — Estudo (dispositivo->pesquisa, zero src/tcf) que fecha a semântica hierárquica JSON/DatasetH via codec-oráculo preorder antes do wire; S0-S1 feitos (20/20 RT, 8/8 fail-loud, confirmada-conceitual), aberto p/ corpus realista, política numérica pública e integração.
- **T-STUDY-HIERARCHICAL-TCF** (research) — Guarda-chuva probatório da hierarquia completa em TCF (JSON=1a fonte, DatasetH independente da fonte); feasibility MEDIDA P1-P9 (RT OK, confirmada-conceitual, nada em src/tcf); hierarquia promovida ao .8 mas o weld em src/tcf foi delegado a ticket separado (T-CODE-TCF8H-WELD); inclui trilha futura P10-P11.
- **T-STUDY-HIERARCHY-LINK-ALGEBRA** (research) — Estudo que trata header/busca/estrutura como planos físicos sobre um IR único e prova equivalência counts<->offsets<->parent_index<->steps + insuficiência do bit first-child; S2-S3 feitos (20/20, contraprova de pai vazio), S4-S7 (wires/custos/default/weld) pendentes; confirmada-conceitual.

## Índice completo dos 82 (referência)

| id | status | escopo | resumo |
|---|---|---|---|
| T-CODE-TCF8H-JSON-PARITY | aberto | 0.8 | Fechar paridade JSON do codec hierárquico .8H (RT lossless de JSON real); escalares+estrutura+raiz (P1/P2/P3/P4a/P4b) WELDED e D_json comple |
| T-CODE-TCF8H-WELD | aberto | 0.8 | Weld do codec hierárquico #TCF.8H em src/tcf como feature do .8 (gate de capacidade, não de compressão); codec welded (W0-W5 feitos, ADR-003 |
| T-DIST-RELEASE-0.8.0 | aberto | 0.8 | Ticket do release do pacote 0.8.0 (#TCF.8 default por ADR-0032); open e bloqueado por T-REL-08-CLOSEOUT — bump de versao/CHANGELOG/suite/smo |
| T-FMT-NAME-ESCAPING | parcial | 0.8 | Escape de nomes no meta: interim backslash (escapa ,=:\ + prefixo !@% inicial, split em separador nao-escapado) WELDED como entrega do .8, d |
| T-QA-8-material-comprobatorio | aberto | 0.8 | Material comprobatório do 0.8.0 (telemetria portável, 3 dicts welded, paralelismo, datasets) em 6 fases; F0-F4 feitos (F3/F4 amostrais), 16  |
| T-REL-08-CLOSEOUT | aberto | 0.8 | Ticket-guia da ordem por ROI (R0-R3) pra fechar o núcleo #TCF.8 e publicar 0.8.0; reescopo 2026-07-13 = .8 é feature-complete (TCF.8H + boun |
| T-SPEC-DEEPDIVE-08 | aberto | 0.8 | Investigacao de fundo dos specs (o que comprime, CNPJ alem do basico, nature-delta/field-split, compilador un-weld); aberto — o FLOOR nature |
| T-SPEC-STATUS-08 | em-andamento | 0.8 | Status dos specs e decisao do que fecha no .8 (Opcao A decidida: so CPF/CNPJ welded, nenhum spec novo; classicos BR e DateSpec ISO registrad |
| META-PERF-PHASE2 | parcial | 0.9 | Meta-ticket de perf fase 2 (OBAT/HCC): sub-pacote 1 (hash trigrama, ADR-0009) welded com 2.70x, sub-pacotes 2/3/4 (H-PERF-04/05/06) adiados  |
| T-CODE-CORE-CONSOLIDATE | aberto | 0.9 | Consolidacao do core (fonte unica de logica anti-BUG-14, rename M8A->HCC, achatar decode de 2 passadas): open/P1, C0 (dedup D1-D3) feito byt |
| T-CODE-DESCAPAR-V2B | parcial | 0.9 | Descapar o cap do dict V2-B pra ele entrar no min() em high-card espalhado; forma A (cap _V2B_MAX_CARD 1024->8192) WELDED no .8 byte-safe se |
| T-CODE-PARALLEL-BUDGET | aberto | 0.9 | Registro (dispositivo->registro) de flag p/ controlar paralelismo/uso de CPU: env TCF_MAX_WORKERS como teto do host, parallel=True mais educ |
| T-FMT-ESCAPE-COMBINATORIAL-STUDY | aberto | 0.9 | Estudo do escape: matriz combinatoria char×posicao×contexto (onde o backslash quebra/custo) + benchmark vs >=3 mecanismos de armazenamento ( |
| T-FMT-QUOTING-STUDY | aberto | 0.9 | Estudo (gate .9) de quoting/escaping de nomes alem do backslash interim do .8 — barra vs CSV-quote vs smart-quote, pressionado pelas chaves  |
| T-FMT-META-STRICT | aberto | 1.0 | Integridade do meta por deducao do canone (so aceita o que o encoder emite, zero bytes novos); lotes 1-4 welded (F0, 590 passed), ABERTO; re |
| T-FMT-OMIT-OR-DECLARE | aberto | 1.0 | Contrato de o-que-pode-ser-omitido vs o-que-vira-declaracao-obrigatoria em 4 categorias (sempre-presente/deduzivel/convencao-default/supress |
| T-OPT-INFERENCE | aberto | 1.0 | Classe de otimizacoes por inferencia/deducao (valor deduzido, nao escrito) — hex-default dos byte-sizes, framework specs-induzidas-por-round |
| META-TYPE-ENCODERS | adiado | 2.0 | Meta-plano de pre-tx por natureza (8 naturezas T01-T07 + estudos L01-L06); T01 absorvido no Pacote 1 (welded), resto PARKED pos-0.7 rumo a v |
| T-CODE-OUTPUT-SINKS | adiado | 2.0 | Interface Sink pluggable (File/MultiFile/Memory + streaming HTTP/TCP + side-output sinks; refactor de scripts/writers) — status deferred, PA |
| T-CODE-PLAN-CONTRACT | adiado | 2.0 | Contrato Plan (group_by/order/batch_size) para ordering reversível (O-FMT-01..04) + futuro SQL->Plan; deferred e parkeado explicitamente par |
| T-SHAPER-CODE-HARDENING | adiado | infra | Hardening do codigo do shaper (5+ acoes A1-A6: escala filter-before-load, bug lstrip, dedup, ImportError silencioso, lazy-load fragil); defe |
| T-SHAPER-NESTED-OUTPUT | aberto | infra | Saida hierarquica nativa no Shaper (aninhar via FK, inverso do flat) para eliminar o aninhamento manual dos labs; aberto, ferramental a deix |
| T-TOOL-TCF-FIX-CORRUPTION | aberto | infra | Ideia registrada (dispositivo->registro) de ferramenta/gadget fora do src/tcf p/ recuperar .tcf corrompido consumindo os ganchos fail-loud d |
| META-STRATA-GOVERNANCE | aberto | meta | Ticket de cadencia para governanca recorrente do metodo Strata (G-1 maturacao de itens, G-2 rotulo dispositivo/probatorio, G-3 re-verify cam |
| T-DOC-3-shebang-terminology | aberto | meta | Termo canonico 'assinatura de formato / magic number' ja setado em vocabulary.md, ADR-0001 e spec; prosa viva sincronizada. Historico NAO se |
| T-DATA-3-EDGE-QUALITY-FIXTURES | adiado | research | Plano (deferred) de fixtures de dados de borda/defeituosos para testar os gadgets de qualidade/schema que so' alertam e nunca arrumam; catal |
| T-FLOW-ENCODE-STRATEGIES-TELEMETRY | aberto | research | Vetor speed/mem ortogonal a bytes: 3 estrategias de encode (S1 default streaming / S2 reorder-at-encode opt-in medido caro / S3 telemetria o |
| T-RECOVER-LLM-SCHEMA-MODE | adiado | research | Gadget externo LLM (coleta schema → formato 'LLM-binary' → gera/executa SQL → dado pro TCF); só planejado, nada implementado, PARK/spin-off  |
| T-STUDY-DATASETH-COMPLETE-SEMANTICS | em-andamento | research | Estudo (dispositivo->pesquisa, zero src/tcf) que fecha a semântica hierárquica JSON/DatasetH via codec-oráculo preorder antes do wire; S0-S1 |
| T-STUDY-HIERARCHICAL-TCF | aberto | research | Guarda-chuva probatório da hierarquia completa em TCF (JSON=1a fonte, DatasetH independente da fonte); feasibility MEDIDA P1-P9 (RT OK, conf |
| T-STUDY-HIERARCHY-LINK-ALGEBRA | em-andamento | research | Estudo que trata header/busca/estrutura como planos físicos sobre um IR único e prova equivalência counts<->offsets<->parent_index<->steps + |
| BUG-BRACKET-CELL-LOSS | fechado | 0.8 | Bug R0 de corrupção silenciosa: célula/linha string igual a '[' ou ']' era descartada no round-trip do codec plano (reusado pelo .8H); fecha |
| BUG-SEQRLE-RANGE-EMPTY-B | fechado | 0.8 | Bug R0: colisão do range seq-RLE 'A..B' com sufixo literal '..'/'...' em afixo crashava o round-trip (int('')); fechado 2026-07-17 com separ |
| T-API-BOUNDARY-CONTRACTS | fechado | 0.8 | Contrato de borda flat/DatasetH: isola fail-louds/conversoes do lote 3 num ponto unico; passada de congelamento .8 feita 2026-07-17 (todas M |
| T-CODE-EMPTY-FRAG-INDEX-RT | fechado | 0.8 | Bug de correcao no core M10 — string vazia deslocava o index de fragmento HCC (off-by-one) causando corrupcao silenciosa e crash violando de |
| T-CODE-HCC-ATOM-DETECTION-REFINE | superseded | 0.8 | Bug #1 do sub-exp 14 — detector de composicao HCC greedy nao cria atom secundario pra prefixo repetido apos criar o atom primario (cross-sub |
| T-CODE-HCC-MULTI-DELTA-FIX | fechado | 0.8 | Bug #2 do sub-exp 14 — compare_for_seq rejeitava pares com delta multi-run {0,0,0,1} exigindo uniformidade absoluta; fix (Opcao A, CSV *N+d1 |
| T-CODE-LAZY-VIEW-PROMOTE | fechado | 0.8 | Moveu a lazy view (scripts/tcf_lazy/lazy.py -> src/tcf/view.py, read-only: LazyTCF/Filtered/view) pro core p/ shipar no wheel — escopo centr |
| T-CODE-PACOTE1-WELD-CANONICAL | fechado | 0.8 | Weldou o pipeline delta-aware do Pacote 1 (auto_cadence + obat_shape + HCC seq-RLE / M9->M10) como canonical em src/tcf; closed com resoluti |
| T-CODE-RT-EDGES | fechado | 0.8 | Duas violações do contrato lossless em bordas (seq-RLE come whitespace final; \n embutido corrompe RT silenciosamente); ambas corrigidas e f |
| T-CODE-SCHEMA-BUILDER | fechado | 0.8 | Orquestrador build_schema que consome SideOutputs e produz TableSchema/ColumnSchema; Fases 1+2 welded e fechadas (escopo 0.7, 24/24 testes,  |
| T-DOC-LAZY-REFERENCE | fechado | 0.8 | docs/reference/lazy-view.md escrito cobrindo a superficie de tcf.view (estavel L1-L4 vs experimental group_ranges/agg_by/L5), exemplos ancor |
| T-EXP-H-DA-11 | fechado | 0.8 | Heuristica shallow (avg_len+cardinalidade+is_numeric) que auto-detecta min_len por coluna; welded canonical em src/tcf (auto_min_len.py + en |
| T-EXP-MULTI-COL-SCALING | fechado | 0.8 | Port do multi-column pro canonical M10 + validacao real-world; welded canonical (src/tcf/multi.py encode_table/decode_table, ADR-0013, 17/17 |
| T-FMT-HEADER-BASE-HEX | fechado | 0.8 | Base HEX implicita e default dos byte-sizes do header (win-or-tie vs decimal; decimal so via comando de inspecao/IO/debug, nao altera o blob |
| T-CODE-H-DA-11c-features-unificadas | fechado | 0.9 | Refactor de consolidacao: extrai analyze_column->ColumnFeatures unificado removendo duplicacao (avg_len/cardinality/is_numeric) entre auto_m |
| T-CODE-LEGACY-PRUNE-PRE-07 | fechado | 0.9 | Poda de legado pre-0.7 (aposentou encode_table/decode_table, isolou producao #TCF.6/322B em tests/legacy, marcou leitura #TCF.6 como _legacy |
| T-EXP-H-PERF-05d | fechado | 0.9 | Otimizacao de perf (Counter incremental por delta em _detect_compositions); prototype validado mas rende so ~1.2-1.7x pure-Python com diverg |
| T-FMT-TCF8H-HEADER | fechado | 0.9 | Decisoes de formato do cabecalho hierarquico TCF.8H; fechado (closed-decided) — discriminador H reservado/weldado no .8 com fail-loud (ADR-0 |
| T-H-PERF-06-V2-T01-WELD-15 | fechado | 0.9 | Weld do candidato #15 (cheap upper-bound prune + running-max inline) em _detect_compositions — otimizacao interna, output byte-identico; clo |
| T-H-PERF-06-V2-T02-CYTHON | fechado | 0.9 | Acelerador Cython OPCIONAL de _detect_compositions com fallback pure-Python silencioso (Fase B), wiring pyproject/hatch/wheel+sdist; closed- |
| T-CODE-ENCODER-MANAGER | fechado | 2.0 | Reviver o D13 EncodeManager (paralelismo + sinks); Fases 1+1b (encode(parallel=N) via ProcessPool + work-stealing) WELDED e validadas no fec |
| T-CODE-LAYERED-PIPELINE | fechado | 2.0 | Infra de camadas toggleaveis (PipelineConfig: pre_pass/obat_shape_preserve/hcc_seq_rle p/ ablacao/debug) — Fase 1 WELDED no 0.7 e ticket clo |
| T-CI-1-github-actions | fechado | infra | CI via GitHub Actions: fase 1 (job lint pre-commit) + fase 2 (T-CI-2 refactor de tests, job test matrix py3.10-3.12) executadas no mesmo dia |
| T-CI-2-tests-refactor | fechado | infra | Refactor da suite pra rodar em CI: arquivou 5 tests v0.5 quebrados, marker requires_data pra SQLite, novo test_core_rt (30 pass+1 xfail), jo |
| T-CI-3-pyx-compiled-byte-gate | fechado | infra | Gate de byte-equivalencia do detect.pyx compilado vs pure-Python: teste local + job CI accel + fix do setuptools no build isolado + TCF_REQU |
| T-CLEAN-1-pre-commit-hooks | fechado | infra | Higiene de repo: .pre-commit-config.yaml criado (detect-secrets, ruff, hooks basicos, bloqueio de cache dirs) + dev deps + README; closed/co |
| T-DATA-1-datasets-financeiros-cientificos | fechado | infra | Aquisição de 3 datasets canônicos UCI (Online Retail, Beijing PM2.5, Wine Quality) com scripts de setup + metadata + hubs SQLite; fechado 20 |
| T-DATA-4-TPCH-PART-SAMPLES | fechado | infra | Emissao de samples git-tracked de part/partsupp do TPC-H para tornar a categoria hierarquica (p_type/p_brand/p_container) observavel; closed |
| T-DIST-PYPI-NAME | fechado | infra | Reservar/capturar o nome de distribuicao no PyPI; closed-done — 'tcf-format' 0.7.1 publicado pelo owner mantendo 'import tcf', com automacao |
| T-FIX-SHAPER-STRATIFY-TEST | fechado | infra | Correcao de teste do shaper: stratify proporcional espelha ~67/33 da populacao (nao 50/50); CLOSED 2026-05-31 via Opcao A (assert ~67/33 sem |
| T-RECOVER-SCHEMA-MULTI-TABLE | fechado | infra | Gadget de qualidade de schema multi-tabela (FK detect, date/format check, quality zero-custo via SideOutputs, CLI/relatório) alert-only; Fas |
| T-REGRESSION-REAL-WORLD | fechado | infra | Gate de regressão real-world (fixtures free-text ≥1000 linhas committadas, byte-canonical) que bloqueia weld de prune algorítmico em HCC; st |
| T-SHAPER-SCIENTIFIC-GATING | fechado | infra | Gate cientifico do shaper com testes estatisticos assertados (chi2/TVD, fk_preserving no-orphans, join row-count, schema-FK); closed-done —  |
| META-DOCS-V05-OBSOLETE | fechado | meta | Meta/docs: arquivar conteúdo v0.5-exclusivo em docs/archive/*_v05 (via git mv, history preservado) e reconectar o restante ao v0.6; fechado  |
| META-EXP-FORMAT | fechado | meta | Meta/processo: formalizar 2 templates de experimento clean (validacao single-axis vs comparativo multi-axis) e reorganizar EXP-008; fechado  |
| META-NAMING | fechado | meta | Meta/naming: oficializar nomenclatura v0.6 — TCF=Tabular Compact Format, alg16->OBAT, M8.A->HCC — e propagar em src/docs/README/CHANGELOG/py |
| META-THEORY-MOVE | fechado | meta | Tarefa de organizacao documental: 11 notas de teoria/hipoteses movidas de dirty/notas para docs/theory (+1 para docs/algorithms) via git mv, |
| T-CLEAN-2-strata-defrag | fechado | meta | Auditoria de aderencia Strata + higiene de superficie (deriva de docs, numero-fonte copiado na prosa): QW-1..5 executados 2026-06-18 e DB-1. |
| T-CLEAN-3-org-defrag-pre-0.8 | fechado | meta | Sucessor do T-CLEAN-2: defrag de organizacao pra facilitar o review do 0.8 (indice de tickets 62/62, diario retroativo de 29 dias, bridge no |
| T-DOC-1-citation-cff | fechado | meta | CITATION.cff criado na raiz + secao 'How to cite' no README; DOI/Zenodo deferido explicitamente ate v1.0 ou primeiro paper (follow-up T-DOC- |
| T-DOC-2-diataxis-naming | fechado | meta | Fechado via ADR-0012 documentando mapeamento local (docs/algorithms->reference, docs/theory->explanation, docs/how-to->how-to); nota no MAP. |
| META-ESCAPE-DEDUCTION | fechado | research | Pesquisa (Pacote 2) sobre suprimir escapes dedutíveis no HCC; caracterização real-world deu ~1.1% (< meta 5%), H-ED-01..04 refutadas; fechad |
| T-DATA-2-RECEITA-CNPJ | fechado | research | Dataset real de CNPJ (Receita) para gating ecologico da nature CNPJ; closed-done — script criado, download real feito, 200k reais 100% compr |
| T-DATA-TRANSMISSION-GROUPING | fechado | research | Matriz de agrupamento dos datasets por cenario de transmissao (3 eixos ortogonais, refinada de 4->7 formas-tx); closed-done sob T-REL-08-CLO |
| T-EXP-DATASETH-S0-S3 | fechado | research | Execucao sintetica S0-S3 (dirty lab) construindo evidencia regeneravel de capacidade semantica e algebra de vinculos p/ #TCF.8H: RT 20/20, a |
| T-EXP-H-DA-09c-d-e | fechado | research | Varredura de threshold {0.5,0.6,0.7,0.8} do detect_cadence em 66 cols (9 sinteticas + 57 real): 0.7 default e robusto/otimo, tunar p/ baixo  |
| T-EXP-H-GDICT-01 | fechado | research | Caracterizacao read-only do dicionario global cross-column (B1); passou gate estrutural/lazy em same-domain-refs mas teste-teto perdeu 4/5 p |
| T-EXP-NATUREZAS-RARAS-EXPLORACAO | fechado | research | Exploracao observacional das naturezas #5 (range narrow) e #8 (arredondamento/sufixo fixo) em Adult+TPC-H; NO-GO — padroes existem isolados  |
| T-EXP-PACOTE5-T03-ENUMERATED | fechado | research | Caracterizacao de encoder enumerated explicito (dict+indices) vs M10 em 37 colunas low-card; NO-GO — M10 (dedup+HCC seq-RLE) ja e enumerated |
| T-REVAL-H-DA-01-06-10 | fechado | research | Revalidação real-world de 3 hipóteses do Pacote 1 (delta-aware) só testadas em sintéticos; status closed (completed-with-surprises): H-DA-06 |
| T-REVAL-H-DA-07 | fechado | research | Revalidacao da hipotese H-DA-07 (OBAT shape-preserve com gating detect_cadence) em dados reais; fechado como confirmed-real-world — gating n |

---
title: CONTRATO EXTERNALIZADO + ARQUIVOS DE ACELERAÇÃO — direção do owner (2026-07-16) + análise crítica
type: report
status: aberta
created: 2026-07-16
related:
  - experiments/lab/dirty/notas/substituicao-indices-especiais-plano.md (Ciclo 2 — precedente: dicionário na VERSÃO)
  - experiments/lab/dirty/notas/tcf-camadas-arquitetura.md (L1/L2/L3)
  - experiments/lab/dirty/notas/estrutura-sem-dado-levantamento.md (irmão — registrado no mesmo ato)
  - docs/adr/0018-v2-format-roadmap.md (V2-J/V2-K/V2-L)
  - docs/adr/0024-pre-1.0-versioning-git-as-compat.md
  - tickets/T-FMT-OMIT-OR-DECLARE.md
  - tickets/T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md (S3 — embrião do profiler)
  - tickets/T-CODE-PLAN-CONTRACT.md
  - tickets/T-RECOVER-SCHEMA-MULTI-TABLE.md (gadget schema — closed-done)
  - experiments/lab/dirty/notas/roadmap-hipoteses.md (H-CONTRACT-EXTERN-01 · H-ACCEL-SIDECAR-01 · H-ENCODE-DEADLINE-01)
---

# Contrato externalizado + aceleradores — registro da direção + análise crítica

**Escopo deste doc**: REGISTRO para estudo do owner ("anote... registre... aí vou estudar").
Nenhuma implementação; nada disso é `.8` (o reescopo 2026-07-13 já deixou streaming/sinks/índices/
tcfx/checksum em `.9`/2.0/pré-1.0 — este doc não muda isso).

## 1. A direção do owner (2026-07-16) — [dispositivo→registro]

Itens fiéis ao ditado, numerados pra referência:

1. **Externalizar diretivas do cabeçalho** (ex.: a assinatura/diretivas de estrutura) economiza
   transmissão; a responsabilidade é **delegada às pontas** (client/server, transmissor/receptor).
2. **TCF auto-contido por DEFAULT**; **modificadores** tiram essa responsabilidade do arquivo.
3. **Contrato padronizado** — pode ser expresso **em TCF ou JSON** — para a estrutura; com
   **encode/decode de header/schema** separável, acoplável nas pontas **por versão**; o TCF
   **roteia** e faz encode/decode com o que for passado.
4. O arquivo deixa de ter o compromisso de guardar as diretivas; precisa só da **capacidade de
   acoplar** — talvez uma **assinatura do contrato**. → por isso a modularização é importante.
5. **Schema tool** (gadget): a partir de um volume de dados, fornece **padrões de schema**; output
   em **TCF compacto ou JSON**.
6. **Acoplamento lossless dependente**: o arquivo perde a capacidade de se explicar — de propósito —
   porque pode estar em **stream** e "não haverá mais 'um arquivo'".
7. Analogia **debug de compilador C/C++**: os acoplamentos internos existem, mas podem ser
   **"stripped"** para performance. Parte já dá pra fazer: **está modularizado, só não
   externalizado**.
8. **Profilers / arquivos auxiliares**: gerados do comportamento dos dados; **sem comprimir ou
   descomprimir de fato** — geram métrica e ajustes externos que **mudam o default** para acelerar
   nas condições da transmissão. O **índice** é um exemplo.
9. **Dicas pro decode do outro lado**: se a intenção do view remoto é filtrar/agrupar, o
   encode/decode pode **importar um arquivo dessas dicas**.
10. **"Desistência" de encode por latência**: estourou o orçamento (~1ms) → **libera saída** e segue
    **em pulsos**. O núcleo em árvore permite — **não pelo código atual, mas pela LINGUAGEM de
    encode/decode**.
11. **Paralelismo etc. calibrado e predefinido** — o encode **não fica "adivinhando"**.
12. A **parte automática** serve, em parte, justamente pra **GERAR** o contrato e os arquivos de
    aceleração: eles **ditam como a transmissão será** e o decode **já sabe o que fazer**.

## 2. O que JÁ existe (a discussão pedida — item a item, com referência)

O diagnóstico do item 7 ("modularizado, não externalizado") **confere** no código:

| ideia | embrião existente | onde |
|---|---|---|
| contrato na ponta + assinatura no wire (1,3,4) | **JÁ EXISTE em miniatura para specs**: o wire carrega só `:id` (a assinatura); o contrato (spec) vem por fora em `decode(..., nature=spec)`; aceito **somente** se `spec.name == id` do header, senão fail-loud | `src/tcf/decoder.py:62-79` (`_resolve_header_spec`) |
| header parcialmente externalizável (1) | colunas **anônimas** (`drop_names`, decodam nome posicional) + última coluna **sem size** (`min_header`) — diretivas já saem do wire quando dedutíveis | `src/tcf/multi/core.py:410-414,596` · O-FMT-15/16 **welded** (ADR-0023) |
| informação que sai do arquivo e vive na VERSÃO (3,4) | Ciclo 2 do plano de substituição: "**A string SAI do arquivo** e passa a viver no **dicionário da VERSÃO**"; "dono-versão... é parte do FORMATO" — mesmo princípio, escopo menor (especiais) | `substituicao-indices-especiais-plano.md:48-53` |
| encode/decode de header separável (3) | `_build_meta`/`_parse_meta` são funções isoladas do corpo (hierárquico); `_parse_meta` multi é "fonte única do parse" | `src/tcf/hierarchical.py:377,436` · `src/tcf/multi/core.py:177` |
| roteamento pelo que for passado (3) | dispatch de 1 char pós-`#TCF.8` (`H`/`M`/espaço/stamp/órfão; desconhecido = fail-loud) | `src/tcf/decoder.py:140-152` · ADR-0029/0031 |
| profiler zero-custo (8,12) | **SideOutputs** (15 campos: column_features, cadence_info, obat_log, hcc_trace, seq_rle_runs...) + `build_schema` → `TableSchema` com bytes por camada; e o **S3 do T-FLOW-ENCODE** (paráfrase fiel do ticket): telemetria sugestiva OFFLINE, por amostras, consumindo SideOutputs grátis — move a otimização pra 1× offline e sugere ao produtor emitir já na ordem ótima — é exatamente o profiler que muda o default | `src/tcf/side_outputs.py:28-71` · `src/tcf/schema.py:106` · `tickets/T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md` (S3) |
| schema tool (5) | gadget multi-tabela **closed-done** (fk_detect, date_check, sideouts_quality, CLI; só alerta, nunca arruma); falta só o output "padrões de schema em TCF compacto/JSON" | `tickets/T-RECOVER-SCHEMA-MULTI-TABLE.md` · `scripts/` |
| dicas de view pro decode (9) | view lazy já no core (`H-QUERY-01` promovido, `src/tcf/view.py`); decode-como-DAG + índices escondidos em DESIGN (`H-QUERY-04`); índice incremental Patricia registrado | Pacote 12 do roadmap · `project_teoria_indice_incremental` |
| latência/pulsos (10) | **V2-J** (pipeline streaming low-latency, TTFB; caso de uso HTTP/websocket/gRPC) — defer v2.0; **bloqueador de formato já mapeado**: header exige sizes ANTES do body → length-prefix, trailer ou size-deferred; O-FMT-15 é o "degrau ZERO" (deferred-sizing); S1 default já é O(N)/mem ~1 coluna | `docs/adr/0018:148-177` · `futuras-otimizacoes-formato.md` (O-FMT-08/15) |
| paralelismo predefinido (11) | `encode(parallel=N)` por coluna (byte-idêntico ao serial) + cap global `TCF_MAX_WORKERS` ticketado (open, design pós-F3; pós-release — cai no `.9` pelo reescopo) + **Plan dataclass** = contrato estável entre otimizadores e encoder (deferred v2.0) | `tickets/T-CODE-PARALLEL-BUDGET.md` · `tickets/T-CODE-PLAN-CONTRACT.md` |
| auto gera o contrato (12) | pre-pass (analyze_column/detect_cadence/detect_min_len) já produz o material; `build_schema` já o serializa (`to_json`) | `src/tcf/auto_*.py`, `column_features.py`, `schema.py` |

**Conclusão do inventário**: nenhuma das 12 ideias parte do zero. O que NÃO existe é (a) o
**contrato como artefato** de 1ª classe (formato, versão, assinatura), (b) o modificador
**strip-de-diretivas** no encode, (c) o **import** de perfil/dicas nas pontas, (d) o modo
**deadline/pulsos**. Tudo o mais é externalização do que já está modularizado.

## 3. Análise crítica — [probatório→opinião; não é decisão do owner]

### 3.1 Duas classes de artefato externo — a distinção que protege o fail-loud

A direção mistura (de propósito, como família) duas coisas com risco MUITO diferente. Proponho
nomeá-las desde já:

- **Classe SEMÂNTICA (contrato)**: sem ele, um wire stripped **não decodifica**. Perder/errar o
  contrato = corrupção. Logo a **assinatura é load-bearing**: wire stripped DEVE carregar
  assinatura curta do contrato, e o decode DEVE verificá-la fail-loud (mismatch = erro, nunca
  "tenta assim mesmo"). É o mesmo desenho já vigente em miniatura no `:id` das natures
  (`_resolve_header_spec`: id do header é autoritativo).
- **Classe de ACELERAÇÃO (profiler, dicas de view, índice)**: **droppable por construção**. Perder
  = perder só velocidade, nunca corretude. O wire decodifica sem eles, sempre. Nunca carregam
  semântica que o wire não tenha.

A régua do [T-FMT-OMIT-OR-DECLARE](../../../../tickets/T-FMT-OMIT-OR-DECLARE.md) já diz isso em
outra escala (verbatim do ticket): *"se o que sobra não a deduz, ela vira declaração
obrigatória"* — o contrato é a forma industrializada da declaração obrigatória; o acelerador é a
forma industrializada do dedutível.

**Terminologia** (higiene): "assinatura" já tem 2 sentidos no projeto (magic number, ADR-0001;
checksum de integridade, trilho tcfx/T-FMT-META-STRICT). Este é um **3º sentido**:
**assinatura-de-contrato** (fingerprint que IDENTIFICA o contrato, não valida bytes). Se virar
ticket, entrar no `docs/vocabulary.md` com os 3 separados.

### 3.2 Isto REVISA um princípio-mestre — dizer explicitamente

`feedback_materializacao_minimal` (memória, 4 mestras) diz: self-containment do `.tcf` — *"sem
hint externo, apenas com o arquivo passado"*, "nunca hint externo/sidecar; analogia gunzip". A
direção de hoje **revisa** isso: o self-containment vira **default** (não invariante absoluto), e
os modificadores opt-in externalizam. Nos estados do dirty lab: *era* invariante → *é* default →
*será* default + perfis stripped. A memória foi atualizada com a revisão (mesmo ato deste doc).
O que **fica intocado**: o pilar explicabilidade — o default continua textual e auto-explicável.

A analogia do owner (debug strip de C/C++) é precisa, com uma **inversão que é identidade do TCF**:
em C, `-g` é opt-in e o release é stripped por default; no TCF a explicação é o DEFAULT e o strip
é o opt-in. Coerente com "áreas explicáveis" (filosofia 2026-05-27).

### 3.3 Precedentes de indústria (o desenho proposto é o desenho provado)

- **Avro** tem exatamente os DOIS modos propostos: *Object Container Files* embutem o schema
  (self-contained) e *single-message encoding* carrega só um **schema fingerprint** e resolve o
  schema fora (registry) — fingerprint = a "assinatura do contrato" do item 4.
- **Confluent Schema Registry** (Kafka): payload = magic byte + 4B de schema-ID + corpo; o schema
  vive no registry, versionado. É o item 3 em produção há uma década.
- **HTTP/2 HPACK**: diretivas de header saem da mensagem e vivem em **tabelas compartilhadas nas
  pontas**, referenciadas por índice — o item 1 aplicado a headers HTTP.
- **Protobuf** é o contraexemplo que valida o DEFAULT do TCF: externalização por construção,
  o wire **nunca** se explica — o TCF mantém os dois modos, com o explicável como default.
- **PGO** (profile-guided optimization, `.profdata`/`.gcda`): roda → coleta perfil → **muda os
  defaults** da compilação seguinte. É o item 8 literal, com SideOutputs no papel do
  instrumentation build. O S3 do T-FLOW-ENCODE já é PGO-de-ordem-de-emissão.
- **Anytime algorithms / tiering de JIT / rate-control de vídeo**: o item 10 — saída válida
  dentro do orçamento, refinamento opcional. O owner está certo de que a **linguagem** permite —
  verificado em execução: qualquer encoding válido decodifica (RLE não emitido → linhas literais,
  RT-exato; RLE parcial idem; ref não descoberta → linha literal **na gramática do wire**, com
  dígitos finais escapados `\` — a mesma forma que o encode de 1 linha isolada emite). O código
  atual não permite (seq-RLE exige full body em memória — bloqueador já registrado no V2-J,
  ADR-0018:167).

### 3.4 Tensões reais (as três que precisam de decisão antes de qualquer weld)

1. **Deadline × byte-canonicidade**: os gates pinam output canônico; modo-pulsos produz output
   **válido mas não-canônico por construção** (o que deu tempo de descobrir). Tem que ser **modo
   declarado** (perfil), nunca default — senão reprodutibilidade e baselines morrem. O default
   continua canônico/determinístico.
2. **Strip × corrupção silenciosa**: um wire stripped decodificado com o contrato ERRADO é a pior
   corrupção possível (decode "funciona" e devolve outra coisa). Mitigação: assinatura obrigatória
   verificada (3.1) — sem assinatura válida, fail-loud. Nunca "modo tolerante".
3. **Stream sem arquivo**: se "não haverá mais 'um arquivo'", o self-containment migra do arquivo
   pra **sessão/canal** (contrato no handshake, 1× por conexão — como HPACK/TLS). O invariante que
   substitui o antigo: **wire + contrato → recupera tudo, lossless** ("acoplamento lossless
   dependente", nome do owner). Mesmo invariante do Ciclo 2: "arquivo + versão recupera".

### 3.5 Riscos menores, registrados

- **Proliferação de contratos** (versioning hell): contrato carrega versão própria + assinatura;
  pré-1.0 o git-as-compat (ADR-0024) cobre; o schema tool GERA contrato (não se edita à mão).
- **Aceleradores virando dependência de fato**: se um decode "precisa" do índice pra ser usável,
  a classe de aceleração degenerou em semântica. Guard-rail: teste de contrato — todo wire
  decodifica sem NENHUM sidecar (só mais devagar).
- **Anti-pattern buffer-over-buffer**: sidecars são artefatos PARALELOS (filosofia dos gadgets),
  não camadas empilhadas de cache. O profiler lê SideOutputs que o encode já computa (zero custo
  adicional) — não re-processa o wire.

## 4. Hipóteses registradas (→ [roadmap-hipoteses.md](roadmap-hipoteses.md))

- **[[H-CONTRACT-EXTERN-01]]** — contrato externalizado (classe semântica): formato do contrato
  (TCF/JSON), assinatura-de-contrato no wire, modificador strip no encode, acople por versão nas
  pontas. Engole a forma-do-header A×B do Ciclo 3 como caso particular.
- **[[H-ACCEL-SIDECAR-01]]** — arquivos de aceleração (classe droppable): profiler (PGO-style,
  SideOutputs→ajustes de default), dicas de view (filtrar/agrupar → ordem/índice), índice sidecar.
- **[[H-ENCODE-DEADLINE-01]]** — encode com orçamento de latência (pulsos/anytime): saída válida
  não-canônica sob deadline, como MODO declarado de perfil; interage com V2-J (mesmo bloqueador
  de sizes).

Todas sob o guarda-chuva [[H-PROFILE-01]] (perfil de uso decide default), nenhuma é `.8`.

## 5. O que explicitamente NÃO fazer agora

- Nenhum weld, nenhum ticket de implementação — o owner vai **estudar** este registro primeiro.
- Não confundir com o `.8` (feature-complete tabular+hierárquico): esta direção é o eixo
  transmissão/aceleração, vive em `.9`/2.0 conforme reescopo.
- Não tocar na dívida já parqueada (V2-J/K/L defer v2.0) — este doc dá o CONTEXTO que faltava a
  elas (o contrato é o que torna o streaming barato), não as reabre.

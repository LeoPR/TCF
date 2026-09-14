---
title: T-QA-8, material comprobatório do #TCF.8/0.8.0 (controle → sintéticos → públicos) com telemetria, dicts e paralelismo
status: open
priority: P1
created: 2026-07-10
updated: 2026-09-14
gate: ".8 (dossie da versao); levantamento dos restos em 2026-09-02, §Levantamento"
blocked-by: []
related:
  - docs/adr/0032-tcf8-default-format.md
  - tickets/T-DIST-RELEASE-0.8.0.md
  - tickets/T-REL-08-CLOSEOUT.md
  - tickets/T-CODE-DESCAPAR-V2B.md
  - tickets/T-CODE-ENCODER-MANAGER.md
  - tests/test_real_world_snapshots.py
  - src/tcf/side_outputs.py
  - scripts/dataset_reader.py
---


## Atualizado 2026-09-01: os itens abertos, verificados um a um

O `.8` publicou cinco releases desde a última passada deste dossiê, e vários itens foram
resolvidos pelo caminho sem o checkbox ser marcado. Conferidos agora, rodando:

| item | verdito | como |
|---|---|---|
| **DOC-01** [alta] | **feito** | o badge do `README.md` diz `0.8.4` e não há `#TCF.7` em lugar nenhum; a página foi reescrita várias vezes desde então |
| **DOC-03** [média] | **feito** | o exemplo `@a=uf,1e=nome` não existe mais em `TCF-format.pt-BR.md` nem no `.en.md`. O real hoje é `#TCF.8M!8=uf,!nome`, com a última coluna sem size, que era exatamente a regra que o exemplo contradizia |
| **DOC-04** [baixa] | **feito** | `pyproject.toml` tem `[project.urls]` e classifiers; a 0.8.4 ainda ganhou o `py.typed` que o classifier `Typing :: Typed` prometia e nenhuma wheel entregava |
| **DOC-05** [baixa] | **feito (2026-09-02)** | o item principal estava resolvido (`scripts/benchmark_compression.py` sem resíduo v0.5). Sub-itens reconferidos: `benchmark_parallel.py` ganhou warmup descartado + mediana de N runs (`--runs`); `metadata.json` dos canônicos já tinham `row_counts`; a linha do `T-FMT-NAME-ESCAPING` no índice já dizia CLOSED-PARCIAL; tabelas do `datasets/synthetic/README.md` cobriam até D11e — incluídas as linhas D11f–D11m. O `run.log` untracked virou moot: `dirty/` é fora-do-git por decisão de 2026-08-22 |
| **BUG-12** [alta] | **corrigido (2026-07-24), provado 2026-09-02** | ver abaixo |

### BUG-12: o que a medição diz, e o que ela não diz

> **RESOLVIDO 2026-09-02 — o bug foi corrigido pelo weld `25ad29eb` (guard de progresso no
> `_parse_decl`, 2026-07-24), 14 dias após o registro, sem o checkbox ser atualizado.** Prova
> antes/depois: a mutação exata do registro pendura o código pré-guard (`1c77b678`; stack em
> `_parse_decl` dentro de `_decode_column`, como descrito abaixo) e levanta `ValueError` em
> ~3 ms já no commit do guard e no HEAD; corpus dirigido de 165 fronteiras deslocadas:
> PRE = 145 `ValueError` + 19 `KeyError` cru + 1 hang · HEAD = 165/165 `ValueError`. O
> residual "`*N|` sem teto" do próprio weld foi fechado no mesmo dia pelo `max_length`
> (`95ab69dc`). Lab: `experiments/lab/dirty/2026-09/2026-09-02/2026-09-02-0102-bug12-existe-ou-obsoleto/`.
> A "proposta, não aplicada" abaixo fica **superseded**: partia de "não reproduz, talvez não
> exista"; a prova mostrou "existiu, está corrigido". Higiene que sobra pro `.9` (barata,
> opcional): varredura formal de "todo laço de parse prova progresso".

Fuzz de flip de **um dígito hexadecimal** no meta, 750 casos: 4 tabelas × 2 modos de header ×
cada posição hex × cada dígito alternativo, com 8 s de timeout por caso, cada um em processo
separado. **Nenhum travou.** 500 levantaram `ValueError` e 250 decodificaram (a maioria destes
por o dígito trocado cair num NOME de coluna, não num size, o que renomeia a coluna e não
corrompe dado).

Isso **não prova que o bug foi corrigido**. O ticket descreve uma condição específica de
fronteira deslocada, e um fuzz de dígito único pode simplesmente não alcançá-la. O que a
medição sustenta é mais modesto e ainda assim útil: a forma trivialmente alcançável do
não-terminar não está aí.

**Proposta, não aplicada**: mover o BUG-12 para o `.9` em vez de fechá-lo ou de deixá-lo
segurando o `.8`. Três razões. Ele é **pré-existente** e o próprio ticket o registra como não
sendo regressão do `.8`. O conserto **toca o core HCC** e exige aprovação explícita mais os
gates byte-canônico e real-world completos, que é escopo de ciclo e não de fechamento. E ele
**não reproduz** no ataque mais óbvio, então segurar uma versão inteira por ele seria pagar
caro por um risco que não se consegue demonstrar.

O que ele merece no `.9` é um guard de terminação no decode, que é barato e vale por si:
qualquer laço de parse deve provar progresso, independentemente deste bug existir ou não.
# T-QA-8: material comprobatório do #TCF.8/0.8.0

> **⚑ ERRATA 2026-07-22** ([parecer 2340](../experiments/lab/dirty/notas/2026-07/2026-07-22-2340-revisao-fechamento-08-ordem-foco.md)):
> **(1)** o achado F4 "nature CNPJ PIORA em real (`+7339 B`)" descreve a forma ABSOLUTA pré-FLOOR,
> **não** o resultado público (o FLOOR nunca regride); está **sob revisão estrutural** (lab de natures
> a abrir), o F6 **não** deve claimar isso como propriedade. **(2)** novo material disponível:
> baseline de perf first-order (`evidencia-0.8/perf-baseline/`) alimenta o F6/DOC-01. **(3)** o F6 só
> depois da API única + decisão do lab de natures + fechamento de `view` (ordem no parecer).

**[dispositivo→execução]** Diretriz do owner (2026-07-10): gerar o **material comprobatório**
de TUDO que foi feito no `.8` até o momento, com dados mais sólidos, todos os **dicts**,
verificação de **paralelismo**, **telemetria** interna (derivada dos dados via SideOutputs)
e a obtível "de graça" (Python/OS). Plano escalonado: **testes de controle bem pequenos**
(single-col com/sem header, variações de reader, o exemplo-propaganda do README) →
**sintéticos maiores** → **datasets públicos** pra bench. Depois disso: alguma **otimização
extra** (se a evidência apontar) e **empacotar pro pip com documento bem feito**.
Este ticket é a tarefa-grande com as microtarefas NA ORDEM, **nada de executar na louca**;
cada fase fecha antes da seguinte.

Fonte do levantamento: workflow de 10 agentes (6 inventário + 4 sweep adversarial),
2026-07-10, read-only, claims verificadas por leitura/execução (repros colados nos achados).

## §1: O que o levantamento achou (estado real, resumo por eixo)

- **Dicts: são 3 welded + 2 de lab** (o material cobre os 3 welded; os de lab só se documenta):
  1. **V2-B dict per-coluna** (`@`, ADR-0025), `src/tcf/multi/dict_v2b.py`; candidato do
     `min(tcf,raw,v2b,split)`; cap de compute 8192 (T-CODE-DESCAPAR-V2B forma A, 2026-07-02).
     Tem suite (TestV2BDict) mas **zero teste do boundary 8192 e do índice width≥2 (K>94)**.
  2. **Dict IMPLÍCITO do HCC/OBAT** (aliases inline + `^eid`), sempre ativo, coberto pelos
     pins byte-canônicos. Dois sistemas de ref coexistem (`^N` decimal vs base-94 do V2-B). H-REF-01.
  3. **SPEC_REGISTRY das natures** (`:cpf/:cnpj/:ip` self-describing, ADR-0027), registry fechado.
  4. (lab, CLOSED) cross-dict/group-dict `&<G>` B1/B2, closed-insufficient-generalization; nicho 0.9+.
  5. (lab, gated) família bN/spec_bin b/b2/b4/b8, sem API pública, sem teste; weld gated por H-TYPE-03.
- **Paralelismo, JÁ EXISTE welded**: `encode(parallel=True|N)` via ProcessPoolExecutor com
  work-stealing e reordenação determinística (`src/tcf/multi/parallel.py`; T-CODE-ENCODER-MANAGER
  fases 1+1b, byte-identidade pinada em `tests/test_parallel.py`). Limites reais: fase de candidatos
  V2-A/B/split roda SERIAL no pai DEPOIS do pool (porção Amdahl não medida); decode 100% serial;
  Cython sem `nogil` (free-threaded 3.13t re-ativa o GIL); byte-identidade parallel==serial só
  testada em D17a (nunca nos snapshots real-world). Speedup histórico ~1.3x teto (IPC Windows spawn).
- **Telemetria**: SideOutputs = 13 campos, todos populados só no ENCODE (decode não tem side).
  `obat_log`/`hcc_trace`/`seq_rle_runs` são gerados INCONDICIONALMENTE (custo sempre pago, relevante
  pra claims de latência). "De graça" verificado no venv real (Py 3.13.13, Windows): perf_counter_ns,
  tracemalloc, getallocatedblocks OK; `resource` AUSENTE; `os.times()` inútil p/ filhos (children=0.0);
  `process_time` quantizado em **15.625ms** → payload pequeno EXIGE repeat+mediana (padrão n=9 do lab f1);
  peak-RSS stdlib-only via ctypes psapi (verificado disponível); **psutil NÃO é dep** (decisão de opt-in
  é do owner). Precedentes: `benchmark_compression.py` QUEBRADO (API v0.5, não rotulado);
  `benchmark_parallel.py` mede 1 run só. Não existe runner vivo bytes+tempo+memória.
- **Datasets**: 31 CSVs sintéticos (7-20 linhas; D1-D9 controle, D10/13/14 stress); hubs SQLite prontos:
  adult 48842, tpch-sf001 60175, tpch-sf01 600572, ibge 5571, br-identidades 600k, receita-cnpj 200k;
  **online-retail/beijing-pm25/wine-quality SEM hub** (só CSV em external/, rodar csv_to_sqlite).
  Buraco de escala: nenhum sintético entre 20 e 2000 linhas (single) / 13 e 100 (multi);
  `tests/fixtures/synthetic_domains.py` é parametrizável em n e cobre o gap.
- **Modos/readers**: 12 kwargs de encode + PipelineConfig (3 toggles) + natures + view lazy.
  Só existem DOIS readers: `decode()` e `view()` (view cobre SÓ `#TCF.8M`; library-only, sem CLI).
  Matriz modo×teste tem furos: escaping×view sem teste, hex sem teste direto de parse, fail-loud só
  testado com 'H', drop_names+última-anônima sem teste, parallel×natures/sort_by sem byte-identidade.
  >
  > **Atualizado 2026-09-01 (0.8.4)**: os dois números deste bullet envelheceram, cada um pelo
  > seu motivo. A contagem de kwargs estava CERTA quando foi escrita: em `34e9655b` (2026-07-12)
  > o `encode` tinha 12 keyword-only. A [ADR-0047](../docs/adr/0047-schema-parametro-unico-de-spec.md)
  > fundiu `nature=` e `nature_per_col=` num `schema=` só, e hoje `inspect.signature(tcf.encode)`
  > devolve **12 parâmetros dos quais 1 é o `data` posicional**, ou seja **11 kwargs**: `schema`,
  > `side_outputs`, `parallel`, `layers`, `fallback`, `min_header`, `min_len`, `sort_by`, `name`,
  > `stamp` e `drop_names`.
  >
  > Os readers continuam sendo dois, `decode()` e `view()`, e continua sem CLI. O que caiu foi a
  > afirmação entre parênteses: a `view` não cobre mais só o `#TCF.8M`. Verificado por execução
  > em 0.8.4, ela abre
  > o single-col `#TCF.8` (`['a','b','c']`, coluna `0`), o mesmo single-col SEM magic
  > (`stamp=False`, o órfão), o single-col TIPADO (`#TCF.8n` de `[1,2,3]`, `#TCF.8b` de bool,
  > `#TCF.8bB` da união bool+str e a forma com spec no header, `schema='data-iso'`), o `#TCF.8M`,
  > o `#TCF.8R` da [ADR-0049](../docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md), que
  > ela normaliza para multi na abertura, e o `#TCF.8H` **quando ele é tabela retangular**.
  >
  > Esse último caso ficou estreito depois da ADR-0049. O retangular plano virou `.8R`, então o
  > `.8H` retangular é hoje só o que a canonização recusa e mesmo assim é tabela, por exemplo
  > uma lista de registros cuja única chave carrega um LF no meio do nome.
  >
  > O que a `view` recusa é o `.8H` que não é tabela, e a mensagem diz qual dos três casos é.
  > Ragged (`[{'a':'1','b':'2'},{'a':'3'}]`): "`view()` precisa de uma tabela retangular: a coluna
  > 'b' é opcional (ragged). Use `decode()` para este blob." Aninhado, e o array na célula cai
  > aqui também (`[{'a':{'x':'1'}}]` e `[{'a':['1','2']}]`): a mesma frase com "a coluna 'a' é
  > aninhada". Raiz que não é tabela (`[['1','2'],['3','4']]`, wire `#TCF.8H#V`): "`view()`
  > precisa de uma TABELA: este `.8H` tem raiz '#V', que não é tabela. Use `decode()`."
- **Natures/CPF**: spec CPF valida o DV DE VERDADE (mod-11); DV inválido → status `check_invalid` →
  **fallback literal `_<valor>`** (repro: 3 valores DV-válido=33B/apply_rate=1.0 vs DV-inválido=72B/
  apply_rate=0.0; RT 100% nos dois). Consequência dura pra regra de anonimização (ver §2).
  Gerador DV-válido existe: `scripts/setup_br_identidades.py` (`_gen_cpf/_gen_cnpj`, seed 20260601).
  Anonimizador (re-invalidar DV) NÃO existe, criar fora de src/tcf.

## §2: REGRAS do material (dispositivo; valem pra todas as fases)

1. **RT sempre**: nenhum byte reportado sem `decode(encode(x)) == x` validado na mesma run.
2. **Medir, não calcular**: todo número do material sai de execução; a prosa aponta pra artefato/teste.
3. **Regra CPF do owner (2026-07-10)**: medição vs publicação são artefatos DISTINTOS:
   - **Medição**: dados DV-**válidos** sintéticos, EFÊMEROS, regenerados por gerador+seed
     (`setup_br_identidades.py`, seed 20260601); assert `nature_apply.apply_rate == 1.0`
     (garante que o codepath base-94 do spec foi exercitado, não o fallback).
   - **Publicação**: NUNCA publicar CPF DV-válido, nem cru, nem dentro de `.tcf`
     (o header self-describing `:cpf` decoda sem spec out-of-band: publicar o blob = publicar os CPFs;
     verificado por execução). Material publicado = gerador+seed referenciado e/ou exemplos
     DV-**inválido** explicitamente ROTULADOS como fallback-path (o fallback deixa os dígitos
     verbatim `_<valor>` e NÃO reproduz os bytes da medição, dizer isso no material).
   - Anonimizador: re-invalidar trocando os 2 DVs por `(dv+1)%10` (não colide com o correto).
   - CPF reporta SEMPRE com ressalva "sintético é o teto" (PII → fonte real impossível);
     só CNPJ (receita-cnpj real) fecha confirmada-empirica (gate registrado).
4. **Telemetria honesta e PORTÁVEL** (F0-3, owner): conceitos independentes de OS/hardware/
   linguagem, sondas isoladas por plataforma com fallback gracioso (campo ausente ≠ medição
   quebrada). Tempo = `perf_counter_ns`, warmup + n≥9 runs + mediana (+p95), no Windows o
   `process_time` tem tick de 15.625ms, mais um motivo pro repeat ser parte do CONCEITO;
   memória = tracemalloc peak em RUN SEPARADA da de tempo (overhead) + `peak_rss` melhor-esforço
   por sonda; claims de paralelismo = wall-clock speedup + byte-identidade +
   `multi_info['parallel_workers']` (CPU/mem dos workers é INOBSERVÁVEL via stdlib em qualquer
   OS, não claimar). Registrar sempre: python/os/cpu, versão tcf, sondas ativas, flag
   `_detect_compositions_accelerated` (Cython on/off muda latência, não bytes).
5. **Outputs visíveis**: resultados em `experiments/results/evidencia-0.8/` (NÃO gitignored),
   JSONL com proveniência (dataset id, n_rows/n_cols, seed, ambiente) + artefatos `.tcf` de exemplo.
6. **Nada toca `src/tcf` sem aprovação explícita**: runner/telemetria/anonimizador vivem em
   `scripts/` ou lab. Bugs do §3 só se corrigem em F0, em lote, sob aprovação.
7. **Gates intocados**: D1-D9=1523B, D17a=300B, real-world=89616B são régua, não alvo, o material
   compara, não re-pina. Stress (D10/13/14) apresentado SEPARADO de design-realista.
8. gzip/brotli/zstd aparecem como sinal qualitativo de composição (TCF+br), nunca como gate.

## Levantamento 2026-09-02: os 20 itens abertos, verificados um a um

Este ticket é o **único** dos 27 abertos com gate `.8`, então o que sobra aqui é literalmente o
que separa a versão de fechada. Verifiquei os 20 itens contra o repositório, rodando. Três
grupos saem daqui: o que já está feito e só não foi marcado, o que é decisão sua, e **um
critério que não está cumprido**.

### A. Feito, provado, só falta marcar (11 itens)

| item | prova |
|---|---|
| **DOC-01** / **F6-1a** | as onze marcas da era 0.7 que o item lista têm **zero** ocorrência nos dois READMEs: `0.7.1`, `#TCF.7`, `TCF.6`, `379 passed`, `244B`, `303`, `322`, `Format 0.7`, `tcf_lazy`, `does not compress`. O badge diz `0.8.4` |
| **DOC-03** / **F6-1c** | `@a=uf,1e=nome` não existe mais em `TCF-format.pt-BR.md` nem no `.en.md` |
| **DOC-04** / **F6-1d** | `pyproject.toml` tem `[project.urls]` (4 links) e os classifiers, `Typing :: Typed` incluso, com o `py.typed` que a 0.8.4 passou a entregar |
| **F6-1b** | DOC-02 já estava feito; a suíte fecha 2005 passed / 2 skipped |
| **F6-1f** | o `CHANGELOG.md` tem entrada própria para `0.8.0` a `0.8.4` |
| **F6-2** | a wheel foi reconstruída e passou smoke em venv limpo nas quatro famílias |
| **F6-3** | publicado: `tcf-format 0.8.4` no PyPI e as tags `v0.8.0` a `v0.8.4` no repo |
| **§5 "sem promessa que não entrega"** | é o DOC-01 acima, e ele fecha |

O `F6-3` é o mais eloquente: o ticket que segura o `.8` lista a **publicação** como pendente,
e a versão está no PyPI desde ontem.

### B. Decisão sua, não trabalho pendente (2 itens)

- **F0-3**: `psutil` como extra de bench (`[bench]`) ou stdlib-only. A recomendação escrita no
  próprio item é stdlib-only nesta rodada, e nada desde então a contradisse.
- **F0-4**: metade virou moot com o DOC-05 (o `benchmark_compression.py` já parseia, e o
  `run.log` saiu do git em 22/08). Não sobra ação, sobra confirmar que não sobra.

### C. Fora do ciclo (1 item)

- **F5-1**: triagem de candidatos de performance. É trabalho de algoritmo, então `.9`, e o
  destino natural é o [`T-PERF-BORDAS-E-MODOS-09`](T-PERF-BORDAS-E-MODOS-09.md), que já é o
  ticket-mestre do ciclo.

### D. Critério NÃO cumprido, e sem gate que o pegue (1 item)

> **§5: "Regra CPF cumprida: nenhum artefato publicado contém CPF DV-válido (nem em `.tcf`)."**

Varri os **1818 arquivos versionados** e o critério **falha**: 265 CPFs com dígito verificador
válido, em 25 arquivos, descontados os de dígito repetido (`111.111.111-11` e afins, que são
sentinelas e não colidem com pessoa). Os maiores focos:

| arquivos | ocorrências |
|---|---:|
| `datasets/samples/br-identidades/pessoas-sample.csv` | 100 |
| `tests/test_natures.py` | 61 |
| `datasets/samples/br-identidades/empresas-sample.csv` | 32 |
| `docs/how-to/use-natures.md` | 21 |
| outros 21 arquivos | 51 |

Três agravantes, e é por isso que isto não é detalhe:

1. **`src/tcf/natures/__init__.py` tem um.** Esse arquivo **embarca na wheel**, então o número
   está publicado no PyPI, não só no GitHub.
2. **Os dois READMEs têm um** (`123.456.789-09`), e o README é a long-description da wheel.
3. **Não existe gate.** O critério é cumprido por convenção, e convenção não pega regressão. É
   exatamente a classe de falha do incidente do pin do `bench_perf`: o que ninguém verifica não
   avisa quando quebra.

Vale a distinção honesta: esses números são **sintéticos**, não vazamento de base real. Mas a
regra que você escreveu não fala de origem, fala de DV válido, e a razão de ser dela é
justamente que um DV válido pode coincidir com o CPF de alguém.

O conserto é barato e é `.8` de cheio, conformidade: trocar o corpo dos números por um que
**falhe** o DV, mantendo o formato e o comprimento (nenhuma medição muda, porque o tamanho em
bytes é idêntico), e amarrar um teste que varre os arquivos versionados e falha vermelho se um
DV válido voltar. O varredor já existe e roda em poucos segundos sobre os 1818 arquivos.

Um cuidado ao executar: os `.jsonl` de baseline em `perf-baseline/` também aparecem na lista, e
**esses não devem ser editados**, porque são evidência gravada de rodada. O certo ali é
registrar a exceção no gate, não reescrever o artefato.

### O que fecha o `.8`, então

Marcar o grupo A, confirmar os dois do grupo B, mandar o F5-1 para o `.9`, e resolver o grupo D.
Só o D é trabalho de verdade, e é trabalho de uma sessão.

## Verificação 2026-09-12: o `.8` está fechado? Prova em partes

**[probatório]** O owner declara o `.8` fechado (`T-REL-08-CLOSEOUT` `closed`, `0.8.4` publicada).
Este ticket é o único ponto que ainda o aponta como aberto, então cada item aberto daqui é
conferido contra o repo, uma parte por vez. **Registrar evidência não marca checkbox**: a marcação
e o fechamento do ticket ficam para o owner, na parte 5. Diário:
`experiments/lab/dirty/notas/diario/2026-09-12.md`.

### Parte 1: o que ainda está aberto (feita)

29 marcações não fechadas, nenhum commit neste ticket depois de 2026-09-02. Grupos, segundo o
levantamento de 09-02 mais a conferência de hoje:

| grupo | itens | situação |
|---|---|---|
| A | DOC-01, DOC-03, DOC-04, F6-1a/b/c/d/f, F6-2, F6-3 | conferido na parte 2 |
| B | F0-3, F0-4 | F0-3 **já decidido**: `T-REL-08-CLOSEOUT:182` registra "F0-3 fechado stdlib-only"; F0-4 moot |
| C | F5-1 | destino `.9` declarado (`T-PERF-BORDAS-E-MODOS-09`), que ainda não o cita |
| D | regra do CPF (§5) | ainda falha: `123.456.789-09` em `src/tcf/natures/__init__.py:37` e nos dois READMEs; sem teste varredor. Tensão de regra: `tests/test_schema_param.py:21` diz "CPFs DV-válidos já presentes na suíte (nunca criar novos)", o §5 proíbe qualquer um em artefato publicado |
| parciais `[~]` | BUG-11, BUG-13, F0-1, F3-3, F3-4, F4-2, F4-4 | sem veredito no levantamento de 09-02; parte 3 |
| aceite | 7 caixas do §5 | sem veredito; parte 3 |

### Parte 2: grupo A (feita)

| item | prova conferida em 2026-09-12 | veredito |
|---|---|---|
| DOC-01 / F6-1a | zero ocorrências nos dois READMEs de `0.7.1`, `#TCF.7`, `TCF.6`, `244B`, `303`/`322`, `379 passed`, `Format 0.7`, `tcf_lazy`, `does not compress`, `legacy`, `forces`, `27B`, `target 0.8`; seção "Format 0.8 (default)" na linha 388; ressalva do CNPJ em dado real em `README.md:325` | feito |
| DOC-03 / F6-1c | `@a=uf,1e=nome` com zero ocorrências em `TCF-format.pt-BR.md` e `.en.md` | feito |
| DOC-04 / F6-1d | `pyproject.toml` com 4 `[project.urls]`, classifiers com `Typing :: Typed`; `src/tcf/py.typed` presente | feito |
| F6-1b | menções a `#TCF.6/.7` em `decoder.py` descrevem o corte fail-loud; `is_v8` zero; `scripts/tcf_lazy` citado em `view.py:9` existe | feito |
| F6-2 | `.github/workflows/release.yml:103-116`: venv limpo, `cd /tmp`, round-trip e versão igual à tag; `publish` com `needs: build`; run da `v0.8.4` em 2026-09-01 com `success` (actions/runs/33536702884); sem `dist/` local | feito |
| F6-3 | tags `v0.8.0`..`v0.8.4`; PyPI lista 0.8.0..0.8.4, a 0.8.4 enviada em 2026-09-01T17:16 | feito |
| F6-1f | seções 0.8.0..0.8.4 existem no CHANGELOG, mas **os fixes do F0 não estão listados**: BUG-01 e BUG-04 aparecem por outro caminho (ADR-0046, corte do legado); BUG-03, BUG-09, BUG-14, BUG-15 e BUG-16 não aparecem (dois eram corrupção silenciosa). O C0 é dedup interno, sem efeito observável, e não precisa entrar | **parcial, aguarda decisão** |

**Decisão pendente (F6-1f).** Fato que restringe as opções: o topo do `CHANGELOG.md` declara
"Entries below are dated and append-only". O item F6-1f foi escrito antes da publicação da 0.8.0,
quando a entrada ainda era rascunho; publicada, ela não se reescreve. Opções:

- (a) editar a entrada 0.8.0: **contraria a regra append-only** do próprio arquivo;
- (b) aceitar o critério como absorvido pela narrativa da release, com ressalva registrada aqui:
  as correções ficam só no git e neste ticket;
- (c) **nova entrada datada, no topo**, registrando as correções que embarcaram na 0.8.0 sem
  terem sido listadas (BUG-03, 09, 14, 15, 16). Respeita o append-only e leva ao histórico público
  duas correções de corrupção silenciosa (BUG-14 e BUG-15). Cuidado de redação: o BUG-16 foi
  descrito com `nature=`, que a própria 0.8.0 cortou em favor de `schema=`.

**Correção ao levantamento de 09-02:** ele diz que a wheel passou smoke "nas quatro famílias". O
smoke que protege a publicação faz round-trip de uma tabela `.8M` e confere a versão. Prova o F6-2
como pedido; "quatro famílias" não tem registro em disco.

### Parte 3: parciais e critérios de aceite (feita 2026-09-14)

Cada item recebe um de três vereditos: feito, adiado para o `.9` com rótulo, ou pendente. Como o
owner declarou o `.8` fechado (`T-REL-08-CLOSEOUT`), o que não foi feito e não é correção vai para
o `.9` com destino nomeado, pela régua de versão.

| item | prova conferida | veredito |
|---|---|---|
| BUG-11 | (b) fixado no lote 3; o resíduo (a) é flip geometricamente consistente, que só checksum pega | adiado com rótulo: [T-FMT-META-STRICT](T-FMT-META-STRICT.md) |
| BUG-13 | (b), (d) e (e) fixados no lote 4; restam (a) e (c), também só checksum | adiado com rótulo: [T-FMT-META-STRICT](T-FMT-META-STRICT.md) |
| F0-1 | lotes 1 a 4 executados; o BUG-12, que restava, foi corrigido pelo weld `25ad29eb` e provado em 09-02 | feito |
| F3-3 | byte-identidade parallel==serial só em D17a; speedup histórico perto de 1,3× (IPC do spawn no Windows); porção serial não medida | adiado com rótulo: [T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md) |
| F3-4 | a rodada com `br-identidades` (600k) não foi registrada; existem os controles pequenos `f2/e5` a `e7` | adiado com rótulo: [T-PERF-BORDAS-E-MODOS-09](T-PERF-BORDAS-E-MODOS-09.md) |
| F4-2 | `online-retail` está no gate real-world e no EXP-019; `wine-quality` só no EXP-019; `beijing-pm25` em nenhum | adiado com rótulo: [T-PERF-BORDAS-E-MODOS-09](T-PERF-BORDAS-E-MODOS-09.md) |
| F4-4 | os `RESULT.md` por fase existem; a tabela-mestra cross-fase e a nota Wohlin, não | adiado com rótulo: [T-PERF-BORDAS-E-MODOS-09](T-PERF-BORDAS-E-MODOS-09.md) |
| §5 JSONL | schema `evidencia-0.8/v1`: `rt_ok` obrigatório para qualquer número, `seed` e kwargs de proveniência; 88 JSONL em `f2`, `f3` e `f4-minimo` | feito |
| §5 dicts e natures | F2-6: um blob por mecanismo; 14 `.tcf` em `evidencia-0.8/f2` | feito |
| §5 paralelismo | o mesmo estado do F3-3 | adiado com rótulo: [T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md) |
| §5 telemetria | F0-3: camada de conceitos portável e sondas por plataforma com fallback `None`; F1-2: `SideOutputs` serializado; ressalvas do Windows no §1 e no §2 | feito |
| §5 bugs do §3 | DOC-01, DOC-03 e DOC-04 feitos na parte 2; BUG-11 e BUG-13 com resíduo adiado com rótulo | feito, pelo texto do próprio critério |
| §5 README | é o DOC-01, feito na parte 2 | feito |

**Correção à nota do F4-2:** ela diz que os CSVs dos três hubs "já viram no gate real-world". Só o
`online-retail` está em `tests/test_real_world_snapshots.py`.

### Parte 4: grupo D, a regra do CPF (feita 2026-09-14)

Decisão do owner em 2026-09-05: **"não existe pendência de CPF"**. A caixa do §5 é marcada como
**dispensada pelo owner**, e não como cumprida: o registro da parte 1 sobre o `123.456.789-09`
continua verdadeiro. Nada em `src/tcf` foi tocado.

### Grupo C: F5-1 (feito 2026-09-14)

O F5-1 foi para o [T-PERF-BORDAS-E-MODOS-09](T-PERF-BORDAS-E-MODOS-09.md), na seção "Recebido do
T-QA-8", com os quatro candidatos e o gate de regressão real-world. O F3-4, o F4-2 e o F4-4 foram
junto, e o F3-3 foi para o [T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md).

### Parte 5: marcação (feita 2026-09-14, com autorização do owner)

O owner autorizou em 2026-09-14 marcar o que as partes provaram. Cada caixa marcada carrega o
veredito ao lado. **Fica aberto só o F6-1f**, que aguarda a decisão entre (a), (b) e (c) da parte
2. Por isso o ticket não fecha ainda.

### Fila do que falta (atualizar ao fim de cada parte)

1. **Decisão do owner, F6-1f**: opção (a), (b) ou (c) da parte 2; a (a) contraria o append-only.
2. **Fechar o ticket**, marcando o F6-1f conforme a decisão. Nada mais resta.

## §3: REGISTRO DE BUGS (achados no planejamento; arrumar em F0, NÃO agora)

> **PONTE 2026-07-12 (revisão de fechamento por ROI)**: o inventário passa a 14 bugs. Os lotes
> F0 fecharam 12/13 achados originais; a revisão pós-F2 encontrou o **BUG-14**, que quebra RT para
> entrada aceita pelo encoder e por isso é gate R0 antes de F3. BUG-12 e guardas de expansão sob
> blob corrompido continuam importantes, mas ficam no hardening 0.8.1 por decisão de prioridade do
> owner. Ordem dispositiva: [T-REL-08-CLOSEOUT](T-REL-08-CLOSEOUT.md).

Sweep adversarial 2026-07-10 (4 agentes; repros executados). Nenhum corrigido ainda, regra do
owner: "SE identificar algum bug sem querer, registre apenas pra arrumarmos depois".

### Corrupção/RT (candidatos a fix pré-medição: tocam src/tcf, exigem aprovação)

> **LOTE 1 EXECUTADO (2026-07-10, aprovação + decisões de design do owner)**: BUG-01+02+07 fixados
> red→green (16 repros pinados em `tests/test_f0_boundary_fixes.py`; suíte 546 passed; pins intactos).
> Verificação adversarial por workflow (3 agentes): **byte-neutralidade old-vs-new PROVADA em 122/122**
> casos (encode E decode, incl. side_outputs e parallel=2); refutador rodou 320 checks (313 pass) e
> achou 1 alta REAL, **gramática ambígua do último token** (`<size>` bare com `min_header=False` +
> anônima parseava como NOME, pré-F0), fechada no EMIT (última anônima SEMPRE sem size) + 1 falso-
> positivo do guard de colisão com drop_names (fechado). Paridade view/decode confirmada até em
> natures e meta-vazio.

- [x] **BUG-01 [alta]**: **FIXADO 2026-07-10** (decisão owner: `''` = coluna SEM nome). Encode
  TRANSFORMA na fronteira: `''` vira ANONIMA no meta (decode dá o nome posicional; warning
  UserWarning; colisão `''`→`str(pos)` vs coluna existente = ValueError, exceto sob drop_names);
  o meta nunca emite escape-vazio. Decode agora MARCA corrupção (fail-loud): nome DECLARADO vazio
  (`<size>=`), backslash dangling (cauda ímpar), size hex inválido, ganchos do
  [T-TOOL-TCF-FIX-CORRUPTION](T-TOOL-TCF-FIX-CORRUPTION.md). `_esc_name` com guard `s[:1] and`.
- [x] **BUG-02 [alta]**: **FIXADO 2026-07-10** (decisão owner: mínimo de verificação, check
  implícito): parse do meta extraído pra **fonte única `_parse_meta`** em `multi/core.py`; decode E
  view consomem dela → **paridade por CONSTRUÇÃO**, zero verificação extra. Idiom `part[:1] in "!@%"`
  eliminado da view; vars mortas `is_v8` removidas nos 2 arquivos.
> **LOTE 2 EXECUTADO (2026-07-10, aprovação + decisões do owner)**: BUG-03+04+05+06 fixados
> red→green (20 repros novos; o xfail histórico de `encode([])` virou contrato `raises`; suíte
> **566 passed**; pins intactos). Verificação adversarial (3 agentes): byte-neutralidade **189/189**
> (encode sha256 + decode cross-check); refutação de falso-positivo FALHOU em 46 combos íntegros
> (split recursivo, V2-B width 1-2, natures, bordas), e o falso-positivo temido do órfão **fecha por
> construção** (HCC escapa dígito pós-literal: `['#TCF.9M x']` encoda `#TCF.\9M x`, RT ok). Eficácia
> MEDIDA (1474 cortes + 503 flips): truncamento calado-errado **29.2%→3.0%** (fora da zona órfã
> k≤6: 27.5%→**0.6%**; blobs 100%-sized: **0 buracos**); byte-flip loud 42.3%→56.9%; excedente
> sized 0/5→**5/5 loud**. Registros profundos das decisões do owner → **O-FMT-20..23** em
> `futuras-otimizacoes-formato.md` (schema-declare/parquet/tcfx; auto-stamp; #TCF1; completude
> streaming).

- [x] **BUG-03 [média]**: **FIXADO 2026-07-10** (decisão owner: fail-loud por enquanto): encode de
  0 linhas → ValueError nos DOIS ramos (colide com 1-linha-vazia por construção; nada de onde
  deduzir). **Profundo registrado (O-FMT-20)**: registro-'0' declara SCHEMA pro trilho de
  armazenamento append→parquet/tcfx, "visto mais no final".
- [x] **BUG-04 [média]**: **FIXADO 2026-07-10**: versão DEDUZIDA do run completo de dígitos do
  magic, `#TCF.9/.10/.85` → ValueError claro (antes `KeyError: 9` críptico; `.85` nem virava mais
  disc `'5'`); `.6/.7` mantêm a dica de git. **Profundo registrado (O-FMT-21/22)**: auto-stamp no
  encode em colisão de magic; visão owner = subversões são controle de dev, `#TCF1`(M) fecha tudo
  no 1.0, compat real só a partir dele.
- [x] **BUG-05 [média]**: **FIXADO 2026-07-10** (decisão owner: os 3 cheques agora, profundo
  registrado): decode deduz do que o header JÁ declara, (1) size vs bytes disponíveis, (2) fecho
  do blob (excedente), (3) cross-check n_rows (invariante nunca gravado, deduzido de graça). View:
  cheques 1+2 (lazy: sem n_rows, divergência DELIBERADA documentada). Limites conhecidos medidos:
  última-coluna-EOF absorvendo excedente row-consistente (9/1439 cortes) + zona pré-magic do órfão.
  **Profundo registrado (O-FMT-23)**: completude de transmissão/streaming, receptor sabe QUANTO
  esperar, fim-antes-do-aviso, timeout→truncamento; dedução incremental, não só no fim.
  Nota de comportamento: blob `min_header=False` + `\n` final de editor agora é loud (antes decodava
  ignorando; no DEFAULT o mesmo `\n` antes corrompia CALADO com linha fantasma, agora loud).
- [x] **BUG-06 [média]**: **FIXADO 2026-07-10** (sugestão aceita): validação de `\n`/`\r` FUNDIDA
  na passada do `_to_str` em `_encode_multi`, valida o que VAI SER USADO (pós-transformação),
  objetos com `__str__` contendo quebra não furam mais, e o caminho dict perdeu a passada separada
  do guard (1 passada em vez de 2). Ramo list mantém o guard até o lote do BUG-10.
- [x] **BUG-07 [média]**: **FIXADO 2026-07-10** (decisão owner: `body_bytes` é artefato VÁLIDO de
  custo compute/memória, MANTIDO com semântica de candidato documentada; contar NO processo, não no
  fim). Novos campos per-col `emitted_bytes`/`emitted_mode` + `multi_info['col_modes']`, capturados
  **no ponto do min()**: a contagem já existia pro size hex do header, zero passada extra/serialização.
  Nota (verificação): telemetria keyed pelo nome de ENTRADA (`''` na telemetria ↔ `'0'` no decode):
  documentado no código; consumidor cruza via posição.
> **LOTE 3 EXECUTADO (2026-07-10, aprovação + decisões do owner)**: BUG-08(fold)+09+10+11b fixados
> red→green (16 repros novos; suíte **582 passed**; pins intactos). Verificação adversarial
> (2 agentes): refutação FALHOU em ~310 checks (100 nomes fuzz + 36 dirigidos: **zero** blob
> legítimo rejeitado pela whitelist; `_ESC_OK` cobre exatamente o que `_esc_name` emite);
> byte-neutralidade **103/103** + `parallel=1 ≡ serial` provado byte-a-byte + decode cross-check.
> Filosofia (owner): fronteiras = **ISOLAMENTO**, o código identifica os casos, comportamento
> re-decidível depois → [T-API-BOUNDARY-CONTRACTS](T-API-BOUNDARY-CONTRACTS.md) (pré-1.0);
> integridade do meta → [T-FMT-META-STRICT](T-FMT-META-STRICT.md).

- [x] **BUG-08 [baixa]**: **FIXADO 2026-07-10** (fold no strict; ticket de revisão mantido):
  `decode('#TCF.8M\n')` (meta vazio SEM body, não-emitível, verificado: 1-linha-vazia emite
  `#TCF.8M!\n`) → ValueError em decode E view (paridade); meta vazio COM body segue legítimo
  (1 col anônima tcf). Semântica definitiva do vazio → T-API-BOUNDARY-CONTRACTS + O-FMT-20.
- [x] **BUG-09 [baixa]**: **FIXADO 2026-07-10**: str/bytes como valor de coluna → TypeError que
  ensina (`envolva em [...]`). Sem auto-embrulho (duas leituras possíveis → declarar > deduzir).
- [x] **BUG-10 [baixa]**: **FIXADO 2026-07-10** (os 7 sub-itens): (a) list converte não-str via
  `_to_str` (= semântica dict, None→''; check de quebra fundido na mesma passada; guard antigo
  `_reject_linebreaks` removido, absorvido nos 2 ramos); (b) `layers` valida PipelineConfig;
  (c) `parallel` negativo/tipo → erro, **`parallel=1` → serial DEDUZIDO** (sem spawn; 1 worker ≡
  serial por construção, provado byte-a-byte); (d) `decode(não-str)` → TypeError; (e) `name=` sem
  nature (ou com dict) → ValueError; (f) `stamp`+dict segue ignorado (M já é o stamp, semântica
  correta, documentar em F6); (g) `nature=`+dict / `nature_per_col=`+list → ValueError cruzado.
  Nota da verificação: `parallel=-1`/`2.0` eram tolerados fora-de-contrato no HEAD, agora erro
  (intencional). Revisão profunda dos contratos (tipos anterior/próximo, diffs, specs) →
  T-API-BOUNDARY-CONTRACTS pré-1.0.
- [x] **BUG-11 [média]** *(parte 3: resíduo (a) ADIADO com rótulo → T-FMT-META-STRICT)*: **(b) FIXADO 2026-07-10 (lote 3)**: whitelist de escape `_ESC_OK =
  ",=:\\!@%"` no `_unesc_name_strict`, escape de char não-estrutural (não-emitível) → ValueError;
  dangling integrado no mesmo scan. **(a) coberto em 2 camadas**: o caso comum do `\` inserido é
  pego pelo fecho/n_rows do lote 2 (medido); o residual geometricamente-consistente é
  indistinguível por construção → **checksum** no trilho tcfx/O-FMT-20. Vínculos e decisões
  restantes → [T-FMT-META-STRICT](T-FMT-META-STRICT.md).
- [x] **BUG-12 [alta]** *(registrado 2026-07-10 pela verificação do lote 2: PRÉ-existente, NÃO é
  regressão)* **CORRIGIDO pelo weld `25ad29eb` (2026-07-24), provado por antes/depois em
  2026-09-02** — lab `experiments/lab/dirty/2026-09/2026-09-02/2026-09-02-0102-bug12-existe-ou-obsoleto/`:
  a mutação abaixo pendura o código pré-guard e vira `ValueError` em ~3 ms desde o commit do
  guard; 165 fronteiras deslocadas sem nenhum hang no HEAD. Registro original: **DoS por
  não-terminação no decode HCC sob header corrompido**: 1 flip de
  hex-digit num size (`52=b`→`12=b`) desloca a fronteira das colunas e a fatia deslocada gira em
  `composicional/syntax.py:718` (`_parse_decl`, >1000s CPU medidos) DENTRO de `_decode_column`:
  antes do cross-check n_rows alcançar. Pior modo de falha (nem loud, nem errado: nunca retorna).
  Fix futuro toca o CORE HCC (guard de terminação/progresso no decode) → aprovação + gate
  byte-canônico completo + real-world obrigatórios.
- [x] **BUG-13 [média]** *(parte 3: resíduos (a) e (c) ADIADOS com rótulo → T-FMT-META-STRICT)*: **(b)(d)(e) FIXADOS 2026-07-10 (lote 4, "vamos fechar os A")**:
  (b) nature-id desconhecido → **ValueError** em decode (multi+single) E view. REVOGA o
  forward-compat de 2026-06-24 (2 testes re-pinados com rastreabilidade; pre-1.0 sem compat,
  ADR-0024); (d) **cross-check incremental na view**: `_col()` compara `len` com qualquer coluna
  já materializada (ints, custo zero, laziness intacta), view não materializa mais dado errado
  calado em blob EOF-truncado; (e) invariantes internas dos slots: V2-B (`ntable` bound, stream
  múltiplo da width, **índice dentro da tabela**: o byte de editor virava índice NEGATIVO e
  wrapava a tabela em silêncio) + split (`ntmpl` bound) + `_dict_parts` da view (paridade L3/L4).
  8 repros novos; suíte **590 passed**; encode intocado (lote decode-only, pins por construção).
  **Restam (a)(c)**: flips nome/size geometricamente consistentes, só checksum (trilho
  tcfx/O-FMT-20, via [T-FMT-META-STRICT](T-FMT-META-STRICT.md)).
- [x] **BUG-14 [alta · domínio válido · gate R0 do `.8`]** *(FEITO 2026-07-12, lote A)*,
  o decoder dos dois níveis foi alinhado ao contrato LF-only (remoção de `splitlines()` em favor
  de split exclusivo por `\n` em `src/tcf/composicional/syntax.py` e
  `src/tcf/composicional/hcc_seqrle.py`). Prova red→green adicionada em
  `tests/test_core_rt.py` com 10 casos parametrizados (single+multi para `\v`, `\f`, NEL,
  `U+2028`, `U+2029`). Execução: red inicial `5 failed, 5 passed`; pós-fix `10 passed`; gates
  `tests/test_core_rt.py` + `tests/test_regression_v1_baseline.py` +
  `tests/test_real_world_snapshots.py` = `104 passed`.
- [x] **BUG-15 [alta · domínio válido]**: **FIXADO 2026-07-12** (owner: "fixe o bug-15"). Literal
  começando com `^` (marcador de ref do HCC) quebrava o RT em tcf/dict (crash em não-dígito,
  **corrupção SILENCIOSA em `^12`**: lido como ref pro eid 12); raw sobrevivia. Causa: `_escape_lit`
  escapava `*`-líder (`\*`) mas não `^`. Fix cirúrgico em `composicional/syntax.py` `_emit_body`:
  `^`-líder de linha → `\^` (ref-runs começam com dígito, nunca `^`, então só literal-líder colide);
  o decode de-escapa via `_parse_decl` (mecanismo `\` já existente). **6 repros red→green** em
  `tests/test_core_rt.py::TestBug15CaretLeadingLiteral` (tcf/dict/dígito-silencioso/multi-col/só-caret/
  mid-string-byte-neutro). **Byte-NEUTRO**: suíte **616 passed**, pinos 1523/300/89616 exatos, Cython
  inalterado (fix no emit, não em `_detect_compositions`). **Destrava o CEILING** dos specs
  (nature-delta/field-split podia produzir base-94 `^`-líder). Achado SÓ porque o lab exigiu RT
  end-to-end, a lição do §RT do owner, com bug real capturado.

- [x] **BUG-16 [alta · fronteira pública de spec]**: **FIXADO 2026-07-12**. A API aceitava um
  `TemplatedCheckedSpec` customizado, emitia `:id` no header e depois rejeitava o próprio blob no
  `decode(..., nature=spec)` porque o `SPEC_REGISTRY` core é fechado. Agora o registry core continua
  autoritativo; para IDs externos, o decode aceita somente um spec out-of-band cujo `name` coincide
  exatamente com o ID do header. Ausência ou divergência permanece fail-loud. Regressões single+multi
  em `tests/test_natures.py` e `tests/test_nature_compete.py`; suite final **634 passed, 2 skipped**.

### Doc-drift 0.7→0.8 (bloqueia o "documento bem feito pro pip": corrigir em F6 com números medidos)

- [x] **DOC-01 [alta]** *(feito; parte 2)* `README.md` (embarcado como long-description da wheel!): badges 0.7.1/#TCF.7;
  exemplo-propaganda mostra `#TCF.7 M` decimal 244B, real 0.8: `#TCF.8M!2c=nome,...` hex **242B**
  (medido); "legacy #TCF.6 still read" (CORTADO); knob "forces legacy #TCF.6" (impossível);
  nature 27B → **39B** (header self-describing +12B que não existia); nega o marker self-describing
  que a 0.8 ENTREGA ("target 0.8", já shipou); D17a 303/322 → **300**; "379 passed" → 530;
  seção "Format 0.7 (default)" inteira; view apontando pro gadget `scripts/tcf_lazy/` (hoje core).
- [x] **DOC-02 [média]**: **FEITO 2026-07-10** (lote 4 + lotes anteriores): docstrings de `src/tcf`
  corrigidas, `__init__.py` (formato #TCF.8 default, dispatch real, D17a 300B com eras no git);
  `decoder.py` (lote 2); `encoder.py` (Args completos: parallel semântica nova, nature
  self-describing, name/stamp/drop_names documentados; Raises real, nomes com separador são
  ACEITOS/escapados); `multi/core.py` (módulo: contratos de fronteira pós-M2/F0; `_encode_multi`:
  fallback/min_header sem promessa de #TCF.6); `dict_v2b.py` (meta #TCF.8M hex; data do weld
  07-02); `view.py` (lê SÓ #TCF.8M; parser único); `natures/__init__.py` (exemplo self-describing,
  decode sem spec); vars mortas `is_v8` removidas (lote 1); `tests/test_tcf_lazy.py`. **Nota**: tudo
  que depende de NÚMERO MEDIDO (README/exemplo/curvas) segue no F6/DOC-01.
- [x] **DOC-03 [média]** *(feito; parte 2)* `docs/algorithms/TCF-format.pt-BR.md:94`: exemplo `@a=uf,1e=nome` mostra
  size na ÚLTIMA coluna contradizendo a própria regra (última sem size); equivalente real:
  `#TCF.8M@14=uf,!nome`. Conferir o .en.md no mesmo ponto.
- [x] **DOC-04 [baixa]** *(feito; parte 2)* `pyproject.toml`: wheel 0.8.0 sem `[project.urls]` e sem classifiers
  (página PyPI sem link pro repo/changelog); readme apontado é o stale do DOC-01.
- [x] **DOC-05 [baixa]** satélites — **feito 2026-09-02**: `benchmark_compression.py` já parseava
  sem resíduo v0.5; `benchmark_parallel.py` ganhou warmup + mediana (`--runs`); tabelas do
  `datasets/synthetic/README.md` completadas (D11f–D11m; título já dizia D1–D17); `metadata.json`
  dos canônicos já tinham `row_counts`; a row do T-FMT-NAME-ESCAPING já estava CLOSED-PARCIAL;
  o `run.log` untracked virou moot (dirty/ fora do git desde 2026-08-22).

## §4: FASES (microtarefas na ordem; cada fase fecha antes da seguinte)

### F0: Gate de entrada: decisões do owner + lote de fixes (pré-medição)

- [x] **F0-1** *(parte 3: feito; o BUG-12 que restava foi corrigido pelo weld `25ad29eb`)* Owner decide o lote de fix pré-medição (toca `src/tcf` → aprovação explícita).
  **LOTES 1-4 EXECUTADOS 2026-07-10** (BUG-01..11b + 13b/d/e + DOC-02; decisões de design do
  owner, ver §3; byte-neutro 122+189+103 casos; eficácia medida 1474 cortes). **Resta**: só
  **BUG-12** entre os achados originais (hang HCC sob blob corrompido) e os residuais-de-checksum
  13a/c (trilho tcfx, T-FMT-META-STRICT). O BUG-14 foi descoberto depois do F2 e entra no gate
  R0 separado abaixo, não reabre historicamente os lotes F0.
- [x] **F0-2** Suíte completa + gates pós-lotes: **590 passed** (530 + 60 repros F0), D1-D9=1523B /
  D17a=300B / real-world=89616B intactos (byte-neutralidade provada em 414 casos fora dos pins;
  lote 4 é decode-only+docstrings, encode intocado por construção).
- [x] **F0-3** Dependência de medição: **stdlib-only E PORTÁVEL** (owner 2026-07-10): a telemetria
  é feita de **CONCEITOS independentes de OS/hardware/linguagem**: fáceis de identificar e de
  transportar (ex.: Rust), e, ficando em Python, tem que rodar **em qualquer lugar que o Python
  rode** (nada engessado). Arquitetura do runner (F1):
  - **Camada de conceitos** (portável, é a interface): `wall_time_ns`, `cpu_time_ns`,
    `peak_heap_bytes`, `peak_rss_bytes`, `bytes_in/out`, `rt_ok`, `env_fingerprint`, nomes/
    semântica que um port Rust implementa 1:1 (`Instant`, `jemalloc stats`, `/proc`/`GetProcessMemoryInfo`).
  - **Sondas** (adaptadores ISOLADOS e rotulados por plataforma): tempo/heap = stdlib pura
    (`perf_counter_ns`, `tracemalloc`, rodam em qualquer Python); `peak_rss` = melhor-esforço por
    plataforma (`resource.getrusage` em POSIX; psapi via ctypes SÓ no adaptador win32) com
    **fallback gracioso `None`**: medição NUNCA quebra por plataforma, o campo fica ausente e
    o relatório declara qual sonda rodou.
  - Workers do ProcessPool: inobserváveis via stdlib em QUALQUER OS → claims de paralelismo =
    wall-clock + byte-identidade + `parallel_workers` (conceito portável). psutil só como
    `[bench]` opcional se o F3 provar necessidade (go do owner).
- [x] **F0-3** *(duplicata: decidido em 2026-07-10, stdlib-only e portável, no F0-3 acima)* Owner decide: psutil como optional-dependency de bench (`[bench]`) ou stdlib-only
  (recomendação: stdlib-only nesta rodada; psutil só se F3 mostrar necessidade).
- [x] **F0-4** *(sem objeto desde 2026-09-02: o script já parseia e o `run.log` ficou em dirty/, fora do git)* Higiene mecânica sem-risco: rotular `benchmark_compression.py` como quebrado-v0.5
  (comentário topo), decidir destino do `run.log` untracked (add ou ignore).

### F1: Harness de telemetria (fora de src/tcf; é a régua de TODAS as fases seguintes)

> **F1 FEITO 2026-07-11/12 (T-REL-08 Passo 2a)**: `scripts/bench_evidencia.py` (runner) +
> `scripts/bench_evidencia_probes.py` (conceitos portáveis F0-3: sondas isoladas por plataforma,
> fallback gracioso, sonda RSS ativa nesta máquina: `k32-getprocessmemoryinfo`). 10 testes-guarda
> em `tests/test_bench_evidencia.py`; suíte **600 passed**. Verificação adversarial (2 agentes,
> passa-com-ressalvas → ressalvas FECHADAS): isolamento OS-specific confinado às sondas (grep
> limpo), fallback sem sonda = campo AUSENTE (não crash), registro JSON-portável; protocolo
> auditado POR EXECUÇÃO, RT-gate real (decode adulterado → registro sem números), mediana/p95
> conferidos contra statistics, timing NÃO roda sob tracemalloc (5.3× de overhead evitado,
> medido), validate_pins pega inflação de +1B. **Achado fechado**: idempotência sozinha aceitava
> decode-constante → RT de transformação agora = **conteúdo-sob-transformação (multiset de
> linhas / valores posicionais) + idempotência 2ª geração** (teste pinado). Notas de honestidade
> gravadas: heap=Python-only (cross-linguagem usa RSS); Solaris ru_maxrss em páginas → sonda
> se declara indisponível.

- [x] **F1-1** runner: CSV single/multi (mesma carga da régua), kwargs parametrizáveis, JSONL com
  bytes/RT/rt_mode/determinismo/timing(mediana+p95, n≥9+warmup)/memória(runs separadas)/side/env.
  (Hub via DatasetReader entra no F4, quando os públicos rodarem.)
- [x] **F1-2** `serialize_side` externo (BUG-07 já welded: usa emitted_bytes/col_modes direto;
  traces opt-in).
- [x] **F1-3** `experiments/results/evidencia-0.8/<fase>/<dataset>.jsonl` + `.tcf` via
  `--save-blob` + README com schema `evidencia-0.8/v1`; exceção no .gitignore (outputs visíveis,
  `phase0/reversibility.json` intocado).
- [x] **F1-4** `--validate-pins`: D1-D9=**1523** · D17a=**300** · real-world=**89616**, exatos;
  também é teste da suíte (roda em todo pytest).

### F2: Controle minúsculo (o owner começa AQUI: single-col, com/sem header, readers, README)

> **F2 FEITO 2026-07-12 (T-REL-08 P2b)**: driver reprodutível `scripts/bench_evidencia_f2.py` →
> **29 casos, RT 29/29**, material em `experiments/results/evidencia-0.8/f2/` (JSONL + 13 blobs
> `.tcf` inspecionáveis + `RESULT.md` GERADO). Régua re-validada antes da rodada. Leituras-chave
> (medidas): custo de header no MESMO dado = órfão **0B** → stamp **+7B** → M-1col **+13B**;
> README default **242B** (era 244 no 0.7, número pro F6); drop_names 215B; `parallel=2`
> byte-idêntico mas mediana 423ms vs 2ms serial (spawn por chamada, dado pro T-CODE-PARALLEL-BUDGET);
> view toca **14.5%** do corpo num group_count; **boundary do cap V2-B**: K=8192→dict 98005B
> (5.0s) vs K=8193→tcf 113296B (2.7s) = **13.5% de bytes deixados na mesa acima do cap** por
> ~metade do compute (a caracterização que faltava pro V2B-DESCAPAR-B/C do .9). **ACHADO (o gate
> §2.3 pegou)**: os placeholders do README (dígitos repetidos) são **mod-11-VÁLIDOS**, o spec
> COMPRIME (apply_rate 1.0); a "invalidade" deles é convenção de cadastro → nota obrigatória no
> F6/README; fallback-path publicável agora usa a ANONIMIZAÇÃO da regra do owner ((dv+1)%10).

- [x] **F2-1** órfão (emails 32B, D1 118B = régua); view() não cobre órfão: na matriz.
- [x] **F2-2** 3 formas de header medidas no mesmo dado (0/+7/+13B; spec medido em e5-e7).
- [x] **F2-3** matriz decode×view: 8 formas, paridade "igual" em todas as M; órfão/stamp/spec =
  fail-loud por design; seletividade L3 demonstrada (14.5%).
- [x] **F2-4** README re-medido: default **242B** + 5 variantes (tabela pronta pro F6).
- [x] **F2-5** escaping/hex-borda(`f`/`10`/3-dígitos)/fail-loud paramétrico (6 blobs, todos
  loud)/multi-1col/anônima-última/só-vazias.
- [x] **F2-6** 1 blob por mecanismo: V2-B w1+w2, split `%`, HCC implícito, natures cpf/cnpj/ip
  (válidos EFÊMEROS apply_rate==1.0, sem blob salvo; misto 0.5; anonimizado 0.0 publicado).
- [x] **F2-7** boundary 8192/8193 medido (acima).

### F3: Sintéticos maiores (escala controlada)

> **Gate R0 cumprido (2026-07-12, lote A)**: BUG-14 fechado red→green com suíte/pinos já
> executados no lote técnico. F3 está liberado; BUG-12/corrupção segue em 0.8.1.

> **Update 2026-07-12 (decisão de escopo do closeout `.8`)**: execução massiva foi interrompida
> e consolidada como **amostra**. Foi gerado
> `experiments/results/evidencia-0.8/f3/RESULT.md` com cobertura parcial explícita: F3-1 = 31/31,
> F3-2 = 10/10, F3-3 = 9 casos (faltaram 7), F3-4 = 0. Registro formal: não-população total nesta
> etapa; retomada completa fica para janela dedicada, sem bloquear o fechamento do núcleo `#TCF.8`.

- [x] **F3-1** Suite D1-D17 completa (31 CSVs) no runner: tabela única; stress (D10/13/14)
  SEPARADO de design-realista na apresentação.
- [x] **F3-2** Curva de escala com `tests/fixtures/synthetic_domains.py` parametrizado:
  n ∈ {20, 100, 1k, 10k, 100k} single e multi (fecha o buraco 20→2000 que não existia);
  bytes/linha, tempo/linha, memória vs n, onde o ganho TCF "liga" (README hoje afirma isso sem curva).
- [x] **F3-3** *(parte 3: ADIADO p/ o `.9` com rótulo → T-CODE-PARALLEL-BUDGET)* Paralelismo (a verificação pedida pelo owner):
  (a) byte-identidade parallel==serial nos REAL-WORLD snapshots (hoje só D17a);
  (b) speedup vs workers {serial,2,4,8} em multi-col grande (tpch/adult via hub), mediana n≥9;
  (c) MEDIR a porção serial pós-pool (fase de candidatos V2-A/B/split), % Amdahl documentada;
  (d) combos sem cobertura: parallel × natures_per_col × sort_by × drop_names (byte-identidade);
  (e) registrar limitações honestas: decode serial, Cython sem nogil (3.13t re-ativa GIL), IPC spawn.

> **Atualizado 2026-09-01 (0.8.4)**: o eixo `natures_per_col` do item (d) não existe mais. A
> [ADR-0047](../docs/adr/0047-schema-parametro-unico-de-spec.md) trocou `nature=` e
> `nature_per_col=` por um `schema=` único, e hoje `encode(..., nature_per_col={})` levanta
> `TypeError: encode() got an unexpected keyword argument 'nature_per_col'`, o mesmo para
> `natures_per_col=` e para `nature=`. O combo continua válido, com o nome novo:
> **parallel × `schema` × `sort_by` × `drop_names`**.
>
> A mesma troca aposenta o item (g) do BUG-10 no §3, que pinava o `ValueError` cruzado entre
> `nature=`+dict e `nature_per_col=`+list: os dois kwargs sumiram, então o cruzamento não tem
> mais como acontecer. O `schema=` escalar pôs a regra no lugar simétrico, verificado por
> execução nas duas grafias: uma coluna aplica (`{'d': [...]}` e `[{'d': ...}]` vão os dois pro
> wire com `:dt` no header), duas ou mais levantam nas duas com a mesma frase ("schema escalar
> ('id'/objeto) aplica a single-col (list) ou tabela de UMA coluna; com 2+ colunas use
> schema={coluna: spec}").
>
> Cuidado ao reprogramar o (d): o `sort_by` deixou de ser ordem garantida. A
> [ADR-0050](../docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md) fez dele um CANDIDATO,
> o encoder emite as duas versões e fica com a menor, então um teste de byte-identidade tem de
> comparar parallel contra serial, nunca contra "a versão ordenada".
- [x] **F3-4** *(parte 3: ADIADO p/ o `.9` com rótulo → T-PERF-BORDAS-E-MODOS-09)* br-identidades (600k, DV-válido seed 20260601): natures em volume, apply_rate==1.0,
  medição efêmera (§2.3), CPF/CNPJ/IP nos 3 codepaths (spec, fallback, misto).

### F4: Públicos (bench)

> **F4-MÍNIMO FEITO 2026-07-12 (T-REL-08 R1/2d)**: driver `scripts/bench_evidencia_f4.py`,
> 9 casos nos hubs PRONTOS, **RT 9/9** + determinístico; material em
> `experiments/results/evidencia-0.8/f4-minimo/` (RESULT.md gerado). Amostras determinísticas
> "primeiros 5000" (população total = janela dedicada pós-release, decisão ROI). Δ vs CSV medido:
> adult **81.1%**, ibge **68.5%**, receita-real **62.4%**, lineitem-free-text **50.2%**,
> br-empresas+cnpj **55.3%**. Sinal zlib9 sempre menor no TCF (brotli indisponível no venv → sonda
> graciosa registrou ausência). **ACHADO FORTE (repro)**: a **nature CNPJ PIORA em dado REAL**:
> receita 100121B → 107460B (+7339B) COM `:cnpj`: a coluna cai de `split` (32665B) pra `raw`
> (39999B), porque o corpo base-94 da nature DESTRÓI a estrutura (matriz/filial, prefixos
> compartilhados) que o split/dict já explorava. No SINTÉTICO (br-empresas) a mesma nature AJUDA
> (55.3%). É o gap sintético-vs-real (anti-incidente 2026-05-21) com medição, **reforça a Opção A
> do [T-SPEC-STATUS-08](T-SPEC-STATUS-08.md)** e é caveat obrigatório pro F6 (nunca claimar nature
> CNPJ como ganho geral).

- [x] **F4-1** hubs prontos medidos (adult 48842→5k, tpch-sf001 lineitem 60175→5k + customer FULL
  1500, ibge FULL 5571, br-identidades pessoas/empresas 5k, receita-cnpj 200k→5k). tpch-sf01 600k =
  janela dedicada.
- [x] **F4-2** *(parte 3: ADIADO p/ o `.9` com rótulo → T-PERF-BORDAS-E-MODOS-09)* os 3 hubs faltantes (online-retail/beijing/wine): **não no mínimo**; janela
  dedicada pós-release (os CSVs já viram no gate real-world via `datasets/samples/`).
- [x] **F4-3** matriz medida (bytes total/header/body + RT + timing indicativo + zlib9 sinal);
  brotli fica pra venv com brotli (sonda registra ausência, F0-3).
- [x] **F4-4** *(parte 3: ADIADO p/ o `.9` com rótulo → T-PERF-BORDAS-E-MODOS-09)* consolidação: RESULT.md por fase pronto; a tabela-mestra cross-fase + nota Wohlin
  entra no F6 (junto do README).

### F5: Otimização extra (janela pós-evidência; SÓ o que a telemetria apontar)

- [x] **F5-1** *(MOVIDO p/ o `.9`: T-PERF-BORDAS-E-MODOS-09, seção "Recebido do T-QA-8")* Triagem dos candidatos COM dado das fases F2-F4 (esperados: porção serial pós-pool;
  parallel=1/negativo; custo do obat_log/hcc_trace incondicional; V2-B width≥2). Cada candidato
  vira sub-exp/ticket próprio com gate T-REGRESSION-REAL-WORLD. NENHUM weld dentro deste ticket.

### F6: Empacotar pro pip com documento bem feito

> **PLANO DETALHADO (owner pediu revisar como o F6 será feito, 2026-07-12)**: o F6 é
> doc-only + build (NÃO toca `src/tcf`); tudo com número MEDIDO do material (F2/F4), nada calculado.
> Ordem e arquivos:

- [x] **F6-1a: README.md/README.pt-BR.md (o que embarca na wheel; DOC-01)** *(feito; parte 2)*: substituir os números
  da era 0.7 pelos medidos: exemplo-propaganda **244B→242B** (F2 c1); badges `0.7.1`→`0.8.0` e
  `#TCF.7`→`#TCF.8`; header do exemplo `#TCF.7 M` decimal → `#TCF.8M` hex; remover "legacy #TCF.6
  still read" e o knob "forces #TCF.6" (cortado); D17a 303/322→**300**; "379 passed"→número atual;
  seção "Format 0.7" → "Format 0.8"; view aponta pro core (não `scripts/tcf_lazy/`). **Nature: o
  bloco muda de história**, o exemplo do README ainda diz que CPF "does not compress" e usa
  nature 27B→39B; substituir pela leitura HONESTA do F2/F4: nature CPF comprime em sintético MAS o
  **caveat obrigatório** = "nature CNPJ PIORA a tabela em dado real (F4: +7339B, split→raw); nenhum
  clássico é ganho de tabela garantido, o TCF já explora a estrutura inter-linha que a nature
  normalizaria". Tabela "Results" com os Δ vs CSV reais (adult 81%, ibge 68%, receita 62%).
- [x] **F6-1b: docstrings src/tcf** *(feito; parte 2)*: DOC-02 já FEITO (lote 4); só re-conferir que nada regrediu.
- [x] **F6-1c: spec docs/algorithms/TCF-format.{pt-BR,en}.md (DOC-03)** *(feito; parte 2)*: exemplo de header que
  contradiz a regra (última-sem-size mostrando size); corrigir com o output real.
- [x] **F6-1d: pyproject.toml (DOC-04)** *(feito; parte 2)*: adicionar `[project.urls]` (repo/changelog/homepage) +
  trove classifiers; conferir que o readme apontado é o corrigido.
- [x] **F6-1e: satélites (DOC-05)**: **feito 2026-09-02** (ver tabela §3): benchmark_compression
  já parseava; benchmark_parallel com warmup+mediana; synthetic README D11f–m; row_counts e a
  row NAME-ESCAPING já estavam certos. A errata T-DOC-3 (shebang→magic) fica com a fase F6.
- [ ] **F6-1f: CHANGELOG.md** *(parcial; aguarda a decisão (a), (b) ou (c) da parte 2)*: conferir a entrada 0.8.0 (já criada em M5) + anexar os fixes F0
  (lotes 1-4) e o C0 (dedup) como itens do 0.8.0.
- [x] **F6-2** *(feito; parte 2: smoke da release em venv limpo, run da v0.8.4 com success)* Re-build wheel + clean-room smoke (protocolo pré-verificado 2026-07-09, T-DIST):
  agora com F0/C0 + docs F6-1; limpar `dist/` (wheels 0.7.1 stale) antes.
- [x] **F6-3** *(feito; parte 2: tags v0.8.0 a v0.8.4 e PyPI)* Publicação = T-DIST C3 (tag v0.8.0 → Trusted Publishing), **go explícito do owner**.
  Avaliar 0.8.0 vs 0.8.1 no CHANGELOG se F0/C0 mudaram comportamento observável (mudaram: fail-loud
  novos, decidir se é minor-note ou espera 0.8.1).

**Pré-F6 (redirect owner 2026-07-12)**: a investigação de specs (R1.5 do T-REL-08) roda ANTES, o
F6 herda dela o caveat definitivo da nature e qualquer decisão de spec pré-1.0. Ver
[T-SPEC-STATUS-08](T-SPEC-STATUS-08.md) (Opção A decidida) + o plano de specs em curso.

## §5: Critérios de aceite

- [x] *(parte 3: feito)* Todo número do material rastreia a um artefato JSONL reproduzível (runner+seed) com RT validado.
- [x] *(parte 3: feito, F2-6)* Os 3 dicts welded + natures têm blob-exemplo inspecionável e medição própria; os de lab
  documentados como research (sem claims de produto).
- [x] *(parte 3: ADIADO p/ o `.9` com rótulo → T-CODE-PARALLEL-BUDGET)* Paralelismo verificado: byte-identidade em real-world + curva de speedup + % serial medida +
  limitações registradas.
- [x] *(parte 3: feito)* Telemetria em 2 famílias (SideOutputs + free) com as ressalvas Windows documentadas.
- [x] *(parte 4: DISPENSADA pelo owner em 2026-09-05, não cumprida)* Regra CPF cumprida: nenhum artefato publicado contém CPF DV-válido (nem em `.tcf`).
- [x] *(parte 3: feito, com resíduos adiados com rótulo)* Bugs do §3: todos ou fixados (F0, sob aprovação, red→green) ou explicitamente adiados com rótulo.
- [x] *(parte 2: feito)* README/docstrings/spec sem promessa que a 0.8.0 não entrega (F6-1) ANTES do go de publicação.

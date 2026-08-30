# STATUS: TCF

**O estado VIGENTE.** Este arquivo diz o que É, não o que foi (invariante **I1** do
[`AGENTS.md`](AGENTS.md) §0: a superfície carrega só o presente). A história vive no **git**,
no [`CHANGELOG.md`](CHANGELOG.md), nos [ADRs](docs/adr/README.md) e no diário
(`experiments/lab/dirty/notas/diario/`).

> Até 2026-08-23 este arquivo acumulava um bloco `⚑ SOLDADO <data>` por sessão, e nada saía:
> 1083 das 1523 linhas eram histórico empilhado antes da primeira seção, o erro que a própria
> I1 nomeia (*append-only* aplicado à superfície). Nada se perdeu: cada bloco corresponde a
> commits, ADR e diário.

## Agora

| | |
|---|---|
| **publicado** | `tcf-format 0.8.2` no PyPI (25/08, via Trusted Publishing) · tag `v0.8.2` |
| **preparado** | `0.8.3` no repo (versão, CHANGELOG e índices); tag e push aguardam go do owner |
| **formato** | `#TCF.8` default: `.8M` multi-col · `.8H` hierárquico · rota tipada · single-col |
| **ciclo aberto** | **`.9`**: otimização **e** integração com armazenamento |
| **números vivos** | nos TESTES, não aqui: `pytest -q` |
| **gates** | `test_regression_v1_baseline.py` (D1-D9, D17a) + `test_real_world_snapshots.py`, os dois obrigatórios (§4) |

A superfície pública está **congelada por teste**: assinaturas de `encode`/`decode` e a lista
de exports em `tests/test_regression_v1_baseline.py`. Mudar exige re-pin deliberado.

## Em curso: o `.9`

O ciclo está descrito em [`ROADMAP.md`](ROADMAP.md) (três eixos: desempenho e bordas, armazenamento e ecossistema, limpeza). Fila de tickets em
[`tickets/README.md`](tickets/README.md).

### Cauda do `.8`: a auditoria de consistência (2026-08-27/28)

As três famílias de wire foram medidas em cinco eixos e discordavam em quase toda borda
([nota](experiments/lab/dirty/notas/2026-08/2026-08-27-consistencia-tres-familias.md)).
Quatro ondas soldadas, com evidência em disco e sem re-pin de bytes:

| onda | o que mudou | ticket |
|---|---|---|
| 0 | o `.8M` passou a usar o **mesmo juiz de homogeneidade** do `.8H` (`_scalar_type`) antes de aceitar a tabela | [`BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA`](tickets/BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA.md) closed |
| 1 | `decode_value` antes de `_dec_scalar` no `.8M`: a nature deixa de ser atropelada pelo cast | (junto da onda 0) |
| 2 | `_unesc_leaf` no ramo string da `view` do `.8H` | (junto da onda 0) |
| 3 | `_n_somado` pergunta se o corpo é **ausente** antes de tirar o terminador | [`BUG-VIEW-UMA-STRING-VAZIA`](tickets/BUG-VIEW-UMA-STRING-VAZIA.md) closed |

Em 2026-08-28 entraram as ondas 5 a 7, com evidência em
[`2026-08-28-0200-cauda-das-divergencias`](experiments/lab/dirty/2026-08/2026-08-28/2026-08-28-0200-cauda-das-divergencias/):

| onda | o que mudou | ticket |
|---|---|---|
| 5 | `view`: `#O` desigual recusado na abertura; órfão sem magic aceito (paridade com o `decode`); corpo ausente é zero linha; aviso no primeiro `nrows` quando as contagens estruturais divergem | [#7](tickets/BUG-VIEW-OBJETO-NAO-RETANGULAR.md), [#13](tickets/BUG-VIEW-ORFAO-SEM-MAGIC.md), [fantasma](tickets/BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA.md) closed |
| 6 | chave não-str cai no `.8H` (erro tipado por construção); `.8H` ganha a telemetria de spec das outras duas e avisa no descarte por valor | (sem ticket: #14b, #15) |
| 7 | **muda wire**: coluna escalar densa-com-nulos no `.8H` declara `?0:` (emask 2-estados) em vez de `?:`; a `view` passa a consultar tabela com nulos; +1 byte de header por coluna assim; 2 pinos de navegação re-pinados, zero nos gates | [#6](tickets/BUG-VIEW-NULO-NO-HIERARQUICO.md) closed |

Ficaram **seis decisões de dono**, cada uma colidindo com um contrato ratificado, com
evidência medida em
[`2026-08-28-decisoes-de-dono-cauda-do-8.md`](experiments/lab/dirty/notas/2026-08/2026-08-28-decisoes-de-dono-cauda-do-8.md):
união bool+str, LF/CR, FLOOR do spec, spec em coluna tipada (a seta da auditoria estava
invertida), kwargs engolidos no flat de string e `decode(schema=)` ignorado.

**A `0.8.2` publicada contém os defeitos das ondas 0 a 7**, e a `0.8.3` preparada os
corrige. A atualização muda comportamento visível: entrada mista que passava calada agora
levanta, e o wire do `.8H` com nulo denso mudou de grafia.

Compatibilidade, medida nos dois sentidos: a `0.8.3` lê **tudo** que a `0.8.2` emitiu; a
`0.8.2` **não** lê o `.8H` denso-com-nulos da `0.8.3`, e falha alto em vez de ler errado.
ADR-0024: minors pré-1.0 não carregam garantia entre si, e o leitor antigo recusar é o
comportamento certo diante de grafia que ele não conhece.

## Onde achar o quê

| pergunta | fonte |
|---|---|
| o que mudou entre versões | [`CHANGELOG.md`](CHANGELOG.md) |
| por que se decidiu assim | [`docs/adr/README.md`](docs/adr/README.md) |
| o que está aberto | [`tickets/README.md`](tickets/README.md) |
| como usar | [`docs/`](docs/) · [`README.md`](README.md) |
| regras de trabalho | [`AGENTS.md`](AGENTS.md) (comece pela **§0**) |
| onde fica cada coisa | [`MAP.md`](MAP.md) |
| a narrativa de uma sessão | `experiments/lab/dirty/notas/diario/` (fora do git desde 22/08) |

## Escala de verificação (decisão de processo, vigente)

**E0** ingênuo · **E1** round-trip · **E2** assimetria · **E3** fail-loud barato ·
**E4** canonicidade · **E5** adulteração ("homem no meio").

**`.8` = E1/E2 obrigatórios + E3 (custa zero) + E4 quando trivial. `.9` = E4
sistemático + E5 opt-in.** Evidência: **4 dos 6 bugs catastróficos do ciclo eram
E1/E2**, os únicos alcançáveis por `encode→decode`. Orçamento de auditoria vai pra
round-trip e assimetria, não pra wire escrito à mão. Ressalva do próprio `malloc`:
ele não pré-verifica, mas devolve `NULL`. E3 fica no `.8` porque falhar CORRETAMENTE
custa zero no caminho feliz.

Detalhe + classificação das 17 checagens do bN:
[`escala-de-verificacao-e-fechamento-do-bn`](experiments/lab/dirty/notas/2026-08/2026-08-07-escala-de-verificacao-e-fechamento-do-bn.md).

## TCF em um parágrafo

**TCF** (Tabular Compact Format) comprime dados **tabulares e aninhados** para **texto ASCII
inspecionável**: o que se repete vira referência, o que é único fica cru (sem inflar). O motor é
**OBAT** (Online Bidirectional Affix Tokenizer) + **HCC** (Hierarchical Compositional Coding),
com camadas que competem num `min()` **nunca-pior** por coluna: fallback raw, dicionário, split
estrutural, polaridade, bN de domínio, seq-RLE. Round-trip é o contrato: **ou preserva byte a
byte, ou falha alto**. Sem dependências de runtime.

Formato vigente `#TCF.8` ([ADR-0032](docs/adr/0032-tcf8-default-format.md)); pacote
`tcf-format 0.8.2`. Pré-1.0 ([ADR-0024](docs/adr/0024-pre-1.0-versioning-git-as-compat.md)): os
minors são iterações de desenvolvimento, **sem compatibilidade rígida entre eles**: versão
antiga se recupera pelo git. O congelamento definitivo é ato do 1.0.

Detalhe do formato: [`docs/algorithms/TCF-format.en.md`](docs/algorithms/TCF-format.en.md).

## Datasets ativos

### Canonical (`datasets/canonical/`, metadata+sample no git, dados reais fora do repo)
| Dataset | Tipo | Volume | Nota |
|---|---|---|---|
| adult-census | real (UCI) | 48842 | single-table mixed |
| tpch-sf001 | gerado (DuckDB) | 60k lineitem | SF=0.01, 8 tabelas FK |
| tpch-sf01 | gerado (DuckDB) | 600k lineitem | SF=0.1, ~866k total |
| online-retail | real (UCI) | 541909 | free-text Description, .99 prices |
| beijing-pm25 | real (UCI) | 43824 | sensor decimais, range narrow. **ATENCAO: `<data_root>/interim/beijing-pm25.db` tem 0 BYTES** (arquivo vazio, sem tabelas; verificado 2026-08-14 na varredura de float). Buraco do corpus, nao erro de leitura |
| wine-quality | real (UCI) | 6497 | features quimicas decimais |
| ibge-municipios | real (IBGE) | 5571 | BR, categoria hierarquica acentuada |
| br-identidades | **sintetico** | 600k | CPF+CNPJ validos, geografia IBGE; vies declarado |
| receita-cnpj | **real non-PII** | 200k | CNPJ Receita; nature CNPJ 40.9% real |

> Gaps de cobertura + roadmap em memoria `project-dataset-coverage-map`
> (free-text longo, IP/UUID, monetary-string, >1M linhas).
>

### Synthetic (`datasets/synthetic/`):

### Core TCF (D1-D9): controle algoritmo
Padroes estruturais (afixos, wrappers). Cobertos pelo TCF-CORE
canonical. Total 2981 raw -> 1523 TCF (51.1%, baseline M10/ADR-0011 pinado
em test_regression_v1_baseline.py; 1615B era M9 antigo). Referenciados em
EXP-007/008.

### ERP/CRM tipos (D10-D15): variety (stress de tipos, nao guia)
Formatos misturados artificialmente: uteis pra entender limites,
nao guia de evolucao (cf. diretriz dados-realistas).

### Incremental T01 (D11a-m): realistic
- `D11a-datas-dia.csv` (12 linhas): sequencial maio-junho 2026 [day]
- `D11b-datas-borda.csv` (14 linhas): bordas mes/ano + Feb 29 [day]
- `D11c-datas-mensal.csv` (13 linhas): fatura mensal dia 5 [day]
- `D11d-datetime-min.csv` (13 linhas): heartbeat top-of-minute [second]
- `D11e-datetime-mensal.csv` (13 linhas): fatura mensal datetime (datas+9h) [second]
- `D11f-datetime-ms.csv` (13 linhas): cadencia 1s [ms]
- `D11g-datetime-us.csv` (13 linhas): cadencia 1ms (multi-char) [us]
- `D11h-datetime-ns.csv` (13 linhas): cadencia 1us (multi-char) [ns]
- `D11i-datas-mensal-com-correcao.csv` (7 linhas): mensal com day corrections (multi-position)
- `D11j-datetime-tz-Z.csv` (13 linhas): minute cadence, tz constante `Z` [second+tz]
- `D11k-datetime-tz-offset.csv` (13 linhas): minute cadence, tz constante `-03:00`
- `D11m-datetime-tz-variavel.csv` (6 linhas): multiplas zonas (-03/+00/+02), mesma UTC absoluta

---

## Tickets

**Fonte unica: [`tickets/README.md`](tickets/README.md)**, o indice e' reconciliado
contra o `status:` de cada arquivo, que e' quem manda.

> Ate' 2026-08-22 esta secao replicava a tabela de tickets aqui, e a copia parou de
> ser atualizada em 2026-06-14: mostrava como OPEN itens fechados havia meses
> (inclusive os dois pre-requisitos de feature-complete do `.8`). Duas superficies
> para o mesmo fato, uma delas apodrecendo (Strata §5, fonte unica por altitude).

## Experimentos publicados

Cada experimento tem README e relatório próprios em
[`experiments/lab/clean/`](experiments/lab/clean/); o índice da pasta lista todos.
Os números vivem lá e nos testes, não nesta página.

## Discipline de manutencao

Este arquivo deve ser **atualizado**:
- Ao fechar sub-experimento (status table)
- Ao tomar decisao estrutural (estrutura de pastas, ticket aberto/fechado)
- Ao mudar foco de natureza (T01 -> T02 etc.)

Se editar, lembrar: **status absoluto, nao incremental**. Substituir
o que mudou, manter o resto coerente.

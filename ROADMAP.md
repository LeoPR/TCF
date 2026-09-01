# TCF: Roadmap

> Visão **organizada por tier** do que fazer (sem ordem fixa dentro de cada tier).
> Registro granular de hipóteses: [`experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md`](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md).
> Estado atual sempre em [`STATUS.md`](STATUS.md).
>
> **Critério recorrente do owner**: preferir o que é **barato** e **não afeta o núcleo
> com severidade** (exceto bug fix). Invariantes: `src/tcf` só muda com aprovação
> explícita; **lossless por default**; **GATE real-world** (`tests/test_real_world_snapshots.py`)
> obrigatório pra qualquer mudança em HCC / pre-pass / prune; nada de weld de natureza/lossy
> sem medir o **incremento** em ≥2 datasets reais (anti-incidente 2026-05-21).

## Estado

Formato `#TCF.8` default ([ADR-0032](docs/adr/0032-tcf8-default-format.md)); pacote
`0.8.4` publicado no PyPI (`tcf-format`), tag `v0.8.4`, com o roteamento que tirou a
tabela retangular da família hierárquica ([ADR-0049](docs/adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md))
e o `sort_by` virando candidato ([ADR-0050](docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md)).

Os números byte-canônicos vivem nos testes que os medem
([`test_regression_v1_baseline.py`](tests/test_regression_v1_baseline.py) e
[`test_real_world_snapshots.py`](tests/test_real_world_snapshots.py)), não nesta página.
O que mudou em cada versão está no [CHANGELOG](CHANGELOG.md).

### Cauda do `0.8.x`: o que fechou, e o que ficou

A auditoria de consistência das três famílias de wire (2026-08-27) soldou quatro ondas, e
com elas fecharam os dois P1 do tema *vazio não é ausente*:

- [`BUG-VIEW-UMA-STRING-VAZIA`](tickets/BUG-VIEW-UMA-STRING-VAZIA.md): uma única string
  vazia era contada como zero e o `select()` truncava a linha. A correção é a ordem de três
  linhas em `_n_somado`;
- [`BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA`](tickets/BUG-ENCODE-VAZIO-EM-COLUNA-TIPADA.md):
  coluna mista perdia valor no `encode`/`decode` e, em dois casos, colapsava dois valores
  num só. O `.8M` passou a usar o mesmo juiz de homogeneidade do `.8H`, e as três famílias
  recusam, que é o que `api.md` já publicava. A política coerciva foi **retirada**: medida
  caso a caso, ela cobre sete dos nove defeitos e mente nos outros dois.

Em 2026-08-28 fecharam os quatro da camada read-only, todos com o `decode` já correto:
[`BUG-VIEW-NULO-NO-HIERARQUICO`](tickets/BUG-VIEW-NULO-NO-HIERARQUICO.md) (a única solda que
muda wire: `?0:` para coluna densa-com-nulos no `.8H`),
[`BUG-VIEW-OBJETO-NAO-RETANGULAR`](tickets/BUG-VIEW-OBJETO-NAO-RETANGULAR.md),
[`BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA`](tickets/BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA.md) e
[`BUG-VIEW-ORFAO-SEM-MAGIC`](tickets/BUG-VIEW-ORFAO-SEM-MAGIC.md), mais três divergências sem
ticket (#12 aviso sobre wire morto, #14b chave não-str, #15 telemetria do `.8H`). Nenhum
bug da auditoria de consistência continua aberto sem decisão de dono.

Eram **seis decisões**, não restos de bug, cada uma colidindo com um contrato ratificado
(`evidência`).
Cinco fecharam: união bool+str ([ADR-0048](docs/adr/0048-uniao-bool-str-e-capacidade-da-familia-single.md)),
LF/CR, `decode(schema=)` ignorado, spec em coluna tipada, e metade dos kwargs engolidos
(`sort_by` e `name` passaram a levantar, [ADR-0050](docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md)).

A quinta fechou em 2026-09-01: `fallback`, `min_header`, `drop_names` e `parallel`
passaram a levantar na rota `list[str]`, juntando-se ao `sort_by` e ao `name`. A própria
docstring do `encode` já os declarava multi-col, e a medição confirmou: nenhum deles mexe um
byte ali, em seis corpora. O `min_len` **não** entrou na recusa, e essa é a parte que corrige
o registro anterior: ele nunca foi no-op, é o único da lista que funciona no single-col, e
recusá-lo tiraria capacidade real (46 B para 23 B numa coluna de IDs).

A sexta e última fechou no mesmo dia, e o veredito foi diferente do esperado: das três
contabilidades do **FLOOR do spec**, só uma era defeito. O single compara contra um baseline
polarizado e com bN e está **certo**, porque a gramática torna polaridade e `:spec`
mutuamente exclusivos e o candidato não pode receber esse arsenal; comparar o melhor emitível
de cada lado é o que um FLOOR deve fazer. O multi já era a conta justa. O hier cobrava 11 B
de um header que não emite, e passou a cobrar `:<size>:<id>`, o pior caso real.

**Nenhuma decisão de dono da cauda do `.8` continua aberta.** `src/tcf` segue sob aprovação
explícita.

## Ciclo `.9`: aberto 2026-08-23, com base medida

O `.8` está **publicado e funcionando** (`tcf-format 0.8.4` no PyPI). O `.9` não é só
performance: são **três eixos**, e o que os une é que agora há **medição de onde partir**,
não intuição.

### O que a medição já estabeleceu

| achado | número | consequência |
|---|---|---|
| o eixo quente é **cardinalidade**, não volume | `lineitem` 60k = 475 s · `adult` 49k = 3,3 s (**143×**) | otimizar por cardinalidade, não por linhas×colunas |
| **encode** é o alvo; decode não | razão de **10× a ~800×** | e a topologia 1 encode : N decodes conta a favor |
| os **bytes já estão lá** | `tcf+brotli` = 2,3% do JSON (metade do `json+brotli`) | falta tempo pra colhê-los |
| break-even hoje | **1,2 a 36 Mbps** | linear no custo de CPU: encode 10× → ~360 Mbps |
| borda superior | 500 mil linhas = 53 min de CPU, 1,2 GB, sem terminar | o alvo é volume pequeno; isto é a borda |

Base: labs `0100`
e `0300`.

### Eixo 1: desempenho, bordas e modos

Ticket-mestre: [`T-PERF-BORDAS-E-MODOS-09`](tickets/T-PERF-BORDAS-E-MODOS-09.md).

- **modos de compressão** (o eixo nunca testado): rápido (*"praticamente só busca e
  repetição"*) · normal · máximo. Pista concreta: `T-BUDGET-DE-BUSCA` mostra que o único
  freio é um contador **fixo de 99, já saturado**.
- **bench na topologia real** 1 encode : N decodes (o 1:1 subestima)
- **tabela de bordas por eixo**, com cardinalidade separada
- fechar o **F3-3** (paralelismo byte-idêntico + combos) que a janela de massa não alcançou

### Eixo 2: armazenamento e ecossistema

**O trilho já existe**, não abrir ticket paralelo (**I7**):

| registro | o que já decidiu |
|---|---|
| **`O-FMT-20`** ([registry](experiments/lab/dirty/notas/2026-05/futuras-otimizacoes-formato.md)) | registro-'0'/schema-declare para **append**, conversão a **parquet** e **index sidecar `.tcfx`** |
| **`H-QUERY-04`** (Tier 1 abaixo) | design de índices: *derivável > {in-file inerte / sidecar `.tcfx`} > formato*; escolha **por perfil de uso**: transmissão sem índice, at-rest index-on-arrival |
| lab `2026-07-13-0156` | composição de compressão **já medida**: em texto livre denso o codec binário sozinho vence e o TCF por baixo **piora (−41%)**; em tabela estruturada vence e compõe. **Quem decide é a estrutura, não o container** |

Novidade a investigar: [`T-HTTP-QUERY-E-VIEW`](tickets/T-HTTP-QUERY-E-VIEW.md), **QUERY virou
RFC 10008** (jun/2026): corpo na requisição, safe/idempotente e **resposta cacheável com o
corpo na chave**. É o envelope que faltava para o `view()`, e conversa direto com at-rest.

Execução de H-QUERY-06/07: [`T-CODE-VIEW-SUBTCF-RECORTE`](tickets/T-CODE-VIEW-SUBTCF-RECORTE.md),
alvo `.9`. A viabilidade está provada para `.8M`; a API pública depende dos contratos de
índice, projeção e canonicidade, mais fallback correto para single-column e `.8H`.

**Princípio transversal da `view`**: oportunista no custo, determinística na resposta.
Cada pergunta e cada blob derivado devem usar a menor evidência suficiente já disponível
no wire, em ordem local: header → estrutura compacta → K únicos/índices → posições e
colunas pedidas → materialização. Se a estrutura não prova a resposta, faz fallback sem
mudar a semântica. O `.8` fecha correções e contratos óbvios; fusão, pushdown posicional e
novas rotas de sub-TCF vão para lab/`.9`. Owners:
[`DECISAO-GROUPING-SEMANTICA`](tickets/DECISAO-GROUPING-SEMANTICA.md) e
[`T-CODE-VIEW-SUBTCF-RECORTE`](tickets/T-CODE-VIEW-SUBTCF-RECORTE.md).

### Eixo 3: limpeza e simplificação (o `.9` clássico)

| item | onde |
|---|---|
| consolidação do core (C1 rename M8A→HCC, C2 achatar decode) | `T-CODE-CORE-CONSOLIDATE` (declarado "abertura do ciclo pós-release") |
| descapar V2-B formas B/C | `T-CODE-DESCAPAR-V2B` |
| quoting/escaping além do backslash interim | `T-FMT-QUOTING-STUDY` · `T-FMT-ESCAPE-COMBINATORIAL-STUDY` |
| assinatura de contrato (`drop_names`, `sort_by`) | `T-FMT-CONTRACT-SIGNATURE` |
| perfis de uso / calibração dos vértices | `T-STUDY-USE-PROFILES` |
| perfis macro (`fast=true`) | `T-PERFIS-MACRO` (casa com os modos do eixo 1) |
| dívida de lint dos acessórios (158, `scripts/` e `shaper/`) | - |

### Decisões do owner ainda abertas

- ~~**Tag de tipo por coluna no `.8M`**~~ **FECHADA** em duas etapas, e nada resta dela. A
  premissa era que uma coluna tipada (`int`, `bool`, `float`) ou um `None` tirava a tabela
  retangular do `.8M` e a mandava para o `.8H`, onde a competição `min(tcf, raw, dict, split)`
  não roda. Custava **+43,6%** no adult-census e **+55,6%** num sintético de 500 linhas.

  O lado `dict` caiu em 2026-08-26: o tipo passou a viajar como tag de 1 byte no meta
  (`!8N=valor`) e o nulo pelo slot 0 do core, então coluna tipada deixou de tirar a tabela do
  `.8M`. O lado `list[dict]` caiu com o **ADR-0049**: a tabela retangular escrita como lista de
  registros roteia para o `#TCF.8R`, que é o corpo do `.8M`. Com os dois, não sobra entrada
  retangular que a tipagem empurre para o `.8H`, e o `schema=` funciona nas duas grafias.
  O que continua no `.8H` é o que de fato é hierárquico: ragged, aninhado e array na célula.
  A `view` já lê as duas rotas (`BUG-VIEW-RECUSA-COLUNA-TIPADA`, fechado), então o que
  falta é o **byte** e o `schema=`. Muda o formato, então pede ADR, e implica reservar
  um id por tipo. Sobre a POSIÇÃO da tag: o que colide depois do size é o alfabeto
  **hex** (`@1b=age` vira size 27, e `@1B=age` também, porque o parser aceita
  maiúscula), não a posição em si. Com símbolo fora do hex ela é utilizável. O
  espaço globalmente livre são as maiúsculas fora de `A-F`, `H` e `M`. Atenção:
  `B` e `C` já são discriminadores (bN de domínio, ADR-0036).

- **bN-dense no FLOOR, COMO entrar**: (a) ligado por padrão, com re-pin de D17a e
  real-world registrado em ADR, ou (b) atrás de flag desligada (`fallback_bn=False`).
  Plano pronto, escopo `.8M`, marcador `#` já reservado no registry, nunca-pior por
  construção (entra no `min()`). Medido: tabela real 1,86x menor, mas o ganho encolhe sob
  gzip e some com N pequeno. Nada em `src/tcf` foi tocado. Labs `2026-07-23-1857` (v2) e
  `-1832`.
- **ruff-format em massa** (68 arquivos): aplicar como commit isolado, ou remover o hook
- o **`uv.lock`** que entrou no commit da limpeza de comentários

### Registrado, sem casa própria ainda

- **Track 2 L01-L05**: estudos de camada de algoritmo (token-level, detecção de slot,
  marcadores tipados, balanceamento de árvore, pré-filtro). Adiados explicitamente.
- **Gate forte do CNPJ**: a nature é confirmada-empírica com **uma** fonte real; subir a
  confiança pede N >= 5 fontes distintas. Só se houver interesse em fortalecer a claim.

### Fora do `.9`

`2.0`: streaming, sinks, lossy, `T-OBAT-NOS-PROXIMIDADE`.

`1.0` (direcao do owner, reafirmada 2026-08-23): congelar **tudo** de uma vez na virada,
formato, API, e cada decisao implicita que hoje e' detalhe de implementacao (ordem de
dicts implicitos inclusive). Ate' o ultimo segundo antes da chave virar, NADA e'
compativel: pre-1.0 nao carrega compatibilidade nenhuma, e o proprio `.8` pode ficar
obsoleto e ser limpo. Port para Rust fecha o ciclo.

## Tier 1: PRÉ-1.0 (organizável agora)

Tudo opt-in / gadget / knob; impacto no núcleo nenhum/leve (ou atrás de GATE).

| id | item | custo | impacto núcleo | nota |
|---|---|---|---|---|
| **H-QUERY-01** | Lazy/queryable `view()`: descompressão seletiva por coluna/linha (`count/sum/min/max/avg` + `where`) | M | leve (aditivo read-only) | **PROMOVIDO PRO CORE** (A4, 2026-06-21): `src/tcf/view.py`, `from tcf import view`; shim em [`scripts/tcf_lazy/`](scripts/tcf_lazy/). L1–L5 funcional (pruning, dimensões, contar/agrupar/filtrar sem expandir, group-by por layout). Lê `#TCF.8` (default, ADR-0032), não muda encode/decode/formato. Tese central da 1.0. PoC: `2026-06-16-lazy-query/`. |
| **H-QUERY-04** | Expansão (design 2026-06-17): **decode-como-DAG**, decode parametrizado (`execute()` pushdown), **índices escondidos** pra grouping | M | nenhum (gadget) | **DESIGN FEITO** (`nota`). Princípio: índices = **derivável > {in-file inerte / sidecar `.tcfx`} > formato**, nunca in-blob por default; decisão de índice **por perfil de uso** (transmissão = sem índice; at-rest = index-on-arrival). Unificação **não-dura** (fazer cada→otimizar→fatorar o comum, não monólito); paralelismo por coluna. Plano fases A/B/C + transversal, barato no gadget. Limite duro: coluna `tcf` é entrelaçada → fallback total (o lazy vive em `@dict`/raw). |
| LAZY-QUERY-RUNS (=L3) | agregar/contar grupos sem expandir a coluna | - | nenhum | **FEITO via dicionário/raw** (`group_count`/`nrows`). **Achado**: o `*N|` do modo-tcf é entrelaçado (OBAT+HCC, refs entre linhas), **não separável**; o ganho limpo vive no dict/raw. |
| **FILTRO-NUMERO** | Filtro/nature básico de **número** (além de CPF/CNPJ/IP) | S | leve | **CARACTERIZADO → PARK** (`2026-06-16-number-nature-caracterizacao/`): **weighted na tabela NÃO atinge ≥15% em 2+** (adult 14,5%, receita 7,1%, tpch 3,4%, beijing 1,3%) e **some sob brotli** (≤6%). Ganho per-coluna (fnlwgt −41%) dilui na tabela. dict/seq-RLE/split já cobrem. Reabrir só como **nature opt-in estrita** se houver caso de transporte cru integer-heavy. Variantes (padded-int / scaled-decimal-lossy) → Pacote 10/v2.0. |
| FILTROS-POPULARES | CEP, telefone, MAC, data-BR + clássicos-BR (PIS/renavam/título/CNH...), barato-primeiro | S | nenhum (CEP/PIS/renavam/título/CNH) ou máquina nova (telefone/RG/placa) | **ALVO .9** (owner 2026-07-12, Opção A do [T-SPEC-STATUS-08](tickets/T-SPEC-STATUS-08.md)): a máquina JÁ cobre 5/7 por construtor (`check_fn` é param livre); o gargalo é DADO: nenhum hub tem a coluna e o gerador só faz cpf/cnpj. Weld só com ganho ≥15% em 2+ reais; **F4 mediu que nem CNPJ é ganho de tabela garantido em real** (piora receita +7339B, split→raw). Pré-reqs: anonimizador §2.3 + gerador estendido (não existem). Um por vez, com dataset real. |
| **H-NAT-MARK-01** | Marcador de nature **auto-descritivo** no header (o SPEC viaja com o TCF) | M | leve | **SHIPADO no `.8` p/ natures core** (verificado 2026-07-13): o `#TCF.8M…:cpf` / `#TCF.8 :cpf` carrega o `:id` no header e o `decode` reverte **sem spec out-of-band** (header autoritativo; RT True). Veio de carona com o FLOOR nature-compete. Resolução **core-only** (CPF/CNPJ/IP); id desconhecido → exige spec out-of-band coincidente (ver [T-API-BOUNDARY-CONTRACTS](tickets/T-API-BOUNDARY-CONTRACTS.md)). ADR-0027 (`proposed`) fica como registro do design; o **registry carregável de terceiros** segue aberto (`.9`/pré-1.0). Substitui o antigo "DESIGN FEITO → PARADO em (A)". |
| V2-RLE-STREAM | RLE no stream de índices do V2-B (follow-up do 0.7) | S | nenhum | **CLOSED p/ geral; NICHO textual-puro ABERTO (decisão do owner)** (caracterizado 2026-06-19, `lab`). Geral: +1,19% weighted/7 reais, 0/7 ≥15%, −1,39% sob brotli. **Nicho** (payload minúsculo, low-card texto **skewed**, ordem natural, textual-puro): situacao +55%, workclass +22% (2 reais ≥15% no nicho). Achado: **clusterizado flipa p/ tcf-`*N|`** (overlap); stream-RLE só ganha em runs curtos+skewed. Weld = #TCF.8+GATE. Decisão do owner se o nicho "transmissão minúscula" justifica. Registro: [roadmap-hipoteses Pacote 11-bis](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md) (H-V2RLE-01/02); família RLE: `estudo`. |
| H-INTRA-01/02/03 | Repetição **intra-valor** (fatorar `111.` dentro de um valor) | M | **médio** | Pacote 11 / O-FMT-17, alvo 0.8. Decidir engine (OBAT×HCC), **medir net** com escape de dígito e **overlap** com nature/split. GATE obrigatório, *não atropelar*. |
| **OMIT-CONTRACT** | Contrato de omissão do formato (deduzir / convenção-default / declarar + fail-loud) | S | nenhum (contrato) | **AVALIAR ANTES DE FECHAR O 1.0** (owner 2026-07-07): [T-FMT-OMIT-OR-DECLARE](tickets/T-FMT-OMIT-OR-DECLARE.md): 4 categorias, invariantes fail-loud + proveniência; generaliza o eixo versão do ADR-0029. |
| V2B-DESCAPAR-B/C | Descapar V2-B além da forma A: forma B (+skip cadence-aware) e C (sem cap) | M | **médio** (toca min() por coluna) | **ALVO .9** (T-REL-08-CLOSEOUT Passo 1b, 2026-07-10): forma A (cap 8192) welded no .8 (`a201c1e`); estudo/medições das formas B/C vivem em [T-CODE-DESCAPAR-V2B](tickets/T-CODE-DESCAPAR-V2B.md) (closed-parcial). Gate real-world obrigatório. |
| QUOTING-STUDY | Quoting/escaping de nomes além do backslash interim (CSV-quote / smart) | S | leve (gramática do meta) | **ALVO .9** (T-REL-08-CLOSEOUT Passo 1d, 2026-07-10): interim backslash = entrega do .8 (fuzz-validado); estudo em [T-FMT-QUOTING-STUDY](tickets/T-FMT-QUOTING-STUDY.md) (filho de T-FMT-NAME-ESCAPING); pressão real vem da hierarquia `{}[]`. |

**Lazy-view, em etapas** (a "venda": descomprimir só o suficiente pra responder): L1
column-pruning + agregadores (PoC) · **L2 medido**: `where(CustomerID=X).sum(Quantity)`
("qtd comprada por um usuário") toca **7,9%** do blob, `count()` 0,2%, vs `decode()` 100%
(online-retail 5k×8) · L3 agregar runs (`*N|`) sem expandir · L4 filtro por índice (`@`) ·
L5 **layout p/ baixa latência** (organizar pra uma query-alvo tocar o mínimo; dimensões
**memória/velocidade/latência/compressão**). **Não é versão de formato**, lê o `#TCF.8` existente (ADR-0032).
**L3, L4 e L5 já feitos** no gadget. L3/L4 (via dict/raw): `nrows`/`group_count`/`where`
contam/agrupam/filtram **sem expandir as N linhas**, varrendo o stream do dicionário
(`where(workclass='Private')` em 5k toca ~5% do blob, sem cachear a coluna). L5 (`group_ranges`/
`agg_by`): quando a chave sai contígua, o group-by vira slice (o "qtd por usuário"
= `agg_by('CustomerID','Quantity','sum')`, verificado), e o `agg_by` cai no caminho
order-free quando ela não sai, então nunca levanta por layout. Achados: (1) agregar `*N|`
direto no modo-tcf não é separável (OBAT+HCC entrelaçados): o ganho limpo vive no
dicionário/raw; (2) o `sort_by` deixou de ser trade-off de bytes no
[ADR-0050](docs/adr/0050-sort-by-vira-candidato-o-floor-decide.md): ele virou **candidato**,
o encoder emite as duas versões e fica com a menor, e por isso pedir o layout nunca custa
bytes e também não garante que ele saia (o `group_ranges` continua estrito, de propósito).

**Filtros modulares (H-NAT-MARK-02, ideia do owner)**: `natures/` vira **pasta de plugins**,
cada filtro um módulo spec auto-contido (regex + transform + id), com um registry que descobre
os de terceiros (drop-in), pra outros desenvolverem os seus. **A API/pasta não é versão** (output
idêntico); só o *spec viajar no header* pra auto-decode por terceiros **é versão (0.8)** = H-NAT-MARK-01.
**Plano completo (DSL textual → "compilador" → registry → header)**: `filtros-dsl-plano.md`.
As natures já são paramétricas (`TemplatedCheckedSpec`/`TemplatedPaddedSpec` = dados + `check_fn`), então o
compilador é um gerador de instâncias (1:1). Fluxo faseado: **F1 ✅ FEITO** (`scripts/natures_compiler/`,
DSL flat→spec, round-trip obrigatório, **9 testes, zero src/tcf**; regenera CPF/CNPJ/IP do DSL == à mão;
achado: CEP/MAC precisam spec novo) → **F1.5 ✅ FEITO** (registry gadget, lookup de nature por nome, semeado com cpf/cnpj/ip; 5 testes) →
**F2 ⏸ DESIGN FEITO, PARADO** (spec viaja no header #TCF.8 = H-NAT-MARK-01; [ADR-0027 `proposed`](docs/adr/0027-nature-mark-header-self-describing.md);
owner 2026-06-17 escolheu **não implementar agora**: o magic permanente não se justifica só por DX, que o registry gadget já cobre quase de graça) → **F4** builder visual (2.0, front-end
do mesmo compilador). Ressalva: o DSL vale como **infra/DX/explicabilidade**, não garante bytes; gate de ganho antes de weldar.

### Cheap-wins (organizados 2026-06-17)

**Tier A, zero core (infra/docs), feitos:**
- ✅ **CW-1 release.yml** + Trusted Publishing (tag `v*` → `uv build`+`uv publish` via OIDC, sem
  token; gate byte-canonical antes de publicar). Pré-req 1x no PyPI: cadastrar o repo como Trusted
  Publisher de `tcf-format`. [`.github/workflows/release.yml`](.github/workflows/release.yml)
- ✅ **CW-2 Reference dos knobs** (`fallback`/`min_header`/`min_len`/`sort_by` + trade-offs medidos).
  [`docs/reference/encode-knobs.md`](docs/reference/encode-knobs.md)
- ✅ **CW-3 Higiene de comentário CI**: baseline do `D17a` corrigida.
  [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

**Tier B, toca `src/tcf`, exige aprovação (NÃO são cheap-wins puros):**
- ✅ **CW-4 FEITO** (owner OK, 2026-06-19): docstrings stale alinhados em `src/tcf`, e a
  baseline do `D17a` corrigida junto. **Só docstring/comentário, zero código** (diff
  verificado); suíte 379 passed, byte-canonical intacto.
- ~~**CW-5** "Higiene de header compacto" (O-FMT-11, byte-precise)~~, **FECHADO/subsumido**
  (verificado 2026-06-19): as reduções concretas já estão welded: O-FMT-16 (dispensa prefixo `# `)
  + O-FMT-15 (última coluna sem size) via `min_header` (ADR-0023); escaping via name-guard (ADR-0026);
  flag `M` existe. Single-col já é mínimo (sem header; shebang *adicionaria* bytes). Não sobra byte
  barato no header multi-col; o restante (espaço do magic, sizes decimais) seria **mudança de
  formato**, não higiene: fora de escopo cheap-win.

**Parked:**
- ~~**O-FMT-12**: auto-detect CSV + `encode_file()`~~, **PARK** (owner 2026-06-16): leitura-de-input
  é fora-do-core por design; `encode(dict)`+`DictReader` bastam (0 bytes). `levantamento`

### Plano dos filtros (sem atropelar)
Ordem barata-primeiro: **(1)** `FILTRO-NUMERO`, **caracterizado 2026-06-16**: nicho restrito
(integer alta-card, ganho cru que some sob brotli; decimais exigem variante lossy). Weld só se
houver caso de transporte cru integer-heavy; senão o dict/seq-RLE já cobrem; **(2)** demais populares (CEP/telefone/MAC/data-BR) reusando o framework
existente, **um por vez**; **(3)** `H-NAT-MARK-01` (marcador no header) como camada ortogonal
que faz o decode reconhecer a nature sozinho. Critério de weld por candidato: **ganho ≥15% em
2+ datasets reais**; todos opt-in, sem tocar HCC/pre-pass/prune. Nada avança sem medir incremento.

---

## Tier 2: 2.0 (depois de uma 1.0 sólida)

- **Lossy** (Pacote 10, `loss-taxonomia.md`); 0.7 fica lossless-puro:
  - `H-LOSS-00` meta-camada de **contrato** (pré-requisito de toda perda).
  - `H-LOSS-02` **cross-coluna / DERIVED-DROP** (`valor = soma(parcelas)`): maior teto, owner prioriza.
  - `H-LOSS-01` resíduo-redistribuído (perda por-linha, **soma exata** no agregado). PoC OK.
  - `V2-C-LOSSY` round/quantização/truncamento + naturezas lossy (nicho ~1.5%). Sob GATE N≥5.
- **Streaming / binário** (ADR-0018): `V2-J` streaming low-latency, `V2-K` disco zero-copy + column-pruning, `V2-L` binarização interna (header textual mantido, ainda explicável).
- `META-TYPE-ENCODERS` Pacote 7 (templated/checksummed/composite) + schema-builder Fase 3: reabre com caracterização real-world (ganho ≥15% em 2+).
- Infra de streaming: output-sinks + encoder-manager Fases 2-4 + plan-contract + per-channel headers (pré-req de V2-J).
- Perf residual: counter incremental HCC (H-PERF-05d, divergência byte-canonical em datetime); Patricia trie como índice OBAT.
- Bundles de menor prioridade: ordenação avançada (O-FMT-01/03/04), **cross-column dict** + type-aware (O-FMT-06/07 = **[H-GDICT-01](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md)**, "dicionário global no header", ideia do owner 2026-06-19; distinta do V2-RLE-STREAM) + header desacoplável (O-FMT-14).
- Suporte: fixtures de dados edge (T-DATA-3) pro schema gadget; shaper hardening (>100k).

---

## Tier 3: Pesquisa / spin-off (talvez 2.0+, muita pesquisa)

Big bets, custo XL, **paralelos** ao Python (não substituem o canonical no curto prazo).
Pré-requisitos comuns: **API pública estável + 1.0 sólida** antes de portar, e **equivalência
byte-canonical** como critério de aceite. Spin-off em repo separado recomendado.

- **TCF-RUST**: core nativo (speed-first dentro do espaço textual). Base dos demais.
- **TCF-WASM-WEB**: codec no browser; queries client-side em `.tcf` local (sinergia com H-QUERY-01). Depende do Rust.
- **TCF-PARQUET-POLARS**: embutir como camada estilo Parquet **ou** módulo no Polars pra acelerar leitura; TCF como backend de I/O. Integração externa ao core.

### Ferramentas auxiliares (gadgets: integração leve, sem dependência dura)
Consomem `SideOutputs`, **nunca arrumam dados**. Podem andar juntas ou separadas, pra terceiros usarem.
- **Qualidade/Schema** (owner #4): o schema gadget multi-tabela **já está completo**
  (`scripts/schema_gadget/`, ALERT-ONLY). O elo novo pedido (*identifica dado → gera SPEC
  automático → marca no header*) **é exatamente o H-NAT-MARK-01** (Tier 1) acoplado ao gadget:
  o gadget vira fonte do SPEC, o header vira veículo.
- **LLM→SQL** (owner #5, spin-off `tcf-llm-tools`): duas tools independentes (schema + geração de
  consulta); a LLM gera SQL e o **SQL roda na camada lazy** (H-QUERY-01). Não toca `src/tcf`.
  Sequência: consolidar H-QUERY-01 primeiro (dá onde o SQL rodar).

---

## Fechados / não retomar (têm veredito)
- **V2-D** strip de afixo: refutado (subsumido pelo OBAT, 0.11%); o ganho real era o split estrutural.
- **H-PERF-04** trigrama de meio: não preserva byte-canonical; coberto por Patricia (Tier 2).
- **H-HCC-01/02** detector de subconta (Re-Pair): closed-insufficient-gain (teto 1.30%, cauda longa, risco alto no core).
- **H-LOSS-03** round isolado: nicho ~1.5% (só wine); absorvido em V2-C-LOSSY.
- **O-FMT-10 / Pacote 2** escape-dedução: refutada real-world (<1.13%). Manter fechada salvo demanda.

---

## Notas de pesquisa (medidas, 2026-06-16)

- **TCF + brotli são complementares em ESCALA** (`2026-06-16-staged-and-ordering-brotli/`):
  em multi-coluna real (3k linhas, 4 datasets), `tcf-0.7+brotli` **vence** `csv+brotli`
  (Adult −28%), e **quanto mais TCF, menor o pós-brotli**. Refuta "menos TCF ajuda o brotli";
  TCF cheio é o melhor pré-processo. (O cadastro minúsculo do README vendia o contrário:
  artefato de 4 linhas; corrigido.) "TCF pela metade" (`tcf-lite`) chega a ser pior que CSV+brotli.
- **Ordenação é codec-dependente**: a melhor chave de `sort_by` p/ TCF-sozinho ≠ a melhor p/
  TCF+brotli em 3/4 datasets. Ganho ≤5%. Lever pequeno; se welder auto-`sort_by`, considerar o
  modo (com/sem compressão a jusante). Baixa prioridade (2.0).
- **Guia de transmissão por API: onde o TCF importa** (pesquisa 2026-06-21,
  `transmissao-api-onde-tcf-importa.md`):
  honesto: a prática é JSON pequeno+gzip/brotli (TCF não ajuda na maioria); o nicho do TCF é
  **~5-15%** (batch/export tabular **grande+repetitivo** como pré-processo do brotli; lazy/consulta
  seletiva). **Teste decisivo PENDENTE**: `TCF+brotli` **vs `NDJSON+brotli`** (só comparamos com
  CSV+brotli; NDJSON é o concorrente textual real, padrão em BigQuery/Elasticsearch/X). Cenários
  T1-T6 (NDJSON-baseline, break-even por volume, cardinalidade, lazy×Parquet, CPU, cap de resposta)
  no guia, candidatos a lab antes de qualquer narrativa de transmissão. Header byte-size: economico
  em tabela real (0,01-0,03% do blob); só pesa em payload minúsculo (O-FMT-18 base-94, ~3%).

---

*Reorg crítica de 2026-06-16 (132 itens → ~55 únicos). Detalhe granular e proveniência:
[`roadmap-hipoteses.md`](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md).*

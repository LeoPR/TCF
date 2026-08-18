# 2026-08-17-0800 — prevalência e ganho relativo nos sintéticos de controle do `.8H`

> **Estado: VERIFICADO — e a conclusão principal CAIU.** Workflow `wf_b07bfd49-3f9`
> (20 agentes, 16 alegações, **7 confirmadas** após refutação). A prevalência (§A) sobrevive
> **intacta, dígito a dígito**. Os ganhos (§B) foram corrigidos para baixo, e a leitura que
> eu tinha tirado deles — *"B2 é quase todo absorvido por B1"* — **não se sustenta**: é
> propriedade do **mix** deste conjunto, não dos mecanismos. Detalhe em §Verificação.

## O que isto é — e o que não é

**Não é julgamento.** Os 12 casos são enviesados de propósito, e o próprio gerador declara:
*"cada um isolando UM mecanismo do fluxo… Propósito: observar a NAVEGAÇÃO do fluxo, não
ganhar bytes."* Medir "quanto o TCF ganha" aqui não significaria nada.

É um **levantamento**: onde os bytes moram, quais mecanismos disparam e com que
frequência, e quanto cada achado em aberto valeria sobre este conjunto — para decidir o
que levar ao lab clean com volume.

## Fonte única — nada de sintético novo

`tests/fixtures/control_synthetics_h.py`, o **mesmo** gerador que alimenta
`tests/test_hierarchical_control_synthetics.py` (12 pins de navegação, seed fixa).

Isso foi decisão de método: o conjunto de controle **já existia e já estava pinado**.
Inventar um segundo só criaria uma régua paralela que diverge da suíte.

## Coleta — e o Shaper

Este lab é **100% sintético**: zero corpus, zero sqlite. Quando for para o lab clean com
volume, a coleta tem de vir pelo **Shaper** (`src/shaper/` — `ShapeRequest` com
`stratify_by`, `volume`, `seed`, `schema`, `join_level`, `compressibility_range`), com
estratificação honesta, **não** `LIMIT/OFFSET` direto no sqlite.

Registro honesto: os labs [`0400`](../2026-08-17-0400-o-candidato-unico-do-H/) e
[`0600`](../2026-08-17-0600-limites-de-profundidade-do-H/) pegaram **direto do sqlite**.
Precedente do jeito certo: `2026-07-14-2336-hierarquia-amostra-populacao-honesta`.

## A. Prevalência — onde os bytes moram

| caso | total | meta | controle | folhas | ctrl% | json |
|---|--:|--:|--:|--:|--:|--:|
| c01-uniforme | 798 | 30 | 0 | 768 | 0,0% | 4893 |
| c02-telemetria-array | 3132 | 26 | 8 | 3098 | 0,3% | 8001 |
| c03-telemetria-split | 2830 | 43 | 0 | 2787 | 0,0% | 10801 |
| c04-ragged | 685 | 31 | 78 | 576 | 11,4% | 3868 |
| c05-null-campo | 842 | 33 | 90 | 719 | 10,7% | 6662 |
| c06-null-elemento | 1420 | 40 | 407 | 973 | **28,7%** | 2582 |
| c07-arrays-vazios | 465 | 25 | 199 | 241 | **42,8%** | 2608 |
| c08-matriz | 646 | 27 | 14 | 605 | 2,2% | 1087 |
| c09-espinha | 3218 | 57 | 237 | 2924 | 7,4% | 8676 |
| c10-tipos-cadenciados | 1317 | 34 | 0 | 1283 | 0,0% | 5013 |
| c11-categorico | 1688 | 21 | 0 | 1667 | 0,0% | 9180 |
| c12-compose-total | 1453 | 75 | 434 | 944 | **29,9%** | 3409 |
| **TOTAL** | **18494** | **442** | **1467** | **16585** | **7,9%** | 66780 |

Por mecanismo:

| kind | colunas | casos | bytes | % do total |
|---|--:|--:|--:|--:|
| `scalar` | 30 | 11 | 11353 | 61,4% |
| `arr_scalars` | 5 | 5 | 5232 | 28,3% |
| `count` | 8 | 6 | 870 | 4,7% |
| `emask` | 2 | 2 | 310 | 1,7% |
| `mask` | 4 | 3 | 287 | 1,6% |

**Leitura**: o controle é 7,9% no agregado mas **varia de 0% a 42,8%** por caso — e a
variação é exatamente o que cada caso foi construído para isolar. O `c07-arrays-vazios`
gasta quase metade em controle porque é *só* estrutura; o `c11-categorico` gasta zero
porque não tem nada opcional. O meta é 2,4% do total.

## B. Ganho relativo dos achados em aberto — CORRIGIDO

| achado | reportado | **honesto** | % | casos | ref |
|---|--:|--:|--:|--:|---|
| B1 — candidato único (`raw`/`dict`/`split`) | 8173 | **≤ 8151** | 44,1% | 12/12 | [lab 0400](../2026-08-17-0400-o-candidato-unico-do-H/) |
| B2 — folha tipada → encoder nativo | 3306 | **3257** | 17,6% | 11/12 | [lab 0500](../2026-08-17-0500-header-do-H-sintetico/) |
| B3 — `count` constante-1 (singleton) | 0 | **não-exercitado** | — | 0/12 | [nota 0700](../../../notas/2026-08/2026-08-17-0700-escada-de-array-e-o-manual.md) |
| UNIÃO (melhor por coluna, **só folhas**) | 8380 | **8358** | 45,2% | 12/12 | — |
| **+ colunas de CONTROLE** (nunca testadas) | — | **+496** | — | 6 cols | lacuna |
| **UNIÃO com controle** | — | **~8854** | **47,9%** | — | ainda um **piso** |

**As três correções são do mesmo feitio dos dois erros anteriores: custo estrutural
descontado como se fosse grátis.**

- **B2 −49 B**: eu descontava a **linha de header inteira** do wire tipado, alegando que
  "a tag migraria pro meta". A tag (`n`/`b`) migra mesmo — o meta já a declara
  (`#TCF.8Hseq:30n,ok:203b,…`). Mas o header tipado é `#TCF.8nB8258`, `#TCF.8b196`,
  `#TCF.8n!!` — os 1–5 bytes **depois** da tag são load-bearing: `decode('#TCF.8b' + corpo)`
  **falha**; só `decode('#TCF.8b196' + corpo)` devolve a lista. Só migram magic+tag+LF = 8 B.
- **B1 −22 B**: o modo precisa de **1 char de prefixo por coluna** (`!`/`@`/`%`,
  `multi/core.py:447`), e o meta do `.8H` não tem esse slot. 22 colunas trocam de modo.
  Provado em `.8M` real: **0/22 decodam sem o prefixo, 22/22 com**.
- **B3 não é 0 medido, é ausência de caso**: nenhuma das 8 colunas de `count` é constante-1.
  O teto foi medido à parte — uma coluna de count constante custa **7–8 B** (o RLE já a
  colapsa), então B3 vale ~7–8 B/coluna, não um valor a descobrir.

### A conclusão que eu tirei está errada

Eu escrevi *"B1 e B2 se sobrepõem quase inteiramente"* e ia usar isso para priorizar.
**O número sobrevive** (união − B1 = 185 B honestos, +2,3% sobre B1). **A leitura não.**

- **É propriedade do MIX, não do mecanismo.** Bool é **2,0%** das folhas (328 B de 16 585), e
  o gerador **não tem** bool-em-array nem bool-com-null. Acrescentando dois casos bool, o
  excedente da união salta de 185 B para **1147 B (6,2×)** — a leitura inverte para
  "não absorvido" **sem tocar em mecanismo nenhum**.
- **Nas 2 colunas bool que existem, o B2 domina sozinho**: `c10/ok` poupa 172 B contra 39 do
  B1; `c12/ok` poupa 114 contra 71. "Absorvido no agregado" não autoriza descartar o B2 —
  autoriza dizer que ele **só paga onde há bool**.
- **"Teto real" era rótulo errado** — é um *piso* do teto. Os próprios dados mostram
  `string+split` batendo o tipado com folga (`c10/temp` 196 vs 902; `c02/v` 1380 vs 2324):
  um tipado que **também** tivesse split ficaria abaixo dos dois, e um `min()` entre eles é
  cego para isso.

**Por que isso importa**: era exatamente o tipo de conclusão que viaja para fora do lab e
vira decisão de roadmap. Um "%" global de um mix **escolhido** não é transferível.

## C. Régua externa

TCF `.8H` 18 494 B contra JSON compacto 66 780 B. **Só ordem de grandeza** — o conjunto é
enviesado, então isto não é resultado de compressão, é sanidade.

## Erros deste lab (os dois que eu mesmo achei)

1. **Fatiei o corpo da folha por `\n` e tratei as linhas como valores.** O corpo é um wire
   single-col **órfão**, já passado pelo core (`hierarchical.py:491` chama
   `_encode_col(vals, stamp=False)`) — as linhas são tokens (`^1`, `*3|true`), não valores.
   O certo é **decodar** o corpo. Sintoma que denunciou: `c10` tem 150 bools em 203 B;
   literal seriam ~825 B. O bug **zerava B2** e subestimava B1 (17,7% em vez de 44,2%).
2. **Somei B1+B2** sem notar que competem pela **mesma coluna**. Corrigido com a união.

Os dois são do mesmo feitio: medir sobre a coisa errada e não conferir contra uma âncora
independente. Por isso o número do `c10` (203 B para 150 bools) virou o teste de sanidade.

## Round-trip

**12/12 OK** para os wires que existem — `outputs/<caso>.tcf` + `outputs/<caso>.roundtrip.json`.

**Ressalva do §RT levantada na verificação**: esse `12/12` valida só o **wire atual**. Os
bytes de B1/B2 são de wires que **não existem**. O verificador fez o RT por fora
(22/22 do B1 em `.8M` com prefixo · 6/6 do controle · corpo tipado com header completo
devolvendo a lista idêntica) e **nada desmentiu os números** — mas o lab precisa imprimir
isso, senão o §RT não está satisfeito para B1/B2.

## Verificação (workflow `wf_b07bfd49-3f9`)

20 agentes · 3 lentes (reproduzir do zero · atacar a conclusão · caçar lacuna) · cada
alegação passando por refutador instruído a **refutar em caso de dúvida**.
**16 levantadas → 7 confirmadas**: 3 número-errado, 2 conclusão-não-suportada,
2 lacuna-de-cobertura.

O que a verificação **caçou e não achou** (o método aguenta):
- `b_atual == baseline tcf` do `min_do_M` em **35/35** colunas de dado — B1 compara igual com igual
- B2 nunca troca o tipo do dado (0/21) — não há ganho falso convertendo `"30"` em `30`
- 0/40 colunas falharam ao decodar; o assert de exaustão do corpo segura. **A correção do
  erro (1) está de pé.**

### O que falta antes do clean com volume

1. **O bucket de controle na mesma régua.** 1467 B, 7,9% do total, e o `run.py:161` dá
   `continue` neles. Só o `min()` já recupera **496 B** (33,8% do bucket) — mais que os
   185 B que o B2 acrescenta sobre o B1.
2. **O lado do CUSTO, nunca medido.** B1 exige um slot de modo no meta que **não existe**;
   B2 exige os parâmetros do header tipado no meta. Só contei byte de **corpo**.
3. **A combinação B1×B2**, não só o `min()`. Os contra-exemplos dizem que `tipado+split` é o
   candidato que interessa.
4. **Estratificação — e é aqui que o Shaper entra.** Todo número aqui é "% do total", média
   ponderada de um mix. No clean, o ganho tem de sair **por estrato** (por kind e por tipo
   escalar: string/num/bool, com/sem null, escalar/array) **com o mix declarado ao lado**.
   Foi exatamente o "%" de mix escolhido que produziu a conclusão instável acima.

## Conexões

- Sintéticos: `tests/fixtures/control_synthetics_h.py` · pins em
  `tests/test_hierarchical_control_synthetics.py`
- Lab original do conjunto: `2026-07-17-0014-sinteticos-controle-fluxo-hierarquia`
- Achados medidos: [`0400`](../2026-08-17-0400-o-candidato-unico-do-H/) ·
  [`0500`](../2026-08-17-0500-header-do-H-sintetico/) ·
  [`0600`](../2026-08-17-0600-limites-de-profundidade-do-H/)
- Shaper para o clean: `src/shaper/`

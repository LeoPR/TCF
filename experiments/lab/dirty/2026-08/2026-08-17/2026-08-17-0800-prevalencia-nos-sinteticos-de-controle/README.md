# 2026-08-17-0800 — prevalência e ganho relativo nos sintéticos de controle do `.8H`

> **Estado: em verificação** (workflow `wf_b07bfd49-3f9`). Os números abaixo saíram de
> **uma** medição, e esta mesma medição já teve **dois erros meus** corrigidos no caminho
> (§Erros). Não usar como base de decisão até a verificação fechar.

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

## B. Ganho relativo dos achados em aberto (provisório)

| achado | bytes | % do total | casos | ref |
|---|--:|--:|--:|---|
| B1 — candidato único (`raw`/`dict`/`split`) | 8173 | **44,2%** | 12/12 | [lab 0400](../2026-08-17-0400-o-candidato-unico-do-H/) |
| B2 — folha tipada → encoder nativo | 3306 | 17,9% | 11/12 | [lab 0500](../2026-08-17-0500-header-do-H-sintetico/) |
| B3 — `count` constante-1 (singleton) | 0 | 0,0% | 0/12 | [nota 0700](../../../notas/2026-08/2026-08-17-0700-escada-de-array-e-o-manual.md) |
| **UNIÃO** (melhor dos dois **por coluna**) | **8380** | **45,3%** | 12/12 | teto real |

**B1 e B2 se sobrepõem quase inteiramente.** A união fica só **1,1 pp** acima do B1
sozinho — numa coluna bool o `dict` já captura o que o denso capturaria, então somar os
dois inflaria. *Ressalva sob verificação*: isso pode ser artefato de coluna curta; numa
coluna bool longa o `b1` bit-pack deveria vencer o `dict`. É uma das lentes do workflow.

**B3 = 0 em 12/12** confirma a nota `0700`: nível singleton reaninhado **não aparece** num
conjunto de controle desenhado por gente olhando dado. A escada era mesmo só stress.

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

**12/12 OK.** `outputs/<caso>.tcf` + `outputs/<caso>.roundtrip.json` por caso.

## Conexões

- Sintéticos: `tests/fixtures/control_synthetics_h.py` · pins em
  `tests/test_hierarchical_control_synthetics.py`
- Lab original do conjunto: `2026-07-17-0014-sinteticos-controle-fluxo-hierarquia`
- Achados medidos: [`0400`](../2026-08-17-0400-o-candidato-unico-do-H/) ·
  [`0500`](../2026-08-17-0500-header-do-H-sintetico/) ·
  [`0600`](../2026-08-17-0600-limites-de-profundidade-do-H/)
- Shaper para o clean: `src/shaper/`

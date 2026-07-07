# EXP-015 — TCF hierárquico: lê CSV e JSON, reverte pros dois (protótipo v0) [probatório]

**Lab clean / protótipo** que consolida as IDEIAS do estudo dirty (grupo hierárquico, peças 1-9 +
[mapa](../../dirty/notas/estudo-tcf-hierarquico-mapa.md) + [teoria-cardinalidade](../../dirty/notas/teoria-cardinalidade.md)),
**reconstruído do zero** (não copia a engenhoca dirty — extrai a ideia, per a filosofia). `python run.py`
regenera `outputs/`.

## O que faz (v0)

Um **codec** (`codec.py`) com um formato-protótipo **TCF.8H** (opt-in, fora de `src/tcf`):
```
#TCF.8H <meta-em-colchete>\n<bodies TCF por coluna>
```
- **JSON ↔ TCF.8H ↔ JSON** (`obj_to_tcf`/`tcf_to_obj`): **preserva a árvore** (`{}`=objeto, `[]`=array),
  `M`/`N`/cardinalidade DEDUZIDOS. RT exato. Ex. (S6): `#TCF.8H nome:9,endereco{rua:19,cidade:9,geo{lat:8,lon:8}},telefones[tel]`.
- **CSV ↔ TCF ↔ CSV** (`cols_to_tcf_flat`/`tcf_flat_to_cols`): multi-col plano (o que o TCF já faz). RT exato.
- **CSV + dedução** (`classify`/`deduce_to_obj`): detecta 1:N por FD; mostra o limite.

## Fluxo inspecionável (`outputs/`, amostras minúsculas primeiro)

```
01-json-{S4,S6}.tcf.txt + -decode.json   JSON → TCF.8H → JSON (RT exato)
02-csv-C1-flat.tcf.txt   + -decode.csv    CSV  → TCF → CSV (RT plano)
03-csv-deducao.txt                         CSV: explícito-plano vs implícito (limite + bytes)
00-resumo.txt                              o report gerado
```

## Achado (v0, medido)

- **JSON** (S4 67B, S6 154B): a **árvore É o RT-alvo** → hierarquia **EXPLÍCITA** (preservada). RT exato.
- **CSV** (C1 107B): o **RT-alvo é a tabela plana** → hierarquia **DISPENSÁVEL**. Deduzir a 1:N multi-pai
  (i) precisa de **link posicional** (array-em-array / N raízes — peça 10, v0 não faz) e (ii) **não compensa
  bytes** (o pai sozinho já vira RLE 23B; RLE↔fk duais, peças 1/8). → **confirma a hipótese do owner**:
  "no JSON precisa preservar mais; no CSV não precisa tanto".
- **Consistência OK** em amostras minúsculas → o próximo passo é **escalar** com os datasets sintéticos.

## Dados / ponteiro

Fixtures minúsculas em `inputs/`: **S4/S6** (JSON aninhado, do owner) + **C1** (CSV plano 1:N). Valores
sintéticos/fictícios. **Ponteiro para escalar**: `datasets/synthetic/` (D1-D17) — CSVs canônicos do repo.

## Arquivos

- [`codec.py`](codec.py) — o codec (árvore↔colunas, bracket meta, JSON/CSV, dedução). Protótipo limpo.
- [`run.py`](run.py) — o fluxo inspecionável. [`report.md`](report.md) — achados.

## Estado / próximo

- **É**: protótipo v0 — JSON hierárquico + CSV plano, RT exato; o limite (link posicional) mapeado.
- **Será**: escalar (datasets sintéticos) · tipos (num/bool/null) · o **link posicional** (peça 10) p/
  hierarquizar CSV multi-pai e arrays aninhados · cross-convert JSON↔CSV. Welding em `src/tcf` = decisão futura.
- **Ideias registradas** (owner, a explorar com calma): [tcf8h-proximas-ideias](../../dirty/notas/tcf8h-proximas-ideias.md)
  — consumo DIRETO da estrutura (sem reconstruir JSON; muda o RT-alvo → reorder order-free vira normal) ·
  enriquecimento por **spec com gabarito** (CPF/CEP/telefone; 1º-valor = molde implícito).

## Micro-opt do cabeçalho — CONDIÇÕES (não "quem vence")

As 2 otimizações de fim-de-linha atuam na **última folha**: `SAVING(L) = digits(size(L)) + depth(L)`
(última-sem-size dá os digits, omit-closes dá a depth). — `outputs/05-header-condicoes.txt`.
- **omit-closes**: SEMPRE bom (−1B+, RT-exato). Adotar.
- **reorder** (order-free): vale **SSE** `argmax(digits+depth) ≠ natural-última`. Em **S6 empata** (a
  natural já é o argmax — situação particular); num caso profundo+grande enterrado, ganha +4B. **Não é só
  profundidade** — é digits+depth.
- **hex nos sizes** (ideia do owner): `len(hex(s)) < len(str(s))` para `s∈[10,15]∪[100,255]∪…` → economiza
  por-size e pode mudar o argmax. É **config-dependente**: o ganho é uma conta.

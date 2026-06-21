# Vocabulario controlado — TCF

> Single source of truth para termos do projeto. Use estas formas
> exatas em docs, codigo, commits, conversas. Evita drift ("cadencia"
> vs "cadence" vs "cadência regular").

## Algoritmos canonicos

- **TCF** (Tabular Compact Format) — formato + projeto
- **OBAT** (Online Bidirectional Affix Tokenizer) — camada 1; aka
  `alg16` historico. Codigo: `src/tcf/core/online.py`
- **HCC** (Hierarchical Compositional Coding) — camada 2; aka `M8.A`
  historico. Codigo: `src/tcf/composicional/syntax.py`
- **M1.E** — sintaxe de ambiguidade local (range + escape escopo);
  embutido em HCC

## Conceitos do algoritmo

- **LCP** (Longest Common Prefix) — prefixo maximo entre 2 strings
- **LCS** (Longest Common Suffix) — sufixo maximo entre 2 strings
  (atencao: na literatura geral LCS = Longest Common **Substring**
  ou **Subsequence**; aqui SEMPRE sufixo)
- **Token** — saida do OBAT. Tipos: `TokLit`, `TokRefPref`, `TokRefSuf`
- **Ref atomico** — referencia ja' declarada (id positivo)
- **Ref virtual** — referencia composicional (id negativo, alias temporario)
- **Frag** (fragmento) — substring atomica indexada
- **Quebra** — posicao onde algum token referencia a string (cria
  boundary pra fragmentacao)
- **Sub-tupla** — sequencia de refs reusavel; candidata a virtual ref

## Operadores HCC body

- `~` — operador composicional (cria ref de chain)
- `,` — concat efemero (separa refs adjacentes)
- `^N` — line-ref (refere linha N ja' declarada)
- `*N|<line>` — RLE adjacente (repete `<line>` N vezes)
- `*N+delta|<line>` — seq-RLE (N linhas, escape-digits incrementam por delta)
- `\<digits>` — escape literal (literal e' digit, nao ref)
- `\*`, `\\`, `\~` — escape de chars reservados
- `..` — range (1..4 = refs 1, 2, 3, 4)

## Marcadores de modo (multi-col header, #TCF.7)

Prefixos no tamanho de coluna da meta-line (`# !8=id,@22=cat,nome`):

- `!<size>=<name>` — modo **raw** (V2-A): body em TCF puro (OBAT+HCC); fallback quando TCF < raw
- `@<size>=<name>` — modo **dict** (V2-B): body em stream de indices inteiros (coluna categorica)
- `%<size>=<name>` — modo **split** (V2-C): body com separador estrutural inferido
- `<size>=<name>` (sem prefixo) — modo legado `#TCF.6` (sem V2-A; `# ` no inicio da meta-line)
- Coluna sem size (ultima): `<name>` — modo `min_header` (V2 ADR-0023); body ate' EOF

## Pre-tx (pre-transformation)

- **Pre-stage** / **Pre** — etapa antes do OBAT (detecta tipo, gera dica)
- **Dica generica** — parametro pro OBAT type-agnostic (ex:
  `prefer_shape_consistency=True`, `byte_window=(X,Y)`). Ver
  [ADR-0003](adr/0003-tripartite-pre-obat-hcc.md).
- **Dica viciada** — parametro que nomeia tipo (`type="date"`). REJEITADA.
- **Auto-detect cadence** — heuristica que decide se hint deve ser habilitado.
  Ver `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/auto_pre.py`

## Restricoes de projeto

- **Vertice triplice** — compressao + memoria + latencia, todas restricoes
  duras. Ver [ADR-0002](adr/0002-vertice-triplice-restricao.md).
- **Single-pass** — uma passada sobre input; nao pode look-ahead nem revisitar
- **Low-mem** — memoria extra O(1) alem do necessario
- **Self-containment** — `.tcf` decoda so' com arquivo + algoritmo padrao
- **src/tcf intocado** — fonte da verdade; nao modificar sem aprovacao

## Cadencia (delta-aware)

- **Cadencia regular** — strings consecutivas diferem por delta
  constante (timestamps a cada minuto, IDs sequenciais)
- **Shape** (de tokens OBAT) — `(p_src, p_len, has_L, s_src, s_len)`.
  H-DA-07 preserva shape atraves de transicoes.
- **Cadence break** — transicao onde cardinalidade muda (`\\9` → `\\10`)
  e shape natural mudaria; ver [H-DA-04](../experiments/lab/dirty/notas/roadmap-hipoteses.md)
- **Seq-RLE** — RLE de tokens near-identical com delta consistente.
  Sintaxe: `*N+delta|<template>`. Ver [ADR-0004](adr/0004-multi-column-header-compacto.md)
  e EXP-010.

## Datasets

- **D1-D9** — controle TCF-CORE stress (validados em M9 baseline)
- **D10-D15** — tipos ERP/CRM (data, datetime, CPF, UUID, base64)
- **D11a-h, D11i-m** — variantes incremental T01
  (dia/borda/mensal/datetime/ms/us/ns/tz)
- **D16a-c** — IDs numericos sequenciais (3-digit, 4-digit, prefixados)
- **D17a** — multi-column mixed (4 cols)
- **Canonical** — datasets reais em `Z:/tcf-data/interim/*.db`
  (adult-census, tpch-sf001)
- **Hub SQLite** — formato unificado de canonical datasets em Z:/

## Labs

- **Dirty lab** — exploracao naive; codigo descartavel; ideias extraidas
  para clean. Ver `feedback_dirty_lab_filosofia.md`
- **Clean lab** — prototypes consolidados (`EXP-NNN-*`)
- **Sub-experimento** — pasta numerada dentro de lab (`NN-descricao/`)
- **Welding** — port de codigo dirty pra clean ou pra `src/tcf`. Ver
  `experiments/lab/dirty/notas/welding-plan.md`
- **Pacote** — agrupamento tematico de hipoteses (Pacote 1 = Delta-aware,
  Pacote 2 = Escape-deduction)

## Status markers (hipoteses)

- `aberta` — identificada, nao testada
- `em-exp` — sub-exp ativo testando
- `confirmada-empirica` — validada nos datasets testados; generalizacao
  nao garantida
- `confirmada-conceitual` — empirica + revisao conceitual (ressalvas
  explicitas, real-world)
- `refutada` — testada e nao funciona
- `refutada-parcial` — funciona em alguns cenarios, falha em outros
- `absorvida` — incorporada em hipotese maior
- `subsumida` — coberta por outra hipotese sem teste isolado
- `adiada` — fora de escopo atual

## Roles e processos

- **User scope memory** — `~/.claude/.../memory/`, preferencias pessoais
- **Project scope memory** — `/CLAUDE.md` + `/docs/adr/`, partilhado via git
- **Diario** — `experiments/lab/dirty/notas/diario/YYYY-MM-DD.md`,
  cronologico
- **Checkpoint** — pausa explicita com instrucoes de retomada;
  `experiments/lab/dirty/notas/checkpoints/`
- **Roadmap** — `experiments/lab/dirty/notas/roadmap-hipoteses.md`,
  registry cross-lab

## NAO usar (drift / formas antigas)

| Use | Nao use |
|---|---|
| OBAT | alg16 (so' em contexto historico) |
| HCC | M8.A (so' em contexto historico) |
| confirmada-empirica | confirmada (sem qualificacao) |
| dica generica | hint type-aware |
| Pacote N | macro N |
| Vertice triplice | "estado-da-arte" sem qualificar 3 vetores |
| cadencia regular | cadence (em portugues use cadencia) |

## Como atualizar este vocabulario

- Termo novo aparecendo em conversas: adicionar aqui PRIMEIRO
- Termo mudando significado: deprecate forma antiga ("NAO usar"), adicionar nova
- Cross-link de docs que usam termo extensivamente

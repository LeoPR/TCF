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

## Marcadores de modo (multi-col header, #TCF.8M)

Prefixos no tamanho de coluna do meta INLINE (`#TCF.8M!8=id,@16=cat,nome` — sem `# `, sizes em **HEX**):

- `!<size>=<name>` — modo **raw** (V2-A): body em TCF puro (OBAT+HCC); fallback quando TCF < raw
- `@<size>=<name>` — modo **dict** (V2-B): body em stream de indices inteiros (coluna categorica)
- `%<size>=<name>` — modo **split** (V2-C): body com separador estrutural inferido
- `<size>=<name>` (sem prefixo) — modo **tcf** (OBAT+HCC direto, sem fallback vencer)
- Coluna sem size (ultima): `<name>` — modo `min_header` (ADR-0023); body ate' EOF
- Nome com separador (`,`/`=`/`:`/`\`/prefixo `!@%`) — **escapado com backslash** (T-FMT-NAME-ESCAPING)
- `<size>` (sem `=<name>`, nao-ultima) — coluna ANONIMA (`drop_names`); nome = posicao
- **byte-size em HEX** (T-FMT-HEADER-BASE-HEX, ADR-0032 §3). *(o modo legado `#TCF.6` com prefixo `# ` +
  sizes decimais foi CORTADO de src/tcf, ADR-0032 §4.)*

## Primitiva: referencia por indice (dicionario indexado)

> Consolidacao 2026-07-08 (audit de primitivas, Cluster 1): varios mecanismos com
> nomes diferentes sao a MESMA primitiva — **"guardar cada valor distinto UMA vez e
> referenciar por indice"** — variando so' em (granularidade, escopo, radix, lugar).
> Detalhe + hipoteses: [`dict-referencia-hipoteses.md`](../experiments/lab/dirty/notas/dict-referencia-hipoteses.md) (H-REF).

| instancia | granularidade | escopo | radix do indice | lugar |
|---|---|---|---|---|
| refs OBAT (`TokRefPref`/`TokRefSuf`) + ref atomico/virtual (HCC) | token/afixo (ex.: `fe1` = `fe`+ref linha 1) | intra-coluna | decimal inline | body |
| `^N` line-ref | valor inteiro (linha) | per-coluna (reseta) | decimal inline (exige escape `\<digits>`) | body |
| ref-stream `*N\|^k` | corrente de `^N` em RLE | per-coluna | decimal em RLE | body |
| `@dict` (V2-B, welded) | coluna categorica | per-coluna | base-94 (sem escape) | tabela separada |
| `&<G>` cross-dict (H-GDICT, prototipo) | grupo de colunas | cross-coluna | base-94 (namespace/grupo) | header |
| bN `b1/b2/b4` (research, H-TYPE-02; nomenclatura owner 2026-07-08: b1/b2/b4 = largura FISICA, `b3` = trio b2+null, `b5-b7` = reservados, `B` = bool dict-interno — [char-registry §Eixo 2](../experiments/lab/dirty/notas/tcf8-header-char-registry.md)) | coluna low-card | per-coluna | **w bits** (1/2/4; w=8 = 1 byte, regime do @dict, fora da familia — F3) | body binario (V2-L) |

Consequencias praticas: (1) `^N` JA' e' um dict-index — nao criar mecanismo "novo" de
referencia sem posicionar nos 4 eixos acima (anti-drift); (2) os modos por-coluna
COMPETEM no mesmo `min()` (tcf/raw/dict/split[/bN]) — instancias da primitiva
disputando a mesma coluna, nao features independentes; (3) mudar so' o RADIX
(base-94 → bits) mantem a informacao → compressor de entropia a jusante iguala
(colapso do bN pos-brotli, gate D3); (4) indices RESETAM por coluna (a limitacao
que motivou o cross-dict/H-REF-02).

## Versionamento (3 eixos)

> Single source of truth dos termos de versao. Tres eixos distintos e ortogonais
> (ADR-0024 refinado por ADR-0028). Nao confundir formato (`#TCF.N`) com versao
> de pacote (`0.N.x`).

- **Assinatura de formato / magic number** — `#TCF.N` no início do blob. **Termo canônico**
  (2026-07-01): o `#TCF.N` **NÃO é shebang** (shebang é `#!`, diretiva de interpretador Unix). É uma
  **assinatura de formato textual** que codifica formato+versão, análoga a **`%PDF-1.7`** (também
  `<?xml`, ou binárias `GZ`=`1F 8B`, `MZ`, `PK`). É o que `file`/libmagic usam pra inferir o
  **mimetype** (`application/x-tcf`). "shebang" na prosa antiga = uso histórico impreciso (ADR-0001).
- **Versao de FORMATO** — a versão codificada na assinatura `#TCF.N` (acima). Contrato on-disk; so'
  muda com mudanca de formato. Hoje: **`#TCF.8` (default**, ADR-0032); `#TCF.6`/`#TCF.7` CORTADOS de
  `src/tcf` (git-as-compat, nao mais lidos no codigo vivo). Eixo A.
- **Geracao do encoder** — marco interno do algoritmo (`M8A` -> `M9` -> `M10`).
  Bytes diferentes DENTRO da mesma familia de formato. NAO e' versao publica; nota
  historica. Eixo B.
- **Versao do pacote** — pre-1.0 = `0.<formato>.<release>`. O minor = numero do
  formato (`0.N` <-> `#TCF.N`); o release/patch = contador de entregas dentro
  daquele formato. PyPI `tcf-format`. Eixo C.
- **Release** — contador de entregas (acessorio/fix/poda/perf) DENTRO de um mesmo
  formato. Avanca o patch sem mover o minor.

**Regra de bump (pre-1.0)**:
- mudanca de FORMATO (`#TCF.N` -> `#TCF.N+1`) move o **minor**: `0.(N+1).0`;
- entrega com formato inalterado move so' o **release**: `0.N.x -> 0.N.(x+1)`;
- `1.0` so' quando o formato final congelar -> ai semver estrito.

Exemplo (ADR-0032, 2026-07-09): `#TCF.8` vira o formato DEFAULT = minor `0.8.0`; o ciclo lazy+poda foi
**absorvido** no 0.8.0 (sem release `0.7.2` separado). O rotulo "cross-dict = 0.8.0" esta' SUPERADO (o
gate geral do cross-dict falhou 2026-06-27; o payload do bump e' o `.8`-default, nao o cross-dict).

| Use | Nao use |
|---|---|
| "versao de formato `#TCF.N`" | "versao 0.N" pra falar do formato on-disk |
| "`#TCF.8` = formato default (0.8.0)" | "#TCF.7 default" / "0.7.2 separado" (absorvido no 0.8.0) |
| "minor 0.8.0 = #TCF.8 (default, ADR-0032)" | "0.8.0 = cross-dict" (gate falhou; payload = .8-default) |
| "geracao do encoder M9/M10 (interno)" | "versao M10" como se fosse versao publica |

Cross-link: [`algorithms/TCF-format.md`](algorithms/TCF-format.md) secao Versionamento;
[ADR-0024](adr/0024-pre-1.0-versioning-git-as-compat.md) + [ADR-0028](adr/0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md).

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

---
title: LEVANTAMENTO — P5/union (array polimórfico / tipo-misto) — a última estrutura JSON
type: report
status: aberta
created: 2026-07-17
related:
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - experiments/lab/dirty/notas/funil-fechamento-json-language-2026-07-17.md (P5 = J2)
  - experiments/lab/dirty/notas/matriz-caminhos-hierarquia-2026-07-17.md
  - docs/adr/0033-hierarchical-codec-weld.md
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
---

# Levantamento — P5/union. Para inspeção e DECISÃO do owner.

**[probatório + recomendação]** A questão que fecha (ou declara) a estrutura do `.8`. §1–§2
medido (executado contra o core em `3dc4a81`); §3 pesquisa com fonte; §4–§6 análise/parecer.
**Nada decidido** — a decisão soldar-vs-ratificar é do owner.

## O que é P5 (e o que NÃO é)

**Union = uma coluna (campo ou slot-de-elemento) cujos valores não-nulos NÃO têm todos o mesmo
kind do TCF.** O `.8H` fragmenta por coluna com UM tipo por coluna (tag `n`/`b`/string, ou kind
estrutural scalar/object/array). Union é justamente a coluna que **não tem um tipo só** — quebra a
premissa do shredding.

**Precisão medida — o que PARECE union mas NÃO é** (já faz RT hoje):
- `int + float` no mesmo campo/array → **é number único** (mesmo tipo JSON; P2 tag `n`). RT-OK.
- `[{"a":1}, {"b":2}]` (objetos com chaves diferentes) → **é ragged**, não union (união de chaves,
  P1). RT-OK.
- `null` misturado com qualquer tipo → `null` **não é tipo** (é máscara P3). RT-OK.

## 1. A superfície de falha — MEDIDA (3 lugares, todos fail-loud, todos JSON legítimo)

Todos os casos abaixo: `json.loads/dumps` faz RT (são D_json válidos) e o `.8H` é fail-loud.

| lugar | exemplo | erro atual | sub-classe |
|---|---|---|---|
| **A. elemento de array** | `[1, "a"]` · `[1, true]` | "tipos escalares MISTOS `{n,s}`" | **escalar** |
| | `[1, {"a":2}]` · `[1, [2]]` · `[{"a":1},[2]]` | "array com elementos de tipos mistos" | **estrutural** |
| **B. campo entre registros** | `[{x:1},{x:"a"}]` · `[{x:true},{x:5}]` | "tipos escalares MISTOS" | **escalar** |
| | `[{x:1},{x:{a:2}}]` · `[{x:1},{x:[1,2]}]` | "campo com tipos ESTRUTURAIS mistos" | **estrutural** |
| **C. raiz** | `[1, "a"]` na raiz (via envelope P4b) | "tipos escalares MISTOS" | **escalar** |

**A decomposição que importa pro custo — duas sub-classes:**
- **P5-escalar** (`n\|s\|b` misturados; valores todos escalares, tipos diferentes): `[1,"a"]`,
  `[true,5]`. Os valores são todos folhas — falta só saber o TIPO de cada um.
- **P5-estrutural** (`scalar\|object\|array` misturados): `[1,{"a":2}]`, `[{x:1},{x:[2]}]`. Cada
  branch tem um SUB-SCHEMA completamente diferente (folha vs objeto-com-campos vs array).

Essa distinção é o eixo da decisão (§4): P5-escalar é barato; P5-estrutural é caro.

## 2. Frequência em dado real — MEDIDA (Z: acessível, 200 colunas)

**union é RARO e marginal.** Varredura de **165 colunas reais** (5 datasets, 15 tabelas:
adult, br-identidades, ibge, receita-cnpj, tpch-sf001/sf01) + ~35 sintéticas. Método: cada valor
não-nulo classificado no tipo JSON (number=int∪float, bool, string); `null`/`""` não contam;
union = ≥2 tipos entre não-nulos.

**Resultado: 3 colunas union em 200 (1,5%) — e só 1 é real:**
- **`receita.estabelecimentos.nome_fantasia`** (o único real): 104.141 string + **7** number
  (`"2001"`, `"391"`… em campo free-text). Off-type = **0,007%** — **contaminação** de um campo
  texto, não coluna polimórfica projetada.
- as outras 2 são sintéticas built-to-test (D11 datetime, D13 CPF) → o viés declarado do CLAUDE.md
  ("D10/13/14 = stress, não guia").
- **Zero** colunas polimórficas projetadas em dado real. O `"?"` de missing do adult NÃO gera
  union (vive em coluna já-string).

**Limitação declarada**: 3 canônicos sem `.db` no hub (online-retail, beijing, wine) não medidos —
`online-retail` (free-text Description/StockCode) seria a candidata mais provável e ficou de fora.

### ⚠ Achado colateral que MUDA a prioridade: código com zero-à-esquerda
2 colunas de `receita` são "union" **só sob JSON estrito** (JSON proíbe zero-à-esquerda em número):
- `cnae_principal`: 198.303 número + **1.697** com zero-à-esquerda (`"0230600"`).
- `municipio_cod`: 187.461 + **12.539** com zero-à-esquerda (`"0890"`).

Semanticamente são **um tipo só** (código identificador) — ~14k valores. **Comum em dado
governamental BR** (CNAE, IBGE). Isto NÃO é union real; é uma **decisão de política numérica**:
`"0890"` é number-com-zero ou string? O `.8H` hoje já trata como **string** (preserva o zero, RT
byte-exato) — que é o certo. Só viraria "union" se alguém tentasse tipá-lo como number. **É um
argumento a favor de manter a fronteira estrita**: forçar number sobre código-com-zero perderia o
zero; deixar string preserva. O caso real recorrente NÃO é union-de-tipo — é o TCF já fazendo a
coisa certa (string-core preserva).

## 3. Como os formatos representam union — pesquisa com fonte (2026-07-17)

O mecanismo COLUNAR canônico é o **Arrow dense union**, e ele é *exatamente* o que um codec
shredded-por-coluna precisa:

| formato | union? | mecanismo | custo/valor |
|---|---|---|---|
| **Arrow dense** | nativo | **type-id buffer** (1B, o discriminador) + **offset buffer** (int32) + **N child-arrays** (1 sub-coluna densa por branch) | **5 B** (1+4) + child arrays |
| **Arrow sparse** | nativo | type-id buffer + child-arrays FULL-LENGTH (sem offset) | **1 B** + slots vazios |
| **Parquet** | **NÃO** ("lacks a native union/mixed-type column") | workaround **VARIANT** (2025): blob binário auto-descritivo `value`+`metadata` em coluna BINARY; **shredding** re-extrai campos frequentes p/ colunas tipadas | blob por linha |
| **Protobuf** | `oneof` (schema) | discriminador = o próprio **field-number no tag** (nada extra no wire) | ~1 B (o tag que já viria) |
| **Avro** | union 1ª classe | **branch-index** (varint) antes do valor | 1 B (até ~64 branches) |
| **CBOR / JSON** | nativo por self-description | tipo viaja em CADA item (major-type nos 3 bits altos) | 0 B extra, mas NUNCA fatora tipo do valor |

**As duas lições que decidem o custo no TCF:**
1. **Confirmação do desenho**: union num codec por-coluna = **coluna-discriminador de tipo +
   sub-colunas por branch** — literalmente o Arrow dense union (type-id = discriminador; child
   arrays = sub-colunas; offset = a cola). Meu esboço §4 (WELD) é o padrão da indústria, não
   invenção.
2. **O TCF tem uma vantagem estrutural sobre o Arrow aqui**: os 5 B/valor do Arrow são FLAT. No
   TCF a coluna-discriminador passa pelo L1 — e tipo-misto em dado real tende a ser **blocado**
   (não intercalado linha-a-linha), então o discriminador vira `*N|<tipo>` e **colapsa para
   quase-zero** por RLE. É o mesmo motivo pelo qual o TCF ocupa "áreas explicáveis": o
   agrupamento é visível e barato. O overhead irredutível é ~1 B/valor ANTES do RLE.
3. **Parquet é o espelho do TCF**: ambos são shredded-schema-fixo, e Parquet **recusa** union
   nativo pela mesma razão que o `.8H` fail-louda hoje. A resposta deles (VARIANT + shredding) é
   um blob auto-descritivo — o oposto da filosofia textual/explicável do TCF. Ou seja: **ratificar
   a fronteira é a mesma escolha que o Parquet fez** (e ele é o formato colunar de referência).

## 4. Opções de gramática (esboço — a escolha é do owner)

Reusando o maquinário welded o máximo possível:

### Opção RATIFICAR (custo ~0) — P5 é a fronteira declarada do `.8`
Manter fail-loud. O material de fechamento reporta **"fração in-class"** (não "qualquer JSON").
Coerente com o funil (P5 = J2, pausa deliberada). O `.8H` cobre D_json **menos** union — que é
raro em tabular (§2 confirma/refuta). **Nada a implementar; documentar a fronteira.**

### Opção WELD-ESCALAR (custo baixo) — só P5-escalar
Coluna com escalares de tipos mistos ganha um **type-tag por valor** (uma coluna de discriminador
`n`/`s`/`b`, 1 char/valor, que colapsa por RLE se houver padrão) + os valores serializados como
hoje; decode re-tipa por-valor. É a extensão natural do P2 (tag por-COLUNA → tag por-VALOR).
Cobre `[1,"a"]`, `[true,5]`. **NÃO cobre** scalar+object+array. Gramática: um marcador de "coluna
union-escalar" no meta + a coluna de tags.

### Opção WELD-PLENO (custo alto) — union estrutural (dense union do Arrow)
Discriminador de branch por valor + **sub-colunas por branch** (uma sub-árvore de colunas para o
branch-objeto, outra para o branch-array, a coluna de folhas para o branch-escalar). É o dense
union do Arrow transposto pro `.8H`. Cobre tudo, mas multiplica colunas de controle e é a
gramática mais complexa do codec. Candidato a 1.0, não a `.8`.

## 5. Tensão explícita (a decisão é sua)

O owner tem DUAS diretrizes que apontam em direções opostas AQUI:
- **Funil (2026-07-17)**: P5 = J2, com **pausa explícita antes**. → ratificar/adiar.
- **"tudo que mexe em estrutura no `.8`" (2026-07-17)**: P5 É estrutura. → soldar.

O que resolve a tensão é a **frequência real** (§2) e o **custo por sub-classe** (§4): se union é
raro E o valor prático é P5-escalar, o meio-termo **WELD-ESCALAR** fecha "quase toda" a union por
pouco custo, deixando o estrutural (raro e caro) como fronteira 1.0.

## 6. Recomendação — **RATIFICAR a fronteira** (com os fatos na mesa)

Os três fatos convergem:
1. **Frequência (§2)**: union real = **1 coluna em 165**, por contaminação de **0,007%** — não há
   polimorfismo projetado em dado real. O caso recorrente ("código com zero-à-esquerda") **não é
   union**; é o `.8H` já fazendo o certo (string preserva o zero).
2. **Indústria (§3)**: **Parquet — o formato colunar de referência — RECUSA union nativo** pela
   MESMA razão que o `.8H` (shredded-schema-fixo). A resposta deles (VARIANT = blob binário
   auto-descritivo) é o oposto da filosofia textual/explicável do TCF. Ratificar nos alinha ao
   Parquet; soldar nos empurraria pro blob-por-linha do CBOR.
3. **Funil (§5)**: P5 = J2, pausa deliberada. A frequência CONFIRMA a intuição do funil.

**Recomendação: ratificar o fail-loud de union como a fronteira declarada do `.8`.** Concretamente:
- **Não implementar P5 no `.8`.** O `.8H` cobre **D_json − union**. O material de fechamento
  reporta **"paridade com o fluxo JSON exceto tipo-misto no mesmo slot"** (honesto, não "qualquer
  JSON").
- **Endurecer a fronteira** (barato, é `.8`): a mensagem de fail-loud de union deve ser tipada e
  ENSINAR ("coluna/array com tipos mistos {n,s} — union/P5 fora do `.8`; separe por tipo ou use
  string"). Hoje já é `HierarchicalError` (medido) — só refinar a mensagem. **Isto sim é `.8`**
  (é fronteira/contrato, não capacidade nova).
- **Registrar o WELD como 1.0/J2** com o desenho pronto (§4): a ordem de custo é
  WELD-ESCALAR (tag-por-valor, RLE-friendly) → WELD-PLENO (dense union). Se um dia um corpus real
  semi-estruturado (config/eventos/`online-retail`) pagar, reabre-se com o desenho na mão.

**Resolução da tensão do §5**: "estrutura no `.8`" vale para estrutura **que o dado real usa** —
e union não é usado (medido). Ratificar não contradiz a diretriz; a **cumpre**, porque a diretriz
é sobre fechar o que paga, e o funil já dizia isso (uso vs completude). Union é o ponto onde
completude teórica e uso real divergem mais — e o dado escolheu uso.

**O que NÃO muda**: union é **fail-loud honesto** (0 wire, 0 corrupção) — não há dívida, só
capacidade ausente e **agora declarada com fundamento** (frequência + indústria + funil).

## 7. Consequência: a estrutura do `.8` fica COMPLETA

Ratificado o P5, **não há mais estrutura pendente no `.8`** (o sweep dos 22 tickets já mostrou:
o resto é otimização/ferramenta/release). As duas bordas declaradas (contagem-de-contêiner-vazio =
problema B → T-FMT-OMIT-OR-DECLARE; ordem-de-chaves-ragged = S6) são **decisões de contrato**, não
capacidade — podem fechar no `.8` (barato) ou pré-1.0. O caminho vira **RELEASE** (F3/F4/F6/C3) +
a decisão de timing (0.8.0 feature-complete agora vs 0.8.x incremental).

---
title: LEVANTAMENTO — P4 rep-level / N-raízes / root (o STRUCTURAL que falta) — PARA INSPEÇÃO
type: plan
status: aberta
created: 2026-07-16
updated: 2026-07-16
related:
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - experiments/lab/dirty/2026-07-06-2246-tcf8h-fronteira-link-posicional/ (B3 caracterizado)
  - experiments/lab/dirty/notas/hierarquia-inventario-hipoteses.md (taxonomia presença/repetição/normalização)
  - docs/adr/0033-hierarchical-codec-weld.md
---

# Levantamento — P4 (rep-level / N-raízes / root). Para inspeção. NÃO implementado.

## Onde estamos

Escalares JSON COMPLETOS (P1 presença · P3a/P3b null · P2 tipos). Falta a **ESTRUTURA** que o JSON
permite e o codec ainda rejeita (verificado hoje):

| construto JSON (comum) | codec hoje |
|---|---|
| **array-em-array** `[[1,2],[3]]`, `[[{...}]]` | ❌ "valor escalar de tipo não suportado: list" |
| **root = array de arrays / de escalares** `[[1,2],[3,4]]` | ❌ "espera objetos (dict) em cada registro" |
| **root = objeto único** `{...}` (resposta de API típica!) | ❌ "espera lista NÃO-VAZIA de objetos" |
| **root = escalar / null** `42`, `"x"`, `null` | ❌ idem |

## O primitivo faltante (inventário, taxonomia SETTLED)

`presença → repetição → normalização`. A **máscara** (P1/P3) é o **definition-level do Dremel**
(presença/nulidade). Falta o **repetition-level**: **um NÚMERO posicional** — onde o array aninhado
reinicia. O inventário: *"tudo difícil colapsa em UM primitivo: o link posicional (um número)"*
(H-HET-REPLEVEL-SINGLE-PRIMITIVE-03). Convergência: Parquet/Dremel = def-level + **rep-level** (streams
distintos); temos o def, falta o rep.

## Insight TCF (proposta): o rep-level colapsa no COUNT recursivo

O TCF já tem o `#count` (multiplicidade 1:N). Um **array cujo ELEMENTO é um array** reusa o MESMO
mecanismo count→elementos, **recursivamente** — não precisa de um stream rep-level flat separado
(a menos que se queira Dremel puro). Ex.: `[[1,2],[3]]` → count-externo=2, counts-internos=[2,1],
folhas=[1,2,3]. Cada nível de aninhamento = mais um nível de count. É a extensão natural do que já
existe (arr_scalars/arr_objects viram casos de "elemento = escalar/objeto"; falta "elemento = array").

## Design proposto (a inspecionar)

### P4a — array-em-array (novo kind `arr_arrays`)
- `_field_node`: se os elementos de um array são ARRAYS → `arr_arrays` (elemento recursivo).
- leaves: `count` (externo) → o elemento-array recursivo (que tem seu próprio `count` + folhas).
- Gramática (candidata): `m#:count[#:innercount[]:asize<tag>]` — o elemento entre `[...]` é a spec do
  array interno (recursivo). Compõe com element-mask (null-de-array-elemento) e tipos.
- Profundidade arbitrária = recursão (medir custo de counts aninhados).

### P4b — root generalizado (N-raízes + root não-list[dict])
- Hoje o contrato é `list[dict]`. Generalizar o **root** pra qualquer valor JSON:
  - `list[dict]` (atual) · `list[list]`/`list[scalar]` (via arr_arrays/arr_scalars no root) ·
    objeto único `{...}` · escalar · `null`.
- Duas rotas: **raiz sintética** (envolve o documento num registro-raiz único — H-HET-NROOTS-SYNTHROOT-04,
  barato SE a ordem cross-root é livre) OU **root polimórfico** (o discriminador do header diz o tipo
  da raiz). **Muda o contrato da API** (`encode_hierarchical(list[dict])` → aceita `Any` JSON).

## DECISÕES a fechar (o que peço que você analise)

1. **array-em-array: recursive-count (`arr_arrays`) ou Dremel rep-level flat?** Recomendo
   **recursive-count** — reusa o `#count`, mantém a separabilidade O(1)/stream (Ciclo 4), inspecionável.
   O rep-level flat é mais Dremel-puro mas menos alinhado ao nosso count-por-nível.
2. **Root: quão longe generalizar?** Opções: (a) só `list[X]` (arrays no root); (b) + objeto único;
   (c) qualquer valor JSON (incl. escalar/null no root). Recomendo **(c)** pra paridade real (API
   devolve `{...}` único), via **raiz sintética** (envolve tudo, reversível) — decide o contrato da API.
3. **null-na-raiz** (`null` como documento inteiro): entra no root generalizado (raiz sintética + máscara).
4. **Escopo: P4a e P4b juntos ou P4a → P4b?** Recomendo **P4a (array-em-array) primeiro** (o primitivo),
   **P4b (root) depois** (é contrato de API, mais sensível).
5. **Profundidade**: recursão cobre arbitrário; declarar/medir o custo (counts aninhados) — sem limite artificial.

## Fronteira / fora (declarar)

- **Array POLIMÓRFICO** (elementos de tipos DIFERENTES no mesmo array: `[1, "a", {}]`) = **P5 union**,
  segue fail-loud. P4 é array-em-array HOMOGÊNEO (todos os elementos são arrays), não polimórfico.
- **N:N / grafo / referência compartilhada** = a capacidade exclusiva (H-HIER-SHARED-REF-01), além do JSON.
- Ordem cross-root (se a raiz sintética assume ordem livre e não é) — verificar no estudo.

## Metodologia (padrão P1/P3/P2)

Estudo-primeiro (didático: array-em-array raso/fundo, matriz, N-raízes, root variado, null-root,
compõe com null+tipo) → fechar a gramática → weld no core (aditivo; kind `arr_arrays` + root) → gate
byte-canônico + **auditoria adversarial** (gramática nova esconde corrupção — F1 do P3b).

## Confiança

`Média` no design (o recursive-count é natural; o root muda contrato — mais decisão que técnica). O
difícil é a gramática do array-interno e o contrato do root. Depois de P4, falta só **P5 union** p/
a fronteira JSON completa (reportar fração in-class até lá).

## Revisão crítica independente — 2026-07-16

**[probatório→opinião; não é decisão do owner]** Revisão read-only do P2 welded e deste levantamento,
seguida de probes adversariais e suíte completa. Estado observado: P2 preserva tipo nos caminhos
válidos e compõe com P3a/P3b; o endurecimento de decode de `268608d` rejeita bool/number inválidos,
NaN e infinitos. Suíte no estado revisado: **731 passed, 2 skipped, 2 xfailed**. Os `xfail` são bugs
L1 pré-existentes e separados (`BUG-SEQRLE-RANGE-EMPTY-B` e `BUG-BRACKET-CELL-LOSS`).

### Achado residual do P2

O parser de metadata ainda não rejeita toda **tag desconhecida** depois do tamanho de dado. Probe com
header corretamente enquadrado `x:<size>x` resultou em `[]`, pois `stag()` não consome `x` e o parser
o reinterpreta como novo campo. Não afeta wire emitido pelo encoder, mas viola fail-loud para blob
estrangeiro/corrompido. Tratar como hardening de framing: tag após size deve ser `n`, `b` ou ausência;
qualquer outro caractere não estrutural deve levantar `HierarchicalError`, com teste adversarial.

### Parecer sobre P4a — estrutura

O **count recursivo** é a direção recomendada. Ele não elimina conceitualmente repetition-level;
representa a mesma informação posicional em forma hierárquica por nível, alinhada ao `#count` já
existente. Para `[[1,2],[3]]`: count externo `2`, counts internos `[2,1]`, folhas `[1,2,3]`. Não há
evidência de que um stream flat de rep-level pague a gramática e o mecanismo adicionais nesta etapa.

Gate mínimo antes de weld:

- matriz rasa, profundidade >2 e arrays internos vazios;
- array de arrays de objetos;
- null como elemento entre arrays (`[[1], null, [2]]`): decidir se P3b cobre o slot estrutural ou se
  fica fora; não classificá-lo automaticamente como union P5;
- count interno truncado, excedente e fechamento/tag inválidos;
- custo de header/streams medido por profundidade, sem impor limite arbitrário antes da evidência.

### Parecer sobre P4b — contrato de raiz

Separar P4b de P4a. P4a adiciona um kind estrutural interno; P4b muda entrada e saída públicas de
`encode_hierarchical(list[dict])` para uma raiz generalizada. Os dois incrementos exigem decisões e
gates distintos.

Terminologia: JSON tem **uma raiz**. Um array na raiz tem N elementos, não N raízes. Usar daqui em
diante **raiz generalizada** / **array na raiz**; conservar “N-raízes” apenas como nome histórico da
hipótese e dos links existentes.

A ordem de arrays é semântica e **não é livre**. Uma raiz sintética só é aceitável se for envelope
transparente e explicitamente discriminado no wire: o decoder precisa restaurar exatamente o tipo da
raiz e nunca devolver o envelope. Sem um `root_kind` inequívoco, `list[dict]` fica ambíguo entre o
DatasetH atual e um documento cujo valor-raiz é um array. Gate de P4b deve distinguir e preservar:
`[]`, `[{}]`, `{}`, objeto único, array de escalares, escalar, string vazia e `null` na raiz.

### Ordem recomendada de investigação

1. **P4a** em lab próprio: fechar modelo recursivo + gramática + adversarial.
2. Weld de P4a somente após aprovação de `src/tcf` e gates flat/real-world.
3. **P4b** em estudo separado: decidir envelope/discriminador e contrato de API.
4. P5 union continua fora; não usar “qualquer JSON” antes dele.

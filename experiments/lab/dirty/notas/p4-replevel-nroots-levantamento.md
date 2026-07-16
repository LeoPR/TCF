---
title: LEVANTAMENTO — P4 rep-level / N-raízes / root (o STRUCTURAL que falta) — PARA INSPEÇÃO
type: plan
status: aberta
created: 2026-07-16
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

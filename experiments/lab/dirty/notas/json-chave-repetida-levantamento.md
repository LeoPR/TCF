---
title: LEVANTAMENTO — chave repetida em JSON: o que significa, como o modelo resolve, opções exaustivas
type: report
status: aberta
created: 2026-07-17
related:
  - experiments/lab/dirty/2026-07-17-0050-json-chave-repetida-semantica/ (as medições)
  - experiments/lab/dirty/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/ (o contrato S0 que rejeitou)
  - tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md
  - tickets/T-API-BOUNDARY-CONTRACTS.md
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
---

# Chave repetida: o que significa, como o modelo resolve, e a revisão da escolha do S0

**[probatório]** Tudo abaixo é MEDIDO (lab `2026-07-17-0050`, Python 3.13 `json`), exceto §1
(normas, do conhecimento — verificável). Pergunta do owner: entender puramente o que significa a
chave repetida; o que o json CONSTRÓI; como fazer estrutura dict+array que retorne; se a opção do
S0 (fail-loud) foi engessada ou limpa; e "o json colidiria chaves? se não, temos inferência".

## 1. O que a chave repetida É (normas)

- **ECMA-404**: texto com chave repetida é **sintaticamente válido** — a norma não exige unicidade.
- **RFC 8259 §4**: nomes **SHOULD** be unique; com repetição, o comportamento do receptor é
  **imprevisível** — a própria RFC lista as três famílias que existem na prática: last-wins,
  erro, ou reportar todos os pares.

Ou seja: a duplicata é um fenômeno do **TEXTO**. Ela não tem semântica definida — cada receptor
inventa a sua. Este é o fato-base: *não há significado a preservar*, há uma ambiguidade a resolver.

## 2. O que o json CONSTRÓI (medido, simples → 2 níveis → difíceis)

| texto | `json.loads` constrói | pares reais (lossless via `object_pairs_hook`) |
|---|---|---|
| `{"a":1,"a":2}` | `{"a":2}` — **last-wins CALADO** | `[(a,1),(a,2)]` |
| `{"a":1,"b":9,"a":2}` | `{"a":2,"b":9}` — posição da 1ª, valor da última | `[(a,1),(b,9),(a,2)]` |
| `{"o":{"a":1,"a":2}}` | idem em QUALQUER nível | `[(o,[(a,1),(a,2)])]` |
| `[{"a":1,"a":2},{"a":3}]` | idem em array de objetos | — |
| `{"a":1,"a":[1,2]}` | último vence mesmo com TIPOS diferentes | — |
| `{"a":1,"a":1}` | `{"a":1}` — indistinguível de chave única | — |
| `{"a":1,"a":{"b":2,"b":3}}` | `{"a":{"b":3}}` — dupla perda, 2 níveis | — |

**Resposta à pergunta "o que ele constrói quando chaves similares aparecem":** um dict com a
posição da primeira aparição e o valor da última — **descartando o resto em silêncio**. A única
forma de VER os pares todos é sair do modelo dict (`object_pairs_hook` → lista de pares).

## 3. "O json colidiria chaves?" — a inferência (o ponto 8 do owner), medida

**Com chaves STRING: NÃO, nunca.** O colapso acontece **no modelo, antes de qualquer
serialização**: o literal Python `{"a":1,"a":2}` já É `{"a":2}` antes do `json.dumps` ver
qualquer coisa (`{True:'x',1:'y'}` idem — `True==1` colapsa no dict). Portanto um texto JSON
**gerado de dict+array com chaves string jamais contém duplicata** → se um receptor VÊ duplicata,
o texto **não veio** desse modelo (é estrangeiro/manual/adulterado). Essa é exatamente a
inferência que você intuiu — e ela é a justificativa do fail-loud: duplicata = evidência de
origem fora do contrato.

**O ÚNICO furo (medido): chave NÃO-string.** `json.dumps({1:"x","1":"y"})` **EMITE**
`{"1":"x","1":"y"}` — duplicata real, por coerção int→str — e o round-trip perde `"x"` calado.
`{None:"x"}` → `{"null":"x"}` (colide com chave literal `"null"`). Bônus medidos do export:
`dumps(nan)` → `NaN` (**inválido** por RFC — `allow_nan=True` é o default do Python!); tuple→list
(o tipo não volta); set/bytes → TypeError. **Regra de borda que isso induz: chaves string, só.**

## 4. "Como faço estrutura dict+array que retorne?" — as opções exaustivas

### 4a. Representações de multi-valor (decisão do PRODUTOR, todas RT-medidas)

| forma | exemplo | RT | perde ordem? | perde multiplicidade? | colide com dado legítimo? | muda o modelo? |
|---|---|---|---|---|---|---|
| **R1 array-valued** | `{"a":[1,2]}` | ✅ | não | não | **não distingue** "lista" de "repetida" — mas isso é escolha semântica do produtor, não perda | não |
| **R2 lista-de-pares** | `[["a",1],["a",2]]` | ✅ | não | não | não | **sim** (não é objeto) |
| R3 sufixo-renomeio | `{"a":1,"a__2":2}` | ✅ | não | não | **SIM** (chave literal `a__2`) — regride ao problema do escape | não |
| R4 envelope-marcador | `{"a":{"__dup__":[1,2]}}` | ✅ | não | não | **SIM** (chave literal `__dup__`) | não |

R1 é o que o ecossistema faz (HTTP APIs, xmltodict, query strings `a=1&a=2` → array). R2 é a
única lossless que preserva até a *duplicata em si* — ao custo de sair do modelo objeto. R3/R4
recriam o problema que resolvem (marcador colide com dado — a lição do escape).

### 4b. Políticas de IMPORT de texto estrangeiro (decisão do ADAPTADOR)

| política | resultado medido | perde? | veredicto |
|---|---|---|---|
| **P0 fail-loud** (S0) | `ValueError: chave duplicada ['a']` | **zero** — não decide pelo usuário | **default correto** |
| P1 last-wins (default py/js) | `{"a":2}` | perda **calada** | nunca como default nosso |
| P2 first-wins | `{"a":1}` | perda calada | idem |
| P3 collect→array | `{"a":[1,2]}` | **COLISÃO PROVADA**: `== loads('{"a":[1,2]}')` → `True` — indistinguível do array legítimo | só como opt-in declarado |
| P4 lista-de-pares | `[(a,1),(a,2)]` | zero, mas **sai do modelo** | opt-in p/ quem precisa forense |

## 5. Revisão da escolha do S0: engessada ou limpa? — **LIMPA e generalista**

Três razões, todas medidas:

1. **A "opção inexistente" é óbvia no modelo**: dict+array não expressa duplicata (colapsa antes
   de serializar). O fail-loud do S0 não proíbe nada que o modelo permita — ele **espelha a
   impossibilidade do próprio modelo**. Não há round-trip a perder de algo que o modelo não
   segura.
2. **Toda alternativa perde calado ou colide**: P1/P2 perdem (medido); P3 colide com dado
   legítimo (medido, `True`); P4 muda o modelo. O fail-loud é a única política que devolve a
   decisão a quem tem o contexto (o produtor escolhe R1 ou R2 ANTES de transmitir).
3. **É o mesmo desenho do resto do projeto**: T-FMT-OMIT-OR-DECLARE (não-dedutível → declaração),
   e o `.8H` já faz o mesmo no wire (coluna duplicada no meta → `HierarchicalError`, hardening
   P4a — medido de novo aqui).

**Onde a flexibilidade entra sem engessar**: as políticas P1-P4 pertencem ao **adaptador**
(texto estrangeiro → DatasetH), como transformações **opt-in declaradas** — território de gadget
(`scripts/`), fora do core. O core nunca "resolve" duplicata; o adaptador pode, se o usuário
pedir por nome.

## 6. Bordas do `.8H` (medidas agora) + 1 achado

- **API**: duplicata inexpressível (o dict colapsa antes) ✓.
- **Wire estrangeiro** com coluna duplicada: `HierarchicalError: campo duplicado 'a' no header` ✓.
- **NFC×NFD** (`café` composto × decomposto): chaves DISTINTAS no modelo, no json e no `.8H`
  (RT ✓, sem normalização) — consistente; "parecer igual" não é colidir.
- **ACHADO — chave não-string na borda**: `encode_hierarchical([{1:"x"}])` → **`TypeError` CRU**
  ("argument of type 'int' is not iterable"); `{None:"x"}` → `HierarchicalError` com mensagem
  **enganosa** ("nome de campo vazio"). Rejeitar está CERTO (evita o furo da coerção do §3 —
  o `.8H` é mais seguro que o `json.dumps` aqui!) — mas o erro deve ser tipado e ensinar
  ("chave de objeto deve ser str"). Registrado em T-API-BOUNDARY-CONTRACTS; **não consertado**
  (`src/tcf` = aprovação).

## 7. Recomendações (para sua decisão)

1. **Manter fail-loud** no S0 e no `.8H` (nada a mudar — a escolha foi limpa).
2. **Declarar a regra de borda "chave = str"** no contrato DatasetH (fecha o único furo real,
   o da coerção) e re-tipar o TypeError cru quando você aprovar mexer.
3. **Política de adaptador** (P1/P3/P4 opt-in por nome) fica REGISTRADA como possibilidade de
   gadget futuro — não construir agora.
4. R1 (array-valued) documentada como a representação recomendada de multi-valor para produtores;
   R2 (lista-de-pares) para quem precisa preservar a forma textual estrangeira.

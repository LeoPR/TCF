# ADR-0047 — `schema=`: o parâmetro único de spec da API (corta `nature=`/`nature_per_col=`)

- **Status**: **aceito — SOLDADO** (2026-08-22, aprovação do owner: *"esse é o momento de fazer
  essa faxina, o .8 é pra fazer tudo isso"*; e sobre o destino: *"registre que quero o Schema"*).
  Suíte 1315 → **1336**; gates byte-canônicos intactos (D17a=300, D1–D9, real-world);
  varredor de snippets 71/0.
- **Supersede** (na API): os canais `nature=` (ADR-0015) e `nature_per_col=` como **parâmetros
  públicos**. Os nomes sobrevivem só como canais INTERNOS pós-normalização.
- **Registra o destino**: o objeto `Schema` prescritivo —
  [`T-API-SCHEMA-PRESCRITIVO`](../../tickets/T-API-SCHEMA-PRESCRITIVO.md) — que entrará como
  mais uma FORMA deste mesmo parâmetro (aditivo, não rename).
- **Política reafirmada pelo owner (2026-08-22)**: pré-1.0 o controle de versão é de
  DESENVOLVIMENTO — sem modos de compatibilidade até o 1.0; o passado se lê pelo git
  (ADR-0024/0028). Este corte é seco, como o do legado `.6/.7` (ADR-0032): sem alias,
  sem depreciação.

## O problema (medido no inventário 2026-08-22)

1. **Dois parâmetros para um conceito**, mutuamente exclusivos por rota: `nature=` só single-col,
   `nature_per_col=` só multi/dataset — passar o "errado" era `ValueError` apontando o outro.
2. **Posição não existia**: `nature_per_col={0: spec}` e `{"0": spec}+drop_names` → "coluna não
   existe".
3. **2 dos 5 specs soldados eram INALCANÇÁVEIS pela API**: `SPEC_DATA_ISO` e `SPEC_INT_PAD` não
   eram exportados de `tcf`, nem o `SPEC_REGISTRY` — quem quisesse 100 specs teria que importar
   100 objetos, sem ter como nomeá-los.
4. A pergunta do owner que disparou: *"se eu tiver 100 specs, como farei? não é mais simples
   declarar as colunas e os specs deles?"*

## Decisão

`encode(data, *, schema=None, …)` e `decode(text, *, schema=None, …)` — um parâmetro, quatro
formas, válido nas quatro rotas:

| forma | significado |
|---|---|
| `"cpf"` (str) | UM spec pelo **name** do registry (single-col) |
| objeto spec | idem, direto (specs de terceiros; duck: tem `wire_id`) |
| `{"col": "cpf", 3: "ip", "x": SPEC, "y": None}` | por coluna — chave **str = NOME** (`''` e `'0'` inclusos, ADR-0046), **int = POSIÇÃO** na ordem das colunas; valor = name/objeto/None |
| `Schema(...)` *(futuro)* | a forma longa — ticket próprio, aditiva |

- Resolução string→spec **pelo `name`** (`SPEC_REGISTRY`, plano da API do ADR-0041) — nunca pelo
  `wire_id` (dois nomes para a mesma coisa é convite a deriva). Name desconhecido → `ValueError`
  listando o registry.
- **Fail-loud em toda forma inválida**: posição fora do range, colisão posição/nome na mesma
  coluna, chave `bool`, valor de tipo errado, posição em entrada `list` (dataset `.8H` endereça
  por PATH; single-col usa a forma escalar). Spec duck-typed **sem `wire_id`** → a recusa
  ensinante de `_valida_wire_id` (fonte única), não um TypeError genérico.
- A normalização vive na **porta** (`encoder.py`/`decoder.py`); o miolo das rotas não mudou.
- No decode o header segue **autoritativo** (pós-FLOOR): coluna sem `:id` é definitivamente
  original; o `schema=` out-of-band só cruza com ids fora do registry — semântica pré-existente,
  intocada.
- **Exports novos**: `SPEC_DATA_ISO`, `SPEC_INT_PAD`, `SPEC_REGISTRY` (re-pin do
  `EXPECTED_PUBLIC_API`).

## Byte-neutralidade

Por construção — o parâmetro só decide **qual spec vai em qual coluna**, que é o que os canais
internos já faziam — e por gate: D17a=300, D1–D9, real-world byte-idênticos; paridade
string-vs-objeto e posição-vs-nome pinada em `tests/test_schema_param.py`.

## O bug que o corte revelou (e fechou)

O `.8H` chamava a **API pública por dentro** com o kwarg antigo
(`hierarchical.py: _encode_col(raw, nature=spec, …)`) sob um `except Exception`. Após o corte,
o `TypeError` era engolido e o spec sumia **calado** — wire válido, sem `:id`, byte-idêntico ao
sem-spec. Pego por `test_hier_nature_cpf_rt_e_comprime` (compara COM×SEM); o meu teste de paridade
não pegava porque comparava `schema=`×`schema=` — **os dois lados dropando também são iguais**.
Consertos: a chamada migrada, o `except` estreitado para `ValueError` (só o caso legítimo:
valor que o flat não representa), e cláusula anti-tautologia no teste (`:cpf` no meta prova
aplicação). Lição de método: teste de paridade precisa de uma **testemunha de aplicação**,
não só da igualdade.

## Migração (o censo do corte)

`src/tcf` 2 portas + 1 chamada interna + docstrings/mensagens (6 arquivos) · testes: **148 linhas**
em 8 arquivos migradas mecanicamente + 6 pins de mensagem re-escritos + `TestLacunaImpostorDuckType`
re-pinado · docs vivas: `use-natures`, `api`, `encode-knobs`, READMEs EN/PT (0 sobras; snippets
71/0) · scripts: 7 arquivos. **ADRs e labs históricos intocados** (imutáveis/registro).

## Alternativas rejeitadas

- **Alias/depreciação** — sem precedente no projeto; pré-1.0 é corte seco (`.6/.7`).
- **Resolver string também pelo `wire_id`** — deriva; o wire_id é plano do DADO.
- **Adivinhar nome-vs-posição** da chave (str "0" como posição) — a coluna literalmente chamada
  `"0"` existe e o nome vazio é legítimo (ADR-0046); int/str é a única regra sem ambiguidade.

## Evidência

`tests/test_schema_param.py` (contrato, 21 testes) · suíte 1336 · gates verdes · inventário e
weld no diário `2026-08-22` · aprovação e direção do owner na mesma data.

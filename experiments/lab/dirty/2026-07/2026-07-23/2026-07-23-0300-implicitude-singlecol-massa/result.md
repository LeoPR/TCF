# Single-column em massa por TIPO — baseline atual + equivalência JSON

N = 500 elementos por caso. Mede o wire ATUAL, o RT (== JSON), e o OVERHEAD estrutural (bytes que NÃO são os elementos) — o que um single-col tipado arrancaria.

| caso | tipo | forma do wire | total B | elems B | overhead B | B/elem | RT=JSON |
|---|---|---|---:|---:|---:|---:|:---:|
| str-email | string | órfão (0 B header) | 3583 | 3583 | 0 | 7.17 | ✅ |
| str-lowcard | string | órfão (0 B header) | 1510 | 1510 | 0 | 3.02 | ✅ |
| str-uuid | string | órfão (0 B header) | 5637 | 5637 | 0 | 11.27 | ✅ |
| str-freetext | string | órfão (0 B header) | 3624 | 3624 | 0 | 7.25 | ✅ |
| int-seq | number | #TCF.8H (#V) | 57 | 31 | 26 | 0.11 | ✅ |
| int-rand | number | #TCF.8H (#V) | 4370 | 4342 | 28 | 8.74 | ✅ |
| int-repeat | number | #TCF.8H (#V) | 34 | 9 | 25 | 0.07 | ✅ |
| int-big | number | #TCF.8H (#V) | 89 | 63 | 26 | 0.18 | ✅ |
| float-dec | number | #TCF.8H (#V) | 4772 | 4744 | 28 | 9.54 | ✅ |
| bool-alt | bool | #TCF.8H (#V) | 1533 | 1505 | 28 | 3.07 | ✅ |
| null-all | null | #TCF.8H (#V) | 32 | 13 | 19 | 0.06 | ✅ |
| spec-cpf | spec:cpf | #TCF.8 nature (:cpf) | 1527 | 1515 | 12 | 3.05 | ✅ |
| spec-cnpj | spec:cnpj | #TCF.8 nature (:cnpj) | 1526 | 1513 | 13 | 3.05 | ✅ |
| spec-ip | spec:ip | #TCF.8 nature (:ip) | 92 | 81 | 11 | 0.18 | ✅ |

## Leitura

- **string** (órfão): header 0 B, overhead 0 — a `list`-ness e o tipo já são IMPLÍCITOS. É o alvo de baixo-overhead que os outros tipos deveriam alcançar.
- **number/bool/null** (`.8H` hoje): o `overhead B` é o custo do envelope `#V` + nome-vazio `\z` + coluna de `#count` + `[]` — estrutura que numa coluna única é DEDUTÍVEL. Um single-col tipado (`#TCF.8:n` + body) manteria só `elems B` + ~9 B de header.
- **specs**: a nature JÁ é uma coluna tipada (`#TCF.8 :id`, self-describing) — moldura candidata a unificar com o tipo primitivo.
- **equivalência JSON**: RT do TCF == RT do JSON em TODOS os casos (mesmo objeto Python; tipos preservados) — datasets similares. ✅ é o gate; nunca reportar bytes sem ele.

**14 casos · 0 falhas de equivalência.** Regenera: `python run.py`.

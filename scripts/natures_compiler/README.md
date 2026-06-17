# natures_compiler — DSL textual de filtro → nature executável (gadget)

**F1 do plano** [`filtros-dsl-plano.md`](../../experiments/lab/dirty/notas/filtros-dsl-plano.md).
Gadget auxiliar (`scripts/`, **não toca `src/tcf`**): compila uma **definição textual** de filtro
num spec executável (`TemplatedCheckedSpec`/`TemplatedPaddedSpec` do core), validando
**reversibilidade (round-trip lossless)** no compile-time. A única parte "código" (`check_fn`) vem
de uma **biblioteca fechada nomeada** — zero código do usuário, zero `eval`.

## DSL (flat `chave: valor`, sem dependência de YAML)
```
name: cpf
template: NNN.NNN.NNN-DD     # N/D = dígito; resto = literal
body_length: 9
check_length: 2
check_algorithm: mod11-cpf  # mod11-cpf | mod11-cnpj | none
```
Padded (sem check) usa `padding_slots` + `separator` (ver `examples/ip.dsl`).

## Uso
```bash
cd scripts && python -m natures_compiler natures_compiler/examples/cpf.dsl
# OK: nature 'cpf' compilada e validada (round-trip lossless) de cpf.dsl.
```
```python
from natures_compiler import compile_file
from tcf import encode, decode
spec = compile_file("natures_compiler/examples/cpf.dsl")   # valida round-trip
decode(encode(cpfs, nature=spec), nature=spec)             # usa como qualquer nature
```

## O "compilador" (4 estágios)
PARSE (flat, zero eval) → VALIDATE (campos; nº de dígitos do template == body+check; check_algorithm
na biblioteca fechada; coerência check_length↔algoritmo; capacidade base94; `sum(padding_slots)`) →
BUILD (regex + formatter **auto-gerados do template**; instancia o spec) → **ROUND-TRIP** (64 amostras
sintéticas; `encode→decode==original`; rejeita se falhar).

## Prova (F1)
`tests/test_natures_compiler.py` (9 testes): o spec **compilado do DSL** se comporta **idêntico** ao
spec canônico escrito à mão (`SPEC_CPF`/`SPEC_CNPJ`/`SPEC_IP`) — encode/decode batem em todas as
amostras; `encoded_length` computado bate (5/7). Não é versão de formato (output idêntico).

## Limitação conhecida (achado 2026-06-16)
Cobre só o que os specs atuais suportam: **inteiros canônicos** (sem zero à esquerda) no padded e
**dígitos + mod-11** no checked. **CEP** (zeros à esquerda significativos → vira literal, não comprime)
e **MAC** (hex → não casa o decimal) **NÃO cabem** no `TemplatedPaddedSpec` — exigem um **spec novo**
(padded-fixo preserva-zeros / slots hex) em `src/tcf` → **fase futura** (precisa aprovação + GATE).
A biblioteca de check-fns hoje reusa as do core (`mod11-cpf/cnpj`); novos algoritmos (Luhn etc.)
entram por ticket, nunca inline.

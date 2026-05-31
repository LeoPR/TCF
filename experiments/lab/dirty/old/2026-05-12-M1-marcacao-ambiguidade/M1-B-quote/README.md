# M1.B — Quote em grupo

## Tecnica

Literal com qualquer char ambiguo (digito ou `*`) e' envolto em
aspas simples `'X'`. Custo fixo: +2 bytes por literal ambiguo,
**independente de quantos chars** estao envolvidos.

Dentro de `'X'`:
- `'` interno e' escapado para `\'`
- `\` interno e' escapado para `\\`

Literais SEM ambiguidade ficam raw (sem aspas). `'` no literal
sozinho **nao** dispara aspas — apenas digito ou `*` (o conflito
real e' com refs e separador).

## Custo

- Sem ambiguidade: 0 bytes extra
- Com >=1 char ambiguo: +2 bytes (aspas)
- `'` ou `\` interno em literal com aspas: +1 byte por ocorrencia

Vs M1.A (escape):
- K=1 ambiguo: M1.A +1B vs M1.B +2B (M1.A vence)
- K=2 ambiguos: M1.A +2B vs M1.B +2B (empate)
- K>=3 ambiguos: M1.A +KB vs M1.B +2B (M1.B vence)

## Roundtrip nos 4 datasets

| Dataset | Bytes | Roundtrip | Vs M1.A |
|---|---:|---|---:|
| D1-emails-simples | 162 | OK | empate (sem ambig) |
| D2-emails-quote-id | 198 | OK | **-2 (vs M1.A 200)** |
| D3-stress-substring | 233 | OK | **-9 (vs M1.A 242)** |
| D4-caos-mix | 160 | OK | **+8 (vs M1.A 152)** |

Observacao:
- D1: empate (nenhum literal tem digito → ambas emitem raw)
- D2: M1.B ganha 2B (alguns literais K=2 viram +2B em vez de +K)
- D3: M1.B ganha 9B (literais "users/00", "orders/00", "00042" tem
  varios digitos contiguos → aspas eficiente)
- D4: M1.B perde 8B (literais misturados com varios `'`, `*`,
  digitos isolados — K=1 nesses contextos favorece escape)

## Propriedades para F2

| Eixo | Comportamento |
|---|---|
| Stateful encoder? | nao — decisao local por fragmento (K>=1 → aspas) |
| Stateful decoder? | sim — modo aspas aberto/fechado |
| Latencia incremental | linha por linha |
| Complexidade encoder | 1 regra (K ambiguos → aspas) |
| Complexidade decoder | 2 modos (literal sem aspas, literal com aspas) |
| Lookahead | nao precisa |

## Exemplo (D2 linha 11)

`'o\'connor103'@yahoo7`

- `'o\'connor103'` literal com aspas, conteudo "o'connor103"
  (o `\'` no meio e escape do `'` interno)
- `@yahoo` literal raw
- `7` ref

## Comparacao M1.A vs M1.B em D2 linha 2

```
M1.A: 1,2,3\4\25,6,7      (escape de cada digito)
M1.B: 1,2,3'42'5,6,7      (aspas envolvendo "42")
```

Mesmos 14 chars. Empate.

Em D3 linha 1:
```
M1.A: api*/*users/\0\0*\0\4\2*/profile*.*json   (39 chars)
M1.B: api*/*'users/00''042'/profile*.*json      (36 chars)
```

M1.B vence por 3 chars em uma linha (escape de 5 digitos seguidos
custaria 5 bytes; aspas custam 2 + 2 = 4 mas o '042' tem 4 chars
e os 5 digitos consecutivos do `users/00` mais favoraveis).

## Limitacoes

- `'` no literal sem aspas **funciona** (tratado como char comum
  no modo sem aspas) — `'` so' inicia modo aspas no comeco de
  elemento.
- Mas literal com `'` E digito precisa de aspas externas (por causa
  do digito) + escape do `'` interno = custo total 3 bytes em vez
  de 2. O escape pontual seria mais barato nesse caso edge.
- Aspas pareadas exigem que linha esteja completa para decode (parser
  busca aspa de fechamento).

## Implementacao

Arquivo `syntax.py`. Classe `M1BQuoteSyntax(Syntax)`. Importa
`online.py` (raiz exp 16) e `syntax_base.py` (interface).

Compartilha logica de quebras com M1.A (codigo similar mas
duplicado — cada micro autocontido por princípio).

## Como rodar

```bash
cd 2026-05-12-M1-marcacao-ambiguidade/M1-B-quote
python teste.py
```

Imprime TCFs gerados em D1-D4 com bytes + decode em contra-prova.

# M1.E — Range de refs sequenciais

## Tecnica

Refs consecutivas formando sequencia aritmetica `n, n+1, n+2, ...`
sao agrupadas como `a..b`. Ortogonal a escape/quote: pode combinar
com qualquer sintaxe das outras micros.

Esta implementacao combina range com **escape com escopo** (M1.A')
para a parte de literais.

## Custo

| Caso | M1.A'/B | M1.E |
|---|---|---|
| ref isolada | `5` (1) | `5` (1) |
| K=2 sequencial | `1,2` (3) | `1,2` (3) — nao agrupa |
| K=3 sequencial | `1,2,3` (5) | `1..3` (4) | -1 |
| K=4 sequencial | `1,2,3,4` (7) | `1..4` (4) | -3 |
| K=N sequencial (1 dig) | 2N-1 | 4 | 2N-5 |

Para refs com idx multi-digito, ganho cresce ainda mais.

## Escolha de sintaxe `..` vs `[a-b]`

- `[a-b]` (5 chars overhead) colide com literal `[` em D4 e com
  delimitador de body (`[` abre, `]` fecha).
- `..` (2 chars overhead) sem colisao com brackets, sem necessidade
  de escapar `[`.
- Limiar K menor: `1..3` ja' ganha 1 byte; `[1-3]` empata.

Decoder consome `.` em ref-context apenas se for `..` consecutivo
(lookahead 1). Literais com `.` unico (`.com`, `.json`) seguem
intocados.

## Mistura

`1,2,3,4,8,9` -> runs greedy `[1,2,3,4]` + `[8,9]` -> `1..4,8,9`
`1,5,6,7,8` -> `[1]` + `[5,6,7,8]` -> `1,5..8`

## Roundtrip e bytes nos 4 datasets

| Dataset | M1.A | M1.B | M1.A' | **M1.E** | M1.E ganho vs A' |
|---|---:|---:|---:|---:|---:|
| D1-emails-simples | 162 | 162 | 162 | **149** | -13 (-8.0%) |
| D2-emails-quote-id | 200 | 198 | 197 | **180** | -17 (-8.6%) |
| D3-stress-substring | 242 | 233 | 233 | **206** | -27 (-11.6%) |
| D4-caos-mix | 152 | 160 | 152 | **141** | -11 (-7.2%) |
| **TOTAL** | 756 | 753 | 744 | **676** | **-68 (-9.1%)** |

**Roundtrip 4/4 OK.**

## Exemplos comparativos

### D1 eid=3 (`maria@gmail.com`) — M1.E ganha 4 bytes vs A'

```
M1.A': mari*a3,4,5,6
M1.E : mari*a3..6        (-4)
```

### D3 eid=13 (`api/users/00001/items.html`) — M1.E ganha 5 bytes

```
M1.A': 1,2,3,4,5,6html
M1.E : 1..6html          (-5)
```

### D4 eid=3 (`123@foo.com`) — M1.E ganha 2 bytes

```
M1.A': 1,2,3,4\3
M1.E : 1..4\3            (-2)
```

### D3 linha onde mistura aparece — M1.E lida bem

```
M1.A': 10,2,11,12,13,6,7
M1.E : 10,2,11..13,6,7   (-3)
```

## Propriedades para F2

| Eixo | M1.A | M1.B | M1.A' | M1.E |
|---|---|---|---|---|
| Stateful encoder? | nao | nao | nao | nao |
| Stateful decoder? | nao | sim | sim | sim |
| Parse linear? | sim | nao | quase | quase (lookahead `..`) |
| Lookahead | nao | sim | sim | sim (2 chars: `..`) |
| Bytes (total D1-D4) | 756 | 753 | 744 | **676** |
| Combinavel com outras? | base | base | base | sim (herdou A') |

## Limitacoes

- **Limiar K=3**: K=2 nao agrupa por nao ganhar bytes. OK.
- **Lookahead `..` no decode**: se algum dia literal tiver `..`
  contiguo (raro), ainda funciona porque parser entra em literal-mode
  por dispatch externo (digit dispara ref-mode). Mas dentro de
  ref-mode, `..` em literal pode confundir se o ref-mode greedy
  comesse muito. Para os 4 datasets atuais nao acontece (verificado).
- **Decoder e' stateful** (igual M1.A' e M1.B). Nao perde nem ganha
  vs M1.A'.

## Como rodar

```bash
cd 2026-05-12-M1-marcacao-ambiguidade
python run_lote.py
```

ou inspecionar so' M1.E:

```bash
cat resultados/M1-E-range/<dataset>.tcf
cat resultados/M1-E-range/<dataset>.debug.txt
```

## Implicacao para o macro M1

M1.E ganha em todos os 4 datasets sobre as 3 anteriores. Mas isso
**nao encerra a exploracao semantica** — restam M1.C (sumida) e
M1.D (slice arbitrario) que atacam dimensoes distintas:

- M1.C: parser stateful — omite marcacao quando idx N nao existe na
  tabela atual (economia em casos sem ambiguidade)
- M1.D: extende algoritmo com `TokRefSlice(eid, a, b)` — referencia
  trecho central de string ja' declarada (vai mudar o algoritmo do
  exp 16, nao apenas a sintaxe)

Antes de pular pra F2/F3, vale implementar pelo menos uma versao
minima de C e D para mapear diferencas semanticas.

# Macro M1 — Marcação de ambiguidade textual

## Manifesto

Este é um **macro experimento**: agrupa 4 micro experimentos
(M1.A, M1.B, M1.C, M1.D) que testam técnicas de marcação de
ambiguidade textual numa **base controlada**.

A partir do **exp 16** como raiz dos tokens, descartamos
mentalmente todas as sintaxes (v1-v6) feitas nos exps 21-28.
Cada micro é **reimplementado do zero**, autocontido, sem
reaproveitar código antigo. O objetivo é mapear **diferenças**
entre técnicas em **múltiplas dimensões**, não declarar
"vencedor".

## Princípios

1. **Comparamos diferenças, não vencedores**. Cada técnica pode
   brilhar num eixo e perder em outro.
2. **Múltiplas dimensões**: bytes, gzip, statefulness, latência,
   complexidade.
3. **Datasets sintéticos enviesados**: conclusões valem só no
   regime testado, não generalizam.
4. **Cada micro é autocontido**: 1 pasta, 1 arquivo de sintaxe.
   Não importa de v4-q-fix nem de v6-sumida antigos.

## Estrutura

```
M1/
  online.py                  raiz: tokens do exp 16 (intocado)
  syntax_base.py             interface Syntax (encode + decode)
  data/
    D1-emails-simples.csv    baseline limpo (sem ambiguidade)
    D2-emails-quote-id.csv   ambiguidade pontual (digitos + aspas)
    D3-stress-substring.csv  padrao central grande (testa slice)
    D4-caos-mix.csv          stress maximo (varios chars reservados)
  M1-A-escape/               micro: escape pontual `\X`
  M1-B-quote/                micro: quote em grupo `'X'`
  M1-C-sumida/               micro: parser stateful (omite quando idx
                              nao existe)
  M1-D-slice/                micro: slice arbitrario (extende algoritmo)
  run_lote.py                roda 4 micros x 4 datasets = 16 cenarios
  matriz.md                  matriz consolidada apos F2
  conclusoes_lote.md         fechamento do macro apos F4
```

## Fases

### F1 — Viabilidade

Para cada (M1.X, D_Y):
- Roda? encode + decode + roundtrip OK?
- Cabe em 1 arquivo de sintaxe?
- Tempo de processamento OK?

Saida: tabela 4x4 (OK/FAIL/CAVEAT).

### F2 — Diferenças

Para cada cenario OK em F1, medir 6 dimensoes:

| Dimensao | Como medir |
|---|---|
| Bytes totais | `len(tcf.encode('utf-8'))` |
| Bytes ref+dados | decompose por camadas |
| Bytes apos gzip | `gzip.compress(tcf)` |
| Stateful encoder? | sim/nao + grau |
| Stateful decoder? | sim/nao + grau |
| Latencia incremental | linhas de lookback necessarias |

Saida: matriz 16 cenarios x 6 dimensoes.

### F3 — Substituicao

- Tecnica A engole tecnica B em todos os eixos? -> A vence categoricamente
- Tecnicas complementares (uma vence eixo X, outra eixo Y)? -> mistura possivel
- Tudo insuficiente? -> abre macro alternativo (M2)

Saida: mapa de regimes.

### F4 — Fechamento

Decisao final do macro:
1. Adotar uma como padrao
2. Abrir M2 explorando escolha automatica
3. Encerrar M1 e abrir macro alternativo

## Datasets

| ID | Nome | Conteudo | Por que |
|---|---|---|---|
| D1 | emails-simples | 4 nomes x 3 dominios, sem digitos | baseline limpo, sem ambiguidade |
| D2 | emails-quote-id | nomes com `'` + IDs numericos | ambiguidade pontual (vinda do exp 26) |
| D3 | stress-substring | URLs com path comum + IDs | padrao central grande (vinda do exp 28) |
| D4 | caos-mix | strings com `*`, `'`, `[`, `]`, digitos | stress maximo (vinda do exp 24) |

## Micros

| Codigo | Tecnica | Mecanismo |
|---|---|---|
| M1.A | Escape pontual | `\X` por char ambiguo |
| M1.A' | **Escape com escopo** | `\<digitos>` agrupando sequencia |
| M1.B | Quote em grupo | `'X'` envolvendo bloco com ambiguidades |
| M1.C | Sumida | parser stateful — omite marcacao quando idx N nao existe |
| M1.D | Slice arbitrario | extende o algoritmo com TokRefSlice(eid, a, b) |

## Status atual

- [x] Setup: pasta, raiz, datasets, syntax_base
- [x] M1.A: escape (D1=162, D2=200, D3=242, D4=152, total=756)
- [x] M1.B: quote (D1=162, D2=198, D3=233, D4=160, total=753)
- [x] M1.A': escape com escopo (D1=162, D2=197, D3=233, D4=152, total=744)
- [x] **M1.E: range de refs `a..b` + escape escopo (D1=149, D2=180, D3=206, D4=141, total=676)**
- [x] M1.C: sumida — parser stateful (D1=149, D2=180, D3=206, D4=141, total=676 — **empate com M1.E** nos datasets atuais; ver insight em M1.C/README)
- [ ] M1.D: slice arbitrario — estende algoritmo com TokRefSlice
- [ ] F2 a F4: pendentes

## Limitacoes conhecidas

- Datasets sinteticos enviesados — nao representam producao
- Apenas 4 datasets — coverage limitada
- 4 micros podem nao esgotar o espaco — poderiam ter M1.E hibrida
- Comparacao com gzip e' a unica externa — falta HTFC/FSST

## Compromisso

Nao acelerar para "implementar todos" sem pensar. Cada micro tem
seu README, sua justificativa e suas limitacoes. F4 e' o momento
de fechamento — nao antes.

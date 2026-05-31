# 25 — sintaxes adaptativas (correção do v4-quote + substituição global)

## Princípio / motivação

O exp 24 levantou 2 pontos:

1. **Bug em v4-quote**: dispara aspas por `'` no literal, mas `'`
   não é marcador em v3. Conflito não existe — não deveria
   forçar aspas.

2. **Substituição global**: em vez de escapar char ambíguo, trocar
   o marcador conflitante por outro char não-usado no dado.
   Anuncia substituição no header.

Este experimento testa ambos.

## Sintaxes testadas

| Sintaxe | Origem | Mudança |
|---|---|---|
| compact_v2 | exp 22 | aspas sempre |
| compact_v3 | exp 23 | sem aspas |
| compact_v4_escape | exp 24 | `\X` escape |
| compact_v4_quote | exp 24 | aspas se digit/`*`/`'` (BUG) |
| **compact_v4_quote_fixed** | NOVO | aspas se digit/`*` apenas (`'` é char comum) |
| **compact_v5_adapt_escape** | NOVO | substitui `*` se conflita + escape dígitos |
| **compact_v5_adapt_quote** | NOVO | substitui `*` se conflita + aspas dígitos |

## Resultado observado

| Dataset | v2 | v3 | v4-esc | v4-q | **v4-q-fix** | v5-a-esc | v5-a-q |
|---|---:|---:|---:|---:|---:|---:|---:|
| emails-com-id | 226 | X | 215 | **213** | 214 | 215 | 214 |
| nomes-com-aspas | X | 161 | 161 | **181** | **161** | 161 | 161 |
| codigos-com-arroba | 98 | X | 95 | **92** | 93 | 98 | 97 |
| caos-mix | X | X | **152** | 158 | 160 | 155 | X |

### Bug do v4-quote — corrigido

Em **nomes-com-aspas**, v4-q antigo dava 181 bytes (forçava aspas
por causa de `'` no literal). **v4-q-fix dá 161 bytes** — 20 bytes
economizados. Confirmado: `'` não é marcador, não deveria forçar
aspas.

### Substituição global — não ganhou em nenhum dataset

Surpresa: v5-adapt-* **não venceu** v4 em nenhum dos 4 datasets.

#### Por que substituição não ajudou em codigos-com-arroba

Analisando TCFs:

**v4-esc** (95 bytes):
```
PED*@\2\0\2\6\*\0\0*\1
1,2\2
...
```

**v5-a-esc** (98 bytes, +3):
```
~*+                         ← header (4 bytes com newline)
PED+@\2\0\2\6*\0\0+\1       ← `*` no literal sem escape (−1 byte)
1,2\2                       ← escape dígitos igual
...
```

O `*` no literal aparece em **1 único fragmento** do nó-base
(`@2026*00`). Outras strings reusam por ref, não duplicam o `*`.

Economia: −1 escape (`\*` virou `*`).
Custo: +4 bytes do header.
Líquido: **+3 bytes**. Substituição perdeu.

#### A lógica do break-even

Substituição vale a pena se:

```
N_ocorrências_no_literal − 4 (custo header) > 0
N_ocorrências_no_literal > 4
```

Em **fragmentos** do nó-base, não em string completa. O algoritmo
do online.py emite cada padrão **1 vez** (depois reusa por ref).
Então N_ocorrências_no_literal = N_fragmentos_distintos com o
char ambíguo.

Nos datasets atuais, cada char ambíguo aparece em **1-2
fragmentos** apenas. Substituição **nunca compensa**.

#### Quando substituição valeria a pena

Cenários hipotéticos onde substituição ganha:

- Dataset com `*` em vários nomes únicos diferentes ("p*omar",
  "k*iwi", "a*bacate" etc.) — cada um seria fragmento literal
  separado
- Dataset onde o algoritmo NÃO consegue fatorar (regime B do
  exp 17 — uuids, cpfs)
- Dataset grande onde o overhead do header dilui

Em datasets do regime A (com fatorização forte), o `*` no
literal aparece em poucos fragmentos. Substituição é overhead.

### v4-q-fix vs v4-q antigo em datasets sem `'`

| Dataset | v4-q antigo | v4-q-fix | Δ |
|---|---:|---:|---:|
| emails-com-id | 213 | 214 | +1 |
| codigos-com-arroba | 92 | 93 | +1 |
| caos-mix | 158 | 160 | +2 |

v4-q-fix é **1-2 bytes pior** em datasets onde o bug do v4-q não
era acionado. Causa: a regra mais conservadora de separador
(`*` quando literal anterior não tem aspas, mesmo se atual tem
aspas) emite um `*` extra em algumas transições.

**Justificativa do regulador**: garantir parser sem ambiguidade.
Os 1-2 bytes extras são preço pequeno pela robustez.

## Insight central

**O conflito tem que existir** — você estava certo. Forçar
aspas/escape sem conflito real é desperdício de bytes.

E **substituição global tem ROI mensurável**: vale apenas se o
char substituído aparece em mais que ~4 fragmentos literais
distintos. Em datasets com fatorização forte (regime A), o char
aparece em poucos fragmentos e a substituição perde para
escape ou quote local.

## Limitações

- **4 datasets sintéticos**: não capturam casos onde substituição
  brilharia (alta densidade de char ambíguo em fragmentos
  distintos)
- **v5-adapt-quote falha em caos-mix**: bug residual a debugar.
  Não afeta a conclusão central (substituição não ganha em
  datasets testados)
- **Apenas `*` e `,` como candidatos a substituição**: outros
  marcadores (`^`, `|`, `[`, `]`) só causam ambiguidade em
  posições específicas, resolvidas por contexto

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-25-syntax-adapt
python run.py
```

7 sintaxes × 4 datasets + TCFs lado a lado para inspeção visual.

## Conclusões

Ver [conclusoes.md](conclusoes.md). Pontos principais:

1. **v4-quote-fixed valida sua intuição**: `'` não é marcador em
   v3; forçar aspas é desperdício
2. **Substituição global é overhead em datasets atuais**:
   precisaria de N_ocorrências > 4 para compensar header
3. **Em datasets do regime A**: v4-quote-fixed ou v4-escape são
   as sintaxes adequadas para casos reais (cobrem ambíguos sem
   excesso)
4. **Direção a investigar**: dataset onde substituição realmente
   ganha (alta densidade de char ambíguo em fragmentos distintos)

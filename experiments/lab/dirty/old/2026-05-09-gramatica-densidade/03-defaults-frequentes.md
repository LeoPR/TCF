# Defaults implícitos para padrões frequentes

A hipótese: certos padrões são tão comuns que vale criar shorthand
sintático para eles. O usuário sugeriu:
- `3*+` em vez de `3*+1` (delta +1 por dia, o mais comum)
- `3*-` em vez de `3*-1` (delta -1, simétrico)
- `3*0` já é compacto e único

---

## Análise de frequência (este dataset + intuição)

Deltas observados na coluna `data` (sort cronológico):

| Delta | Ocorrências | % |
|---|---|---|
| +1 | 9 | 31% |
| 0 | 8 | 28% |
| +7 | 3 | 10% |
| +4 | 2 | 7% |
| outros (8 valores únicos) | 7 | 24% |

→ `+1` e `0` somam **59% das transições**. Justifica defaults.

### Em datasets reais (intuição extrapolada)

| Tipo de dado | Delta dominante | Frequência esperada |
|---|---|---|
| Logs de eventos diários | +1 dia | 80%+ |
| Vendas em loja | mix de 0 (mesmo dia) e +1 (dia seguinte) | 60% combinado |
| Telemetria por hora | +1 hora | 90%+ |
| Relatórios mensais | +30 ou +31 | 95%+ na sua granularidade |
| IDs sequenciais | +1 | 99%+ |

→ `+1` é universal em dados ordenados temporalmente. `0` é universal em
dados com agregação por momento.

---

## Proposta de shorthand

| Forma original | Shorthand | Economia |
|---|---|---|
| `+1` (delta +1) | `+` (após `*` ou em contexto delta) | 1 char |
| `-1` (delta -1) | `-` | 1 char |
| `0` (delta zero) | `0` (já mínimo) | — |
| `3*+1` (RLE) | `3*+` | 1 char |
| `3*-1` | `3*-` | 1 char |

### Onde aplicar

`+` e `-` sozinhos só fazem sentido onde delta é esperado:
1. Após `*` de RLE (`3*+`)
2. Em modo inline ANTES de outro token (`+1+++3` = `+1, +1, +1, +3`?
   complicado)

→ Para evitar ambiguidade, restringir shorthand a APÓS `*`. Em modo
inline puro, manter `+1` explícito.

---

## Outras frequências aproveitáveis

### Default de `*` (multiplicador)

Em RLE, `N*X` sempre tem N. Mas N=2 é o mais comum (par adjacente).

Poderia haver shorthand `*X` = `2*X`?

`*+1` = duas ocorrências de delta +1?
`**+1` = duplo? Confuso.

→ Não vale a pena. Salvar 1 char por par RLE = 5-10 B em datasets
inteiros. Custo de complexidade não compensa.

### Default de "delta de 1 unidade"

Para colunas de timestamp por hora: `+1h` é o comum. `+` poderia ser
`+1h`. Mas isso depende do tipo da coluna.

→ A semântica de `+` deve ser **dependente do tipo da coluna**:
- coluna `date`: `+` = `+1d`
- coluna `timestamp`: `+` = `+1s` (segundo) — ou `+1h` se header
  declarar
- coluna numérica genérica: `+` = `+1` (incremento de 1 unidade)

Header pode declarar a unidade implícita:
```
# ext: data=delta:days, ts=delta:hours
```

Sem header, decoder infere pelo formato do absoluto.

### Defaults para dict references

Refs também têm distribuição: idx 1, 2, 3 são mais usados (1ª, 2ª, 3ª
declaração). Refs altas (idx 50+) raramente são as mais frequentes em
datasets bem-comportados.

Mas dict é dependente da ordem de aparição (encoder controla via sort).
Não há "default frequente" universal. Pular.

---

## Trade-off complexidade vs ganho

| Shorthand | Ganho/uso | Complexidade decoder |
|---|---|---|
| `+` = `+1` (após `*`) | 1 B/ocorrência | +2 linhas no parser |
| `-` = `-1` (após `*`) | 1 B/ocorrência | simétrico |
| `*X` = `2*X` | 1 B/par | mais ambíguo |
| `+` em modo inline | 1 B mas ambíguo | risco alto |

→ Adotar só os dois primeiros (`+` e `-` após `*`). Os demais ficam
fora.

---

## Validação no dataset

Coluna `data`, cenário 5 (mesa anterior), com shorthand:

Antes:
```
6*+1
5*0
+1 (×4)
+7 (×3)
+4 (×2)
+9, +13, +15, +2, +8, +5, +10
```

Aplicando shorthand `*+` = `*+1`:
```
6*+        ← era 6*+1, saves 1
5*0        ← já era ótimo
+1 (×4)
+7 (×3)
+4 (×2)
+9, +13, +15, +2, +8, +5, +10
```

Saves: 1 B (apenas no `6*+1` virou `6*+`).

Saves total no cenário 5: 1 B (74 → 73 B).

Trivial neste dataset. Mas em datasets de logs com muitos `N*+1`
seguidos, ganho cresce. Para 100 sequências de `N*+1`, salvaria 100 B.

---

## Decisão

Adicionar shorthand `*+` e `*-` ao formato. **Custo zero** quando não
usado, ganho proporcional em datasets temporais.

Especificação:
- Em RLE de delta, se o valor for `+1`, omitir o `1` → `N*+`
- Idem para `-1` → `N*-`
- Decoder vê `*+` → expande para `*+1`. Idem `*-` → `*-1`.
- Encoder usa shorthand quando aplicável; escreve forma completa caso
  contrário.

Fora desse caso, manter sintaxe explícita.

---

## Hipótese da estabilidade do shorthand

Confirma **H-G3**: deltas `0` e `+1` dominam em dados temporais.
Justifica investimento mínimo em shorthand (1-2 caracteres novos no
parser).

Também confirma princípio mais geral: **densificações justificam-se
quando o padrão alvo aparece com frequência alta**. Se não aparece, o
custo de complexidade do parser não retorna em bytes salvos.

→ Heurística: **densificação só vale quando frequência > 30% dos
tokens da coluna**.

---

## Não densificar (rejeitados)

Lista do que NÃO virou shorthand para fechar a discussão:

- `*X` para `2*X` (par): ganho marginal, ambiguidade alta
- `0+` ou `+0` (delta zero alternativo): `0` já é 1 char
- Refs implícitas por posição: muita complexidade, risco de erro
- Compressão de prefixos comuns na hora (P-elision em runtime): mesa
  separada (P)
- "Delta de delta" (segunda derivada): cobre casos raríssimos,
  dispersa o foco

Mantêm-se como ideias de pesquisa para tickets futuros se padrões
empíricos justificarem.

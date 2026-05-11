# Primeiro absoluto = valor + declaração de formato

A insight do usuário transforma overhead em informação útil. O 1º token
da coluna serve como dois propósitos simultaneamente:

1. **Valor de referência** (baseline para deltas)
2. **Formato implícito** (o decoder lê a estrutura e sabe como
   reconstruir os subsequentes)

---

## Como o decoder infere formato a partir do 1º absoluto

### Reconhecimento por shape

| 1º token | Shape | Formato inferido |
|---|---|---|
| `2026-01-05` | 10 chars, hífens em pos 5 e 8 | data ISO YYYY-MM-DD |
| `2026-01-05 14:30:00` | 19 chars, espaço, dois-pontos | timestamp ISO YYYY-MM-DD HH:MM:SS |
| `2026-01-05T14:30:00` | 19 chars, T separator | ISO 8601 estendido |
| `2026-01-05 14:30:00.123` | 23 chars, ponto + 3 dígitos | timestamp com millis |
| `2026-01-05 14:30:00.123456` | 26 chars | timestamp com micros |
| `14:30:00` | 8 chars, dois-pontos | hora pura (HH:MM:SS) |
| `14:30` | 5 chars | hora HH:MM |
| `2026-01` | 7 chars | YYYY-MM (granularidade mês) |
| `2026` | 4 chars dígitos | ano só |
| `1.0` | decimal | número |

→ Decoder não precisa de header declarando "formato é YYYY-MM-DD HH:MM:SS";
deduz pelo shape.

### Custo amortizado

O 1º token é "longo" (até 26 chars para timestamp com micros), mas é
**único na coluna inteira**. Para N=30 linhas, custo médio = 26/30 ≈ 1
char por linha — desprezível.

Para N=1000, custo médio = 26/1000 ≈ 0.03 char/linha. Praticamente
zero.

→ **Princípio**: dependência linear de bytes em precisão? Não. Custo
de precisão é constante (1 token longo). Os deltas são na escala
necessária, não na precisão máxima.

---

## Vantagens estruturais

### Sem header de formato

Antes (alternativa explícita):
```
# ext: ts=delta:format=YYYY-MM-DD HH:MM:SS.fff:units=ms
ts:
1767608445.123
+1
+1
+1
```

Com primeiro absoluto declarando:
```
ts:
2026-01-05 14:30:45.123
+1ms
+1ms
+1ms
```

O 2º estilo é mais legível e elimina a metadata externa.

### Reset transparente

Se o encoder quiser "resetar" o baseline (ex: gap muito grande), basta
escrever um novo absoluto:

```
ts:
2026-01-05 14:30:00       ← baseline 1
+1m
+1m
2026-06-15 09:00:00       ← novo baseline (gap de 5 meses, mais
                            barato escrever absoluto que +13176000s)
+1m
+1m
```

Decoder vê absoluto → muda baseline. Sem regras especiais — vem
naturalmente do parser.

### Ambiguidade ao misturar precisões?

Pode acontecer: 1ª linha é `2026-01-05 14:30:00` (precisão segundo)
mas em algum ponto aparece `2026-01-05 14:30:00.123` (precisão ms).

Decoder pode:
- Promover precisão para a maior vista (com truncamento implícito do
  resto = .000)
- Rejeitar como erro (encoder deveria ter usado a maior precisão desde
  o início)

→ **Decisão**: encoder normaliza precisão na 1ª passada. Se há valor
com sub-segundo, todos ficam com precisão sub-segundo (zeros padding
nos demais).

---

## Variantes de formato e seus shorthands

### Forma canônica vs forma packed

ISO 8601 canônico: `2026-01-05 14:30:00.123` — 23 chars
Sem hífens/dois-pontos: `20260105143000123` — 17 chars (-6)

A forma packed (Π) ainda funciona para o 1º absoluto. Decoder vê
sequência de 17 dígitos → identifica como timestamp packed.

Trade-off: legibilidade vs bytes.

### Forma reduzida quando precisão menor

Se a coluna inteira é precisão "minuto" (segundos sempre 00, ms ausente):
- Canônico: `2026-01-05 14:30:00`
- Reduzido: `2026-01-05 14:30`

Decoder infere precisão pelo tamanho. 16 chars (com espaço) = precisão
minuto. 19 chars = precisão segundo. 23 = ms. 26 = µs.

Encoder escolhe a forma reduzida se nenhum valor da coluna tem
precisão maior.

### Frações de segundo arbitrárias

Casos comuns: ms (3 dígitos), µs (6), ns (9). Decoder olha a quantidade
de dígitos após o `.`:

| Sufixo | Precisão |
|---|---|
| `.123` | milissegundos (3 dígitos) |
| `.123456` | microssegundos (6 dígitos) |
| `.123456789` | nanossegundos (9 dígitos) |

Fora desses, decoder usa a quantidade exata de dígitos como precisão
fracional.

---

## O que isso resolve da intuição do usuário

> O primeiro absoluto pode servir ao mesmo tempo como formato para ser
> usado na reconstrução, ou seja, ele "gasta" sendo representado grande,
> mas ao mesmo tempo já diz como é o formato.

**Confirma H-T1.** Implementação:
- Encoder escreve 1º absoluto na precisão máxima detectada na coluna
- Decoder lê e infere shape (formato + precisão)
- Deltas subsequentes ficam livres dessa carga — só carregam a
  diferença, não o formato

> Os deltas independem do formato em si, só sabem incrementar.

**Confirma**. A sintaxe `+1ms`, `+1s`, `+1m` etc. é independente do
formato do absoluto. Decoder aplica delta na escala correspondente.

---

## Interação com flag Π (packed)

Π já cobre empacotamento de absolutos. Aqui adiciona-se um caso novo:
**precisão variável**. Encoder pode emitir absoluto **na menor precisão
suficiente** quando ativo Π:

```
# ext: ts=delta+packed
ts:
20260105143000             ← packed sem ms (14 chars)
+1m
+1m
```

Mais compacto que `2026-01-05 14:30:00` (19 chars). Mas perde
legibilidade.

→ Π e formato canônico são opções alternativas; encoder escolhe pela
flag. Default = canônico.

---

## Conclusão da seção

O 1º absoluto carrega o formato implicitamente. Decoder infere precisão
e estrutura sem header dedicado. Deltas operam em qualquer escala
necessária.

Próxima seção (`02-campos-congelados.md`): como aproveitar quando
componentes do timestamp não variam.

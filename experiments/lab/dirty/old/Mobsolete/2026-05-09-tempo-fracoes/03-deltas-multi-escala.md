# Deltas multi-escala

Sintaxe e semântica das deltas para timestamps com múltiplas precisões.

---

## Unidades de delta

Cada unidade de tempo tem seu sufixo:

| Sufixo | Unidade | Equivalência |
|---|---|---|
| `ms` | milissegundo | 1/1000 s |
| `µs` ou `us` | microssegundo | 1/10⁶ s |
| `ns` | nanossegundo | 1/10⁹ s |
| `s` | segundo | (base) |
| `m` | minuto | 60 s |
| `h` | hora | 3600 s |
| `d` | dia | 86400 s |
| `w` | semana | 7 d |
| `mo` | mês | 28-31 d (depende do mês de origem) |
| `y` | ano | 365 ou 366 d |

### Uso da unidade `mo` e `y`

`mo` e `y` são **calendárico-dependentes**: `+1mo` desde `2026-01-31`
pode ser `2026-02-28` (sem 31 em fevereiro) ou outro comportamento.
Decoder precisa decidir convenção:
- ISO 8601: clamp ao último dia do mês destino
- Naive: somar dias de um mês "típico" — gera deriva

→ **Decisão**: `mo` e `y` aceitos com convenção ISO (clamp). Encoder
prefere `+Nd` para distâncias pequenas (até ~90d) e `+Nmo` para
distâncias maiores onde o ganho compensa.

### Uso de `w`

`+1w` = `+7d`. Mesmo número de chars (`+7d` ou `+1w`). Marginal. Pode
ficar como conveniência alias.

---

## Sintaxe formal

```
delta-time ::= '+' digits unit | '-' digits unit | '0'
unit       ::= 'ms' | 'us' | 'µs' | 'ns' | 's' | 'm' | 'h' | 'd' | 'w' | 'mo' | 'y'

shorthand:
'+'  alone after '*' = '+1<inferred-unit>' (most common in column)
'-'  alone after '*' = '-1<inferred-unit>'
```

### Inferência de unidade no shorthand

Encoder declara a "unidade implícita" para shorthand. Pode ser detectada
da unidade mais frequente nas deltas explícitas.

Exemplo: 70% das deltas são `+1m`. Encoder declara unidade implícita = `m`.
`*+` então = `*+1m`.

Sem essa frequência clara, shorthand não se aplica (encoder explicita
sempre).

### Header (opcional)

```
# ext: ts=delta:default-unit=m
```

Ou implícito pela 1ª delta vista (se a 1ª e seguintes 5 são `+1m`,
default = `m`).

---

## Algoritmo do encoder por delta

```
v_prev = valor anterior
v_curr = valor atual
diff_seconds = v_curr - v_prev (em segundos, podendo ser fracionário)

para cada unidade U em ordem decrescente [y, mo, w, d, h, m, s, ms, µs, ns]:
    se diff_seconds é múltiplo inteiro de U.seconds:
        emit "+<n>U" onde n = diff_seconds / U.seconds
        return

# fallback: usar a menor unidade necessária
se há fração de segundo: emit "+<diff>ms" (ou µs ou ns conforme precisão)
senão: emit "+<diff_seconds>s"
```

### Exemplo

| Diff (segundos) | Resultado |
|---|---|
| 1 | `+1s` |
| 60 | `+1m` |
| 300 (= 5 min) | `+5m` |
| 90 | `+90s` (não é múltiplo de m) |
| 3600 | `+1h` |
| 86400 | `+1d` |
| 86430 | `+86430s` (não é múltiplo) |
| 0.001 | `+1ms` |
| 0.5 | `+500ms` |

---

## Combinando com δ + RLE + dict

Já que deltas têm unidade-sufixo, dois deltas iguais em unidades
diferentes não colapsam:
- `+60s` ≠ `+1m` para fins de dict (diferente representação)

Encoder emite a **representação canônica mínima** em cada caso. Se a
unidade canônica for sempre a mesma para um valor (ex: encoder sempre
prefere `+1m` sobre `+60s`), o dict captura.

```
ts:
2026-01-05 14:30:00
6*+1m              ← run de 6 deltas +1m
+5m                ← declara dict idx 1 (= +5m)? ou idx 1 = +1m?
```

Para evitar confusão de idx: dict por coluna inclui as unidades.

```
dict deltas:
  idx 1 = +1m       (criada com 6*+1m)
  idx 2 = +5m       (criada com +5m)
```

Refs operam por idx normalmente.

---

## Reset implícito por novo absoluto

Quando o gap é grande demais, encoder pode preferir escrever um novo
absoluto:

```
ts:
2026-01-05 14:30:00
+1m
+1m
2026-06-15 09:00:00     ← reset; +5mo+10d+18h30m seria muito caro
+1m
```

Critério do encoder:
```
se bytes(absoluto) < bytes(deltas necessárias para chegar):
    emitir absoluto (reset)
```

Para a maioria dos casos, delta vence (mesmo `+161d` é só 5 chars vs
absoluto 19 chars). Reset é raro mas vale ter como opção.

---

## Exemplo completo — log de evento misto

Cenário: timestamps de logs ao longo de algumas horas, com bursts e
gaps.

Dataset:
```
2026-01-05 14:30:00
2026-01-05 14:30:00        (mesmo segundo, possível em logs que não rastreiam ms)
2026-01-05 14:30:01
2026-01-05 14:30:02
2026-01-05 14:30:02
2026-01-05 14:30:15        (gap de ~13 seg)
2026-01-05 14:35:00        (gap de ~5 min)
2026-01-05 15:00:00        (mais 25 min)
2026-01-05 15:00:30
2026-01-05 15:00:30
```

Encoder analisa. Usa precisão segundo (sem ms na coluna). 1º absoluto
inclui segundos.

Encoded:
```
ts:
2026-01-05 14:30:00
0                          (mesmo valor; +0s = 0)
+1s
+1s
0                          (mesmo)
+13s
+5m                        (= +285s mas múltiplo de 60 → +5m)
+25m                       (300s × 5; mais limpo `+25m`)
+30s
0
```

Bytes corpo (10 transições + 1 absoluto):
- "2026-01-05 14:30:00\n" = 20
- "0\n"×3 = 6
- "+1s\n"×2 = 8
- "+13s\n" = 5
- "+5m\n" = 4
- "+25m\n" = 5
- "+30s\n" = 5

Total ≈ 53 B para 10 timestamps. Header `ts:\n` = 4 B. Coluna ≈ 57 B.

Comparação com absoluto literal: 10 × 20 = 200 B. **Delta multi-escala
economiza 71%**.

---

## Validação da intuição

> A hora e frações ficam mais difíceis a cada momento.

**Parcialmente verdade.** Sub-segundo introduz mais valores possíveis
(maior cardinalidade), mas multi-escala compensa: delta `+1ms` em ms é
4 chars, igual `+1m` em minutos. **A complexidade não cresce linearmente
com a precisão**, porque cada escala tem sua delta independente.

> O comportamento de hora, minuto, segundo pode ter algo que possa ser
> capturado assincronamente.

**Confirma H-T3.** Multi-escala é a captura do "assíncrono". Cada
componente muda na sua frequência; encoder emite delta apenas na
escala da mudança.

> Pode ser que os segundos sejam sempre zero apesar de estarem
> ocupados.

**Confirma H-T4.** Algoritmo emite delta na escala maior necessária —
deixa segundos intactos automaticamente quando não mudaram.

---

## Resumo

| Aspecto | Decisão |
|---|---|
| Unidades suportadas | ns, µs, ms, s, m, h, d, w, mo, y |
| Encoder escolhe | maior unidade que ainda é múltipla exata da diff |
| Calendar-dependent (mo, y) | convenção ISO 8601 (clamp ao mês de destino) |
| Default unit no shorthand | unidade mais frequente da coluna |
| Reset para absoluto | quando absoluto é mais curto que deltas até lá |
| Frozen fields | emergente: deltas em escalas maiores não tocam menores |

→ Próxima seção (`04-recomendacao.md`): o que vai para v0.5, o que
defere.

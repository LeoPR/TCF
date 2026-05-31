# Campos congelados (frozen fields)

Caso comum: alguma componente do timestamp **não varia** ao longo da
coluna. Exemplos:
- Métricas a cada 5 minutos: segundos sempre `00`
- Eventos diários (1×/dia): hora, minuto, segundo todos sempre `00:00:00`
- Logs de uma janela de 1 hora: hora sempre a mesma, varia só minuto/seg

Encoder pode detectar e excluir esses campos das deltas.

---

## Detecção (1 passada pela coluna)

```
para cada componente C ∈ {Y, M, D, h, m, s, ms}:
    se todos os valores da coluna têm o mesmo C:
        marcar C como frozen
    senão:
        marcar C como variable
```

Custo: O(N) sobre a coluna, antes de codificar.

---

## Como o encoder usa

### Caso A — frozen embaixo (segundos sempre 00)

Coluna:
```
2026-01-05 14:30:00
2026-01-05 14:35:00
2026-01-05 14:40:00
2026-01-05 14:45:00
```

Detecção: `s = 00 sempre`. Frozen.

Encoded (com δ multi-escala, automaticamente):
```
2026-01-05 14:30:00         ← absoluto inicial (mostra "00" nos seg)
+5m
+5m
+5m
```

Decoder: aplica delta `+5m` ao último valor. Segundos permanecem `00`
porque delta não os toca. Funciona naturalmente.

→ **Frozen "automático"**: não precisa header declarando frozen. O
delta opera só nas escalas necessárias; campos não-tocados ficam.

### Caso B — frozen no topo (mesmo dia, hora varia)

Coluna:
```
2026-01-05 14:30:00
2026-01-05 14:31:00
2026-01-05 14:32:00
```

Encoded:
```
2026-01-05 14:30:00
+1m
+1m
```

Idem caso A. Hora/dia/mês/ano permanecem porque delta `+1m` só altera
minutos (e propaga overflow para hora se necessário).

### Caso C — frozen misto

Coluna:
```
2026-01-05 14:30:00
2026-01-05 14:35:00
2026-01-05 15:00:00     ← mudou de hora
2026-01-05 15:05:00
```

Encoded:
```
2026-01-05 14:30:00
+5m
+25m                     ← +25m de 14:35 = 15:00 (overflow para hora)
+5m
```

Decoder: aplica `+25m` a `14:35:00`, resultado `15:00:00`. Aritmética
sabe propagar.

### Caso D — frozen "real" (não há dado abaixo daquela escala)

Coluna:
```
2026-01-05
2026-01-06
2026-01-07
```

Aqui o "formato" da 1ª linha já é `YYYY-MM-DD` — não tem hora. Frozen
não se aplica; os campos abaixo do dia simplesmente **não existem** no
formato.

Encoded:
```
2026-01-05
+1d
+1d
```

→ Não confundir "frozen" (escala existe mas é constante) com "ausente"
(escala nem aparece no formato). Frozen pede 1ª aparição com a constante;
ausente nem precisa.

---

## Decisão de design — frozen é implícito

O encoder NÃO precisa declarar quais campos são frozen. Sintaxe atual
de delta multi-escala já lida automaticamente:

- Delta `+5m` muda só minutos (e propaga). Segundos ficam.
- Delta `+1d` muda só dia. Hora/min/seg ficam.

O encoder escolhe a escala da delta baseada no que **mudou** entre
valores consecutivos. Se segundos não mudaram, encoder usa delta em
minutos ou maior. Se minutos não mudaram, usa delta em horas.

→ Frozen vira **emergente** da escolha de escala da delta. Sem flag
nova, sem header.

### Algoritmo do encoder

```
para cada par consecutivo (v_i, v_{i+1}):
    diff = v_{i+1} - v_i
    encontrar a maior escala E tal que diff é múltiplo inteiro de E
    emitir delta na escala E
```

Exemplos:
- diff = 1 segundo → `+1s`
- diff = 60 seg = 1 min → `+1m`
- diff = 300 seg = 5 min → `+5m`
- diff = 3600 seg = 1 hora → `+1h`
- diff = 86400 seg = 1 dia → `+1d`
- diff = 90 seg → não múltiplo de minuto, tem que ser `+90s` (ou
  ambíguo: `+1m+30s`?). **Decisão**: usar a unidade mínima necessária,
  `+90s`.

→ Encoder simplifica para `+5m` em vez de `+300s` quando aplicável.
3 chars vs 5 chars. Ganho real.

---

## Interação com sub-segundo

Quando há precisão sub-segundo, a escala mais fina é `ms` (ou `µs`).
Ainda funciona:

```
2026-01-05 14:30:00.000
+1ms
+1ms
+1s                        ← +1 segundo (1000 ms; usar +1s é mais curto)
+1ms
```

Decoder normaliza unidades.

---

## Validação da intuição do usuário

> Pode ser que os segundos sejam sempre zero apesar de estarem
> ocupados, ai a gente pode mostrar ele como zero e ao somar apenas os
> minutos, o zero do segundo permanece.

**Confirma H-T2 e H-T4.** Solução:
- 1º absoluto mostra `:00` nos segundos (visível, ocupando bytes)
- Deltas posteriores não mexem nos segundos (escala maior é mais
  econômica)
- Reconstrução: segundos permanecem `:00` porque ninguém os alterou

Sem header. Sem flag. Comportamento emergente da escolha de escala
ótima nas deltas.

---

## Casos onde frozen falha

### Frozen "intermitente"

Coluna com seg=00 em algumas linhas mas seg=variado em outras:

```
2026-01-05 14:30:00
2026-01-05 14:30:15        ← agora segundo varia
2026-01-05 14:31:00        ← volta a 00
```

Encoder usa `+15s` para a 2ª transição, `+45s` (ou `+0m45s`?) para a
3ª. Granularidade fina perdida. Sem economia de frozen.

### Resolução para reset de precisão

Se a maioria das linhas é frozen mas algumas não, encoder pode optar
por escrever absoluto a cada "quebra de frozen":

```
2026-01-05 14:30:00
+1m
+1m
2026-01-05 14:30:15        ← reset (mais barato que +14m45s? não, +14m45s = 7 chars vs 19)
```

Decisão de reset depende do tamanho da diferença. Para diferenças
pequenas (segundos a minutos), delta vence. Para mudanças "atípicas"
muito grandes, absoluto pode vencer (raro).

→ Encoder rodando ambos e escolhendo o menor.

---

## Resumo

- **Frozen automático**: não há flag `F`. A escolha de escala maior na
  delta naturalmente preserva os campos menores.
- **Algoritmo**: encoder mede o GCD da diff em segundos, escolhe a maior
  unidade que cabe.
- **Visibilidade**: 1ª linha "carrega" o formato com todas as
  precisões. Linhas seguintes só mostram o que mudou (em escala
  econômica).
- **Sem header novo**: tudo emerge da regra de delta multi-escala
  detalhada na próxima seção.

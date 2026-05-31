# Formas de codificar delta

Várias decisões de design para fechar antes de aplicar.

---

## D1 — Sintaxe do delta

Como uma linha indica "delta vs absoluto"?

### Proposta principal: prefixo `+` ou `-`

```
2026-01-05         ← absoluto (sem prefixo, é literal)
+1                 ← delta = +1 (unidade implícita = dia para coluna de datas)
+0                 ← delta = 0 (mesmo valor)
-3                 ← delta negativo (data anterior)
```

Decoder: linha começando com `+`, `-` ou `0` é delta. Senão, absoluto.

### Variante: marcador explícito `δ` ou `~`

```
2026-01-05
~+1
~-3
```

Mais explícito, custa 1 char/linha. **Rejeitada** se não for necessária
para evitar ambiguidade.

### Para nosso caso (datas)

Datas absolutas têm formato `YYYY-MM-DD` — começam com dígito mas têm
hifens, então não colidem com `+1` ou `-1` ou `0`. Sintaxe `+`/`-`/`0`
funciona sem marcador.

→ **Decisão**: usar prefixo `+`/`-`/`0` direto. Sem marcador adicional.

---

## D2 — Unidade do delta

Datas têm várias unidades possíveis: dias, horas, segundos, etc.

### Opções

- `+1` (unidade implícita pelo tipo da coluna)
- `+1d` (sufixo explícito = dias)
- `+86400s` (em segundos)

### Para coluna de datas

Implicit `+1` = `+1 dia` é a convenção mais comum em bancos de dados.
Sufixo `d` é redundante.

→ **Decisão**: `+N` significa `+N dia(s)` para coluna de datas. Sufixo
explícito quando coluna for timestamp (futuro).

---

## D3 — Onde declara o delta

### Opção A: implícito por header

```
# ext: data=delta
data:
2026-01-05
+1
+1
...
```

### Opção B: implícito pelo conteúdo

Decoder vê `+1` na 2ª linha → infere modo delta. Sem header.

### Opção C: misto

Algumas linhas absolutas, outras delta na mesma coluna. Encoder escolhe
por linha o que é mais curto.

```
data:
2026-01-05         ← absoluto
+1                 ← delta (bytes: 3)
+1
2026-03-03         ← absoluto novamente (gap grande, talvez delta seria +43, mais bytes que valor literal? não, +43 é menor que 2026-03-03)
```

Espera, em datas o absoluto sempre tem 10 chars + \n = 11 B; o delta
máximo plausível em dias é 3 chars + sinal + \n = 5 B. **Delta sempre
ganha** vs absoluto.

→ **Decisão**: modo C com encoder escolhendo por linha. Mas para datas,
o encoder vai sempre escolher delta após o 1º absoluto.

---

## D4 — Reset implícito

Quando o delta acumula erro ou quer "ancorar de novo", pode reaparecer
um absoluto. Decoder reset baseline.

```
data:
2026-01-05
+1
+1
+1
2026-06-01         ← reset, novo absoluto
+1
+1
```

Útil em casos onde delta acumulado seria muito grande (`+125` é mais
bytes que `2026-06-01`? Não, `+125` = 5 B vs `2026-06-01` = 11 B. Ainda
ganha.)

→ Reset não é necessário para fins de bytes em datas. Pode ser útil
para **chunked TCF**, onde cada chunk começa com seu próprio absoluto.

---

## D5 — Composição com a regra unificada

Após gerar deltas, aplicar a regra unificada normalmente:
- Deltas iguais e contíguos → RLE: `6*+1`
- Deltas iguais e espalhados → dict implícito: 1ª aparição declara, demais
  são refs

Refs em coluna delta usam dict-bare (refs são bare integers, e literais
delta começam com `+`/`-`/`0` — sem colisão com inteiros bare).

```
data:
2026-01-05
6*+1            ← RLE de 6 deltas +1; declara idx 1 = +1
+4
5*0             ← RLE de 5 zeros; declara idx 2 = 0
+7
1               ← ref a idx 1 (+1) — mais curto que `+1` literal? Empate (2B = 2B)
                  → encoder mantém literal por consistência
2               ← ref a idx 2 (0)
+9
2
1
+13
2
1
+15
+7              ← OU ref para +7? "+7\n"=3B, ref "<idx>\n"=2B → ref ganha
+2
+8
+5
+7              ← idem
+4
+10
```

A regra unificada aplica naturalmente sobre os deltas.

---

## D6 — Onde o decoder reconstitui

Decoder, ao ler:
1. Linha absoluta (sem `+`/`-`/`0` prefix) → guarda como "última data"
2. Linha delta → soma à última data, emite resultado, atualiza última
3. Linha ref → resolve dict, aplica como delta

Estado do decoder: 1 baseline + dict de deltas.

Custo de memória: O(cardinalidade dos deltas), pequeno.

---

## D7 — Compatibilidade com sort

Se a coluna for primária do sort, datas vêm cronológicas → deltas pequenos
e repetitivos. Ótimo.

Se for secundária ou não-sortida, datas vêm fora de ordem → deltas grandes
e/ou negativos. Delta ainda economiza vs absoluto (representação curta),
mas RLE não funciona.

→ **Heurística do encoder**: aplicar delta sempre que for monotônico
(positivo ou zero) na maioria das transições. Caso contrário, manter
absolutos.

Métrica simples: contar transições com `delta ≥ 0`. Se >70%, ativar delta.

---

## Síntese

Sintaxe final adotada:

```
<absoluto>          ex: 2026-01-05
+<n>                delta positivo (n dias para coluna de datas)
-<n>                delta negativo
0                   delta zero (= mesmo valor)
N*<absoluto>        RLE de absoluto literal
N*<delta>           RLE de delta literal
<ref>               ref bare (idx do dict implícito)
N*<ref>             RLE de refs
```

Decoder regras:
- Linha começa com dígito sem hífen-no-meio → ref bare
- Linha começa com `+`, `-` ou apenas `0` → delta
- Linha contém `-` na 5ª e 8ª posição (formato `YYYY-MM-DD`) → absoluto
- Header opcional `# ext: data=delta` força modo

Aplica em `03-aplicado.md`.

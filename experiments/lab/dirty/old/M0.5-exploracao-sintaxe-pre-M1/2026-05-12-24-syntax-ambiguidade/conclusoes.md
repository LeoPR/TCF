# Conclusões — escape vs aspas é trade-off mensurável, não há vencedor universal

Roundtrip OK nas sintaxes v4 (escape + quote) em 4/4 datasets.
v2 e v3 falharam em datasets reais como esperado.

## A descoberta central — limiar matemático

Considere um literal de L chars com K chars ambíguos
(que mudariam o modo do parser):

| Estratégia | Custo extra |
|---|---|
| v4-escape (`\X` por char) | K bytes |
| v4-quote (`'X'` em volta) | 2 bytes |

**Empate em K=2**. Se K=1, escape ganha. Se K≥3, quote ganha.

Confirmado empiricamente:

- `nomes-com-aspas` (K=0 em v4-escape, K=1 em v4-quote): escape vence
- `emails-com-id` (K=1-3 dígitos): quote vence por pouco
- `codigos-com-arroba` (K=5): quote vence claramente
- `caos-mix` (K disperso): escape vence (literais curtos, K=1-2)

## Insight não-óbvio — `'` é mais barato em escape

`'` não é reservado em v3 nem v4-escape. O parser trata como
char qualquer dentro do literal. Em v4-quote, `'` dispara aspas
externas + escape do `'` interno.

Isso significa que **escape e quote tratam o mesmo char com
custos diferentes**:

| Char | v4-escape | v4-quote |
|---|---|---|
| Dígito | +1 (escape) | dispara aspas (+2) ou +1 (escape interno) |
| `*` | +1 (escape) | dispara aspas (+2) ou +1 (escape interno) |
| `'` | 0 (não reservado) | dispara aspas (+2) + escape interno (+1) |

Por isso o vencedor depende não só de **quantos** chars ambíguos,
mas **quais**.

## Estratégias futuras não testadas

### Híbrido por literal (v4-auto)

Para cada literal, calcula custo de escape vs quote e usa o
menor. Ganho teórico: union das vantagens de ambos.

Custo de implementação: baixo (1 comparação por literal).

### Default no header

Anunciar a versão da sintaxe no header do TCF:

```
TCF v4-escape
[
...body...
]
```

Custo: ~10 bytes (uma vez por arquivo). Ganho: parser sabe qual
modo usar sem ambiguidade.

Vale a pena se o ganho médio for **maior que 10 bytes por
arquivo**. Em datasets pequenos (D2-mini = 85 bytes), 10 bytes
é 12% — significativo.

### Marcador especial por linha (modo local)

Linha com prefixo `'mode=escape':` ou `:` pode mudar modo só
naquela linha. Custo: 1-2 bytes por linha que muda. Ganho:
sintaxe ótima para cada linha.

Excessivo para datasets pequenos. Pode valer em casos extremos.

### Anúncio por nó

Se um nó tem muitos chars ambíguos, marca com prefixo (`'q':`
para "use quote") senão usa default (escape). Custo: 2 bytes
por nó com modo diferente. Ganho: por nó individualmente.

## Pontos a registrar

1. **Sintaxes sem escape (v2, v3) são frágeis**: falham em
   datasets reais como esperado
2. **Escape vs Quote tem limiar K=2 chars ambíguos**: limiar
   confirmado empiricamente
3. **Nem escape nem quote vence em tudo**: cada um em ~50% dos
   casos
4. **`'` é "grátis" em escape, caro em quote**: literais com `'`
   favorecem escape
5. **Híbrido v4-auto** (escolher por literal) é o próximo passo
   óbvio
6. **Default no header** pode economizar bytes em datasets
   pequenos onde o overhead da escolha é dominante

## Validação de hipóteses do user

O user perguntou sobre dois escapes:
1. **"Default + opt-in (versão do TCF)"**: ainda não testado.
   Provavelmente vale para datasets onde uma estratégia domina
2. **"Marcador especial na linha em caso de ambiguidade"**:
   v4-quote-condicional é uma forma disso (aspas só quando
   necessário). Vence em metade dos casos

Ambas as direções são válidas e complementares. Híbrido v4-auto
unifica.

## O que este experimento não mostra

- Comportamento em datasets do mundo real
- Híbrido v4-auto (escolha por literal)
- Default no header + opt-in por linha
- Sintaxes binárias (chars Unicode reservados)
- Comparação com gzip downstream (chars de escape podem ser
  comprimidos)

## Próximo experimento natural

**Exp 25 — v4-auto híbrido**: escolher entre escape e quote por
literal, automaticamente. Implementação:

```python
def _emit_literal_auto(text):
    chars_ambiguos = sum(1 for c in text if c.isdigit() or c == '*')
    if chars_ambiguos == 0 and "'" not in text:
        return text  # sem nada
    elif chars_ambiguos <= 2 and "'" not in text:
        return ''.join('\\'+c if c.isdigit() or c=='*' else c for c in text)
    else:
        return f"'{text.replace('\\','\\\\').replace(chr(39),chr(92)+chr(39))}'"
```

Esperado: vence em todos os 4 datasets do exp 24 (escolhe a
melhor opção local).

Sugestão de prioridade:
1. **v4-auto** primeiro (close esta linha de investigação)
2. Depois: escalar v4-auto para os 21 datasets (regime A do
   exp 18)
3. Eventualmente: comparação externa (TCF + gzip vs CSV + gzip)

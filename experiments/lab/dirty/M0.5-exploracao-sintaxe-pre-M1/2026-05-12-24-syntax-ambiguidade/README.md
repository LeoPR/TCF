# 24 — resistência das sintaxes a ambiguidades

## Princípio / motivação

As sintaxes v2 e v3 do exp 22/23 funcionaram em datasets onde
literais NÃO contêm chars que conflitam com a sintaxe. Mas
datasets reais contêm:

- Dígitos (emails com id, urls, IPs, datas, codigos)
- Aspas simples (sobrenomes irlandeses/italianos: `d'angelo`)
- Símbolos especiais (`@`, `*`, `[`, `]`, etc.)

Este experimento testa **duas estratégias de escape** em 4
datasets com gradiente de ambiguidade.

## Propósito

Responder: **qual estratégia de escape é mais eficiente** em
diferentes regimes de densidade de chars ambíguos no literal?

## Comparação

4 sintaxes × 4 datasets:

| Sintaxe | Estratégia |
|---|---|
| compact_v2 | aspas sempre (exp 22) |
| compact_v3 | sem aspas (exp 23) |
| **compact_v4_escape** | NOVO — v3 + `\X` antes de char ambíguo |
| **compact_v4_quote** | NOVO — v3 + aspas condicionais (`'X'` se contém char ambíguo) |

4 datasets com chars ambíguos crescentes:

| Dataset | Chars ambíguos no literal |
|---|---|
| emails-com-id | dígitos (1-3 por literal) |
| nomes-com-aspas | `'` (1 por literal) |
| codigos-com-arroba | `@`, `*`, dígitos (5 por literal) |
| caos-mix | `[`, `]`, `'`, `*`, `@`, dígitos (vários) |

## Resultado observado

### Tabela 1 — bytes por sintaxe (X = falhou)

| Dataset | v2 | v3 | v4-escape | v4-quote |
|---|---:|---:|---:|---:|
| emails-com-id | 226 | **X** | 215 | **213** |
| nomes-com-aspas | **X** | **161** | **161** | 181 |
| codigos-com-arroba | 98 | **X** | 95 | **92** |
| caos-mix | **X** | **X** | **152** | 158 |

### Tabela 2 — qual sintaxe ganhou em cada dataset

| Dataset | Vencedor | Por quê |
|---|---|---|
| emails-com-id | **v4-quote (213)** | literais com vários dígitos contíguos: aspas (+2) < escape (+1 por dígito) |
| nomes-com-aspas | **v3/v4-escape (161)** | `'` não é ambíguo em v3; v4-quote insiste em aspas e perde 20 bytes |
| codigos-com-arroba | **v4-quote (92)** | `@2026*00` tem 5 chars ambíguos: aspas (+2) < escape (+5) |
| caos-mix | **v4-escape (152)** | chars dispersos beneficiam escape granular |

**Conclusão**: nem v4-escape nem v4-quote é universalmente
melhor. Cada um vence em ~50% dos casos.

### Sintaxes que falharam (esperado)

| Sintaxe | Falha em | Causa |
|---|---|---|
| compact_v2 | nomes-com-aspas, caos-mix | `'` no literal quebra o delimitador |
| compact_v3 | emails-com-id, codigos, caos-mix | dígitos, `*`, `[`, `]` no literal |

Confirma que **uma sintaxe sem estratégia de escape é frágil**
em datasets do mundo real.

## Trade-off escape vs aspas — limiar matemático

Considere um literal de `L` chars com `K` chars ambíguos:

- **v4-escape**: custo extra = K (um `\` por char ambíguo)
- **v4-quote**: custo extra = 2 (uma `'` antes, uma depois)

Limiar: **K=2 → empate**. Se K=1, escape ganha. Se K≥3, quote ganha.

Aplicando:

| Dataset | K médio | Esperado | Observado |
|---|---:|---|---|
| emails-com-id | 2-3 | quote ≥ escape | quote vence por pouco |
| nomes-com-aspas | 1 | escape vence | confirmado |
| codigos-com-arroba | 5 | quote vence | confirmado |
| caos-mix | misto | depende | escape vence por dispersão dos chars em literais variados |

### Observação importante: `'` em v3/v4-escape NÃO é ambíguo

`'` não é reservado em v3 nem v4-escape — o parser apenas trata
como char qualquer dentro do literal. Por isso `d'angelo` em
v4-escape tem custo zero. Em v4-quote, `'` força aspas (+2) e
escape do `'` interno (+1) = custo de 3 bytes.

Isso explica por que v4-quote **perde** 20 bytes em
nomes-com-aspas (12 strings × ~1.7 bytes de overhead).

## TCF lado a lado — caos-mix (12 strings, mix completo)

**v4-escape (152 bytes)** — escape granular:
```
[
[a*]\*'*foo*'@\4*\2
1,2,3,4\3
1,2,3,4\4
[b2,3,4,5
...
```

**v4-quote (158 bytes)** — aspas para literais com qualquer ambiguidade:
```
[
[a']*\''foo'\'@4''2'
1,2,3,4'3'
...
```

Em caos-mix, v4-escape ganha porque os literais resultantes do
algoritmo (após quebras) tendem a ser **curtos e contêm 1-2
chars ambíguos**.

## Limitações

- **4 datasets sintéticos**: representam regimes específicos, não
  o universo de datasets reais
- **v4-quote tem regra simplificada**: dispara aspas se literal
  contém **qualquer** dígito/`*`/`'`. Versão mais sofisticada
  poderia decidir por literal individualmente
- **Não testa híbrido** que escolheria escape ou quote
  localmente por literal
- **Não testa estratégia "default no header"** (anunciar
  versão e omitir marcadores)

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-12-24-syntax-ambiguidade
python run.py
```

3 tabelas + status detalhado por sintaxe + caos-mix lado a lado.

## Conclusões

Ver [conclusoes.md](conclusoes.md). Pontos principais:

1. **v2 e v3 são frágeis** — falham na maioria dos datasets reais
2. **v4-escape e v4-quote sempre funcionam** mas trocam ganho
   por outro: escape ganha em literais com 1-2 chars ambíguos,
   quote ganha em literais com 3+ chars ambíguos
3. **Híbrido v4-auto** (escolher escape ou quote por literal
   individualmente) seria o ótimo teórico — próximo experimento
4. **`'` é mais barato em v4-escape** porque não é reservado lá
5. **Limiar de break-even**: K=2 chars ambíguos é onde escape e
   quote empatam

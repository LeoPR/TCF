# Recomendação — o que vai para v0.5, o que defere

---

## Decisões maduras (vão para v0.5)

### 1. Primeiro absoluto = formato declarado implicitamente

- Encoder emite o 1º valor com a precisão máxima detectada na coluna
- Decoder infere shape (data, timestamp, timestamp+ms, etc.) pelo
  comprimento e estrutura do 1º token
- **Sem header de formato** — auto-descritivo

### 2. Frozen fields emergem da escolha de escala

- Não há flag explícita "frozen=s,ms"
- Algoritmo do encoder seleciona a maior unidade que é múltipla exata
  da diff
- Campos não-tocados pela delta permanecem do último valor

### 3. Deltas multi-escala

- Sufixos: `ns`, `µs`, `ms`, `s`, `m`, `h`, `d`, `w`, `mo`, `y`
- Encoder pick finest-fit
- `mo` e `y` usam convenção ISO 8601 (clamp ao mês de destino)
- `+0` e `0` ambos válidos para "mesmo valor"

### 4. Shorthand `*+` e `*-`

- Já decidido em `2026-05-09-gramatica-densidade/`
- Em coluna de timestamp, unidade implícita = unidade mais frequente

### 5. Reset por absoluto quando barato

- Encoder pode emitir novo absoluto se for mais curto que a delta
  acumulada
- Critério: `bytes(absoluto) < bytes(delta_acumulada)`
- Geralmente raro, mas habilitado

---

## Integração com a hierarquia Lxxx

A flag δ existente cobre tudo isso. Sem flag nova. Sub-modos opt-in
via header:

```
# ext: ts=delta                      ← default: multi-escala automática
# ext: ts=delta:default-unit=m       ← shorthand explicit
# ext: ts=delta+packed               ← combinação com Π
```

A regra unificada (RLE+dict) opera **sobre as deltas**, capturando
runs e refs onde aparecem.

---

## Decisões deferidas (precisam de mais pesquisa)

### Hipótese H-T5 (não validada com dataset real)

> Sub-segundo é o caso mais "caro" mas o mais beneficiado por δ
> multi-escala.

Não validada ainda. Precisa dataset com timestamps em precisão variável
(ms + µs + s misturados). Quando aparecer, validar e ajustar a
heurística.

### Convenção `mo`/`y` em casos extremos

Edge cases com `+1mo` desde data como 31 de janeiro: clamp ISO 8601
(28 ou 29 de fev) é uma convenção entre várias. Em datasets contábeis,
"mês fiscal" pode requerer outra convenção. Reservar como ticket
quando aparecer.

### Timezone

A mesa **não** abordou timezone. Cenários reais usam `2026-01-05
14:30:00+02:00` ou `Z`. Adiciona ~6 chars no absoluto, e deltas
precisam considerar conversão.

→ **Defer**: timezone vira ticket separado quando dataset com TZ
aparecer.

### Calendários não-gregorianos

Hijri, hebraico, juliano antigo. Casos raríssimos para o objetivo do
TCF. Defer indefinidamente.

### µs/ns em datasets reais

Telemetria de alta frequência. Útil saber se a sintaxe escala bem para
nano-precisão. Mesa de validação em escala (TPC-H ou similar pode não
ter, precisa dataset específico).

---

## Tickets gerados desta mesa

### S-timestamp-timezone

Quando aparecer dataset com timezone, abrir mesa para:
- Como representar TZ no absoluto (`+02:00`, `Z`, etc.)
- Como deltas se comportam atravessando DST
- Se TZ "frozen" (toda a coluna em UTC) pode ser elidida do header

### S-calendarico-nao-gregoriano

Reservado. Sem urgência.

### S-validacao-multi-precisao

Quando dataset com timestamps de precisão mista chegar, validar:
- H-T5 (sub-segundo é beneficiado)
- Algoritmo de finest-fit funciona em escala ns
- Custo do parser para 10 unidades vs 5 unidades

---

## Atualização do PROGRESSO geral

A mesa adiciona ao PROGRESSO consolidado:

### Decisões maduras (adicionar)

- 1º absoluto carrega formato implícito (sem header de formato)
- Frozen fields emergem da escolha de escala da delta
- Deltas multi-escala com 10 unidades (`ns` a `y`)

### Tickets novos

- S-timestamp-timezone (deferido)
- S-validacao-multi-precisao (deferido)

### Itens que continuam pendentes

(sem mudança):
- Mesa P (prefix elision)
- Mesa L' (line-RLE)
- Mesa K (count-recycling) — ligada a streaming
- Voltar à mesa de transporte
- Protótipo Python
- Validação em escala

---

## Resumo executivo

A mesa fechou tempo/frações sem adicionar nada novo na hierarquia Lxxx
— tudo se encaixou na flag δ que já existia. A complexidade do encoder
sobe ~10 linhas (suporte a 10 unidades de delta + algoritmo finest-fit).
O decoder ganha ~15 linhas (parsing de unidades + aritmética calendárica).

Confirma o princípio das mesas anteriores: **base bem desenhada
absorve casos novos sem renumerar/reformular**. Cada novo padrão
estrutural fecha como sub-modo de uma flag existente, não como flag
nova.

A linguagem do TCF v0.5 segue **estável e composicional**.

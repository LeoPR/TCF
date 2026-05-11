# Limites da regra unificada

Casos onde ela não basta, ou onde a hipótese precisa ser refinada.

---

## Limite 1 — Coluna de inteiros curtos com cardinalidade alta

Cenário: coluna como `quantidade` mas com cardinalidade igual ao tamanho
do dataset (cada qty diferente). Sem dict possível, sem RLE possível.

Regra unificada: cada linha é literal. Equivale a literal puro. Sem ganho
sobre C11.

Não é falha — é o caso degenerado. Mas vale notar que **a regra unificada
não cria valor onde não existe**.

---

## Limite 2 — Marcador caro vs valores curtos

Hipotético: coluna numérica com valores `1`–`9` e cardinalidade 9, com cada
valor aparecendo várias vezes mas em ordem aleatória.

Cada literal: `5\n` = 2 B
Cada ref marcada: `:5\n` = 3 B
Cada literal RLE: `3*5\n` = 4 B
Cada ref RLE: `3*:5\n` = 5 B

→ Ref **sempre perde** para literal nesse caso. A regra unificada decide
corretamente por linha, mas os ganhos são zero. Empata com literal puro.

---

## Limite 3 — Padrões fora de RLE/dict

Tipos de dado que se beneficiam de outros esquemas:

### Timestamps sequenciais

Sequência: `2026-01-01, 2026-01-02, 2026-01-03, 2026-01-04, 2026-01-05`

- Cada valor é único → dict não ajuda.
- Não há runs adjacentes → RLE não ajuda.
- Mas **delta encoding** (diferença) revela: `+1d, +1d, +1d, +1d` que
  comprime trivialmente.

A regra unificada não cobre delta. Para timestamps, precisaria de modo δ
adicional.

### IDs com prefixo comum

Sequência: `INV-001, INV-002, INV-003, ...`

- Único cada → dict não ajuda.
- Sem runs → RLE não ajuda.
- **Prefix elision** (`INV-` extraído como prefixo da coluna): cada linha
  vira `001, 002, 003`. Ganho proporcional ao tamanho do prefixo.

Modo P para prefix elision não está coberto pela regra unificada.

### Float com precisão variável

Sequência: `1.50, 1.500, 1.5, 1.5000`

São o mesmo número mas strings diferentes. Dict trata como 4 valores
distintos. Não economiza.

Solução: normalização pré-encoder (canonicalização). Fora do escopo do
formato.

---

## Limite 4 — Linhas duplicadas exatas

Se o dataset tem **linhas inteiras idênticas** (mesmo nome, produto, qty,
valor), a regra unificada coluna-a-coluna captura cada coluna mas não
captura "esta linha inteira é igual à anterior".

Hipotético: 3 linhas idênticas `Ana, Caneta, 10, 1.50`.

Coluna nome: 1 declaração + 2 refs (ou 2*ref) = 4-6 B
Coluna produto: idem
Coluna qty: idem (literal por colisão)
Coluna valor: idem

Total ~16-20 B para 3 linhas duplicadas.

Versus encoding "linha-RLE":
```
3*(Ana, Caneta, 10, 1.50)
```

Sintaticamente exótico — sairia do estilo column-major. Mas para datasets
de logs/eventos com muitas duplicatas, pode valer modo dedicado.

→ Reservar como **L'** (linha-RLE) — extensão futura.

---

## Limite 5 — Stream sem total conhecido

A regra unificada constrói o dict implícito em 1 passada. Funciona perfeito
em batch. Em **stream**, o encoder não sabe se um valor vai reaparecer.

Cenários:
- Streaming sem visão completa: encoder emite literal mesmo quando seria
  ref. Tradeoff aceitável.
- Encoder com janela móvel: declara dict só dentro da janela; se valor
  reaparecer fora, retransmite literal. Funciona mas perde alguma compressão.

Para stream verdadeiro, talvez precise de modo "dict reciclável" (C12 da
mesa de dict implícito) onde valores antigos saem do dict para abrir
espaço.

---

## Limite 6 — Decoder que precisa pular linhas

Se o cliente quer ler só uma linha específica (ex: linha 17), a regra
unificada **força leitura sequencial** porque o estado do dict depende das
linhas anteriores.

C11-híbrido com encoding=literal não tem esse problema (cada linha é
auto-contida).

Para acesso aleatório dentro de uma coluna, regra unificada perde para
literal. Mas isso é o trade clássico de qualquer compressão — a regra
unificada não é pior que dict-based em geral.

→ Mitigação: chunks com dict local. Cada chunk é auto-contido com seu
próprio dict. Acesso aleatório fica em granularidade de chunk.

---

## O que a regra unificada cobre bem

| Situação | Resultado |
|---|---|
| Coluna primária do sort | RLE puro emergente, ótimo |
| Coluna com fragmentação simples | Ganha 1-N B vs RLE puro |
| Coluna com repetição espalhada | Iguala dict-bare |
| Coluna sem repetição | Iguala literal |
| Coluna com mix RLE + refs | Captura **ambos** (vantagem real) |

## O que ela NÃO cobre

| Situação | Solução fora da regra |
|---|---|
| Sequenciais (timestamps, IDs) | modo δ (delta) |
| Prefixos comuns | modo P (prefix elision) |
| Linhas duplicadas exatas | modo L' (linha-RLE) |
| Streaming sem total | dict reciclável (C12) |
| Acesso aleatório | chunks com dict local |

---

## Pergunta aberta

A regra unificada é uma **boa fundação**, mas o conjunto completo de
modos que o TCF v0.5+ deveria ter inclui pelo menos:
- Regra unificada (RLE+dict por linha) — base
- Modo δ — para sequenciais
- Modo P — para prefixos
- Modo L' — para linhas duplicadas

Discutir em ticket: **regra unificada como default, modos especiais
selecionáveis por header opcional para casos onde valem.**

```
# encoding-base: unified-v05
# col timestamps mode=delta
# col invoice_id mode=prefix
```

Isso preserva a elegância da regra única (default) e abre espaço para
otimizações específicas (opt-in).

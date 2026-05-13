# Fase 1 — Desenho manual do TCF adaptativo (TPC-H)

**Data:** 2026-05-07
**Objetivo:** validar se as primitivas de formato propostas em PLANO-formato-adaptativo.md
são suficientes para um caso real, antes de escrever qualquer motor.

---

## Esclarecimento conceitual prévio

`grouped_by` no TCF **não é** GROUP BY do SQL.

| Conceito | Sentido no SQL | Sentido no TCF |
|---|---|---|
| `GROUP BY x` | Agregar (sum, count, etc.) por valor de x | Posicionar valores de x contiguamente no arquivo |
| Resultado | Uma linha por grupo, com agregações | Mesmas linhas, mas reordenadas para que iguais fiquem juntos |
| Por quê | Calcular respostas | (a) habilitar RLE; (b) habilitar entrega prioritária por grupo |

No nível L0 (sem RLE), `grouped_by` é equivalente a `ordered_by`:
não há ganho de compressão, só de **ordem de entrega**. O efeito físico é o mesmo
(linhas reorganizadas), mas o motivo é outro.

Possível bônus futuro (registro para ticket separado): se o decoder, ao
descomprimir, **mantiver** os valores agrupados, ele entrega ao cliente uma
estrutura quase pronta para um GROUP BY real — economizando passe extra. Mas
isso é decisão do encode/decode, não do formato de arquivo.

→ Decisão para Fase 1: usar `grouped_by` no header (consistência com lab anterior
de categóricos). L0 e L2+ usam o mesmo nome; o efeito é diferente.

---

## Dataset de exemplo (mini TPC-H)

3 clientes, 6 ordens, 7 lineitems. Tamanho propositadamente pequeno para caber
no documento e ser comparável byte a byte.

```
customers (derivado, totais agregados):
  C001  515.50
  C002  359.99
  C003  1500.00

orders:
  1  C001  150.00   2026-01-05
  2  C001  320.50   2026-02-10
  3  C002  89.99    2026-01-15
  4  C003  1500.00  2026-03-01
  5  C001  45.00    2026-04-20
  6  C002  270.00   2026-03-15

lineitem:
  1  P10  2   75.00
  1  P22  1   75.00
  2  P15  5   320.50
  3  P10  1   89.99
  4  P30  10  1500.00
  5  P22  1   45.00
  6  P10  3   270.00
```

**Cenário de uso:** UI quer mostrar "total gasto por cliente" o mais rápido
possível. Detalhes (ordens + itens) podem chegar depois.

---

## V1 — Baseline monolítico (TCF atual, L2)

```
# TCF v0.4 lv=2
## orders n=6 grouped_by=o_custkey
o_orderkey:
1
2
5
3
6
4
o_custkey:
3*C001
2*C002
C003
o_totalprice:
150.00
320.50
45.00
89.99
270.00
1500.00
o_orderdate:
2026-01-05
2026-02-10
2026-04-20
2026-01-15
2026-03-15
2026-03-01
## lineitem n=7 grouped_by=l_orderkey
l_orderkey:
2*1
2
3
4
5
6
l_partkey:
P10
P22
P15
P10
P30
P22
P10
l_quantity:
2
1
5
1
10
1
3
l_extendedprice:
75.00
75.00
320.50
89.99
1500.00
45.00
270.00
```

**Bytes:** ~520 (contagem aproximada; o que importa é a comparação relativa).

**Problema:** receptor precisa de tudo antes de poder calcular o total por cliente.

---

## V2 — Adaptativo, prioridade + agrupamento por cliente

```
# TCF v0.4 lv=2
# MANIFEST chunks=4 grouped_by=o_custkey delivery=priority
# TIER 1 cols=o_custkey,total_spent answer=true
# TIER 2 cols=o_orderkey,o_orderdate,o_totalprice,l_partkey,l_quantity,l_extendedprice answer=false

@chunk 0/4 tier=1 self_contained=true n=3
## summary
o_custkey:
C001
C002
C003
total_spent:
515.50
359.99
1500.00
@end

@chunk 1/4 tier=2 group=C001 self_contained=true n_orders=3 n_items=4
## orders
o_orderkey:
1
2
5
o_orderdate:
2026-01-05
2026-02-10
2026-04-20
o_totalprice:
150.00
320.50
45.00
## lineitem
l_orderkey:
2*1
2
5
l_partkey:
P10
P22
P15
P22
l_quantity:
2
1
5
1
l_extendedprice:
75.00
75.00
320.50
45.00
@group_complete o_custkey=C001
@end

@chunk 2/4 tier=2 group=C002 self_contained=true n_orders=2 n_items=2
## orders
o_orderkey:
3
6
o_orderdate:
2026-01-15
2026-03-15
o_totalprice:
89.99
270.00
## lineitem
l_orderkey:
3
6
l_partkey:
P10
P10
l_quantity:
1
3
l_extendedprice:
89.99
270.00
@group_complete o_custkey=C002
@end

@chunk 3/4 tier=2 group=C003 self_contained=true n_orders=1 n_items=1
## orders
o_orderkey:
4
o_orderdate:
2026-03-01
o_totalprice:
1500.00
## lineitem
l_orderkey:
4
l_partkey:
P30
l_quantity:
10
l_extendedprice:
1500.00
@group_complete o_custkey=C003
@end
```

**Bytes:** ~720 (+38% vs V1).

**Ganho:** após receber o chunk 0 (~50 bytes), o cliente já pode renderizar todos
os totais. T_first é uma fração do T_total.

**Custos:**
- +38% bytes (overhead de manifest + chunks + group_complete)
- RLE perde efeito (`3*C001` desaparece — cada chunk tem só um cliente)
- Soma `total_spent` foi pré-calculada (custo no servidor — não é "free")

---

## V3 — Mesmo desenho em L0 (sem RLE, para destacar a semântica)

```
# TCF v0.4 lv=0
# MANIFEST chunks=4 ordered_by=o_custkey delivery=priority
# TIER 1 cols=o_custkey,total_spent answer=true
# TIER 2 cols=o_orderkey,o_orderdate,o_totalprice,l_partkey,l_quantity,l_extendedprice answer=false
...
```

A única mudança: `grouped_by` → `ordered_by` no manifest. O conteúdo dos chunks é
idêntico em forma (o RLE só sumiria nos casos onde havia `N*valor`).

**Decisão proposta para o formato:** o header sempre usa `grouped_by` para ambos
os casos (consistência com lab de categóricos). A diferença é interna: encoder L0
trata como ordering; encoder L2+ trata como grouping para RLE. Cliente que lê o
header não precisa se importar — o efeito de entrega é o mesmo (linhas
fisicamente contíguas por valor da coluna).

→ Tiquete pendente: avaliar se essa unificação de termo é elegante ou confusa.
Reservar para ciclo seguinte.

---

## Observações sobre as primitivas (validação)

### O que funcionou
1. **MANIFEST como header explícito** — declara prioridade e modo num bloco fácil de
   ler para humano e LLM. O server burro só precisa entender `@chunk` e `@end`.
2. **TIER com `answer=true`** — sinaliza qual chunk libera resposta cedo. Sem isso,
   o cliente não saberia quando emitir resposta parcial.
3. **`group=<value>` no @chunk** — combina com `grouped_by` do manifest para deixar
   claro que cada chunk de tier-2 contém os dados de UM grupo.
4. **`@group_complete`** — funciona melhor que esperado. Tira a ambiguidade de
   "esse chunk tem todos os dados desse grupo, ou tem mais chegando?". Crucial
   para H7 (server burro).
5. **Multi-tabela dentro do chunk** — `## orders` + `## lineitem` no mesmo chunk
   funciona naturalmente. O grupo (cliente) é a chave; tabelas são detalhes do
   grupo.

### O que ficou estranho
1. **`n=` no @chunk com múltiplas tabelas** — usei `n_orders=3 n_items=4` ad-hoc.
   Convenção atual é só `n=<rows>` para uma tabela. Decisão: cada `## tabela` tem
   seu próprio `n=` interno; o `n=` do @chunk fica fora ou some.
2. **Tier-1 não respeita `grouped_by`** — o chunk 0 lista os 3 clientes e seus
   totais. Não há agrupamento interno (cada cliente aparece uma vez). O manifest
   diz `grouped_by=o_custkey` mas isso só faz sentido para tier-2.
   → Possível solução: `grouped_by` no chunk, não no manifest. Cada chunk declara
   sua própria semântica de organização.
3. **Custo de pré-cálculo do total_spent** — não é o TCF que paga, mas o Planner
   precisa decidir se vale a pena. Fora do escopo do formato, mas precisa
   aparecer em algum lugar do plano.
4. **RLE perdido entre chunks** — `3*C001` que existia em V1 some em V2 porque
   chunks são self-contained. Confirma o que estava escrito em M-chunks-v04:
   "RLE não cruza chunks". Trade-off explícito: 1-5% de overhead vs paralelismo.
5. **Repetição de `o_custkey` no manifest** — aparece em `grouped_by=` e no `## summary`
   do tier-1. Não é redundância destrutiva, mas dá pra ser mais conciso.

### O que parece faltar
1. **Schema/types declarado por tier** — V2 não diz que `total_spent` é float.
   Hoje o decoder infere. Se houver mistura de tipos entre tiers, pode dar
   ambiguidade. → Reaproveitar `# TYPES` (já em H-compression-v04-roadmap).
2. **Hash/checksum por chunk** — para H2 (retransmissão eficiente em redes com
   perda). Sem isso, não há como o transportador saber qual chunk corromper.
   → Adicionar `crc=<hex>` opcional no `@chunk`.
3. **Hint de ordem entre chunks de mesmo tier** — chunks 1, 2, 3 podem chegar em
   qualquer ordem (são paralelos), mas é útil dizer ao cliente "C001 vem antes
   de C002 na ordenação canônica" para alguns UIs. → `seq=<n>` opcional?
4. **Tamanho declarado do chunk em bytes** — útil para o server burro saber
   onde termina sem parsear. → `bytes=<n>` no `@chunk`. Decisão: opcional;
   server inteligente parseia, server burro pode usar isso para fast-skip.

---

## Métricas estimadas (a confirmar com encoder real)

| Versão | Bytes (~) | T_first (relativo) | T_total (relativo) | RLE eficaz? |
|--------|-----------|--------------------|--------------------|-------------|
| V1 (mono L2)   | 520 | 1.0× | 1.0× | sim |
| V2 (adapt L2)  | 720 | 0.10× | 1.05× | parcial |
| V3 (adapt L0)  | 800 | 0.10× | 1.10× | não |

Onde `T_first` é o tempo até o cliente ter o total dos 3 clientes na tela.
V2 paga 38% mais bytes mas entrega resposta inicial 10× mais rápido.
A pergunta-chave (H6): em datasets reais, em qual ponto esse trade vale a pena?

---

## Decisões a levar para o próximo ciclo

1. **`grouped_by` unificado** (L0 = ordering, L2+ = grouping)? Provisoriamente sim.
2. **`grouped_by` no manifest ou no chunk?** Provisoriamente: chunk (mais flexível).
3. **`n=` como behavior por tabela, não por chunk** quando há multi-tabela.
4. **`crc=`, `bytes=`, `seq=` no `@chunk`** — opcionais, ativados conforme cenário.
5. **Pré-agregações (como `total_spent`) são responsabilidade do Planner**, não do
   formato. O formato só precisa carregar o resultado em tier-1.
6. **Não revisitar dedução implícita ainda** — manter explícito até o formato
   estabilizar; otimizar verbosidade depois (próprio user pediu).

---

## Próximo ciclo (Fase 1 cont.)

Antes de partir para Fase 2 (motores), revisitar este desenho com:
- caso de cardinalidade alta (1000 clientes, 10000 ordens) — como ficam os chunks?
- caso de "resposta dinâmica" (cliente pede top-10, não totais — Planner precisa
  saber qual coluna ordenar para que tier-1 já vem ordenado por valor)
- caso de chunks chegando fora de ordem (cliente recebe chunk 2 antes de chunk 1
  — o `@group_complete` ainda funciona?)
- caso onde tier-1 NÃO está pronto antes de tier-2 começar (servidor demora pra
  agregar) — manifest precisa lidar com chunks "atrasados"?

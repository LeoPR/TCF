# Marcadores redundantes e agrupamento — visão consolidada

Data: 2026-05-12
Origem: observação do user durante M1.A/M1.B, conectando ideias
que ja discutimos em momentos separados.

## A intuição central

> "o algoritmo já comprime muito, então nossa luta está mais em
> representar isso de forma barata do que comprimir de fato"
> "marcadores podem ser redundantes em explicações"
> "se forem sequenciais, dá pra deduzir a sequencia substituindo
> por um marcador que explique a sequencia"

A análise critica em `analise_critica_M1A_M1B.md` confirma:
**31-100% dos fragmentos sao raw**. A sintaxe disputa apenas os
0-60% restantes. O algoritmo do exp 16 ja faz o trabalho pesado.

A direcao que sobra: **agrupar marcadores que aparecem em
sequencia**, substituindo-os por marcacao mais economica.

## Conexao com o que ja discutimos

### Nota `range-de-indices.md` (anterior)

Discutimos: refs em sequencia `1,2,3,4,5` (9 chars) podem virar
range `[1-5]` (5 chars) quando idx sao contiguos. Ganho:
proporcional a K-2.

**E isso e um caso especifico** do principio mais geral que
voce esta articulando agora.

### Etapa 4 do flow semantico (exp 27)

Quando propus o flow em 5 etapas no exp 27:

> "Etapa 4 — agrupamento: marcar segmento maior cobrindo grupo
> (em vez de escape pontual em cada char)"

**Tambem e a mesma ideia.**

### M1.A' (escape com escopo) — proximo passo

A variante que voce aprovou:

> "M1.A' — `\` antes da sequencia sinaliza 'tudo ate proximo `*`
> e literal'"

**Tambem e agrupamento**: marcador unico cobre N chars de
literal ambiguo, em vez de N marcadores individuais.

## Generalizacao — principio do agrupamento

| Tipo de marcador redundante | Forma agrupada | Onde aplica |
|---|---|---|
| `\X\Y\Z` (3 escapes por char) | `\XYZ*` (1 escape escopo) | M1.A' |
| `1,2,3,4,5` (refs contiguos) | `[1-5]` ou `1..5` (range) | nota range |
| `'X''Y''Z'` (literais em sequencia) | `'X*Y*Z'` (sep interno) | flow E4 |
| `*X*Y*Z` (separadores entre literais raw) | um marcador de "lista de literais" | nao explorado |
| `,,,` virgulas adjacentes (refs vazias?) | nao ocorre por construcao | n/a |

**Cada caso e uma instancia do mesmo principio**: marcadores
adjacentes do mesmo tipo podem ser fundidos.

## Inventario de redundancias visiveis nos TCFs atuais

Inspecao dos outputs em `tokens_dump/`:

### Em M1.A — sequencias de escape

**D2 eid=11** (M1.A): `o'connor\1\0\3*@yahoo7`
- `\1\0\3` = 3 escapes contiguos cobrindo "103"
- Forma agrupada (M1.A'): `o'connor\103*@yahoo7` (-2 bytes)

**D3 eid=1** (M1.A): `api*/*users/\0\0*\0\4\2*/profile*.*json`
- `\0\0` = 2 escapes ("00")
- `\0\4\2` = 3 escapes ("042")
- Forma agrupada: `api*/*users/\00*\042*/profile*.*json` (-3 bytes)

### Em M1.B — aspas adjacentes

**D3 eid=1** (M1.B): `api*/*'users/00''042'/profile*.*json`
- `'users/00''042'` — duas aspas adjacentes (fim de uma + inicio da outra)
- Forma agrupada: `'users/00*042'` (-2 bytes, com separador interno)

### Em refs — sequencias contiguas

**D1 eid=3** (ambas): `pedr2,3,4,5,6`
- `2,3,4,5,6` = 5 idx contiguos (9 chars)
- Forma agrupada (range): `pedr[2-6]` (-3 bytes)

**D3 eid=4** (ambas): `web2,3,4,5,6,7`
- `2,3,4,5,6,7` = 6 contiguos (11 chars)
- Forma agrupada: `web[2-7]` (-5 bytes)

### Em estrutura — `*` separadores entre literais raw

**D1 eid=1** (ambas): `joa*o*@*g*mail*.com`
- 5 separadores `*` entre 6 fragmentos
- Difícil agrupar — cada fragmento tem idx proprio

Hmm, **este caso e' interessante**: o algoritmo fragmentou s1 em
6 pedacos pequenos por causa de quebras propagadas. Os
fragmentos sao `joa`, `o`, `@`, `g`, `mail`, `.com` — 5
separadores entre eles.

Se nenhum desses fragmentos for referenciado individualmente,
faria sentido agrupa-los? Sim — em uma string indivisivel. Mas
o exp 16 ja gera assim por necessidade de refs futuras.

**Observacao**: o agrupamento de separadores `*` deve ser
explorado **olhando para a real necessidade** de cada idx. Se
fragmentos pequenos como `o` e `@` so' sao referenciados em
combinacao com vizinhos, talvez nao precisem de idx
individual. Volta a ideia de **slice arbitrario** (M1.D).

## O que isto sugere para M1.A'

A implementacao de M1.A' (escape com escopo) e' o **primeiro
caso testavel** do principio de agrupamento. Se funcionar bem,
podemos pensar em:

1. **M1.A''** — agrupamento por classes (escape escopo + range
   de refs)
2. **M1.X — "agrupamento universal"** — uma sintaxe minimalista
   que aplique TODOS os agrupamentos vistos como uteis

Mas isto e' para apos M1.A'. Antes precisamos ver se a
implementacao de M1.A' confirma a teoria.

## Limites teoricos da abordagem

Por que **agrupamento** tem ROI maior que **substituicao**:

| Abordagem | Custo | Ganho |
|---|---|---|
| Substituicao global (exp 25) | header (3-4B) + parsing | poucos chars/ocorrencia |
| Agrupamento (este principio) | 0 (sintaxe propria, sem header) | 1 byte por adjacencia |

Agrupamento nao paga header. Ganho cumulativo conforme
adjacencias aparecem.

**Estimativa em D3** (dataset com mais adjacencias):
- M1.A: 242 bytes → M1.A' espera ~233-237 (3-9B economia)
- M1.B: 233 bytes → versao com aspas-agrupadas pode chegar a
  ~225-228 (mesma ordem)

Diferenca de ~5-10B em datasets ambiguos. Pequeno mas consistente.

## Pontos a registrar

1. **Agrupamento e' principio unificador** — abrange escape
   escopo, ranges de refs, aspas-de-grupo-com-separador.

2. **Discutimos antes** mas dispersos. Esta nota consolida.

3. **O algoritmo do exp 16 nao precisa mudar** — agrupamento
   e' camada de sintaxe. Compativel com qualquer micro do M1.

4. **M1.A' e' o primeiro teste pratico** do principio. Se vencer,
   abre caminho para variantes.

5. **A "luta" e' representacao economica do exp 16**, nao
   compressao adicional. Esta nota e a `analise_critica_M1A_M1B.md`
   convergem nessa leitura.

## Acoes

Imediato:
- Implementar M1.A' (proximo)
- Comparar com M1.A e M1.B em D1-D4

Depois:
- Se M1.A' vence: pensar em M1.A'' (escape escopo + ranges)
- Se empata: trade-off complementar fica claro
- Se perde: agrupamento de escapes especificamente nao paga

Apos M1.A': F2 do macro com 3 micros (A, A', B). M1.C e M1.D
podem ficar de fora se M1.A'/B forem suficientes.

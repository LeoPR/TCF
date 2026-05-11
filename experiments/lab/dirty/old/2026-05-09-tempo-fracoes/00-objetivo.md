# Mesa — tempo/horas/frações

Refinamento de δ para colunas de timestamp/hora/precisão variável.
Datas (dia) já foram cobertas em `../2026-05-09-delta-datas/`. Agora o
escopo cresce: hora, minuto, segundo, milissegundo, e suas combinações.

---

## A intuição do usuário (registrada)

> A hora e frações ficam mais difíceis a cada momento. O comportamento
> de hora, minuto, segundo pode ter algo que possa ser capturado
> assincronamente. Por exemplo, pode ser que os segundos sejam sempre
> zero apesar de estarem ocupados — a gente pode mostrar ele como zero
> e ao somar apenas os minutos, o zero do segundo permanece.
>
> O primeiro absoluto pode servir ao mesmo tempo como FORMATO para
> reconstrução. Ele "gasta" sendo representado grande, mas ao mesmo
> tempo já diz como é o formato. Os deltas independem do formato em si,
> só sabem incrementar.

Duas observações com implicação direta no formato:

1. **Campos congelados** (frozen fields): se uma componente do timestamp
   nunca varia, o encoder não precisa representá-la nas linhas
   subsequentes — só a 1ª aparição já a "carrega".
2. **Primeiro absoluto declara o formato**: a parsing do 1º token
   estabelece a "forma" (precisão, presença de cada campo), e os deltas
   subsequentes operam sobre essa estrutura sem repeti-la.

---

## Por que tempo é mais difícil que data

Datas são uniformes: todas as transições são em "dias". Delta é um
inteiro escalar.

Timestamps têm múltiplas escalas hierárquicas:
- Y (ano) — raramente muda em dataset de curto período
- M (mês) — raro
- D (dia) — todo dia em dataset diário
- h (hora) — várias por dia
- m (minuto) — muitas por hora
- s (segundo) — muitas por minuto
- ms (millis) — muitas por segundo

Cada escala muda em frequência diferente. Um delta "+86400s" e "+1d"
têm o mesmo significado mas tamanhos diferentes na representação.

→ Multi-escala vira eixo importante.

---

## Padrões empíricos comuns em timestamps

| Cenário | Comportamento típico | Implicação |
|---|---|---|
| Logs de servidor | sub-segundo (ms ou µs), bursts | δ em ms/µs domina, +1ms muito comum |
| Vendas com timestamp | minuto ou segundo, gaps grandes | δ em min/s, gaps em h/d |
| Eventos diários (1×/dia) | só a data muda | seg/min/hora frozen, δ em dias |
| Métricas a cada 5 min | min muda em passos de 5, seg sempre 00 | seg frozen, δ em min |
| Telemetria horária | hora muda, min/seg sempre 00 | min/seg frozen, δ em h |
| Histórico mensal | M, D, h, m, s todos podem ser frozen | δ em mês ou ano |

→ Frozen fields varia por dataset. Detecção automática pelo encoder é
prática.

---

## Plano da mesa

| Arquivo | Conteúdo |
|---|---|
| `01-formato-via-primeiro-absoluto.md` | Primeiro absoluto = valor + declaração de formato |
| `02-campos-congelados.md` | Detecção e exclusão de campos constantes |
| `03-deltas-multi-escala.md` | Sintaxe `+1s`, `+1m`, `+1h`, `+1d`, `+1mo`, `+1y`, `+1ms` |
| `04-recomendacao.md` | O que vai para v0.5, o que defere |

---

## Hipóteses prévias

| ID | Hipótese | Predição |
|---|---|---|
| H-T1 | Primeiro absoluto serve como format declaration; decoder infere precisão e campos do tamanho/forma do 1º token | confirma; elimina header de formato |
| H-T2 | Encoder detecta campos congelados em uma passada; ganho proporcional ao número de campos congelados × N linhas | confirma para datasets uniformes |
| H-T3 | Delta multi-escala (`+1s`, `+1m`, etc.) é mais compacto que delta sempre na unidade mínima | confirma; encoder picks finest-fit |
| H-T4 | Hierarquia natural (Y > M > D > h > m > s > ms): mudança em escala maior reseta menores ou exige novo absoluto | depende — testar |
| H-T5 | Sub-segundo é o caso mais "caro" (ms varia muito) mas também o mais beneficiado por δ multi-escala | confirma; deltas em ms ficam curtos |

A mesa testa cada uma e fecha a especificação.

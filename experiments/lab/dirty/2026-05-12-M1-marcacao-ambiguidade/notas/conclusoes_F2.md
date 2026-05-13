# Conclusoes F2 — Multiplas dimensoes mudam o vencedor

F2 mede 6+ dimensoes alem de bytes literais. Resultado: **nao ha
vencedor unico**, ha frente de Pareto.

## Totais por dimensao

| Dimensao | Vencedor | Total | Diferenca para 2o |
|---|---|---|---|
| Bytes UTF-8 | M1.E ou M1.C | 676 | -10.6% vs M1.A (756) |
| Bytes pos-gzip | **M1.C** | **508** | -0.2% vs M1.E (509), -1.5% vs M1.A (516) |
| Bytes pos-bz2 | **M1.C** | **562** | -1.2% vs M1.E (569), -1.4% vs M1.B (571) |
| Tempo encode | **M1.D** | **273us** | **-65% vs M1.A (786us), -73% vs M1.C (1149us)** |
| Tempo decode | **M1.D** | **332us** | -12% vs M1.A (379us) |

## Inversoes notaveis (vencedor por dataset)

| dataset | UTF-8 | gzip | bz2 | tempo enc | tempo dec |
|---|---|---|---|---|---|
| D1 | M1.E | **M1.A** (!) | M1.E/C | M1.D | M1.C |
| D2 | M1.E | M1.E/C | M1.C | M1.D | M1.D |
| D3 | M1.E | M1.C | M1.C | M1.D | M1.D |
| D4 | M1.E/C/D | **M1.A** (!) | M1.A | M1.D | M1.A |

**Em D1 e D4, M1.A (a mais "ingenua") VENCE em gzip.**

## Hipotese explicativa: M1.A tem mais redundancia textual

Razao gzip (gzip/utf8) — quanto menor, mais comprimivel:

| dataset | M1.A | M1.E |
|---|---|---|
| D1 | **0.691** | 0.758 |
| D2 | 0.760 | 0.822 |
| D3 | **0.612** | 0.689 |
| D4 | 0.684 | 0.752 |

M1.A e' consistentemente MAIS COMPRESSIVEL por gzip (~6-10 pontos
% a mais). Razao: M1.A tem refs verbosas que se repetem ("\1",
"\103" varias vezes; lista `,3,11,5,6` repetida em multiplas
linhas). M1.E ja' comprimiu essas listas em range — restou pouca
redundancia textual para gzip aproveitar.

Conclusao: **agrupamento sintatico interno (M1.E) compete com gzip
externo**. Em datasets com muita redundancia entre linhas, M1.A
ingenuo + gzip pode bater M1.E + gzip.

## M1.D — perdedor em bytes, vencedor em tempo

M1.D perde em todas as dimensoes de bytes:
- UTF-8: +52 bytes vs M1.E
- gzip: +35 bytes vs M1.E
- bz2: +24 bytes vs M1.E

Mas DOMINA em tempo encode:
- M1.D: 273us (total D1-D4)
- M1.A: 786us (2.9x mais lento)
- M1.E: 1022us (3.7x mais lento)
- M1.C: 1149us (4.2x mais lento)

**Razao algoritmica**: M1.D nao precisa chamar `_coletar_quebras`
(que e' O(n*m) sobre nos x quebras propagadas). Apenas itera tokens
raw do exp 16. **Outras 5 sintaxes pagam custo de fragmentar
literais ancestrais** mesmo quando descendentes nem reusam todos
os frags.

Implicacao: **se latencia importa mais que bytes**, M1.D ganha. Em
contexto de transmissao com gzip, M1.D fica ~7% maior — mas roda
3x mais rapido.

## Pareto frontier no macro M1

Nenhuma sintaxe domina em todas as dimensoes. Frente de Pareto:

1. **M1.A**: vence gzip em D1/D4 (refs verbosas comprimem bem); decoder mais simples; sem state
2. **M1.E/C**: vencem em UTF-8; vencem ou empatam em gzip nos D2/D3
3. **M1.D**: vence em tempo enc/dec; perde em bytes

Cada uma tem regime de vitoria.

## Statefulness vs simplicidade

| Sintaxe | Enc state | Dec state | Total complexity |
|---|---|---|---|
| M1.A | nao | nao | mais simples |
| M1.A' | nao | sim (escopo) | media |
| M1.B | nao | sim (aspas) | media |
| M1.E | nao | sim (range) | media |
| M1.C | **sim** | **sim** (max_idx) | mais complexa |
| M1.D | nao | sim (eids completos em mem) | media |

**M1.A e' a unica sem ANY state**. Tem valor de simplicidade.
**M1.C e' a unica com state no ENCODER** — implementacao mais
delicada e bug-prone (vimos isso em M1.C: fix necessario do
separador).

## Implicacoes para a fase F3 (substituicao) e F4 (fechamento)

F3 deve avaliar **substituicao por eixo**, nao por bytes:

- Para minimizar bytes UTF-8 → M1.E ou M1.C
- Para minimizar bytes transmitidos (com gzip) → M1.A em datasets com
  muita redundancia entre linhas; M1.C em outros
- Para minimizar latencia → M1.D
- Para minimizar complexidade de implementacao → M1.A

**Nenhuma "engole" todas as outras.** F3 portanto resulta em mapa
de regimes, nao em vencedor unico.

F4 (fechamento) pode:
- (a) Adotar M1.E como padrao (vence em UTF-8 nos canonicos, segundo
  lugar em gzip)
- (b) Adotar M1.A como padrao (vence em gzip nos extremos, mais
  simples, sem state)
- (c) Hibrido: M1.E nos formatos textuais visiveis; M1.A no transit
  + gzip
- (d) Abrir M2 explorando ALGORITMO modificado (slice central
  REAL, range adversarial, etc.)

## Achado metodologico importante

A escolha de **medir apenas bytes literais** teria escondido:
- Que M1.A pode ser melhor pra transmissao comprimida
- Que M1.D e' 3x mais rapido
- Que M1.C compete com M1.E em gzip mas perde em encode time

**Vale o esforco de medir 6 dimensoes em F2 — ranking muda
drasticamente.**

## Decisao apos F2

1. **M1 NAO se fecha em "M1.E vence"**. Vence em UMA dimensao.
2. Apresentar Pareto frontier ao user.
3. Decisao de F4 fica para o user definir prioridade
   (bytes literais? transit? latencia? simplicidade?).
4. Datasets canonicos D1-D4 mantidos. F2 nao requer novos datasets.

## Limitacoes

- Tempos medidos em Python puro com `time.perf_counter`. Em prod
  com C/Rust, ordem seria a mesma mas magnitudes diferentes.
- Apenas 4 datasets canonicos pequenos. Nao extrapola para datasets
  com 10k+ linhas (latencia incremental nao testada).
- gzip nivel 9 (maxima compressao). Niveis menores poderiam
  reordenar.
- Razao gzip e' afetada por header gzip (~20 bytes fixos) — em
  datasets maiores essa fracao diminui.

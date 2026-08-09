# Resultado — o alvo DELTA: os dois designs são COMPLEMENTARES, não concorrentes

**2026-08-09 · dirty · `n=600` (+ escala 6000), RT conferido em todos os casos
(D2 em dois níveis: coluna pelo decoder REAL + valor pelo `decode_value` REAL)**

Pergunta do lab: o teto de 5,8–6,8× que a triagem achou (H6+H2) se realiza melhor como
**transform de coluna** (D1, protocolo) ou como **seq-RLE periódico** (D2, gramática —
ideia do owner, anterior a esta rodada)? Resposta: **cada um ganha onde o outro não
alcança**; sob FLOOR, os dois juntos cobrem tudo o que apareceu.

## O placar (bytes; D1 já paga +12 B e D2 +10 B de header hipotético)

| caso | C0 sem spec | C1 com spec | D1 delta-col | D2 período | vence |
|---|---:|---:|---:|---:|---|
| diario-controle | 414 | 32 | 35 | 32 | empate C1/D2 (byte-igual) |
| semanal-controle | 2744 | 32 | 35 | 32 | empate C1/D2 |
| **uteis** | 2471 | 1590 | 239 | **41** | **D2 (39× vs hoje)** |
| uteis-feriado-mensal | 2878 | 1889 | **345** | 649 | D1 |
| mensal-dia1 | 1085 | 1085 | **349** | 664 | D1 |
| quinzenal | 7628 | 3951 | **349** | 600 | D1 |
| espalhado-ordenado | 6398 | 4059 | **644** | 3766 | D1 |
| espalhado-desordenado | 6104 | 4737 | **3167** | 4212 | D1 |
| uteis-ruido-1pct | 2710 | 1644 | 350 | 209 | D2 (184 na forma-lista) |
| uteis-ruido-5pct | 3016 | 3016 | **353** | 764 | D1 |
| **ids-turno (NÃO-data)** | 1959 | — | 241 | **33** | **D2 (59×, sem nature)** |
| **uteis-n6000** | 26595 | 15630 | 2040 | **42** | **D2 (O(1) em n)** |

Tabela completa com a coluna D2L (forma-lista) em [`outputs/medicoes.md`](outputs/medicoes.md).

## O que cada um é, no fundo

**D2 (periódico) paga UMA vez; todo o resto paga por valor.** O wire inteiro dos 600
dias úteis é `*600~1,3,1,1,1|739617` — e com n=6000 ele cresce 1 byte (o contador).
O D1 nos mesmos dados roteia pro bN (`#TCF.8B2258`, domínio `{739617,1,3}`) e paga
2 bits por valor pra sempre: 239 B → 2040 B. Cadência EXATA é assunto de gramática.

**D1 (delta-coluna) é robusto porque COMPÕE com o core inteiro.** A coluna de deltas
cai no `encode()` real e o core escolhe a rota: alfabeto pequeno → bN (mensal
`{28,29,30,31}` = 349 B), irregular → raw. Feriado no meio vira UM símbolo a mais no
alfabeto (`4`), não uma quebra — por isso ruído quase não o move (345–353 B em todas as
variações de ruído). O D2 quebra o run a cada perturbação: 30 runs no feriado-mensal
(649 B), 15 no ruído-5% (764 B).

**Regra que resume o quadro:** delta **exatamente cíclico** → D2 (ordens de grandeza);
delta **de alfabeto pequeno ou irregular** → D1 (2–11× vs hoje); os dois sob `min()`,
nunca-pior — os controles uniformes ficaram byte-idênticos ao wire de hoje.

## Achados de design (o que o weld precisa saber)

1. **A forma degenerada é o D1 disfarçado — e perde dele.** Com 1 ciclo só o marcador
   "periódico" vira LISTA literal de deltas (`*25~d1,...,d24|`). Medido: a lista faz
   1825 B no espalhado onde o D1 faz 644 — o marcador paga ~3 chars/delta, o bN paga
   2–5 bits. **A forma-lista não merece gramática**; ela só venceu no ruído-1% (184 vs
   209) por margem pequena. Exigir **≥2 ciclos completos** no detector.
2. **Greedy mistura mal as duas formas.** Com a forma-lista permitida, o greedy prefere
   listas grandes que DESTROEM runs periódicos melhores (feriado-mensal: 904 na forma
   livre vs 649 na estrita). Mais um motivo pra só soldar o estrito.
3. ~~**A rota do candidato digit-heavy é o raw `#TCF.8!!`** — o periódico soldado precisa
   de um espelho raw.~~ **ERRADO, corrigido em `design_probe.py` (mesmo dia).** O `!!`
   não é rota raw: é o **sufixo de POLARIDADE** (weld 2026-07-26), camada de borda
   aplicada depois de tudo (`encoder.py:459`). O corpo que o `compact_body` enxerga ainda
   tem os escapes (`*3+1|7\3` pré-polaridade vira `*3+1|7!3` pós) — logo `compare_for_seq`
   e `shift_escape_digits` **servem como estão**, sem espelho novo. Eu media o wire
   emitido em vez do ponto de decisão; de fora, o mundo parece raw. Mesma classe da
   "âncora de pin" do EXP-016 e do baseline do FLOOR da nature. **Isso barateia o design
   do periódico** — ver [`design_probe.py`](design_probe.py) e a
   [nota de design](../../notas/2026-08/2026-08-09-designs-do-alvo-delta-custo-e-recomendacao.md).
4. **Sintaxe em aberto**: a vírgula já é do multi-delta per-run (ADR-0016) e `~` real é
   operador composicional — o `*N~...|` daqui é PROVISÓRIO. Multi-run × periódico
   (produto cruzado com ADR-0016) fica registrado como não-explorado.
5. **O D1 pressupõe o `T-NATURE-CANDIDATO-BN`** (H1 da triagem, aguarda aprovação): os
   239–644 B do D1 só existem se o caminho da nature consultar o bN — foi medido aqui
   com `encode()` completo, que consulta.
6. **Zfill/largura no modo raw**: o shift preserva largura com zfill (espelha o core);
   ordinais não têm zero à esquerda, mas o weld precisa fixar a semântica.

## Miúdos

- `mensal-dia1` mostra por que o spec recusa hoje: o candidato ordinal (3266 B) perde do
  ISO (1085 B) — os deltas 28–31 quebram o `*N+d|` em pares. Com período, o candidato
  cai pra 664; com delta-coluna, pra 349. Os dois INVERTEM a decisão do FLOOR.
- `espalhado-desordenado`: mesmo sem ordem, o D1 ganha 33% do spec (3167 vs 4737) só
  porque delta com sinal é mais curto que ordinal — sem mecanismo novo.
- O protótipo D2 re-compacta uniforme por conta própria e ficou ~0,2% menor que o corpo
  do core em um caso (artefato de `<=` no custo do par); irrelevante pro placar.

## Sonda de design (`design_probe.py`, mesmo dia)

Depois da correção do §3 acima, o periódico foi posto **onde ele moraria** — dentro do
`compact_body`, via subclasse + monkeypatch de `tcf.encoder/decoder.HCCSeqRLE` (`src/tcf`
intocado no disco, `encode`/`decode` REAIS). Resultado:

- ganho sobrevive ao pipeline inteiro: úteis **1590 → 40 B**, n=6000 → **41 B** (381×),
  ids não-data **1959 → 32 B** (61×);
- **D1-D9 = 1545 B e real-world = 89430 B, byte-idênticos** aos congelados;
- decoder de HOJE diante do wire novo: **fail-loud** (E3), nunca calado;
- valores adversariais que imitam o marcador fazem RT (E1).

E pegou **dois defeitos de design**: padrão uniforme disfarçado (`*600~1,1|`, piorava o
diário 32→34) e FLOOR comparando com o corpo cru em vez do compactado (piorava 4 de 8) —
os dois com guarda de uma linha cada. Detalhe e custo comparado dos dois designs na
[nota de design](../../notas/2026-08/2026-08-09-designs-do-alvo-delta-custo-e-recomendacao.md).

## Próximo passo

1. **Decisão do owner**: a nota de design recomenda **começar pelo periódico** — um
   arquivo, sem dependência de outro weld, vale pra qualquer coluna numérica, e os dois
   gates não se mexeram. O delta-coluna (protocolo) fica para depois, e continua
   complementar.
2. Se o delta-coluna for adiante, o `T-NATURE-CANDIDATO-BN` (weld pequeno, aguarda
   aprovação) é pré-requisito de fato.
3. Depois: **lab clean em massa** da família data (molde EXP-016), consolidando spec +
   alvo(s) delta.

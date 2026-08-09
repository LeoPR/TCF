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

## O custo de CPU — o número que mais mudou (`custo_cpu.py`, `detector_v2/v3/v4.py`)

O ADR marcava "custo a medir". Medido, a resposta inicial foi **ruim**: o detector ingênuo
é **O(n²)** e custava **13,8 s** em `n=2400` contra 47 ms do encode. Três consertos:

| detector | n=600 | n=1200 | n=2400 |
|---|---:|---:|---:|
| v1 ingênuo (`O(n²)`) | 756 ms | 3 269 ms | **13 838 ms** |
| v2 fronteira de cadeia 1× | 27 | 60 | 127 |
| v3 + saída curta | 25 | 52 | 101 |
| **v4 + salto de padrão uniforme** | **18** | **35** | **71** |
| encode sem a camada | 10,5 | 25,5 | 52 |
| | +71% | +38% | **+35%** |

Todas as versões dão **bytes idênticos** e mantêm os dois gates — o que muda é só o
desperdício. As duas primeiras armadilhas eram algorítmicas (refatiar a cadeia por
índice); a terceira só apareceu **instrumentando por dentro da camada**: minha medição
isolada dizia 1,6 ms, a real dizia 19,5 ms, porque eu reconstruía o corpo sem o hint de
cadência e o corpo real tem **uma cadeia única de 1199 deltas**. O guard de padrão
uniforme rodava por (posição × período): ~27 600 fatias para concluir "pule".

**Lição de método (a segunda hoje, mesma família):** medir o mecanismo fora do lugar onde
ele roda dá número errado — primeiro foi o `!!` (li o wire emitido, não o ponto de
decisão), agora foi o custo (reconstruí o corpo, não usei o real).

Do que sobra, a maior fatia é o array de deltas que o `detect_seq_runs` já computa (6,8 ms
contra 1,6 ms da lógica de período) — **compartilhá-lo é parte do weld**.

## A caçada adversarial — o que ela mudou no design

Cinco lentes independentes atacaram o protótipo (12 achados brutos em
[`outputs/cacada-achados-brutos.json`](outputs/cacada-achados-brutos.json), **5 distintos**
após dedup). A [`detector_v5.py`](detector_v5.py) fecha todos; a
[`v5_verificacao.py`](v5_verificacao.py) testa cada um — **8/8**.

| # | defeito | como fechou |
|---|---|---|
| 1 | teto de memória não cobria `*N~…\|`: bomba de 16 B virava 21 s | expand **dentro** do core → 0,03 ms |
| 2 | detector `O(n²)`: n=2400 levava **13,8 s** | fronteira de cadeia 1× + `mudanca[]` → **+30–32%** |
| 3 | FLOOR invertia o desempate — reescrevia wire de dado **sem** periodicidade | ordem `min(hoje, cru, cand)` |
| 4 | telemetria `seq_rle_runs` **zerava calada**: 1 → 0 em wire byte-idêntico ao do core | info do candidato **vencedor**, `start_line` reancorado |
| 5 | pad com cauda morta: `*3~1,4,9\|` == `*3~1,4\|` (não-injetivo) | período mínimo + guard de re-emissão |

**O #4 é o mais instrutivo**: não era lacuna do mecanismo novo, era **regressão** de um
canal público que os próprios labs consomem (`encoder.py:726` → `schema.py:192` →
`sideouts_quality.py`). Nenhum teste pegava — `test_side_outputs.py:58` só afirma
`isinstance(..., list)`. Um mecanismo novo pode quebrar telemetria antiga sem quebrar
nenhum byte.

**O #5 rendeu uma regra além do caso.** Consertar a injetividade expôs a pergunta melhor:
o decode aceitava grafias que o encode **nunca emitiria** (menos de 2 ciclos). É a mesma
assimetria do `DataIsoSpec` — `fromisoformat` aceita `20191204`, `isoformat` nunca emite,
e por isso o spec tem o guard `d.isoformat() != v`. Aqui: `count-1 >= 2·len(pad)`. Mesma
cura, e agora com dois casos ela vira regra.

### Uma correção minha no caminho

Rotulei `*7~1,3,1,3,1|` como grafia ambígua — **não é**: seu período mínimo é 5, então ela
*é* a forma canônica daquele dado. O caso de teste estava errado, não o código. O que a
investigação achou de verdade foi o problema de re-emissão acima, que é melhor.

## Próximo passo

1. **O periódico está pronto para weld** — [ADR-0040](../../../../../docs/adr/0040-seq-rle-periodico.md)
   proposto, código em [`weld_proposto.py`](weld_proposto.py), referência rodando em
   [`detector_v5.py`](detector_v5.py). Falta só o **"pode soldar"**: `src/tcf` exige
   aprovação explícita.
2. O delta-coluna (protocolo) fica para depois e continua **complementar** — ganha onde o
   ciclo não é exato. Se for adiante, o `T-NATURE-CANDIDATO-BN` é pré-requisito de fato.
3. Depois dos dois: **lab clean em massa** da família data (molde EXP-016), consolidando
   spec + alvo(s) delta.

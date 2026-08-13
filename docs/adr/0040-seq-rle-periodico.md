# ADR-0040 — seq-RLE periódico: o delta que CICLA entre linhas

- **Status**: **aceito** (weld 2026-08-09, suíte 1238 passed)
- **Escopo**: corpo de coluna (`compact_body` / `expand_seq_marker` em
  `src/tcf/composicional/hcc_seqrle.py`). Vale para **qualquer coluna numérica**, em
  todas as rotas que passam pelo corpo (flat, `.8M`, spec).
- **Interage com**: ADR-0011 (seq-RLE canônico), ADR-0016 (multi-delta per-run),
  ADR-0024 (baselines re-pináveis), ADR-0035 (polaridade), ADR-0036 (bN)
- **Origem**: ideia do owner, anterior à rodada de data (*"tinha pensado nisso antes mas
  não tive oportunidade de testar completamente"*), confirmada como candidata na triagem
  [`0024`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0024-data-hipoteses-restantes/result.md)
  e medida no lab [`0042`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/result.md)

## Contexto

O seq-RLE de hoje come **delta uniforme entre linhas** (`*N+d|`). Duas cadências muito
comuns não são uniformes:

| regime | delta entre linhas | hoje |
|---|---|---|
| dias úteis | `1,3,1,1,1` repetindo | quebra a cada 5 linhas |
| ids por turno / lote | `10,10,10,50` | quebra a cada 4 |
| quinzenal, mensal | `14,17,14,16…` | quebra a cada 2 |

Não é caso de nicho: **dias úteis é o calendário de negócio**. Uma coluna de 600 dias
úteis custa **1590 B** com o spec de data; a mesma coluna diária custa 32 B.

O `*N+d1,d2,…|` do ADR-0016 **não** resolve isto — ele é per-**run** dentro da *mesma*
linha (prefixo invariante + sufixo cadenciado, tipo IP), não per-**linha**.

## Decisão

Marcador novo: **`*N~d1,…,dp|template`** — linha `k+1` = linha `k` deslocada por
`d[k mod p]`.

```
600 dias úteis, coluna inteira:     *600~1,3,1,1,1|\739617
```

**O ciclo paga UMA vez.** É a propriedade que separa este mecanismo de todos os outros
candidatos: com `n = 6000` o wire cresce **um byte** (o contador), enquanto qualquer
alternativa por-valor cresce com `n`.

### O caractere `~` é escolha reversível, não estrutura

Os marcadores do TCF são abstratos por dentro; o caractere é a *saída*. `~` já é operador
composicional em outro contexto, e a vírgula já é do ADR-0016 — não houve colisão em
teste (§Evidência), e **se colidir, troca-se antes do 1.0** (decisão do owner, 2026-08-09;
ADR-0024 já torna baselines re-pináveis).

### Escopo do primeiro weld: um run de escape-digit por linha

Pares com **mais de um** run (o território do ADR-0016) ficam de fora. Periódico ×
multi-run é produto cruzado das duas gramáticas e não tem caso medido que o justifique.
Registrado, não feito.

### Canonicidade da grafia — duas condições, medidas

Uma caçada adversarial (5 lentes, 12 achados brutos em
[`cacada-achados-brutos.json`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/outputs/cacada-achados-brutos.json))
mostrou que o marcador ingênuo é **não-injetivo**: `*3~1,4,9|` decodifica idêntico a
`*3~1,4|` — o `9` nunca é lido. Infinitas grafias válidas para o mesmo dado, o oposto do
byte-canonical que o projeto usa como gate.

O decode só aceita a grafia que é **canônica** *e* **emissível**:

| condição | rejeita | por quê |
|---|---|---|
| `len(pad) == período_mínimo(seq)` | `*5~1,4,9\|` (cauda morta) · `*5~1,4,1,4\|` (repetição) · `*5~1,4,1\|` (extensão parcial) · `*600~1,1\|` (uniforme) | **injetividade**: uma grafia por dado |
| `count - 1 >= 2 · len(pad)` | `*4~1,3\|` · `*7~1,3,1,3,1\|` | **re-emissão**: o detector exige 2 ciclos completos, logo o decode não pode aceitar o que o encode nunca produz |

A segunda é o **mesmo guard do `DataIsoSpec`** (`d.isoformat() != v`, que recusa
`20191204` porque `fromisoformat` aceita mais do que `isoformat` emite). Mesma
assimetria, mesma cura — e por isso a regra, não o caso.

> `período_mínimo` cobre a "guarda 1" (pad uniforme) de graça: mínimo `1` ⇒ é `*N+d|`.

## As duas guardas — sem elas o mecanismo REGRIDE

Medidas no `design_probe.py`; sem cada uma, o placar piora:

1. **Padrão uniforme disfarçado.** `*600~1,1|` é `*600+1|` escrito com mais bytes. Sem
   rejeitar `len(set(pad)) == 1`, o diário piorava **32 → 34 B**.
2. **FLOOR contra o baseline que o encoder emitiria.** Comparar o candidato periódico com
   o corpo **cru** o fazia "vencer" e piorar **4 de 8** casos (ruído alta-cardinalidade
   203 → 253 B) — ele ganhava do cru e perdia do compactado. O FLOOR é
   `min(cru, compactado_de_hoje, periódico)`.

> A guarda 2 é a **terceira ocorrência** da mesma classe neste projeto — comparar com um
> baseline que o encoder não emitiria (antes: `T-BN-TIPADO`, e o FLOOR da nature em
> 2026-08-08). Vale como regra, não como caso.

**Desempate**: o critério de hoje prefere o **compactado** no empate
(`compactado if len(compactado) <= len(body_text)`). O `min()` do Python devolve o
*primeiro* mínimo, então a ordem dos candidatos é load-bearing para byte-canonicidade —
o weld deve preservar a preferência atual em empates.

## Onde o mecanismo mora — e por que o lugar importa

**Estender `expand_seq_marker`, deixando o laço de `decode` intocado.** Não é preferência
de estilo: é o que preserva o teto de memória.

O laço de `HCCSeqRLE.decode` pré-checa o contador **antes** de materializar
(`_contador_declarado`, que já lê `*2000000~1,2|` corretamente — verificado). Medido:

| colocação | bomba `*2000000~1,2\|` com `max_length=10` |
|---|---|
| expansão em passe separado (1º protótipo) | rejeita **em 2,473 s**, depois de materializar 2 M strings |
| dentro de `expand_seq_marker` (**decisão**) | rejeita **em 0,0000 s**, antes de materializar |

O marcador antigo rejeita em 0,0015 s. A colocação certa é **mais barata de escrever e
mais segura**; a errada passa nos testes funcionais e deixa a bomba de pé.

## Evidência

Lab [`0042`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/),
sonda `design_probe.py` (subclasse + monkeypatch de `tcf.encoder/decoder.HCCSeqRLE` —
`src/tcf` intocado, `encode`/`decode` **reais**):

| caso | hoje | com periódico | |
|---|---:|---:|---|
| dias úteis n=600 | 1590 | **40** | 39,8× |
| dias úteis n=6000 | 15630 | **41** | 381× |
| ids de turno (não-data, sem nature) | 1959 | **32** | 61× |
| úteis + feriado mensal | 1889 | 677 | 2,8× |
| diário · semanal · texto · ruído alta-card | — | **byte-idêntico** | — |

**Gates byte-canonical, com a camada LIGADA:**

| | congelado | com periódico |
|---|---:|---:|
| D1-D9 sintéticos | 1545 | **1545** ✔ |
| real-world (retail ×2 + lineitem) | 89430 | **89430** ✔ |
| **suíte inteira** | 1199 passed | **1238 passed** ✔ (39 testes novos) |

**E3**: o decoder de hoje diante do wire novo **falha alto**
(`contador RLE invalido: '600~1,3,1,1,1'`) — nunca devolve dado errado calado.
**E1 adversarial**: valores que *imitam* o marcador (`"*600~1,3,1,1,1|739617"`,
`"*3~1,2|z"`, `"a|b"`) fazem round-trip — a heurística de separador do ADR-0007 protege.

### A caçada adversarial, e o que ela custou ao design

Cinco lentes independentes atacaram o protótipo; **cinco defeitos distintos**
sobreviveram à deduplicação. Todos foram fechados na v5
([`detector_v5.py`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/detector_v5.py)),
e cada um tem teste em
[`v5_verificacao.py`](../../experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/v5_verificacao.py) (**8/8**):

| # | defeito | escala | como fechou |
|---|---|---|---|
| 1 | teto de memória não cobria o marcador novo (bomba: 16 B → 21 s) | E3 | expand **dentro** do core → 0,03 ms |
| 2 | detector `O(n²)` (n=2400: 13,8 s) | E3 | fronteira de cadeia 1× + `mudanca[]` → +30–32% |
| 3 | FLOOR invertia o desempate → reescrevia wire de dado **sem** periodicidade | E4 | ordem `min(hoje, cru, cand)` |
| 4 | telemetria `seq_rle_runs` zerava **calada** — 1 → 0 em wire byte-idêntico ao do core | E3 | info do candidato **vencedor**, com `start_line` reancorado |
| 5 | pad com cauda morta / extensão → não-injetividade | E4 | período mínimo + guard de re-emissão |

O #4 é o mais instrutivo: não era lacuna do mecanismo novo, era **regressão** de um canal
público (`encoder.py:726` → `schema.py:192` → `sideouts_quality.py`) que os próprios labs
consomem. Nenhum teste pegava — `test_side_outputs.py:58` só afirma `isinstance(..., list)`.

### Segunda caçada — contra a v5 — e os dois defeitos que os CONSERTOS criaram

A v5 foi atacada de novo (5 lentes, 10 achados brutos, **3 confirmados / 2 refutados**,
e **44 hipóteses que não quebraram** — determinismo, empate de economia, assimetria
emite/expande, RT em ~15 000 colunas, polaridade, multi-col, `.8H`, natures, colisão de
gramática). Os dois defeitos distintos que sobreviveram **foram introduzidos pelos
próprios consertos anteriores**:

| # | defeito | medido | fechado na v6 |
|---|---|---|---|
| 6 | o guard de canonicidade (#5) virou **amplificador de recursos**: `_periodo_minimo` era `O(p²)` sobre um pad **sem teto**, e `seq` materializava `count-1` elementos **antes** de validar | 48,8 KB de wire hostil → **126,87 s** (16.881× a camada desligada, que dá o mesmo erro em 7,5 ms); 22 B → 17,25 s e **85 MB** | teto `len(pad) <= MAX_PERIODO`, re-emissão `O(1)` **antes** do resto, período mínimo calculado do **pad** (Fine–Wilf) → **3,75 ms** e **0 MB** |
| 7 | `compact_body(pend)` reaplicado por fragmento **sem piso** ressuscitava marcadores `*N+d\|` que o core tinha recusado — e a **polaridade** cobrava a conta | corpo 9 B menor embarcando wire 19 B **maior**; 963 regressões em 28 985 casos paramétricos | FLOOR por fragmento (o mesmo do core, na granularidade certa) → **0 regressões** e 4905 B a menos |

**A lição do #6 não é sobre este mecanismo**: um gate de validação que trabalha
proporcional ao que o wire *declara*, antes de validar o que o wire declara, é um
amplificador. A ordem das condições é defesa, não estilo.

**A lição do #7 é sobre o projeto**: o `min()` do HCC mede o **corpo canônico**, mas o que
embarca é `polariza(corpo)` (`encoder.py:456`). O FLOOR está sendo medido numa grandeza
que não é a final. Isso vale para o core **hoje**, não só para este mecanismo — o
periódico só tornou visível. Registrado como `T-FLOOR-POS-POLARIDADE`.

> Isolamento que salva o design: o marcador periódico **sozinho** já era nunca-pior
> (0 regressões em 28 985 casos). O defeito era inteiro do `_drena`.

## Consequências

**A favor**

- Ganho de ordem de grandeza num regime comum, e **`O(1)` em `n`** — nenhum outro
  candidato desta família tem isso.
- Vale para qualquer coluna numérica (ids, contadores, ordinais), não só data: o ganho de
  61× apareceu numa coluna que não passa por nature nenhuma.
- Um arquivo, encode e decode espelhados; `_contador_declarado` e o FLOOR por corpo já
  existem e não mudam.

**Contra / custos**

- É **format change** (`#TCF.8`): wire novo não é legível por decoder anterior — mas
  falha alto, não corrompe.
- **CPU.** O número abaixo (**+35%**) é o **PIOR CASO**, não o custo: ele foi medido numa
  série uniforme longa (n=2400) — o formato construído para maltratar o detector, que
  varre tudo e nunca acha nada. **Medido depois em corpus real** (2026-08-13, 138 colunas
  de samples+synthetic+hub, 266 chamadas): o detector custa **1,37% do encode** e ativa em
  **4 de 138** colunas. Publicar só o +35% descrevia o mecanismo errado; os dois números
  ficam, com os regimes explícitos. A forma ingênua do detector era **O(n²)**:

  | detector | n=600 | n=1200 | n=2400 |
  |---|---:|---:|---:|
  | ingênuo (`O(n²)`) | 756 ms | 3 269 ms | **13 838 ms** |
  | + fronteira de cadeia calculada 1× | 27 | 60 | 127 |
  | + saída curta quando não há run | 25 | 52 | 101 |
  | **+ salto de padrão uniforme** (o do weld) | **18** | **35** | **71** |
  | encode sem a camada | 10,5 | 25,5 | 52 |
  | | +71% | +38% | **+35%** |

  Das três armadilhas, a terceira só apareceu **instrumentando por dentro da camada** — a
  medição isolada mentia porque reconstruía o corpo sem o hint de cadência, e o corpo real
  tem uma cadeia única de 1199 deltas. O guard de padrão uniforme rodava por
  (posição × período): ~27 600 fatias e `set()` para concluir "pule". O pré-cálculo
  `mudanca[]` mata isso em `O(n)`.

  Do que sobra, a maior fatia é o **array de deltas**, que `detect_seq_runs` já computa —
  6,8 ms contra 1,6 ms da lógica de período (corpo de 1200 linhas). **Compartilhar o
  array é parte do weld**, não otimização posterior. Vizinho do `T-GATES-ANTES` e do
  `T-SEQRLE-INCREMENTAL`.

- `MAXP = 24` é limite arbitrário (cobre mensal=12 e quinzenal-ano=24). Sem caso medido
  acima disso.

**Não decidido aqui**

- Periódico × multi-run (ADR-0016) — registrado, fora do escopo.
- Trocar `~` se aparecer colisão — antes do 1.0.

## Alternativa considerada e rejeitada

**Forma-lista** (1 ciclo só: `*25~d1,…,d24|` = lista literal de deltas). É o transform de
coluna expresso em gramática, e **perde dele**: 1825 B contra 644 B do delta-coluna no
espalhado, porque o marcador paga ~3 chars por delta e o bN paga 2–5 bits. Pior, com a
forma-lista liberada o greedy prefere listas grandes que destroem runs periódicos
melhores (feriado-mensal: 904 B na forma livre contra 649 B na estrita). Daí a exigência
de **≥ 2 ciclos completos**.

O **transform de coluna** (delta-coluna) continua de pé como mecanismo *complementar* —
ganha onde o ciclo não é exato (mensal 349 B, espalhado-ordenado 644 B, robusto a ruído).
Mas é mudança de **protocolo** (contrato que as 4 specs implementam + decoder + registry)
e depende do `T-NATURE-CANDIDATO-BN`. Ordem: este ADR primeiro.

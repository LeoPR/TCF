# T01 — Critica v1 e direcao v2 (sintese)

**Data**: 2026-05-16
**Contexto**: apos 13 sub-experimentos do T01 incremental (datas/datetime/tz), sintese critica + revisao de literatura + propostas pra v2.
**Status**: HISTÓRICO (faxina 2026-06-21) — exploratorio, NAO implementado.

> **Encerrado**: as propostas v2 foram resolvidas pela superfície welded — pipeline
> delta-aware M10 (ADR-0008/0010/0011) absorveu staged-pipeline/GCD/cadência; o
> escape-deduction proposto aqui foi REFUTADO real-world (Pacote 2, <1.13%). Fica como
> registro da revisão de literatura e do pivô. Lab de origem em
> [`old/welded/2026-05-15-naturezas-e-camada/`](../old/welded/2026-05-15-naturezas-e-camada/).

---

## Parte 1 — Critica T01 v1 (auditoria)

### 1.1 O que T01 v1 fez bem (e cita-se a literatura)

- **Staged pipeline (A identify / B normalize / C optimize)** — corresponde a pratica
  de motores TSDB modernos (InfluxDB TSM, IoTDB TS_2DIFF, ClickHouse codec chain).
  "Burros e trabalhadores agora, pequenos e rapidos depois" tem analogo direto
  em codec-chain de ClickHouse: `CODEC(DoubleDelta, LZ4)` = 2 passos explicitos.
- **Sufixos de escala (`Y`/`M`/`D`/`h`/`m`/`s`/`ms`/`us`/`ns`)** — equivalente a
  **GCD scaling** do InfluxDB TSM (detectar GCD que e' fator de 10 nos deltas e
  promover a unidade). Diferenca: InfluxDB e' automatico, T01 v1 e' greedy per-scale
  com decisao manual. Validado em D11c→`1M`, D11e→`1M`, D11f→`1s`, etc.
- **Self-containment do .tcf** (sub-exp 09) — `decoder(.tcf path) → original` sem
  hint externo. Equivalente a logical types do Parquet
  (`TIMESTAMP(unit, isAdjustedToUTC)` carregado dentro do arquivo).
- **Escape dedutivel (sub-exp 11)** — descoberta independente do principio
  "materializacao minima". Nao tem equivalente direto em sistemas pesquisados,
  mas e' analogo ao principio geral de **omitir o que e' deducivel pelo decoder**.
- **Template marker (sub-exp 12)** — POC do principio "parte estatica do template,
  parte variavel marcada". Tem analogo em **calendar-aware encoding** (codificar
  `(year, month)` quando dados sao mensais — `?` no template = posicao varivel).
- **TZ-aware (sub-exp 13)** — analogo a **VertiPaq Date+Time split**: separar
  constante (tz) da parte variavel (datetime) habilita encoding mais agressivo.

### 1.2 O que ficou implicito ou nao testado

Levantado pela auditoria explore + perspectiva literatura:

| # | Gap | Impacto |
|---|---|---|
| G1 | **Delta-of-delta (DoD)** nunca testado | Gorilla/Prometheus/IoTDB: cadencia regular gera 96% de DoD zero. Nosso `*12\|1M` ja' captura RLE-equivalente; mas DoD generaliza pra cadencias semi-regulares (gap de fim de semana, etc.). |
| G2 | **Auto-detect de granularidade real** via GCD do delta-stream | InfluxDB faz; ns gravados como `09:00:00.000000000` com deltas multiplos de 60s viram `m`. T01 v1 detecta granularidade no Stage A pelo FORMATO (sufixos `.fff`), nao pelo CONTEUDO dos deltas. |
| G3 | **Block/segment com min_delta subtraction** | Parquet DELTA_BINARY_PACKED: divide em blocos de 128, subtrai `min(block)` antes de pack. Reduz drift em series longas. T01 v1 usa base unica global. |
| G4 | **Formato alternativo de delta** | Sempre decimal string. Varint, base32, ou outros formatos texto-compativeis nao testados. |
| G5 | **Deltas negativos** | Permitido em principio, todos datasets D11a-h sao monotonicos. Sem dataset adversarial. |
| G6 | **Periodic pattern detection (sliding window)** | TSXor mantem N predecessores como candidatos pra menor delta. Aplicavel a dados com sazonalidade (semanal/mensal). |
| G7 | **Composicao com outras naturezas** | T01 isolado. Pipeline T01→T02 (templated→incremental) nao testado. |
| G8 | **Calendar-aware NAO foi articulado como fast path explicito** | Funcionou via escala `M`, mas v2 deveria expor "este e' o caminho calendarico" claramente. |
| G9 | **Detecao automatica de natureza** | User marca "isto e' incremental". Heuristica auto (e.g., monotonicidade + delta pequeno) nao tentada. |
| G10 | **Performance / memoria** | Zero medicao. Tudo CPU-batch. |
| G11 | **Datasets reais** | Todos D11a-m sinteticos. Logs reais, series de producao, nao tocados. |
| G12 | **Variable-length encoding pos-delta** (Simple-8b, FOR, PFOR) | Justificavel: TCF e' texto, nao bit-stream. Mas vale registrar que o **paradigma binario** tem 60-90% menos bytes que decimal em deltas iguais. |

---

## Parte 2 — O que a literatura ensina (sintese de 20+ fontes)

### 2.1 Tecnicas que aparecem em quase TODO sistema sertio

- **Delta-of-delta** (Gorilla, Prometheus, ClickHouse, TimescaleDB, IoTDB, Parquet DBP).
  Para cadencia regular: D[i] = D[i-1] → DoD = 0 → bit unico.
- **Block-level min subtraction** (Parquet, IoTDB, FOR-encoding).
  `block = [min_delta, deltas-min_delta]` permite bit-pack agressivo.
- **Bit-packing pos-delta** (Simple-8b, FOR, PFOR, NewPFD). Aplicavel a binario; em
  TCF (texto) o analogo seria decimal-pack ou base32-pack.
- **Dictionary encoding** (VertiPaq, Columnstore, Parquet RLE_DICTIONARY).
  Pra datas: vale quando ha repeticao massiva (agregacao diaria, nao timestamps unicos).
- **RLE sobreposto** (universal). T01 v1 ja' herda do HCC (`*N|`).
- **Pre-tx + entropy coder** (LZ4/ZSTD/Snappy). VictoriaMetrics: zstd em cima de
  Gorilla ganha 10x extra. Licao: pre-tx NAO substitui coder geral; **alimenta**-o.

### 2.2 Tecnicas Microsoft-especificas

- **VertiPaq Date+Time split** (SQLBI canon): separar `DateKey` int de `TimeKey` int
  habilita value+RLE em Date (baixa cardinalidade) e dict pequeno em Time. 30-60%
  reducao vs DateTime monolitico em BI workloads.
- **SQL Columnstore + XPRESS (LZ77)**: 2 camadas, valor+packing seguido por entropy.
  Datetime se beneficia mais de RLE quando ordenado.
- **Parquet DELTA_BINARY_PACKED**: bloco 128, mini-bloco 32, min_delta subtraction,
  bitwidth por mini-bloco. **Recomendado pra timestamps INT64**.

### 2.3 Tecnicas pouco usadas mas relevantes pro TCF

- **GCD scaling auto** (InfluxDB) — quase ninguem mais faz; sub-exp 06-08 do T01
  fizeram greedy por scale. Auto seria detectar GCD dos deltas e mudar unidade.
- **TSXor sliding window** — mantem N predecessores como candidatos pra delta.
  Util pra dados com saltos periodicos.
- **Calendar-aware encoding explicit** (raro): codificar `(year, month)` int16+int8
  pra dados mensais bate qualquer DoD bruto. T01 ja' faz isso implicitamente
  com escala `M`, mas vale articular como caminho preferido.
- **Lexicographic-preserving ISO 8601 basic** (`YYYYMMDDTHHMMSSZ` sem separadores):
  preserva sort cronologico = lexico, habilita LCP/LCS sem ruido. Vale considerar
  como **representacao interna** durante encode (re-format na saida).

### 2.4 Consenso da literatura

Pipeline canonico pra coluna temporal (toda fonte: Gorilla, IoTDB, Parquet, TSDB):

```
1. Detect granularity / GCD              ← Stage A do T01 v1 (ja' faz parcialmente)
2. Convert to unit base                   ← Stage B (ja' faz)
3. Delta encoding                         ← Stage B/C
4. Delta-of-delta encoding                ← **T01 v1 NAO faz**
5. Min subtraction por bloco              ← **T01 v1 NAO faz**
6. Bit-packing (Simple-8b/FOR/PFOR)       ← inaplicavel a texto TCF; analogo decimal
7. RLE pra runs de zero/igual             ← HCC ja' aplica (`*N|`)
8. Entropy coder final (LZ4/ZSTD)         ← out-of-scope TCF (formato texto)
```

T01 v1 cobre passos 1, 2, 3, 7 (parcial); pula 4, 5, 6. Passos pulados sao onde
estao **bytes adicionais nao colhidos**.

---

## Parte 3 — Diferenca conceitual T01 v1 vs estado-da-arte

**T01 v1 e' single-pass + greedy + scale-aware**. Funcionou bem para datasets
realisticos com cadencia regular pequena (D11a-h, 6-14 linhas). O algoritmo
fundamental e':

```python
base = first_value
for i in range(1, n):
    delta = value[i] - value[i-1]
    if delta == greatest_scale.unit:
        emit("1" + greatest_scale.suffix)
    else:
        # try smaller scales, fall back to base unit
        emit(scale_aware_repr(delta))
```

**Estado-da-arte e' multi-pass + chain de codecs + bloco-aware**:

```python
# Pass 1: GCD scaling auto
unit = detect_gcd_of_deltas(values)
# Pass 2: DoD
deltas = first_diff(values)
double_deltas = first_diff(deltas)
# Pass 3: Block min subtraction
for block in chunks(double_deltas, 128):
    min_d = min(block)
    emit(min_d, [d - min_d for d in block])
# Pass 4: Bit-pack (ou ascii-pack pra texto)
# Pass 5: RLE (downstream)
# Pass 6: Entropy coder (out-of-scope TCF)
```

A diferenca pratica: **DoD reduz 96% dos valores a zero quando cadencia e' regular**.
T01 v1 captura isso indiretamente via RLE no HCC (`*12|1M` = 12 deltas iguais),
mas isso e' RLE sobre deltas iguais, NAO compactacao de "sequencia de zeros"
gerada por DoD.

Exemplo de cadencia semi-regular (sem `1M` exato, com gaps):
```
[2026-01-05, 2026-02-05, 2026-03-05, 2026-04-06, 2026-05-05]
deltas: [31d, 28d, 31d, 29d]  ← em days, ruido por mes
DoD:    [-3d, 3d, -2d]         ← pequenos
```

T01 v1 com escala `M` falharia (delta `29d` nao bate `1M` exato);
DoD com bit-packing colocaria isso em poucos bits.

---

## Parte 4 — T01 v2: propostas (ordem de prioridade)

Cada item: **conceito** + **ganho esperado** + **complexidade**. Numeracao
nao implica ordem de execucao; user escolhe.

### V2.1 — Delta-of-delta primeiro, scale-aware depois

**Conceito**: depois de calcular deltas (passo atual do Stage B), calcular
second-difference. Se DoD-stream tem muitos zeros consecutivos → caminho preferido.
Senao → cai pra deltas + escala (caminho atual).

**Ganho esperado**: cadencias semi-regulares (mensais com 28/29/30/31), padroes
com pequenos jitters; DoD captura padrao mesmo quando escala exata falha.

**Complexidade**: baixa. Stage B' adiciona linha; Stage C' decide entre 2 streams.

**Risco**: maior overhead pra single-row ou cadencia totalmente irregular.

### V2.2 — Auto-detect GCD do delta-stream (InfluxDB-style)

**Conceito**: depois de Stage B, calcular `gcd(deltas)`. Se GCD e' fator natural
(60s, 3600s, 86400s, 7×86400s = semanal), promover a unidade automaticamente.

**Ganho esperado**: deltas em segundos multiplos exatos de 86400 ja' viram
`1d`/`2d`/... sem precisar usuario marcar; cobre **cadencias semanais e custom**
nao previstas em sub-exp 08.

**Complexidade**: media. GCD em timedelta tem casos especiais (mes nao tem GCD
exato com segundo).

**Risco**: ambiguidade quando GCD e' coincidencia (3 datas separadas por 12h cada,
GCD=12h, mas semantica e' "meio dia" e nao unidade real).

### V2.3 — Calendar-aware fast path explicito

**Conceito**: Stage A detecta "cadencia calendarica" (mensal, anual, semanal-fixo).
Stage B aplica encoder dedicado `(year, month [, day_of_month])` em vez de
delta-em-segundos. Stage C nao precisa de escala `M`.

**Ganho esperado**: dados mensais com ruido jamais batem DoD bem (irregular por
natureza); encoder dedicado bate ate' DoD. Caso D11e, D11c.

**Complexidade**: media. Precisa formalizar "cadencia calendarica" e seu encoder
canonico.

**Vantagem adicional**: deixa T01 v2 conectado a calendario, nao a clock-tick.

### V2.4 — Block-based com min subtraction

**Conceito**: dividir delta-stream em blocos (e.g., 128 valores ou tamanho
dataset). Por bloco: `[min_delta, deltas - min_delta]`. Reduz drift em series
longas.

**Ganho esperado**: series com 1k+ valores onde drift acumula (TCF v1 atual nao
tem dataset assim — datasets sao todos < 14 linhas). Util pra escalar TCF a
inputs reais (logs).

**Complexidade**: media. Precisa convencao pra delimitar blocos no .tcf.

**Risco**: overhead em blocos pequenos. Pode ser opt-in para inputs > N linhas.

### V2.5 — Periodic pattern detection (sliding window)

**Conceito**: pra cada novo valor, computar deltas vs N predecessores (t-1, t-7,
t-30). Escolher o menor. Codificar como `<delta>@<offset>` ou marcador. 

**Ganho esperado**: dados com sazonalidade explicita (logs ignoram fim de
semana → t-3 produz delta 0 enquanto t-1 produz 3 dias). 

**Complexidade**: alta. Precisa janela + convencao de marcador.

**Risco**: complexidade alta sem dataset que prove valor. Diferir ate' ter dado real.

### V2.6 — Composicao com outras naturezas (entry points)

**Conceito**: T02 templated extrai layout, devolve slots por linha; T01
incremental opera sobre os slots numericos. Pipeline:

```
"2026-05-15 09:30:45-03:00"
    ↓ T02 templated extract
template: "????-??-?? ??:??:??-??:??"
slots:    ["2026", "05", "15", "09", "30", "45", "-03", "00"]
    ↓ T01 incremental em cada serie de slots (year, month, day, ...)
```

**Ganho esperado**: T01 sozinho nao pode atacar D12 (timezone composto); T02→T01
poderia.

**Complexidade**: alta. Pipeline multi-natureza e' novo territorio.

**Status**: T02 ainda nao existe. Tem que esperar.

### V2.7 — Representacao alternativa de delta (base32 / varint-texto)

**Conceito**: testar deltas em base32 (`0-9a-v`) ou varint-texto (`!`-`~`).
Comparar bytes vs decimal.

**Ganho esperado**: deltas grandes (> 9) ganham bytes em base32; ja' < 9 nao.
Datasets D11h (cadencia 1us) com deltas pequenos talvez nao se beneficie.

**Complexidade**: baixa. Encoder/decoder simples.

**Risco**: quebra de legibilidade do .tcf texto. Conflito com filosofia de TCF
texto-amigavel. Decisao do user.

---

## Parte 5 — OBAT/HCC tree-time integration (sketch conceitual)

A pergunta do user: "vamos ver como podemos auxiliar o obat e o hcc para fazerem
isso em tempo de avaliacao de arvore e/ou hcc". Isto e' essencialmente o
**Track 2** do META-TYPE-ENCODERS (L01-L05). Sketch das ideias mais viaveis:

### Sketch A — HCC com threshold-based virtual ref (L02 estendido)

**Hoje**: HCC detecta virtual refs por **igualdade exata** de substring.

**Proposta**: permitir ref **com offset/delta tipado**. Sintaxe ilustrativa:
```
^N+1d        ← ref ao node N + 1 dia (semantic delta)
^N+1m        ← ref ao node N + 1 minuto
^N*2         ← ref ao node N multiplicado por 2 (escala)
```

Pra isso ser viavel, HCC precisa **conhecer o tipo do node** referenciado.
Conecta com:

- Stage A do T01 (identify) → marca node como `[type=date, unit=day]`
- Detector HCC verifica nodes do mesmo tipo, calcula distancia
- Se distancia < threshold → emite virtual ref com delta inline

**Implicacao**: T01 v2 pode-se transformar em **plugin do HCC**. Em vez de
pipeline pre-tx separado, e' uma "biblioteca de deltas tipados" que HCC chama
quando detecta dois nodes tipados como datas.

### Sketch B — OBAT com LCP calendar-aware (L01 estendido)

**Hoje**: OBAT compara byte-a-byte pra LCP (longest common prefix).

**Proposta**: quando ambos strings sao detectados como dates (Stage A do T01
roda inline), LCP vira "common calendar prefix" (year > year-month >
year-month-day).

Exemplo:
```
"2026-05-15 09:00:00"  vs  "2026-05-15 09:01:00"
LCP atual (byte): "2026-05-15 09:0"  (15 chars)
LCP calendar-aware: ("year", "month", "day", "hour") = 4 niveis = 13 chars
```

Marginal pra dates, mas significativo em datasets onde estrutura calendarica
muda mas byte-prefix nao (e.g., timestamps em diferentes timezones).

### Sketch C — Marker tipado no HCC (L03)

**Hoje**: `~` e' generico.

**Proposta**: `~d` (date), `~e` (enum), `~t` (templated), etc. Detector
seleciona estrategia conforme tipo.

**Conexao com T01 v2**: T01 v2 vira o "modulo date" que detecta cadencia + emite
representacao otimizada quando HCC encontra `~d`.

### Resumo dos sketches

Track 2 (L01-L03) e Track 1 v2 (T01 v2) **convergem** numa visao onde:

```
encode(linhas):
    for linha in linhas:
        nodes = OBAT.tokenize(linha)     # LCP/LCS calendar-aware quando aplicavel
        for node in nodes:
            type = identify_type(node)   # Stage A do T01 inline
            HCC.add_node(node, type)     # node + tipo
    HCC.detect_refs(threshold_per_type) # refs exatas ou com delta tipado
    HCC.emit(format_strategy_per_type)   # T01-style delta pra dates, etc.
```

Isto e' uma re-arquitetura de OBAT+HCC, NAO uma evolucao de T01 v1. T01 v1 e
seus 13 sub-exps validaram **conceitos isolados** (delta+scale, template,
materializacao minima, tz-extract). Versao final desses conceitos pode acabar
**embutida no algoritmo** em vez de pre-tx externo.

**Caminho recomendado**: T01 v2 como **pipeline pre-tx solido** (V2.1-V2.4 = ganhos
robustos imediatos) E **explicitamente desenhado pra ser portavel pra inline em
HCC depois** (interface limpa, tipo-aware).

---

## Parte 6 — Recomendacao de proximo passo

**Tradeoff principal**: T01 v2 pode ser

- **(a)** continuacao iterativa: 1 sub-exp por proposta V2.X, ao longo de 1-2
  semanas, gerando mais 5-7 sub-experimentos dirty.
- **(b)** clean-room: 1 desenho consolidado que aplica V2.1-V2.4 num pipeline
  novo, com decoder espelho, testado em D11a-m. Engenhoca anterior nao re-usa
  codigo (filosofia dirty: engenhoca extrai ideia, descarta codigo).

**Recomendacao**: **opcao (b)** — clean-room. Justificativa:

- T01 v1 validou conceitos basicos suficientes. Mais 7 sub-exps incrementais
  arriscam diluir foco.
- Literatura mostra que tecnicas-chave (DoD, GCD-auto, min-subtraction) sao
  pipeline coerente, nao adicoes ortogonais. Faz sentido desenhar junto.
- Clean-room forca articulacao do conceito sem heranca de hardcode dirty.

**Caso (b) seja escolhido**, proxima conversa pode arrancar com:

1. Decidir escopo V2 (quais propostas: V2.1+V2.2+V2.3? V2.1+V2.4? V2.1-V2.4?)
2. Decidir representacao concreta (texto puro vs base32, marker convention,
   block delimiter)
3. Desenhar interface tipo-aware pensando em portabilidade pra HCC inline
4. Implementar em `2026-05-16-T01-v2/` (pasta nova, fora do `T01-incremental-base-delta/`)

**Conexoes**:

- [`tickets/META-TYPE-ENCODERS.md`](../../../tickets/META-TYPE-ENCODERS.md) —
  plano-mestre original
- [`docs/theory/data-natures-taxonomy.md`](../../../docs/theory/data-natures-taxonomy.md)
- [feedback-dirty-lab-filosofia] — engenhoca extrai ideia
- [feedback-validacao-e-dados] — datasets realistas, esgotar semantica
- [feedback-materializacao-minimal] — principio aplicado em sub-exp 11

## Anexo — Bibliografia consultada

**Microsoft / VertiPaq / Parquet**:

- SQLBI VertiPaq topic — https://www.sqlbi.com/topics/vertipaq/
- Microsoft Learn Data Compression — https://learn.microsoft.com/en-us/sql/relational-databases/data-compression/data-compression
- Parquet Encodings spec — https://parquet.apache.org/docs/file-format/data-pages/encodings/
- Parquet LogicalTypes — https://github.com/apache/parquet-format/blob/master/LogicalTypes.md

**Papers academicos**:

- Pelkonen et al. 2015 (Gorilla, VLDB) — https://www.vldb.org/pvldb/vol8/p1816-teller.pdf
- Liakos et al. 2022 (Chimp, VLDB) — https://www.vldb.org/pvldb/vol15/p3058-liakos.pdf
- Song et al. 2022 (IoTDB TS_2DIFF, VLDB) — https://www.vldb.org/pvldb/vol15/p2148-song.pdf
- Bruno et al. 2021 (TSXor, SPIRE) — https://link.springer.com/chapter/10.1007/978-3-030-86692-1_18
- Anh & Moffat 2010 (Simple8b)
- Zukowski et al. 2006 (PFOR)
- Lemire et al. 2015 (FastPFOR survey)

**TSDB / Warehouses**:

- ClickHouse Codecs — https://clickhouse.com/resources/engineering/database-compression
- TimescaleDB Hypercore — https://www.tigerdata.com/blog/time-series-compression-algorithms-explained
- InfluxDB Storage Engine — https://docs.influxdata.com/influxdb/v1/concepts/storage_engine/
- Prometheus TSDB chunks — https://github.com/prometheus/prometheus/blob/main/tsdb/docs/format/chunks.md
- Apache IoTDB encoding — https://iotdb.apache.org/UserGuide/V1.2.x/Basic-Concept/Encoding-and-Compression.html
- VictoriaMetrics compression — https://faun.pub/victoriametrics-achieving-better-compression-for-time-series-data-than-gorilla-317bc1f95932

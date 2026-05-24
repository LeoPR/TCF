# META-TYPE-ENCODERS — Pre-tx por natureza + estudos da camada de algoritmo

**Status**: OPEN (T01 absorvido; T02-T07 + L01-L05 adiados; sub-escopo Perf transferido pra novo ticket)
**Criado**: 2026-05-15
**Ultima atualizacao**: 2026-05-24

## Atualizacao 2026-05-24 — sub-naturezas templated/checksummed catalogadas

Owner detalhou sub-naturezas concretas de T02 (Templated) e T04 (Checked),
plus extensoes de #10 (Lossy) catalogadas em
[`experiments/lab/dirty/notas/naturezas-templated-2026-05-24.md`](../experiments/lab/dirty/notas/naturezas-templated-2026-05-24.md):

- **TM-IP4/IP6/MAC/CEP/EAN** (Templated puro)
- **TM-CPF/CNPJ/TITULO/IBAN/LUHN** (Templated + Checksummed dual)
- **TM-FONE-BR/INTL, TM-DATA-BR, TM-EMAIL, TM-URL** (Templated com mascara)
- **LR-FLOAT-PREC/GEO/MONETARY/DIST/PERC** (Lossy com erro controlado)
- **CP-DATETIME/ENDERECO/MONEY/VERSION** (Composite multi-nature)

Hipoteses H-TM-* / H-LR-* / H-CP-* registradas em
[`roadmap-hipoteses.md`](../experiments/lab/dirty/notas/roadmap-hipoteses.md)
secao "Pacote 7 — Templated / Checksummed / Lossy".

**Status**: catalogado, **lab nao iniciado**. Mesmo criterio de reabertura
de T02-T07: casos real-world onde Pacote 1+ADR-0008 nao bastem. Pre-requisito
imediato: owner roda T-DATA-1 scripts (Online Retail, Beijing PM2.5,
Wine Quality) -> dados disponiveis -> sub-exp caracterizacao.

## Atualizacao 2026-05-19 — realidade pos-Pacotes 1/3/4

Plano original (2026-05-15) propunha 7 naturezas (T01-T07) + 5 estudos
(L01-L05) executados em ondas paralelas. Realinhamento 2026-05-15 reduziu
pra "uma natureza por vez", comecando por **T01 incremental**. 13
sub-exps de T01 foram executados — mas conclusao revelou que **pre-tx
multi-pass viola vertice triplice** (single-pass/low-mem/low-latency).

**T01 foi ABSORVIDO** numa abordagem OBAT-level (Pacote 1 Delta-aware),
welded em [`EXP-010-tcf-delta-aware-prototype/`](../experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/).

**Pacotes posteriores nao previstos no plano original**:
- **Pacote 3 (parser robustness)** [ADR-0007](../docs/adr/0007-comma-in-literals-bug.md) — bug `,` em literais HCC fixado
- **Pacote 1 refino** [ADR-0008](../docs/adr/0008-detect-cadence-numeric-rule.md) — heuristica numeric+high-cardinality
- **Pacote 4 (perf OBAT)** [ADR-0009](../docs/adr/0009-obat-trigram-index-optimization.md) — hash trigrama, alpha 1.75→1.42

**Decisao**: T02-T07 e L01-L05 **permanecem adiados**. Reabertura
condicionada a:
1. Pacote 4 perf fechar (H-PERF-04/05/06)
2. Pelo menos uma natureza estrutural (T02 templated ou T03 enumerated)
   ter casos real-world onde Pacote 1 + ADR-0008 nao bastam

Sub-escopo de performance (L01-L05 + novas H-PERF-*) foi **transferido**
pra ticket dedicado: [META-PERF-PHASE2](META-PERF-PHASE2.md) (a criar).

## Escopo original (preservado abaixo para referencia historica)

**Escopo atual** (apos realinhamento 2026-05-15):

- **Primeira natureza: incremental (datas)**. Trabalho em dirty lab
  pequeno e iterativo, descartavel/refazivel ("faz/refaz/destroy/
  reconstroi" sem deixar lixo em src/tcf).
- **Demais naturezas (T02-T07) e Track 2 inteiro: diferidos.**
  Documentados abaixo como **roadmap conceitual**, sem execucao
  ate' T01 validar metodologia.

### Por que realinhar

Plano inicial (2026-05-15 manha) propunha 7 naturezas + 5 estudos
de algoritmo em 4 ondas paralelas. Usuario apontou que isso e'
escopo excessivo: precisamos de **uma natureza por vez** pra
controle fino, e o processo aprendido na primeira **padroniza-se**
pra demais. Ambicao multi-track + comprometimento prematuro com
`src/tcf_pretx/` foram removidos.

## Motivacao

[EXP-008](../experiments/lab/clean/EXP-008-compressao-comparada/) deixou claro:

- TCF sozinho cai pra **64% vs CSV** (reducao 36%);
- Mas com brotli no caminho: `csv/brotli` vence em **10/15** datasets, `tcf/brotli` so' em D8 (cabeca-cauda).
- TCF como pre-tx **raramente complementa** brotli/zstd nessa escala — sobreposicao alta de mecanismos.
- D10-D15 (tipos ERP/CRM variety) ficam parados: TCF v0.6 atual nao consegue normalizar formato.

Estratégias 1.A (pre-tx por tipo) e 3.B (slot detection online) do
[roadmap perspectiva-triplice](../docs/theory/perspectiva-triplice-e-pre-tx.md) respondem essa lacuna.

## Principio metodologico

> **Estudar pela natureza do comportamento dos dados, nao pelos dados em si.**

Em vez de escrever encoders separados pra CPF, UUID, data, email,
base64, ... classificar dados em **categorias comportamentais**
(incremental, templated, enumerated, checked, etc.) e escrever
encoders **por nature**. Tipos especificos sao **exemplos** dessas
naturezas. Um dado pode pertencer a multiplas naturezas
(ex: datetime e' templated + incremental + composite).

**Vantagens**:
- Encoder generalizado por nature cobre N tipos de uma vez.
- Manutencao melhor (menos codigo, mais reuso).
- Composicao explicita: pipeline pode aplicar multiplas naturezas em sequencia (templated → incremental → ...).
- Estrutura conecta melhor com camada algoritmica (Track 2): se OBAT sabe que slots existem, integra com encoder templated naturalmente.

### Dados realistas, nao caos artificial

> **TCF e' pra dados de sistemas reais** (saudaveis, coerentes, com
> padrao). Diretriz [feedback-dados-realistas-nao-lixo] (2026-05-15).

Quando alguem constroi um sistema de dados, a probabilidade de criar
um padrao e segui-lo e' alta. **Pre-tx por natureza tem maior valor
onde redundancia estrutural existe** (caso comum em sistemas reais),
nao em variedade extrema (caso patologico).

**Datasets que guiam evolucao**: padroes realisticos — log
sequencial, registros incrementais com gaps razoaveis, cadencias
periodicas, enumeracoes coerentes (`D1`-`D9`, `D11a`, `D11b`,
`D11c+`).

**Datasets que NAO guiam evolucao** (mas servem como stress de
variety extrema): `D10` (15 layouts mundiais de data na mesma
coluna), `D13` (CPFs misturados/defeitos), `D14` (UUIDs em multiplos
formatos canonical). Sistemas reais validam formato; nao acontece.
Esses ficam como **referencia de comportamento extremo**, nao
direcao.

"Lixo total" (formatos misturados, defeitos generalizados) e'
tratado em fase separada, **depois** do TCF ser solido em dados
realisticos.

## Visao de end-state (decisao adiada totalmente)

Destino final pretendido: pipeline `pre → encode` / `decode → pos`
**como modulo dentro de `src/tcf/`** (ex: `src/tcf/pretx/` +
`src/tcf/postx/`, ou unificado `src/tcf/pipeline/`).

```
input → [pre-tx por nature] → encode (OBAT + HCC) → bytes
bytes → decode (HCC + OBAT) → [pos-tx por nature] → output
```

**Mas trabalho atual e' INTEIRAMENTE no dirty.** Dirty e'
destrutivo ("faz/refaz/destroy/reconstroi") — colocar codigo
exploratorio no `src/tcf/` cedo gera lixo dificil de remover.
**Welding final acontece so' quando uma natureza for solida.**

E mesmo assim, **forma do welding depende do desfecho do Track 2**:

- **Cenario A — Track 1 sustenta valor proprio**: pre-tx por
  nature reduz bytes consistentemente alem do que OBAT/HCC
  conseguem. Welding → `src/tcf/pretx/` como modulo dedicado.
- **Cenario B — Track 2 absorve parte do Track 1**: se L02
  (slot detection online no OBAT) e/ou L03 (markers tipados)
  provarem que natures podem ser detectadas e aplicadas durante
  a construcao da arvore do OBAT, partes do Track 1 viram parte
  nativa do OBAT — sem encoder pre-tx dedicado.
- **Cenario C — hibrido (esperado mais provavel)**: natures que
  precisam de semantica externa (incremental, checked, lossy,
  composite) ficam pre-tx; natures estruturais (templated, slot)
  sobem pro OBAT.

Por isso: **nada vai pra `src/tcf/` ate' Track 1 ter pelo menos
uma natureza solida E Track 2 ter alguma evidencia inicial**.
Antes disso, `src/tcf/` fica intocado (canonical desde welding M14).

## Taxonomia das 8 naturezas

| # | Nature | Definicao | Mecanismo | Exemplos tipicos | Datasets onde aparece |
|---|---|---|---|---|---|
| 1 | **Incremental** | Valor expresso como Δ de referencia | base + delta | data, timestamp, ID sequencial, contador | D6 logs (timestamps), D10-D12 datas |
| 2 | **Templated** | Layout fixo + slots variaveis | extrai template, encode slots | CPF, UUID, email, IP, URL, telefone | D1-D2 emails, D3 URLs, D8 prefix/suffix, D13 CPF, D14 UUID |
| 3 | **Enumerated** | Dominio finito (caber em dicionario) | indice no dicionario | gender, status, country, currency, dominios populares | D1-D2 dominios (gmail/hotmail/yahoo) |
| 4 | **Checked** | Tem digito verificador redundante | elide check, regen no decode | CPF, CNPJ, EAN/UPC, Luhn, IBAN | D13 CPF |
| 5 | **Composite** | Multiplos sub-valores em um campo | split + encoder por parte | datetime (date+time+tz), money (currency+amount), phone (cc+area+num) | D11, D12 datetime, D6 logs |
| 6 | **Hierarchical** | Valores aninhados em arvore | shared prefix tree | path, URL, DNS, JSON path, namespace | D3 URLs `api/users/...`, D7 aninhamento |
| 7 | **Lossy-recoverable** | Aproximado com erro controlado registrado | round + delta error | geo coords com precisao, floats com tolerancia | (nao presente em D1-D15 atual) |
| 8 | **High-entropy** | Sem redundancia exploravel | passthrough (don't encode) | UUID random, hash, base64 random, criptografado | D4 caos parcial, D14 UUID random, D15 base64 random |

Taxonomia formal em [`docs/theory/data-natures-taxonomy.md`](../docs/theory/data-natures-taxonomy.md) (a criar).

### Composicao de naturezas

Um valor pode ser **decomposto sucessivamente**. Exemplo: datetime com timezone.

```
"2026-05-15T09:30:45-03:00"
    ↓ templated extract
template: "YYYY-MM-DDThh:mm:sszz:zz"
slots:    ["2026","05","15","09","30","45","-03","00"]
    ↓ composite split
date_slots:  ["2026","05","15"]
time_slots:  ["09","30","45"]
tz_slots:    ["-03","00"]
    ↓ incremental (em cada componente, se serie)
date_base = "2026-05-15", deltas = [0, 0, 0, ...]
time_base = "00:00:00",   deltas = [9:30:45, ...]
tz = enum {-03:00} (1 valor unico — dicionario)
```

Pipeline natureza-a-natureza pode ser **enorme** em redundancia em
casos reais (logs de timestamp, IDs sequenciais).

## Estrutura proposta de diretorios

Decisoes vigentes apos realinhamento:

- **Dirty lab**: 1 unificado com 2 tracks dentro (criado, com sub-pastas vazias).
- **EXP-009**: meta-pasta criada como stub — **sub-experimentos
  abrem so' quando macro dirty correspondente fechar com sucesso**.
- **Localizacao final do codigo no `src/tcf/`**: **decisao adiada
  totalmente**. Trabalho fica no dirty enquanto experimentos rodam.
  Quando algo se mostrar solido, decide-se entre embutir no
  `src/tcf/` (modulo, ex: `src/tcf/pretx/`) ou em outro layout
  conforme aprendido. Nao criar `src/tcf_pretx/` agora.

```
experiments/lab/dirty/2026-05-15-naturezas-e-camada/
├── README.md
├── notas/
│   ├── historia-naturezas-camada.md
│   └── conclusoes_T0X.md              # 1 por macro fechado
├── pre-tx/                            # Track 1 (ativo: so T01)
│   ├── T01-incremental-base-delta/    # ATIVO
│   ├── T02-templated-extract/         # DIFERIDO
│   ├── T03-enumerated-dict/           # DIFERIDO
│   ├── T04-checked-elide/             # DIFERIDO
│   ├── T05-high-entropy-passthrough/  # DIFERIDO
│   ├── T06-composite-split/           # DIFERIDO
│   └── T07-hierarchical-shared/       # DIFERIDO
└── algoritmo/                         # Track 2 — INTEIRO DIFERIDO
    └── (vazio ate' Track 1 validar metodologia)

experiments/lab/clean/
└── EXP-009-pre-tx-natureza/           # stub, abre quando T01 fechar
    └── README.md
```

T01 e' o **unico ativo**. Demais T0N e L0N **nao tem pasta criada
ainda** — quando vier a vez, cria-se.

## Track 1 — Pre-tx por natureza (detalhe por sub-fase)

> **Execucao realinhada (2026-05-15)**: foco em **T01 incremental** primeiro.
> Sub-fases T02-T07 abaixo sao **roadmap conceitual** — execucao
> adiada ate' T01 validar metodologia. Quando T01 fechar, este
> ticket sera revisado pra escolher a proxima natureza com base
> em gaps identificados, composicao com incremental, etc.

### T01 / EXP-009.1 — Incremental (base + delta)  **— ATIVO**

**Pergunta**: Quanto reduz uma serie de datas se extrairmos base
(menor) + deltas pequenos (geralmente em dias/horas) em vez de strings completas?

**Hipotese**: D11 (datetime-precisao) atualmente 70% vs csv com TCF;
com base+delta cai pra <30% (deltas sao numeros pequenos
codificavies em poucos digitos).

**Dataset alvo**: D11, D12, D6 logs (timestamps).

**Sub-perguntas**:
- Como representar delta? Decimais? Bytes raw? Codigo Elias gamma?
- Reset de base periodico (chunks) ou base unica global?
- Sinal de delta (negative deltas permitidos)?
- Composicao com templated: encoder templated extrai estrutura, encoder incremental opera nos slots numericos.

**Saida esperada**: `incremental.py` com `encode(linhas) -> (base, deltas_encoded)` e `decode((base, deltas)) -> linhas`.

### T02 / EXP-009.2 — Templated (layout extract)

**Pergunta**: Dado um set de strings que seguem layout fixo
(CPF, UUID, email), conseguimos extrair o template + slots e
ganhar bytes?

**Hipotese**: D13 CPF cai de 100% (TCF identidade) pra <50% (so slots).

**Sub-perguntas**:
- Como **detectar** o template? Regex? Anti-unificacao online? Heuristica simples ate' funcionar?
- Multiplos templates no mesmo input (ex: CPFs misturados com/sem mascara)?
- Encoder devolve [template_id, slots] ou inline (template ja' embutido na cabeca)?
- Template como dicionario externo (compartilhado por coluna) ou inline (auto-contido)?

**Saida esperada**: `templated.py` com `extract_template(amostras) -> Template` (offline) e/ou `encode(linhas, template) -> bytes` (online).

### T03 / EXP-009.3 — Enumerated (dicionario)

**Pergunta**: Quanto reduz se substituir valores comuns por indices
de dicionario?

**Hipotese**: D1/D2 emails (3 dominios em 12 linhas) — dicionario
de dominios reduz substring repetido.

**Sub-perguntas**:
- Dicionario inline ou externo (preambulo)?
- Threshold de cardinalidade vs tamanho de input pra valer a pena?
- Composicao com templated: enumerated opera em UM slot do
  template (ex: dominio dentro do email).

**Saida**: `enumerated.py`.

### T04 / EXP-009.4 — Checked (elide check digits)

**Pergunta**: CPF tem 2 digitos check no final. Se eliminarmos
no encode e regenerarmos no decode, ganhamos quanto?

**Hipotese**: D13 CPF cai mais 18% (2 digitos de 11 totais).

**Sub-perguntas**:
- Como representar CPF "encoded sem check"? Bytes raw? Inteiro?
- Validacao no encode (rejeitar CPF invalido) ou aceitar e regenerar mesmo com check errado original (caso de defeito intencional como D13 tem)?
- Composicao: aplica DEPOIS do templated extract (so' nos slots numericos).

**Saida**: `checked.py` com `elide_cpf(s) -> bytes` etc.

### T05 / EXP-009.5 — Composite (split em sub-valores)

**Pergunta**: Datetime = (date, time, timezone). Decompor em 3 sub-valores cada qual com seu encoder otimiza vs tratar como string?

**Hipotese**: D12 cai pra <40% combinando templated + composite + enumerated (timezone enum) + incremental (date+time).

**Sub-perguntas**:
- Estrutura do split: tupla, dict, lista ordenada?
- Re-juncao no decode preserva format exato (ISO vs space-separated)?
- Composicao com encoder de cada sub-tipo automatizada ou manual?

**Saida**: `composite.py` com decomposition + recomposition.

### T06 / EXP-009.6 — Hierarchical (shared prefix tree)

**Pergunta**: URLs `api/users/123`, `api/users/456`, `api/posts/789` formam arvore. Encoder de arvore reduz vs literal?

**Hipotese**: D3 URLs ja' tem prefix exploited via TCF, mas
explicit tree pode achatar profundidade variavel mais agressivamente.

**Sub-perguntas**:
- Construcao online (1 pass) ou offline (2 passes)?
- Separador hierarquico configuravel (`/`, `.`, `,`)?
- Composicao com templated: hierarchical opera em UM componente
  do template (path), incremental nos numericos finais.

**Saida**: `hierarchical.py`.

### T07 / EXP-009.7 — High-entropy (passthrough)

**Pergunta**: UUID random, hash, base64 random — type encoder ajuda?

**Hipotese**: nao ajuda; documenta-se como "skip".

**Sub-perguntas**:
- Como **detectar** high-entropy automaticamente? Estatistica de
  entropia por linha? Heuristica simples?
- O encoder devolve "no-op" passthrough ou erro?
- Composicao: se 1 slot e' high-entropy (ex: UUID dentro de
  template), os outros slots ainda valem.

**Saida**: `high_entropy.py` com detector + passthrough.

## Track 2 — Camada de algoritmo (estudos)  **— DIFERIDO**

> **Diferido inteiramente (2026-05-15)**: Track 2 nao inicia
> ate' Track 1 (primeira natureza, T01 incremental) validar
> metodologia em dirty. Sub-estudos abaixo documentados como
> roadmap, sem execucao agora. Reavaliacao depois de pelo menos
> 2-3 naturezas Track 1 fechadas.

OBAT (alg16) e HCC (composicional) estao **estaveis e canonicos**
desde welding. Esta fase **nao mexe no canonical** — explora em
dirty se ha' melhorias possiveis, validavel a parte.

### L01 — Comparacao token-level vs byte-level no OBAT

**Pergunta**: OBAT atual compara byte-a-byte em LCP/LCS. Se tokenizar input antes (tokens delimitados por whitespace, `/`, `.`, `-`), as comparacoes ficam mais semanticas?

**Hipotese**: tokens reduzem ruido em datasets com delimitadores estruturais (D3 URLs `/`, D11 datetime `-`/`:`). Mas adiciona overhead em casos sem delimitadores claros (D4 caos).

### L02 — Slot detection online + threshold de similaridade (Estrategia 3.B + extensao)

**Pergunta 1 (slot)**: D9 (`@@@KEY=valueX@@@`) — slot variavel `X`
poderia ser detectado online via anti-unificacao incremental no
proprio OBAT, sem pre-tx externo?

**Pergunta 2 (threshold)**: OBAT atual constroi grafo de
similaridade por **igualdade exata** de substrings (threshold = 0).
E se o threshold pudesse ser > 0 — tolerancia configuravel? Ex:
- threshold "1 dia": datas ate' 1 dia de diferenca compartilham no
- threshold "1 unidade": numericos a distancia <= 1
- threshold "5%": variacoes percentuais
- threshold "edit distance 2": strings similares

**Hipotese**: Generalizando OBAT de **igualdade** pra **distancia**,
podemos:
1. Capturar padroes "fuzzy" que igualdade pura nao pega
2. Conectar diretamente a natureza **lossy-recoverable** (delta de
   erro do canonical) — encoder lossy quase de graca via OBAT
3. Servir de base pra futuro online sem pre-tx explicito

**Conexao com Track 1 (pre-tx)**: o **Stage A (identify)** do staged
pipeline e' precondicao natural — sem saber o tipo, OBAT nao tem
metrica de distancia adequada (data nao se compara como string).

**Risco**: complica OBAT (intocado desde M0). Decisao caso-a-caso.
Parqueado ate' pelo menos 2-3 naturezas Track 1 validadas.

### L03 — Markers tipados (tagged markers)

**Pergunta**: Marker `~` atualmente e' generico. Se for **tipado**
(ex: `~i` incremental, `~e` enumerated, `~t` templated), o detector
pode escolher estrategia diferente pra cada ref.

**Hipotese**: Reduz bytes em datasets multi-padrao (D5) onde
diferentes padroes precisam de tratamento diferente.

### L04 — Composicao tree-based vs left-associative

**Pergunta**: HCC atualmente compoe pares left-associative
(`(((a b) c) d)`). Composicao em arvore balanceada
(`((a b) (c d))`) reduz profundidade de inline expansion?

**Hipotese**: Em datasets com padroes simetricos (D8 prefix/suffix),
tree balance reduz bytes do body.

### L05 — Pre-filter de candidatos ao composicional

**Pergunta**: HCC explora **todos** candidatos para virtual refs.
Pre-filter eliminando candidatos com benefit negativo cedo reduz
custo computacional.

**Hipotese**: Latencia do encoder cai 30-50% sem perda de bytes.
Compressao mesma; tempo melhor.

### L06 — Escape dedutivel (descoberta 2026-05-16)

**Pergunta**: encoder canonical sempre escapa digit-runs com `\`.
Pode-se omitir `\` quando o digit-value > current_node_count
(unambiguous literal, ja' que ref correspondente nao existe)?

**Hipotese**: ganho de 10-18% no `.tcf` final, especialmente na
primeira linha (count=0, todos digits literais sem ambiguidade).

**Princípio subjacente**: [[feedback-abstrato-minimal-materializacao]]
— objetos abstratos sao livres em tamanho; materializacao no .tcf
deve ser minima, omitindo o que pode ser deduzido pelo decoder.

**Implementacao** (proposta):
- Encoder rastreia node_count linha a linha
- Pra cada digit-run literal `N`: se `N > count` no momento → omitir `\`
- Decoder rastreia count similarmente: digit-run bare com value > count e' literal-deduzido

**Validacao**: testado em sub-exp 11 dirty (`11-escape-dedutivel/`).
Roundtrip byte-canonical preservado, savings medidos por dataset.

**Risco**: quebra de compat com decoder v1 atual. Solucoes:
- Versionamento do formato (v1 fixed-escape, v2 dedutivel)
- Migracao gradual com fallback
- Decisao quando sair do dirty pro src/

**Status**: experimentado em dirty (sub-exp 11). Nao welded.

## Ordem de execucao (realinhada 2026-05-15)

**Foco unico:** uma natureza por vez, controle fino, processo refinavel.

1. **Primeira natureza: incremental (datas)** — confirmado 2026-05-15.
   Trabalho em `experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/`.
   Sub-experimentos pequenos, descartaveis/refazaveis, RT obrigatorio.
   Saida esperada: encoder + decoder funcional pra ao menos um
   dataset (provavelmente D11), com hipotese byte-reducao
   confirmada ou refutada. Lecoes para metodologia das proximas.
2. **Apos T01 fechar** (com hipotese confirmada ou explicitamente
   refutada), revisar este ticket. Escolher proxima natureza com
   base em:
   - Gaps identificados em T01 (o que faltou?)
   - Aplicabilidade aos datasets disponiveis
   - Composicao com incremental (qual natureza compoe bem?)
3. **Eventual:** outras naturezas seriais, uma por vez. Track 2
   (estudos camada algoritmo) abre depois de pelo menos 2-3
   naturezas validadas — pra dar massa de dados que justifique
   estudo de OBAT/HCC.
4. **Welding eventual:** decisao **adiada totalmente**. Vai
   depender do desfecho de Track 1 + Track 2 (cf. secao "Visao de
   end-state" e "Riscos").

**Sem ondas paralelas. Sem multi-track simultaneo. Reavaliacao
explicita ao fim de cada natureza fechada.**

## Datasets necessarios

D1-D15 cobrem **maioria** das naturezas. Gaps:

| Nature | Dataset atual | Gap |
|---|---|---|
| Incremental | D6 logs, D10-D12 datas | OK |
| Templated | D1-D2, D3, D8, D13, D14 | OK |
| Enumerated | D1-D2 dominios | OK |
| Checked | D13 CPF | OK |
| Composite | D11, D12 | OK |
| Hierarchical | D3, D7 | OK |
| Lossy-recoverable | — | **D16 floats com tolerancia** |
| High-entropy | D14, D15 random | OK |

**Datasets novos sugeridos** (criar conforme necessidade):
- **D16 floats-tolerantes** — `3.14159`, `3.14` (mesmo dado, precisao diferente). Pra T-lossy.
- **D17 logs-com-incremental** — timestamps + IDs sequenciais misturados. Stress pra composite.
- **D18 enderecos-completos** — rua + numero + bairro + cidade + estado + CEP (templated + hierarchical + enumerated).
- **D19 telefones-internacionais** — `+CC (AA) NNNNN-NNNN` em multiplas geografias (templated + enumerated CC).

Criar conforme necessidade do macro; nao tudo de uma vez.

## Criterios de sucesso

Por sub-fase (T0X / EXP-009.X):

1. **Reducao bytes mensuravel** vs baseline.
   - Baseline = **csv/brotli** (campeao do EXP-008) ou **tcf** (TCF puro) dependendo da nature.
   - Reducao alvo: ≥15% absoluto vs baseline relevante (varia por nature).
2. **RT 100% byte-canonical**: encode + decode reproduz input bit-a-bit.
3. **Latencia tolerable**: < 10x do encoder TCF puro (decoders devem ser ainda mais rapidos).
4. **Composicao funciona**: encoder pode ser **encadeado** com outros encoders sem corrupcao.
5. **Documentacao**: ticket fechado com `notes/conclusoes_TXX.md` + report em EXP-009.X.

## Riscos / questoes abertas

1. **Detecao automatica vs configuracao manual** — em quase todas
   as naturezas, perguntar "o usuario provê a info (qual nature
   aplicar) ou o sistema deduz?". Inicial: **manual**; deduzir
   depois.
2. **Composicao explosiva** — pipeline de 4-5 naturezas em sequencia
   tem espaco de combinacao grande. Como escolher ordem?
3. **Custo de metadata** — cada nature precisa de cabecalho/marker
   no output (qual nature, qual template, qual base). Pra datasets
   pequenos esse custo pode dominar.
4. **D16 lossy-recoverable** — definir matematicamente o que e'
   "tolerable error". Sem definicao, encoder lossy fica subjetivo.
5. **Track 2 toca canonical** — qualquer mudanca real em OBAT/HCC
   precisa **revalidar M14 byte-canonical** (memoria
   [project-macro-M9-stress] e [project-macro-M8-virtual-refs]).
   Nao mudar canonical em dirty; criar **fork** em dirty pra
   experimentar, comparar contra canonical.
6. **Absorcao Track 1 ↔ Track 2 (decisao de welding final)** —
   se L02/L03 mostrarem que natures sao detectaveis durante
   construcao da arvore OBAT, parte do Track 1 fica redundante.
   Mitigacao: **trabalhar so' no dirty enquanto Track 1 e Track 2
   nao tem dados suficientes** pra decidir. Nao criar
   `src/tcf_pretx/` agora — codigo no dirty so' migra pra `src/tcf/`
   quando welding tiver direcao clara (cf. "Visao de end-state").
7. **Risco geral de dirty largar lixo no src/tcf** — apontado
   pelo usuario 2026-05-15. Mitigacao: dirty fica isolado;
   `src/tcf/` so' recebe codigo apos welding deliberado, com
   testes byte-canonical e revisao.

## Tickets filhos a criar

Conforme execucao avanca:

- `T-PRETX-T01` — Macro incremental
- `T-PRETX-T02` — Macro templated
- `T-PRETX-T03` — Macro enumerated
- `T-PRETX-T04` — Macro checked
- `T-PRETX-T05` — Macro composite
- `T-PRETX-T06` — Macro hierarchical
- `T-PRETX-T07` — Macro high-entropy
- `T-LAB-L01` — Estudo token-level
- `T-LAB-L02` — Estudo slot detection online
- `T-LAB-L03` — Estudo markers tipados
- `T-LAB-L04` — Estudo composicao tree-based
- `T-LAB-L05` — Estudo pre-filter

Quando hipoteses se confirmarem em dirty, abrir:

- `T-EXP-009-1` ... `T-EXP-009-7` — sub-experimentos clean
- `T-CODE-PRETX-WELD` — welding das naturezas validadas

## Criterio de aceite (deste meta-ticket)

1. [x] Plano completo registrado
2. [x] Realinhamento 2026-05-15 (foco unico em uma natureza)
3. [x] Dirty lab `2026-05-15-naturezas-e-camada/` criado
4. [x] `experiments/lab/clean/EXP-009-pre-tx-natureza/README.md` (stub, abre quando primeira natureza fechar)
5. [x] `docs/theory/data-natures-taxonomy.md` (taxonomia formal de referencia)
6. [x] **T01 incremental** explorado em dirty (13 sub-exps) — concluido
   que multi-pass viola vertice triplice; abordagem absorvida em
   **Pacote 1 Delta-aware** (welded em EXP-010, 2026-05-17)
7. [x] **Realinhamento pos-T01 (2026-05-19)**: Pacotes 1/3 fechados,
   Pacote 4 em curso. T02-T07 e L01-L05 explicitamente adiados.
8. [ ] **Decisao sobre Pacote 2** (escape deduction): priorizar agora ou
   manter adiado pos-Pacote 4 fechar
9. [ ] **Reabertura T02+** condicionada a casos real-world onde Pacote 1
   + ADR-0008 nao bastem (criterio empirico, nao calendario)

## Conexoes

- Memoria: [feedback-exp-format-for-comparative](../memory/feedback_exp_format_for_comparative.md), [project-teoria-comparacao-modular](../memory/project_teoria_comparacao_modular.md)
- Roadmap: [docs/theory/perspectiva-triplice-e-pre-tx.md](../docs/theory/perspectiva-triplice-e-pre-tx.md)
- EXP-008: [reports](../experiments/lab/clean/EXP-008-compressao-comparada/reports/) (motivacao)
- Dirty antigo: [historia M0-M14](../experiments/lab/dirty/notas/historia-dirty-lab.md) (analogo metodologico)

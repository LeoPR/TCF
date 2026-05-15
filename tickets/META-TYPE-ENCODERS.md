# META-TYPE-ENCODERS — Pre-tx por natureza + estudos da camada de algoritmo

**Status**: OPEN
**Criado**: 2026-05-15
**Estimativa**: multi-semana (provavelmente 4-8 semanas dependendo
de profundidade — varias macros + sub-experimentos clean).
**Escopo**: dois tracks paralelos.

1. **Track 1 (Pre-tx)** — type encoders por **natureza
   comportamental** dos dados (Estrategia 1.A do roadmap perspectiva
   tríplice).
2. **Track 2 (Algoritmo)** — estudos da **camada de comparacao** do
   OBAT (alg16) e da composicao do HCC (Estrategia 3.B e adjacentes).

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

## Visao de end-state (decisao adiada)

O destino final dos resultados de **ambos os tracks** e' modular
dentro de `src/tcf/` formando pipeline `pre → encode` na ida e
`decode → pos` na volta:

```
input → [pre-tx por nature] → encode (OBAT + HCC) → bytes
bytes → decode (HCC + OBAT) → [pos-tx por nature] → output
```

`src/tcf_pretx/` (sibling proposto na fase de experimentacao) e'
**sala de espera** — quando welding fechar, o destino e' como
**modulo do src/tcf/** (ex: `src/tcf/pretx/` + `src/tcf/postx/`
ou unificado `src/tcf/pipeline/`).

**Mas a estrutura final depende do desfecho do Track 2:**

- **Cenario A — Track 1 sustenta valor proprio**: pre-tx por
  nature reduz bytes consistentemente alem do que OBAT/HCC
  conseguem. Welding → `src/tcf/pretx/` como modulo dedicado.

- **Cenario B — Track 2 absorve parte do Track 1**: se L02
  (slot detection online no OBAT) e/ou L03 (markers tipados)
  provarem que **natures podem ser detectadas e aplicadas
  durante a construcao da arvore do OBAT**, partes do Track 1
  ficam redundantes. Slots templated, por exemplo, viram parte
  nativa do OBAT — sem encoder pre-tx dedicado.

- **Cenario C — hibrido (esperado mais provavel)**: algumas
  natures (templated, slot detection) ficam embutidas no OBAT
  via Track 2; outras (incremental delta, checked elide, lossy
  recoverable, composite split) **continuam pre-tx** porque
  exigem semantica externa (saber que e' uma data, que tem digito
  verificador, etc.) — OBAT nao pode deduzir isso da string.

**Decisao adiada ate' o fim da Onda 3.** Antes disso, manter
estrutura experimental conforme decisao 2026-05-15 (sibling
`src/tcf_pretx/`); o welding final aceita refactor.

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

Decisoes registradas (2026-05-15):
- **Dirty lab**: 1 unificado com 2 tracks dentro
- **EXP-009**: meta-pasta com sub-experimentos numerados
- **Code**: `src/tcf_pretx/` separado de `src/tcf/`

```
experiments/lab/dirty/2026-05-15-naturezas-e-camada/
├── README.md                          # entrada + roadmap
├── notas/
│   ├── historia-naturezas-camada.md   # narrativa cronologica
│   ├── conclusoes_T01.md              # 1 por macro fechado
│   └── ...
├── pre-tx/                            # Track 1
│   ├── T01-incremental-base-delta/
│   ├── T02-templated-extract/
│   ├── T03-enumerated-dict/
│   ├── T04-checked-elide/
│   ├── T05-high-entropy-passthrough/
│   ├── T06-composite-split/
│   └── T07-hierarchical-shared/
└── algoritmo/                         # Track 2
    ├── L01-comparacao-token-vs-byte/
    ├── L02-slot-detection-online/
    ├── L03-markers-tipados/
    ├── L04-composicao-tree-based/
    └── L05-pre-filter-candidatos/

experiments/lab/clean/
└── EXP-009-pre-tx-natureza/           # meta-pasta
    ├── README.md                      # indice + status sub-experimentos
    ├── EXP-009.1-incremental/
    ├── EXP-009.2-templated/
    ├── EXP-009.3-enumerated/
    ├── EXP-009.4-checked/
    ├── EXP-009.5-composite/
    ├── EXP-009.6-hierarchical/
    └── EXP-009.7-high-entropy/        # passthrough; mais documentacao que codigo

src/tcf_pretx/                          # pacote irmao (futuro)
├── __init__.py
├── incremental.py
├── templated.py
├── enumerated.py
├── checked.py
├── composite.py
├── hierarchical.py
└── high_entropy.py                    # pass-through helpers
```

EXP-009.7 high-entropy e' **escrito ultimo** (ou logo, dependendo
do criterio); resultado esperado e' "type encoder nao ajuda — pular
encoder, mandar pra compressor direto". Documentar isso pra evitar
re-tentar futuramente.

## Track 1 — Pre-tx por natureza (detalhe por sub-fase)

### T01 / EXP-009.1 — Incremental (base + delta)

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

## Track 2 — Camada de algoritmo (estudos)

OBAT (alg16) e HCC (composicional) estao **estaveis e canonicos**
desde welding. Esta fase **nao mexe no canonical** — explora em
dirty se ha' melhorias possiveis, validavel a parte.

### L01 — Comparacao token-level vs byte-level no OBAT

**Pergunta**: OBAT atual compara byte-a-byte em LCP/LCS. Se tokenizar input antes (tokens delimitados por whitespace, `/`, `.`, `-`), as comparacoes ficam mais semanticas?

**Hipotese**: tokens reduzem ruido em datasets com delimitadores estruturais (D3 URLs `/`, D11 datetime `-`/`:`). Mas adiciona overhead em casos sem delimitadores claros (D4 caos).

### L02 — Slot detection online (Estrategia 3.B)

**Pergunta**: D9 (`@@@KEY=valueX@@@`) — slot variavel `X` poderia
ser detectado online via anti-unificacao incremental no proprio
OBAT, sem pre-tx externo?

**Hipotese**: Se SLOT for marcador nativo do OBAT, alguns datasets
viram trivialmente compactos sem precisar de templated encoder
externo.

**Risco**: complica OBAT (intocado desde M0). Decisao caso-a-caso.

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

## Ordem de execucao

### Onda 1 (2-3 semanas) — primeiros macros

1. **T01 incremental** — datas / timestamps. Dataset abundante.
   Mecanismo conceptualmente simples. **Boa primeira hipotese pra testar metodologia.**
2. **T02 templated** — CPF / UUID. Conceito central; valida tooling
   de template extract.
3. **L05 pre-filter** — paralelo. Estudo de algoritmo de baixo risco
   (nao muda saida, otimiza tempo).

### Onda 2 (3-4 semanas)

4. **T03 enumerated** — dicionario simples; depois de T02
   (composicao com slots).
5. **T04 checked** — depois de T02 (opera em slots numericos).
6. **T05 composite** — depois de T01+T02+T03+T04 (compose elas).
7. **L01 token-level** — paralelo.

### Onda 3 (3-4 semanas)

8. **T06 hierarchical** — depois de T02 (opera em sub-componente path).
9. **T07 high-entropy** — paralelo, mais documentacao que codigo.
10. **L02 slot online** — pode ate' substituir parte do T02 se
    se mostrar viavel.
11. **L03/L04 markers tipados + tree composicao** — explorar.

### Onda 4 — consolidar

12. **Welding** das naturezas validadas → `src/tcf_pretx/`.
13. **EXP-009.* clean** finalizando cada nature com baseline byte-canonical.
14. **Cross-comparison** — pipeline composto rodando em todos D1-D15 + datasets novos. Report final consolidado.

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
   Decisao adiada ate' fim da Onda 3:
   - Cenario A: src/tcf_pretx/ → `src/tcf/pretx/` (Track 1 sustenta valor)
   - Cenario B: natures embutidas no OBAT (Track 2 absorve)
   - Cenario C (esperado): hibrido — natures que dependem de
     semantica externa (incremental, checked, lossy, composite)
     ficam pre-tx; natures estruturais (templated, slot) sobem
     pro OBAT.
   - Risco: comecar a weldar Track 1 antes de ver Track 2 evolve;
     refactor depois pode ser caro. Mitigacao: **nao fazer
     welding final antes de ter dados das duas tracks**.

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

1. [x] Plano completo registrado (este documento)
2. [ ] Dirty lab `2026-05-15-naturezas-e-camada/` criado com:
   - [ ] `README.md` entrada
   - [ ] `notas/historia-naturezas-camada.md` (stub, preencher conforme avanca)
   - [ ] subpastas `pre-tx/` e `algoritmo/` vazias (cada macro cria sua propria pasta)
3. [ ] `experiments/lab/clean/EXP-009-pre-tx-natureza/README.md` (meta-pasta indice)
4. [ ] `docs/theory/data-natures-taxonomy.md` (taxonomia formal — ja' bom o suficiente neste ticket por enquanto; mover quando crescer)
5. [ ] Pelo menos **Onda 1** (T01, T02, L05) completa antes de revisar plano
6. [ ] Re-revisao do plano apos cada onda — naturezas adicionais/divisoes podem emergir

## Conexoes

- Memoria: [feedback-exp-format-for-comparative](../memory/feedback_exp_format_for_comparative.md), [project-teoria-comparacao-modular](../memory/project_teoria_comparacao_modular.md)
- Roadmap: [docs/theory/perspectiva-triplice-e-pre-tx.md](../docs/theory/perspectiva-triplice-e-pre-tx.md)
- EXP-008: [reports](../experiments/lab/clean/EXP-008-compressao-comparada/reports/) (motivacao)
- Dirty antigo: [historia M0-M14](../experiments/lab/dirty/notas/historia-dirty-lab.md) (analogo metodologico)

---
title: T-CODE-TCF8H-WELD — weld do codec hierárquico #TCF.8H no src/tcf (feature do .8)
status: open
priority: P1
created: 2026-07-13
updated: 2026-07-13
gate: capability
blocked-by: []
related:
  - tickets/T-STUDY-HIERARCHICAL-TCF.md
  - tickets/T-FMT-TCF8H-HEADER.md
  - docs/adr/0031-hierarchical-discriminator-H.md
  - experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/
  - experiments/lab/dirty/2026-07-13-dataseth-json-bridge/
  - experiments/lab/dirty/notas/dataseth-hierarquia-completa-plano.md
  - tests/test_real_world_snapshots.py
  - src/tcf/decoder.py
---

# T-CODE-TCF8H-WELD — promover o codec hierárquico para o core

**[dispositivo→exec]** Decisão do owner (2026-07-13, reescopo `.8` = feature-complete "1.0"): a
**hierarquia / DatasetH (`#TCF.8H`)** entra no `.8` como a expansão de capacidade do 1.0.
Este ticket é o **weld** do codec — promover o protótipo validado para `src/tcf`, sob aprovação
explícita e o gate de CAPACIDADE (não o gate de compressão).

JSON é a primeira fonte do caminho de pesquisa, não a API do core. O codec deve receber o DatasetH
definido no estudo e não deve criar `encode_json` nem importar parser JSON em `src/tcf`.

## Ponto de partida (o que já está pronto)

- **Char `H` reservado** no discriminador `#TCF.8` (ADR-0031, `accepted`): `H` = multi-col hierárquico,
  especialização de `M`, **sem-espaço** (`#TCF.8H<meta>`), dispatch O(1) no decode.
- **Regras de header decididas** (T-FMT-TCF8H-HEADER, `closed-decided`): `M` implícito, **omit-closes**
  (o `\n` do header auto-fecha grupos abertos → dropa `}`/`]` final, RT-exato, −1B), última-folha-sem-size,
  colchetes `{}`=objeto / `[]`=array, cardinalidade/multiplicidade **deduzidas** (não escritas).
- **Codec protótipo limitado**: `experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/codec.py`
  (self-contained, **não toca `src/`**) tem RT exato apenas nas amostras all-string S4/S6 e C1.
  Ele prova a notação inicial, não o contrato de um JSON total nem a independência da fonte. O guarda-chuva
  de pesquisa é T-STUDY-HIERARCHICAL-TCF (P1–P9, `confirmada-conceitual`).
- **Produção hoje**: `src/tcf/decoder.py` só **reserva + fail-loud** o `H` (não decoda). Zero codec no core.

## Update 2026-07-14 — arquitetura em 3 CAMADAS (reframe do owner) + codec base

Owner: o weld deve respeitar 3 camadas desacopladas
([tcf-camadas-arquitetura.md](../experiments/lab/dirty/notas/tcf-camadas-arquitetura.md)):
- **L1 compressor de COLUNAS** — o mesmo p/ single/multi/hierarquia/multi-tabela; **REUSAR o
  `encode`/`decode` de coluna do core SEM tocá-lo**. O hierárquico é 100% CLIENTE dele.
- **L2 RELACIONAMENTO entre colunas** — a natureza do vínculo (multi-col, hierarquia, ragged, N:N).
  Vive no HEADER; **só a descrição no header já reconstrói o dataset**, independente da compressão.
  Módulo NOVO (`src/tcf/hierarchical.py`), aditivo.
- **L3 OTIMIZAÇÃO pelo relacionamento** — deduções (count, omit-closes, projeção tabelão×nível-aware).
  Passe opt-in; tirar L3 e ainda reconstrói (só maior).

Por isso o weld é **aditivo e de baixo risco**: flat byte-idêntico; hierárquico = cliente do
compressor + dispatch por `H`. **Codec base** (extrair a ideia, não copiar): `shred.py` do lab
[2026-07-14-0111-hierarquico-fechar-fluxo](../experiments/lab/dirty/2026-07-14-0111-hierarquico-fechar-fluxo/)
— blocos + `#count`, RT-exato nos clássicos de transmissão (cadastro c/ 2 listas irmãs, pedido
aninhado, telemetria; arrays vazios; ambiguidade resolvida). Supera o EXP-015 (múltiplas listas irmãs).

## Gate de CAPACIDADE (não é ≥15% de compressão)

Hierarquia **não** é otimização de bytes — é **representar dado que a tabela plana não representa**
(1:N, objeto-em-objeto, arrays). Logo o gate ≥15%/2-reais (que rege weld de nature/otimização) **não se
aplica**. O gate de aceite deste weld é:

1. **RT-exato do DatasetH**: o gate do core é `decode(encode(dataset_h)) == dataset_h`, sem importar JSON
  nem depender da origem. O primeiro adaptador de prova é JSON: `json -> DatasetH -> TCF.H -> DatasetH -> json`,
  com ≥3 documentos aninhados reais/realistas (pessoa⊃endereço⊃geo + telefones[]; pedido⊃itens[];
  org⊃deptos[]⊃membros[]). A comparação deve preservar a semântica definida pelo DatasetH, incluindo
  ordem, tipos, presença, `null`, vazios e repetição.
2. **Non-regressão do flat**: `test_core_rt` + `test_regression_v1_baseline` + `test_real_world_snapshots`
   **inalterados** (D1-D9=1523B, D17a=300B, real-world=89616B). O caminho `#TCF.8M`/single/órfão não muda
   **1 byte**. Hierarquia é aditiva (dispatch por `H`).
3. **Aprovação explícita de `src/tcf`** (invariante do projeto) para cada arquivo tocado.

## WELD 2026-07-14 — 1º INCREMENTO (classe coberta) FEITO, gate verde

**[dispositivo→feito]** Owner deu o go ("vamos fazer o weld"). Weld ADITIVO em 3 camadas:
- **`src/tcf/hierarchical.py`** (NOVO, L2/L3): shredding em blocos + `#count`; header sem-espaço
  `#TCF.8H<meta>` (ADR-0031); `{}` 1:1 · `[]` 1:N · counts · última-sem-size · omit-closes.
- **`src/tcf/decoder.py`**: o branch `H` (era fail-loud reservado) agora **roteia** p/
  `decode_hierarchical` — dispatch O(1). `M`/single/órfão INTACTOS.
- **`src/tcf/__init__.py`**: exporta `encode_hierarchical`; `decode()` auto-roteia pelo magic.
- **L1 REUSADO sem tocar**: o hierárquico é cliente de `encode(coluna)`/`decode(body)`.

**Gate verde**: suíte **646 passed, 2 skipped** (12 testes hierárquicos novos em
`tests/test_hierarchical_rt.py`). **Flat BYTE-IDÊNTICO** (D1-D9=1523, D17a=300, real-world=89616
pinados passaram). RT-exato nos clássicos de transmissão: cadastro (2 listas irmãs + endereco{geo}),
pedido aninhado, telemetria, arrays vazios, ambiguidade de chave (count resolve).

**Cobre** (classe coberta): uma raiz, chaves UNIFORMES por nível, `{}`/`[]` recursivos, arrays vazios.
**Fail-loud / próximos incrementos**: objetos **ragged** (chave faltando → máscara def-level, peça 11);
**tipos**/`null` (tudo string; camada ortogonal); **N raízes**; **N:N/snowflake** (FK, super-hierarquia
H-HIER-MULTITABELA-01). ADR de weld + reconciliação final = W5 (pendente).

Fases W abaixo: **W2/W3 FEITOS** (classe coberta); **W4 gate verde** p/ a classe; W0/W1 cobertos pelos
labs (records = DatasetH source-agnostic, list[dict]); **W5 (ADR + ragged/tipos)** pendente.

## FIXAR O ÓBVIO 2026-07-14 — fuzz EM MASSA da classe coberta (óbvio fechado)

**[probatório]** Owner: *"fixar o óbvio primeiro. fechar, testar em massa e ir fechando os outros."*
Lab [`2026-07-14-2120-hierarquia-massa-classe-coberta`](../experiments/lab/dirty/2026-07-14-2120-hierarquia-massa-classe-coberta/):
fuzz DETERMINÍSTICO (seed 20260714) de **8000 documentos** aleatórios DENTRO da classe coberta →
RT byte-exato `decode(encode_hierarchical(recs))==recs`: **8000/8000, 0 falhas**. Cobertura: 5263
arrays vazios · 2379 ≥2 arrays irmãos · 1609 aninhados. → A **classe coberta está FIXADA** (fuzz +
clássicos pinados em `tests/test_hierarchical_rt.py`). Candidato a promover a property-test seedado
em `tests/` (guarda permanente). Estudo L3 (multiplicidade) de-firmado como HIPÓTESE (bloco de
otimizações, deixado pro fim) — lab `2026-07-14-2043`. Próximos INCREMENTOS de funcionalidade abaixo;
**`null`/tipos ficam pro FIM** (decisão do owner 2026-07-14).

## Plano (fases)

- [x] **W0 — contrato do DatasetH**: `records = list[dict]` source-agnostic (JSON é adapter, não contrato).
  Folhas string; `{}` 1:1; `[]` 1:N; classe coberta = schema uniforme. `null`/tipos/ragged/N-raízes/N:N =
  fail-loud (fronteira registrada no ADR-0033). FEITO (labs + ADR-0033).
- [x] **W1 — pesquisa de adaptadores**: DatasetH sem JSON provado (records nativos); labs cobriram o
  caminho. FEITO.
- [x] **W2 — codec externo**: shredding em blocos + `#count` (labs `2026-07-14-0111`); ideia extraída, não
  copiada. FEITO.
- [x] **W3 — dispatch no core**: `decoder.py` roteia `H` → `decode_hierarchical` (O(1)); `M`/single/órfão
  intactos. FEITO (commit a20ddf7).
- [x] **W4 — gate de capacidade**: RT dos clássicos + bordas + fuzz seedado (1200) em
  `tests/test_hierarchical_rt.py`; lab `2026-07-14-2120` roda 8000/8000; flat byte-idêntico; suíte 647
  passed. FEITO.
- [x] **W5 — docs e weld**: **ADR-0033 FEITO** (weld welded 2026-07-14, indexado). **`src/tcf` APROVADO
  arquivo-a-arquivo pelo owner (2026-07-15)** — aprovação condicionada à ESTABILIDADE, demonstrada pelo teste
  em massa com dado real (TPC-H aninhado, RT byte-exato estável em volume, lab `2026-07-14-2231`). 3 arquivos:
  `hierarchical.py` novo + 2 linhas em `__init__.py` + ramo `H` em `decoder.py`. README/referência de formato
  do `H` = pendente (entra no F6/docs do release). Otimização/decouple de L3 = `.9` (não soldar demais).

## Riscos

- **Codec novo no core** = maior risco desde os welds de formato. Mitigar: aditivo (dispatch por `H`),
  flat 100% intacto, gate de non-regressão duro.
- **Topologia e bordas** (array-in-array, N-raízes, link posicional / Dremel rep-level): pertencem ao
  contrato do DatasetH e ao codec, não ao adaptador JSON isoladamente. Devem ser classificadas em W0-W2;
  o que ficar fora do domínio entra como fail-loud explícito.
- **Tipos**: o H não herda a coerção do flat. A representação tipada, `null` e presença devem ser
  definidos no DatasetH antes de escolher tags ou deduções no header.

## AUDITORIA ADVERSARIAL 2026-07-15 — BUGS R0-class no header do `H` (repro pinado)

**[probatório→preempção]** Workflow de auditoria (4 lentes + síntese) sobre o estudo de amostragem
honesta encontrou — e os probes verificaram
([lab 2336/probes_auditoria.py](../experiments/lab/dirty/2026-07-14-2336-hierarquia-amostra-populacao-honesta/probes_auditoria.py)) —
**nomes de chave com chars da gramática do meta quebram RT** (entrada que o encoder aceita →
critério 1 da regra de ROI do T-REL-08, preempta):

| entrada | comportamento HOJE | classe |
|---|---|---|
| nome com `,` | **corrupção SILENCIOSA** (`{'c,d':'2'}` → `[{'c':'2','d':'2'}]`) | pior |
| nome com `{` | **corrupção SILENCIOSA** (objeto fantasma `{'i':{'j':...}}`) | pior |
| nome com `[` | **HANG** no parse do meta (classe BUG-12) | pior |
| nome com `:` / `#` | fail-loud TARDIO (no decode, erro confuso) | médio |
| espaço / `\` em nome; `\t`/`\x00` em valor; vazios | RT-OK (robustos) | — |
| `\n` em valor | fail-loud CLARO do core (contrato pendente, boundary) | ok |

**Causa**: `_build_meta` emitia nomes CRUS; `_parse_meta` cortava nome em `,[]{}:#`. O header plano
`.8M` já **escapa nomes com `\`** (T-FMT-NAME-ESCAPING) — o `.8H` nasceu sem portar o escaping.
**FIX WELDED (aprovado pelo owner, commit `40a7e10`)**: escaping portado (`_esc_name`/`_unesc_name`
estrito + `nm()` escape-aware + `_rstrip_closes` que preserva closers ESCAPADOS no omit-closes).
Red→green: 14 nomes adversariais parametrizados + interações árvore/omit-closes + fail-loud claro
p/ nome vazio e `\n`-em-nome; fuzz agora gera ~25% nomes adversariais. **Suíte 666 passed**, pins
flat byte-canônicos verdes; probes 13/13 conforme esperado (nomes RT-OK; `\n`-em-valor segue
fail-loud claro do core, contrato boundary pendente). Wire: nomes sem chars especiais ficam
byte-idênticos (sem regressão de blob válido).
Correções de rotulagem do estudo (ESTRUTURAL→robusto-a-valores; br-identidades é 1:N puro fan-out
1.03, não N:N; N:N é INEXPRESSÁVEL no contrato, não "fail-loud") já aplicadas no result do lab 2336.
Probes de dado real pendentes registrados: receita-cnpj matriz→filiais (hub pronto) e
online-retail InvoiceNo→itens (precisa build).

## PRÓXIMOS INCREMENTOS — roadmap de paridade JSON (2026-07-15)

O que falta pra fechar "hierarquia" (amplo) foi consolidado em
[T-CODE-TCF8H-JSON-PARITY](T-CODE-TCF8H-JSON-PARITY.md): critério = RT lossless de qualquer JSON
real (fundamento do owner). Ordem: **P1 presença/ragged → P2 tipos → P3 null → P4 rep-level** +
congelar contratos de borda; depois a capacidade EXCLUSIVA (shared-ref/grafo, além do JSON). O
escape ganhou ticket de estudo próprio ([T-FMT-ESCAPE-COMBINATORIAL-STUDY](T-FMT-ESCAPE-COMBINATORIAL-STUDY.md)).

## PRÓXIMO — teste em massa via shaper (owner 2026-07-14, "depois de fechar os tickets")

**[probatório, planejado]** Owner: *"depois precisamos de um teste em massa disso, nem que o esquema
hierárquico venha do shaper montando pra gente nosso dataset de teste."* O fuzz sintético (2120) já cobre
a forma; falta **dado REAL em massa**. Plano ancorado:
- **Fonte**: hub `Z:/tcf-data/interim/tpch-sf001.db` (e `tpch-sf01.db` p/ escala). FK real dá cadeia
  pai→filho: `customer` (c_custkey) ← `orders` (o_custkey) ← `lineitem` (l_orderkey). Cadeia 1:N em 2 níveis.
- **Bridge**: o shaper ACHATA (join.py); aqui é o INVERSO — usar modo `normalized` + metadata de FK pra pegar
  as tabelas separadas e **aninhar** (group filhos sob o pai pela FK) → documentos hierárquicos reais.
- **Coerção**: classe coberta = all-string; `str()` em todas as folhas ANTES (input == decode output). Sem
  ragged (schema uniforme por tabela). Nulls → decidir (parte da família `null`, deixada pro fim) ou
  stringificar p/ o teste de topologia.
- **Gate**: RT byte-exato `decode(encode_hierarchical(docs)) == docs` em massa + invariantes estruturais
  (contagens de filhos preservadas) + byte-determinismo. Adversarial: caçar corrupção silenciosa.
- Vive em lab dirty (`inputs/`+`intermediates/`+`outputs/`, extensões reais); NÃO toca `src/tcf`.
- **FEITO 2026-07-14/15** (labs `2026-07-14-2231` massa + `2026-07-14-2336` amostra honesta 18/18
  estratos). O aninhamento foi feito À MÃO nos labs; capacidade nativa no Shaper registrada em
  [T-SHAPER-NESTED-OUTPUT](T-SHAPER-NESTED-OUTPUT.md) (ferramental até 1.0, não bloqueia .8).

## Critério de aceite

- [x] DatasetH definido e independente de JSON (`records=list[dict]`); segunda origem (records nativos) comprova.
- [x] `decode(encode(dataset_h)) == dataset_h`, com fixtures (clássicos + fuzz seedado) committadas e RT/non-regressão pinados.
- [~] `src/tcf` **revisão apresentada** arquivo-a-arquivo; flat byte-idêntico ✅. Aprovação final = owner (cauteloso em mexer agora).
- [~] Fronteira de tipos/bordas: classe coberta decidida + fail-loud registrado (ADR-0033). `null`/tipos/ragged = próximos incrementos (cruzam T-API-BOUNDARY-CONTRACTS), deixados pro FIM.
- [x] ADR de weld: **ADR-0033** (a gramática do meta-árvore consolidada; consome T-FMT-TCF8H-HEADER).
- [ ] **Teste em massa via shaper** (dado real TPC-H aninhado) — planejado acima, próximo passo.

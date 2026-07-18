---
title: T-API-BOUNDARY-CONTRACTS — contrato flat e fronteira DatasetH
status: closed
priority: P1
created: 2026-07-10
updated: 2026-07-17
gate: .8
blocked-by: []
related:
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-FMT-OMIT-OR-DECLARE.md
  - src/tcf/encoder.py
  - src/tcf/multi/core.py
---

# T-API-BOUNDARY-CONTRACTS — contrato flat e fronteira DatasetH

**[dispositivo→registro]** Direção do owner (2026-07-10, ao aprovar o lote 3 do T-QA-8 F0):

> "o núcleo trabalha com strings mas tem algumas coisas relacionadas com anterior e próximo,
> diferença etc... tem também as questões dos specs. mas vamos tratar essas fronteiras primeiro,
> já pra ter os isolamentos. O código tendo tratamento pode identificar eles e a gente pode mudar
> comportamento. [...] faça um ticket pra inspecionar melhor no futuro, antes de terminar o 1.0."

Ou seja: os fail-louds/conversões do lote 3 são **ISOLAMENTO** — cada caso agora é identificado
num ponto único do código, então mudar o comportamento depois é trocar UMA decisão, não caçar
corrupção espalhada. Este ticket guarda a lista do que re-inspecionar **antes de fechar o 1.0**.

## O que ficou isolado no lote 3 (estado atual = fail-loud/converte; re-decidir aqui)

| caso | hoje (lote 3) | questão aberta pro 1.0 |
|---|---|---|
| BUG-08: meta vazio + body vazio | ValueError (não-emitível) | semântica de VAZIO no formato (junto com 0-rows/O-FMT-20: registro-'0' schema-declare pra append/parquet/tcfx) |
| BUG-09: str/bytes como valor de coluna | TypeError que ensina | aceitar iteráveis não-list (tuple? generator? numpy?) — contrato de container |
| BUG-10a: não-str em list | converte via `_to_str` (= dict, None→'') | conversão é a semântica certa pro núcleo-de-strings? tipos com relação anterior/próximo (deltas, cadência) e specs numéricos podem querer o VALOR TIPADO, não a str — cruzar com META-TYPE-ENCODERS/H-TYPE |
| BUG-10b/c/d: layers/parallel/decode tipos | TypeError/ValueError na porta | — (estável) |
| BUG-10c: parallel=1 | serial deduzido (sem pool) | ok; rever se paralelismo intra-coluna (V2-J) mudar o contrato |
| BUG-10e: name= sem nature | ValueError | name deveria existir sem nature (rotular single-col órfão)? exigiria header — decisão de formato |
| BUG-10f: stamp+dict | ignorado (M já é magic) — documentado | — |
| BUG-10g: nature=+dict / nature_per_col=+list | ValueError cruzado | unificar num kwarg só (`nature=` aceitando spec OU dict)? decode tem a MESMA assimetria calada (decode(single, nature_per_col=) ignora) — alinhar |
| tuple como valor de coluna | aceito (len+iter funcionam) | formalizar ou rejeitar |
| parallel= com list | ignorado calado | warning? single-col paralelo não existe |
| spec customizado fora do `SPEC_REGISTRY` | header `:id` exige `decode(..., nature=spec)` ou `nature_per_col` com `spec.name == id`; registry core vence | decidir antes do 1.0 se haverá registry carregável; nunca inferir spec por forma |

## REFOCO 2026-07-13 — contrato flat congelado; DatasetH em pesquisa

O reescopo `.8`=feature-complete (2026-07-13) congela o contrato da tabela flat, mas não transforma a
coerção de strings em contrato do DatasetH. JSON e outras fontes entram por adaptadores externos; a
semântica hierárquica vive no estudo [T-STUDY-HIERARCHICAL-TCF](T-STUDY-HIERARCHICAL-TCF.md) e no weld
[T-CODE-TCF8H-WELD](T-CODE-TCF8H-WELD.md). As bordas abaixo são o que a fronteira flat observa hoje e o
que o estudo precisa comparar:

| borda de origem hierárquica | comportamento MEDIDO na tabela flat | decisão para DatasetH/H |
|---|---|---|
| `null` (≠ `""` ≠ ausente) | `None` coage para `''` no flat | DatasetH deve distinguir `null`, vazio e ausência; representação ainda em pesquisa |
| tipos escalares (number/bool) | converte para strings; `123` e `"123"` podem colidir | DatasetH deve preservar tipo e valor segundo contrato semântico; não decidir por `str()` |
| registros ragged (keys diferentes por objeto) | tabela exige colunas alinhadas e pode falhar | DatasetH precisa de presença/definition level ou equivalente |
| `\n` dentro de valor | `ValueError` (LF delimita linhas) | H precisa de framing próprio; não herdar a delimitação flat sem teste |
| `""` vazio vs coluna vazia | `''` é valor; coluna/registro vazio tem restrições do flat | DatasetH deve testar vazios de folha, objeto e array separadamente |
| **chave repetida** (estudo 2026-07-17, lab `0050`) | inexpressível no MODELO (dict colapsa antes do encode); wire estrangeiro c/ coluna duplicada → `HierarchicalError` (hardening P4a). Texto JSON estrangeiro c/ duplicata = origem fora do contrato (com chaves str o modelo NUNCA emite duplicata — medido) | **manter fail-loud** (revisão: escolha limpa, não engessada — toda alternativa perde calado ou colide, provado). Políticas last-wins/collect/pares = opt-in de ADAPTADOR (gadget), nunca do core. Ver [json-chave-repetida-levantamento](../experiments/lab/dirty/notas/json-chave-repetida-levantamento.md) |
| **erros CRUS na borda do `.8H`** (medidos 2026-07-17) | `\n` em valor → **`ValueError` cru** (herdado do flat); lone surrogate `"\ud800"` → **`UnicodeEncodeError` cru**; chave int/bool → **`TypeError` cru** | re-tipar os 3 p/ `HierarchicalError` que ensina — **sem afrouxar** (rejeitar está certo: nos 3 o json é que é permissivo demais — ver [perfil-json-like](../experiments/lab/dirty/notas/perfil-json-like-condicoes-parametro.md) §1C) |
| **chave NÃO-string** (achado 2026-07-17, mesmo lab) | `.8H` REJEITA (certo — evita o furo da coerção: `json.dumps({1:'x','1':'y'})` emite DUPLICATA e o RT perde calado), mas: `{1:...}`/`{True:...}` → **TypeError CRU** ("argument of type 'int' is not iterable"); `{None:...}` → `HierarchicalError` com mensagem **enganosa** ("nome de campo vazio") | declarar regra "chave de objeto = str" no contrato DatasetH; re-tipar o TypeError p/ `HierarchicalError` que ensina (quando aprovado mexer) |
| **ordem de chaves em ragged** (achado 2026-07-17, suíte de controle) | `.8H` devolve chaves na ordem do SCHEMA (união por 1ª aparição): chave opcional que estreia após o 1º registro volta ao FIM do dict. Igualdade semântica (dict) preservada; byte-igualdade do `json.dumps` NÃO. Mínimo: `[{a,c},{a,obs,c}]` → reg. 2 volta `[a,c,obs]`. Pinado em `test_ordem_de_chaves_ragged_e_do_schema` | decidir contrato: declarar ordem-do-schema como canônica OU preservar ordem por-registro (custo de wire). O contrato S0 do DatasetH (lab 2026-07-16-1708) preserva por-registro — gap S0×`.8H`; decisão junto do S6/P4b |

**Tabela do lote 3** (BUG-08..10g abaixo): cada linha ganha uma decisão **manter/mudar** registrada,
com teste de contrato. A maioria continua sendo contrato do núcleo de strings. Ela não decide o DatasetH;
as exceções estruturais são investigadas no estudo antes de qualquer weld em `src/tcf`.

> A hierarquia **não herda automaticamente** a coerção flat. O contrato compartilhado é o round-trip da
> estrutura aceita; DatasetH e tabela flat são fronteiras distintas.

## Por que não decidir agora (SUPERSEDED 2026-07-13 — mantido por histórico)

Pre-1.0 o custo de mudar é zero (git-as-compat, ADR-0024) e o material comprobatório (T-QA-8)
ainda vai revelar o que os usos reais pedem. As questões de TIPO (anterior/próximo, diferença,
specs) dependem do rumo do META-TYPE-ENCODERS — decidir contrato de container antes disso seria
chute.

## LIMITAÇÕES INERENTES do wire `.8H` (auditoria P4a 2026-07-16 — registrar, indetectável sem checksum)

Formas de adulteração de blob que são **indistinguíveis por construção** de um blob canônico de
OUTRO documento (a informação não existe no wire; detecção = trilha checksum/tcfx, pré-1.0):
1. **Meta truncado até forma canônica string**: cortar `:size<tag>` inteiro da última coluna de dado
   (ex.: `m#:3[#:8[]:8n` → `m#:3[#:8[]`) produz um meta VÁLIDO de schema all-string — ints decodam
   como strings sem erro. (Cortes PARCIAIS são detectados: size-explícito-na-última-string e tag
   truncada = fail-loud desde 2026-07-16.)
2. **Truncamento de cauda unsized**: a última coluna sem size absorve o que restar; perda parcial do
   fim do corpo em coluna única/unsized não é detectável (herdado do omit-size; declarado no P1).
3. **`]` deletado em arr_objects no FIM do meta** (omit-closes torna o fim-de-meta fechamento válido) —
   pode re-bindar campos irmãos pra dentro do array em metas específicos.
4. **Bytes apendados quando a última coluna é unsized** (single-column string): viram conteúdo da
   coluna (registro fantasma). Com última coluna SIZED, apêndice é rejeitado (guard 2026-07-16).
5. **Troca de root-kind `#V`↔`#O`** (P4b, auditoria 2026-07-17): o wire mutado é o wire CANÔNICO
   de outro documento legítimo (`V` vs `{"": V}`) — indistinguível por construção. Idem qualquer
   1-char-flip que produza kind válido com meta compatível.
6. **Truncamento do PRÓPRIO magic**: o prefixo truncado (`#TCF.`) cai no contrato ÓRFÃO do flat
   (qualquer texto = coluna única, discriminador 0 B — ADR-0029/0031). Herdado do desenho do
   órfão, não do P4b.

## PASSADA DE CONGELAMENTO 2026-07-17 (gate `.8` — decisão manter/mudar, MEDIDA)

Comportamento **medido hoje** (o código evoluiu desde julho) e decidido caso a caso. Regra-mestra
do reescopo: **contrato flat CONGELADO** (ADR-0024, custo de mudar depois = 0). Default = **MANTER**
com teste que pina; assimetrias de ergonomia (não-corrupção) viram follow-up pré-1.0.

| caso | medido 2026-07-17 | decisão | teste |
|---|---|---|---|
| BUG-08 vazio (0-rows) | `encode([])`/`encode({})`/`encode({'a':[]})` → ValueError; **`['']` (1 linha) faz RT**; `decode('#TCF.8\n')`→`['']` | **MANTER** — fronteira ≥1 linha; 0-rows/registro-'0' é O-FMT-20 (trilho armazenamento, não `.8`) | `TestBug03ZeroRows` |
| BUG-09 str/bytes como dados/coluna | TypeError que ensina | **MANTER** | `test_str/bytes_as_column_value_raises` |
| BUG-10a não-str em list | converte via `str()` (int→RLE, `None`→`''`, `True`→`"True"`, dict→`str`) — **string-core**; tipagem JSON vive no `.8H` (`"true"`) | **MANTER** — a coerção É a semântica do núcleo de strings (o `.8H` é a fronteira tipada) | `test_list_nonstr_items_convert_like_dict` |
| BUG-10b/c/d layers/parallel/decode | TypeError/ValueError na porta | **MANTER** (estável) | `test_layers/parallel/decode_*` |
| BUG-10e name= sem nature | ValueError | **MANTER** | `test_name_without_nature_raises` |
| BUG-10f stamp+dict | ignorado (M já é magic) | **MANTER** (documentado) | — |
| BUG-10g nature/nature_per_col cruzados (encode) | ValueError cruzado | **MANTER** | `test_nature*_raises` |
| **tuple** como valor de coluna vs tabela inteira | coluna → **aceito** (converte); topo → **TypeError** | **MANTER** (assimetria INTENCIONAL: topo = shape do contrato `list\|dict`; valor de coluna = container de str) | `test_tuple_como_*` (novos) |
| **decode(single, nature_per_col=)** | **ignorado calado** (mesma saída) | **MANTER** p/ `.8` (não corrompe); alinhamento = follow-up | `test_decode_nature_per_col_em_single_*` (novo) |
| **parallel=True em single-col** | serial silencioso (byte-idêntico) | **MANTER** (single não tem pool) | `test_parallel_true_em_single_*` (novo) |
| spec fora do `SPEC_REGISTRY` | `:id` exige `spec.name==id`; registry vence; nunca inferir por forma | **MANTER** | `test_natures.py` |

**Follow-ups pré-1.0 (registrados, NÃO bloqueiam `.8`)**: (a) `decode` alinhar simetria de kwargs
(hoje `nature_per_col=` em single-col é no-op silencioso — encode RAISES no cruzado, decode não);
(b) `parallel=`/`name=` em single-col poderiam emitir `UserWarning` (hoje no-op); (c) `tuple` no topo
poderia ser aceito (hoje TypeError) SE o contrato de container for relaxado — cruza com BUG-09.
Nenhum é corrupção; todos custam 0 pra mudar depois (pré-1.0).

## Critério de aceite

- [x] Passada única revisando a tabela acima, caso a caso, com decisão registrada (manter/mudar) e
  testes de contrato — **FEITA 2026-07-17** (todas MANTER; 3 assimetrias novas pinadas; 63 passed
  em `test_f0_boundary_fixes.py`).
- [x] Simetria encode/decode conferida — decode só tem `(nature, nature_per_col)`; `nature_per_col=`
  em single-col é **no-op silencioso** (medido e pinado); demais kwargs de encode não existem no
  decode (TypeError). Alinhamento = follow-up (a) acima.
- [x] Cruzado com T-FMT-OMIT-OR-DECLARE (vazios → O-FMT-20/registro-'0', fora do `.8`) e
  META-TYPE-ENCODERS (BUG-10a: string-core vs `.8H` tipado — fronteiras distintas, ambas registradas).
- [x] DatasetH: as bordas hierárquicas (null/tipos/ragged/`\n`/`""`/CR/chave-repetida/ordem-de-chaves)
  foram TODAS resolvidas ou decididas nos welds 2026-07-17 (escape D_json + P4b + tabela acima);
  `encode_json` NÃO foi introduzido no core (adaptadores ficam fora).

**Contratos de borda CONGELADOS — o item (2) do reescopo `.8`=feature-complete está fechado.**

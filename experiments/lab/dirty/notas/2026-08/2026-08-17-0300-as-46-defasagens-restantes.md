# 2026-08-17 — as 46 defasagens que restam (verificação adversarial)

> **Origem**: workflow `wf_091c3b09-c1d` — 76 agentes, 47 min, 4,1M tokens. Levantou **64**
> alegações; **54 sobreviveram** à refutação adversarial (os refutadores foram instruídos a
> refutar em caso de dúvida, e a tratar ADR/theory/blocos-datados como log, não defasagem).
> **3 foram resolvidas em 2026-08-17** (as da raiz, escolha do owner); estas **46** ficam.

## Por que elas existem — a assinatura única

Não são defasagens aleatórias. É **uma classe só**: *a frase foi editada pela metade.*

- a tabela de discriminadores foi corrigida no topo do `TCF-format`, e o fluxograma **175
  linhas abaixo** ficou dizendo `H → fail-loud` — nos dois idiomas
- `D17a=300` foi corrigido no `encode-knobs`, e `D1-D9=1523` **na mesma frase** ficou
- `{}` foi corrigido no `api.md`, e `[]` **na mesma linha** ficou

A régua de 2026-08-16 era *procurar o número morto conhecido*. Ela não pega esta classe,
porque a metade errada não contém a string procurada. **O gate que pega é executar o
exemplo** — 5 dos 8 achados do crítico de completude vieram de execução.

Esse gate agora existe: [`varre_snippets.py`](../../2026-08/2026-08-16/2026-08-16-2350-sincronizacao-docs-x-codigo/varre_snippets.py) — 70 blocos python
nos docs vivos, 50 executáveis, **0 falhas**, 20 pulados (declarados, não contam como
aprovados). Roda os blocos de um mesmo arquivo **cumulativamente**, como o leitor faz.

## O erro estrutural — já corrigido

As correções de 2026-08-16 foram feitas **nas folhas, não na raiz**. O `AGENTS.md` é o guia
canônico — o `CLAUDE.md` diz literalmente *"divergência entre os dois: AGENTS.md vence"* — e
ele ainda ensinava as **duas** coisas que a auditoria tinha ido caçar: que o default do
single-col é o órfão de 0 B (morto pela ADR-0034) e que só existem 5 discriminadores. O
próximo agente que o lesse reintroduziria no `src/` exatamente o que acabara de ser corrigido.
Resolvido em `AGENTS.md:180-193` e `MAP.md:128`.

## As 46


### ensina-erro-de-porte (13)

- **`docs/algorithms/TCF-format.pt-BR.md:258`**
  - *doc diz*: Diagrama "### Decode (espelho)" (:253-259):

    decode(text) → list[str] | dict[str, list[str]]
             │
             ├─ disc após "#TCF.8" == "M" ──► _decode_multi → dict
             │  (H/desconhecido → fail-loud; #TCF.6/.7 → erro
  - *real*: Comportamento pre-ADR-0033. O `H` foi soldado em 2026-07-14 e roteia para o codec hierarquico; o `decode` devolve `list[dict]`, que nem sequer esta' na assinatura do diagrama. O proprio doc ja' registra o weld 14 linhas antes da tabela de d
- **`docs/algorithms/core-data-model.md:155`**
  - *doc diz*: Secao "## Gramática do output (marcadores que o emit gera)" (:140). A tabela fecha em :154-155 com `*N+delta|<template>` (seq-RLE) e `*N+d1,d2,...|<template>` (multi-delta, ADR-0016), e :158-159 conclui: "O decode é o espelho exato: expande
  - *real*: O encoder default emite `*N~d1,…,dp|` hoje, sem knob nenhum. Um decoder portado com a gramatica desta tabela nao le um wire que o encode de hoje produz em coluna de data/serie periodica. Vale o mesmo pra `docs/vocabulary.md:37` ("Operadores
- **`docs/algorithms/core-data-model.md:163`**
  - *doc diz*: :162-163 — "`multi/core.py` orquestra N colunas. Header textual: `#TCF.7` + `M` (multi flag) + linha meta `# <size1>=<name1>,...`."
  - *real*: O header multi-col hoje e' `#TCF.8M<meta>` com o meta INLINE na propria linha de assinatura, sem o prefixo `# ` e com os sizes em HEX. Nem o minor (`.7`), nem o espaco antes do `M`, nem a linha-meta separada, nem a base decimal correspondem
- **`docs/algorithms/core-data-model.md:164`**
  - *doc diz*: Secao "Multi-coluna e modos V2": "`multi/core.py` orquestra N colunas. Header textual: `#TCF.7` + `M` (multi flag) + linha meta `# <size1>=<name1>,...`". O doc se declara "dispositivo de orientacao ao port" que deve reproduzir o output **by
  - *real*: O header emitido hoje e' `#TCF.8M!5=id,!name` — assinatura `#TCF.8` (nao `.7`), meta INLINE na mesma linha (nao "linha meta" separada), sem o prefixo `# `, tamanhos em hex e marcadores de modo colados. Nao existe segunda linha de meta: a li
- **`docs/how-to/encode-csv-file.md:172`**
  - *doc diz*: "Há **um único caractere proibido**: `\n`, que é o separador de linha do próprio meta e por isso não tem como ser representado dentro dele." (L172-173) + "Todo o resto passa." (L180). Afirmacao NORMATIVA VIVA, escrita neste commit.
  - *real*: `\r` (CR) tambem nao e' representavel, e o proprio codigo diz isso -- mas so' pra VALORES. Em VALOR, encode() levanta `ValueError: valor com quebra de linha (\r) nao e' representavel no TCF (LF delimita linhas)`. Em NOME DE COLUNA nao ha' c
- **`docs/reference/api.md:34`**
  - *doc diz*: Linha da tabela "Dispatch de encode(data) — por tipo de entrada" manda pro hierarquico #TCF.8H, entre outros, `[]` e "`list`/coluna **tipada** (item nao-str)". A tabela e' a regra de roteamento normativa viva.
  - *real*: Nenhum dos dois vai pro .8H. `encode([])` produz '#TCF.8\n' (7 B, single-col flat) e `encode([1,2,3])` produz '#TCF.8n\n*3+1|\\1\n' (tag n, single-col tipada). A propria linha 32 da MESMA tabela ja' diz o certo (`list[int|float|None]` -> `#
- **`docs/reference/api.md:48`**
  - *doc diz*: Tabela de tags: "| `b` | bool; **tres modos** no indice 7 — `b1`, `b2`, `bB` (abaixo) |", reforcado na linha 66 ("Verificavel — o modo aparece no indice 7 do header") e na tabela das linhas 60-64, que enumera b1/b2/bB como o conjunto fechad
  - *real*: Existe uma QUARTA forma emitida: `#TCF.8b` puro, sem nenhum char no indice 7, quando o denso perde o min() (n pequeno). `encode([True])` -> '#TCF.8b', `encode([True, False])` -> '#TCF.8b', `encode([True, None])` -> '#TCF.8b' — este ultimo e
- **`docs/reference/encode-knobs.md:73`**
  - *doc diz*: "Os invariantes byte-canonical (D1-D9 = 1523 B, D17a = 300 B) sao pinados em [`tests/test_regression_v1_baseline.py`]". Afirmacao viva e normativa (secao "Notas de versao" de um doc reference, sem data), apontando pro arquivo de teste como
  - *real*: O teste pina D1_D9_TOTAL = **1545**, nao 1523. 1523 e' um dos numeros mortos (morreu em ADR-0034: 1523 -> 1586, e ADR-0035: 1586 -> 1545). O D17a = 300 esta' certo — ou seja, a auditoria anterior mexeu no D17a desta linha e deixou o D1-D9 m
- **`docs/reference/encode-knobs.md:73`**
  - *doc diz*: :72-75 — "Os invariantes byte-canonical (D1-D9 = 1523 B, D17a = 300 B) são pinados em [`tests/test_regression_v1_baseline.py`] e re-pináveis só com ADR (ADR-0024/0025)."
  - *real*: O arquivo de teste que o proprio doc aponta como fonte pina 1545, nao 1523. O 1523 e' da era pre-ADR-0034 (o header default somou +63) e pre-ADR-0035 (a polaridade tirou −41). O D17a=300 esta' certo. E' o mesmo numero morto que a auditoria
- **`docs/tutorials/getting-started.md:78`**
  - *doc diz*: Passo 1, bullets 2 e 3 (linhas 78-79, NAO tocados pelo commit, mas o commit inseriu o paragrafo do carimbo 3 linhas ACIMA deles): "- **Second string (`abcd`)**: represented as `1d`. It means \"reuse 3 characters of the prefix of string 1 an
  - *real*: O digito NAO e' contagem de caracteres nem indice de STRING: e' o id final de atomo/alias (posicao de primeira-emissao no body), como o proprio guia de port declara em docs/algorithms/core-data-model.md:122-127 ("o id final NAO e' o prov_id
- **`docs/tutorials/getting-started.pt-BR.md:81`**
  - *doc diz*: Mesmo defeito do EN, linhas 81-82: "- **Segunda string (`abcd`)**: representada como `1d`. Significa \"reutilize 3 caracteres do prefixo da string 1 e adicione `d` ao final\"." e "- **Terceira string (`abcde`)**: representada como `1,2e`. S
  - *real*: Identico ao achado do EN: o digito e' id de atomo/alias (posicao de primeira-emissao), nao contagem de caracteres nem indice de string. O pt-BR nao diverge do EN aqui -- ele reproduz o mesmo erro, entao a correcao tem de ser feita nos DOIS
- **`src/tcf/__init__.py:27`**
  - *doc diz*: Linhas 25-30 (docstring do pacote, o que `help(tcf)` mostra): "Encoder rota por TIPO: flat puro (`list[str]` / `dict[str,list[str]]` retangular >=1 linha) fica flat; aninhado/**tipado**/vazio (list[dict], objeto, escalar, **`[]`**/`{}`, rag
  - *real*: O ramo TIPADO nao vai pro `#TCF.8H`: single-col tipado emite `#TCF.8b*` (bool) e `#TCF.8n*` (numero). E `[]` nao vai pro `#TCF.8H`: emite o stamp `#TCF.8`+LF (7 B). Ambos sao contraditos pelo PROPRIO commit — a linha de Status do ADR-0033 q
- **`src/tcf/decoder.py:292`**
  - *doc diz*: Comentario NOVO, escrito por este commit (bloco :286-292, marcado "ATUALIZADO 2026-08-16 (auditoria docs x codigo)"): "...as TRES tags decodam: 'b'... 'n'... 's'... **O que sobra fora dessas tres cai no fail-loud 'discriminador desconhecido
  - *real*: `B` e `C` (bN de DOMINIO, ADR-0036) tambem decodam, e o dispatch pra eles esta' no MESMO arquivo em :194-201, NOVENTA linhas ACIMA do fail-loud de :202-205 — ou seja, nunca chegam nele. Pior: `#TCF.8B` e' emitido pelo `encode()` publico POR

### afirmacao-falsa (31)

- **`README.md:253`**
  - *doc diz*: :214 "Filters already implemented ([ADR-0015]):" seguido de uma tabela com exatamente 3 linhas (`SPEC_CPF`, `SPEC_CNPJ`, `SPEC_IP`); e :252-254 "Core natures are **opt-in and self-describing when they win** ... `decode(blob)` recognizes the
  - *real*: O registry tem 5 specs e o `decode(blob)` resolve automaticamente tambem `:dt` (data-iso) e `:ipad` (int-pad). A frase e' uma enumeracao fechada ("the official cpf, cnpj and ip filters"), nao uma amostra — e' o texto de entrada do projeto p
- **`README.md:353`**
  - *doc diz*: Secao viva "## Status (pre-1.0)": "- Test suite: **861 passed, 3 skipped** in the **current** local full run; run `pytest` for the number in your environment." O "current" torna a afirmacao normativa viva.
  - *real*: Rodada local completa hoje: **1285 passed, 3 skipped**. O doc subestima em 424 testes (-33%). O 861 e' do Passo 2 de 2026-07-23 (o proprio STATUS.md registra depois suite 1192, 1199, 1238, 1247). O hedge "run pytest for the number in your e
- **`README.md:368`**
  - *doc diz*: Secao viva "## Results": "**With no compressor at all, TCF is the most compact _text_ format in the set.** Across the 15 synthetic datasets in [EXP-008]" seguida da tabela | **TCF** | **3131** | / CSV 4872 / JSON 5409 / JSONL 7001. Presente
  - *real*: TCF = **2983 B**, nao 3131. Diferenca -148 B. CSV/JSON/JSONL batem EXATO (4872/5409/7001), o que confirma que o metodo de serializacao reproduzido e' o mesmo do EXP-008 — so' o lado TCF andou (header default ADR-0034 +7B x15, menos a polari
- **`README.md:373`**
  - *doc diz*: "~36% smaller than CSV and ~42% smaller than JSON, while staying readable." — percentuais derivados da tabela da linha 368.
  - *real*: Com o TCF real de hoje (2983 B): **-38.8% vs CSV** e **-44.9% vs JSON**. Os percentuais do doc sao os derivados de 3131 (1-3131/4872=35.7%; 1-3131/5409=42.1%) e portanto SUBESTIMAM o ganho atual. Mesma causa-raiz da linha 368.
- **`README.md:402`**
  - *doc diz*: "Across the aggregate of 15 synthetic **single-column** datasets (EXP-008, where the 0.7 multi-col welds do not apply) the same story: `csv+brotli` = 1742 B against `tcf+brotli` = **2116 B**." Presente, mesma secao viva "## Results".
  - *real*: `tcf+brotli` = **2218 B**, nao 2116 (+102 B). `csv+brotli` = 1742 B bate EXATO, o que isola o desvio no lado TCF e confirma que compressor/nivel sao os mesmos. Ambiente confere com o config.json do EXP-008: brotli 1.2.0, quality 11. O senti
- **`README.pt-BR.md:357`**
  - *doc diz*: "- Suite: **861 passed, 3 skipped** na execucao local completa **atual**; rode `pytest` para o numero do seu ambiente."
  - *real*: **1285 passed, 3 skipped**. Espelho pt-BR de README.md:353.
- **`README.pt-BR.md:372`**
  - *doc diz*: Espelho pt-BR da secao "## Resultados": "**Sem nenhum compressor, o TCF e o formato de _texto_ mais compacto do conjunto.** Nos 15 datasets sinteticos do [EXP-008]" + tabela | **TCF** | **3131** |.
  - *real*: TCF = **2983 B**, nao 3131. Identico ao achado do README.md:368 (mesma tabela, arquivo traduzido). CSV/JSON/JSONL do doc (4872/5409/7001) batem exato com a medicao.
- **`README.pt-BR.md:377`**
  - *doc diz*: "~36% menor que CSV e ~42% menor que JSON, continuando legivel."
  - *real*: Hoje: **-38.8% vs CSV**, **-44.9% vs JSON**. Percentuais derivados do 3131 morto. Espelho de README.md:373.
- **`README.pt-BR.md:407`**
  - *doc diz*: "...a mesma historia: `csv+brotli` = 1742 B contra `tcf+brotli` = **2116 B**."
  - *real*: `tcf+brotli` = **2218 B**. Espelho pt-BR de README.md:402; `csv+brotli` = 1742 B esta' correto.
- **`ROADMAP.md:43`**
  - *doc diz*: Paragrafo de estado vigente "Bytes-core welded: ... Formato default `#TCF.8` (ADR-0032). Pacote publicado no PyPI = `tcf-format 0.7.1` (0.8.0 no go do owner). **D1-D9=1523 B** (single-col intacto), D17a=300 B (#TCF.8M, re-pin ADR-0032; cont
  - *real*: D1-D9 = **1545 B**. O parenteses "(single-col intacto)" tambem ficou falso: o single-col foi exatamente o que mudou duas vezes desde entao — ADR-0034 (header default, +7 B x 9 = +63) e ADR-0035 (delimitador de polaridade, -41 em D5/D6). Mes
- **`docs/algorithms/TCF-format.en.md:54`**
  - *doc diz*: Linha NORMATIVA VIVA, editada por este commit: "**`#TCF.8` is the DEFAULT format** (ADR-0032, 2026-07-09): every multi-col emits `#TCF.8M`". pt-BR linha 57-58: "todo multi-col emite `#TCF.8M`".
  - *real*: Nem todo multi-col emite `#TCF.8M`. Um dict PLANO (nao hierarquico) que contenha `None` sai como `#TCF.8H` — o min() escolhe a rota H, que hoje esta' soldada. O autor editou esta frase (o hunk trocou o final dela sobre single-col) e nao not
- **`docs/algorithms/TCF-format.en.md:254`**
  - *doc diz*: Fluxograma "### Decode (mirror)": `├─ disc after "#TCF.8" == "M" ──► _decode_multi → dict  (H/unknown → fail-loud; .6/.7 → legacy error)`. Identico na pt-BR, linha 258: `(H/desconhecido → fail-loud; #TCF.6/.7 → erro de legado)`.
  - *real*: `H` decoda — foi soldado pela ADR-0033 em 2026-07-14. Esta e' EXATAMENTE a afirmacao morta que o commit se propos a matar (ele consertou a tabela do discriminador nas linhas 64-79 e deixou a MESMA afirmacao viva 175 linhas abaixo, nos DOIS
- **`docs/divulgacao-tcf.md:19`**
  - *doc diz*: Bloco do post: "JSON  596 B   ->   CSV  277 B   ->   TCF  244 B", com a nota da linha 78 declarando "Fontes dos numeros: `README.md` (exemplo do cadastro)".
  - *real*: O cadastro do README encoda hoje em **242 B**, nao 244 B. O proprio README.md:38 ja' diz "TCF *(242 B, format 0.8, real `encode` output)*" — o doc de divulgacao ficou 2 B atras da sua fonte declarada. JSON 596 B e CSV 277 B conferem (CSV me
- **`docs/divulgacao-tcf.md:74`**
  - *doc diz*: Bloco "Notas pra quem for postar", linhas 74-76: "**Estado real**: pre-1.0 (`#TCF.7`). A `view()` lazy e' **gadget funcional** (`scripts/tcf_lazy/`, 27 testes, L1-L5) — real/testado, mas **nao** e' API estavel de `src/tcf` ainda. Os filtros
  - *real*: Tres afirmacoes mortas: (1) o wire e' `#TCF.8`, nao `#TCF.7` — `#TCF.7` foi CORTADO e da' fail-loud no decode; (2) `view` e' API publica de `src/tcf` (esta' em `tcf.__all__` junto com `LazyTCF`/`Filtered`), e `docs/reference/lazy-view.md` d
- **`docs/how-to/encode-csv-file.md:66`**
  - *doc diz*: Passo 2, "Exemplo de saída (aproximado — detalhe do header em TCF-format.md)" (L66) seguido do bloco L67-77, que mostra `Charlie` e `alic*e*@example.com` em LINHAS SEPARADAS.
  - *real*: O wire real concatena as duas colunas na MESMA linha (`Charliealic*e*@example.com`) -- e' justamente o mecanismo de fronteira implicita de coluna do formato. O bloco do doc tem uma quebra de linha a mais: 86 B contra os 85 B reais, e nao de
- **`docs/how-to/encode-csv-file.md:103`**
  - *doc diz*: "TCF garante round-trip lossless: `decode(encode(x)) == x` sempre." (L103, absoluto, sem ressalva).
  - *real*: Contradito pelo texto que ESTE MESMO COMMIT adicionou 96 linhas abaixo, no mesmo arquivo: L199-206 diz que o nome vazio "**não** faz round-trip idêntico" e mostra `decode(encode({'': ['1','2']})) -> {'0': ['1','2']}`. Verifiquei: e' verdade
- **`docs/how-to/fluxo-hipotese-producao.md:206`**
  - *doc diz*: Secao "### M9 byte-canonical: invariante vs reanalisavel": "- M9 (**1615 bytes** em D1-D9) e' o **baseline de regressao** **atual**." Front-matter do arquivo: `type: how-to`, `status: active` — how-to VIVO que rege o Estagio 6 (integracao e
  - *real*: O baseline de regressao atual e' **M10 = 1545 B**, nao M9 = 1615 B. O 1615 e' anterior ate' ao 1523 da lista de mortos conhecidos (STATUS.md registra "D1-D9 baseline mudou: M9=1615B -> M10=1523B (-92B, -5.70%)", e depois 1523 -> 1586 -> 154
- **`docs/how-to/inspect-compression.md:303`**
  - *doc diz*: Padrao 1 ("Alta cardinalidade, sem repetição"): `print(f"body_bytes: {col.body_bytes}")     # ~280 (pior caso)` (L303), sustentado por "`body_bytes` grande (próximo de `avg_len * n_rows`)" (L286) e "TCF não consegue explorar repetição. OBAT
  - *real*: Para o snippet exato do doc (`[f"user{i}" for i in range(100)]`), `col.body_bytes` = **28**, nao ~280 -- uma ordem de grandeza. O wire inteiro tem 35 B e faz RT. E a regra de bolso do L286 tambem nao vale aqui: avg_len*n_rows = 590. O exemp
- **`docs/how-to/inspect-compression.md:303`**
  - *doc diz*: Secao "Padrao 1: Alta cardinalidade, sem repeticao". Sinais declarados: "`body_bytes` grande (proximo de `avg_len * n_rows`)". Exemplo executavel (linhas 295-303): `data = [f"user{i}" for i in range(100)]` com o comentario de saida esperada
  - *real*: `body_bytes` medido = **28**, nao ~280 (10x menor). E `avg_len * n_rows` = 590, ou seja o exemplo tambem refuta o "sinal" que a secao ensina: `user0..user99` compartilha o prefixo `user` inteiro, entao o OBAT fatora quase tudo. O exemplo es
- **`docs/how-to/use-natures.md:34`**
  - *doc diz*: "**Exemplo medido**: uma coluna com 1000 CPFs válidos caiu de 15 KB para 8,5 KB com a *nature*. Sem ela, caiu para 9 KB." (L34-35). Esta' na secao "Quando usar" -- e' o argumento de decisao do guia.
  - *real*: Nenhuma das duas metades fecha, e a segunda inverte a decisao. No dataset canonico de 1000 CPFs validos (D-CPF-uniform.csv, 15004 B): COM nature = 6810 B (6,65 KB, nao 8,5 KB); SEM nature = 14993 B (14,64 KB) -- nao cai pra 9 KB, praticamen
- **`docs/how-to/use-natures.md:155`**
  - *doc diz*: "**Ganho observado em laboratório**: 1000 IPs na mesma `/24` chegaram a **1,71% do tamanho** da codificação comum. Em amostras pequenas ou IPs aleatórios, o filtro não ajudou (102% do tamanho, ou seja, ficou ligeiramente maior)." (L155-157)
  - *real*: 1,71% nunca foi ratio vs a codificacao comum: e' o numero do ADR-0015 medido contra `M10 puro` = 13349 B, que e' praticamente o CSV cru. Hoje, no dataset canonico D-IP-subnet (o mesmo que gerou o 1,71%), a nature da' 240 B contra 495 B da c
- **`docs/how-to/use-natures.md:304`**
  - *doc diz*: :291-292 — "**Data ISO**: ganho forte em single-column ... Uma futura `DateSpec` precisa validar o calendário e só entra com testes em dados reais." E :304-305 — "Por isso, o `.8` mantém CPF/CNPJ/IP. Os demais candidatos ficam no `.9`, salv
  - *real*: A `DateSpec` deixou de ser "futura": `SPEC_DATA_ISO` esta' soldada e no registry, emite `#TCF.8 :dt` (ADR-0041 §mapa de ids) e o decode a resolve sozinho, sem spec out-of-band. `SPEC_INT_PAD` (`:ipad`, soldado 2026-08-14) tambem. O `.8` hoj
- **`docs/reference/api.md:34`**
  - *doc diz*: Tabela de dispatch, linha 34: "... `[]` · `{}` ... | hierárquico | `#TCF.8H` (`#D`/`#E`/`#O`/`#V`)". Reforçado na linha 80: "`encode([])`/`encode({})` deixaram de ser fail-loud e viram `.8H` (`#D0`/`#E`, representáveis)".
  - *real*: Só a metade `{}` -> `#TCF.8H#E` é verdadeira. `encode([])` devolve `'#TCF.8\n'` — single-col flat, 7 B, NÃO `.8H`, e o wire não contém `#D0` nem começa por `#TCF.8H`. O próprio api.md se contradiz 60 linhas abaixo: 93-95 dizem "wire com `#T
- **`docs/reference/api.md:34`**
  - *doc diz*: Tabela de dispatch ("Dispatch de `encode(data)` — por tipo de entrada"): a linha `| list[dict] (dataset) · dict com valor escalar/aninhado · dict ragged ou 0-linha · escalar solto · `[]` · `{}` · list/coluna tipada (item nao-str) | hierarqu
  - *real*: `encode([])` sai em `#TCF.8` (single-col flat, 7 B) — nao `#TCF.8H`. O proprio doc se contradiz 3 linhas abaixo (linha 37, "Regra"): "Aninhado, misto, escalar solto ou `{}` vai pro `.8H`" — ali `[]` NAO aparece, que e' o comportamento corre
- **`docs/reference/api.md:87`**
  - *doc diz*: Secao "## kwargs de `encode` por rota", :87 — "- **`nature`** (spec único): só **single-col flat** (`list[str]`)." O doc se declara "Fonte única da superfície pública" (:3).
  - *real*: `nature=` deixou de ser recusado na rota TIPADA quando o `IntPadSpec` foi soldado (2026-08-14; o id `ipad` esta' no mapa do ADR-0041). Hoje `encode(list[int], nature=...)` e' aceito, muda o wire (26 B contra 37 B) e emite `#TCF.8n :ipad` —
- **`docs/reference/encode-knobs.md:9`**
  - *doc diz*: Bloco de codigo que declara a assinatura publica de encode(): "encode(data, *, side_outputs=None, parallel=False, nature=None, nature_per_col=None, layers=None, fallback=True, min_header=True, min_len=None, sort_by=None)". O doc se apresent
  - *real*: A assinatura real tem 12 kwargs, nao 9: faltam `name`, `stamp` e `drop_names`. `stamp` e' o unico knob com efeito de bytes no single-col (tira os 7 B do header) e esta' ausente da referencia de knobs; api.md documenta os tres (L88), entao a
- **`docs/reference/encode-knobs.md:13`**
  - *doc diz*: "Aplicam-se a **multi-coluna** (`dict[str, list[str]]`); para single-col (`list[str]`) sao **ignorados**, exceto `min_len` e `nature`." — regra normativa viva sobre a lista de excecoes.
  - *real*: A lista de excecoes esta' incompleta e inverte o caso mais relevante. Medido em `list[str]`: `parallel`, `layers`, `fallback`, `min_header`, `sort_by`, `drop_names` sao de fato ignorados (wire byte-identico ao baseline, 30 B). Mas `stamp` N
- **`docs/reference/encode-knobs.md:73`**
  - *doc diz*: Secao "## Notas de versao" (reference viva, Diataxis): "Os invariantes byte-canonical (**D1-D9 = 1523 B**, D17a = 300 B) **sao pinados** em [`tests/test_regression_v1_baseline.py`] e re-pinaveis so' com ADR (ADR-0024/0025)." Presente do ind
  - *real*: O arquivo apontado pina **D1_D9_TOTAL = 1545**, nao 1523. O doc contradiz diretamente a fonte que ele proprio cita. O D17a = 300 B esta' CORRETO (a auditoria anterior consertou esse metade e deixou o D1-D9).
- **`docs/reference/encode-knobs.md:73`**
  - *doc diz*: "Os invariantes byte-canonical (D1-D9 = 1523 B, D17a = 300 B) sao pinados em tests/test_regression_v1_baseline.py" — afirmacao NORMATIVA VIVA (presente, sem data), em doc de reference. 1523 esta' na lista de numeros MORTOS; a auditoria de 2
  - *real*: O teste pina D1_D9_TOTAL = 1545, nao 1523. O proprio comentario do teste registra a cadeia de mortes: 1523 -> 1586 -> 1545. D17a = 300 esta' correto. Unico hit de numero morto que sobrou nos docs vivos (grep sobre docs/reference/, docs/how-
- **`docs/vocabulary.md:46`**
  - *doc diz*: Linha reescrita por este commit: "`!<size>=<name>` — modo **raw** (V2-A): body = `"\n".join(valores)`, texto LITERAL sem OBAT/HCC (decode = `split("\n")`); **vence quando `len(raw) < len(tcf)`** e nenhum valor tem `\n` embutido (`_fallback_
  - *real*: `len(raw) < len(tcf)` + `_fallback_safe` e' condicao NECESSARIA, nao suficiente. Em `src/tcf/multi/core.py:458-469` o raw so' vira o melhor CORRENTE; depois `_v2b_encode` (`@`, dict) e `_struct_split_encode` (`%`) ainda podem bater o raw. M
- **`src/tcf/__init__.py:61`**
  - *doc diz*: Bloco "## Validacao", cujo preambulo (:50) declara "Numeros abaixo sao probatorios: o TESTE mede, a prosa aponta" — o ponteiro E' a parte que carrega o peso. Duas linhas apontam pro mesmo teste: :60-61 "Real-world Adult+TPC-H 57 cols: -11.7
  - *real*: `tests/test_real_world_snapshots.py` tem 97 linhas e TRES fixtures, todas SINGLE-COLUMN carregadas por `_load_single_col`: retail-description-2k (27588 B), retail-stockcode-2k (11237 B), lineitem-comment-2k (50605 B). Zero ocorrencias de "a

### link-quebrado (2)

- **`README.md:604`**
  - *doc diz*: Tres links relativos `[\`llm-benchmark/\`](llm-benchmark/)` em README.md (:604, :660, :668) e os tres espelhos em README.pt-BR.md (:609, :665, :673) — inclusive a linha de wayfinding "I want to run the LLM benchmark -> [llm-benchmark/](llm-
  - *real*: O diretorio `llm-benchmark/` nao existe na raiz e nao esta' no indice do git; nao esta' gitignored (`git check-ignore` sai 1). O conteudo foi movido pra `old/llm-benchmark/` (rastreado: `old/llm-benchmark/README.md` etc.). Os 6 links dao 40
- **`docs/algorithms/TCF-format.pt-BR.md:328`**
  - *doc diz*: "Implementação: [`src/tcf/multi.py`](../../src/tcf/multi.py)." — 3 linhas abaixo do hunk do `None` preservado que este commit editou.
  - *real*: `src/tcf/multi.py` nao existe: `src/tcf/multi` e' PACOTE (diretorio com `__init__.py`, `core.py`, `dict_v2b.py`...). A EN, no ponto equivalente (linha 325), ja' aponta pra `src/tcf/multi/`. Unico link quebrado dos 5 arquivos do cluster, e e

## Não coberto (declarado)

- `docs/adr/**`, `docs/theory/**`, `docs/archive/**` e os blocos **datados** do `STATUS.md`:
  imutáveis ou log histórico. Os números antigos lá dentro estão **certos** pro momento que
  registram — não são defasagem.
- `STATUS.md` além do topo (1200+ linhas de blocos-registry), `ROADMAP.md` além do reportado,
  e os ~40 `tickets/*.md` um a um.
- O gate de snippets **não** pega prosa falsa nem número solto no texto. Ele complementa o
  [`run.py`](../../2026-08/2026-08-16/2026-08-16-2350-sincronizacao-docs-x-codigo/run.py) (27 afirmações nomeadas), não o substitui.

## Conexões

- Lab: [`2026-08-16-2350-sincronizacao-docs-x-codigo`](../../2026-08/2026-08-16/2026-08-16-2350-sincronizacao-docs-x-codigo/)
- Commit do sync original: `007719aa`


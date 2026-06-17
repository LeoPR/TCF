export const meta = {
  name: 'hquery01-lazy-decode-dag-design',
  description: 'Design H-QUERY-01: decode como DAG, caminhos minimos pra agregacao, encode-para-lazy, indices escondidos pra grouping',
  phases: [
    { title: 'Mapear', detail: '5 lentes ancoradas no codigo + estado-da-arte de formatos consultaveis' },
    { title: 'Desenhar', detail: 'sintese: decode-DAG, decode unificado, encode-para-lazy, indices escondidos, knob/gadget/formato' },
  ],
}

const ROOT = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF'

const CTX = `
PROJETO TCF (Tabular Compact Format) — compressao TEXTUAL e EXPLICAVEL de strings tabulares.
Filosofia (ADR-0002 vertice triplice): compressao + memoria + LATENCIA sao restricao DURA, nao
so' bytes. Output permanece TEXTUAL e inspecionavel (RLE *N|linha mostra grupos sem expandir).
NAO compete com gzip/brotli/zstd (binarios opacos); ocupa a area explicavel. Binarizacao (V2-L)
seria INTERNA/em-camadas, header textual mantido.

ALVO desta sessao = H-QUERY-01 (lazy/queryable view). Owner quer EXPANDIR o design de:
1. DECODE-COMO-DAG: o decode hoje eh "tudo ou nada". Mas os artefatos de compressao formam uma
   arvore/grafo de dependencias. Pergunta do owner: que CAMINHO DIFERENTE no grafo de decode da
   pra tomar pra obter o MINIMO necessario pra uma AGREGACAO (ex: sum(qtd) group by usuario), em
   vez de materializar tudo? Mapear o grafo real e o "corte minimo" por tipo de query.
2. DECODE UNIFICADO vs DOIS CAMINHOS: o owner NAO quer um descompressor total + um separado pras
   queries. Quer avaliar se da pra o PROPRIO decode ser PARAMETRIZADO (projecao + predicado
   "empurrados pra dentro") e emitir saidas parciais por demanda. Viabilidade + forma da API.
3. ENCODE-PARA-LAZY: da pra orientar o ENCODE a otimizar pra que o decode lazy fique mais
   eficiente? (escolha de modo por coluna, ordem de coluna, sort_by/clustering, blocagem,
   guardar offsets). Qual o CUSTO em compressao de cada escolha? Eh um profile/knob?
4. INDICES ESCONDIDOS (a parte que o owner MAIS quer expandir): artefatos estilo-indice
   "escondidos" no arquivo (ou sidecar) que marquem descompressao rapida / indiquem rapidamente
   COMO AGRUPAR — pra acelerar groupings. Onde vivem (in-blob = mudaria formato; sidecar = sem
   mudar formato)? Custo em bytes vs ganho de query? Continuam EXPLICAVEIS?

ESTADO REAL DO CODIGO (ancorar, nao inventar):
- Formato multi-col #TCF.7 M: linha1 magic; linha2 meta = pares <marcador?><size?>=<nome> por
  virgula. Marcadores de MODO por coluna: ! = raw (V2-A), @ = dict (V2-B), % = split estrutural,
  nenhum = tcf (OBAT+HCC). Ultima coluna sem size (corpo ate' EOF). Row-aligned por POSICAO (a
  i-esima posicao de cada coluna eh a linha i).
- V2-B dict (@): corpo = ntable + tabela de unicos (#TCF aninhado) + stream de indices base-94
  (largura fixa, 1+ char por linha). DA pra contar/filtrar/agrupar VARRENDO O STREAM sem decodar
  as N linhas (so decoda os K unicos). Isso ja eh explorado pelo gadget.
- modo tcf (OBAT+HCC): ACHADO VERIFICADO 2026-06-16 — os runs *N| e refs entrelacam o valor com
  refs de OUTRAS linhas; NAO eh separavel/contavel sem decode. O ganho lazy limpo vive no dict/raw.
- split estrutural %: campos-digito viram sub-colunas (sub-#TCF aninhado), guardadas como strings.
- GADGET existente scripts/tcf_lazy/lazy.py (NAO eh src/tcf; LE o formato): LazyTCF parseia header
  e FATIA o corpo por coluna sem decodar; _col() decoda UMA coluna sob demanda (cache+touched).
  L1 column-pruning; L3 nrows/group_count (dict: tally do stream; raw: conta newlines); L4 where
  (dict: varre stream comparando id, sem decodar N valores; encadeia AND); L5 group_ranges/agg_by
  sobre layout sort_by (grupos contiguos -> group-by por SLICE; "qtd por usuario"). Numeros
  medidos: where(CustomerID=X).sum(Quantity) toca ~7.9% do blob; count() ~0.2%;
  where(workclass=Private) ~5%. L5 sort_by eh TRADE-OFF de compressao (adult sort_by=education
  -10%; online-retail sort_by=CustomerID +2.3%) — mas o ganho de LATENCIA da query eh sempre presente.

REGRAS DURAS: src/tcf SO muda com aprovacao explicita do owner (esta sessao eh DESIGN, nao
implementa). Mudanca de FORMATO (novo magic/marcador) eh decisao pesada (ADR + GATE real-world +
re-pin de baseline). LOSSLESS por default. GATE: qualquer toque em HCC/pre-pass/prune exige
tests/test_real_world_snapshots.py verde. Vocabulario disciplinado (sem superlativos). Distinguir
sempre: o que eh GADGET (zero core), o que eh KNOB de encode (opt-in, sem mudar formato), o que eh
MUDANCA DE FORMATO (#TCF.8). Preferir o barato que nao toca o nucleo.
`

const ITEM_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['achados'],
  properties: { achados: { type: 'array', items: {
    type: 'object', additionalProperties: false,
    required: ['titulo', 'detalhe', 'implicacao'],
    properties: {
      titulo: { type: 'string' },
      detalhe: { type: 'string', description: 'concreto e ancorado no codigo real ou em fonte citada' },
      implicacao: { type: 'string', description: 'o que significa pro design lazy (gadget/knob/formato; custo/ganho)' },
    },
  } } },
}

phase('Mapear')
const LENSES = [
  { key: 'decode-dag', agentType: 'Explore', prompt:
    `LENTE 1 — DECODE COMO GRAFO. Leia src/tcf/decoder.py, src/tcf/multi.py, ` +
    `src/tcf/composicional/syntax.py, src/tcf/composicional/hcc_seqrle.py, src/tcf/core/online.py, ` +
    `src/tcf/obat_shape.py. MAPEIE o grafo de dependencias do decode: quais sao os NOS (parse de ` +
    `header -> fatiar slot por coluna -> decode do modo -> materializar linhas) e as ARESTAS. Para CADA ` +
    `modo (tcf/raw/dict/split), responda concretamente: o que PRECISA ser decodado pra recuperar (a) UMA ` +
    `celula [linha i, coluna c]; (b) UMA coluna inteira; (c) um COUNT de linhas; (d) um GROUP-TALLY ` +
    `(contagem por valor) numa coluna; (e) sum/avg de uma coluna numerica filtrada por outra. ` +
    `Onde o decode() ATUAL super-computa em relacao a uma query de agregacao? Qual eh o CORTE MINIMO do ` +
    `grafo pra cada caso? Onde estao os pontos de corte naturais (colunas independentes, stream de dict ` +
    `separavel, sub-tabela de split)? Onde NAO ha corte (tcf entrelacado)?` },
  { key: 'lazy-atual', agentType: 'Explore', prompt:
    `LENTE 2 — ESTADO ATUAL DO GADGET LAZY. Leia scripts/tcf_lazy/lazy.py INTEIRO (inclusive as NOTAS ` +
    `no fim) e tests/test_tcf_lazy.py. Documente EXATAMENTE o que ja existe (L1/L3/L4/L5), quais ` +
    `artefatos cada nivel explora (stream do dict, contagem de newlines no raw, slices do layout ` +
    `ordenado), a API publica (view/LazyTCF/Filtered/group_count/where/group_ranges/agg_by/report), e os ` +
    `LIMITES JA DOCUMENTADOS (tcf entrelacado nao separavel; L5 trade-off de compressao). Liste os HOOKS ` +
    `de otimizacao que as NOTAS ja preveem ("saltos dedutivos", "dicas no header"). O que falta pra ` +
    `"decode parametrizado por demanda" (projecao + predicado pushdown) em cima do que ja tem?` },
  { key: 'separabilidade', agentType: 'Explore', prompt:
    `LENTE 3 — SEPARABILIDADE POR ARTEFATO + MODELO DE CUSTO. Para cada modo (tcf/raw/dict/split), ` +
    `formalize quanto trabalho/bytes custa: contar linhas, achar as linhas que casam um predicado, ` +
    `agrupar (tally), agregar numerico. Use o codigo (multi.py _decode_v2b/_v2b_width/_decode_struct_split, ` +
    `decoder.py _decode_column) pra ancorar. Quais modos ja sao "query-friendly" (dict, raw) e quais ` +
    `forcam materializacao total (tcf)? Para o dict: o stream de indices eh um indice POSICIONAL de fato ` +
    `(id por linha) — que operacoes de grouping/join-por-posicao isso ja habilita de graca? Quantifique ` +
    `com os numeros medidos (7.9%, 5%, 0.2%) e explique de onde vem cada fracao.` },
  { key: 'encode-para-lazy', agentType: 'Explore', prompt:
    `LENTE 4 — ENCODE ORIENTADO A LAZY. Leia src/tcf/encoder.py e src/tcf/multi.py (selecao de modo por ` +
    `coluna no fallback min(tcf,raw,dict,split); sort_by O-FMT-02). Liste as escolhas de ENCODE que ` +
    `deixariam o decode lazy mais barato, e o CUSTO em compressao de cada uma: (1) preferir dict/raw a ` +
    `tcf numa coluna de filtro/group-by (perde bytes? quanto?); (2) ordem das colunas (a de filtro ` +
    `primeiro/menor?); (3) sort_by/clustering pra localidade de grupo (ja medido: trade-off); ` +
    `(4) blocagem/chunking (quebrar a coluna em blocos pra pular blocos); (5) guardar offsets/limites de ` +
    `grupo. Isso eh um PROFILE/KNOB opt-in (sem mudar formato) ou exige formato novo? O que cabe no ` +
    `min() do fallback sem regressao? Ancorar no codigo. Lembre do vertice triplice (trocar bytes por ` +
    `latencia eh legitimo SE for opt-in e o default lossless-puro nao mudar).` },
  { key: 'indices-estado-arte', agentType: 'Explore', prompt:
    `LENTE 5 — INDICES ESCONDIDOS + ESTADO DA ARTE. Esta eh a parte que o owner MAIS quer expandir. ` +
    `Pesquise (WebSearch/WebFetch) o estado da arte de FORMATOS COLUNARES CONSULTAVEIS e decode parcial: ` +
    `Parquet (row-group statistics, min/max, dictionary pages, page index, bloom filter), zone maps, ` +
    `bitmap/Roaring bitmap indexes, dictionary+RLE predicate pushdown, positional/offset indexes, ` +
    `FastLanes / BtrBlocks (compressao consultavel), DuckDB lazy scan, Apache ORC (row index, bloom). ` +
    `Para CADA tecnica relevante, mapeie pro TCF: como seria um "indice escondido" que (a) marca ` +
    `descompressao rapida (pular blocos via zone map min/max), (b) indica rapidamente como agrupar ` +
    `(offsets de grupo / contagem por grupo pre-computada / bitmap por valor de dicionario). Para cada: ` +
    `ONDE VIVE (in-blob -> mudaria formato #TCF.8; sidecar .tcfx -> zero mudanca de formato; derivavel ` +
    `on-the-fly do dict-stream -> custo zero de bytes), CUSTO em bytes, GANHO de query, e se continua ` +
    `EXPLICAVEL/textual (filosofia TCF). Cite as fontes.` },
]
const designs = await parallel(LENSES.map((l) => () =>
  agent(CTX + '\n\n' + l.prompt + `\n\nUse Read/Grep/Glob em ${ROOT} (e Web na lente 5). Retorne SO o objeto estruturado (achados, concretos e ancorados).`,
    { label: `mapear:${l.key}`, phase: 'Mapear', schema: ITEM_SCHEMA, agentType: l.agentType })
))
const all = designs.filter(Boolean).flatMap((r) => r.achados || [])

phase('Desenhar')
const SYNTH = {
  type: 'object', additionalProperties: false,
  required: ['modelo_decode_dag', 'cortes_minimos', 'decode_unificado', 'encode_para_lazy', 'indices_escondidos', 'knob_vs_gadget_vs_formato', 'vertice_triplice', 'proximos_experimentos', 'riscos', 'recomendacao'],
  properties: {
    modelo_decode_dag: { type: 'string', description: 'o grafo de decode dos artefatos TCF + onde decode super-computa pra agregacao' },
    cortes_minimos: { type: 'array', items: { type: 'string' }, description: 'corte minimo do grafo por tipo de query (celula/coluna/count/group-tally/agg-filtrada), por modo' },
    decode_unificado: { type: 'string', description: 'um decode parametrizado (projecao+predicado pushdown) vs dois caminhos: viabilidade + forma da API + o que reusa do gadget atual' },
    encode_para_lazy: { type: 'array', items: {
      type: 'object', additionalProperties: false, required: ['escolha', 'custo_compressao', 'ganho_lazy', 'classe'],
      properties: { escolha: { type: 'string' }, custo_compressao: { type: 'string' }, ganho_lazy: { type: 'string' }, classe: { type: 'string', description: 'gadget | knob-opt-in | mudanca-de-formato' } } } },
    indices_escondidos: { type: 'array', items: {
      type: 'object', additionalProperties: false, required: ['tecnica', 'onde_vive', 'custo_bytes', 'ganho_query', 'explicavel'],
      properties: { tecnica: { type: 'string' }, onde_vive: { type: 'string', description: 'in-blob(TCF.8) | sidecar(.tcfx) | derivavel-on-the-fly' }, custo_bytes: { type: 'string' }, ganho_query: { type: 'string' }, explicavel: { type: 'string' } } } },
    knob_vs_gadget_vs_formato: { type: 'string', description: 'classificacao clara: o que cabe SO no gadget (zero core), o que vira knob de encode opt-in, o que exige formato novo' },
    vertice_triplice: { type: 'string', description: 'como cada proposta troca memoria/velocidade/latencia/compressao (ADR-0002)' },
    proximos_experimentos: { type: 'array', items: { type: 'string' }, description: 'passos BARATOS pra prototipar no gadget/lab sem tocar src/tcf, em ordem' },
    riscos: { type: 'array', items: { type: 'string' } },
    recomendacao: { type: 'string', description: 'honesta: o que fazer primeiro, o que adiar, o que NAO vale o custo' },
  },
}
const synthesis = await agent(
  CTX + `\n\nRecebeu ${all.length} achados de 5 lentes (decode-DAG, gadget atual, separabilidade, ` +
  `encode-para-lazy, indices/estado-da-arte):\n\n` + JSON.stringify(all, null, 2) +
  `\n\nSINTETIZE o design de expansao do H-QUERY-01 cobrindo as 4 ideias do owner: (1) decode como DAG ` +
  `+ cortes minimos por query; (2) decode UNIFICADO parametrizado (sem dois caminhos); (3) encode-para-lazy ` +
  `(com custo de compressao e classe gadget/knob/formato de cada escolha); (4) indices escondidos pra ` +
  `grouping (com onde-vive/custo/ganho/explicabilidade). Some: a classificacao knob/gadget/formato, o ` +
  `vertice triplice, os proximos experimentos BARATOS no gadget (zero src/tcf), riscos e uma recomendacao ` +
  `honesta. Priorize o que NAO toca o nucleo. Vocabulario disciplinado, sem superlativos. Retorne SO o objeto estruturado.`,
  { label: 'sintese:hquery01', phase: 'Desenhar', schema: SYNTH, effort: 'high' })

return { bruto: all, synthesis }
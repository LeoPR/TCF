export const meta = {
  name: 'tcf-transmissao-api-guia',
  description: 'Pesquisa: boas praticas de transmissao de dados por API (JSON, big techs) -> guia honesto de onde o TCF faz diferenca pratica + cenarios de teste',
  phases: [
    { title: 'Pesquisar', detail: '3 lentes web: praticas JSON/HTTP, formatos das big techs, onde compressao/colunar ganha-ou-nao' },
    { title: 'Guia', detail: 'sintese honesta: onde TCF faz diferenca (estatisticamente relevante) vs onde nao + cenarios de teste' },
  ],
}

const CTX = `
OBJETIVO: o owner quer um GUIA DE ARGUMENTACAO honesto: dado o que as boas praticas e as big techs
REALMENTE usam/pedem pra transmitir dados por API, EM QUE SITUACOES (estatisticamente relevantes) o
TCF faz diferenca PRATICA? E em quais NAO ajuda? Pra focar a utilidade do TCF em transmissao e virar
cenarios de teste no progresso.

O QUE E O TCF (ancorar pra honestidade, nao superlativo):
- Formato TEXTUAL e INSPECIONAVEL de strings TABULARES (colunas). Comprime compartilhando afixos
  (OBAT) + composicao (HCC) + dicionario por coluna + split estrutural. Output continua texto.
- NAO compete com gzip/brotli/zstd (compressao binaria generica). Posicao registrada: COMPLEMENTAR —
  medimos que "TCF + brotli" vence "csv + brotli" em escala (multi-col real, adult -28%); TCF como
  PRE-PROCESSO textual. (Em payload minusculo e dado nao-tabular, TCF nao ajuda.)
- Tese central: "lazy/queryable" — descomprimir SO o necessario pra responder (medido: query toca
  ~10-14% do blob). Explicabilidade enquanto comprimido (RLE/grupos visiveis).
- Pre-1.0, Python. O algoritmo e' a camada abstrata (vale em qualquer linguagem).

SEJA HONESTO (regra do projeto): a maioria das APIs manda JSON pequeno sobre HTTP com gzip/brotli —
ai o TCF NAO faz diferenca. O TCF so' importa num nicho: payloads TABULARES, GRANDES, REPETITIVOS
(list/batch/export endpoints), onde se quer compressao que continue TEXTUAL/consultavel, ou como
pre-processo antes do brotli, ou consulta sem descomprimir tudo. Pesquisar pra CONFIRMAR/REFINAR
esse nicho com fontes reais — nao pra inflar.
`

const ITEM = {
  type: 'object', additionalProperties: false, required: ['achados'],
  properties: { achados: { type: 'array', items: {
    type: 'object', additionalProperties: false,
    required: ['titulo', 'detalhe', 'fonte', 'relevancia_tcf'],
    properties: {
      titulo: { type: 'string' },
      detalhe: { type: 'string', description: 'fato concreto sobre pratica de transmissao' },
      fonte: { type: 'string', description: 'org/doc/URL (Google AIP, MDN, RFC, AWS, Stripe, etc.)' },
      relevancia_tcf: { type: 'string', description: 'isso amplia ou reduz o nicho do TCF? por que (honesto)' },
    },
  } } },
}

phase('Pesquisar')
const LENSES = [
  { key: 'json-http-praticas', prompt:
    `LENTE 1 — BOAS PRATICAS de transmissao JSON/HTTP. Pesquise (WebSearch/WebFetch): compressao HTTP ` +
    `(gzip/brotli, Accept-Encoding/Content-Encoding), negociacao de conteudo, guidance de TAMANHO de ` +
    `payload, paginacao, field masks/sparse fieldsets, batching. Fontes: MDN, RFCs (7231/9110, brotli ` +
    `7932), Google API Improvement Proposals (AIP), Microsoft REST API Guidelines, JSON:API, docs de ` +
    `Stripe/GitHub/Shopify. Pergunta-chave: na pratica padrao, JSON ja' vai comprimido (gzip/brotli) ` +
    `por padrao? quando o tamanho do payload vira problema? E onde isso DEIXA espaco (ou nao) pro TCF?` },
  { key: 'formatos-bigtech', prompt:
    `LENTE 2 — FORMATOS que as BIG TECHS usam/pedem alem de JSON. Pesquise: Protobuf/gRPC (Google), ` +
    `Avro, Parquet, Arrow/Arrow Flight, MessagePack, CBOR, columnar exports (BigQuery, Snowflake, ` +
    `Redshift UNLOAD), bulk/batch APIs, NDJSON/JSON Lines. Quando cada um e' RECOMENDADO (interno vs ` +
    `publico; RPC vs dados; streaming; analitico/tabular). Pergunta-chave: pra dados TABULARES/em massa, ` +
    `o que a industria recomenda hoje, e onde um formato TEXTUAL+consultavel como o TCF se encaixaria ` +
    `(ou seria batido por Parquet/Arrow/Protobuf)?` },
  { key: 'onde-ganha-ou-nao', prompt:
    `LENTE 3 — ONDE compressao/colunar/textual GANHA ou NAO em transmissao. Pesquise: limiares de ` +
    `tamanho onde comprimir compensa (overhead em payload pequeno), dados repetitivos/tabulares vs ` +
    `heterogeneos, "gzip ja' resolve?" (redundancia que o gzip/brotli pega de graca), consulta SEM ` +
    `descomprimir tudo (Parquet predicate pushdown / projection), trade textual-vs-binario, custo ` +
    `CPU/latencia de compressao. Pergunta-chave: em que CONDICOES um formato como o TCF faria diferenca ` +
    `PRATICA mensuravel sobre "JSON+gzip/brotli" — e em quais seria irrelevante ou pior? Seja cetico.` },
]
const scans = await parallel(LENSES.map((l) => () =>
  agent(CTX + '\n\n' + l.prompt + `\n\nUse WebSearch/WebFetch. Cite fontes. Retorne SO o objeto estruturado (achados).`,
    { label: `pesquisa:${l.key}`, phase: 'Pesquisar', schema: ITEM, agentType: 'Explore' })
))
const all = scans.filter(Boolean).flatMap((r) => r.achados || [])

phase('Guia')
const SYNTH = {
  type: 'object', additionalProperties: false,
  required: ['estado_da_pratica', 'onde_tcf_faz_diferenca', 'onde_tcf_nao_ajuda', 'vs_alternativas', 'cenarios_de_teste', 'posicionamento_honesto', 'fontes'],
  properties: {
    estado_da_pratica: { type: 'string', description: 'o que eh padrao/recomendado hoje pra transmitir dados por API (sobrio, com fontes)' },
    onde_tcf_faz_diferenca: { type: 'array', items: { type: 'string' }, description: 'situacoes estatisticamente relevantes em que o TCF faz diferenca pratica, com a condicao precisa' },
    onde_tcf_nao_ajuda: { type: 'array', items: { type: 'string' }, description: 'situacoes (a maioria) em que o TCF NAO ajuda — honesto' },
    vs_alternativas: { type: 'string', description: 'TCF vs gzip/brotli, Parquet/Arrow, Protobuf, NDJSON — onde cada um ganha; onde o TCF tem nicho real' },
    cenarios_de_teste: { type: 'array', items: { type: 'string' }, description: 'cenarios concretos de transmissao pra adicionar ao progresso (datasets/forma/baseline a medir)' },
    posicionamento_honesto: { type: 'string', description: 'a frase-guia de argumentacao: qual o formato comum/recomendado e onde o TCF realmente faz diferenca pratica' },
    fontes: { type: 'array', items: { type: 'string' } },
  },
}
const synthesis = await agent(
  CTX + `\n\nRecebeu ${all.length} achados de 3 lentes (praticas JSON/HTTP, formatos big-tech, onde ` +
  `ganha-ou-nao):\n\n` + JSON.stringify(all, null, 2) +
  `\n\nSINTETIZE um GUIA DE ARGUMENTACAO honesto: (1) estado da pratica; (2) onde o TCF FAZ diferenca ` +
  `(situacoes estatisticamente relevantes, condicao precisa); (3) onde NAO ajuda (a maioria — honesto); ` +
  `(4) vs alternativas (gzip/brotli, Parquet/Arrow, Protobuf, NDJSON); (5) cenarios de teste concretos ` +
  `pro progresso; (6) o posicionamento-frase. Vocabulario sobrio, SEM superlativo. Nada de inflar o ` +
  `nicho. Retorne SO o objeto estruturado.`,
  { label: 'guia:transmissao', phase: 'Guia', schema: SYNTH, effort: 'high' })

return { bruto: all, synthesis }
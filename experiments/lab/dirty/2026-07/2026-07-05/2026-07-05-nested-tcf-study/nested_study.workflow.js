export const meta = {
  name: 'nested-tcf-study',
  description: 'Pesquisa formas reais de payload JSON aninhado (request/response) + design-panel de "TCF aninhado similar ao JSON"',
  phases: [
    { title: 'Research', detail: 'formas reais de payload aninhado (AWS/Azure/REST) + como formatos existentes tabelam nested' },
    { title: 'Design', detail: 'judge-panel de designs de TCF-aninhado (4 abordagens x 3 lentes)' },
    { title: 'Synthesis', detail: 'consolida pesquisa + design recomendado' },
  ],
}

const PRIMER = `
CONTEXTO TCF (Tabular Compact Format) — leia antes de responder:
- TCF e' um formato TEXTUAL, lossless, de compressao de STRINGS TABULARES. API: encode(list) OU encode(dict[str,list[str]]).
  A unidade nativa e' uma TABELA colunar homogenea (dict de colunas de mesmo tamanho). NAO ha suporte nativo a JSON aninhado.
- Camadas: OBAT (tokeniza afixos LCP/LCS) + HCC (composicional: refs, concat). HCC ja' faz "nesting" em nivel de VALOR/afixo
  (ex.: filho_de(no2=decl folha "Mar")+"ina"). Isso NAO e' nesting de DOCUMENTO (objeto/array). O estudo e' sobre nesting de DOCUMENTO.
- seq-RLE modela cadencia: *N+delta|template (ex.: timestamps 2026-... viram *24|\\2026). Nenhum layout JSON captura cadencia.
- Filosofia (pilares, NAO negociar): (1) TEXTO + EXPLICABILIDADE enquanto comprimido — grupos visiveis sem descomprimir;
  (2) NAO compete com gzip/brotli/zstd (esses sao binarios opacos) — TCF e' pre-processo textual ANTES do brotli; (3) representacao do MESMO
  conteudo logico, semantica preservada. Concorrente textual real = NDJSON e JSON-colunar {col:[...]}. Medido: TCF+brotli vence NDJSON+brotli
  sempre; vence JSON-colunar so' onde ha estrutura (categorico largo ou cadencia).
- Perfil DUPLO de API: upload=request (pequeno <1KB, config/instrucao multi-camada; TCF nao ajuda) vs download=response (VOLUME; arrays grandes; nicho do TCF).
`;

const RESEARCH_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['lens', 'summary', 'examples', 'nested_to_tabular_notes', 'citations'],
  properties: {
    lens: { type: 'string' },
    summary: { type: 'string' },
    examples: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['label', 'shape_json', 'nesting_kind', 'contains_bulk_array', 'why_it_matters'],
        properties: {
          label: { type: 'string' },
          shape_json: { type: 'string', description: 'pequeno esqueleto JSON ANONIMIZADO/sintetico (sem dado real)' },
          nesting_kind: { type: 'string', description: 'ex.: scalar-config | nested-object | array-of-objects | array-of-scalars | mixed' },
          contains_bulk_array: { type: 'boolean', description: 'tem array grande homogeneo (o que interessa ao TCF)?' },
          why_it_matters: { type: 'string' }
        }
      }
    },
    nested_to_tabular_notes: { type: 'string', description: 'como formatos existentes (BigQuery nested/repeated, Parquet, Spark explode/flatten, Avro, JSON-API, MongoDB) lidam com nested->tabular' },
    citations: { type: 'array', items: { type: 'string' } }
  }
};

const DESIGN_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['approach', 'one_liner', 'worked_example', 'rt_strategy', 'pros', 'cons', 'explicability_note'],
  properties: {
    approach: { type: 'string' },
    one_liner: { type: 'string' },
    worked_example: { type: 'string', description: 'um JSON aninhado pequeno -> como fica nesta abordagem (texto)' },
    rt_strategy: { type: 'string', description: 'como reconstruir o JSON original (round-trip)' },
    pros: { type: 'array', items: { type: 'string' } },
    cons: { type: 'array', items: { type: 'string' } },
    explicability_note: { type: 'string', description: 'quanto o output continua textual/inspecionavel (pilar 1)' }
  }
};

const JUDGE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['approach', 'lens', 'score_0_10', 'verdict', 'notes'],
  properties: {
    approach: { type: 'string' },
    lens: { type: 'string' },
    score_0_10: { type: 'number' },
    verdict: { type: 'string' },
    notes: { type: 'string' }
  }
};

const SYNTH_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['recommended_approach', 'rationale', 'ranking', 'key_examples', 'open_questions', 'positioning_sentence'],
  properties: {
    recommended_approach: { type: 'string' },
    rationale: { type: 'string' },
    ranking: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['approach', 'avg_score', 'note'], properties: { approach: { type: 'string' }, avg_score: { type: 'number' }, note: { type: 'string' } } } },
    key_examples: { type: 'array', items: { type: 'string' }, description: 'exemplos de payload aninhado real que devem entrar no writeup' },
    open_questions: { type: 'array', items: { type: 'string' } },
    positioning_sentence: { type: 'string', description: 'uma frase honesta e sobria: quando TCF-aninhado ajuda e quando nao' }
  }
};

phase('Research');
const LENSES = [
  { key: 'request-config-multilayer', prompt: `${PRIMER}\nLENTE A — REQUEST payloads (upload). Pesquise (WebSearch/WebFetch) as formas TIPICAS de CORPO DE REQUISICAO de APIs reais que enviam informacao basica em campos de instrucao, as vezes multi-camada: config objects aninhados (options/settings/filters), batch requests com array de itens, query DSLs (Elasticsearch query, GraphQL variables, JSON-RPC params), AWS/Azure request bodies. Foco: quao ANINHADO e um request tipico, e se contem ARRAY GRANDE homogeneo (onde o TCF poderia ajudar) ou so config escalar pequeno (<1KB, onde nao ajuda). De exemplos ANONIMIZADOS/sinteticos.` },
  { key: 'response-envelope-bulk', prompt: `${PRIMER}\nLENTE B — RESPONSE payloads (download). Pesquise as formas TIPICAS de RESPOSTA de APIs reais que carregam VOLUME: envelopes aninhados (data/meta/links no JSON-API, results paginados), arrays de objetos homogeneos, respostas de series temporais/forecast/metrics (Prometheus, CloudWatch GetMetricData, time-series DBs), resultados de query. Foco: identificar o array grande homogeneo dentro de um envelope aninhado — o alvo do TCF. Exemplos ANONIMIZADOS/sinteticos.` },
  { key: 'nested-in-existing-formats', prompt: `${PRIMER}\nLENTE C — como formatos EXISTENTES lidam com nested->tabular. Pesquise: BigQuery nested & repeated fields (STRUCT/ARRAY, dot+UNNEST), Parquet nested (Dremel repetition/definition levels), Spark explode()/flatten, Avro nested records, pandas json_normalize (record_path/meta), MongoDB embedded docs, JSON-API. Como cada um mapeia arvore JSON <-> tabela colunar? Qual a licao para um TCF aninhado? Cite mecanismos concretos.` },
  { key: 'flatten-conventions', prompt: `${PRIMER}\nLENTE D — convencoes de FLATTENING e path-addressing. Pesquise: JSONPath, dotted paths (a.b.c), bracket-index (a[0].b), JSON Pointer (RFC 6901), flatten libraries (flatten-json, dotty), o problema de arrays-de-objetos no flatten (explosao de colunas vs normalizacao para sub-tabela). Qual convencao de PATH e melhor para reconstruir (round-trip) o JSON? Exemplos.` },
];
const research = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `research:${l.key}`, phase: 'Research', schema: RESEARCH_SCHEMA })
));
const researchClean = research.filter(Boolean);
const researchDigest = JSON.stringify(researchClean).slice(0, 12000);

phase('Design');
const APPROACHES = [
  { key: 'dotted-flatten-single', desc: 'Achatar TODA folha para path dotted/bracket -> 1 tabela (2 col: path, value) OU single-col path=value. Arrays viram index no path.' },
  { key: 'path-value-plus-subtables', desc: 'Esqueleto = tabela (path, value) para escalares; cada ARRAY-DE-OBJETOS vira uma sub-tabela TCF nomeada, referenciada por placeholder no esqueleto.' },
  { key: 'envelope-with-tcf-blocks', desc: 'TCF aninhado: mantem o esqueleto JSON fino (inspecionavel), mas hoista cada array-de-objetos para um BLOCO TCF multi-col nomeado (delimitado), preservando a forma da arvore. Skeleton pequeno + blocos TCF grandes.' },
  { key: 'json-columnar-hybrid', desc: 'Mantem a arvore JSON mas columnariza cada array {col:[...]} e opcionalmente TCF-encoda cada coluna. Steelman: e o JSON-colunar ja medido.' },
];
const designs = await parallel(APPROACHES.map(a => () =>
  agent(`${PRIMER}\nPROJETE a abordagem de TCF ANINHADO chamada '${a.key}': ${a.desc}\nUse os achados da pesquisa como contexto:\n${researchDigest}\nDe um worked_example concreto (um JSON aninhado pequeno com um array-de-objetos -> como fica). Explique a estrategia de ROUND-TRIP (reconstruir o JSON exato). Seja honesto nos cons (ex.: explosao de colunas, perda de tipo, overhead de esqueleto).`,
    { label: `design:${a.key}`, phase: 'Design', schema: DESIGN_SCHEMA })
));
const designsClean = designs.filter(Boolean);

const JUDGE_LENSES = [
  { key: 'bytes-redundancy', prompt: 'Avalie BYTES/redundancia: quanto esta abordagem explora redundancia colunar (dedup de chaves, cadencia, low-card) vs deixa tudo pro brotli. Arrays grandes homogeneos sao o teste.' },
  { key: 'round-trip-safety', prompt: 'Avalie ROUND-TRIP: a reconstrucao do JSON exato esta garantida? Riscos: perda de ordem de chaves, tipo (int vs string), null vs ausente, arrays vazios, nesting profundo, chaves com caracteres especiais.' },
  { key: 'explicability', prompt: 'Avalie EXPLICABILIDADE (pilar 1 do TCF): o output continua textual e com grupos visiveis sem descomprimir? Ou vira sopa opaca? A forma da arvore continua legivel?' },
];
const judged = await parallel(designsClean.map(d => () =>
  parallel(JUDGE_LENSES.map(jl => () =>
    agent(`${PRIMER}\nJULGUE a abordagem '${d.approach}' pela lente ${jl.key}.\n${jl.prompt}\nDesign:\n${JSON.stringify(d).slice(0, 4000)}\nDe score_0_10 e um veredito curto e honesto.`,
      { label: `judge:${d.approach}:${jl.key}`, phase: 'Design', schema: JUDGE_SCHEMA })
  )).then(js => ({ approach: d.approach, judgements: js.filter(Boolean) }))
));

phase('Synthesis');
const synth = await agent(
  `${PRIMER}\nSINTETIZE o estudo TCF aninhado similar ao JSON.\nPESQUISA (4 lentes):\n${researchDigest}\nDESIGNS:\n${JSON.stringify(designsClean).slice(0, 6000)}\nJULGAMENTOS:\n${JSON.stringify(judged).slice(0, 6000)}\nEscolha a abordagem RECOMENDADA (media dos scores + honestidade). Liste ranking com avg_score. Extraia os exemplos de payload aninhado REAL que devem entrar no writeup do lab. Liste open_questions. Escreva UMA frase de posicionamento sobria (sem superlativos): quando o TCF-aninhado ajuda (array grande homogeneo dentro do envelope) e quando NAO (config escalar pequeno <1KB). NAO invente numeros de bytes — a medicao empirica e feita separadamente.`,
  { label: 'synth', phase: 'Synthesis', schema: SYNTH_SCHEMA }
);

return { research: researchClean, designs: designsClean, judged, synth };

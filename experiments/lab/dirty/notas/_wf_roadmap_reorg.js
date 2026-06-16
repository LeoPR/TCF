export const meta = {
  name: 'roadmap-reorg',
  description: 'Analise critica de tickets/docs + reorganiza roadmap em tiers (pre-1.0 / 2.0 / pesquisa)',
  phases: [
    { title: 'Analise', detail: '4 agentes: tickets+hipoteses, filtros/natures, ferramentas-aux, cheap-wins+big-bets' },
    { title: 'Sintese', detail: 'planner: reorg em tiers + cheap-wins + plano filtros/tools + big-bets' },
  ],
}

const ROOT = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF'

const IDEAS = `
CONTEXTO: o owner pediu uma REORGANIZACAO do roadmap do TCF (formato textual de compressao
tabular, pre-1.0, 0.7.1 publicado). Sem ordem definida — so' AGRUPAR em tiers pra fazer depois.
Tiers: PRE-1.0 (organizavel agora), 2.0 (talvez), PESQUISA/SPIN-OFF.

NOVAS DIRECOES DO OWNER (precisam ser COLOCADAS na reorg, alem do que ja' existe nos tickets/docs):
1. **Lazy/queryable view (H-QUERY-01)**: API que conecta no blob e so' descomprime o necessario
   quando puxa agregador. count/sum/min/max/avg + filtro (where). Descompressao SELETIVA por
   coluna (e por linha no filtro). PoC pronto em experiments/lab/dirty/2026-06-16-lazy-query/.
   Tese central da 1.0 ("consultar quase sem descomprimir"). Passo+: agregar runs (*N|) sem expandir.
2. **Filtros basicos populares**: CPF/CNPJ/IP ja' welded; quer NUMERO (novo) e talvez outros
   populares. "Nao atropelar" — fazer aos poucos, sem afetar o nucleo com severidade.
3. **Marcador de nature auto-descritivo / auto-SPEC no header (H-NAT-MARK-01)**: hoje natures sao
   opt-in OUT-OF-BAND. Ideia: o SPEC "passeia" com o TCF no header quando NAO da' pra deduzir dos
   dados iniciais; gerado automaticamente na identificacao.
4. **Ferramenta de qualidade de dado / schema (gadget, possivel spin-off)**: ajuda em schema;
   identifica o dado -> gera um SPEC automatico -> marca no protocolo (header) pra descomprimir
   depois. Conecta com (3). Ja' existe parte (scripts/schema_gadget, T-RECOVER-SCHEMA-MULTI-TABLE).
5. **Ferramenta LLM->SQL (gadget, spin-off)**: consulta o schema por uma tool, passa parametros pra
   uma tool que chama uma LLM e gera SQL; o SQL roda na CAMADA LAZY do TCF. NAO depende do TCF;
   integracao LEVE. A tool de schema e a de geracao-de-consulta podem andar juntas como tools
   separadas pra outros usarem. T-RECOVER-LLM-SCHEMA-MODE ja' registrado (parked).
6. **TCF compilado pra maquina (Rust)** + **versao web** (wasm/browser). Big bet / pesquisa.
7. **Embutir TCF como camada estilo Parquet OU modulo no Polars** pra acelerar leitura de dados.
   Big bet / pesquisa.

REGRAS/INVARIANTES: src/tcf so' muda com aprovacao; lossless por default; GATE real-world p/
mudancas em HCC/pre-pass/prune; "barato e nao afeta o nucleo com severidade (exceto bug fix)"
e' um criterio que o owner quer ver destacado.
`

const ITEM_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['items'],
  properties: {
    items: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['id', 'titulo', 'fonte', 'estado', 'tier', 'custo', 'impacto_nucleo', 'depende_de', 'nota'],
        properties: {
          id: { type: 'string' },
          titulo: { type: 'string' },
          fonte: { type: 'string', description: 'ticket/doc/ideia onde aparece' },
          estado: { type: 'string', description: 'welded/parked/aberta/PoC/ideia/done' },
          tier: { type: 'string', enum: ['pre-1.0', '2.0', 'pesquisa-spinoff', 'done', 'descartado'] },
          custo: { type: 'string', enum: ['S', 'M', 'L', 'XL'] },
          impacto_nucleo: { type: 'string', enum: ['nenhum', 'leve', 'medio', 'alto', 'bug-fix'] },
          depende_de: { type: 'string' },
          nota: { type: 'string', description: 'uma frase: por que esse tier; risco; conexao' },
        },
      },
    },
  },
}

phase('Analise')
const ANGLES = [
  {
    key: 'tickets-hipoteses',
    prompt: `Inventarie TODO item nao-terminal do TCF. Leia ${ROOT}/tickets/ (Grep "^status:" e abra os ` +
      `nao-closed), ${ROOT}/experiments/lab/dirty/notas/roadmap-hipoteses.md (Pacotes 1-11, status nao-welded/` +
      `refutada), e o topo do ${ROOT}/STATUS.md. Para cada: tier (pre-1.0 / 2.0 / pesquisa-spinoff), custo, ` +
      `impacto_nucleo, dependencias. Inclua os V2-* do ADR-0018. NAO repita itens ja' welded/done (marque tier=done so' se relevante citar).`,
  },
  {
    key: 'filtros-natures',
    prompt: `Mapeie o estado dos FILTROS/NATURES e o plano de filtros basicos. Leia ${ROOT}/src/tcf/natures/ ` +
      `(SPEC_CPF/CNPJ/IP welded), roadmap Pacote 7 (templated/checksummed/lossy) e Pacote 11 (intra-linha + ` +
      `H-NAT-MARK-01 marcador auto-descritivo). Avalie: (a) o que falta p/ um filtro de NUMERO basico; (b) ` +
      `H-NAT-MARK-01 (SPEC viaja no header) — custo e impacto; (c) quais filtros populares sao baratos e ` +
      `nao mexem no nucleo com severidade. Liste como items (tier/custo/impacto). "Nao atropelar" = priorizar baratos.`,
  },
  {
    key: 'ferramentas-aux',
    prompt: `Mapeie as FERRAMENTAS AUXILIARES (gadgets, possiveis spin-offs). Leia ${ROOT}/scripts/schema_gadget/ ` +
      `(se existir), tickets T-RECOVER-SCHEMA-MULTI-TABLE e T-RECOVER-LLM-SCHEMA-MODE, T-SHAPER-*. Avalie: ` +
      `(a) ferramenta de qualidade/schema -> gerar SPEC automatico -> marcar no header (conecta H-NAT-MARK-01); ` +
      `(b) ferramenta LLM->SQL rodando na camada lazy (H-QUERY-01); (c) shaper. Frame integracao LEVE (sem ` +
      `dependencia dura), o que ja' existe vs falta, e tier (a maioria pesquisa-spinoff). Liste como items.`,
  },
  {
    key: 'cheap-wins-big-bets',
    prompt: `Produza (a) CHEAP-WINS e (b) BIG-BETS. Cheap-wins = itens BARATOS (custo S/M) com impacto_nucleo ` +
      `nenhum/leve (ou bug-fix), tipo: doc, knobs, pequenas features, follow-ups (ex: V2-B RLE no stream), ` +
      `higiene. Big-bets = Rust/compilado, versao web/wasm, camada Parquet, modulo Polars — todos ` +
      `pesquisa-spinoff/2.0, com escopo grosso (XL) e nota de pre-requisito. Leia ${ROOT}/experiments/lab/dirty/` +
      `notas/futuras-otimizacoes-formato.md (O-FMT-*) e roadmap. Liste como items (tier/custo/impacto).`,
  },
]

const analyses = await parallel(ANGLES.map((a) => () =>
  agent(IDEAS + '\n\n' + a.prompt + '\n\nUse Read/Grep (base ' + ROOT + '). Retorne SO o objeto estruturado (items).',
    { label: `analise:${a.key}`, phase: 'Analise', schema: ITEM_SCHEMA, agentType: 'Explore' })
))

const all = analyses.filter(Boolean).flatMap((r) => r.items || [])

phase('Sintese')
const SYNTH_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['analise_critica', 'pre_1_0', 'v2_0', 'pesquisa_spinoff', 'cheap_wins', 'filtros_plan', 'tools_plan', 'big_bets', 'descartar_ou_fechar'],
  properties: {
    analise_critica: { type: 'string', description: '3-5 frases: leitura critica do estado + o que organizar agora vs depois' },
    pre_1_0: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'titulo', 'custo', 'impacto_nucleo', 'porque'], properties: { id: { type: 'string' }, titulo: { type: 'string' }, custo: { type: 'string' }, impacto_nucleo: { type: 'string' }, porque: { type: 'string' } } } },
    v2_0: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'titulo', 'porque'], properties: { id: { type: 'string' }, titulo: { type: 'string' }, porque: { type: 'string' } } } },
    pesquisa_spinoff: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'titulo', 'porque'], properties: { id: { type: 'string' }, titulo: { type: 'string' }, porque: { type: 'string' } } } },
    cheap_wins: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'titulo', 'custo'], properties: { id: { type: 'string' }, titulo: { type: 'string' }, custo: { type: 'string' } } }, description: 'baratos, impacto nucleo nenhum/leve ou bug-fix' },
    filtros_plan: { type: 'string', description: 'plano dos filtros basicos populares (numero etc.) sem atropelar; ordem sugerida barata-primeiro' },
    tools_plan: { type: 'string', description: 'plano das ferramentas auxiliares (qualidade/auto-spec + LLM-SQL), integracao leve, spin-off' },
    big_bets: { type: 'string', description: 'Rust/web/Parquet/Polars: framing, pre-requisitos, por que sao pesquisa/2.0' },
    descartar_ou_fechar: { type: 'array', items: { type: 'string' }, description: 'itens mortos/refutados a manter fechados' },
  },
}

const synthesis = await agent(
  IDEAS + `\n\nRecebeu ${all.length} items das 4 analises (com duplicatas):\n\n` + JSON.stringify(all, null, 2) +
  `\n\nReorganize TUDO num roadmap em tiers. DEDUPLIQUE. Coloque CADA direcao nova do owner (1-7) no tier certo. ` +
  `pre_1_0 = organizavel agora (inclui H-QUERY-01 vision, filtros baratos, cheap-wins, marcador de nature se barato). ` +
  `v2_0 = depois da 1.0 (lossy, streaming/binary V2-J/K/L, intra-linha). pesquisa_spinoff = Rust/web/Parquet/Polars + ` +
  `tools LLM-SQL/schema (integracao leve). Destaque o criterio "barato + nao afeta nucleo com severidade (exceto bug)". ` +
  `Vocabulario disciplinado, sem superlativos. Retorne SO o objeto estruturado.`,
  { label: 'synth:reorg', phase: 'Sintese', schema: SYNTH_SCHEMA }
)

return { bruto: all, synthesis }

export const meta = {
  name: 'pendentes-pos-07',
  description: 'Sweep adversarial de itens pendentes pos-fechamento 0.7 (alem do V2-B RLE)',
  phases: [
    { title: 'Sweep', detail: '3 varreduras por angulos diferentes' },
    { title: 'Sintese', detail: 'consolida, dedup, categoriza, flag 0.7-lossless vs v2.0/owner' },
  ],
}

const ROOT = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF'

const CTX = `
CONTEXTO: o ciclo 0.7 do TCF (formato textual de compressao tabular, pre-1.0) foi fechado.
JA WELDED/RESOLVIDO (NAO listar como pendente): V2-A fallback (!), V2-B dicionario (@),
split estrutural (%), header minimo (ADR-0023, O-FMT-15/16), sort_by (O-FMT-02), Cython
(H-PERF-06 T01/T02), CPF/CNPJ/IP natures (ADR-0015), pacote 0.7.1 publicado (tcf-format).
DECISOES JA TOMADAS: 0.7 lossless-puro (V2-C round e Pacote 10 loss -> roadmap v2.0);
release.yml/Trusted Publishing adiado (follow-up). O owner JA conhece o follow-up "V2-B
RLE no stream" — a pergunta dele e': QUE OUTROS pendentes existem alem desse.
Quero o levantamento EXAUSTIVO dos itens ainda ABERTOS/ADIADOS/PENDENTES (qualquer status
nao-terminal), de qualquer fonte do repo (roadmap, notas, ADRs, tickets, STATUS, diarios).
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
        required: ['id', 'titulo', 'fonte', 'status_lido', 'tipo', 'lossless', 'resumo'],
        properties: {
          id: { type: 'string', description: 'identificador (O-FMT-xx, H-xxx, T-xxx, V2-x, etc.)' },
          titulo: { type: 'string' },
          fonte: { type: 'string', description: 'arquivo onde aparece' },
          status_lido: { type: 'string', description: 'status textual lido (aberta/adiada/deferred/pendente/etc.)' },
          tipo: { type: 'string', enum: ['format-microopt', 'perf', 'lossy-v2', 'nature', 'streaming-binary-v2', 'tooling-dist', 'gadget-externo', 'outro'] },
          lossless: { type: 'string', enum: ['lossless', 'lossy', 'na'], description: 'se o lever preserva lossless' },
          resumo: { type: 'string', description: 'uma frase: o que e + por que ainda aberto' },
        },
      },
    },
  },
}

phase('Sweep')
const ANGLES = [
  {
    key: 'hipoteses',
    prompt: `Varra as HIPOTESES ainda vivas do TCF. Leia ${ROOT}/experiments/lab/dirty/notas/roadmap-hipoteses.md ` +
      `na integra e faca Grep por status nao-terminal (aberta, adiada, em-exp, caracterizada-adiada, A-revalidar) ` +
      `em ${ROOT}/experiments/lab/dirty/notas/. Liste TODA hipotese que NAO esteja welded/refutada/subsumida/absorvida. ` +
      `Inclua Pacote 7 (templated/checksummed/lossy/composite), Pacote 10 (H-LOSS-*), H-PERF-04/05d, H-TH-02 (Patricia), etc.`,
  },
  {
    key: 'formato-adr',
    prompt: `Varra os LEVERS DE FORMATO ainda abertos. Leia ${ROOT}/experiments/lab/dirty/notas/futuras-otimizacoes-formato.md ` +
      `(O-FMT-01..16) e ${ROOT}/docs/adr/0018-v2-format-roadmap.md (V2-C/D/J/K/L). Faca Grep por "proposed", "aberta", ` +
      `"nao implementar", "defer", "PENDENTE", "futuro" em ${ROOT}/docs/adr/. Liste cada O-FMT-* e V2-* que NAO esteja welded ` +
      `(ex: O-FMT-01/03/04/06/07/08/09/12/13/14, aspecto streaming do O-FMT-15, V2-J/K/L). Diga o status real de cada.`,
  },
  {
    key: 'tickets-status',
    prompt: `Varra os TICKETS e PENDENCIAS operacionais. Faca Grep por "^status:" em ${ROOT}/tickets/ e identifique os que ` +
      `NAO estao closed/closed-done/superseded (ou seja: open, deferred, blocked, in-progress, PARKED). Tambem leia o topo do ` +
      `${ROOT}/STATUS.md e ${ROOT}/experiments/lab/dirty/notas/diario/2026-06-15.md procurando secoes "pendente"/"follow-up". ` +
      `Liste cada item operacional aberto (tooling, dados, dist, gadgets). NAO inclua tickets ja' closed.`,
  },
]

const sweeps = await parallel(ANGLES.map((a) => () =>
  agent(CTX + '\n\n' + a.prompt + '\n\nUse ' + ROOT + ' como base. Retorne SO o objeto estruturado (lista items).',
    { label: `sweep:${a.key}`, phase: 'Sweep', schema: ITEM_SCHEMA, agentType: 'Explore' })
))

const all = sweeps.filter(Boolean).flatMap((s) => s.items || [])

phase('Sintese')
const SYNTH_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['resposta_direta', 'lossless_07_doable', 'perf', 'lossy_v2_owner', 'natures', 'streaming_binary_v2', 'tooling_dist', 'descartados', 'recomendacao'],
  properties: {
    resposta_direta: { type: 'string', description: '2-3 frases respondendo: alem do V2-B RLE, o que mais esta pendente (visao geral)' },
    lossless_07_doable: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'resumo', 'esforco', 'risco'], properties: { id: { type: 'string' }, resumo: { type: 'string' }, esforco: { type: 'string' }, risco: { type: 'string' } } }, description: 'levers lossless ainda realizaveis no espirito do 0.7 (sem cruzar linha lossless, sem v2.0 grande)' },
    perf: { type: 'array', items: { type: 'string' } },
    lossy_v2_owner: { type: 'array', items: { type: 'string' } },
    natures: { type: 'array', items: { type: 'string' } },
    streaming_binary_v2: { type: 'array', items: { type: 'string' } },
    tooling_dist: { type: 'array', items: { type: 'string' } },
    descartados: { type: 'array', items: { type: 'string' }, description: 'itens efetivamente mortos/refutados que aparecem como aberto mas nao valem (com motivo)' },
    recomendacao: { type: 'string', description: 'se algo vale fazer agora alem do V2-B RLE, ou se o resto e tudo v2.0/owner. Sem superlativos.' },
  },
}

const synthesis = await agent(
  CTX + `\n\nRecebeu ${all.length} itens das 3 varreduras (com duplicatas):\n\n` +
  JSON.stringify(all, null, 2) +
  `\n\nConsolide e DEDUPLIQUE (mesmo lever citado em fontes diferentes = 1 item). Categorize. ` +
  `Foco da resposta: o owner quer saber, ALEM do "V2-B RLE no stream", QUE OUTROS pendentes existem. ` +
  `Em lossless_07_doable coloque so' o que da' pra fazer mantendo lossless e sem abrir v2.0 grande (ex: cross-column ` +
  `dictionary LOSSLESS se aplicavel, refinamentos de ordering, type-aware). Seja honesto sobre o que e' marginal. ` +
  `Marque em descartados o que ja' foi refutado/skip (ex: O-FMT-01 reversible net-negativo). Vocabulario disciplinado, ` +
  `sem superlativos. Retorne SO o objeto estruturado.`,
  { label: 'synth:pendentes', phase: 'Sintese', schema: SYNTH_SCHEMA }
)

return { bruto: all, synthesis }

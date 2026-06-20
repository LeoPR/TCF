export const meta = {
  name: 'rle-crossref-audit',
  description: 'Auditoria de cross-references faltantes da familia RLE (V2-RLE-STREAM, H-INTRA intra-valor) + outline do doc de estudo; read-only',
  phases: [
    { title: 'Auditar', detail: '3 lentes read-only: mencoes RLE+links, cobertura dos indices, links quebrados' },
    { title: 'Sintetizar', detail: 'fix-list de cross-refs a adicionar + outline do doc de estudo das 2 ideias RLE' },
  ],
}

const ROOT = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF'
const MEM = 'C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory'

const CTX = `
PROBLEMA (owner 2026-06-19): "estou tentando achar o documento que detalha o V2-RLE-STREAM e nao
estou achando". Causa: o lab/resultado existe mas esta' pouco cross-linkado dos pontos de entrada e
nao tem entrada no registry de hipoteses. Diretiva: SEMPRE por cross-references + links pra
hipoteses/conclusoes. Achabilidade = par.2 do metodo Strata.

ESTA AUDITORIA e' READ-ONLY: so' diagnostica onde FALTA link; NAO edita. (Voce e' Explore = sem escrita.)

A FAMILIA RLE no TCF (3 coisas que se relacionam e CONFUNDEM — mapear os links entre elas):
- OBAT/HCC star-N-pipe (welded em src/tcf): RLE de LINHA — linhas adjacentes identicas viram
  "*N|<linha>" (e seq-RLE "*N+delta|template"). E' o modo "tcf". ADR-0016 (seq-RLE). docs/algorithms.
- V2-RLE-STREAM (caracterizado 2026-06-19, CLOSED-geral / nicho textual-puro ABERTO): RLE no STREAM
  de indices do V2-B (modo dict "@"). Lab:
  experiments/lab/dirty/2026-06-19-v2rle-stream-caracterizacao/ (result.md + result_forms.txt +
  analyze.py + analyze_forms.py). ACHADO: clusterizado flipa pro tcf star-N-pipe (overlap); so' ganha
  em runs curtos+skewed; morre sob brotli. Depende de V2-B (ADR-0025).
- RLE na celula / intra-valor = H-INTRA-01/02/03 (ADIADO a pedido do owner): repeticao DENTRO de um
  valor (ex "111.111.111" ou substring repetida numa frase). Registry: roadmap-hipoteses.md.

PONTOS DE ENTRADA / INDICES a checar: ${ROOT}/MAP.md, ${ROOT}/STATUS.md, ${ROOT}/ROADMAP.md,
${ROOT}/experiments/lab/dirty/notas/roadmap-hipoteses.md (registry de hipoteses),
${ROOT}/experiments/lab/dirty/notas/futuras-otimizacoes-formato.md (O-FMT / formato futuro),
${ROOT}/docs/adr/ (0016 seq-RLE, 0025 V2-B), ${ROOT}/docs/algorithms/ (OBAT/HCC/TCF-format),
${MEM} (memoria). Convencao de link: markdown relativo [texto](caminho); memoria usa [[slug]].
`

const ITEM_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['achados'],
  properties: { achados: { type: 'array', items: {
    type: 'object', additionalProperties: false,
    required: ['onde', 'problema', 'fix'],
    properties: {
      onde: { type: 'string', description: 'arquivo (e secao/linha) onde falta o cross-ref OU onde ha link quebrado' },
      problema: { type: 'string', description: 'o que falta linkar ou esta quebrado/orfao' },
      fix: { type: 'string', description: 'link concreto a adicionar (texto -> destino) ou correcao' },
    },
  } } },
}

phase('Auditar')
const LENSES = [
  { key: 'mencoes-rle', prompt:
    `LENTE 1 — MENCOES DA FAMILIA RLE + LINKS. Use Grep em ${ROOT} (docs/, experiments/, md raiz) e ` +
    `${MEM} por: V2-RLE-STREAM, H-INTRA, intra-valor, intra valor, RLE, seq-RLE, e o marcador de run ` +
    `(asterisco-N-pipe). Pra CADA mencao verifique: ela LINKA pra fonte canonica (o lab result.md / o ` +
    `ADR / a entrada de registry)? Ou e' mencao solta sem ponteiro? Liste as mencoes SEM link que ` +
    `deveriam ter + o link que falta. Foco no V2-RLE-STREAM (lab novo 2026-06-19): quem o menciona sem ` +
    `linkar, e quem DEVERIA mencionar/linkar e nao menciona (ex: roadmap-hipoteses.md tem entrada dele?).` },
  { key: 'cobertura-indices', prompt:
    `LENTE 2 — COBERTURA DOS INDICES. Leia ${ROOT}/MAP.md, ${ROOT}/STATUS.md, ${ROOT}/ROADMAP.md, ` +
    `${ROOT}/experiments/lab/dirty/notas/roadmap-hipoteses.md, ${ROOT}/experiments/lab/dirty/notas/` +
    `futuras-otimizacoes-formato.md. Verifique: (a) MAP.md lista o lab 2026-06-19-v2rle-stream e labs ` +
    `recentes? (b) roadmap-hipoteses.md tem ENTRADA pra V2-RLE-STREAM com status/confianca + link pro ` +
    `lab? (provavelmente NAO — era so follow-up no ROADMAP). (c) H-INTRA-01/02/03 no registry cross-linka ` +
    `pra V2-RLE-STREAM (competem pelo mesmo fenomeno via tcf run-RLE)? (d) STATUS.md menciona o achado ` +
    `2026-06-19? Liste cada index que FALTA o ponteiro + o link exato a adicionar.` },
  { key: 'links-quebrados', prompt:
    `LENTE 3 — LINKS QUEBRADOS / ORFAOS (saude §2/§3, foco na vizinhanca RLE/formato). Em ` +
    `${ROOT}/experiments/lab/dirty/notas/ e ${ROOT}/docs/: ache links markdown relativos pra arquivo ` +
    `inexistente, e slugs [[..]] de memoria sem destino. Cheque especialmente futuras-otimizacoes-` +
    `formato.md (O-FMT-15/16/17, H-INTRA), roadmap-hipoteses.md, e se o lab novo result.md aponta de ` +
    `volta pra V2-B (ADR-0025) / OBAT-HCC (docs/algorithms) / H-INTRA. Liste cada link quebrado/faltante.` },
]
const scans = await parallel(LENSES.map((l) => () =>
  agent(CTX + '\n\n' + l.prompt + `\n\nRetorne SO o objeto estruturado (achados, ancorados em arquivo).`,
    { label: `auditar:${l.key}`, phase: 'Auditar', schema: ITEM_SCHEMA, agentType: 'Explore' })
))
const all = scans.filter(Boolean).flatMap((r) => r.achados || [])

phase('Sintetizar')
const SYNTH = {
  type: 'object', additionalProperties: false,
  required: ['resumo', 'fix_list', 'estudo_outline', 'mapa_familia_rle'],
  properties: {
    resumo: { type: 'string', description: 'estado das cross-refs da familia RLE, sobrio' },
    fix_list: { type: 'array', items: {
      type: 'object', additionalProperties: false, required: ['arquivo', 'acao', 'link', 'prioridade'],
      properties: {
        arquivo: { type: 'string' },
        acao: { type: 'string', description: 'o que adicionar/corrigir (concreto)' },
        link: { type: 'string', description: 'o link/destino exato' },
        prioridade: { type: 'string', description: 'alta media ou baixa' },
      } } },
    mapa_familia_rle: { type: 'string', description: 'mapa de como as 3 RLEs se relacionam (linha run-RLE / stream V2-B / intra-valor) e onde cada uma e documentada' },
    estudo_outline: { type: 'array', items: { type: 'string' }, description: 'secoes do doc de estudo consolidando as 2 ideias (intra-valor + stream): fatos medidos, overlap, nicho, perguntas abertas' },
  },
}
const synthesis = await agent(
  CTX + `\n\nRecebeu ${all.length} achados de 3 lentes:\n\n` + JSON.stringify(all, null, 2) +
  `\n\nSINTETIZE: (1) resumo sobrio. (2) FIX_LIST priorizada — cada cross-ref/link concreto a adicionar ` +
  `(arquivo + acao + link + prioridade). (3) MAPA da familia RLE (linha run-RLE welded / stream-V2-B / ` +
  `intra-valor-H-INTRA: como se relacionam, overlap, onde cada uma vive). (4) ESTUDO_OUTLINE: secoes do ` +
  `doc de estudo que consolida as DUAS ideias que o owner quer estudar (RLE intra-valor + V2-RLE-STREAM), ` +
  `com fatos JA medidos (situacao +55%, clusterizado-flipa-tcf, morre-sob-brotli), o overlap com o ` +
  `run-RLE do tcf, o nicho textual-puro, e as PERGUNTAS ABERTAS pro owner decidir. Vocabulario sobrio. ` +
  `Retorne SO o objeto estruturado.`,
  { label: 'sintese:crossref', phase: 'Sintetizar', schema: SYNTH, effort: 'high' })

return { bruto: all, synthesis }
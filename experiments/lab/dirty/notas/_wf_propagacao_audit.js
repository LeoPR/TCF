export const meta = {
  name: 'propagacao-audit',
  description: 'Audita o encadeamento de docs vs a realidade da sessao (propagar achados desde o README)',
  phases: [
    { title: 'Audit', detail: '3 agentes: README+divulgacao / STATUS / ROADMAP+roadmap-hipoteses+futuras' },
    { title: 'Sintese', detail: 'fix-list de propagacao, ordenada por severidade' },
  ],
}

const ROOT = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF'

const GT = `
REALIDADE DA SESSAO (2026-06-16) — os docs DEVEM refletir isto. Flag o que esta' STALE/faltando.

1. **Lazy view() — agora e' GADGET CONSTRUIDO** em \`scripts/tcf_lazy/\` (NAO mais "proposta/PoC"):
   L1 column-pruning + agregadores (count/sum/min/max/avg + where); L2 dimensoes (qtd-por-usuario
   toca 7.9% do blob); L3 contar/agrupar SEM expandir (nrows/group_count, via dict/raw); L4 filtro
   pelo indice do dicionario (where varre o stream); L5 group-by por layout ordenado
   (group_ranges/agg_by, "qtd por usuario"). 27 testes; suite total 425 passed. Le #TCF.7, NAO toca
   src/tcf, NAO e' versao de formato. Achados: agregar \`*N|\` no modo-tcf nao e' separavel (so'
   dict/raw); L5 layout e' trade-off de compressao (adult -10%, online-retail +2.3%).
   -> O README tem uma secao "Proposta: view()" que esta' DESATUALIZADA (era PoC; agora e' gadget).
2. **TCF+brotli vence em ESCALA**: TCF cheio + brotli < csv+brotli em multi-col real (adult -28%);
   "menos TCF" nao ajuda o brotli (refutado). Ordering e' codec-dependente. Lab
   2026-06-16-staged-and-ordering-brotli. (README ja' tem nota de escala; conferir.)
3. **Number-nature**: caracterizado -> PARK (weighted <15% em 2+ datasets; some sob brotli).
4. **O-FMT-12** (encode_file/auto-detect CSV): levantado -> PARK (input fora-do-core por design; 0 bytes).
5. **Filtros modulares** (H-NAT-MARK-02) + classificacao "e' versao?" registrados.
6. Criados nesta sessao: **ROADMAP.md** (tiers) + **docs/divulgacao-tcf.md**. Pacote: tcf-format 0.7.1 (PyPI).
7. README ja' deve ter: exemplo CPF 5-col no topo, secao Filtros (WIP), bloco compressao HTTP + escala,
   secoes "Pra onde vai a 1.0" e "Roadmap 2.0".

INVARIANTES: src/tcf intocado; lossless default; 0.7.1; #TCF.7 default / #TCF.6 legado.
`

const FIND_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['findings'],
  properties: {
    findings: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      required: ['doc', 'ancora', 'problema', 'severidade', 'fix_sugerido'],
      properties: {
        doc: { type: 'string' },
        ancora: { type: 'string', description: 'trecho/secao exata' },
        problema: { type: 'string', description: 'stale ou faltando vs realidade da sessao' },
        severidade: { type: 'string', enum: ['faltando', 'stale', 'cosmetico'] },
        fix_sugerido: { type: 'string' },
      },
    } },
  },
}

phase('Audit')
const ANGLES = [
  { key: 'readme-divulgacao', prompt: `Audite ${ROOT}/README.md e ${ROOT}/docs/divulgacao-tcf.md. ` +
    `Foco: a secao do \`view()\` lazy esta' como "proposta/PoC"? Deveria refletir que e' GADGET ` +
    `CONSTRUIDO (scripts/tcf_lazy/, L1-L5, 27 testes) — ainda fora de src/tcf, mas real/testado, ` +
    `nao so' PoC. Conferir tambem: nota de escala do brotli, exemplo CPF, secoes 1.0/2.0, versao 0.7.1, ` +
    `links. Liste o que atualizar pra propagar a realidade da sessao.` },
  { key: 'status', prompt: `Audite ${ROOT}/STATUS.md (ponto de entrada bibliografico, status ABSOLUTO). ` +
    `Ele tem um bloco refletindo a SESSAO 2026-06-16 (lazy gadget L1-L5, number-nature PARK, ` +
    `TCF+brotli vence em escala, O-FMT-12 PARK, ROADMAP.md + divulgacao criados, filtros modulares)? ` +
    `Provavelmente FALTA. Diga exatamente que bloco adicionar/atualizar no topo (sem reescrever o historico).` },
  { key: 'roadmap-chain', prompt: `Audite ${ROOT}/ROADMAP.md, ${ROOT}/experiments/lab/dirty/notas/roadmap-hipoteses.md ` +
    `e ${ROOT}/experiments/lab/dirty/notas/futuras-otimizacoes-formato.md. Confira consistencia dos status: ` +
    `H-QUERY-01 (lazy) = gadget L1-L5 feito; FILTRO-NUMERO = caracterizado/PARK; O-FMT-12 = PARK; ` +
    `H-NAT-MARK-02 modular; staged-brotli/ordering achados. Flag qualquer status stale ou contradicao entre eles.` },
]

const audits = await parallel(ANGLES.map((a) => () =>
  agent(GT + '\n\n' + a.prompt + '\n\nUse Read/Grep (base ' + ROOT + '). Retorne SO o objeto estruturado (findings).',
    { label: `audit:${a.key}`, phase: 'Audit', schema: FIND_SCHEMA, agentType: 'Explore' })
))
const all = audits.filter(Boolean).flatMap((r) => r.findings || [])

phase('Sintese')
const SYNTH = {
  type: 'object', additionalProperties: false, required: ['resumo', 'fixes'],
  properties: {
    resumo: { type: 'string', description: '2-3 frases: estado de propagacao do encadeamento' },
    fixes: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      required: ['doc', 'ancora', 'severidade', 'fix_sugerido'],
      properties: { doc: { type: 'string' }, ancora: { type: 'string' },
        severidade: { type: 'string', enum: ['faltando', 'stale', 'cosmetico'] }, fix_sugerido: { type: 'string' } },
    }, description: 'dedup, ordenada (faltando > stale > cosmetico)' },
  },
}
const synthesis = await agent(
  GT + `\n\nRecebeu ${all.length} achados (com duplicatas):\n\n` + JSON.stringify(all, null, 2) +
  `\n\nDEDUPLIQUE e ordene por severidade. Para cada um, o fix exato pra PROPAGAR a realidade da sessao. ` +
  `Conservador: so' o que realmente diverge. Retorne SO o objeto estruturado.`,
  { label: 'synth:propagacao', phase: 'Sintese', schema: SYNTH })

return { bruto: all, synthesis }

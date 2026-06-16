export const meta = {
  name: 'close-07-review',
  description: 'Inventaria itens abertos do ciclo 0.7 e sintetiza priorizacao de fechamento',
  phases: [
    { title: 'Inventario', detail: 'um agente por ticket/decisao aberta -> avaliacao estruturada' },
    { title: 'Sintese', detail: 'planner: o que fechar agora vs decidir vs adiar' },
  ],
}

const ROOT = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF'

const CYCLE = `
CONTEXTO DO CICLO 0.7 (pre-1.0, "perseguir bytes"):
- 0.7 = #TCF.7, multi-col e' o DEFAULT do encode. Foco: espremer bytes no formato textual, payload pequeno.
- JA WELDED neste ciclo: O-FMT-02 sort_by; V2-A fallback identity (ADR-0022); header v2 minimo (ADR-0023);
  V2-B dicionario/categorico (ADR-0025, 13.9% weighted); split estrutural (ADR-0026, 19.39% weighted, maior lever).
- SHELVED/REFUTADO neste ciclo: Pacote 8 H-HCC dinamico (1.3% teto, adiado); V2-D strip afixo (refutado, subsumido OBAT).
- PENDENTE DE DECISAO DO OWNER: V2-C lossy-round (caracterizado, nicho 1.5%); Pacote 10 LOSS amplo (taxonomia registrada).
- INVARIANTES: src/tcf so' muda com aprovacao explicita; GATE tests/test_real_world_snapshots.py p/ qualquer
  mudanca em HCC/pre-pass/prune; D1-D9=1523B single-col intocado; D17a=303B multi-col.
- Filosofia: TCF e' LOSSLESS por default; qualquer lossy cruza linha filosofica e exige GATE real-world N>=5 + decisao owner.
A pergunta do owner: "revisar as atividades e ver prioridades pra FECHAR o que pudermos do 0.7."
"Fechar" pode ser: (a) terminar implementacao curta; (b) tomar/registrar decisao; (c) PARK explicito como pos-0.7/v2.0
com rationale de 1 linha pra limpar o quadro; (d) marcar done o que ja' esta' efetivamente pronto.
`

const ASSESS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['id', 'title', 'current_status', 'belongs', 'remaining_work', 'disposition', 'effort', 'value_to_07', 'blockers', 'recommendation'],
  properties: {
    id: { type: 'string' },
    title: { type: 'string' },
    current_status: { type: 'string', description: 'status atual lido do arquivo (frontmatter/prosa)' },
    belongs: { type: 'string', enum: ['core-0.7', 'adjacente', 'v2.0-ou-pos-1.0', 'gadget-externo'] },
    remaining_work: { type: 'string', description: 'o que falta concretamente; "" se nada' },
    disposition: { type: 'string', enum: ['close-done', 'close-as-parked', 'small-finish', 'needs-owner-decision', 'defer-v2.0', 'keep-open'] },
    effort: { type: 'string', enum: ['none', 'S', 'M', 'L'] },
    value_to_07: { type: 'string', enum: ['high', 'med', 'low', 'none'] },
    blockers: { type: 'string' },
    recommendation: { type: 'string', description: '1-3 frases, acionavel; sem superlativos' },
  },
}

const ITEMS = [
  { id: 'T-CODE-ENCODER-MANAGER', src: 'tickets/T-CODE-ENCODER-MANAGER.md' },
  { id: 'T-CODE-OUTPUT-SINKS', src: 'tickets/T-CODE-OUTPUT-SINKS.md' },
  { id: 'T-CODE-PLAN-CONTRACT', src: 'tickets/T-CODE-PLAN-CONTRACT.md' },
  { id: 'T-CODE-SCHEMA-BUILDER', src: 'tickets/T-CODE-SCHEMA-BUILDER.md' },
  { id: 'T-CODE-LAYERED-PIPELINE', src: 'tickets/T-CODE-LAYERED-PIPELINE.md' },
  { id: 'T-SHAPER-CODE-HARDENING', src: 'tickets/T-SHAPER-CODE-HARDENING.md' },
  { id: 'T-DIST-PYPI-NAME', src: 'tickets/T-DIST-PYPI-NAME.md' },
  { id: 'T-FIX-SHAPER-STRATIFY-TEST', src: 'tickets/T-FIX-SHAPER-STRATIFY-TEST.md' },
  { id: 'META-TYPE-ENCODERS', src: 'tickets/META-TYPE-ENCODERS.md' },
  { id: 'T-RECOVER-LLM-SCHEMA-MODE', src: 'tickets/T-RECOVER-LLM-SCHEMA-MODE.md' },
  { id: 'T-H-PERF-06-V2-T01-WELD-15', src: 'tickets/T-H-PERF-06-V2-T01-WELD-15.md' },
  { id: 'T-H-PERF-06-V2-T02-CYTHON', src: 'tickets/T-H-PERF-06-V2-T02-CYTHON.md' },
  { id: 'V2-C-lossy-decision', src: 'experiments/lab/dirty/2026-06-14-v2c-lossy-round-caracterizacao/result.md ; docs/adr/0018-v2-format-roadmap.md (secao V2-C)' },
  { id: 'Pacote-10-LOSS', src: 'experiments/lab/dirty/notas/loss-taxonomia.md ; roadmap-hipoteses.md (Pacote 10)' },
  { id: 'V2-B-RLE-stream-followup', src: 'experiments/lab/dirty/2026-06-14-v2b-dicionario-caracterizacao/result.md ; docs/adr/0025-v2b-dictionary-categorical-weld.md' },
  { id: 'V2-roadmap-remaining', src: 'docs/adr/0018-v2-format-roadmap.md (V2-D/V2-J/V2-K/V2-L + estado geral)' },
]

phase('Inventario')
const assessments = await parallel(ITEMS.map((it) => () =>
  agent(
    `Voce avalia UM item aberto do projeto TCF para decidir como fecha-lo no ciclo 0.7.\n${CYCLE}\n\n` +
    `ITEM: ${it.id}\nFONTE(S) (relativo a ${ROOT}): ${it.src}\n\n` +
    `Leia a(s) fonte(s) com Read/Grep (use ${ROOT} como base). Se for um ticket, leia o frontmatter YAML (status) e o corpo. ` +
    `Para itens de decisao/lab, leia o result/taxonomia e a secao relevante do ADR.\n\n` +
    `Avalie objetivamente:\n` +
    `- current_status: o status REAL lido (nao invente).\n` +
    `- belongs: o item e' core do 0.7 (bytes/formato textual), adjacente (tooling/dist/test), v2.0-ou-pos-1.0 (exige format change grande ou e' explicitamente futuro), ou gadget-externo (nao TCF-core)?\n` +
    `- remaining_work: o que CONCRETAMENTE falta. Se ja' efetivamente pronto, "".\n` +
    `- disposition: close-done (ja' feito, so' marcar) / small-finish (cabe agora, baixo esforco/risco) / needs-owner-decision (cruza linha filosofica ou e' escolha do owner) / defer-v2.0 (adiar com rationale) / close-as-parked (encerrar como pos-0.7 sem fazer) / keep-open (segue ativo).\n` +
    `- effort: none/S(<1h)/M(algumas h)/L(dias). value_to_07: quanto move a agulha de bytes/fechamento do 0.7.\n` +
    `- blockers: dependencias (ex: "bloqueado por encoder-manager", "exige aprovacao src/tcf", "GATE N>=5").\n` +
    `- recommendation: acionavel, 1-3 frases, SEM superlativos. Se tocar src/tcf, diga que exige aprovacao explicita.\n\n` +
    `Retorne SO o objeto estruturado.`,
    { label: `assess:${it.id}`, phase: 'Inventario', schema: ASSESS_SCHEMA, agentType: 'Explore' }
  )
))

const valid = assessments.filter(Boolean)

phase('Sintese')
const SYNTH_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['resumo_estado_07', 'fechar_agora', 'decisoes_owner', 'adiar_explicito', 'ja_pronto', 'sequencia_recomendada', 'riscos'],
  properties: {
    resumo_estado_07: { type: 'string', description: '2-4 frases: onde o 0.7 esta' },
    fechar_agora: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'acao', 'effort', 'porque'], properties: { id: { type: 'string' }, acao: { type: 'string' }, effort: { type: 'string' }, porque: { type: 'string' } } }, description: 'itens que EU posso terminar/fechar agora com baixo risco' },
    decisoes_owner: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'pergunta', 'opcoes', 'recomendacao'], properties: { id: { type: 'string' }, pergunta: { type: 'string' }, opcoes: { type: 'string' }, recomendacao: { type: 'string' } } }, description: 'o que somente o owner decide' },
    adiar_explicito: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'rationale'], properties: { id: { type: 'string' }, rationale: { type: 'string' } } }, description: 'park/defer com rationale 1 linha' },
    ja_pronto: { type: 'array', items: { type: 'string' }, description: 'itens efetivamente prontos, apenas marcar status' },
    sequencia_recomendada: { type: 'array', items: { type: 'string' }, description: 'ordem de execucao pra fechar 0.7' },
    riscos: { type: 'string', description: 'riscos/armadilhas de fechar (GATE, src/tcf, lossless)' },
  },
}

const synthesis = await agent(
  `Voce e' o planner de fechamento do ciclo 0.7 do TCF.\n${CYCLE}\n\n` +
  `Recebeu ${valid.length} avaliacoes estruturadas dos itens abertos:\n\n` +
  JSON.stringify(valid, null, 2) +
  `\n\nProduza um plano de fechamento do 0.7. Regras:\n` +
  `- Separe claramente: fechar_agora (eu executo, baixo risco, NAO toca src/tcf sem aprovacao), decisoes_owner (so' o owner), adiar_explicito (park com rationale), ja_pronto (so' marcar status).\n` +
  `- NAO proponha tocar src/tcf como "fechar_agora" — isso e' sempre decisao/aprovacao do owner.\n` +
  `- sequencia_recomendada: ordem pragmatica, comecando pelo que limpa mais o quadro com menor risco.\n` +
  `- Seja honesto: muito do 0.7 (bytes) ja' esta' welded; "fechar" aqui e' em boa parte higiene de tickets + 2 decisoes do owner.\n` +
  `- Vocabulario disciplinado, SEM superlativos.\n` +
  `Retorne SO o objeto estruturado.`,
  { label: 'synth:close-07', phase: 'Sintese', schema: SYNTH_SCHEMA }
)

return { assessments: valid, synthesis }

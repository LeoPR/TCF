export const meta = {
  name: 'h-perf-06-v2-fase-a',
  description: 'H-PERF-06-v2 Fase A: prune algoritmico + early-term em HCC _detect_compositions, format-safe',
  phases: [
    { title: 'Map' },
    { title: 'Baseline' },
    { title: 'Propose' },
    { title: 'Verify' },
    { title: 'Prototype' },
    { title: 'Measure' },
    { title: 'Synthesize' },
  ]
}

const MAP_SCHEMA = {
  type: 'object',
  required: ['summary', 'hotspot_function', 'loops', 'data_structures', 'callers', 'byte_canonical_tests'],
  additionalProperties: true,
  properties: {
    summary: { type: 'string' },
    hotspot_function: {
      type: 'object',
      required: ['file', 'line_start', 'line_end', 'signature', 'returns'],
      properties: {
        file: { type: 'string' },
        line_start: { type: 'integer' },
        line_end: { type: 'integer' },
        signature: { type: 'string' },
        returns: { type: 'string' }
      }
    },
    loops: {
      type: 'array',
      items: {
        type: 'object',
        required: ['location', 'bounds', 'complexity', 'what_iterates'],
        properties: {
          location: { type: 'string' },
          bounds: { type: 'string' },
          complexity: { type: 'string' },
          what_iterates: { type: 'string' }
        }
      }
    },
    data_structures: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'usage', 'alloc_pattern'],
        properties: {
          name: { type: 'string' },
          usage: { type: 'string' },
          alloc_pattern: { type: 'string' }
        }
      }
    },
    callers: {
      type: 'array',
      items: {
        type: 'object',
        required: ['file', 'line', 'context'],
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          context: { type: 'string' }
        }
      }
    },
    byte_canonical_tests: {
      type: 'array',
      items: {
        type: 'object',
        required: ['test_file', 'what_locks'],
        properties: {
          test_file: { type: 'string' },
          what_locks: { type: 'string' }
        }
      }
    },
    notes: { type: 'string' }
  }
}

const BASELINE_SCHEMA = {
  type: 'object',
  required: ['dataset', 'top_functions', 'detect_compositions_pct', 'total_time_sec'],
  additionalProperties: true,
  properties: {
    dataset: { type: 'string' },
    runner_script: { type: 'string' },
    total_time_sec: { type: 'number' },
    detect_compositions_pct: { type: 'number' },
    top_functions: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'cumtime_sec', 'pct', 'calls'],
        properties: {
          name: { type: 'string' },
          cumtime_sec: { type: 'number' },
          pct: { type: 'number' },
          calls: { type: 'integer' }
        }
      }
    },
    confirms_88pct_hypothesis: { type: 'boolean' },
    notes: { type: 'string' }
  }
}

const PROPOSAL_SCHEMA = {
  type: 'object',
  required: ['lens', 'candidates'],
  properties: {
    lens: { type: 'string' },
    candidates: {
      type: 'array',
      minItems: 1,
      items: {
        type: 'object',
        required: ['id', 'title', 'description', 'where_in_code', 'code_sketch', 'expected_speedup_pct', 'risk_byte_canonical'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          description: { type: 'string' },
          where_in_code: { type: 'string' },
          code_sketch: { type: 'string' },
          expected_speedup_pct: { type: 'number' },
          risk_byte_canonical: { type: 'string', enum: ['none', 'low', 'medium', 'high'] },
          rationale: { type: 'string' }
        }
      }
    }
  }
}

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['candidate_id', 'safety', 'reasoning', 'preserves_d1_d9', 'preserves_d17a', 'requires_prototype'],
  properties: {
    candidate_id: { type: 'string' },
    safety: { type: 'string', enum: ['SAFE', 'NEEDS_PROTOTYPE', 'UNSAFE'] },
    reasoning: { type: 'string' },
    preserves_d1_d9: { type: 'string', enum: ['yes', 'no', 'unknown'] },
    preserves_d17a: { type: 'string', enum: ['yes', 'no', 'unknown'] },
    requires_prototype: { type: 'boolean' },
    breaks_which_scenarios: { type: 'string' }
  }
}

const PROTO_SCHEMA = {
  type: 'object',
  required: ['candidate_id', 'lab_dir', 'status', 'regression_passed'],
  properties: {
    candidate_id: { type: 'string' },
    lab_dir: { type: 'string' },
    status: { type: 'string', enum: ['PROTOTYPED', 'FAILED_BUILD', 'FAILED_REGRESSION'] },
    regression_passed: { type: 'boolean' },
    actual_bytes_d1_d9: { type: 'integer' },
    actual_bytes_d17a: { type: 'integer' },
    notes: { type: 'string' },
    runner_script_path: { type: 'string' },
    forked_file_path: { type: 'string' }
  }
}

const MEASURE_SCHEMA = {
  type: 'object',
  required: ['candidate_id', 'lab_dir', 'baseline_time_sec', 'variant_time_sec', 'speedup_factor'],
  properties: {
    candidate_id: { type: 'string' },
    lab_dir: { type: 'string' },
    baseline_time_sec: { type: 'number' },
    variant_time_sec: { type: 'number' },
    speedup_factor: { type: 'number' },
    detect_compositions_pct_after: { type: 'number' },
    notes: { type: 'string' },
    measurement_dataset: { type: 'string' }
  }
}

const REPORT_SCHEMA = {
  type: 'object',
  required: ['summary', 'safe_candidates_count', 'top_3_recommended', 'amdahl_assessment', 'next_steps'],
  properties: {
    summary: { type: 'string' },
    safe_candidates_count: { type: 'integer' },
    prototyped_count: { type: 'integer' },
    top_3_recommended: {
      type: 'array',
      maxItems: 5,
      items: {
        type: 'object',
        required: ['candidate_id', 'speedup', 'rationale'],
        properties: {
          candidate_id: { type: 'string' },
          speedup: { type: 'number' },
          rationale: { type: 'string' }
        }
      }
    },
    amdahl_assessment: { type: 'string' },
    unsafe_with_lessons: { type: 'string' },
    next_steps: { type: 'string' },
    open_questions: { type: 'string' }
  }
}

phase('Map')
log('Mapeando _detect_compositions e helpers + identificando tests byte-canonical')

const mapPrompt = [
  'Voce e o agente de MAPEAMENTO para H-PERF-06-v2 Fase A. Missao:',
  '',
  '1. Read EXAUSTIVAMENTE src/tcf/composicional/syntax.py (inteira). Foco especial em _detect_compositions (linhas 225-362).',
  '2. Read src/tcf/composicional/hcc_seqrle.py.',
  '3. Read src/tcf/encoder.py — encontrar TODAS as chamadas a _detect_compositions ou HCCDetector.processar. Documentar callers.',
  '4. Glob tests/**/test_*.py e identifique tests que travam byte-canonical (D1-D9 = 1523B total, D17a = 322B). Procurar test_regression_v1_baseline.py.',
  '5. Glob scripts/benchmark_*.py — listar scripts disponiveis.',
  '6. Documente cada loop dentro de _detect_compositions com bounds reais e complexity O(.) e o que itera.',
  '7. Documente data structures (Counter, dict, tuple, set) e alloc pattern.',
  '8. Mapeie helpers como _estimate_baseline_chars.',
  '',
  'Retorne JSON conforme MAP_SCHEMA. Seja exaustivo. Cite linha exata sempre (file:line).',
  'NAO modifique nenhum arquivo. So leitura.'
].join('\n')

const map = await agent(mapPrompt, { schema: MAP_SCHEMA, label: 'map-hcc' })

phase('Baseline')
log('Rodando cProfile baseline pra confirmar 88% em _detect_compositions')

const baselinePrompt = [
  'Voce e o agente de BASELINE PROFILE para H-PERF-06-v2 Fase A.',
  '',
  'Profile-alvo: confirmar (ou refutar) que _detect_compositions em HCC consome ~88% do tempo de encode.',
  '',
  'Plano:',
  '1. Identifique o dataset alvo. Preferencial: online-retail 20k. Buscar em datasets/ ou Z:/tcf-data/. Fallbacks:',
  '   - Adult census ou TPC-H lineitem em Z:/tcf-data/interim/*.db (via scripts/dataset_reader.py)',
  '   - Sintetico 5k-20k linhas com strings repetitivas',
  '2. CRIE o diretorio experiments/lab/dirty/old/welded/2026-05-27-h-perf-06-v2-fase-a/ se nao existir.',
  '3. Adicione um README.md curto explicando "Fase A — prune algoritmico + early-term em HCC _detect_compositions, dirty lab".',
  '4. Crie experiments/lab/dirty/old/welded/2026-05-27-h-perf-06-v2-fase-a/00-baseline/runner.py que:',
  '   - Carrega o dataset',
  '   - Roda from tcf import encode em cProfile',
  '   - Salva stats em baseline.prof',
  '   - Imprime top 20 funcoes',
  '5. Execute via Bash: python -m cProfile -o baseline.prof runner.py',
  '   Parse stats com pstats pra extrair top funcs.',
  '6. Reporte: dataset, top_functions (cumtime + pct + calls), detect_compositions_pct, total_time_sec, confirms 88%.',
  '',
  'NAO modifique src/tcf. Se Bash falhar, documente em notes em vez de fingir.',
  'Retorne JSON conforme BASELINE_SCHEMA.'
].join('\n')

const baseline = await agent(baselinePrompt, { schema: BASELINE_SCHEMA, label: 'baseline-profile' })

log('Baseline: ' + (baseline?.detect_compositions_pct ?? '?') + '% em _detect_compositions, total ' + (baseline?.total_time_sec ?? '?') + 's em ' + (baseline?.dataset ?? '?'))

phase('Propose')
log('6 lenses geram candidatos prune + early-term + micro-opts em paralelo')

const LENSES = [
  {
    key: 'prune-k',
    desc: 'Prune por comprimento minimo de sub-tupla (K menor que 3)',
    detail: 'Sub-tuplas com K muito pequeno raramente compensam o overhead de criar alias. Investigar threshold ideal (K=2? K=3?). Propor variantes que skip sub-tuplas curtas.'
  },
  {
    key: 'prune-singleton',
    desc: 'Prune sub-tuplas que aparecem 1x (singletons inuteis pra dedup)',
    detail: 'Counter.update conta tudo, mas sub-tuplas com count==1 nunca viram alias. Variantes: pre-filtrar via probabilidade (chave hash), ou descobrir singletons em 1 pass e skip no 2-pass.'
  },
  {
    key: 'early-iter',
    desc: 'Early termination apos N iter sem novo alias',
    detail: 'HCC e iterativo ate convergencia. Se N iteracoes consecutivas nao produzem novo alias, parar. N tipico: 2-3. Variantes com diferentes N e criterios.'
  },
  {
    key: 'early-gain',
    desc: 'Early termination se ganho por iter abaixo de threshold (bytes ou %)',
    detail: 'Mesmo se houver novo alias, se o ganho real (bytes economizados) cai abaixo de threshold, parar. Threshold: 5%, 1%, 0.5%. Trade speedup vs cobertura HCC.'
  },
  {
    key: 'tier-scoring',
    desc: 'Prune por tier de scoring HCC (so processar sub-tuplas com score promissor)',
    detail: 'HCC tem heuristica de scoring (length * occurrences - overhead). Pre-score sub-tuplas e processar so as top-tier. Variantes: top-50%, top-25%, threshold absoluto.'
  },
  {
    key: 'micro-opt',
    desc: 'Micro-opts em data structures (Counter, tuple, bytes, dict)',
    detail: 'tuple(refs[a:b]) aloca. bytes pode ser mais rapido. Counter() vs dict com tuple-int. Hash de tupla pode ser cached. Variantes ortogonais aos prunes.'
  },
]

function buildProposalPrompt(lens, mapCtx, baseCtx) {
  return [
    'Voce e a lente ' + lens.key + ' para H-PERF-06-v2 Fase A.',
    '',
    'Especializacao: ' + lens.desc,
    '',
    'Detalhe da lente: ' + lens.detail,
    '',
    'Contexto do mapa de codigo (truncado):',
    JSON.stringify(mapCtx ?? { summary: 'map indisponivel' }, null, 2).slice(0, 8000),
    '',
    'Baseline observado (truncado):',
    JSON.stringify(baseCtx ?? { note: 'baseline indisponivel' }, null, 2).slice(0, 2000),
    '',
    'Tarefa: Gerar 2 a 4 candidatos concretos dentro da sua lente. Cada candidato deve ter:',
    '- id: slug unico no formato ' + lens.key + '-NN-shortname (e.g. ' + lens.key + '-01-skipK2)',
    '- title: titulo curto',
    '- description: 2-3 paragrafos',
    '- where_in_code: file:line range',
    '- code_sketch: pseudocode ou mini-diff mostrando a mudanca',
    '- expected_speedup_pct: estimativa percentual overall (realistic, considere Amdahl)',
    '- risk_byte_canonical: none | low | medium | high',
    '- rationale: por que esse candidato faz sentido',
    '',
    'REGRAS:',
    '- Leia src/tcf/composicional/syntax.py se precisar pra escrever code_sketch realista.',
    '- Candidatos devem ser mutuamente distintos dentro da sua lente.',
    '- NAO sugira coisas fora da sua lente.',
    '- Seja honesto em risk_byte_canonical: prunes que reduzem cobertura HCC = high risk.',
    '- NAO modifique nenhum arquivo. So propor.',
    '',
    'Retorne JSON conforme PROPOSAL_SCHEMA.'
  ].join('\n')
}

const proposals = await parallel(LENSES.map(lens => () =>
  agent(buildProposalPrompt(lens, map, baseline), {
    schema: PROPOSAL_SCHEMA,
    label: 'propose:' + lens.key,
    phase: 'Propose'
  })
))

const allCandidates = proposals.filter(Boolean).flatMap(p => (p.candidates ?? []).map(c => ({ ...c, lens: p.lens })))
log(allCandidates.length + ' candidatos gerados em ' + proposals.filter(Boolean).length + '/6 lenses')

phase('Verify')
log('Verificando byte-canonical impact em ' + allCandidates.length + ' candidatos (adversarial)')

function buildVerifyPrompt(c) {
  return [
    'Voce e o verificador adversarial BYTE-CANONICAL para o candidato ' + c.id + ' de H-PERF-06-v2 Fase A.',
    '',
    'Candidato sob analise:',
    JSON.stringify(c, null, 2),
    '',
    'Missao: REFUTAR ou CONFIRMAR que este candidato preserva byte-canonical D1-D9 = 1523B total + D17a = 322B exatos.',
    '',
    'Default to SAFETY: na duvida, classifique como NEEDS_PROTOTYPE. Apenas marque SAFE se OBVIAMENTE format-safe (micro-opt puramente algoritmica sem mudar output).',
    '',
    'Analise adversarial:',
    '1. Cobertura HCC: prune ou early-term pode causar omissao de alias que existe no baseline?',
    '2. Order-dependent: HCC depende da ordem de iteracao? Mudar ordem pode mudar tie-break.',
    '3. Convergencia: se early-term, em quais datasets D1-D9 ou D17a HCC roda mais de N iter?',
    '4. Singletons inuteis?: skippar pode mudar contagem de outros?',
    '5. Tier-scoring threshold: top-50% pode descartar sub-tuplas que entram no baseline.',
    '',
    'Procedure: leia src/tcf/composicional/syntax.py area relevante. Leia datasets/synthetic/ ou tests/ pra entender D1-D9 e D17a.',
    '',
    'Classificacao:',
    '- SAFE: 100% certeza que NAO muda bytes',
    '- NEEDS_PROTOTYPE: provavelmente safe mas precisa medir (default pra duvida)',
    '- UNSAFE: VAI mudar bytes (prune agressivo que omite aliases reais)',
    '',
    'Retorne JSON conforme VERDICT_SCHEMA, reasoning de 3-5 paragrafos. NAO modifique nada.'
  ].join('\n')
}

const verified = await parallel(allCandidates.map(c => () =>
  agent(buildVerifyPrompt(c), {
    schema: VERDICT_SCHEMA,
    label: 'verify:' + c.id,
    phase: 'Verify'
  }).then(v => ({ ...c, verdict: v }))
))

const verifiedClean = verified.filter(Boolean)
const safe = verifiedClean.filter(c => c.verdict && c.verdict.safety !== 'UNSAFE')
const unsafe = verifiedClean.filter(c => c.verdict && c.verdict.safety === 'UNSAFE')
log('Verificados: ' + safe.length + ' SAFE/NEEDS_PROTOTYPE, ' + unsafe.length + ' UNSAFE')

function buildProtoPrompt(c, labSubDir) {
  return [
    'Voce e o PROTOTIPADOR para o candidato ' + c.id + ' de H-PERF-06-v2 Fase A.',
    '',
    'Candidato:',
    JSON.stringify(c, null, 2),
    '',
    'Diretorio designado (CRIE com Bash mkdir -p): ' + labSubDir,
    '',
    'Tarefa:',
    '1. Criar o diretorio ' + labSubDir + '/ via Bash.',
    '2. Copiar src/tcf/composicional/syntax.py para ' + labSubDir + '/syntax_variant.py.',
    '3. Aplicar o code_sketch do candidato no syntax_variant.py (modificar SOMENTE o arquivo COPIADO, NUNCA o original).',
    '4. Criar ' + labSubDir + '/runner_regression.py que:',
    '   - Importa o syntax_variant via importlib.util.spec_from_file_location',
    '   - Monkey-patches src.tcf.composicional.syntax._detect_compositions (ou nome real) com a versao do variant',
    '   - Roda from tcf import encode em datasets D1-D9 (procurar em datasets/synthetic/) e D17a',
    '   - Concatena bytes totais D1-D9 e compara com 1523. D17a sozinho compara com 322.',
    '   - Imprime PASS/FAIL e bytes reais.',
    '5. Executar o runner_regression via Bash.',
    '6. Reportar:',
    '   - status: PROTOTYPED se OK; FAILED_BUILD se import falhou; FAILED_REGRESSION se bytes mudaram',
    '   - regression_passed: true sse D1-D9 = 1523 E D17a = 322',
    '   - actual_bytes_d1_d9 e actual_bytes_d17a observados',
    '',
    'NUNCA modificar src/tcf/. Tudo em ' + labSubDir + '/.',
    'Se a chamada era em metodo de classe (HCCDetector), pode precisar monkey-patch o metodo da classe.',
    'Se datasets D1-D9/D17a nao existirem nominalmente, procurar em datasets/synthetic/ por padroes.',
    '',
    'Retorne JSON conforme PROTO_SCHEMA.'
  ].join('\n')
}

function buildMeasurePrompt(proto, baseCtx) {
  return [
    'Voce e o MEDIDOR para o variant prototipado:',
    JSON.stringify(proto, null, 2),
    '',
    'Baseline pra comparar:',
    JSON.stringify(baseCtx, null, 2).slice(0, 2000),
    '',
    'Tarefa:',
    '1. No diretorio ' + proto.lab_dir + ', criar runner_profile.py que:',
    '   - Replica o setup do baseline (mesmo dataset, mesmo encode)',
    '   - Monkey-patches syntax_variant igual ao runner_regression',
    '   - Roda cProfile pelo mesmo dataset usado no baseline',
    '   - Salva variant.prof',
    '   - Imprime top 20 funcs + tempo total',
    '2. Executar via Bash.',
    '3. Comparar:',
    '   - baseline_time_sec',
    '   - variant_time_sec',
    '   - speedup_factor = baseline/variant',
    '   - detect_compositions_pct_after',
    '4. Se algo falhar, reportar 0 com notes.',
    '',
    'Retorne JSON conforme MEASURE_SCHEMA.'
  ].join('\n')
}

const measured = await pipeline(
  safe,
  async (c, original, idx) => {
    const labSubDir = 'experiments/lab/dirty/old/welded/2026-05-27-h-perf-06-v2-fase-a/' + String(idx + 1).padStart(2, '0') + '-' + c.id
    return await agent(buildProtoPrompt(c, labSubDir), {
      schema: PROTO_SCHEMA,
      label: 'proto:' + c.id,
      phase: 'Prototype'
    })
  },
  async (proto, originalCandidate, idx) => {
    if (!proto || proto.status !== 'PROTOTYPED' || !proto.regression_passed) {
      return {
        candidate_id: originalCandidate.id,
        lab_dir: (proto && proto.lab_dir) ? proto.lab_dir : 'unknown',
        baseline_time_sec: baseline?.total_time_sec ?? 0,
        variant_time_sec: 0,
        speedup_factor: 0,
        detect_compositions_pct_after: 0,
        notes: 'Skipped measurement: proto status=' + (proto?.status ?? 'null') + ', regression=' + (proto?.regression_passed ?? 'null'),
        measurement_dataset: 'N/A'
      }
    }
    return await agent(buildMeasurePrompt(proto, baseline), {
      schema: MEASURE_SCHEMA,
      label: 'measure:' + originalCandidate.id,
      phase: 'Measure'
    })
  }
)

const measuredClean = measured.filter(Boolean)
const successful = measuredClean.filter(m => m.speedup_factor > 1)
log('Medidos: ' + measuredClean.length + '; ' + successful.length + ' com speedup > 1')

phase('Synthesize')
log('Consolidando relatorio final')

const synthPrompt = [
  'Voce e o SINTETIZADOR FINAL para H-PERF-06-v2 Fase A.',
  '',
  'MAP (truncado):',
  JSON.stringify(map, null, 2).slice(0, 6000),
  '',
  'BASELINE:',
  JSON.stringify(baseline, null, 2).slice(0, 3000),
  '',
  'PROPOSALS (' + allCandidates.length + ' candidatos, truncado):',
  JSON.stringify(allCandidates, null, 2).slice(0, 8000),
  '',
  'VERIFY VERDICTS (' + verifiedClean.length + ', truncado):',
  JSON.stringify(verifiedClean.map(c => ({
    id: c.id,
    lens: c.lens,
    safety: c.verdict?.safety,
    reasoning: c.verdict?.reasoning
  })), null, 2).slice(0, 6000),
  '',
  'MEASURED (' + measuredClean.length + ', truncado):',
  JSON.stringify(measuredClean, null, 2).slice(0, 6000),
  '',
  'Tarefa: consolidar relatorio final exaustivo (REPORT_SCHEMA).',
  '',
  'Inclua:',
  '- summary: 3-5 paragrafos sobre o que foi descoberto. Honesto: se ninguem deu speedup notavel, diga.',
  '- safe_candidates_count e prototyped_count',
  '- top_3_recommended: ate 5 candidatos com melhor speedup E byte-canonical preservado (regression_passed=true). Cite candidate_id, speedup, rationale.',
  '- amdahl_assessment: dado que _detect_compositions e ' + (baseline?.detect_compositions_pct ?? '?') + '% do tempo, qual o teto teorico de speedup overall se reduzir 50%? 80%?',
  '- unsafe_with_lessons: o que UNSAFE candidates ensinaram sobre cobertura HCC?',
  '- next_steps: Fase B (Cython) ou welding direto?',
  '- open_questions',
  '',
  'Tone: rigoroso, sem superlativos (incrivel, muito melhor, etc — projeto proibe). Conclusoes honestas. Se Amdahl bloqueia, diga.',
  '',
  'Apos retornar JSON, escreva tambem o relatorio em experiments/lab/dirty/old/welded/2026-05-27-h-perf-06-v2-fase-a/REPORT.md em markdown legivel.'
].join('\n')

const report = await agent(synthPrompt, { schema: REPORT_SCHEMA, label: 'synthesis' })

log('H-PERF-06-v2 Fase A complete')

return {
  map,
  baseline,
  proposals_count: allCandidates.length,
  verified_count: verifiedClean.length,
  safe_count: safe.length,
  unsafe_count: unsafe.length,
  measured_count: measuredClean.length,
  successful_count: successful.length,
  report
}

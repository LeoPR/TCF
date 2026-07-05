export const meta = {
  name: 't1-ndjson-brotli-review',
  description: 'Revisao adversarial do T1 (TCF+brotli vs NDJSON/JSON+brotli): fairness, validade, verificacao da conclusao, sintese',
  phases: [
    { title: 'Critique', detail: '4 lentes de fairness/validade lendo harness + results.json' },
    { title: 'Verify', detail: 'ceticos tentam refutar a conclusao a partir dos numeros' },
    { title: 'Synthesize', detail: 'achado honesto + frase de posicionamento + gaps abertos' },
  ],
}

const LAB = 'experiments/lab/dirty/2026-07-05-t1-ndjson-brotli'
const CTX = `Contexto do projeto TCF (leia antes de julgar):
- CLAUDE.md (filosofia: TCF ocupa "areas explicaveis textual"; NAO compete com gzip/brotli
  binario; checklist ANTI-INCIDENTE "antes de declarar confirmada-empirica" com 5 perguntas;
  regra: nunca reportar bytes sem RT; sem superlativos).
- ${LAB}/t1_bench.py (o harness — leia o codigo, ache vies/bug de fairness).
- ${LAB}/results.json (os numeros medidos — TODOS os formatos, scales, datasets, rt_ok).
- experiments/lab/dirty/notas/transmissao-api-onde-tcf-importa.md (o T1 definido: TCF so' tem
  caso de transmissao se vencer NDJSON+brotli em bytes OU oferecer consulta seletiva).
Formatos medidos por (dataset,scale): csv, ndjson_str (valores string), ndjson_typed (numeros
sem aspas quando bijetivo = STEELMAN NDJSON), json_array, json_columnar ({col:[...]}, chaves
uma vez = STEELMAN JSON maximo), tcf (v0.7). Metricas: _raw, _gz (gzip-9), _br (brotli q11),
_br5 (brotli q5). rt_ok = decode(tcf)==tabela (obrigatorio).`

const FINDINGS_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['lens', 'fairness_verdict', 'objections', 'additional_measurements'],
  properties: {
    lens: { type: 'string' },
    fairness_verdict: { type: 'string', enum: ['fair', 'minor-issues', 'major-issues', 'invalid'] },
    objections: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['severity', 'claim', 'evidence', 'remedy'],
        properties: {
          severity: { type: 'string', enum: ['blocker', 'high', 'medium', 'low'] },
          claim: { type: 'string' },
          evidence: { type: 'string' },
          remedy: { type: 'string' },
        },
      },
    },
    additional_measurements: { type: 'array', items: { type: 'string' } },
    what_holds: { type: 'string' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['refuted', 'reason', 'strongest_counterexample'],
  properties: {
    refuted: { type: 'boolean' },
    reason: { type: 'string' },
    strongest_counterexample: { type: 'string' },
  },
}

// --- Fase 1: painel de critica de fairness/validade (4 lentes independentes) ---
const LENSES = [
  { key: 'steelman', prompt: `${CTX}

LENTE A — FAIRNESS DO CONCORRENTE (steelman NDJSON/JSON). Voce e' advogado do NDJSON.
O TCF esta' sendo comparado de forma JUSTA, ou o harness da' vantagem indevida ao TCF?
Cheque: (1) ndjson_typed realmente e' o NDJSON mais compacto honesto? (2) json_columnar
(chaves uma vez) e' o steelman JSON correto e esta' bem construido? (3) ha' alguma
representacao textual JSON/NDJSON AINDA mais compacta e legitima que faltou? (4) o TCF
esta' recebendo algum tratamento que o concorrente nao recebe (ex: exclusao de coluna,
ordenacao, encoding)? (5) as duas variantes NDJSON round-trip pra mesma data logica que o
TCF (RT)? Aponte objecoes concretas com evidencia dos numeros em results.json.` },

  { key: 'validity', prompt: `${CTX}

LENTE B — VALIDADE ESTATISTICA/SELECAO (Wohlin threats-to-validity + checklist anti-incidente
5-perguntas do CLAUDE.md). Cheque: (1) selecao de datasets tem vies (so' TCF-favoraveis)? o
espectro favor="favoravel/misto/desfavoravel" cobre o caso onde TCF PERDE? (2) N>=5 reais de
fontes diferentes? (3) sintetico vs real (aqui todos reais — ok)? (4) ha' anomalia nos numeros
(ex: nao-monotonicidade byte vs scale — ibge 5000 vs 5571)? investigue e explique ou marque.
(5) bytes ABSOLUTOS relevantes (>=5% e escala real de transmissao)? o ganho % se traduz em bytes
que importam? Aponte objecoes com evidencia.` },

  { key: 'codec', prompt: `${CTX}

LENTE C — FAIRNESS DO CODEC. Cheque: (1) brotli q11 (_br) e' justo (melhor de cada) mas q5 (_br5,
HTTP dinamico) muda a conclusao? compare _br vs _br5 no results.json — o TCF ainda vence em q5?
(2) gzip (_gz) como controle — a conclusao e' consistente entre gzip e brotli? (3) a janela do
brotli/gzip afeta datasets grandes (10k) diferente de pequenos? (4) algum confound de codec
(ex: brotli tem dicionario embutido de web/JSON que ajuda o NDJSON)? (5) a comparacao deveria
incluir zstd? isso mudaria o veredito de POSICIONAMENTO (textual+explicavel) ou nao? Objecoes
com evidencia dos _br5/_gz.` },

  { key: 'interpret', prompt: `${CTX}

LENTE D — INTERPRETACAO/POSICIONAMENTO. O T1 (transmissao-api note) pergunta: "TCF+brotli vence
NDJSON+brotli?" — o resultado RESOLVE isso? Cheque: (1) qual e' a headline HONESTA (onde vence,
por quanto, onde perde/empata)? (2) o ganho vs NDJSON e' o mesmo que vs CSV (ja' sabido) ou novo?
(3) o que T1 NAO resolve e fica aberto (T2 break-even, T3 cardinalidade, custo de decode, Parquet
invisivel, payloads reais <1KB onde TCF perde)? (4) a filosofia do projeto (TCF complementa, nao
compete com binario) — o resultado confirma "pre-processo textual antes do brotli"? (5) risco de
over-claim (anti-incidente): a frase de posicionamento resultante seria honesta? Objecoes +
o que legitimamente SE SUSTENTA (what_holds).` },
]

phase('Critique')
const critiques = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `critique:${l.key}`, phase: 'Critique', schema: FINDINGS_SCHEMA })
))
const valid = critiques.filter(Boolean)
const blockers = valid.flatMap(c => (c.objections || []).filter(o => o.severity === 'blocker'))
const measurements = [...new Set(valid.flatMap(c => c.additional_measurements || []))]
log(`Critique: ${valid.length}/4 lentes; ${blockers.length} blockers; ${measurements.length} medicoes extras sugeridas`)

// --- Fase 2: verificacao adversarial da conclusao (5 ceticos independentes) ---
phase('Verify')
const CLAIM = `A partir de ${LAB}/results.json: "Em batch tabular real >~1k linhas, TCF+brotli
produz MENOS bytes que NDJSON+brotli (ambas variantes str/typed) E que json_columnar+brotli
(steelman JSON maximo, chaves uma vez), em TODOS os datasets medidos; a margem e' grande em
low-card (adult ~40%) e menor em misto/desfavoravel (~5-15%); RT do TCF passa em todos. Logo o
'teste decisivo' do posicionamento textual se resolve A FAVOR do TCF como pre-processo antes do
brotli — nao so' vs CSV, mas vs o concorrente textual real NDJSON."`
const verdicts = await parallel(Array.from({ length: 5 }, (_, i) => () =>
  agent(`${CTX}

Voce e' um CETICO. Tente REFUTAR esta afirmacao lendo results.json diretamente (nao confie na
prosa — cheque os numeros _br e _br5 por dataset/scale). Procure: um dataset/scale onde
NDJSON+brotli OU json_columnar+brotli <= TCF+brotli; um RT-fail que invalide o TCF ali; uma
nao-monotonicidade que sugira bug; um caso onde a margem some em q5. Se a afirmacao sobrevive ao
seu ataque, diga refuted=false com a razao. Default refuted=true se voce achar QUALQUER
contraexemplo real nos dados. Cetico #${i + 1}.`,
    { label: `verify:${i + 1}`, phase: 'Verify', schema: VERDICT_SCHEMA })
))
const vv = verdicts.filter(Boolean)
const refutes = vv.filter(v => v.refuted).length
log(`Verify: ${refutes}/${vv.length} ceticos refutaram`)

// --- Fase 3: sintese ---
phase('Synthesize')
const synthesis = await agent(`${CTX}

Voce sintetiza o T1 num achado HONESTO pro diario/nota do projeto. Insumos:
- Criticas de fairness (4 lentes): ${JSON.stringify(valid)}
- Veredito adversarial: ${refutes}/${vv.length} ceticos refutaram. Detalhe: ${JSON.stringify(vv)}
- Medicoes extras sugeridas: ${JSON.stringify(measurements)}

Leia results.json voce mesmo pros numeros exatos. Produza (markdown, PT, sobrio, SEM superlativos):
1. HEADLINE (1-2 frases): TCF+brotli vs NDJSON+brotli — resolve o teste decisivo? onde vence,
   por quanto (%), onde a margem e' fina.
2. TABELA-resumo por dataset (scale representativo): tcf_br vs ndjson_typed_br vs json_columnar_br
   vs csv_br + % do TCF sobre cada.
3. SENSIBILIDADE q5 (o TCF ainda vence em brotli q5?) + gzip consistente?
4. Checklist anti-incidente (5 perguntas do CLAUDE.md) respondido explicitamente → confianca
   (Alta/Media/Baixa) e status (confirmada-empirica? com ressalva?).
5. O QUE T1 RESOLVE e o que fica ABERTO (T2-T6, Parquet, decode-cost, payloads <1KB).
6. FRASE DE POSICIONAMENTO honesta (atualiza a de transmissao-api note) + implicacao pro README.
7. Blockers/objecoes que exigem medicao extra ANTES de weld/registro (se houver).`,
  { label: 'synthesize', phase: 'Synthesize' })

return {
  n_critiques: valid.length,
  blockers: blockers.length,
  refutes: `${refutes}/${vv.length}`,
  additional_measurements: measurements,
  synthesis,
}

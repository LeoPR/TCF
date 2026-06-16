export const meta = {
  name: 'readme-consistency-audit',
  description: 'Audita README inteiro contra ground-truth (exemplo 5-col, versoes, imports, links)',
  phases: [
    { title: 'Audit', detail: '3 auditores por dimensao + critico de completude' },
    { title: 'Sintese', detail: 'consolida lista de inconsistencias com fix exato' },
  ],
}

const README = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF/README.md'

const GT = `
GROUND-TRUTH (verdade medida, 2026-06-16) — o README DEVE bater com isto:

EXEMPLO DIDATICO DO TOPO = cadastro de 5 COLUNAS (nome, email, cidade, plano, cpf), 4 linhas.
CPFs usados = placeholders de digitos repetidos: 111.111.111-11 / 222.222.222-22 /
333.333.333-33 / 444.444.444-44 (invalidos por convencao, mas compressiveis pela nature).

Bytes do cadastro (5-col), medidos:
- JSON (json.dumps indent=2): 596 B
- CSV (sem newline final): 277 B
- TCF 0.7 default: 244 B ; meta line = "!44=nome,42=email,28=cidade,20=plano,!cpf"
- TCF #TCF.6 legado (fallback=False, min_header=False): 265 B ;
  shebang "#TCF.6 M" + meta "# 45=nome,42=email,28=cidade,20=plano,76=cpf"
- Compressao HTTP do cadastro: JSON gzip218/br212/zstd211 ; CSV gzip177/br162/zstd165 ;
  TCF gzip209/br185/zstd194. Moldura gzip = ~18 B fixos.
- Filtro CPF (nature=SPEC_CPF): coluna isolada 76->27 B (-64%); cadastro inteiro cru 244->208 B;
  exemplo concreto "111.111.111-11" -> "%g$.u" (14->5 chars).
- EXP-008 (15 datasets SINGLE-COLUMN, niveis maximos, re-rodado 2026-06-16): csv+brotli 1742,
  tcf+brotli 2116, tcf raw 3039. RT 300/300.

VERSAO / FORMATO:
- Pacote (distribuicao) = tcf-format, versao 0.7.1 (badge). Import = "import tcf".
- Formato default = #TCF.7 ("0.7"); #TCF.6 = legado, so' LIDO pelo decoder. Projeto PRE-1.0 (ADR-0024).
- O minor do formato (#TCF.N) != versao do pacote (0.7.1). v2.0 = roadmap futuro.
- ATENCAO: rotulos "v0.6" espalhados (ex: "CANONICAL v0.6 API ... #TCF.6", "Tools shipped (v0.6)")
  estao DEFASADOS — o canonical hoje sai #TCF.7 / 0.7. v0.5 = ciclo LLM acessorio (esse pode ficar).
- Suite: 398 passed, 1 xfailed. Baselines: D1-D9=1523 B, D17a=303 B.

IMPORTS: tanto "from tcf import SPEC_CPF" quanto "from tcf.natures import SPEC_CPF" funcionam.
PADRONIZAR em "from tcf import SPEC_CPF" (top-level, mais limpo).

REGRA CPF: NUNCA usar CPF que possa ser real/valido-associavel. Usar so' os placeholders
de digitos repetidos acima. (No README ha' "111.444.777-35" e "529.982.247-25" que sao
CPFs VALIDOS reais-associaveis -> TROCAR pelos placeholders.)
`

const FIND_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['ancora', 'problema', 'severidade', 'fix_sugerido'],
        properties: {
          ancora: { type: 'string', description: 'trecho/linha exata do README onde esta (citar o texto)' },
          problema: { type: 'string', description: 'o que esta inconsistente/defasado vs ground-truth' },
          severidade: { type: 'string', enum: ['quebra', 'numero-errado', 'defasado', 'cosmetico'] },
          fix_sugerido: { type: 'string', description: 'o texto corrigido proposto' },
        },
      },
    },
  },
}

phase('Audit')
const ANGLES = [
  {
    key: 'numeros-exemplo',
    prompt: `Audite NUMEROS e o EXEMPLO DIDATICO. Leia ${README} inteiro. Cheque CADA byte-number, meta line, ` +
      `marker (!@%), e qualquer secao que DISSEQUE o exemplo do topo (ex: "Formato 0.7 / onde os bytes vao", ` +
      `"Como ler", "Resultados", "Filtros"). Tudo deve bater com o cadastro de 5 COLUNAS do ground-truth. ` +
      `Atencao especial: secoes que ainda falem em "4 colunas" ou usem o meta antigo "!44=nome,42=email,28=cidade,plano" ` +
      `(sem cpf) ou bytes 177/182 estao DEFASADAS (o topo agora e' 5-col, 244 B vs 265 B legado). Liste cada discrepancia.`,
  },
  {
    key: 'versao-rotulos',
    prompt: `Audite ROTULOS DE VERSAO/FORMATO. Leia ${README} inteiro. Liste todo lugar que diga v0.6 / 0.7.0 / #TCF.6 ` +
      `como se fosse o ESTADO ATUAL do canonical (deveria ser 0.7 / #TCF.7 / pre-1.0). Distinga: #TCF.6 como LEGADO-LIDO ` +
      `e' correto; "CANONICAL v0.6 API ... #TCF.6" e "Tools shipped (v0.6)" estao DEFASADOS. v0.5 (LLM) pode ficar. ` +
      `Confira tambem o badge (0.7.1) e qualquer "0.7.0" remanescente.`,
  },
  {
    key: 'imports-links-cpf',
    prompt: `Audite IMPORTS, LINKS e SEGURANCA-CPF. Leia ${README} inteiro. (1) Imports: padronizar "from tcf import SPEC_CPF" ` +
      `(o README mistura "from tcf.natures import SPEC_CPF"). (2) CPFs: achar QUALQUER CPF que nao seja placeholder de ` +
      `digitos repetidos (ex: "111.444.777-35", "529.982.247-25" sao VALIDOS -> trocar). (3) Links markdown relativos ` +
      `obviamente quebrados/typos. (4) Blocos de codigo que nao casam com a API atual.`,
  },
]

const audits = await parallel(ANGLES.map((a) => () =>
  agent(GT + '\n\n' + a.prompt + '\n\nUse Read/Grep. Retorne SO o objeto estruturado (findings).',
    { label: `audit:${a.key}`, phase: 'Audit', schema: FIND_SCHEMA, agentType: 'Explore' })
))

const critic = await agent(
  GT + `\n\nVoce e' o CRITICO DE COMPLETUDE. Leia ${README} inteiro (Read) e procure o que os 3 auditores ` +
  `podem ter deixado passar: contradicoes internas, claims defasados, secoes que se referem ao exemplo com ` +
  `numeros velhos, qualquer coisa que um leitor novo acharia inconsistente apos as adicoes recentes (CPF no topo, ` +
  `secao Filtros, secoes "Pra onde vai 1.0" e "Roadmap 2.0"). Retorne SO findings que agreguem (nao repita o obvio).`,
  { label: 'audit:critico', phase: 'Audit', schema: FIND_SCHEMA, agentType: 'Explore' }
)

const all = [...audits.filter(Boolean), critic].filter(Boolean).flatMap((r) => r.findings || [])

phase('Sintese')
const SYNTH_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['resumo', 'fixes'],
  properties: {
    resumo: { type: 'string', description: '1-2 frases: estado de consistencia do README' },
    fixes: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['ancora', 'problema', 'severidade', 'fix_sugerido'],
        properties: {
          ancora: { type: 'string' },
          problema: { type: 'string' },
          severidade: { type: 'string', enum: ['quebra', 'numero-errado', 'defasado', 'cosmetico'] },
          fix_sugerido: { type: 'string' },
        },
      },
      description: 'lista deduplicada e ordenada por severidade (quebra/numero-errado primeiro)',
    },
  },
}

const synthesis = await agent(
  GT + `\n\nRecebeu ${all.length} achados (com duplicatas) dos auditores:\n\n` + JSON.stringify(all, null, 2) +
  `\n\nDEDUPLIQUE (mesma ancora/problema = 1), ordene por severidade (quebra > numero-errado > defasado > cosmetico), ` +
  `e para cada um de' o fix_sugerido exato. Seja preciso e conservador: so' liste o que realmente diverge do ground-truth ` +
  `ou se contradiz. Retorne SO o objeto estruturado.`,
  { label: 'synth:readme', phase: 'Sintese', schema: SYNTH_SCHEMA }
)

return { bruto: all, synthesis }

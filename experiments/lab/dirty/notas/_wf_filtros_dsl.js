export const meta = {
  name: 'filtros-dsl-design',
  description: 'Design: filtros populares modulares via DSL textual human-friendly + "compilador" + plano',
  phases: [
    { title: 'Design', detail: '4 lentes: DSL / compilador / integracao+visual / prior-art+riscos' },
    { title: 'Sintese', detail: 'fluxo end-to-end + plano faseado + revisao critica da ideia' },
  ],
}

const ROOT = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF'

const CTX = `
IDEIA DO OWNER (revisar + planejar fluxo): filtros (natures) populares como **definicoes TEXTUAIS
human-friendly** ("facilidade visual de construcao"), que passam por um **"compilador"** e
integram como natures executaveis e plugaveis. Ou seja: o usuario ESCREVE um filtro de forma
declarativa/legivel (nao em Python), um compilador valida + gera o spec executavel, e ele entra
no registry modular. Filosofia TCF: textual, human-friendly, explicavel; lossless por default.

O QUE JA EXISTE (base — o compilador NAO parte do zero):
- \`src/tcf/natures/\`: Protocol uniforme (encode_value/decode_value/classify_value) + 2 specs
  PARAMETRICOS (ja' sao quase-declarativos — DADOS + uma check_fn):
  - TemplatedCheckedSpec(name, regex, body_length, check_length, check_fn, formatter, encoded_length)
    -> SPEC_CPF / SPEC_CNPJ (strip pontuacao + base-94 pack + regen do digito verificador mod-11).
  - TemplatedPaddedSpec(name, regex, slot_widths, separator) -> SPEC_IP (padding, sem check).
  A UNICA parte "codigo" e' a check_fn (mod-11 CPF/CNPJ, Luhn...) -> pode virar BIBLIOTECA de
  algoritmos nomeados (mod11-cpf, mod11-cnpj, luhn, none), selecionavel por nome na DSL.
- Opt-in: encode(col, nature=SPEC) / nature_per_col; decode precisa do MESMO spec (out-of-band).
- Registrado no roadmap: H-NAT-MARK-01 (marcador de nature no header -> decode reconhece sozinho,
  format change alvo 0.8) e H-NAT-MARK-02 (natures/ vira pasta de PLUGINS).
- FILTRO-NUMERO caracterizado -> PARK (nicho). Filtros populares-alvo: CEP, telefone-BR, MAC,
  data-BR, EAN, alem de CPF/CNPJ/IP ja' welded.

REGRAS: src/tcf so' muda com aprovacao; lossless por default (o compilador DEVE garantir
reversibilidade); gadgets/tooling em scripts/; "barato e nao afeta o nucleo com severidade".
`

const ITEM_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['achados'],
  properties: {
    achados: { type: 'array', items: {
      type: 'object', additionalProperties: false,
      required: ['titulo', 'detalhe', 'tier', 'risco'],
      properties: {
        titulo: { type: 'string' },
        detalhe: { type: 'string', description: 'concreto e acionavel' },
        tier: { type: 'string', enum: ['pre-1.0', '0.8', '2.0-pesquisa', 'gadget', 'transversal'] },
        risco: { type: 'string', description: 'risco/armadilha ou "baixo"' },
      },
    } },
  },
}

phase('Design')
const LENSES = [
  { key: 'dsl', prompt: `Desenhe a **DSL textual human-friendly** do filtro. De' EXEMPLOS concretos da definicao ` +
    `declarativa pra: CPF, CNPJ, IP, CEP, telefone-BR, MAC, data-BR (formato/template, contagem de digitos, ` +
    `algoritmo de check por NOME, padding, packing). Proponha a gramatica/campos (YAML/TOML-like ou mini-grammar), ` +
    `mostrando que e' DECLARATIVA (sem codigo arbitrario) e mapeia nos specs parametricos existentes ` +
    `(TemplatedCheckedSpec/TemplatedPaddedSpec). Inclua o contrato lossless (o que a DSL precisa declarar pra ser reversivel).` },
  { key: 'compilador', prompt: `Desenhe o **"compilador"**: estagios parse -> validar -> build -> registrar. ` +
    `Como VALIDA reversibilidade/lossless (template cobre o valor, check derivavel, packing reversivel; round-trip ` +
    `de teste automatico sobre amostras). Biblioteca de check-fns NOMEADAS (mod11-cpf/cnpj, luhn, none) pra evitar ` +
    `codigo do usuario. Erros amigaveis. ONDE vive (gadget scripts/ vs core). Como gera o spec executavel a partir da DSL.` },
  { key: 'integracao-visual', prompt: `Desenhe a **integracao + a facilidade visual**. Como o spec compilado pluga ` +
    `no registry modular (H-NAT-MARK-02) e em encode/decode (nature_per_col). O **marcador no header** (H-NAT-MARK-01): ` +
    `o spec-id (e/ou a propria DSL compacta) "passeia" com o TCF pra decode reconhecer sozinho -> e' versao (0.8)? ` +
    `A "facilidade visual de construcao": a DSL e' o CONTRATO; um builder visual (form/UI) GERA a DSL. Esboce esse ` +
    `front-end (campos do form -> DSL -> compilador -> preview do encode). Classifique o que e' versao vs nao.` },
  { key: 'priorart-riscos', prompt: `Levante **prior art** e **riscos**. Prior art de DSLs de formato/validacao a se ` +
    `inspirar/reusar: Kaitai Struct, ANTLR/grammar, JSON-Schema/Pydantic, validadores BR (validate-docbr, brazilcep), ` +
    `regex. O que vale BORROW vs over-engineering. RISCOS: garantia lossless de filtro de terceiro; seguranca ` +
    `(nunca executar codigo do usuario — so' DSL declarativa); decode precisa do spec (out-of-band) ate' o header ` +
    `carregar (0.8); colisao de spec-id; manutencao. O que e' barato vs caro.` },
]
const designs = await parallel(LENSES.map((l) => () =>
  agent(CTX + '\n\n' + l.prompt + '\n\nUse Read/Grep em ' + ROOT + ' pra ancorar no codigo real. Retorne SO o objeto estruturado (achados).',
    { label: `design:${l.key}`, phase: 'Design', schema: ITEM_SCHEMA, agentType: 'Explore' })
))
const all = designs.filter(Boolean).flatMap((r) => r.achados || [])

phase('Sintese')
const SYNTH = {
  type: 'object', additionalProperties: false,
  required: ['revisao_critica', 'fluxo', 'dsl_exemplo', 'compilador', 'integracao', 'plano_faseado', 'riscos', 'recomendacao'],
  properties: {
    revisao_critica: { type: 'string', description: '3-5 frases: a ideia se sustenta? onde brilha, onde e arriscada/over-eng' },
    fluxo: { type: 'array', items: { type: 'string' }, description: 'fluxo end-to-end em passos (define -> compila -> registra -> usa -> [header])' },
    dsl_exemplo: { type: 'string', description: 'um exemplo concreto da DSL (ex: CPF) + 1-2 linhas de como fica outro (CEP/telefone)' },
    compilador: { type: 'string', description: 'estagios + como garante lossless + onde vive' },
    integracao: { type: 'string', description: 'registry + header-marker (versao ou nao?) + relacao com o builder visual' },
    plano_faseado: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['fase', 'entrega', 'tier'], properties: { fase: { type: 'string' }, entrega: { type: 'string' }, tier: { type: 'string' } } }, description: 'MVP -> ... ordenado, com tier' },
    riscos: { type: 'array', items: { type: 'string' } },
    recomendacao: { type: 'string', description: 'por onde comecar (barato), sem superlativos' },
  },
}
const synthesis = await agent(
  CTX + `\n\nRecebeu ${all.length} achados de design (4 lentes, com duplicatas):\n\n` + JSON.stringify(all, null, 2) +
  `\n\nSintetize um FLUXO end-to-end + PLANO FASEADO + REVISAO CRITICA da ideia. Seja concreto (mostre a DSL). ` +
  `Diga claramente o que e' pre-1.0 (DSL+compilador como gadget), o que e' 0.8 (spec viaja no header), o que e' ` +
  `2.0/pesquisa (builder visual). Honesto sobre riscos (lossless de terceiro, out-of-band, over-engineering). ` +
  `Comece barato. Vocabulario disciplinado, sem superlativos. Retorne SO o objeto estruturado.`,
  { label: 'synth:filtros-dsl', phase: 'Sintese', schema: SYNTH })

return { bruto: all, synthesis }

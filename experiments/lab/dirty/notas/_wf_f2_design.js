export const meta = {
  name: 'f2-header-nature-design',
  description: 'Design de F2 (H-NAT-MARK-01: spec viaja no header, #TCF.8) + revisao critica + plano sob aprovacao',
  phases: [
    { title: 'Design', detail: '3 lentes: formato do header / resolucao no decode / compat+ADR+gate+tests' },
    { title: 'Sintese', detail: 'vale agora? + plano sob aprovacao + escopo exato do diff em src/tcf' },
  ],
}

const ROOT = 'c:/Users/leona/OneDrive/Documents/Projects/Acadêmicos/TCF'

const CTX = `
F2 = **H-NAT-MARK-01**: o spec/nature-id "viaja" no header pra o decode reconhecer a nature
SOZINHO (hoje e' out-of-band: decode precisa receber o spec). E' **format change #TCF.7 -> #TCF.8**
e **TOCA src/tcf** -> exige APROVACAO EXPLICITA do owner + ADR + GATE + re-pin de baseline.
Este design e' PRE-aprovacao (nao implementa nada no core).

ESTADO REAL (ancorar no codigo):
- Header multi-col (multi.py): linha1 \`#TCF.7 M\`; linha2 meta = pares \`<marcador?><size?>=<nome>\`
  separados por virgula. Marcadores: \`!\`=raw, \`@\`=dict, \`%\`=split, nenhum=tcf. Ultima coluna sem
  size (min_header, corpo ate' EOF). \`~\` e \`,\` sao RESERVADOS (HCC). #TCF.6 (legado) mantem prefixo \`# \`.
- Natures sao **pre-transform** (ADR-0015): \`encode(col, nature=SPEC)\` / \`nature_per_col\` PACKA os
  valores ANTES do pipeline; o header NAO registra que houve nature. decode hoje: \`decode(text,
  nature=SPEC)\` aplica o inverso. Specs: SPEC_CPF/CNPJ (TemplatedCheckedSpec), SPEC_IP (Padded).
  Gadget natures_compiler (F1/F1.5): DSL->spec + registry por nome (cpf/cnpj/ip).
- Default SEM nature preserva byte-canonical: D1-D9=1523B, D17a=303B (#TCF.7). GATE real-world =
  tests/test_real_world_snapshots.py (qualquer mudanca no encode/decode core).
- O gadget lazy (scripts/tcf_lazy/) PARSEIA o header -> qualquer tag nova no meta-line afeta ele.
- "E' versao?": so' o spec viajar no header e' versao (0.8); o resto (DSL/compilador/registry) nao.

CRITERIO REGISTRADO: F2 "so' avancar se houver filtro com ganho >=15% weighted em 2+ datasets reais"
(anti-incidente 2026-05-21). Realidade: CNPJ nature = 40.9% em receita (1 dataset REAL); CPF/IP so'
em sinteticos. Entao a barra "2+ reais" NAO esta' claramente batida pra ganho-de-compressao. MAS F2 e'
INFRA (mecanismo self-describing), nao um filtro novo — o valor e' DX (sem out-of-band) + interop.
BACKWARD-COMPAT obrigatorio: #TCF.7 (sem nature) continua identico; #TCF.8 so' quando ha' nature.
`

const ITEM_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['achados'],
  properties: { achados: { type: 'array', items: {
    type: 'object', additionalProperties: false,
    required: ['titulo', 'detalhe', 'risco'],
    properties: { titulo: { type: 'string' }, detalhe: { type: 'string', description: 'concreto, ancorado no codigo' }, risco: { type: 'string' } },
  } } },
}

phase('Design')
const LENSES = [
  { key: 'header-format', prompt: `Desenhe COMO taggear a nature por coluna no meta-line do #TCF.8, sem ` +
    `colidir com marcadores existentes (!@%) nem com reservados (~ ,). Opcoes concretas (ex: sufixo no nome ` +
    `tipo \`nome:cpf\` ou \`nome#cpf\`; um segmento separado tipo \`...|natures=col:cpf,...\`; ou 3a linha de ` +
    `header). Escolha um e justifique. Mostre o ANTES/DEPOIS do meta-line p/ um cadastro com 1 coluna nature. ` +
    `Defina o que muda no encode (multi.py/encoder.py): registrar quais colunas tiveram nature + o id, e ` +
    `emitir a tag. Backward-compat: #TCF.7 sem nature = identico (nada muda). Leia ${ROOT}/src/tcf/multi.py.` },
  { key: 'decode-resolucao', prompt: `Desenhe COMO o decode resolve o nature-id -> spec executavel pra reverter. ` +
    `BIFURCACAO (analise as 3): (a) CORE-ONLY — so' ids canonicos (cpf/cnpj/ip) resolviveis de src/tcf/natures; ` +
    `terceiros continuam out-of-band; (b) DSL-NO-HEADER — a definicao declarativa compacta viaja junto (auto-contido, ` +
    `qualquer spec, header maior); (c) REGISTRY-COMPARTILHADO — ambos os lados tem o registry (como codebook). ` +
    `Recomende UMA pra F2 (provavelmente a mais simples/segura) e diga o que fazer com id DESCONHECIDO no decode ` +
    `(erro? fallback pro valor cru?). Defina o diff no decoder.py/multi.py. Seguranca: nunca executar codigo do header.` },
  { key: 'compat-adr-gate', prompt: `Desenhe a parte de SEGURANCA DE MUDANCA: (1) backward-compat — #TCF.6/#TCF.7 ` +
    `continuam lidos; #TCF.8 so' emitido quando ha' nature (default off preserva D1-D9=1523/D17a=303 byte-canonical). ` +
    `(2) ADR novo (numero apos 0026) — esboco. (3) GATE: tests/test_real_world_snapshots.py + suite; o que re-pinar ` +
    `(nada deve mudar sem nature). (4) Impacto no gadget lazy (scripts/tcf_lazy/ parseia o header) + no natures_compiler. ` +
    `(5) testes novos (round-trip self-describing: encode com nature -> decode SEM passar nature -> recupera). ` +
    `Liste o escopo EXATO de arquivos src/tcf tocados.` },
]
const designs = await parallel(LENSES.map((l) => () =>
  agent(CTX + '\n\n' + l.prompt + '\n\nUse Read/Grep em ' + ROOT + '. Retorne SO o objeto estruturado (achados).',
    { label: `design:${l.key}`, phase: 'Design', schema: ITEM_SCHEMA, agentType: 'Explore' })
))
const all = designs.filter(Boolean).flatMap((r) => r.achados || [])

phase('Sintese')
const SYNTH = {
  type: 'object', additionalProperties: false,
  required: ['vale_agora', 'header_design', 'resolucao_recomendada', 'diff_src_tcf', 'compat_gate', 'testes', 'adr', 'plano_passos', 'riscos', 'pergunta_aprovacao'],
  properties: {
    vale_agora: { type: 'string', description: 'revisao critica honesta: F2 vale o bump de formato AGORA? (criterio >=15% em 2+ reais nao claramente batido; valor e DX/interop)' },
    header_design: { type: 'string', description: 'a tag escolhida + antes/depois do meta-line' },
    resolucao_recomendada: { type: 'string', description: 'core-only vs dsl-no-header vs registry — qual e por que; id desconhecido' },
    diff_src_tcf: { type: 'array', items: { type: 'string' }, description: 'arquivos src/tcf tocados + o que muda em cada' },
    compat_gate: { type: 'string', description: 'backward-compat + o que NAO pode mudar (D1-D9/D17a) + GATE' },
    testes: { type: 'array', items: { type: 'string' } },
    adr: { type: 'string', description: 'numero + titulo + decisao do ADR novo' },
    plano_passos: { type: 'array', items: { type: 'string' }, description: 'ordem de implementacao (sob aprovacao)' },
    riscos: { type: 'array', items: { type: 'string' } },
    pergunta_aprovacao: { type: 'string', description: 'a pergunta exata a fazer ao owner antes de tocar src/tcf' },
  },
}
const synthesis = await agent(
  CTX + `\n\nRecebeu ${all.length} achados de design (3 lentes):\n\n` + JSON.stringify(all, null, 2) +
  `\n\nSintetize: (1) revisao critica HONESTA "vale agora?" (o criterio >=15% em 2+ reais nao esta' claramente batido; ` +
  `F2 e' infra/DX, default-off, baixo risco se feito direito — pese isso). (2) o design do header. (3) a resolucao ` +
  `recomendada. (4) o diff EXATO em src/tcf. (5) compat+gate. (6) testes. (7) ADR. (8) passos. (9) riscos. ` +
  `(10) a pergunta de aprovacao exata. Vocabulario disciplinado, sem superlativos. Retorne SO o objeto estruturado.`,
  { label: 'synth:f2', phase: 'Sintese', schema: SYNTH })

return { bruto: all, synthesis }

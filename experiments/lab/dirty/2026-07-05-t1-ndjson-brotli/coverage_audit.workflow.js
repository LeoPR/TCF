export const meta = {
  name: 'dataset-shaper-coverage-audit',
  description: 'Auditoria: datasets agrupados consistentemente + shaper dimensiona em todas as direcoes (tipos/qualidades/volumes) para cenarios de transmissao; reabertura de tickets',
  phases: [
    { title: 'Audit', detail: '4 lentes: tickets, cobertura datasets, capacidade shaper, taxonomia-alvo' },
    { title: 'Synthesize', detail: 'matriz de gaps + veredito consistencia + plano de tickets' },
  ],
}

const CTX = `Projeto TCF (compressao textual tabular). Contexto para a auditoria:
- CLAUDE.md: filosofia (TCF supoe "dados felizes"; shaper/datasets sao TOOLING nao core; gadgets
  de qualidade so' ALERTAM; vies declarado; anti-incidente checklist). Datasets canonicos =
  metadata em datasets/canonical/, dados reais em Z:/tcf-data/. Shaper em scripts/shaper/.
- DESCOBERTA T1 (2026-07-05, experiments/lab/dirty/2026-07-05-t1-ndjson-brotli/result.md):
  TCF importa na transmissao DOWNLOAD (response = volume) como pre-processo antes do brotli.
  Vence NDJSON+brotli sempre; vence o steelman JSON-colunar SO' onde ha' ESTRUTURA (categorico
  largo OU cadencia/sequencia — ex: series temporais/forecast). Perde em high-card poucas-colunas.
- Owner (2026-07-05) quer saber, ANTES de novos benchmarks: (1) nossos datasets estao AGRUPADOS de
  forma CONSISTENTE pra representar os cenarios de transmissao reais? (2) o SHAPER consegue
  DIMENSIONAR em todas as direcoes: TIPOS de dados, QUALIDADES de dados, VOLUMES (de dados E de
  arquitetura)? O objetivo maior (3 eixos): testes controlados minusculo/grande (bordas) +
  datasets canonicos representativos + cenarios realistas (AWS/Azure/APIs, media/mediana de uso
  diario) => amostra que cobre bordas idealistas E a media/mediana de uso.`

const LENS_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['lens', 'summary', 'findings', 'gaps'],
  properties: {
    lens: { type: 'string' },
    summary: { type: 'string' },
    findings: { type: 'array', items: { type: 'string' } },
    gaps: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['gap', 'severity', 'evidence'],
        properties: {
          gap: { type: 'string' },
          severity: { type: 'string', enum: ['alta', 'media', 'baixa'] },
          evidence: { type: 'string' },
        },
      },
    },
    tickets: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['id', 'status_atual', 'acao'],
        properties: {
          id: { type: 'string' },
          status_atual: { type: 'string' },
          acao: { type: 'string', enum: ['reabrir', 'criar', 'atualizar', 'manter', 'ja-cobre'] },
          motivo: { type: 'string' },
        },
      },
    },
  },
}

const LENSES = [
  { key: 'tickets', prompt: `${CTX}

LENTE A — ARQUEOLOGIA DE TICKETS. Leia tickets/ (especialmente T-DATA-1/2/3/4,
T-DATA-3-EDGE-QUALITY-FIXTURES, T-SHAPER-SCIENTIFIC-GATING, T-SHAPER-CODE-HARDENING,
T-FIX-SHAPER-STRATIFY-TEST, T-EXP-MULTI-COL-SCALING, T-RECOVER-SCHEMA-MULTI-TABLE, tickets/README.md)
+ Grep por dataset/coverage/cobertura/cenario/volume/qualidade/transmissao em tickets/ e
experiments/lab/dirty/notas/. Objetivo: o que JA' levantamos sobre (cobertura de datasets /
cenarios de transmissao / dimensionamento do shaper / dados de qualidade-borda)? Para CADA ticket
relevante devolva id + status_atual + acao (reabrir/atualizar/criar/manter/ja-cobre) + motivo.
Foco: quais REABRIR para reanalise a luz do achado T1 (transmissao download + cadencia).` },

  { key: 'datasets', prompt: `${CTX}

LENTE B — COBERTURA DE DATASETS. Enumere os datasets: datasets/synthetic/*.csv (D-series),
datasets/canonical/*/ (metadata+README), e os hubs Z:/tcf-data/interim/*.db + raw
Z:/tcf-data/external/*/ (adult, tpch-sf001/sf01, online-retail, beijing-pm25, wine-quality,
ibge-municipios, br-identidades, football-results, receita-cnpj). Leia tambem a memoria de
cobertura C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/project_dataset_coverage_map.md
se existir. CLASSIFIQUE cada dataset por: (a) TIPO de dado dominante (categorico low-card /
numerico / free-text / timestamp-cadenciado / identificador-highcard / monetario / geografico),
(b) VOLUME disponivel (linhas, colunas), (c) FORMA de transmissao que representa (tabular-bulk /
serie-temporal-download / nested-response / small-payload). Responda: os datasets estao AGRUPADOS
de forma CONSISTENTE (ha' um esquema de agrupamento explicito ou e' ad-hoc)? Que cenarios de
transmissao ficam SEM cobertura (ex: serie-temporal cadenciada tipo forecast; nested JSON
response; payload minusculo <1KB; >1M linhas; alta-cardinalidade pura)? gaps com severidade.` },

  { key: 'shaper', prompt: `${CTX}

LENTE C — CAPACIDADE DO SHAPER. Leia scripts/shaper/ COMPLETO (pipeline.py, request.py, result.py,
strategies/{schema,join,compressibility,stratify,fk_preserving,volume,ordering}.py) + scripts/
shaper/_stratify_metrics.py. Objetivo: em que DIRECOES o shaper consegue dimensionar HOJE, e quais
sao STUBS/futuros? Mapeie explicitamente contra os 3 eixos do owner:
  - TIPOS de dados: o shaper SELECIONA/varia por tipo de coluna (categorico/numerico/timestamp/id)?
    ou so' filtra colunas por nome (schema)?
  - QUALIDADES de dados: o shaper injeta/varia defeito/missing/ruido? (provavelmente NAO — e' um
    SAMPLER de dado limpo; a qualidade e' concern do T-DATA-3 corruption). Confirme.
  - VOLUMES: de DADOS (linhas via volume_sampler) E de ARQUITETURA (nº tabelas, largura de schema,
    profundidade de join). O que existe (volume/schema/join) e o que falta?
  Verifique se 'compressibility' e 'stratify' estao IMPLEMENTADOS ou vazios. Devolva o veredito:
  o shaper dimensiona "todas as direcoes"? gaps concretos com evidencia (arquivo:funcao).` },

  { key: 'target', prompt: `${CTX}

LENTE D — TAXONOMIA-ALVO (o que precisariamos pra ser "estatisticamente relevante"). Leia
experiments/lab/dirty/notas/transmissao-api-onde-tcf-importa.md (ja' tem pesquisa AWS/Azure/APIs +
perfil upload/download) + o result.md do T1. Defina a TAXONOMIA-ALVO de cobertura que uniria os 3
eixos do owner: (1) bordas controladas (minusculo <1KB / grande >1M), (2) canonicos
representativos, (3) cenarios realistas (formas de API comuns: JSON paginado pequeno, bulk
NDJSON/CSV, serie-temporal/forecast download, event-stream; e a distribuicao media/mediana de
tamanho de payload diario). Objetivo: dar o ALVO contra o qual medir a cobertura atual — NAO
re-pesquisar a fundo (a nota ja' tem), so' SINTETIZAR a taxonomia-alvo (dimensoes x niveis) e
apontar o que falta pra amostra cobrir bordas E media/mediana. gaps = o que a taxonomia-alvo exige
que hoje nao temos.` },
]

phase('Audit')
const audits = await parallel(LENSES.map(l => () =>
  agent(l.prompt, { label: `audit:${l.key}`, phase: 'Audit', schema: LENS_SCHEMA })
))
const valid = audits.filter(Boolean)
const allGaps = valid.flatMap(a => (a.gaps || []).map(g => ({ ...g, lens: a.lens })))
const allTickets = valid.flatMap(a => (a.tickets || []).map(t => ({ ...t, lens: a.lens })))
const reopen = allTickets.filter(t => t.acao === 'reabrir')
log(`Audit: ${valid.length}/4 lentes; ${allGaps.length} gaps; ${reopen.length} tickets p/ reabrir`)

phase('Synthesize')
const synthesis = await agent(`${CTX}

Sintetize a auditoria num ASSESSMENT acionavel (markdown, PT, sobrio, SEM superlativos). Insumos:
- Lente A (tickets): ${JSON.stringify(valid.find(a => a.lens === 'tickets') || {})}
- Lente B (datasets): ${JSON.stringify(valid.find(a => a.lens === 'datasets') || {})}
- Lente C (shaper): ${JSON.stringify(valid.find(a => a.lens === 'shaper') || {})}
- Lente D (target): ${JSON.stringify(valid.find(a => a.lens === 'target') || {})}

Produza:
1. VEREDITO 1 — datasets agrupados consistentemente? (sim/parcial/nao + porque). Se ha' um esquema
   de agrupamento, qual; se e' ad-hoc, propor um esquema explicito (eixos: tipo x volume x forma-tx).
2. VEREDITO 2 — shaper dimensiona "todas as direcoes"? Tabela: eixo (tipo/qualidade/volume-dados/
   volume-arquitetura) x [cobre HOJE? / stub / ausente] + arquivo-evidencia.
3. MATRIZ DE GAPS priorizada (alta/media/baixa): o que falta pra amostra cobrir bordas + media/mediana.
4. PLANO DE TICKETS: quais REABRIR (id + o que reanalisar), quais CRIAR (titulo + escopo curto),
   quais ja' cobrem. Ligar cada um ao achado T1 quando aplicavel.
5. PROXIMO PASSO minimo (o foco-agora do owner): a menor acao que responde "datasets consistentes?
   shaper dimensiona?" sem abrir benchmark novo.
Seja concreto e cite arquivos/tickets. Nao invente cobertura que as lentes nao acharam.`,
  { label: 'synthesize', phase: 'Synthesize' })

return {
  n_lentes: valid.length,
  n_gaps: allGaps.length,
  tickets_reabrir: reopen.map(t => t.id),
  gaps_alta: allGaps.filter(g => g.severity === 'alta').map(g => g.gap),
  synthesis,
}

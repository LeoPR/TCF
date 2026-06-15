export const meta = {
  name: 'loss-taxonomy-review',
  description: 'Revisao exaustiva das vertentes de loss (lossy) para o TCF',
  phases: [
    { title: 'Facets', detail: 'exploradores de vertentes em paralelo' },
    { title: 'Critique', detail: 'critico de completude acha lacunas' },
  ],
}

const TCF_CONTEXT = `CONTEXTO TCF (Tabular Compact Format):
TCF e um compressor TEXTUAL de strings tabulares (saida ASCII inspecionavel, nao binario opaco).
Filosofia: textual + explicavel enquanto comprimido; ate hoje TODO weld e LOSSLESS-EXATO (decode(encode(x))==x).
Pipeline lossless atual (multi-coluna, #TCF.7): por coluna escolhe o MENOR de 4 candidatos:
  - tcf (OBAT afixo bidirecional LCP+LCS + HCC composicao/dedup)
  - raw (join cru por newline, quando menor)
  - dict (V2-B: low-card vira tabela de unicos + stream de indices 1-char)
  - split (split estrutural: valor com template uniforme de digitos/separadores vira colunas-campo;
           ex decimal 12.34 vira campo 12 + campo 34 + template ".", cada campo low-card cai no dict)
"Natures" (ADR-0015) sao pre-transforms OPT-IN por coluna (CPF/CNPJ/IP), reversiveis, spec out-of-band.
ESTADO LOSSY: V2-C (round simples) foi caracterizado: nicho pequeno (~1.5% weighted, so dados cientificos
de alta-precisao decimal tipo wine; dados de negocio o split ja resolve lossless). Decisao do owner pendente.

VISAO NOVA DO OWNER (motivo desta revisao): loss de dados e amplo e e PRO TCF FAZER SIM.
Vertente-chave que ele citou: LOSS INDIVIDUAL COM RECUPERACAO LOSSLESS NO AGREGADO. Exemplo: 7 linhas de
valores; arredondar alguns pra baixo e deixar RESIDUO em outros, de modo que a SOMATORIA total fique exata.
E loss por-linha mas recuperavel na soma. Usado em parcelamento de pagamentos (dividir um valor em N parcelas
quando da dizima). Tambem quer arredondamento simples, e todas as vertentes de loss, talvez em outros tipos
de dados. O entregavel e uma TAXONOMIA/REVISAO conceitual (decide-se depois como implementar).

Cada faceta deve ATERRISSAR no TCF: como integraria (pre-transform/nature/marcador no header/decoder),
qual o CONTRATO DE RECUPERACAO (exato / dentro-de-tolerancia / exato-no-agregado-qual), tipos de dado,
ganho potencial, riscos, e prior art. Escreva o conteudo em PORTUGUES, concreto e curto.`

const FACET_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['facet','summary','mechanism','tcf_integration','recovery_contract','data_types','gain_potential','examples','risks','prior_art','priority'],
  properties: {
    facet: { type: 'string', description: 'nome curto da vertente' },
    summary: { type: 'string', description: '1-2 frases do que e' },
    mechanism: { type: 'string', description: 'como funciona, passo a passo / a matematica' },
    tcf_integration: { type: 'string', description: 'como entra no TCF: pre-transform/nature/marcador/decoder, e o que precisa ser guardado' },
    recovery_contract: { type: 'string', description: 'exato | dentro-de-tolerancia (qual) | exato-no-agregado (qual agregado: soma/media/contagem/extremos/ordem)' },
    data_types: { type: 'array', items: { type: 'string' }, description: 'tipos de dado onde aplica' },
    gain_potential: { type: 'string', description: 'estimativa qualitativa ou pct se souber; onde brilha e onde nao' },
    examples: { type: 'array', items: { type: 'string' }, description: 'exemplos concretos com numeros' },
    risks: { type: 'string', description: 'riscos, armadilhas, quando NAO usar' },
    prior_art: { type: 'array', items: { type: 'string' }, description: 'algoritmos/sistemas/papers relacionados' },
    priority: { type: 'string', description: 'alta|media|baixa + justificativa curta pro owner' },
  },
}

const CRITIQUE_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  required: ['gaps','overall'],
  properties: {
    gaps: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        required: ['name','why','sketch'],
        properties: {
          name: { type: 'string' },
          why: { type: 'string' },
          sketch: { type: 'string' },
        },
      },
    },
    overall: { type: 'string', description: 'leitura geral: o espaco de loss esta coberto? o que e mais promissor pro TCF?' },
  },
}

const FACETS = [
  { key: 'residual-distributed', prompt: `VERTENTE: arredondamento com REDISTRIBUICAO DE RESIDUO, loss por-linha mas LOSSLESS NO AGREGADO (soma). Esta e a ideia-chave do owner (parcelamento). Detalhe a matematica (metodo do maior resto / Hamilton apportionment / erro acumulado tipo error-diffusion/dithering), como o TCF guardaria so os valores arredondados + um residuo/correcao compacto pra recuperar a soma exata, e como o decoder redistribui de forma DETERMINISTICA. Cubra: preservar a soma; generalizar pra preservar a media, ou um total por GRUPO (group-by). Discuta onde guardar a ancora (soma exata) e o custo em bytes.` },
  { key: 'aggregate-preserving-general', prompt: `VERTENTE: loss com recuperacao EXATA DE AGREGADOS em geral (nao so soma). Quais agregados sao preservaveis e como armazenar a correcao minima: soma, media, contagem, min/max (extremos), ordem/ranking, histograma/quantis. Para cada: o contrato e o custo de bytes da ancora que garante o agregado. Quando faz sentido pro TCF (relatorios, faturamento, telemetria agregada).` },
  { key: 'fixed-precision-round', prompt: `VERTENTE: arredondamento simples de precisao fixa (a base do V2-C ja caracterizado, ~1.5% nicho). Estenda: casas decimais por-coluna vs algarismos significativos; truncar vs round-half-even; precisao derivada do instrumento/dominio; como declarar no header e COMPOR com o split estrutural (arredondar so o campo-fracao -> campo low-card -> dict). Quando vence e quando e inutil.` },
  { key: 'quantization-binning', prompt: `VERTENTE: quantizacao / binning. Mapear valores continuos a uma grade/codebook (uniforme, ou k-means/Lloyd-Max nao-uniforme) e guardar codebook + indices (que caem no dict V2-B). Erro limitado pelo passo da grade. Quando vence o round simples (distribuicoes concentradas/multimodais). Custo do codebook vs ganho nos indices.` },
  { key: 'lossy-text', prompt: `VERTENTE: loss em DADOS TEXTUAIS. Normalizacao (case-fold, trim/collapse de espacos, remocao de acentos), near-dedup/fuzzy (colapsar strings quase-iguais a um canonico via distancia de edicao/clustering), abreviacao/stemming. Contrato (recuperavel? so o canonico?), tipos (nomes, descricoes, enderecos, free-text), risco de perder informacao semantica. Quando e aceitavel e como o TCF marcaria.` },
  { key: 'lossy-temporal', prompt: `VERTENTE: loss em DATAS/TIMESTAMPS. Truncar granularidade (segundo->minuto->hora->dia), quantizar epoch a um passo, snap a periodicidade. Ganho: o split estrutural ja separa campos; truncar zera os campos de baixa-ordem -> viram constantes -> somem. Contrato e tipos (logs, telemetria, cadastros). Erro = a granularidade descartada.` },
  { key: 'lossy-categorical-id', prompt: `VERTENTE: loss em CATEGORICOS/IDs. Merge de categorias raras numa categoria OUTRAS, hash-bucketing (reduz cardinalidade com colisao controlada), renumeracao/remap de IDs (perde o ID textual original, preserva a identidade relacional/joins). Contrato (preserva joins? distribuicao? top-K?), quando aceitavel, risco.` },
  { key: 'error-budget-contracts', prompt: `VERTENTE: CONTRATOS de tolerancia e verificacao. Como declarar e validar a perda: erro absoluto maximo, erro relativo, erro distribuicional (preserva media/variancia), agregado-exato. Como o TCF marcaria isso no header de forma INSPECIONAVEL (parte da filosofia), e como verificar no decode. Semantica de recuperavel-dentro-de-tolerancia vs exato-no-agregado. Determinismo/reprodutibilidade da perda.` },
  { key: 'prior-art-cross-domain', prompt: `VERTENTE: PRIOR ART e analogias cross-dominio que o TCF pode roubar. Time-series: downsampling, Gorilla/Facebook (XOR de floats), delta-of-delta. Matematica contabil/eleitoral: metodo do maior resto, DHondt, apportionment, distribuicao de centavos (banker rounding). Formatos float: bfloat16, posit, decimal128. ML: quantizacao (int8, k-means, product quantization). Lossy classico: dithering/error-diffusion, JPEG/audio (transform+quantize), sketches probabilisticos (bloom, count-min). Privacidade diferencial (loss intencional). Para cada: o que e transferivel pro TCF textual e qual vertente acima ele reforca.` },
]

phase('Facets')
const facets = (await parallel(FACETS.map(f => () =>
  agent(`${TCF_CONTEXT}\n\n${f.prompt}`, { label: `facet:${f.key}`, phase: 'Facets', schema: FACET_SCHEMA })
))).filter(Boolean)

phase('Critique')
const critique = await agent(
  `${TCF_CONTEXT}\n\nJa foram exploradas ${facets.length} vertentes de loss:\n${JSON.stringify(facets, null, 2)}\n\n` +
  `Voce e um CRITICO DE COMPLETUDE. O owner quer TODAS as vertentes de loss, talvez em outros tipos de dados. ` +
  `Liste vertentes/estrategias de loss AUSENTES ou sub-exploradas (modalidade nao coberta, tipo de dado esquecido, ` +
  `contrato de recuperacao nao modelado, combinacao de vertentes). Para cada gap: nome + por que importa pro TCF + esboco do mecanismo. ` +
  `No final (overall), diga qual vertente e a MAIS PROMISSORA pro TCF e por que.`,
  { label: 'completeness-critic', phase: 'Critique', schema: CRITIQUE_SCHEMA }
)

return { facets, critique }

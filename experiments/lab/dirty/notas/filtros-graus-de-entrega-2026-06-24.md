# Filtros / naturezas — "graus de entrega" e o spec-dict universal [plano/lente]

**Data**: 2026-06-24 · plano (lente conceitual + consolidação; NÃO implementa). Origem: owner
resgatou os filtros por causa do cross-dict (B1), com um reframe novo. Análise crítica + revisão do
corpus (workflow 6 agentes). Checkpoint: [`checkpoints/2026-06-24-pausa-0.8...`](checkpoints/2026-06-24-pausa-0.8-A-feito-B1-passou-revisitar-filtros.md).

## A lente nova do owner (contribuição conceitual)

O pré-filtro por tipo tem **graus de entrega** — um espectro entre **otimizar o formato** (encolher/
limpar o valor → OBAT/HCC mais rápidos/melhores) e **virar um "pré-dict"/bypass** (o núcleo vira
no-op). E uma distinção explícita: **onde o dicionário mora** —

| tier | onde o dict mora | mecanismo | custo no blob | veredito |
|---|---|---|---|---|
| 1 | in-blob, por coluna | V2-B `@dict` (ADR-0025) | tabela + stream por coluna | **welded** |
| 2 | in-blob, header compartilhado | B1 cross-dict / H-GDICT | tabela 1× + streams | **paga em same-domain-refs** (B1) |
| 3 | **out-of-blob, universal/spec** | "pré-dict notório" = **H-CODEBOOK-01** | **só o stream** (tabela é senso comum, viaja com TCF+versão) | já pesquisado → nicho |

O tier 3 é o "dict roubado" do owner: para tipos notórios (sim/não, UF, true/false), a tabela é
senso comum → não precisa estar no blob → viaja com o spec/versão.

## Os 4 graus de entrega e seus vereditos (reconciliados com a pesquisa)

1. **Dígito verificador recuperável** (CPF/CNPJ): strip + regen mod-11 no decode. Lossless, grátis,
   independe de repetição. **WELDED** (ADR-0015, SPEC_CPF/CNPJ; CPF −55/−64% sint, CNPJ +40.9% receita
   real). Não reabrir (é dispositivo).
2. **Template constante** (pontuação CPF, slots IP): guardado 1× no spec. **WELDED** (ADR-0015).
3. **Encolher pra acelerar** (owner citou IP→hex): eixo **VELOCIDADE**, distinto de bytes.
   **Correção da pesquisa**: o SPEC_IP atual NÃO faz hex e NÃO mira velocidade — faz padding
   digit-preserving pra **ativar HCC seq-RLE** (eixo bytes, cadência de subnet). O eixo velocidade
   (valor limpo → encode mais rápido) **não tem implementação NEM medição** em lugar nenhum →
   **lacuna real**, não um item existente. IP→hex-pra-velocidade nunca foi testado.
4. **Spec-dict / bypass notório** (sim/não, UF): o núcleo vira no-op; emite só índices num dict
   universal. **Real mas estreito** — ver abaixo.

## O que a análise crítica acertou, e o que a pesquisa corrigiu

**Confirmado** (a pesquisa já tinha chegado lá, independente):
- Os 3 tiers mapeiam 1:1 (V2-B / B1 / H-CODEBOOK). O "novo" tier 3 já foi pesquisado em
  [`cep-outer-dict-codebook-pesquisa.md`](cep-outer-dict-codebook-pesquisa.md) (2026-06-16).
- **O ganho do spec-dict sobre o V2-B é SÓ a tabela** (o stream de índices é idêntico) → **nicho de
  payload pequeno**. Dois achados independentes batem: cep-outer-dict (ganho só sobre a tabela inline,
  relevante em payload pequeno) + B1 Etapa 3 (vocab trivial sim/não: tabela de 2-3 entradas já é
  trivial inline; ganho ≤4.6% sub-gate).
- "Reabre o custo do F2 (#TCF.8 + codebook versionado = passivo de compat)" = literalmente o "por que
  parado" de ADR-0027.
- **Enumerated in-blob já REFUTADO** (−2.28% se forçado; M10+V2-B cobrem low-card). Tipos notórios
  (sim/não, UF) são casos dessa natureza in-blob → veredito in-blob já existe e é negativo.

**Correções / o que faltou na análise**:
- (a) **Forward-compat do out-of-blob é MAIS DURO que o F2**: no F2, "id desconhecido → valor cru"
  funciona porque a nature pré-tx é reversível a partir do valor. No bypass out-of-blob o **valor não
  viaja** (só o índice) → codebook-id desconhecido = **decode IRRECUPERÁVEL**, dependência DURA da
  versão exata. Passivo maior que o reframe assume; encosta na fronteira "não competir com shared-dict
  do brotli/zstd" (filosofia CLAUDE.md).
- (b) **O caso exato NÃO foi medido**: universal+TRIVIAL (sim/não/UF) em payload MINÚSCULO. cep
  raciocinou tabelas GRANDES (IBGE/CNAE/ISO, 1300-5570 entradas); B1 mediu in-blob. O nicho do owner
  (universal+minúsculo) permanece **asserido, não medido**.
- (c) **UF é cross-TABELA** (B1 Etapa 1: pessoas.uf=empresas.uf=receita.uf), não intra-blob; e o
  dict de UF out-of-blob economiza poucos chars vs 27 strings curtas inline (sub-gate).

## spec-dict precisa de #TCF.8?

**Depende da semântica** (ambas verificadas no código):
- **Out-of-band** (caller passa `nature_per_col={'col': spec}`, dict viaja por fora via versão): **NÃO
  precisa de #TCF.8**. É pra onde o reframe ("viaja com TCF+versão, não no blob") aponta. **MAS** exige
  um **EnumSpec/DictSpec novo no core** (não existe — `TemplatedChecked/Padded` modelam ID-templated,
  não mapa-de-valores; `grep enum|categorical|dict` em src/tcf/natures = 0). Criar isso **toca
  src/tcf → aprovação + weld + GATE**. O gadget DSL/registry sozinho não materializa (só instancia
  specs que já moram no core). E não é self-describing (caller reanexa por nome+versão — como o
  registry já faz hoje pra cpf/cnpj/ip).
- **Self-describing** (id do tipo viaja no blob): **SIM, precisa #TCF.8** = exatamente o F2/ADR-0027,
  parado em (A). A metade barata (só marcar a nature) já falhou o custo×ganho.

## Timing recomendado

**Não agora.** Sequência coerente com v08-plano + ADR-0027(A) + a economia da infra compartilhada
"dict referenciado do header / bump #TCF.8":

1. **0.8** = lazy endurecido+shipado (A, feito) + B1 cross-dict (feito, paga) → **release 0.8.0**.
   NÃO mexer em spec-dict/F2 aqui.
2. **0.9** = **B2/B3 cross-dict** (#TCF.8 opt-in, dict de grupo no header). **Este canal paga o
   passivo do magic #TCF.8 PRIMEIRO**, porque tem ganho real medido (−19.3% same-domain) e o v08-plano
   já condiciona "#TCF.8 entra SE o cross-dict weldar" — não ao nature-mark. F2/spec-dict ficam
   **baratos por carona** depois (mesma infra de header). Pagar o magic por F2/spec-dict primeiro
   inverteria o custo-benefício (a parte de menor ganho pagaria o passivo).
3. **Spec-dict notório (EnumSpec)**: só DEPOIS de #TCF.8 existir via B, e só se o owner quiser medir o
   nicho. **Pré-requisito antes de QUALQUER código**: sub-exp read-only que MEÇA o caso exato
   (sim/não/UF universal em payload minúsculo / single-col / valor avulso) vs V2-B inline. Hoje o
   ganho é asserido, não medido (gate anti-incidente 2026-05-21). Provável sub-gate → registrar-adiado.

## Decisões abertas (owner)

1. Semântica do spec-dict: **out-of-band** (sem #TCF.8, mas EnumSpec novo no core, gated) ou
   **self-describing** (#TCF.8/F2, parado)? O reframe aponta pra out-of-band.
2. O **eixo velocidade** (valor limpo → encode mais rápido) é alvo real? Se sim, é trabalho novo
   (nenhuma medição), com critério próprio (throughput, não bytes).
3. Autorizar (ou não) o **sub-exp read-only** que mede o nicho payload-minúsculo (sim/não/UF
   out-of-blob vs V2-B) — antes de qualquer toque no core.
4. Aceitar o **passivo forward-compat duro** do out-of-blob (codebook versionado obrigatório nos dois
   lados; id desconhecido = irrecuperável)?

## Conexões
- Welded: [ADR-0015](../../../../docs/adr/0015-natures-templated-checked-weld.md) (graus 1-2).
- Parked: [ADR-0027 / F2](../../../../docs/adr/0027-nature-mark-header-self-describing.md) +
  [f2-nature-mark-header-design.md](f2-nature-mark-header-design.md).
- Família dict: [dict-referencia-hipoteses.md](dict-referencia-hipoteses.md) (H-REF) +
  [cep-outer-dict-codebook-pesquisa.md](cep-outer-dict-codebook-pesquisa.md) (H-CODEBOOK = tier 3) +
  [B1 cross-dict](../2026-06-21-gdict-caracterizacao/result.md) (tier 2).
- Plano nature: [META-TYPE-ENCODERS](../../../../tickets/META-TYPE-ENCODERS.md) (gate T-DATA-1) +
  [data-natures-taxonomy](../../../../docs/theory/data-natures-taxonomy.md).
- Diretriz: byte-level focus (memory project_byte_level_compression_focus) — o único regime onde o
  tier 3 poderia pagar (payload minúsculo).

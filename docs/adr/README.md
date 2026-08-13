# Architecture Decision Records (ADR)

Registros numerados das decisoes arquiteturais do TCF. Inspirado em
[Michael Nygard's ADR](https://adr.github.io/) + [MADR](https://adr.github.io/madr/).

## Convencao

- **Numeracao**: `NNNN-imperative-phrase.md` (4 digitos, ASCII, kebab-case)
- **Imutabilidade**: ADRs aceitos NUNCA sao editados. Pra mudar, criar
  novo ADR com `Status: Supersedes NNNN` e back-link.
- **Status**: `proposed`, `accepted`, `superseded by NNNN`, `deprecated`
- **Template MADR**:
  ```
  # NNNN — Titulo imperative

  **Status**: accepted | superseded by NNNN | deprecated
  **Date**: YYYY-MM-DD
  **Deciders**: who

  ## Context and Problem Statement
  ## Considered Options
  ## Decision Outcome
  ## Pros and Cons of the Options
  ## More Information / Links
  ```

## Index

| # | Titulo | Status |
|---|---|---|
| [0001](0001-tcf-format-shebang.md) | TCF format shebang (`#TCF.<minor>`) | accepted |
| [0002](0002-vertice-triplice-restricao.md) | Vertice triplice (compressao + memoria + latencia) como restricao dura | accepted |
| [0003](0003-tripartite-pre-obat-hcc.md) | Tripartite Pre/OBAT/HCC com pesos relativo vs absoluto | accepted |
| [0004](0004-multi-column-header-compacto.md) | Multi-column header compacto (`#TCF.6 M` + `# size=name,...`) | accepted |
| [0005](0005-discoverability-claude-md-root.md) | CLAUDE.md no root + MAP.md + hooks pra discoverability | accepted |
| [0006](0006-empty-string-decode-fix.md) | Empty string body line deve ser decodada como string vazia (bug fix src/tcf) | accepted |
| [0007](0007-comma-in-literals-bug.md) | `,` em literais corrompe decode (separator `*` em ref→lit ambiguo) | **accepted** (welded 2026-05-19) |
| [0008](0008-detect-cadence-numeric-rule.md) | detect_cadence: regra numeric+high-cardinality (H-DA-09b refino) | **accepted** (welded EXP-010 2026-05-19) |
| [0009](0009-obat-trigram-index-optimization.md) | OBAT: hash trigrama index reduz O(N²) a O(N) amortizado (alpha 1.75→1.42, 2.70x em 20k) | **accepted** (welded src/tcf 2026-05-19) |
| [0010](0010-auto-detect-min-len.md) | Auto-detect min_len por coluna (H-DA-11) | **accepted** (canonical welded) |
| [0011](0011-pacote1-weld-canonical.md) | Pacote 1 (Delta-aware) welded canonical em src/tcf (M9 → M10) | **accepted** (welded) |
| [0012](0012-diataxis-naming-local.md) | Diataxis naming local (docs/algorithms, docs/theory) | accepted |
| [0013](0013-multi-column-canonical-api.md) | Multi-column canonical API welded em src/tcf | **accepted** (welded; superseded by 0014) |
| [0014](0014-unified-api-side-outputs.md) | API unificada `encode(list\|dict)` + SideOutputs recipiente | **accepted** (welded) |
| [0015](0015-natures-templated-checked-weld.md) | TemplatedCheckedSpec welded canonical em src/tcf/natures | **accepted** (welded) |
| [0016](0016-hcc-multi-delta-seq-rle.md) | HCC seq-RLE multi-delta (Bug #2 sub-exp 14 fix) | **accepted** (welded) |
| [0017](0017-format-spec-v1-frozen.md) | Format spec v1.0 frozen + versioning policy | accepted (parte "freeze" superseded por 0024 — projeto e' pré-1.0) |
| [0018](0018-v2-format-roadmap.md) | Roadmap de formato v2.0 (fallback identity, dicionario, lossy) | **proposed** (V2-A welded por 0022) |
| [0019](0019-hcc-detect-compositions-topk-prune.md) | Weld do prune top-K em HCC _detect_compositions (H-PERF-06-v2 #15) | accepted |
| [0020](0020-cython-optional-accelerator.md) | Acelerador Cython opcional de _detect_compositions (H-PERF-06-v2 Fase B) | accepted |
| [0021](0021-onedrive-git-corruption-recovery.md) | Incidente OneDrive × `.git`: recuperacao (causa = hipotese) | accepted |
| [0022](0022-v2a-fallback-identity-weld.md) | V2-A fallback identity welded (abre v2.0, `#TCF.7`, opt-in `fallback=True`) | **accepted** |
| [0023](0023-v2-minimal-header-weld.md) | Header v2 minimo welded (`#TCF.7`, opt-in `min_header`: sem espaco + ultima coluna sem size) | **accepted** |
| [0024](0024-pre-1.0-versioning-git-as-compat.md) | Versionamento pré-1.0: minors de dev, git como compatibilidade (supersede freeze de 0017) | **accepted** (refinado por 0028: eixo RELEASE separado do MINOR) |
| [0025](0025-v2b-dictionary-categorical-weld.md) | V2-B dicionario categorico welded (`#TCF.7`, marcador `@`, 13.9% weighted) | **accepted** |
| [0026](0026-structural-split-weld.md) | Split estrutural welded (`#TCF.7`, marcador `%`, 19.39% weighted) | **accepted** |
| [0027](0027-nature-mark-header-self-describing.md) | H-NAT-MARK-01: nature-id viaja no header (self-describing, `#TCF.8`; multi + single-col) | **accepted** (MVP welded 2026-06-24) |
| [0028](0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md) | Versionamento pré-1.0: acoplamento minor↔formato + eixo RELEASE (0.N.x); evita inflacao 0.8.0 com formato #TCF.7 (refina 0024) | **proposed** |
| [0029](0029-version-format-identification-semi-implicit.md) | Identificacao versao/formato: semi-implicito (orfao default + header no desvio + chamada explicita) + major-externo + congelamento 1.0 single-col; discriminador `#TCF.8` 1-char (M/espaco/newline); `#TCF.8\n` = magic-number p/ `file`/libmagic | **accepted** (2026-06-24) |
| [0030](0030-freeze-single-col-body-at-1.0.md) | Congelar o body single-col no 1.0 (contrato imutavel do orfao default; linchpin do 0029). Otimizacoes futuras viram desvios opt-in marcados, nao mutacao da base. Pre-1.0 ainda refinavel (0024). | **accepted** (politica; efeito no 1.0) |
| [0031](0031-hierarchical-discriminator-H.md) | Discriminador `H` = multi-col hierarquico (especializacao de `M`, sem-espaco); estende 0029 com o 5o valor. Reserva o char + dispatch O(1); codec hierarquico (EXP-015) segue research-track, weld gated. | **accepted** (2026-07-09; char reservado, codec nao-weldado) |
| [0032](0032-tcf8-default-format.md) | #TCF.8 vira o formato DEFAULT (multi-col); supersede o "opt-in estrito" do 0027. Corta legado .6/.7 de src/tcf; hex e escaping na familia .8; hierarquia = slot+fail-loud (codec pro lab); pacote 0.8.0 (lazy absorvido). Single-col orfao intacto (0029/0030). | **accepted** (2026-07-09) |
| [0033](0033-hierarchical-codec-weld.md) | Weld do codec hierarquico `#TCF.8H` no core: modulo novo `hierarchical.py` (L2/L3) cliente do compressor de coluna (L1 intocado); shredding em blocos + `#count` explicito. Fecha o gate do 0031. Classe coberta (schema uniforme); ragged/tipos/null/N-raizes/N:N = fail-loud (incrementos). Flat byte-identico; gate de CAPACIDADE. | **welded** (2026-07-14) |

| [0034](0034-header-default-100-porcento-single-col.md) | Header `#TCF.8` e' DEFAULT em 100% dos casos no single-col (mesmo vazio); orfao vira ESCAPE explicito (`stamp=False`) p/ transmissao/container tipo parquet. **Supersede o DEFAULT do 0029** (premissa mal registrada, revisada pelo owner). 1 header por ARTEFATO (o .8H passa stamp=False nas colunas). Re-pina D1-D9 1523->1586 e real-world 89616->89637 (+7 B/dataset; core inalterado). | **accepted** (2026-07-24) |
| [0035](0035-delimitador-de-polaridade-single-col.md) | Delimitador de POLARIDADE no single-col (`#TCF.8<tag><sufixo>`): marca a TROCA literal<->referencia em vez de cada literal — 1 byte por TRANSICAO, nao por ocorrencia; carrega tambem a FRONTEIRA entre corridas. Camada de BORDA (o seq-RLE so' ve corpo canonico). Char ELEITO por coluna do complemento do alfabeto; FAIXA = so' pontuacao (exclusao por CLASSE: digito funde com a corrida, letra colide com o discriminador). FLOOR nunca-pior incluindo o sufixo. Re-pina D1-D9 1586->1545 e real-world 89637->89430; D17a intacto (.8M fora do escopo). | **accepted** (2026-07-26) |
| [0036](0036-bn-de-dominio-cardinalidade-baixa.md) | bN de DOMINIO no single-col flat (`#TCF.8B<w><n>` streaming / `#TCF.8C` lote): com k distintos bastam ceil(log2 k) BITS por linha; o dominio viaja 1x, comprimido pelo proprio core. Densidade por CARDINALIDADE, nao por tipo declarado (`['0','1']*100`: 609 -> 54 B). `null` = slot 0. Marcador `=` com escape `\=` (o core nunca emite `\`+char fora de `* 0-9 \ ^ ~`). So' `B` e' EMITIDO -- o `C` e' 1 B menor mas nao streama. Candidato do min(), nunca-pior: NENHUM baseline moveu. | **accepted** (2026-07-27) |
| [0037](0037-denso-b2-ternario-dominio-implicito.md) | Denso b2 TERNARIO no tipado bool (`#TCF.8b2<n>`): 2 bits/simbolo, dominio IMPLICITO congelado `null=0, false=1, true=2` (3 = fail-loud) — tipos puros do JSON nao precisam declarar dominio. 546 -> 79 B (n=200), 15 B a menos que o bN tipado (que declarava o dominio); vence inclusive n=3. Mesmo `bitpack` do b1, mais um candidato do min(). NENHUM baseline moveu. | **accepted** (2026-07-31) |
| [0038](0038-indice-interno-default-core-tipado-bool.md) | Indice interno DEFAULT no CORE tipado bool: o render da tag `b` emite slots congelados (a MESMA tabela do b2) em vez de nomes — `*200\|true` (18 B) -> `*200\|\2` (16 B); run-heavy 30 -> 25; reais ordenados 27 -> 22; nunca pior. Nomes seguem DECODAVEIS-nao-emitidos (contrato do modo `C`, ADR-0036). Familia bool fechada ponta a ponta: b1 · b2 · core-com-slots. NENHUM baseline moveu. | **accepted** (2026-08-01) |
| [0041](0041-spec-id-tres-planos.md) | Spec em TRES PLANOS: `name` legivel (codigo, nunca viaja) x `wire_id` curto `^[a-z][a-z0-9]{0,7}$` (dado) x o CARIMBO (contrato: se o id acompanha o dado). Motivo medido: ` :data-iso` = **31% do artefato** (10 B de 32) e o COMPRIMENTO DO ID FLIPA O FLOOR — em N>=11 a nature PERDE com `data-iso` e VENCE com id de 2 chars (o nome longo suprime a propria nature). Sem validacao, id hostil corrompe com erro ENGANOSO (`,` vira 'referencia a fragmento inexistente'); 3 gramaticas parseiam o id diferente. Minusculas-only reserva MAIUSCULA/pontuacao pros sufixos de rota. A resolucao passa a comparar `wire_id` (senao o plano 2 quebra o plano 3). Modo SEM-CARIMBO (aplica e nao manda junto: 32 -> 15 B) = parametro NOVO, nao o `stamp=False`. Mapa de ids = **escolha revisavel ate' o 1.0**; a ESTRUTURA e' o que congela. | **proposto** (2026-08-12) |
| [0040](0040-seq-rle-periodico.md) | seq-RLE PERIODICO (`*N~d1,...,dp\|template`): o delta CICLA entre linhas — dias uteis (`1,3,1,1,1`), ids por turno (`10,10,10,50`), quinzenal. O `*N+d\|` de hoje so' come delta uniforme e o multi-delta do ADR-0016 e' per-RUN dentro da linha, nao per-linha. **O ciclo paga UMA vez**: uteis n=600 1590 -> 40 B (39,8x), n=6000 -> 41 B (**O(1) em n**), ids nao-data 1959 -> 32 B (61x). DUAS guardas obrigatorias (medidas): rejeitar padrao uniforme (`[1,1]` = `*N+d\|` disfarcado) e FLOOR contra o corpo JA COMPACTADO. Colocacao decidida por medicao: dentro do `expand_seq_marker` (preserva o teto de memoria — 0,0000 s vs 2,473 s num passe separado). D1-D9 1545, real-world 89430, suite 1199: **byte-identicos**. Caractere `~` reversivel pre-1.0. DUAS cacadas adversariais: 7 defeitos fechados, 2 deles criados pelos proprios consertos (o gate de canonicidade virou amplificador 16.881x; o FLOOR por fragmento faltava). Suite 1238 (39 testes novos). | **accepted** (2026-08-09) |
| [0039](0039-lazytype-bool-cabeca-congelada-extras.md) | Lazytype bool (`#TCF.8bB<w><n>`): a uniao bool+str (true/false/null COM excecoes string) era fail-loud; agora cabeca CONGELADA implicita `null=0/false=1/true=2` (nunca se declara) + extras str declarados do slot 3, dominio comprimido pelo core (disciplina ADR-0036). A armadilha decisiva: dominio completo funde `"true"` str com `True` — perda silenciosa. CONTRATO UNIAO novo: 1a rota que emite lista mista (owner: lazy = default). Adult `sex`+" ?" (n=100): 50 B vs 64 completo / 61 flat-str; deteccao 8/8, 0 FP/FN. NENHUM baseline moveu (so' captura ex-fail-loud); pins: nenhum. | **accepted** (2026-08-01) |

## Quando criar ADR

Crie ADR quando:
- Decisao **arquitetural** (afeta multiplos componentes ou versoes futuras)
- Vai mudar comportamento publico (API, formato, convencao)
- Reverter custaria significativo
- Multiplas opcoes foram consideradas e descartadas

NAO crie ADR pra:
- Bug fixes (use commit message + diario)
- Refatoracoes locais
- Tarefas de implementacao (use sub-experimento)

## Como referenciar ADR

- Em outros docs: `[ADR-0003](docs/adr/0003-tripartite-pre-obat-hcc.md)`
- Em codigo (comentario): `# Ver ADR-0003 — tripartite Pre/OBAT/HCC`
- Em ADRs (cross-link): `Supersedes ADR-0001`, `See also ADR-0002`

## Migracao de decisoes antigas

Decisoes anteriores ao ADR system estao em:
- `experiments/lab/dirty/notas/diario/YYYY-MM-DD.md` (cronologico)
- Memorias user (`~/.claude/.../memory/feedback_*.md`, `project_*.md`)

Migrar pra ADR quando: a decisao reaparecer em conversa, OU quando
um novo ADR superseder algo antigo (entao escreve-se ambos pra rastrear).

---
title: T-SPEC-DEEPDIVE-08 — investigação de fundo dos specs (o que comprime, CNPJ além do básico, compilador/un-weld); plano 0.8 + pré-1.0
status: open
priority: P1
created: 2026-07-12
updated: 2026-07-12
blocked-by: []
related:
  - tickets/T-SPEC-STATUS-08.md
  - tickets/T-QA-8-material-comprobatorio.md
  - tickets/T-REL-08-CLOSEOUT.md
  - tickets/T-OPT-INFERENCE.md
  - src/tcf/natures/templated_checked.py
  - scripts/natures_compiler/compiler.py
---

# T-SPEC-DEEPDIVE-08 — o que os specs comprimem, de verdade

**[dispositivo→registro]** Redirecionamento do owner (2026-07-12): antes do F6/release, investigar a
fundo "todas as características que podem comprimir; estudamos bem o CPF, mas o CNPJ ficou no básico;
tem o compilador de specs pra tirar do welded. Planejamento pra fechar 0.8 E pré-1.0." Fonte:
workflow de 4 agentes (2026-07-12, read-only, file:line + medição python real).

## §0 — O INSIGHT que unifica tudo (o CNPJ não é "básico", é arquitetura errada)

A nature é uma **pré-transformação FORÇADA de camada-0** (`encoder.py:277-303`): `encode_value` roda
em TODOS os valores e SUBSTITUI a coluna ANTES da competição de modos multi-col. O corpo base-94
empacota o valor num inteiro denso — o que **DESTRÓI a estrutura inter-linha** (matriz/filial
low-card, base ordenada com deltas concentrados) que o `split`/`dict`/`delta` do próprio TCF já
explorava. Resultado medido (receita real, coluna cnpj isolada):

- **SEM nature**: 32678B (modo `split` vence).
- **COM nature**: 40017B (cai pra `raw`) → **+7339B** = exatamente a regressão do F4.
- **Em amostra EMBARALHADA**: a nature GANHA (40014B vs 41314B).

Ou seja: **a nature ajuda quando a coluna NÃO tem estrutura explorável (sintético/random/embaralhado)
e PIORA quando tem (real ordenado por PK)**. O "CNPJ ficou no básico" é isto: trata 14 dígitos como
UM inteiro, jogando fora a estrutura. E o mesmo mecanismo ameaça o CPF em clustering administrativo
real (nunca testado — só sintético).

## §1 — CPF: o MODELO de spec bem-estudado (10 eixos = gabarito)

O CPF cobriu 10 eixos que servem de checklist pra QUALQUER spec (lab `2026-05-24-cpf-templated-checked`,
14 sub-exps). A máquina explora 3 características: (1) máscara fixa descartável, (2) DV derivável
mod-11, (3) corpo 9-díg → base-94 5 chars. Medido: −55 a −64% em 18 sintéticos. Os eixos completos:
máscara · DV-derivável · corpo→base-N · contra-provas A/B/C · fallback per-value · heurística de
aplicação (quando NÃO aplicar) · stats ISO-25012 · progressão de datasets · generalização de
categoria · self-describing `:id`. **O que o CPF DEIXOU NA MESA**: correlação inter-linha (base-94
a destrói), sub-campo (o 9º díg é região fiscal — fundido no inteiro), e **real-world nunca testado
standalone** (confirmada-empirica do CPF é só sintético).

## §2 — CNPJ além do básico (estrutura medida na receita real)

Coluna cnpj real (receita, 5000 PK-sorted): **filial** 97,6% = `0001` (0,247 bits → 1242B sozinha);
**base-8** 99,9% única MAS 94,9% ordenada, deltas concentrados (+11 = 37%, +9..+12 = ~86%) → como
delta-strings cai de 36136B pra 14914B; **DV** 100% derivável = 0 bits. Direções (com ganho medido):

| direção | o que faz | ganho | quando |
|---|---|---|---|
| **nature COMPETE** (não pré-empta) | encode nos 2 modos, fica o menor | recupera +7339B; safe-by-construction | **decisão do owner: 0.8 ou 0.8.1** |
| derive-only | mantém máscara+split, só dropa o DV | preserva 32678B do split, corta DV | pré-1.0 |
| field-split | base8 \| filial \| DV → dict/delta/0 | melhor caso ~16,2KB vs 32678 (~50%) | .9/pré-1.0 |

## §3 — Mapa de características compressíveis (valida a Opção A)

**Veredito: no `.8` NÃO há característica NOVA que valha ganho de BYTE** — todo o maquinário
byte-relevante já está welded (OBAT afixos, HCC dedup/RLE, dict V2-B, split-em-campos, cadência,
natures). A Opção A do owner está correta. Duas famílias ficam pra depois:
- **(a) binárias/terminais** (bN bit-pack, bool-bitmap): ganho colapsa sob brotli (D3: 8.8%→1.7%);
  valor real = ACELERAÇÃO (F1 2.4-2.9x), não byte textual → V2-L / decisão de PRODUTO, não .8.
- **(b) cross-coluna/cross-linha** (GDICT same-domain −19% textual, DERIVED-DROP, H-INTRA
  intra-valor): exigem estrutura de formato nova → .9/pré-1.0.
- O achado F4 é o caso-padrão do conflito **normalização intra-valor VS estrutura inter-linha** — o
  gap arquitetural mais acionável pra pré-1.0 (é o §0).

## §4 — Compilador / "tirar do welded"

O `natures_compiler` (`scripts/natures_compiler/`, gadget) **JÁ é autoria data-driven**: lê `.dsl`
flat, auto-gera regex+formatter do template, instancia os TemplatedSpec e PROVA lossless por
round-trip de 64 amostras no compile-time; regenera CPF/CNPJ/IP **byte-idênticos** ao hardcoded
(14 testes verdes). O welded (`SPEC_CPF/CNPJ/IP` + `SPEC_REGISTRY` dict literal) é a FONTE DA VERDADE;
o compilador é a superfície de extensão. Fases de "tirar do welded":

- **0.8**: documentar o seam no F6 (o compilador já é a autoria data-driven; welded = fonte da
  verdade). Zero core.
- **pré-1.0**: `SPEC_REGISTRY` CARREGÁVEL — `build_registry(catalog)` que semeia com os 3 core e
  ADICIONA de catálogo; reconciliar meu **BUG-13b** (id desconhecido = erro) com namespace
  **`core:` (fail-loud inalterado) vs `user:` (resolvido do catálogo do caller)**. Toca core →
  aprovação + gate + cruza T-API-BOUNDARY-CONTRACTS.
- **.9**: `check_fn` como registry NOMEADO (CEP/PIS/renavam/título/CNH cabem por construtor,
  no-eval); pré-reqs (anonimizador §2.3 + gerador estendido) faltam.
- **2.0/pesquisa**: W4 TCFL expressivo (DSL compõe DV+segment sobre primitivas fechadas).

## §4-bis — REFINAMENTO do owner (2026-07-12): nature é matematizável → falta o DELTA

O owner apontou (e MEDIMOS, `scripts/spec_demo.py` + medição inline): a nature não destrói a
estrutura pela matemática — **nunca fizemos um delta da nature**. O corpo é um `int`; numa coluna
ordenada os ints são ordenados e deveriam deltar como o pipeline faz. O que quebra hoje: a nature
emite base-94 ABSOLUTO por linha, e `base94(N)` vs `base94(N+11)` não têm relação de afixo → OBAT/HCC
não deltam → cai pra raw. Medido (CNPJ real ordenado, 5000):

| abordagem | bytes | modo |
|---|---|---|
| A — sem nature (pipeline puro) | 32665 | split (baseline) |
| B — nature absoluta (HOJE) | 39999 | raw (+7334, regressão) |
| **C — nature DELTA (corpo-int deltado)** | **17032** | dict — a ideia do owner, **bate o split** |
| **D — field-split (base8Δ \| filial-dict \| DV=0)** | **16137** | decompõe o subcódigo |

E a natureza do CNPJ pelas regras da Receita (confirmar contra IN RFB oficial; empiricamente
confirmado): **8 díg base = inscrição SEQUENCIAL (raiz) → ordenada/deltável; 4 díg filial = contador
de estabelecimento, `0001`=matriz 97,6% → ENUM, não 4 díg livres; 2 díg DV = mod-11 derivável (0
bits)**. Ou seja o CNPJ é "um código só com pouquíssimas coisas classificáveis" (owner) — a
informação efetiva é MUITO menor que 14 dígitos. Isso generaliza: a mesma coisa vale pro CPF (o 9º
díg é região fiscal; corpo pode ter cadência em lotes) e é o gabarito de "subcódigo posicional"
pra qualquer spec numérico.

**Consequência**: "o fix" tem 2 níveis agora —
- **FLOOR (safe, barato)**: nature COMPETE no min() → nunca pior que baseline (recupera pra 32665).
- **CEILING (otimização real)**: nature DELTA-AWARE / FIELD-DECOMPOSED → ~16-17KB (~2× o baseline),
  passa folgado o gate ≥15%. É spec-machinery nova (modo delta do corpo + decomposição de subcódigo),
  merece estudo próprio (multi-coluna real, CPF, sobrevive a brotli?, gate real-world).

## §4-ter — As 3 FORMAS / 6 CAMADAS do spec (arquitetura do owner, 2026-07-12) — MEDIDAS

Owner: o spec pode ser tratado em 3 formas — **A) entrada total** (transforma antes, núcleo nem
trabalha = nature HOJE); **B) paralela** (núcleo trabalha, depois troca a base-94 ao menos nas
REFERÊNCIAS); **C) misto** (limpa na entrada pra o núcleo achar padrões + troca na saída). Em ~6
camadas: limpeza (máscara) · derivação (DV) · pré-forma (ordem/delta) · núcleo · troca nas
referências · saída/header. Decode: "expande o base-94 e depois leva as chaves" (→ delta → zfill →
DV → máscara), lossless por construção.

**Lab `2026-07-12-1917-spec-camadas-v1/`** (escada S1-S5 pelo pipeline REAL, 4 regimes,
**RT end-to-end PROVADO 20/20** — decode→reconstrói→==original; artifacts/04). Números com
alfabeto MARKER-SAFE base-62 (a nature real usa BASE94 com `^`, que dispara o BUG-15 — ver abaixo):

| degrau | CNPJ ord | CNPJ shuf | CPF rand | CPF clust |
|---|---:|---:|---:|---:|
| S1 masked (baseline) | 32665 | 41332 | 7499 | 1043 |
| S2 clean (só limpeza+DV) | 53709 | 64999 | 4999 | 68 |
| S3 clean+delta | 17032 | 51891 | 5146 | 19 |
| S4 base94 absoluto (**hoje**) | 39988 | 39988 | 3032 | 2830 |
| **S5 delta→base94 (misto)** | **14640** | **32954** | 3237 | **14** |

> **NOTA DE HONESTIDADE (§RT)**: os números da 1ª versão deste lab (17032/14270 etc. em base-80,
> commit `9f152d1`) foram reportados SEM RT validado — o RT counter-proof desta v1 revelou que os
> blobs de S3/S5 em base-80 NÃO decodam (BUG-15). Só dizer "lossless por construção" não era
> evidência; a contra-prova é que mede. A conclusão (S5 sempre-boa) sobrevive em base-62 com RT verde.

> **BUG-15 (achado por ESTE lab) — FIXADO 2026-07-12**: literal começando com `^` quebrava o RT em
> tcf/dict. Fix cirúrgico byte-neutro (escape `\^`-líder no emit; 616 passed). **O CEILING está
> DESTRAVADO** — a nature-delta/field-split pode usar o alfabeto base-94 cheio (com `^`). Ver
> T-QA-8 §3 BUG-15.

**Achados**:
1. **A forma C (S5) é a única SEMPRE-boa**: melhor em 3 de 4 regimes (−56% ord, −22% shuf, −98.7%
   clust) e quase-empatada no 4º (random: S4 2971 vs S5 3207 — absoluto fixo vence delta variável
   em dado sem ordem). A forma A (hoje) é a PIOR em 2 de 4.
2. **CPF clustered → 14 BYTES** (de 1043): delta constante `+3` vira RLE `*499|` — o lote inteiro
   é "1º valor + (+3 × 499)". Informação-teórica quase perfeita.
3. **SURPRESA — limpeza ISOLADA PIORA o CNPJ** (S2 +64%!): a MÁSCARA tem valor estrutural — o
   split usa a pontuação como separador de campos; tirar a máscara sem pré-forma cega o núcleo.
   As camadas NÃO são monotônicas → a escolha tem que ser POR COLUNA e MEDIDA — o que reforça o
   "compete no min()" como mecanismo de chão em toda forma.
4. **Nota de máquina**: S3/S5 exigem spec ESTATAL por coluna (delta depende da linha anterior) —
   o `encode_value` per-value de hoje não expressa. É a capacidade nova a projetar: **column-wise
   nature** (com S5 ≡ "troca nas referências" quando o dict vence).

## §5 — DECISÕES pro owner (o que fecha o 0.8 vs pré-1.0)

1. **CRUX — a "nature compete"** — **DECIDIDO (owner 2026-07-12): NO `.8`. FLOOR IMPLEMENTADO.**
   Demo medido (`scripts/spec_demo.py`) + lab RT-provado (`2026-07-12-1917-spec-camadas-v1`) →
   BUG-15 fixado (destravou) → **nature-compete welded**: `multi/core.py` `_encode_multi` agora faz
   a nature COMPETIR no min() por coluna (encoda original vs transformada, fica a menor pelo blob
   serializado completo, incluindo meta, sizes e o custo do `:id`; `nature_specs` desce em vez de
   pré-transformar). Só as colunas onde a nature vence por redução estrita ganham `:id`; empate fica
   no baseline.
   **F4 RESOLVIDO** (medido): receita real com `nature_per_col` = 32665B (a nature perdeu, manteve
   o split) vs 40017B antes. Contrato `never-worse` em 10 testes red→green
  (`tests/test_nature_compete.py`); suíte **634 passed, 2 skipped**, pinos exatos (caminho
   sem-nature byte-idêntico). Telemetria: `multi_info.nature_cols` (venceram) + `nature_lost`
   (perderam) + `nature_apply[col].used`.
   - **RESOLVIDO (owner 2026-07-12):** single-col `nature=` em LIST usa a mesma competição pelo
     blob completo. O header `#TCF.8 :cpf` só é emitido quando a economia do corpo cobre o próprio
     custo; em colunas pequenas, o baseline órfão permanece byte-menor e continua com RT.
   - **CHANGELOG**: o FLOOR muda bytes de coluna-com-nature-que-perde (antes pior, agora igual ao
     baseline) → nota no 0.8.0 (não move pinos; comportamento observável melhora).
2. **CPF real-world standalone** (medição, não código): rodar SPEC_CPF em coluna CPF real com
   clustering administrativo — fecha confirmada-empirica OU expõe a mesma regressão. Falta dataset
   CPF real não-PII/autorizado. **Baixo custo se houver dado**; senão fica registrado.
3. **Heurística de aplicação (EIXO 6)** como guarda `ganho>0` antes de aplicar nature — subsume no
   item 1 (competir É a heurística ganho>0 exata). Não fazer os dois.
4. **Confirmar Opção A** (§3 valida): nenhuma característica nova de byte no `.8`; tudo é pré-1.0/.9.

## §6 — Ideias pro `.9` (owner 2026-07-12; registrar, pensar depois)

- **Heurística estatística de aposta no min() (economia de processamento)**: hoje o FLOOR MEDE os
  dois (original vs nature) e fica o menor — custa 2× encode por coluna-nature. Quando o
  paralelismo pra medir NÃO está disponível, uma HEURÍSTICA ESTATÍSTICA (features baratas:
  cardinalidade, ordenação, entropia por sub-campo, apply_rate amostral) poderia APOSTAR na forma
  provável-min sem encodar ambas — trade: economia de compute × risco de errar a aposta. É o
  min-de-curto estatístico. Cruza com o gate `H-TYPE`/detect_* e com `T-CODE-PARALLEL-BUDGET`
  (quando não há worker, aposta; quando há, mede). **Pensar depois.**
- **Self-explain vs compete (single-col)**: o FLOOR pode DROPAR a nature se ela perde → o arquivo
  perde o marcador `:id` (deixa de se auto-explicar). Owner: "se a gente quiser que o arquivo se
  explique, não tem o que fazer a não ser deixar o nature explícito". Tensão real — um modo
  `force-nature` (marca sempre, custe o que custar, pra semântica downstream) OU o caminho abaixo.
- **Dedução de spec (self-describing SEM marcador explícito)**: "se for algum base, dá pra supor
  qual spec pertence" — deduzir a nature por experimentação/hipótese de tipo (o gabarito propõe,
  RT confirma; = tipos-como-specs/T-OPT-INFERENCE). Se der pra deduzir, não precisa marcar. Também
  hipótese. **Owner: "a gente precisa da estrutura; se ela existir fica mais fácil escolher; não
  tendo estrutura, não temos como mudar o roteamento disso."**

## Critério de aceite

- [x] Owner decidiu e o item §5.1 foi implementado no `.8`: nature-compete multi e single pelo
  blob serializado completo, com regressões de custo de header cobertas.
- [ ] F6 herda o caveat definitivo (§0) + a nota do compilador-é-data-driven (§4).
- [ ] Direções CNPJ (§2) e mapa (§3) registrados no ROADMAP `.9`/pré-1.0 com cross-ref.
- [ ] CPF-model (§1, 10 eixos) vira o gabarito de qualquer spec novo (cross-ref no T-SPEC-STATUS-08).

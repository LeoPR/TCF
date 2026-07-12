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

## §5 — DECISÕES pro owner (o que fecha o 0.8 vs pré-1.0)

1. **CRUX — a "nature compete" entra no 0.8 ou 0.8.1?** — **DECIDIDO (owner 2026-07-12): NO `.8`.**
   Mas com uma pré-condição do owner: **PRIMEIRO demonstrações com dados** das intuições (CPF/CNPJ
   ao menos, depois os outros) — o owner quer VER os exemplos com amostras pra entender a situação
   ANTES da implementação. Ordem: (a) demo medido `scripts/spec_demo.py` → mostrar ao owner; (b)
   implementar nature-compete (encode nos 2 modos, fica o menor) red→green + gate completo. O fix é
   byte-safe-por-construção (nunca pior que o baseline) e não move os pinos (natures não entram em
   D1-D9/D17a/real-world). Revisar 0.8.0 vs 0.8.1 no CHANGELOG (muda bytes de coluna-com-nature).
2. **CPF real-world standalone** (medição, não código): rodar SPEC_CPF em coluna CPF real com
   clustering administrativo — fecha confirmada-empirica OU expõe a mesma regressão. Falta dataset
   CPF real não-PII/autorizado. **Baixo custo se houver dado**; senão fica registrado.
3. **Heurística de aplicação (EIXO 6)** como guarda `ganho>0` antes de aplicar nature — subsume no
   item 1 (competir É a heurística ganho>0 exata). Não fazer os dois.
4. **Confirmar Opção A** (§3 valida): nenhuma característica nova de byte no `.8`; tudo é pré-1.0/.9.

## Critério de aceite

- [ ] Owner decide o item §5.1 (nature-compete: 0.8 vs 0.8.1) — é o crux.
- [ ] F6 herda o caveat definitivo (§0) + a nota do compilador-é-data-driven (§4).
- [ ] Direções CNPJ (§2) e mapa (§3) registrados no ROADMAP `.9`/pré-1.0 com cross-ref.
- [ ] CPF-model (§1, 10 eixos) vira o gabarito de qualquer spec novo (cross-ref no T-SPEC-STATUS-08).

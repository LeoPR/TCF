---
title: META-ESCAPE-DEDUCTION — Pacote 2 (H-ED-01..04, suppressao implicita de escapes)
status: closed
resolution: insufficient-gain
priority: P2
created: 2026-05-21
updated: 2026-05-21
closed: 2026-05-21
related:
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - experiments/lab/dirty/old/welded/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/11-escape-dedutivel/
  - docs/algorithms/HCC.md
  - tickets/META-TYPE-ENCODERS.md
  - tickets/META-PERF-PHASE2.md
---

# META-ESCAPE-DEDUCTION — Pacote 2

## Contexto / motivacao

HCC canonical sempre escapa digit-runs com `\` (e `*`, `~`, `\`) pra evitar
ambiguidade com refs `^N`/atoms. **Mas em muitos contextos o escape e'
deduzivel**: se digit-value > current_node_count, ref nao pode existir,
logo digit-run e' literal sem-ambiguidade. Idem pra outros chars em
contextos especificos.

Origem: identificado em **2026-05-17** ao inspecionar body fork da
tentativa M2 (D11a-h tem 7-10 backslashes/linha cada). Antecedente em
ticket v0.5 frozen (`docs/workbench/_archive/tickets/open/S-supressao-implicita-marcadores.md`).

Prova de conceito antiga: **sub-exp 11 do T01** (15.7% ganho nos 8
datasets D11a-h), MAS **assume 1 lit piece por linha** — invalido em
compositions complexas. Pacote 2 precisa **generalizar**.

## Hipoteses (H-ED-01..04)

| ID | Hipotese | Risco inicial |
|---|---|---|
| **H-ED-01** | Linha 1 do body nunca tem refs → digits sempre literais → escape `\` redundante | Baixo (caso trivial: count=0) |
| **H-ED-02** | Apos `*` separator, proximo nao-digito-de-ref tem contexto deduzivel | Medio (parser state-aware) |
| **H-ED-03** | Escape de `*`, `\`, `~` deduzivel por posicao em alguns casos | Alto (depende sintaxe HCC) |
| **H-ED-04** | Header de coluna (ex: `tipo=numerico`) permite supressao adicional | Medio (opt-in, fora do core) |

## Pergunta cientifica central

Em **datasets reais** (Adult Census, TPC-H), quanto da emit final
HCC e' escape redundante? E quanto disso e' recuperavel preservando
byte-canonical com decoder atualizado?

Quantificacao quick-and-dirty antiga (D11a-h): ~50 backslashes total
em 319 bytes = ~16% do output. Real-world deve ter perfil DIFERENTE
(maior diversidade de chars, menos digit-runs puros).

## Plano

### Fase 1 — caracterizacao (sub-exp 01)

Medir quantos escapes do encode atual SAO deduziveis em:
- D1-D9 (controle)
- Adult Census 1000/5000 rows
- TPC-H 8 tabelas (subset 1000-5000 rows)
- lineitem 5k (cenario perf-test)

Per dataset: total escapes, total deduziveis-H-ED-01 (linha 1 trivial),
total deduziveis-H-ED-02 (apos `*`), etc. Tabela percentual.

### Fase 2 — prototipos isolados (sub-exps 02-04)

Implementar smart_encode + smart_decode em FORK (sem mexer src/tcf).
Variantes:
- v1: H-ED-01 apenas (linha 1 sem escape)
- v2: v1 + H-ED-02 (apos separator)
- v3: v2 + H-ED-03 (outros chars contextuais)

Cada variante:
- Bytes vs canonical
- RT byte-canonical (smart_decode reproduz original)
- Re-encode com smart → decode com canonical: deve **falhar** explicitamente
  (compat broken, esperado)

### Fase 3 — decisao welding (sub-exp 05)

Se ganho real-world >= 5%, considerar welding. Mas:
- **Quebra backward compat** (decoder canonical interpretaria digits bare como refs)
- Requer **versionamento de formato** (`#TCF.7` major bump? ou flag `S` no shebang?)
- Re-validacao D1-D9 baseline obrigatoria

Welding opcoes:
- (A) flag opt-in: `encode(..., smart_escape=True)` produz `#TCF.6 S\n` shebang
- (B) bump major: `#TCF.7` substitui v0.6 (drastic)
- (C) adiar welding, manter fork dirty pra estudos

## Criterio de aceite (KR-style mensuravel)

- [ ] Caracterizacao **completa** em 3 datasets reais (Adult, TPC-H, lineitem)
- [ ] Pelo menos 1 variante: byte loss reduzido em **>= 5%** real-world
- [ ] RT byte-canonical preservado com smart_decode
- [ ] D1-D9 baseline (1615B) revalidado com smart encoder+decoder pareados
- [ ] Decisao explicita sobre welding (A/B/C com justificativa)
- [ ] ADR se welded

## Riscos

1. **Compat-break**: decoder canonical antigo nao decodifica smart output.
   Mitigacao: versionamento explicito (option A flag, option B major bump).
2. **Generalizacao**: prova de conceito antiga assumiu 1 lit/linha; real-world
   tem multiple lits + refs intercalados. Parser estrutural pode ser
   complexo.
3. **Ganho marginal em real-world**: datasets sinteticos T01 tinham muita
   redundancia. Reais (com diversidade) podem ter menos.
4. **Toca src/tcf canonical**: se welded, syntax.py muda. Cuidado especial
   (ja' modificado por ADR-0006, ADR-0007).

## Conexoes

- [Roadmap H-ED-01..04](../experiments/lab/dirty/notas/roadmap-hipoteses.md)
- [Sub-exp 11 T01 (prova de conceito antiga)](../experiments/lab/dirty/old/welded/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/11-escape-dedutivel/)
- [HCC spec](../docs/algorithms/HCC.md)
- [TCF format spec](../docs/algorithms/TCF-format.md) — versionamento
- [ADR-0001 shebang](../docs/adr/0001-tcf-format-shebang.md) — convencao versao
- [META-TYPE-ENCODERS L06](META-TYPE-ENCODERS.md) — Track 2 onde foi originalmente registrado

## Updates datados

### 2026-05-21 — abertura

Ticket criado seguindo nova convencao YAML frontmatter (recomendacao
2026-05-21 em tickets/README.md). Pacote 2 era registrado desde
2026-05-17 sem progresso. Direcao opcao A do plano pos-revisao de
Pacote 4 fechado-parcial. Sub-exp 01 (caracterizacao) e' proximo
passo imediato.

### 2026-05-21 — sub-exp 01 caracterizacao executada

Lab dirty: `experiments/lab/dirty/2026-05-21-escape-deduction/01-caracterizacao-escapes/`

Mediu escapes deduziveis em D1-D9 + Adult Census 1k/5k + TPC-H
region/customer/lineitem 5k. Total body: 942,041B / 29,844 digit
escapes.

| Variante | Real-world weighted |
|---|---:|
| H-ED-01 (linha 1) | 0.01% |
| H-ED-02 (apos `*`) | 0.12% |
| H-ED-original lower bound | **1.13%** |

### 2026-05-21 — FECHAMENTO (insufficient-gain)

Pacote 2 **NAO ATINGE criterio de aceite** (>=5% real-world).
Mesmo upper bound estimado (~2-3%) provavelmente insuficiente.

Custos pra implementar (smart encoder+decoder, versionamento de
formato, ADR, re-validacao multi-camada, manter dois decoders) sao
desproporcionais ao ganho marginal.

Sub-exp 11 antigo (T01) deu 15.7% em D11a-h porque datasets eram
construidos com perfil "digit-dominant". **Nao generaliza pra real-world**.

H-ED-01..04 todas fechadas como `refutada-real-world` no roadmap.
Lab dirty marcado como `closed-insufficient-gain`.

**Aprendizado meta**: este e' o primeiro ticket no formato YAML
frontmatter — funcionou bem pra organizar updates inline + status
estruturado. Validou a convencao 2026-05-21.

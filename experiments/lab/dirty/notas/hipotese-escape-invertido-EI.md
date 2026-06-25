# Hipótese: escape-invertido (EI) — flip global de polaridade por header [aberta, VIÁVEL]

**Data**: 2026-06-25. **Origem**: owner, revendo o caso1-raw (CPF mascarado cheio de `\`).
**Status**: `aberta`, candidato VIÁVEL. **Corrige** a rejeição anterior (eu havia juntado
isto com a escape-deduction fechada — ERRADO; ver distinção). **Confiança**: A-revalidar
(medido em sintético; gate real-world pendente).

## A ideia (owner)
Hoje o HCC escapa TODO digit-run literal com `\` (`_escape_lit`, incondicional) pra
desambiguar de refs. Em coluna **literal-heavy** (CPF, UUID, IDs, datas), isso são MUITOS
`\`. O EI **inverte a polaridade GLOBAL**, marcado por header (`#TCF.8 EI`): digit-run é
**literal por default** (sem `\`); o **ref** (raro) é que ganha marca. Decisão = simples
**contagem de bytes** (inverte se literais-escapados > refs-escapados). Decode: o flag diz
a polaridade. Pra coluna all-literal, é um "pós-filtro" trivial (remove os `\`, decode
re-adiciona).

## DISTINTO da escape-deduction (FECHADA, Pacote 2)
| | deduction (fechada) | **EI** |
|---|---|---|
| decisão | por-ocorrência (`digit>node_count?`) | **global** (contar+flipar) |
| complexidade | alta (contextual) | **baixa** (byte-count + flag) |
| depende node_count | **sim** (colapsou real-world) | **NÃO** |
A deduction caiu 15.7%→0.13% real-world porque a condição falhava em coluna grande. O EI
não depende de node_count — depende só de a coluna ser digit-heavy → não colapsa com tamanho.

## Medição (sintético, read-only 2026-06-25)
- **caso1-raw** (50 CPFs mascarados): 944B, **187 `\` TODOS literais, 0 refs** → EI = 767B
  = **18.8%**.
- **Suíte sintética** (`datasets/synthetic/*`): bruto **9.2%** (4733B, 437 dig-esc). Por
  dataset: **D14-uuid 12.9%**, D13-cpf/D6-ruído **10%**, datetime **7–10%**; texto
  (emails/substring/caos) **~0%** (sem dano).

## Implementação / disambiguação
- **all-literal** (0 refs): TRIVIAL — remove escapes + flag; decode re-adiciona. 1ª versão.
- **com refs**: marcar os refs em vez dos literais (o ganho afina onde há mais refs). Por-
  coluna: inverte SSE literais-escapados > refs-escapados.
- É um **desvio opt-in marcável** → encaixa no #TCF.8 semi-implícito (ADR-0029). ORTOGONAL
  a natures (ajuda coluna digit-heavy SEM nature também).

## Gate (antes de weldar)
- **Real-world digit-heavy** (IDs/datas/números reais — NÃO os snapshots de free-text, que
  são texto → EI baixo). Anti-incidente 2026-05-21: a suíte tem datasets CONSTRUÍDOS
  digit-heavy (D13/D14) → confirmar generalização. Mas o mecanismo (sem node_count) favorece.
- Prototipar é BARATO (pós-filtro byte-count), ao contrário da deduction.

## Cross-links
- [anotacoes-caso1-caso2-escape-dv-pipeline.md](anotacoes-caso1-caso2-escape-dv-pipeline.md)
  (onde a deduction foi marcada fechada — corrigido aqui: EI ≠ deduction),
  [META-ESCAPE-DEDUCTION](../../../../tickets/META-ESCAPE-DEDUCTION.md) (a fechada),
  `_escape_lit` em `composicional/syntax.py` (escapa incondicional hoje).

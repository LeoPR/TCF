# Hipótese: escape-invertido (EI) — flip global de polaridade por header [ENCOSTADA — alcance estreito]

**Data**: 2026-06-25. **Origem**: owner, revendo o caso1-raw (CPF mascarado cheio de `\`).
**Status**: `🔻 encostada` (medido 2026-06-27, alcance ESTREITO). **Corrige** a rejeição
anterior (eu havia juntado isto com a escape-deduction fechada — ERRADO; ver distinção).
**Confiança**: Alta no veredito de alcance.

## VEREDITO DE ALCANCE (lab 2026-06-27 — [result.md](../2026-06-27-EI-alcance/result.md))
A estrutura "ideal" (flip global) **não tem alcance amplo**. Três achados:
1. **Filtro cego nem round-trip faz** — output mistura escape-de-literal com dígitos
   estruturais (refs OBAT, contadores `*N`); EI tem de ser **estágio DENTRO do encoder**.
2. **Textual real só em coluna incompressível** (CPF 21%, decimal 18%, telefone 15%, uuid 13%);
   em coluna estruturada/compressível o pipeline já comeu os escapes → EI net-negativo.
3. **Sob brotli evapora ou INVERTE** (CPF −19.4%) — falha o gate "sob brotli".
→ Nicho textual/lazy puro sobre random-digit. **Encostado**; retomar pelo Estágio 1 (encoder-
internal) só se esse caso de uso aparecer. Estágios 0-3 documentados no result.md.

## A ideia (owner)
Hoje o HCC escapa TODO digit-run literal com `\` (`_escape_lit`, incondicional) pra
desambiguar de refs. Em coluna **literal-heavy** (CPF, UUID, IDs, datas), isso são MUITOS
`\`. O EI **inverte a polaridade GLOBAL**, marcado por header (`#TCF.8 EI`): digit-run é
**literal por default** (sem `\`); o **ref** (raro) é que ganha marca. Decisão = simples
**contagem de bytes** (inverte se literais-escapados > refs-escapados). Decode: o flag diz
a polaridade. Pra coluna all-literal, é um "pós-filtro" trivial (remove os `\`, decode
re-adiciona).

## REFRAME (owner 2026-06-25): EI global = PROVA; o alvo é polaridade INTELIGENTE
O flip GLOBAL (EI) **prova que o ganho existe** e é o **piso** (simples, sempre-aplicável).
O alvo real é um espectro de **inteligência de polaridade de escape**:
- **Piso (provado)**: flip global por header (`#TCF.8 EI`) — esta medição (9–19%).
- **Teto (a estudar)**: decidir **preditivamente e matematicamente DURANTE o processo**
  quando inverter — **não necessariamente global**. Pode ser **serializado**: gastar um
  marcador que inverte **uma linha ou uma sequência** quando paga, voltando depois.
  Atende casos pequenos/grandes/dinâmicos.
- A **escape-deduction** (Pacote 2, fechada) foi UMA tentativa do lado preditivo
  (por-ocorrência, `node_count`) — falhou real-world. Mas o piso provado mostra que **vale
  procurar um mecanismo preditivo/serializado MELHOR**. Reservar como estudo do espectro
  inteiro (global ↔ serializado ↔ preditivo).

## DISTINTO da escape-deduction (FECHADA, Pacote 2) — na decisão por-ocorrência APENAS
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

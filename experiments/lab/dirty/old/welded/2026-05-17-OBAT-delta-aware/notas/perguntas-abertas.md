# Perguntas abertas (roadmap)

**Ultima revisao**: 2026-05-17 (pos-discussao de framing tripartite).
Algumas perguntas mudaram de status — onde a discussao convergiu,
marca-se `RESOLVIDO`. Onde abre nova area, novas perguntas (Q15+).

## Fundamentais

### Q1 — quem detecta tipo? `RESOLVIDO`
- Pre-stage detecta tipo da coluna
- **Nao** passa tipo bruto pro OBAT — gera **dica generica**
  (modo, calibracao, sem nome de tipo)
- OBAT permanece type-agnostic

**Status**: resolvido na discussao de framing. OBAT nao deve saber
"isto e' data". Pre converte info de tipo em dica generica.

### Q2 — quem decide delta semantico? `RESOLVIDO`
- **Ninguem nomeia o delta semanticamente** — nao tem `+1 dia`
- OBAT calcula delta **relativo** (`+N unidades na regiao variavel`)
- HCC materializa em bytes (decide formato, RLE, etc.)

**Status**: resolvido. OBAT trabalha com pesos relativos abstratos.
HCC com pesos absolutos. Sem semantica calendaria nas camadas.

### Q3 — como o decoder sabe reconstruir o delta?
- Decoder ja' tem acesso ao predecessor (idx referenciado)
- Recebe metadata abstrata do body (ex: "rel=+1")
- Aplica metadata ao literal do predecessor → byte reconstruido
- **Sem parsing semantico** no decoder (mantem simetria com OBAT)

**Status**: arquitetura clara. Implementar em tentativa 04.

## Estruturais

### Q4 — tipo do delta no token (OBAT) `RESOLVIDO`
- Nao e' estrutura semantica (`+1d`, "day")
- E' **metadata abstrata** anexa ao TokLit
- Exemplo: `TokLit("1", rel=+1)` — onde `+1` significa "varia por
  uma unidade na regiao variavel relativo ao predecessor"
- Sem unidade. Sem tipo. So' magnitude relativa.

**Status**: resolvido. OBAT cria marcador abstrato, HCC interpreta
e materializa.

### Q5 — quando preferir delta vs literal? `RESOLVIDO`
- Decidido pela **dica generica** do pre-stage
- Pre pode habilitar `enable_relative=True` ou nao
- OBAT, com modo ligado, decide se Δ "cabe" no formato (ex: Δ
  representavel em N bits)
- Sem semantica de "menor que 100 dias" — so' limiares neutros

**Status**: resolvido (vai depender de calibracao da dica). Validar
em tentativa 03/04.

### Q6 — multi-coluna / multi-tipo
Fora de escopo. Uma natureza por vez.

**Status**: out-of-scope. Adiar.

## Operacionais

### Q7 — fork como modulo standalone vs subclass
Fork como funcao `processar_typed()` standalone, mantendo
`processar()` canonico intocado.

**Status**: hipotese — standalone. Confirmar em implementacao.

### Q8 — HCC fork ou extensao do canonico?
Tentativa 02 vai mostrar: se HCC sozinho (sem alterar OBAT) ja'
agrupa near-identical, fork minimo de HCC basta. Se precisar
metadata do OBAT (tentativa 04), fork de ambos.

**Status**: depende de tentativa 02. Decidir apos.

### Q9 — sintaxe no body
Em aberto. Depende da tentativa.
- Tentativa 02: pode reusar `*N|` com placeholder pra varying literal
- Tentativa 04: pode introduzir marker novo (ex: `^N+1` ou `~rel:+1`)
- Compativel com escape rules atuais? Validar caso a caso.

**Status**: em aberto. Tomar forma com implementacao.

## Hipotese central recente `CONFIRMADA — 2026-05-17`

### Q15 — OBAT esta quase pronto? `CONFIRMADA`

Conjectura do user: se OBAT ja' quebra no lugar da diferenca
(Pref + **Lit** + Suf), o trabalho que falta e' so':
1. Verificar se o Lit faz parte de estrutura anterior
2. Decidir como otimizar essa parte

Implicacao: OBAT pode nao precisar de fork — so' uma **revisao**
pra confirmar que isola bem a variacao. Trabalho real e' HCC
agrupando os Lits isolados.

**Status (apos tentativa 02)**: **confirmada empiricamente**.
HCC sozinho (sem alterar OBAT) extraiu -22.2% bytes em D11a-h
(958 → 745). RT 8/8 OK. Sintaxe `*N+delta|<template>` no body.
Detalhes em `../02-hcc-sozinho-rle-near-identical/result.md`.

## Hints genericos `NOVA — 2026-05-17`

### Q16 — qual e' a API minima de hints?

Espectro possivel:
- `byte_window=(X,Y)` — janela esperada de variacao
- `enable_relative=True` — habilitar modo relativo
- `monotonic_expected=True` — esperar sequencia ordenada
- `max_delta=N` — limiar pra emitir delta vs literal

Quais sao **realmente** genericas? Quais sao viciadas disfarcadas?

**Status**: a explorar em tentativa 03. Pode mudar.

### Q17 — onde a dica "escorrega" pra viciada?

Se Pre detectou "data ISO" pra computar `byte_window=(11,15)`, a
info de tipo influenciou indiretamente. O canal (variavel) e'
generico, mas a fonte (calculo) e' tipo-aware.

Tolerancia: aceitar quando o canal e' generico, mesmo se a fonte
nao for. Re-avaliar se isso quebra o objetivo de
type-agnosticismo na pratica.

**Status**: filosofica. Observar empirico.

## Avancadas (depois das tentativas 02/03/04)

### Q10 — hints estruturados completos (ABANDONADO)
~~Alem de column_type, passar format, monotonic, cadence...~~

**Status**: abandonado. Viola separacao. Substituido por Q16 (hints
genericos sem nome de tipo).

### Q11 — calendar-LCP em vez de byte-LCP (REPENSAR)
~~Quando tipo conhecido, LCP semantico em niveis calendaricos...~~

**Status**: violacao de separacao (OBAT precisaria saber calendario).
Repensar como variante generica — talvez "LCP sobre regioes
calibradas pela dica byte_window".

### Q12 — multi-camada delta no body do HCC
Se HCC tiver tokens-delta em runs longos, otimizar serializacao:
`*9|^N+1` em vez de 9 linhas.

**Status**: depende de tentativa 04. Forma a definir.

### Q13 — composicao com outras naturezas
Templated + delta = template com slots delta-aware. Quando T02
existir, esta linha pode ser interessante.

**Status**: out-of-scope curto prazo. Anotado.

### Q14 — onde fica o stage A (identify) do staged pipeline? `RESOLVIDO`
- Stage A migra pra **pre-stage**, gerando dica generica
- Stage B (normalize) e C (optimize) podem ser absorvidos pelo HCC
  ou eliminados (depende das tentativas)

**Status**: resolvido em direcao. Detalhes vao tomar forma.

## Tentativas planejadas + status

| # | Nome | Escopo | Mexe em | Status |
|---|---|---|---|---|
| 02 | HCC sozinho | RLE pra near-identical tokens | so' HCC (fork) | **CONCLUIDA — Q15 confirmada (-22.2% bytes)** |
| 03 | OBAT com `byte_window` | Calibrar LCP/LCS via dica | so' OBAT (fork) + Pre | pending (re-avaliar valor) |
| 04 | OBAT relativo + HCC RLE | Δ abstrato + agregacao | OBAT + HCC (forks) + Pre | pending (re-avaliar valor pos-03) |
| 05? | Cadence-break recovery | Recuperar pos-transicao `\\9`→`\\10` | HCC (fork) + talvez Pre | nova hipotese H-DA-04 |
| 06? | Outros tipos de delta | numerico IDs, signed, step != 1 | HCC fork | nova hipotese H-DA-06 |

Ordem original: 02 → 03 → 04. Apos 02, 03/04 podem ter escopo
reduzido (HCC ja' extraiu o ganho principal).

## Hipoteses ortogonais identificadas (registradas globalmente)

### Q18 — Escape automatico (ORTOGONAL — nao testar neste lab)

Identificada em 2026-05-17 ao revisar body fork da tentativa 02.
Linha 1 dos D11a-h tem 7-10 backslashes cada — overhead de escape
literal independente de delta-awareness.

Antecedente: `docs/workbench/_archive/tickets/open/S-supressao-implicita-marcadores.md`
(2026-05-10, era v0.5). Nunca testada em v0.6 HCC.

**Decisao**: registrada em
[`../../../notas/roadmap-hipoteses.md`](../../../notas/roadmap-hipoteses.md)
Pacote 2 (H-ED-01 a H-ED-04). Candidata a dirty lab proprio
(`2026-05-XX-escape-deduction-hcc-v06`). **Nao misturar com
tentativas 02/03/04 deste lab** (princip-io de ablacao).

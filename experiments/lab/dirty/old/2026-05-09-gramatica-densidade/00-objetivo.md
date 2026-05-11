# Mesa — gramática e densidade da sintaxe

Três perguntas levantadas que afetam o **formato textual** independente
da escolha de RLE/dict/delta:

1. **Empacotamento dos absolutos**: `2026-01-05` (10 chars) pode ser
   `260105` (6 chars) ou similar. Compressão por **representação** do
   valor, não da estrutura. Ortogonal a RLE/dict/delta.

2. **Quebra de linha como separador**: em colunas onde os tokens são
   auto-delimitados (deltas começam com `+`/`-`/`0`, absolutos têm
   formato fixo), `\n` pode ser elidido sem ambiguidade.

3. **Defaults implícitos para padrões frequentes**: `3*+1` poderia ser
   `3*+` se `+` sozinho após `*` significar `+1` (delta mais comum).

A mesa anterior (`2026-05-09-delta-datas/`) fechou a lógica do delta como
transformação. Esta mesa **densifica a sintaxe** depois que delta já
fez seu trabalho.

---

## Princípio do usuário

> Construção da linguagem primeiro e eliminação de redundâncias possíveis
> em segundo lugar.

Esta mesa segue essa ordem:
1. **Linguagem** — fechar gramática formal de tokens, separadores,
   estados do parser
2. **Densificação** — onde há bytes redundantes que podem sumir sem
   perda de unicidade

---

## Estrutura da mesa

| Arquivo | Conteúdo |
|---|---|
| `01-empacotar-absolutos.md` | Como empacotar valores absolutos (datas, números) |
| `02-inline-vs-linha.md` | Quando `\n` pode ser elidido |
| `03-defaults-frequentes.md` | Shorthands para padrões comuns (`3*+` = `3*+1`) |
| `04-gramatica-formal.md` | Gramática consolidada |
| `05-conclusoes.md` | O que adiciona à hierarquia Lxxx |

---

## Hipóteses prévias

| ID | Hipótese | Predição |
|---|---|---|
| H-G1 | Empacotar absolutos vale só quando δ está OFF (com δ, há só 1 absoluto) | confirma |
| H-G2 | Inline mode salva bytes proporcionais ao número de tokens | sim, mas cuidado com legibilidade |
| H-G3 | Deltas `0` e `+1` dominam (>70% das transições em dados temporais) | provável; justifica defaults |
| H-G4 | A gramática unificada cabe em uma página de regras simples | desejável |
| H-G5 | Cada nova densificação custa 1 dimensão de complexidade no decoder | inevitável; precisa fechar a conta |

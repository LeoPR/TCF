---
title: T-FMT-ESCAPE-COMBINATORIAL-STUDY — reestudar o escape (combinatório + estratégias de outros mecanismos)
status: open
priority: P3
created: 2026-07-15
updated: 2026-07-15
gate: ".9 / pré-1.0 (ferramental de formato)"
blocked-by: []
related:
  - tickets/T-FMT-QUOTING-STUDY.md
  - tickets/T-FMT-NAME-ESCAPING.md
  - tickets/T-API-BOUNDARY-CONTRACTS.md
  - src/tcf/multi/core.py
  - src/tcf/hierarchical.py
---

# T-FMT-ESCAPE-COMBINATORIAL-STUDY — o escape merece um estudo próprio

**[dispositivo→registro; SÓ REGISTRAR, não estudar agora]** Owner (2026-07-15): *"o escape me
incomoda; olhando, tenho sempre a sensação de que dá pra fazer melhor. Sei que a estratégia já está
bem boa (escape + regras têm representação bem pequena), mas não fizemos um estudo combinatório, nem
comparamos com a estratégia usada em outros mecanismos de armazenamento."*

Contexto: o escape atual é **backslash interim** — `.8M` escapa `,=:\`+`!@%` inicial
([T-FMT-NAME-ESCAPING](T-FMT-NAME-ESCAPING.md), welded); o `.8H` acabou de portar a mesma convenção
p/ nomes com `,[]{}:#\`+espaço-inicial (commit `40a7e10`). Funciona e é barato, mas nunca foi
**estudado combinatoriamente** nem comparado com o estado-da-arte.

Este ticket amplia o escopo de [T-FMT-QUOTING-STUDY](T-FMT-QUOTING-STUDY.md) (que era só
name-quoting-além-do-backslash): agora inclui o **eixo combinatório** e o **benchmarking contra
outros mecanismos de armazenamento**.

## Perguntas a responder (quando for a hora)

1. **Combinatória**: enumerar as classes de char (separadores do meta, prefixos de modo, colchetes
   de hierarquia, `\n`, espaço, unicode) × posições (inicial/interno/final) × contextos (nome,
   valor, size) → matriz completa; onde o backslash-simples QUEBRA vs onde basta; custo (bytes) por
   célula. Hoje isso é coberto por fuzz pontual, não por enumeração.
2. **Estado-da-arte** (comparar estratégias de outros mecanismos):
   - **CSV/RFC 4180**: quoting com aspas + doubling (`""`) — quando ganha do backslash?
   - **JSON**: `\uXXXX` + escapes nomeados; custo vs legibilidade.
   - **Parquet/Arrow**: length-prefixed (sem escape — o delimitador não existe no wire binário).
   - **Protobuf/Avro/MessagePack/CBOR**: length-prefixed / tag-length-value (idem, escape=0).
   - **Postgres COPY**, **TSV**, **Bencode** (length-prefix textual `N:str`).
   - Eixo-chave: **escape (delimitador in-band)** vs **length-prefix (delimitador eliminado)** — o
     TCF já usa size (hex) em várias posições; quando o size TORNA o escape desnecessário?
3. **Trade do TCF**: o pilar é TEXTO+explicabilidade (§FILOSOFIA). Length-prefix mata o escape mas
   custa legibilidade (o nome deixa de ser lido direto). Qual o ponto ótimo por posição? (nome do
   header quer legibilidade; valor de corpo talvez não.)
4. **Custo real**: bytes de escape em dado real (nomes/valores com separador são raros — medir a
   frequência real antes de otimizar; anti-incidente 2026-05-21).

## Escopo / não-escopo

- **É**: estudo/benchmark de formato (lab), quando priorizado. Pode propor mudança de convenção OU
  confirmar que o backslash-simples é o ponto certo (resultado válido).
- **NÃO é**: mudar `src/tcf` agora. O escaping atual (`.8M` + `.8H`) fica como está até o estudo.
- **Cuidado**: qualquer mudança de wire de escape re-pina baselines (ADR-0024) e toca o freeze
  pré-1.0 dos contratos de borda ([T-API-BOUNDARY-CONTRACTS](T-API-BOUNDARY-CONTRACTS.md)).

## Critério de aceite

- [ ] Matriz combinatória char×posição×contexto documentada (onde quebra / custo).
- [ ] Comparação medida vs ≥3 mecanismos de armazenamento (ao menos 1 escape-based + 1 length-prefix).
- [ ] Recomendação: manter backslash OU mudar (com re-pin + freeze), justificada por bytes+legibilidade.

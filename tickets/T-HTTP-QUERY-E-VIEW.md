---
title: T-HTTP-QUERY-E-VIEW — o método HTTP QUERY (RFC 10008) como transporte natural do view()/lazy
status: open
priority: P2
created: 2026-08-23
updated: 2026-08-23
target: "pesquisa/prova-de-conceito — não muda o formato; candidato ao lab didático"
blocked-by: []
related:
  - tickets/T-LAB-DIDATICO-PONTA-A-PONTA.md
  - tickets/T-PERF-BORDAS-E-MODOS-09.md
  - docs/reference/lazy-view.md
  - experiments/lab/dirty/2026-08/2026-08-23/2026-08-23-0300-tempo-ate-o-dado-chegar/
---

# T-HTTP-QUERY-E-VIEW

**[dispositivo → registro. Pesquisa; nada em `src/tcf`.]**

Direção do owner (2026-08-23): *"o HTTP está com suporte a uma função chamada QUERY, seria ótimo
agora pra testar coisas como os modos view/lazy e tudo mais."*

## O fato apurado (não é mais draft)

**QUERY é RFC 10008, Proposed Standard, publicada em junho/2026** — autores Julian Reschke,
James Snell (Cloudflare) e Mike Bishop (Akamai). Veio do
[`draft-ietf-httpbis-safe-method-w-body`](https://datatracker.ietf.org/doc/draft-ietf-httpbis-safe-method-w-body/).
Não estava no RFC 9110, que lista só os oito métodos clássicos.

O que ela resolve, nas palavras da spec:

| propriedade | QUERY | por que importa aqui |
|---|---|---|
| **corpo na requisição** | *"a entrada da operação de consulta é passada como conteúdo da requisição, não como parte da URI"* | consulta complexa deixa de caber (ou não caber) na URL |
| **safe + idempotente** | *"QUERY requests are safe... e são idempotentes; podem ser repetidas quando necessário"* | ao contrário de POST: pode repetir, pode pré-buscar |
| **resposta cacheável** | *"A resposta a um QUERY é cacheável; um cache PODE usá-la para satisfazer QUERY subsequentes"* | POST com corpo não dá isso |
| **chave de cache** | *"A chave de cache para um QUERY DEVE incorporar o conteúdo da requisição e metadados relacionados"* | a **consulta** vira parte da chave |
| **`Content-Location`** | aponta um recurso com o **resultado**; o cliente pode fazer `GET` nele depois | resultado de consulta vira recurso endereçável |

## Por que casa com o `view()`

O `view()` já faz consulta seletiva sobre o blob — `count`, `sum`, `where`, `select`,
`group_count` — materializando só as colunas que a pergunta toca (medido: 7,9% do blob numa
consulta real, contra 100% de um `decode()`). Faltava o **verbo de transporte** para isso:

- `GET` não tem corpo → predicado tem de virar querystring, e complica rápido
- `POST` tem corpo, mas **não é safe nem cacheável** → perde repetição e cache

QUERY dá exatamente as três coisas. E há uma simetria interessante a investigar: o corpo do
QUERY poderia **ele próprio ser TCF** — a consulta e a resposta no mesmo formato.

## Hipóteses a medir (nenhuma afirmada)

1. **Cache de consulta**: com a chave incorporando o corpo, duas consultas idênticas sobre o
   mesmo blob acertam o cache. Quanto isso vale na topologia 1 servidor : N clientes?
2. **`view()` no servidor vs no cliente**: hoje o modelo assume o cliente consultando o blob
   recebido. QUERY abre a outra: o **servidor** roda o `view()` e devolve só o resultado —
   muito menor. Qual ganha, e a partir de que seletividade?
3. **`Content-Location`**: resultado de consulta como recurso endereçável — cabe no modelo do
   TCF (o resultado também é um blob TCF)?
4. **Suporte real**: quem já implementa? (o .NET 10 tem; servidores e proxies, a verificar).
   Sem suporte de ponta a ponta, é PoC, não caminho de produção.

## O que NÃO é

Não é mudança de formato. O TCF é o **payload**; QUERY é o **envelope**. Nada em `src/tcf`.

## Critério de aceite

- [ ] PoC cliente/servidor com QUERY carregando consulta e devolvendo TCF
- [ ] Medir: `view()` no cliente vs no servidor, por faixa de seletividade
- [ ] Medir o acerto de cache com corpo na chave
- [ ] Registrar honestamente o estado do suporte (servidores, proxies, clientes)
- [ ] Se não houver suporte suficiente, dizer isso e parar — PoC vale, produção não

## Fontes

- [RFC 10008 — anúncio IETF](https://mailarchive.ietf.org/arch/msg/ietf-announce/uNaYyRDGKjyOn_KDT2JaGLlm9fE/)
- [draft-ietf-httpbis-safe-method-w-body (datatracker)](https://datatracker.ietf.org/doc/draft-ietf-httpbis-safe-method-w-body/)
- [RFC 9110 §9.3](https://httpwg.org/specs/rfc9110.html) — os oito métodos clássicos, sem QUERY

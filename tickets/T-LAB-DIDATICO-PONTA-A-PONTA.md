---
title: T-LAB-DIDATICO-PONTA-A-PONTA, micro-lab do fluxo real (coleta → dataset → schema → encode → cliente/servidor → disponibilizar)
status: open
priority: P2
created: 2026-08-23
updated: 2026-08-23
target: "pós-0.8.0, demonstração executável; provavelmente experiments/lab/clean/"
blocked-by: []
related:
  - tickets/T-DOC-MANUAL-FORMAL.md
  - tickets/T-HTTP-QUERY-E-VIEW.md
  - docs/reference/lazy-view.md
---

# T-LAB-DIDATICO-PONTA-A-PONTA

**[dispositivo → registro.]**

Direção do owner (2026-08-23): *"fechar um micro lab didático, só mostrando como seria coletar
os dados, organizar para deixar um dataset OK, o schema, uso do encode, o envio, o
client-server e como disponibiliza."*

## Por que é diferente do manual

O [`T-DOC-MANUAL-FORMAL`](T-DOC-MANUAL-FORMAL.md) ensina **cada comando**. Este lab mostra **o
fluxo inteiro funcionando**, é a diferença entre a referência e o exemplo completo que se
roda. Ele responde *"como isso vive num sistema de verdade?"*, que nenhuma página de
referência responde.

E ele fecha um buraco real: o TCF é sobre **transmissão**, mas não existe no repo **nenhum
exemplo de cliente/servidor**. A topologia que o owner descreve (servidor central, N clientes,
servidor também responde TCF) nunca foi demonstrada, só modelada.

## As seis etapas

| etapa | o que mostra | apoio que já existe |
|---|---|---|
| 1. **coletar** | de onde vem o dado bruto (CSV, dump, API) | hubs em `Z:/tcf-data`, `scripts/dataset_reader.py` |
| 2. **organizar** | o que é "dataset OK": colunas, tipos, nulos, ragged | `src/shaper/` (I3), `build_schema` |
| 3. **schema** | declarar specs por coluna; incremental | ADR-0047, `schema=` |
| 4. **encode** | o wire, e por que ele ficou daquele tamanho | `SideOutputs` (telemetria opt-in) |
| 5. **envio** | HTTP real, com `Content-Encoding` | **não existe nada; é o que o lab cria** |
| 6. **disponibilizar** | o consumidor: `decode` completo **ou** `view()` seletivo | `docs/reference/lazy-view.md` |

## O que o lab tem de provar (não só ilustrar)

- **round-trip ponta a ponta**: o que o cliente recebe é igual ao que o servidor tinha
- **o `view()` tocando menos que o `decode()`**: medido, não afirmado (o argumento central
  do formato, e nunca demonstrado num fluxo real)
- **a topologia 1 servidor : N clientes**, que o bench 1:1 não representa
  ([`T-PERF-BORDAS-E-MODOS-09`](T-PERF-BORDAS-E-MODOS-09.md))

## Onde vive

Provavelmente `experiments/lab/clean/`, é **publicável** (a fronteira de 2026-08-22 mantém
`clean/` no repo) e serve de material do manual. Estrutura obrigatória de lab vale (I2):
`inputs/`, `outputs/`, portão anti-órfão.

## Critério de aceite

- [ ] Roda de ponta a ponta com um comando, sem depender de `Z:/` (dado embarcado pequeno)
- [ ] Servidor + cliente reais (stdlib basta: `http.server`), sem framework
- [ ] RT provado em assert, não em prosa
- [ ] `view()` vs `decode()` medido no mesmo fluxo
- [ ] Cada etapa explicada em uma frase: é didático, não exaustivo

## Não fazer agora

Framework web, autenticação, produção. O lab é **didático**: o mínimo que mostra o fluxo.

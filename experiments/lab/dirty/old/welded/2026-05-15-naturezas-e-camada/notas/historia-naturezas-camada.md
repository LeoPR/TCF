# Historia — Naturezas dos dados e estudos da camada de algoritmo

Narrativa cronologica do dirty lab `2026-05-15-naturezas-e-camada/`.
Preenchida conforme macros fecham.

## Origem (2026-05-15)

EXP-008 (compressao comparada raw vs TCF com 5 compressores)
revelou:

- TCF reduz **64%** vs csv sozinho;
- Mas brotli/zstd dominam em datasets pequenos (overhead fixo dilui em escala);
- TCF + compressor raramente complementa nessa escala;
- D10-D15 (tipos ERP/CRM variety) estao parados — TCF v0.6 sem
  type encoders nao consegue normalizar variedade de formato.

[Roadmap perspectiva-triplice](../../../../docs/theory/perspectiva-triplice-e-pre-tx.md)
propunha 3 estrategias. Decisao: explorar **Estrategia 1.A**
(type encoders) e **Estrategia 3.B** (slot detection online) em
paralelo.

Plano-mestre: [`tickets/META-TYPE-ENCODERS.md`](../../../../../tickets/META-TYPE-ENCODERS.md).

Principio: **estudar pela natureza do comportamento dos dados,
nao pelos dados em si**. Encoder por nature (incremental, templated,
enumerated, ...) em vez de encoder por tipo (CPF, UUID, data, ...).

## Macros (cronologico)

(preencher conforme fechados — cada um entra aqui em ordem)

- _(em planejamento)_ **T01** — Incremental (base + delta)
- _(em planejamento)_ **T02** — Templated (layout extract)
- _(em planejamento)_ **L05** — Pre-filter de candidatos no HCC

## Lecoes / observacoes acumuladas

(preencher conforme emergem)

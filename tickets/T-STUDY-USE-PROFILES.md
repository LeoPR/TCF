---
title: T-STUDY-USE-PROFILES — perfis de uso (transmissão × armazenamento) e a calibração dos vértices
status: open
priority: P3
created: 2026-08-20
updated: 2026-08-20
target: ".9 / pré-1.0 (estudo; nenhuma mudança no .8)"
blocked-by: []
related:
  - docs/adr/0002-vertice-triplice-restricao.md
  - tickets/T-REL-08-CLOSEOUT.md
  - tickets/T-CODE-PARALLEL-BUDGET.md
  - experiments/lab/dirty/notas/diario/2026-08-20.md
  - experiments/lab/dirty/notas/2026-07/contrato-externalizado-e-aceleradores.md
---

# T-STUDY-USE-PROFILES — perfis de uso e a calibração dos vértices

**[dispositivo → registro. SÓ ESTUDAR, não mexer em `src/tcf`.]**

## Contexto

Direção do owner (2026-08-20, diário): o TCF tem **perfis de uso** com economia diferente, e
os vértices ortogonais poderiam ser *calibrados por situação*:

1. **Transmissão assimétrica** — muitos clients gastam tempo comprimindo; um servidor
   central precisa de descompressão rápida. *"O TCF joga as cargas nos lugares corretos."*
2. **Armazenamento** — gasta tempo compactando/guardando uma vez, com a vantagem de decode
   rápido, `view()` lazy nas consultas, e possivelmente índice sidecar (à la Parquet/HDFS).

## A tensão que este ticket EXISTE para resolver

**A [ADR-0002](../docs/adr/0002-vertice-triplice-restricao.md) rejeitou explicitamente a
Opção 3 — "trade-off por flag"** (*"múltiplos formatos pra suportar = manutenção alta"*), e
decidiu o vértice tríplice como **restrição dura**: *"técnicas multi-pass / memória > O(1) /
look-ahead são descartadas mesmo com ganho"*.

**"Calibrar por situação" é aquela Opção 3.** Este estudo não pode contorná-la por fora: ou
conclui que a restrição dura se mantém, ou **produz o material para uma ADR que a supersede**
— o padrão que a ADR-0034 usou com a ADR-0029.

### E o código já se moveu, sem registro (medido 2026-08-20)

Os candidatos V2 são **batch por construção**: `_v2b_encode` e `_struct_split_encode`
recebem a coluna inteira e varrem tudo (2× e 7×) antes de decidir; o gate do split é
`for v in values[1:]` — look-ahead total, que a ADR-0002 lista como **refutado**
(*"Sliding window pattern detect — Buffer > O(1)"*).

As **ADR-0025 e ADR-0026 não mencionam** a ADR-0002. Leitura provável: a restrição
constrangia o **core de coluna** (OBAT/HCC) e o ciclo 0.7 acrescentou uma camada de
**orquestração multi-col** batch — sem que a fronteira fosse redocumentada.

## O que estudar

| # | pergunta | por quê |
|---|---|---|
| **P1** | Qual a assimetria encode/decode **medida hoje**? (o encode paga `min()` de 4 candidatos; o decode fatia por size) | é a tese central do perfil de transmissão, e **nunca foi medida** |
| **P2** | O que muda entre "1 encode / 1 decode" e "1 encode / N decodes"? | decide se encode caro se paga |
| **P3** | A fronteira da ADR-0002 hoje: **onde** o single-pass ainda vale e onde já não vale? | precede qualquer supersede |
| **P4** | Perfis de *emissão* (um formato, esforço variável) resolvem sem virar `L0..L9`? | preserva a decisão da ADR-0002 |
| **P5** | O que o Parquet/HDFS resolve que o `.tcfx` sidecar precisaria resolver? | já triado em `T-REL-08:113` como `.9`/2.0 |

## O que este ticket NÃO é

- **Não é** proposta de flags `L0..L9`. Se o estudo levar lá, exige ADR de supersede.
- **Não** duplica `T-REL-08:113` (adapter/sidecar/chunking/index-on-arrival, já triados) —
  este cobre o eixo **transmissão assimétrica**, que aquele não cobre.
- **Não** toca `src/tcf`.

## Ordem sugerida (e uma discordância registrada)

O owner sugeriu: *"depois de otimizar bem os algoritmos, conseguimos medir melhor as
situações"*. **Registro a discordância**: o perfil de uso decide **quais** otimizações valem,
não o contrário — e o `bn-dict-perspectivas` já estabeleceu o padrão ao mandar *"medir a
latência ANTES de cravar formato"*.

Proposta: **P1 e P3 primeiro** (baratos, e P1 usa o bench que já existe). São eles que dizem
se P2/P4/P5 valem o esforço. Decisão de ordem é do owner.

## Critérios de aceite

- [ ] P1 medido, com o mesmo rigor dos labs (§RT, evidência em disco, mix declarado)
- [ ] P3 respondido: mapa de onde o single-pass vale hoje
- [ ] Decisão registrada: a ADR-0002 se mantém, ou entra ADR de supersede
- [ ] Se supersede: a ADR nova cita ADR-0025/0026 e resolve a fronteira core × orquestração

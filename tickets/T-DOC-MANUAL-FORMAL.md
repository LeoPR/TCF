---
title: T-DOC-MANUAL-FORMAL, manual didático no padrão das ferramentas de dados (índice, quickstart, entradas por tipo)
status: open
priority: P2
created: 2026-08-23
updated: 2026-09-01
gate: "documentacao (continuo, sem ciclo) (triagem 2026-09-01)"
target: "pós-0.8.0, documentação de entrega; não muda código"
blocked-by: []
related:
  - docs/reference/api.md
  - docs/how-to/use-natures.md
  - README.pypi.md
  - tickets/T-LAB-DIDATICO-PONTA-A-PONTA.md
---

# T-DOC-MANUAL-FORMAL

**[dispositivo → registro. Documentação de entrega; não toca `src/tcf`.]**

Direção do owner (2026-08-23): *"organizar uma documentação mais formal para explicar os
comandos em sequência mais didática, igual aos documentos de outras ferramentas, como polars
ou pandas, com index, exemplo quickstart e entradas variadas de cada tipo."*

## O problema

O `.8` tem documentação **boa e verificada**, mas organizada por **origem**, não por
**pergunta do leitor**. Hoje: `docs/algorithms/` (como funciona), `docs/how-to/` (receitas),
`docs/reference/` (superfície), ADRs (por que). Falta a camada que o polars/pandas têm:

- **índice navegável**: o leitor não sabe por onde entrar
- **quickstart** de 5 minutos que leva do zero ao round-trip
- **entrada por TIPO de dado**: "tenho um CSV", "tenho JSON aninhado", "tenho uma coluna
  de CPF", "tenho 500 mil linhas", cada uma levando ao caminho certo
- **sequência**: hoje cada doc é uma ilha; falta o fio que liga instalar → encodar →
  consultar → transmitir

## O que já existe e serve de matéria-prima

| já pronto | vira |
|---|---|
| `README.pypi.md` (182 linhas, focado, verificado) | base do quickstart |
| `docs/reference/api.md` | a referência, já com dispatch por tipo de entrada |
| `docs/how-to/*` | as receitas, já em Diátaxis |
| `docs/algorithms/TCF-format.*` | a explicação do formato |
| lab de auditoria de capa (G1-G7) | **a régua**: estende para o manual novo |

O projeto já segue **Diátaxis** (ADR-0012): tutorial / how-to / reference / explanation. O
manual não substitui isso, ele é o **wayfinding** que falta por cima.

## Escopo proposto

1. **`docs/index.md`**: a porta: o que é, por onde começar, mapa das quatro camadas
2. **Quickstart**: instalar, encodar uma lista, encodar uma tabela, round-trip, `view()`
3. **"Comece pelo seu dado"**: uma página por forma de entrada (CSV, JSON aninhado, DB
   dump, coluna tipada, coluna com spec), cada uma com o exemplo mínimo executável
4. **Sequência de uso**: o fio: coletar → schema → encode → transmitir → consultar
5. **Bilíngue**, seguindo a convenção já existente (EN canônico + pt-BR)

## Critério de aceite

- [ ] Todo exemplo **executável e verificado**: entra na régua do varredor de snippets
- [ ] Nenhum número afirmado sem medição (I4/§RT)
- [ ] Sem cronologia (I1): manual diz o que vale, não o que mudou
- [ ] Índice cobre 100% das páginas; nenhum órfão
- [ ] Links absolutos onde a página puder ser lida fora do repo

## Não fazer agora

Escrever antes de decidir a **estrutura do índice**: é o que dá o fio. Começar pelo
esqueleto e validar com o owner antes de encher de conteúdo.

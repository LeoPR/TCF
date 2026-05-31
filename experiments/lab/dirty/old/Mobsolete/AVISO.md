# Mobsolete — blueprints amassados (pre-reset v0.6)

**O que e' isto**: 26 experimentos de 2026-05-07 a 2026-05-25 do
**ciclo anterior** ao reset v0.6 (10 de maio).

**Estado**: **OBSOLETO COMO REFERENCIA CANONICA.**

## Aviso

Esta pasta era `old/` ate' 2026-05-13. Renomeada para `Mobsolete/`
para deixar explicito que e' **lixao de blueprints amassados** —
ideias rascunhadas durante exploracao anterior, NAO sao referencia
para v0.6 atual.

**NAO citar como evidencia em ticket, finding ou paper.**

## Para que serve

1. **Revisar conceitos** que podem retornar ao v0.6 (sempre
   recriados, nunca importados)
2. **Localizar bugs ja' diagnosticados** (registro historico)
3. **Inspirar novos experimentos** quando necessario

## O que ja' foi resgatado para v0.6

- Conceito de online incremental (Lab 14-15) → exp 16 cleanup → M0
- Patricia bidir + gain refinado → exp 17-19 do M0
- Encadeamento `*N=P+ext` (Lab 20-21) → M3.B (mapeado, sem ganho
  no regime atual)
- 3 camadas ortogonais (Lab 14) → conceito guia em M1/M2/M3
- Marcadores deduzideis (Lab 22) → ABANDONADO (M1.C confirmou
  empate com regra de ouro do agrupamento)

## O que ainda esta' aqui sem ser usado

Ideias mapeadas no
[`../../docs/workbench/research-notes/_archive/`](../../../docs/workbench/research-notes/_archive/)
mas nao implementadas no v0.6 (ver agente de revisao anterior):

- Padroes estruturais (CPF, UUID, IP) com mascara — depende de
  datasets reais
- Delta-of-delta + regressao para numericos — fora do escopo
  tabular textual atual
- Streaming dict / chunks com dict local — para colunas grandes,
  futuro prototipo
- Multi-prefixo topologico — heuristica meta nao implementada

## Como referenciar

Citar por:
- Conceito (ex: "ideia explorada em Mobsolete Lab 20-21 sob outro
  algoritmo")
- Aprendizado historico
- NUNCA por bytes/numeros (formato diferente)

Para acessar, ver subpastas com seus `notes.md`.

# Workbench — TCF v0.6

> **HISTÓRICO (faxina 2026-06-21)**: este README descreve o estado até M9 (pré-0.7).
> O motor canonical está em `src/tcf/` (M10, 0.7.1). Para o estado vivo, ver `STATUS.md`.

**Reset em 2026-05-10.** O ciclo anterior foi inteiramente
arquivado em [`_archive/`](_archive/) como **blueprint não-canônico**.

---

## Perspectiva atual

O trabalho ativo do TCF v0.6 vive em dois lugares:

```
experiments/lab/dirty/              ← fonte da verdade (codigo + notas tecnicas)
  README.md                         ← indice dos macros M0-M9
  notas/historia-dirty-lab.md       ← narrativa canonica (atualizada ate' M9)
  notas/roadmap-hipoteses.md        ← direcoes futuras
  M0-fase-exploratoria-inicial/     ← algoritmo raiz TCF-CORE
  2026-05-16-M8-virtual-refs-clean-output/ ← compactacao composicional canonica
  2026-05-17-M9-stress-adversarial/ ← stress 9 datasets

docs/workbench/research-notes/      ← sintese consolidada
  INDEX.md                          ← pontos pra dirty + listagem das notas
  2026-05-11-sintese-algoritmos-v06.md  (historica — superada)
```

**Para entrar no trabalho atual, ler em ordem**:
1. [`../experiments/lab/dirty/notas/historia-dirty-lab.md`](../experiments/lab/dirty/notas/historia-dirty-lab.md)
2. [`../experiments/lab/dirty/old/2026-05-17-M9-stress-adversarial/README.md`](../experiments/lab/dirty/old/2026-05-17-M9-stress-adversarial/README.md) (M9 stress)
3. [`../experiments/lab/dirty/old/2026-05-16-M8-virtual-refs-clean-output/README.md`](../experiments/lab/dirty/old/2026-05-16-M8-virtual-refs-clean-output/README.md) (M8 canonico — fonte do HCC welded)
4. [`../experiments/lab/dirty/notas/roadmap-hipoteses.md`](../experiments/lab/dirty/notas/roadmap-hipoteses.md) (proximos passos)

---

## O que mudou em relação ao ciclo anterior

| Antes (≤ v0.5) | Agora (v0.6) |
|---|---|
| Foco em formato textual columnar para LLM ler | Foco em algoritmo de compressão estrutural de strings |
| Hierarquia de níveis L0/L1/L2/L3 | Algoritmo único parametrizável |
| Comparação com CSV/JSON/HTML em accuracy LLM | Comparação com Re-Pair/Front-coding/HTFC em bytes e unidades |
| Hipóteses F-Q1..F-Q28 sobre comportamento de modelos | Verificação de comportamento de algoritmo (4 perguntas no dirty README) |
| Linha A / Linha B / M-series | Sequência linear de experimentos exploratórios |
| Tickets H/M/T/P/E/S em `tickets/` | Sem tickets — só READMEs por experimento |

**LLM não está no escopo do v0.6.** É assunto para um ciclo futuro,
após o algoritmo de compressão estar estabilizado e ter uma
implementação clean. Atualmente o trabalho é puramente sobre
**compressão estrutural de coleções de strings em texto**.

---

## Status do que foi arquivado

Tudo em [`_archive/`](_archive/) — `DEVELOPMENT.md`, `SCIENCE.md`,
`history.md`, `PROGRESSO-formato-v05-*`, `tickets/`, notas legadas
de `research-notes/` — são **blueprints**. Servem para:

- Localizar bugs e armadilhas já encontradas
- Resgatar ideias antigas que podem ser **rebatizadas como
  hipóteses novas** e re-testadas no dirty v0.6
- Rastreabilidade histórica via git

**Nenhuma conclusão arquivada conta como evidência viva para v0.6**.
Comprovações antigas (F-findings, ablations, M-series) voltaram a
ser **ideias a re-verificar** quando/se reaparecerem no roadmap.

Quando uma ideia arquivada precisar voltar:

1. Identificar o conceito (não a implementação) na nota antiga
2. Abrir experimento novo em `experiments/lab/dirty/` com o
   próximo ordinal NN, seguindo as convenções do dirty README
3. Re-verificar o comportamento desde zero
4. Citar a nota antiga apenas como **origem da ideia**, nunca
   como evidência

---

## Estrutura desta pasta

```
docs/workbench/
  README.md                   ← este manifesto
  research-notes/
    INDEX.md                  ← índice das notas vivas v0.6
    2026-05-11-sintese-algoritmos-v06.md
    _archive/                 ← notas dos ciclos anteriores
  _archive/                   ← docs raiz arquivados
    DEVELOPMENT.md
    SCIENCE.md
    history.md
    PROGRESSO-formato-v05-2026-05-09.md
    tickets/                  ← tickets H/M/T/P/E/S do ciclo v0.3-v0.5
```

Para entrar no trabalho atual:

1. Ler `experiments/lab/dirty/README.md`
2. Ler `docs/workbench/research-notes/2026-05-11-sintese-algoritmos-v06.md`
3. Olhar o experimento mais recente em `experiments/lab/dirty/`

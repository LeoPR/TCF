# META-THEORY-MOVE — mover hipoteses/teoria dirty → docs/theory/

**Status**: CLOSED (2026-05-17)
**Criado**: 2026-05-17
**Fechado**: 2026-05-17
**Escopo**: notas teoricas e hipoteses devem viver em `docs/theory/`
(documentacao oficial). `dirty/notas/` mantem apenas EXECUCAO
(historia, welding, decisoes fechadas).

## Resultado

11 notas movidas via `git mv` (history preservada):
- 10 → `docs/theory/`
- 1 → `docs/algorithms/output-convention.md` (spec)

Nova nota criada:
- `docs/theory/perspectiva-triplice-e-pre-tx.md` — sintese atual
  das 3 estrategias (multi-col+tipos; manager shared; slot online)
  avaliadas contra perspectiva triplice (compressao+memoria+latencia)

`docs/theory/README.md` reorganizado como index das hipoteses.
`experiments/lab/dirty/README.md` atualizado pra refletir notas/
contendo so' execucao agora.

## Classificacao

### Move (theory/hypothesis → docs/theory/)

- `roadmap-hipoteses.md` — direcoes futuras
- `comparacao-modular-camadas.md` — pre-tx layers theory
- `marcadores-multiplo-proposito.md` — composicional operators theory
- `vetores-de-comparacao-alem-de-bytes.md` — memory/latency vectors
- `quebra-de-linha-como-marcador.md` — line break marker theory
- `no-funcional-marca-e-troca.md` — slot pattern theory
- `2026-05-11-comparacoes-nao-literais.md` — non-literal compare
- `2026-05-11-custo-de-marcadores.md` — marker cost analysis
- `2026-05-11-marcadores-compactos.md` — compact markers
- `2026-05-11-tipos-com-estrutura.md` — typed structured patterns

### Move (spec → docs/algorithms/)

- `convencao-output-tcf.md` — output spec (sem brackets, LF only)

### Stay in dirty/notas/ (execution/history)

- `historia-dirty-lab.md` — narrativa M0-M14
- `welding-plan.md` — execucao welding (closed)
- `naming-compactacao-composicional.md` — registro decisao (closed)

## Create new (docs/theory/)

- `perspectiva-triplice-e-pre-tx.md` — analise critica:
  - Triple perspective (compressao/memoria/latencia)
  - Strategy 1: multi-col + tipos (pre-tx)
  - Strategy 2: shared memory + sync (novo)
  - Strategy 3: slot pattern online (delicado)

## Update

- `docs/theory/README.md` — index das hipoteses movidas + nova nota
- `experiments/lab/dirty/README.md` — se mencionar notas movidas
- Cross-references entre notas (`[[name]]` → relative paths)

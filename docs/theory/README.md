# docs/theory — Teoria + hipóteses do TCF v0.6

> **Reset 2026-05-17**: o conteudo anterior de `docs/theory/`
> (architecture, components, methodology, research-lines) descrevia
> v0.4/v0.5 e foi arquivado em `docs/archive/theory_*_v05/`. Em seu
> lugar, notas teoricas e hipoteses do v0.6 (antes em
> `experiments/lab/dirty/notas/`) foram movidas pra ca' em 2026-05-17.

## Onde esta a teoria canonica v0.6

**Algoritmos** (camadas do TCF):
- [`../algorithms/OBAT.md`](../algorithms/OBAT.md) — Online Bidirectional Affix Tokenizer (camada 1)
- [`../algorithms/HCC.md`](../algorithms/HCC.md) — Hierarchical Compositional Coding (camada 2)
- [`../algorithms/TCF-format.md`](../algorithms/TCF-format.md) — Formato + posicionamento
- [`../algorithms/output-convention.md`](../algorithms/output-convention.md) — Convencao de output

**Narrativa do desenvolvimento**:
- [`../../experiments/lab/dirty/notas/historia-dirty-lab.md`](../../experiments/lab/dirty/notas/historia-dirty-lab.md)
  — historia M0-M14 do dirty lab

## Notas teoricas + hipoteses (em ordem de relevancia)

### Sintese atual

- [perspectiva-triplice-e-pre-tx.md](perspectiva-triplice-e-pre-tx.md)
  — **ATUAL (2026-05-17)**: analise critica das 3 estrategias de
  evolucao (pre-filtro multi-col + tipos; manager com memoria
  shared; slot detection online) avaliadas contra a perspectiva
  triplice (compressao + memoria + latencia)
- [roadmap-hipoteses.md](roadmap-hipoteses.md) — 12 hipoteses futuras
  ordenadas por proximidade

### Vetores de avaliacao (alem de compressao)

- [vetores-de-comparacao-alem-de-bytes.md](vetores-de-comparacao-alem-de-bytes.md)
  — velocidade, memoria, streaming, latency vectors

### Pre-tx layers

- [comparacao-modular-camadas.md](comparacao-modular-camadas.md) —
  comparacao modular (delta / estrutural / aproximado) ortogonal ao TCF-CORE
- [2026-05-11-comparacoes-nao-literais.md](2026-05-11-comparacoes-nao-literais.md)
  — comparacoes nao-literais (precursor da Estrategia 1)
- [2026-05-11-tipos-com-estrutura.md](2026-05-11-tipos-com-estrutura.md)
  — tipos estruturados (CPF/UUID/IP) — precursor de Estrategia 1.A

### Marcadores e sintaxe

- [marcadores-multiplo-proposito.md](marcadores-multiplo-proposito.md)
  — composicional `~`/`,` (foundation do HCC)
- [2026-05-11-marcadores-compactos.md](2026-05-11-marcadores-compactos.md)
  — marcadores compactos e inferidos
- [2026-05-11-custo-de-marcadores.md](2026-05-11-custo-de-marcadores.md)
  — custo algebrico de marcadores e refs

### Slot patterns + estruturas avancadas

- [no-funcional-marca-e-troca.md](no-funcional-marca-e-troca.md)
  — template node com slot (caso D9; Estrategia 3 em formato batch)
- [quebra-de-linha-como-marcador.md](quebra-de-linha-como-marcador.md)
  — quebras como marcadores deduziveis

## Conceitos pendentes para reconectar

Identificados pelo user em 2026-05-17 (todos cobertos em
[perspectiva-triplice-e-pre-tx.md](perspectiva-triplice-e-pre-tx.md)):

1. **Multi-coluna** — TCF v0.6 atual e' single-column.
2. **Tipos de dados pre-filtro** — CPF, IP, datas calculaveis.
3. **Perspectiva triplice** — compressao + memoria + latencia.
4. **Slot pattern online** — resolve `17,??,5` em D9.

## Material historico v0.5

Anteriormente em `docs/theory/` mas v0.5-exclusivo, arquivado em:
- `../archive/theory_architecture_v05/`
- `../archive/theory_components_v05/`
- `../archive/theory_research_lines_v05/`
- `../archive/theory_methodology_v05/`

**Nao citar como evidencia viva para v0.6 sem re-validar.**

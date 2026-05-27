# TCF — Project Guide for Claude Code

> **Project-scope memory** (versionado em git). Carregado automaticamente
> a cada sessao. Complementa `~/.claude/.../memory/MEMORY.md` (user
> scope). User memoria tem preferencias pessoais; este aqui e' o que
> e' COMUM ao time.

## Projeto em 1 paragrafo

**TCF** (Tabular Compact Format) v0.6 — compressao de strings tabulares
com pipeline canonical delta-aware (M10 baseline, ADR-0011):
- **Pre-pass**: `analyze_column` (features) + `detect_cadence` (regras
  1+2, ADR-0008) + `detect_min_len` (heur v3 + gating n>=100, ADR-0010)
- **OBAT** (Online Bidirectional Affix Tokenizer) em `src/tcf/core/` +
  `src/tcf/obat_shape.py` (shape-preserve hint)
- **HCC** (Hierarchical Compositional Coding M8.A + seq-RLE) em
  `src/tcf/composicional/`

API: `from tcf import encode, decode`. Estado: pipeline canonical M10
validado em D1-D9 (1523B baseline, vs M9 antigo 1615B), 20 sint (RT
20/20), Adult+TPC-H 57 cols (ganho 11.73% real-world weighted, RT 57/57).
Multi-column basico em EXP-011.

## ONDE ESTAO AS COISAS — consulte ANTES de propor criar/baixar

### Codigo
- `src/tcf/` — **canonical (M10)**. NAO MODIFICAR sem aprovacao explicita.
  - `core/online.py` — OBAT canonical
  - `obat_shape.py` — OBAT shape-preserve hint (ADR-0011)
  - `composicional/syntax.py` — HCC M8.A
  - `composicional/hcc_seqrle.py` — HCC + seq-RLE near-identical (ADR-0011)
  - `auto_cadence.py` — detect_cadence (ADR-0008/0011)
  - `auto_min_len.py` — detect_min_len (ADR-0010, H-DA-11)
  - `column_features.py` — ColumnFeatures + analyze_column (H-DA-11c)
  - `encoder.py`, `decoder.py` — API publica (pipeline delta-aware)
- `scripts/` — ferramentas de suporte (NAO faz parte do TCF-CORE)
  - `dataset_reader.py` — **le datasets canonicos do hub SQLite**
  - `shaper/` — **sampler multidimensional** (volume, schema, join,
    order, stratify, fk_preserving)
  - `_paths.py` — resolve storage via `config/storage.json`
  - `setup_adult.py`, `setup_tpch.py` — setup canonical datasets
  - `csv_to_sqlite.py`, `derive_formats.py`, `quality_report.py`
  - `benchmark_*.py` — benchmarks varios
- `experiments/lab/dirty/` — labs exploratorios (sub-exps numerados)
- `experiments/lab/clean/EXP-NNN-*/` — prototypes consolidados

### Dados
- `datasets/synthetic/` — CSVs pequenos no repo (D1-D17)
- `datasets/canonical/` — APENAS metadata.json + README. Dados reais em Z:.
- **`Z:/tcf-data/`** — grandes arquivos (via `config/storage.json`)
  - `external/` — raw downloads (adult-census, tpch-sf001)
  - `interim/` — **SQLite hubs prontos**:
    - `Z:/tcf-data/interim/adult-census.db`
    - `Z:/tcf-data/interim/tpch-sf001.db`
  - `processed/` — derivacoes (csv, jsonl, etc.)
  - `archives/`, `benchmarks/`

### Docs
- `STATUS.md` — **ponto de entrada bibliografico**, sempre-atualizado
- `MAP.md` — wayfinding map de 1 pagina
- `docs/algorithms/` — specs canonicos (OBAT, HCC, TCF-format)
- `docs/adr/` — Architecture Decision Records numerados
- `docs/theory/` — fundamentos teoricos
- `docs/vocabulary.md` — vocabulario controlado
- `docs/findings/` — findings consolidados de pesquisa
- `experiments/lab/dirty/notas/` — narrativa + diario + roadmap
  - `roadmap-hipoteses.md` — registry cross-lab de hipoteses
  - `diario/YYYY-MM-DD.md` — decisoes diarias
  - `checkpoints/` — **pontos de pausa explicitos**
  - `futuras-otimizacoes-formato.md` — ideias de formato futuras
  - `historia-dirty-lab.md` — narrativa M0-M14
  - `welding-plan.md`, `naming-compactacao-composicional.md`

## ANTES DE AGIR — Checklist obrigatorio

### Antes de propor download / recriar infra / sintetizar dataset
1. `Glob scripts/**/*.py` — pode ja existir
2. `Glob datasets/**` — pode ja ter dataset
3. `Grep` por termos relacionados (dataset, reader, loader, fetch,
   download, sampler, shaper)
4. `Read STATUS.md` se nao leu recentemente
5. `Read MAP.md` pra layout geral
6. Checar `Z:/tcf-data/` via `Test-Path` ou `ls`

**Sintoma de falha**: propor "vou baixar X", "vou criar Y do zero"
sem ter feito as buscas acima. PARE imediatamente. Ver
[`feedback-discoverability-falha-EXP-012`](C:/Users/leona/.claude/projects/c--Users-leona-OneDrive-Documents-Projects-Acad-micos-TCF/memory/feedback_discoverability_falha_EXP_012.md)
pra contexto do incidente que motivou este guia.

### Antes de modificar labs existentes
- Se marcado `closed`, `fechado`, `obsolete` ou `superseded` — **NAO MODIFICAR**
- Abrir novo sub-experimento ao inves

### Antes de criar novo doc
- Buscar doc similar (Glob, Grep) antes
- Decidir LOCAL apropriado:
  - Stable user-facing → `docs/{tutorials,how-to,reference,explanation}/`
  - Decisao arquitetural → `docs/adr/NNNN-*.md`
  - Lab work → `experiments/lab/{dirty,clean}/...`
  - Notas continuas → `experiments/lab/dirty/notas/`
- Adicionar a `MAP.md` se for ponto de entrada novo

### Antes de declarar `confirmada-empirica` (anti-incidente 2026-05-21)

Caso motivador: Pacote 2 (escape deduction) deu 15.7% em sinteticos
D11a-h mas 0.13-1.13% em real-world — fechado `CLOSED-INSUFFICIENT-GAIN`.
Padrao: sub-exp em dataset construido pra testar a hipotese tende a
nao generalizar.

Checklist (5 perguntas obrigatorias):
1. **Real-world testado?** Adult Census / TPC-H / lineitem (nao so' D1-D17)
2. **N >= 5 datasets** de fontes diferentes (sinteticos contam separado)
3. **Sintetico vs real** mostram ganho similar OU diferenca explicada?
4. **Datasets sinteticos** explicitam que foram "construidos pra testar"
   (vies declarado)?
5. **Bytes absolutos** relevantes (>= 5% real-world weighted), nao
   so' % em dataset pequeno?

Se algum **NAO** → marcar `confirmada-empirica` com ressalva ou
`A-revalidar`. Sub-exp em real-world antes de welding/ADR.

Ver [`revisao-conceitual-2026-05-21.md`](experiments/lab/dirty/notas/revisao-conceitual-2026-05-21.md)
pra classificacao A/B/C das hipoteses existentes.

## CONVENCOES

### Naming
- Labs dirty: `YYYY-MM-DD-name/`
- Labs clean: `EXP-NNN-name/`
- Sub-exps: `NN-description/` (numerados dentro do lab)
- ADRs: `NNNN-imperative-phrase.md`
- Memorias user: `<type>_<topic>.md` (project_, feedback_, reference_, user_)
- Datasets: `D<num><suffix>-<description>.csv`

### Formato TCF
- Magic: `#TCF.<minor>` (v0.6 = `#TCF.6`). Major 0 omite "0".
- Multi-column flag: `M` no shebang. Single-col: sem flag.
- Multi-col meta: `# <size1>=<name1>,<size2>=<name2>,...`
- LF only, UTF-8

### Status markers (hipoteses)
- `aberta`, `em-exp`, `confirmada-empirica`, `confirmada-conceitual`
- `refutada`, `refutada-parcial`, `refutada-real-world`
- `absorvida`, `subsumida`, `adiada`, `welded`
- Add `[VERIFICAR: YYYY-MM-DD]` em claims mutaveis
- Add `confianca: Alta|Media|Baixa|A-revalidar` em hipoteses
  confirmada-empirica (introduzido 2026-05-21)
- Tickets podem usar `closed-insufficient-gain`, `closed-adiado`,
  `closed-parcial` no frontmatter YAML
  (ver `tickets/README.md` convencao 2026-05-21)

### Tier de memoria
- **USER scope** (`~/.claude/.../memory/`): preferencias pessoais,
  feedback de processo (cross-projeto)
- **PROJECT scope** (este arquivo + `docs/adr/`): conhecimento
  partilhado via git
- **Diario** (`experiments/lab/dirty/notas/diario/`): cronologico
- **Checkpoints**: pausas explicitas pra retomada

## NUNCA

- Modificar `src/tcf/` sem aprovacao explicita
- Baixar dados externos quando `Z:/tcf-data/` infra existe
- Push pra GitHub sem solicitacao explicita
- Commit com `Co-Authored-By:`
- Usar superlativos ("incrivel", "muito melhor", "onde brilha",
  "campeao", "vencedor", "descoberta", "surpreendente")
- `git rebase -i`, `git add -i` (interativo nao suportado)
- `git reset --hard`, `git push --force` sem aprovacao
- Mexer em servicos rodando sem confirmacao
- Push pra main exige confirmacao explicita
- Skip hooks (`--no-verify`)

## Foco atual e checkpoint

- **Foco**: ver `STATUS.md`
- **Checkpoint mais recente**:
  `experiments/lab/dirty/notas/checkpoints/2026-05-24-sessao-maxima-natures-multi-delta.md`
  (3 ADRs welded canonical 0014/0015/0016; 14 sub-exps dirty;
  benchmark consolidado TCF vence 5/6 datasets; pronto pra retomada)
- **Diario do dia ativo**: `experiments/lab/dirty/notas/diario/`

## Bibliografia bibliografica deste guia

Este sistema segue:
- **Diataxis** (Procida) — pra docs estaveis em `docs/`
- **ADR/MADR** (Nygard) — pra `docs/adr/`
- **Research Compendium** (Turing Way) — pra `experiments/`
- **FAIR4RS** — metadata em READMEs
- **Information Architecture** (Morville) — wayfinding (CLAUDE.md +
  MAP.md + cross-links)
- **Claude Code memory hierarchy** — user vs project scope
- **Threats to validity** (Wohlin 2012) — Internal/External/
  Construct/Conclusion. Aplicado em checklist "antes de declarar
  confirmada-empirica" acima.
- **Ecological validity** (Brunswik 1956) — separar datasets de
  design (realistico) de datasets de stress (artificial).

**Doc-mae cross-projeto** (sintese metodologica):
[`../README.methodology.md`](../README.methodology.md) — sintese
operacional dos pilares acima, com refs canonicos. Consulta sob
demanda via routing table do proprio doc.

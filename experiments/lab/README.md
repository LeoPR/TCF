# Lab — laboratorio de experimentacao do TCF

Local onde algoritmos e sintaxes do TCF sao iterados, validados e
comparados. **Esta pasta nao faz parte do TCF instalavel** — e'
instrumento de pesquisa.

> **Verdade canonica atual**: `dirty/notas/historia-dirty-lab.md`
> (narrativa M0-M11 do algoritmo TCF-CORE + Compactacao composicional).

## Filosofia

```
TCF (src/tcf/) = formato. Encode + Decode. API estavel.
                       ↓ produzido por
Lab (experiments/lab/) = iteracao do algoritmo + comparacao com
                          outros formatos (CSV/JSON/TOON, gzip/brotli).
                          Documenta tudo.
```

Quem instala `pip install tcf` **nao** tem este lab. E' intencional.

## Estrutura

```
experiments/lab/
├── README.md        ← este arquivo
├── dirty/           ← workbench v0.6 (algoritmo em construcao)
├── clean/           ← experimentos finalizados (EXP-NNN-tema)
├── framework/       ← infra reutilizavel (datasets, encoders, etc.)
└── archive/         ← labs de ciclos antigos (v0.4, etc.)
```

Cada sub-pasta tem seu proprio README com detalhes.

## Padroes — dirty vs clean

### `dirty/` — workbench em curso

Pasta livre. Sub-pastas por **macro experimento** (M0, M1, ..., M11)
ou por data + tema. Codigo experimental, notas vivas, sem cerimonia.

**Regra**: NAO referenciar `dirty/` em paper, artigo ou ticket
oficial. E' rascunho. Mas `dirty/notas/historia-dirty-lab.md`
mantem narrativa canonica do algoritmo.

Estado atual: ciclo v0.6 (algoritmo TCF-CORE + Compactacao
composicional). Macros M0-M11 fechados; welding para `src/` em
curso. Ver [`dirty/README.md`](dirty/README.md).

### `clean/` — experimentos finalizados

Cada experimento tem ID `EXP-NNN-tema-curto`. Estrutura fixa:
README + run.py + config + manifest + report + figures.

**Regra**: experimento clean **nao muda** depois de fechado. Re-runs
geram NOVO `EXP-NNN-v2-...`. Mantem rastreabilidade historica.

Estado atual: EXP-001..EXP-006 sao de ciclo v0.5 (LLM benchmark —
acessorio). EXP-007 sera o primeiro do v0.6 (proto-tipo do
algoritmo welded de `src/`). Ver [`clean/README.md`](clean/README.md).

### `framework/` — infra reutilizavel

Helpers compartilhados (datasets loaders, encoders adapters,
compressors wrappers, metrics). Usados pelos experimentos clean.
Ver [`framework/README.md`](framework/README.md).

### `archive/` — labs de ciclos antigos

Labs do ciclo v0.4 (e anteriores). Material historico. Ver
[`archive/README.md`](archive/README.md).

## Promocao dirty → clean

Quando um experimento sujo gera resultado interessante:

1. Copiar codigo relevante para `clean/EXP-NNN-tema/`
2. Limpar/refatorar `run.py`
3. Re-rodar para gerar `manifest.jsonl` em estado limpo
4. Escrever `report.md` interpretando
5. Fechar com tag git (opcional): `git tag exp-NNN`

Atualmente: **welding do algoritmo do dirty (M0 + M8.A em M11) para
`src/tcf/`** — primeira saida do dirty pro src/clean depois do ciclo
v0.6 maduro. Pre-EXP-007. Ver
[`dirty/notas/welding-plan.md`](dirty/notas/welding-plan.md).

## Estado atual

**Algoritmo (v0.6)**: M11 welding step 1 fechado em 2026-05-17.
alg16 copiado para `src/tcf/core/online.py`; M8.A composicional
ainda no dirty. Welding step 2 (M8.A → `src/tcf/composicional/`)
pendente.

**Resultados bytes (D1-D9 canonicos)**:
- M1.E baseline: 660 bytes
- M8.A composicional: 574 bytes (-13% vs M1.E)
- Ratio medio em stress D1-D9: 54.3% raw

**Experimentos clean v0.5**: EXP-001..EXP-006 sao do ciclo antigo
(LLM benchmark). Validos como historico; nao referenciar para v0.6.

## Como rodar

```bash
# Macros dirty (atuais)
python experiments/lab/dirty/old/2026-05-17-M11-welding-step1-alg16-src/run_lote.py

# Experimentos clean (v0.5)
python experiments/lab/clean/EXP-001-csv-baseline/run.py
```

## Notas

- Para narrativa do algoritmo, sempre comecar por
  [`dirty/notas/historia-dirty-lab.md`](dirty/notas/historia-dirty-lab.md).
- Para direcoes futuras:
  [`dirty/notas/roadmap-hipoteses.md`](dirty/notas/roadmap-hipoteses.md).
- Para entender o "welding" (saida do dirty pro src/):
  [`dirty/notas/welding-plan.md`](dirty/notas/welding-plan.md).
- Phase 1 (LLM benchmark, ciclo v0.5) e' acessorio ao foco atual —
  pode virar projeto a parte.

# Lab — laboratorio de experimentacao do TCF

Local onde o TCF e **comparado cientificamente** com outros formatos
(CSV, JSON, TOON) em diversos cenarios. **Esta pasta nao faz parte
do TCF** — e instrumento de pesquisa.

## Filosofia

```
TCF (packages/tcf/) = formato. Como CSV. Encode + Decode. Apenas.
                            ↓ usado por
Lab (experiments/lab/) = experimentos cientificos.
                          Compara TCF com CSV/JSON/TOON
                          Mede com gzip/brotli
                          Simula transport/network
                          Documenta tudo
```

Quem instala `pip install tcf` **nao** tem este lab. E intencional.

## Estrutura

```
experiments/lab/
├── README.md                          ← este arquivo
├── framework/                         ← infra reutilizavel
│   ├── datasets.py                    ← carregadores (MICRO/Adult/TPCH/sinteticos)
│   ├── encoders.py                    ← adapters (CSV/JSON/TCF/TOON)
│   ├── compressors.py                 ← wrappers (gzip/brotli/zstd)
│   ├── pipeline.py                    ← simulate(rows, encoder, compress, transport)
│   └── metrics.py                     ← bytes/timing/roundtrip
│
├── dirty/                             ← workbench sujo (work-in-progress)
│   └── README.md                      ← regras desta pasta
│
└── clean/                             ← experimentos finalizados (publicaveis)
    ├── EXP-001-csv-baseline/
    │   ├── README.md                  ← descricao do experimento
    │   ├── run.py                     ← codigo reproduzivel
    │   ├── config.json                ← parametros usados
    │   ├── manifest.jsonl             ← cada execucao 1 linha
    │   ├── report.md                  ← analise dos resultados
    │   └── figures/                   ← graficos (se aplicavel)
    └── EXP-002-tcf-baseline/
        └── ... (mesma estrutura)
```

## Padroes — dirty vs clean

### `dirty/` — experimentos sujos

Pasta livre. Sub-pasta por data + tema (`2026-04-27-bench-rle/`),
sem cerimonia. Notas em qualquer formato. Codigo experimental.
Pode ser deletado a qualquer momento.

**Regra**: nao referenciar `dirty/` em paper, em ticket, em finding.
E rascunho.

### `clean/` — experimentos limpos

Cada experimento tem ID `EXP-NNN-tema-curto`. Estrutura fixa:

| Arquivo | Funcao |
|---------|--------|
| `README.md` | Pergunta cientifica + hipotese + metodo + resultado em 1-2 paginas |
| `run.py` | Reproduzivel: `python experiments/lab/clean/EXP-NNN.../run.py` |
| `config.json` | Parametros do experimento (datasets, encoders, etc.) |
| `manifest.jsonl` | 1 linha JSON por execucao |
| `report.md` | Analise estatistica + tabelas + interpretacao |
| `figures/*.png` | Graficos (matplotlib/plotly) |

**Regra**: experimento clean **nao muda** depois de fechado. Re-runs
geram NOVO `EXP-NNN-v2-tema/`. Mantem rastreabilidade historica.

## Promocao dirty → clean

Quando um experimento sujo gera resultado interessante:

1. Copiar codigo relevante para `clean/EXP-NNN-tema/`
2. Limpar/refatorar `run.py`
3. Re-rodar para gerar `manifest.jsonl` em estado limpo
4. Escrever `report.md` interpretando
5. Fechar com tag git (opcional): `git tag exp-NNN`

## Encode paralelo (decisao 2026-04-27)

TCF encoder pode (e sera) feito de forma paralela alem de serial.
Cenarios:

- **Multi-table paralelo**: `encode_dataset(tables)` faz cada tabela em
  process/thread separado
- **Multi-column paralelo**: dentro de uma tabela, cada coluna e
  encoded independentemente — paralelo eh natural

O lab valida tanto modo serial quanto paralelo, comparando overhead
vs ganho.

## Como rodar tudo

```bash
# Listar experimentos disponiveis
python experiments/lab/list.py

# Rodar um especifico
python experiments/lab/clean/EXP-001-csv-baseline/run.py

# Rodar todos os clean
python experiments/lab/run_all.py
```

## Ordem cronologica de experimentos

| ID | Tema | Status |
|----|------|--------|
| EXP-001 | CSV baseline (encode/decode/timing/bytes) | em curso |
| EXP-002 | TCF baseline (mesmas metricas para comparar) | proximo |
| EXP-003 | TCF L0/L1/L2/L3 comparados | depois |
| EXP-004 | + gzip transport | depois |
| EXP-005 | + brotli transport | depois |
| EXP-006 | TCF vs CSV vs JSON em datasets variados | depois |
| EXP-007 | encode paralelo (multi-thread) | depois |
| EXP-008 | TOON integration (se biblioteca disponivel) | depois |

## Notas

- O lab nao bloqueia o desenvolvimento do TCF v0.4. Lab valida o que
  v0.4 produz.
- Cada experimento gera dados que entram em `docs/findings/` como
  evidencia.
- O paper consome resultados do `clean/`, nunca do `dirty/`.

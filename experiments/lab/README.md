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
│   └── README.md                      ← regras + mapa cronologico de labs
│
├── clean/                             ← experimentos finalizados (publicaveis)
│   └── EXP-NNN-tema/                  ← 1 por experimento
│       ├── README.md  run.py  config.json  manifest.jsonl
│       ├── report.md  figures/
│
└── archive/                           ← labs antigos arquivados
    └── 2026-05-design-v04-fase1/      ← labs da fase de design v0.4
```

## Padroes — dirty vs clean

### `dirty/` — experimentos sujos

Pasta livre. Sub-pasta por data + tema (`2026-05-23-escala/`),
sem cerimonia. Notas em qualquer formato. Codigo experimental.
Pode ser deletado a qualquer momento.

**Regra**: nao referenciar `dirty/` em paper, em ticket, em finding.
Eh rascunho. Mas o `dirty/README.md` mantem rastreio cronologico
para navegar a historia da exploracao.

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

### `archive/` — labs arquivados

Labs antigos cujos achados ja foram consolidados em research-notes
ou tickets. Mantidos para historico. Cada subpasta tem seu proprio
README descrevendo o tema e referencias para os documentos
consolidados.

## Promocao dirty → clean

Quando um experimento sujo gera resultado interessante:

1. Copiar codigo relevante para `clean/EXP-NNN-tema/`
2. Limpar/refatorar `run.py`
3. Re-rodar para gerar `manifest.jsonl` em estado limpo
4. Escrever `report.md` interpretando
5. Fechar com tag git (opcional): `git tag exp-NNN`

---

## Estado atual dos experimentos clean

| ID | Tema | Status |
|----|------|--------|
| EXP-001 | CSV baseline (encode/decode/timing/bytes) | aberto |
| EXP-002 | TCF baseline (vs CSV de EXP-001) | aberto |
| EXP-003a | Calibracao CSV + compressor generico | aberto |
| EXP-003b | TCF vs gzip (HP-T1) | aberto |
| EXP-004b | Sintaxe compacta no header (variante B) | aberto |
| EXP-004c | Header shebang `#TCF.5 SRDM` | aberto |
| EXP-005 | Progressao de formatos em datasets escalonados | aberto |
| EXP-006 | Flag P (Affix-DICT) em identificadores | aberto |
| EXP-007 | (proximo) — encoder canonico do dirty (lab 24) | a criar |

**Bloqueador comum**: o **harness de teste**
([T-test-harness-mvp](../../docs/workbench/tickets/open/T-test-harness-mvp.md))
ainda nao esta implementado. Os EXPs acima rodam isolados; integrar
no harness eh proximo passo.

## Estado atual da exploracao dirty

A pasta `dirty/` contem 26 sub-experimentos em **3 fases** entre
2026-05-07 e 2026-05-10. Ver [dirty/README.md](dirty/README.md)
para o mapa completo.

**Achado central** (consolidado em research-notes):
- Algoritmo unificado: PATRICIA bidir + multi-afixo + ext-aware gain
- 7/7 RT OK em escala (N=100 a 1000)
- Avg -54.56% vs literal; E7 URLs -82%
- TCF+gzip vence literal+gzip em escala (-8% vs -8.47% labs anteriores)

**Status de fechamento dirty**: recomendado fechar apos lab 24
(2026-05-10). Proximo: portar para `clean/EXP-007-...` com header
`#TCF.5 SRDM` e harness formal.

---

## Encode paralelo (decisao 2026-04-27)

TCF encoder pode (e sera) feito de forma paralela alem de serial.
Cenarios:

- **Multi-table paralelo**: `encode_dataset(tables)` faz cada tabela em
  process/thread separado
- **Multi-column paralelo**: dentro de uma tabela, cada coluna e
  encoded independentemente — paralelo eh natural

O lab valida tanto modo serial quanto paralelo, comparando overhead
vs ganho.

## Como rodar

```bash
# Rodar um experimento clean especifico
python experiments/lab/clean/EXP-001-csv-baseline/run.py

# Rodar um lab dirty
python experiments/lab/dirty/2026-05-24-fechamento-multi-afixo-escala/run.py
```

## Notas

- O lab nao bloqueia o desenvolvimento do TCF v0.5. Lab valida o
  que v0.5 produz.
- Cada experimento gera dados que entram em `docs/findings/` como
  evidencia.
- O paper consome resultados do `clean/`, nunca do `dirty/`.

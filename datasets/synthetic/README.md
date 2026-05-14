# datasets/synthetic — Controle sintético (D1-D9)

> **Status (2026-05-17)**: datasets de controle do algoritmo TCF-CORE.
> Elevados do dirty lab para localizacao canonica oficial. Validar
> via macro M10 antes de remover duplicatas em macros M4-M9.

## Proposito

Conjunto de **datasets sinteticos pequenos** projetados para
verificar comportamento do algoritmo TCF-CORE + Compactacao
composicional em cenarios variados. Complementa os datasets reais
em `datasets/canonical/` (Adult Census, TPC-H).

Cada arquivo e' um cenario distinto. Single-column CSV com header
`val` e ~12-20 linhas. Total raw: 2973 bytes em 9 arquivos.

## Cenarios

| Arquivo | Cenario | Linhas | Raw bytes | Caracteristica |
|---|---|---:|---:|---|
| D1-emails-simples.csv | Emails 3 dominios | 12 | 191 | Padrao classico (gmail/hotmail/yahoo) |
| D2-emails-quote-id.csv | Emails + apostrofes | 12 | 248 | Nomes com `'` (d'angelo, o'brien) |
| D3-stress-substring.csv | URLs `api/users/...` | 12 | 348 | Stress para detector subseq |
| D4-caos-mix.csv | Mix `[X]*'YYY'@4Z` | 12 | 157 | Alto caos, baixa redundancia |
| D5-padroes-multiplos.csv | email + UUID coexistentes | 12 | 419 | Multi-padrao paralelo |
| D6-poucos-em-ruido.csv | Log com timestamps unicos | 12 | 528 | Estresse para pre-tx delta |
| D7-aninhamento.csv | `[start][a][middle][a][end]` | 12 | 335 | Padrao em multiplas positions |
| D8-cabeca-cauda.csv | `prefix/X/suffix` (X varia) | 12 | 384 | Cenario ideal (prefix/suffix estaveis) |
| D9-frequencia-alta.csv | `@@@KEY=valueX@@@` (X varia) | 20 | 363 | Wrapper com slot variavel |

## Compressao validada (M9 baseline)

M8.A composicional total: **1615 bytes em 2973 raw = 54.3% ratio**.
Varia 26% (D8 melhor) a 72% (D4 caos). Ver
[`../../experiments/lab/dirty/2026-05-17-M9-stress-adversarial/`](../../experiments/lab/dirty/2026-05-17-M9-stress-adversarial/).

## Uso

Macros futuros (M10+) e EXP-NNN no `experiments/lab/clean/`
referenciam diretamente estes arquivos. Macros M4-M9 (closed) mantem
snapshots locais em `data/` por reprodutibilidade.

```python
DATASETS_DIR = Path(__file__).resolve().parents[N] / "datasets" / "synthetic"
```

## Direcoes futuras

User mencionou (2026-05-17): "D1-D9 variados" — expandir com
variantes (D1a, D1b, ...) para stress incremental. Nao urgente.

## Conexoes

- Originadas em `experiments/lab/dirty/2026-05-17-M9-stress-adversarial/data/`
- Validadas por M9 + (planejado) M10
- Para datasets canonicos reais ver `../canonical/`

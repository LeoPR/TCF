# Como usar a estrutura controlada do macro M1

## Estrutura

```
M1/
  online.py                      raiz: tokens do exp 16 (intocado)
  syntax_base.py                 interface Syntax(ABC)
  
  data/
    D1-emails-simples.csv
    D2-emails-quote-id.csv
    D3-stress-substring.csv
    D4-caos-mix.csv
  
  M1-A-escape/syntax.py          micro 1
  M1-A-escape-escopo/syntax.py   micro 2
  M1-B-quote/syntax.py           micro 3
  
  run_lote.py                    script unificado
  
  resultados/
    tokens/                      tokens raiz (1 arquivo por dataset)
    <sintaxe>/
      <dataset>.tcf              encode
      <dataset>.decoded.csv      decode (contra-prova)
      <dataset>.debug.txt        input + tokens + encode + decode
    matriz_comparativa.md
    matriz_bytes.csv
```

## Como rodar

```bash
cd 2026-05-12-M1-marcacao-ambiguidade
python run_lote.py
```

Roda todas as sintaxes em todos os datasets. Gera todos os outputs.

## Como adicionar uma nova sintaxe

### 1. Criar pasta

```
M1/M1-X-minha-sintaxe/
  syntax.py
  README.md     (opcional, explicacao)
```

### 2. Implementar `syntax.py`

Template minimo:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from online import Token, TokLit, TokRefPref, TokRefSuf
from syntax_base import Syntax


class M1XMinhaSyntax(Syntax):
    name = "M1-X-minha"

    def encode(self, linhas_originais, strings_unicas,
                tokens_por_string, header) -> str:
        ...
        return tcf_text

    def decode(self, tcf_text) -> list[str]:
        ...
        return linhas
```

A classe **deve** herdar de `Syntax` e ter atributo `name`.
O `run_lote.py` descobre automaticamente.

### 3. Registrar no `run_lote.py`

Editar a constante:

```python
SINTAXES_REGISTRADAS = [
    "M1-A-escape",
    "M1-A-escape-escopo",
    "M1-B-quote",
    "M1-X-minha-sintaxe",   # nova
]
```

### 4. Rodar

```bash
python run_lote.py
```

Outputs novos aparecem automaticamente em `resultados/M1-X-minha/`.

## Como adicionar um novo dataset

### 1. Criar CSV

```
data/D5-meu-dataset.csv
```

Formato:

```
header
linha1
linha2
...
```

### 2. Registrar no `run_lote.py`

```python
DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
    "D5-meu-dataset",   # novo
]
```

### 3. Rodar

```bash
python run_lote.py
```

Roda todas as sintaxes registradas no novo dataset.

## O que cada output contem

### `resultados/tokens/<dataset>.txt`

Tokens raiz do algoritmo do exp 16. **Compartilhado** entre
sintaxes — todas usam os mesmos tokens. Saida:

```
eid=1: 'string'
  tokens: [L('text'), P(j,k), S(j,k)]
  fragmentos literais: [a:b]='X' | [b:c]='Y' | ...
```

### `resultados/<sintaxe>/<dataset>.tcf`

Output bruto do `encode()` da sintaxe. Texto TCF.

### `resultados/<sintaxe>/<dataset>.decoded.csv`

Output do `decode(tcf)` salvo como CSV. **Contra-prova** —
deve ser identico ao input.

### `resultados/<sintaxe>/<dataset>.debug.txt`

Relatorio detalhado com:
- input (linhas originais)
- tokens (raiz)
- fragmentos
- TCF (encode)
- decode com marca `[ ]`/`[X]` por linha

### `resultados/matriz_comparativa.md`

Tabela markdown com bytes por (sintaxe x dataset), vencedor,
diferenca min-max, e totais.

### `resultados/matriz_bytes.csv`

Dados crus em CSV para analise externa.

## Resultados atuais (4 sintaxes em 4 datasets)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | vencedor |
|---|---:|---:|---:|---:|---|
| D1-emails-simples | 162 | 162 | 162 | **149** | M1-E-range |
| D2-emails-quote-id | 200 | 197 | 198 | **180** | M1-E-range |
| D3-stress-substring | 242 | 233 | 233 | **206** | M1-E-range |
| D4-caos-mix | 152 | 152 | 160 | **141** | M1-E-range |
| **TOTAL** | 756 | 744 | 753 | **676** | **M1-E-range** |

M1.E menor em todos os 4 datasets (range `a..b` para K>=3 sequencial,
combinado com escape escopo de M1.A' para literais).

## Proximas combinacoes sugeridas

Manter esta estrutura. Adicionar progressivamente:

- **M1.C (sumida)**: parser stateful — omite quando idx N nao existe.
- **M1.D (slice arbitrario)**: extende algoritmo (nao so' sintaxe).
- **M1.B' (quote agrupada)**: aspas com separador interno: `'X*Y*Z'`
  em vez de `'X''Y''Z'`. Datasets atuais nao disparam essa condicao
  — candidata pra dataset enviesado.

Cada uma sera adicionada com novo `M1-X-nome/syntax.py` e entry no
`SINTAXES_REGISTRADAS`. **Sem mexer nas existentes.**

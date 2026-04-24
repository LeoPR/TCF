# TCF — Textual Columnar Format

![Python](https://img.shields.io/badge/python-3.10+-blue)
![Tests](https://img.shields.io/badge/tests-112%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.2.0-orange)

Formato de serializacao textual **orientado a colunas** com compressao RLE,
desenhado como veiculo de raciocinio estruturado entre dados tabulares e LLMs.

---

## Parte 1 — O formato

TCF codifica tabelas relacionais em texto ASCII columnar com compressao textual.
Schema (tipos, FK, stats) fica no topo; valores de cada coluna sao agrupados;
sequencias iguais sao codificadas como `N*val`.

```
# TCF v0.2 level=2
## vendas n=509 sorted_by=pessoa
# STATS total: n=509 sum=147445.47 min=9.01 max=759.8 avg=289.68
pessoa:
8*Ana
12*Bruno
15*Carla
...
produto:
Caneta
3*Lapis
Borracha
...
total:
2.5
11.0
1.0
...
```

Quatro niveis de compressao, todos reversiveis byte-a-byte:

| Nivel | Tecnica | Uso recomendado |
|-------|---------|-----------------|
| L0 | Expanded (1 valor por linha) | Maxima legibilidade para LLM |
| L1 | RLE em runs naturais | Quando ordem precisa ser preservada |
| L2 | Sort + RLE | Default — melhor tradeoff |
| L3 | Dict + Sort + RLE | Transporte e storage |

### Compressao comparada — 500 linhas, 3 tabelas

Tamanho em bytes (raw = texto puro; gzip = apos compressao adicional):

| Formato | Raw bytes | vs CSV raw | Gzip bytes | vs CSV gzip |
|---------|----------:|-----------:|-----------:|------------:|
| CSV | 50 314 | 1.00× (baseline) | 12 681 | 1.00× |
| JSONL | 144 591 | **2.87× maior** | 14 756 | 1.16× maior |
| **TCF L0** | 50 525 | 1.00× | 11 110 | **0.88×** (12% menor) |
| **TCF L2** | 45 109 | **0.90×** (10% menor) | 11 422 | **0.90×** |
| **TCF L3** | 28 173 | **0.56×** (44% menor) | 10 440 | **0.82×** |

### A mesma comparacao em 5000 linhas

| Formato | Raw bytes | Gzip bytes | Gzip vs CSV |
|---------|----------:|-----------:|------------:|
| CSV | 544 729 | 125 948 | 1.00× |
| JSONL | 1 495 678 | 151 577 | 1.20× maior |
| TCF L0 | 544 738 | 96 643 | **0.77×** |
| TCF L2 | 485 615 | 100 963 | 0.80× |
| **TCF L3** | **264 511** (51% menor) | **89 472** | **0.71×** (29% menor) |

TCF L3 ganha da CSV mesmo pos-gzip porque a compressao interna ja removeu
redundancia que o gzip nao capturaria do texto linha-a-linha.

---

## Parte 2 — Geracao de SQL via schema

Com TCF como *schema carrier* (nao dos dados completos), um LLM gera SQL que
e executado em SQLite. O formato entrega o schema enxuto com cardinalidades,
FKs e 3 exemplos por coluna. Em 3 dominios, 3 modelos e 10+ tipos de query,
acuracia media foi de **86-100%** (vs ~40% em leitura direta).

### Micro-exemplo — pergunta simples

**Schema TCF (trecho):**
```
## vendas n=509
# STATS total: sum=147445.47 avg=289.68
id_cliente: int [FK -> clientes.id]
id_produto: int [FK -> produtos.id]
total: float
```

**Pergunta:** "Qual e a soma de todos os valores da coluna total em vendas?"

**SQL gerado:**
```sql
SELECT SUM(total) FROM vendas
```

### Micro-exemplo — pergunta complexa (L3)

**Pergunta:** "Quantos clientes distintos têm soma de total acima da media
das somas por cliente?"

**SQL gerado (phi4:latest, dominio financial, 100% em M7):**
```sql
WITH soma_por_titular AS (
    SELECT c.titular, SUM(t.valor) AS soma_valor
    FROM contas c
    JOIN transacoes t ON c.id = t.id_conta
    GROUP BY c.titular
)
SELECT COUNT(DISTINCT titular)
FROM soma_por_titular
WHERE soma_valor > (SELECT AVG(soma_valor) FROM soma_por_titular);
```

### Micro-exemplo — decomposicao em duas etapas

**Pergunta:** "Para o cliente com mais registros, qual a categoria mais
frequente de transacao?"

**SQL gerado (phi4:latest, dominio financial):**
```sql
WITH por_titular AS (
    SELECT c.titular, COUNT(*) AS num_transacoes
    FROM contas c
    JOIN transacoes t ON c.id = t.id_conta
    GROUP BY c.titular
),
titular_mais_registros AS (
    SELECT titular FROM por_titular
    ORDER BY num_transacoes DESC LIMIT 1
)
SELECT cat.nome
FROM transacoes t
JOIN contas c ON t.id_conta = c.id
JOIN categorias cat ON t.id_categoria = cat.id
WHERE c.titular IN (SELECT titular FROM titular_mais_registros)
GROUP BY cat.nome
ORDER BY COUNT(*) DESC LIMIT 1;
```

### Modelos avaliados — 3 dominios, N=744 combos

| Modelo | Accuracy global | Latencia media | Perfil |
|--------|----------------:|---------------:|--------|
| **qwen3:14b** | **85.8%** | ~6.4 s | Melhor balance accuracy+velocidade |
| phi4:latest | 84.5% | ~13.7 s | Lidera em q_lookup; gera CTEs elaboradas |
| qwen2.5-coder:7b | 82.0% | ~4.0 s | Mais rapido; fraco em subqueries L3 |

Detalhes por nivel de complexidade SQL em
[docs/methodology/model-ranking.md](docs/methodology/model-ranking.md).

### Taxa de sucesso por complexidade

| Nivel SQL | Tipo | Accuracy |
|-----------|------|---------:|
| L1 | COUNT, SUM, AVG, simple JOIN | ~95% |
| L2 | WHERE, GROUP BY, HAVING (com fewshot) | ~96% |
| L3 | CTE, subquery aninhada, COUNT DISTINCT | 86% |

---

## Parte 3 — Uso e integracao

### Instalacao

```bash
pip install -e .
```

Zero dependencias externas no core (stdlib only).

### CLI

```bash
# CSV -> TCF em 4 niveis
python -m tcf encode --meta data/metadata.json --data-dir data/ --level 2 --out output.tcf

# TCF -> CSV (auto-detecta nivel)
python -m tcf decode output.tcf --out-dir restored/

# Metadados de um TCF
python -m tcf info output.tcf
```

### API Python

```python
from tcf import encode, decode, EncodeConfig

config = EncodeConfig(
    level=2,              # 0=expanded, 1=rle, 2=sort+rle, 3=dict+sort+rle
    include_stats=True,   # STATS hints (recomendado para LLMs)
    precision=None,       # None = auto
)
tcf_text = encode("data/metadata.json", "data/", config=config)

# Decode com normalizacao de tipos
tables = decode(tcf_text, normalize=True)
```

### Integracao com LLM (exemplo minimo)

```python
from tcf import encode, EncodeConfig
import requests  # Ollama client

tcf_text = encode(meta_path, data_dir, EncodeConfig(level=2))

prompt = f"""Gere UMA query SQLite que responda a pergunta.
Responda apenas com o SQL em bloco ```sql ... ```.

{tcf_text}

Pergunta: Quantos clientes distintos têm mais de 5 compras?
"""

response = requests.post("http://localhost:11434/api/generate",
                         json={"model": "qwen3:14b", "prompt": prompt}).json()
# Executar response['response'] no seu SQLite
```

### Bibliografia e referencias

- **[docs/components/README.md](docs/components/README.md)** — 3 componentes do projeto (Core + LLM Interface + DB Extractor)
- **[docs/FINDINGS_SUMMARY.md](docs/FINDINGS_SUMMARY.md)** — achados principais A0-A7
- **[docs/methodology/F-findings.md](docs/methodology/F-findings.md)** — catalogo canonico F-Q1..F-Q23
- **[docs/methodology/model-ranking.md](docs/methodology/model-ranking.md)** — ranking dos 3 modelos locais
- **[docs/article/](docs/article/)** — artigo cientifico em capitulos
- **[docs/research-notes/INDEX.md](docs/research-notes/INDEX.md)** — diario de pesquisa datado
- **[tickets/README.md](tickets/README.md)** — roadmap operacional

### Testes

```bash
python -m pytest tests/ -v    # 112 testes, ~15s
```

Cobrem: roundtrip todos os niveis, 12 cenarios sinteticos, benchmark
compressao, infra (metrics, GT, parsers).

---

## Ambiente de desenvolvimento

Experimentos foram conduzidos em:

- **Hardware:** CPU multi-core x86_64, GPU com VRAM suficiente para modelos 14B (~9 GB)
- **Runtime LLM:** Ollama em Docker (localhost:11434)
- **Modelos testados:** qwen3:14b, phi4:latest, qwen2.5-coder:7b (+ 9 descartados na qualificacao)
- **Python:** 3.10+
- **OS:** Windows 10 Pro (replicado em Linux)

Metodologia de timing e limitacoes de benchmark em
[docs/research-notes/2026-04-22-timing-measurement-methodology.md](docs/research-notes/2026-04-22-timing-measurement-methodology.md).

---

## Resumo de performance e recomendacoes de uso

| Cenario | Recomendacao |
|---------|--------------|
| Transporte textual de tabelas grandes | **TCF L3** — 44-51% menor que CSV raw; 29% menor apos gzip em 5000 linhas |
| Dados para LLM com contexto limitado | **TCF L2 + STATS** — bom tradeoff legibilidade/compressao |
| Text-to-SQL production | **TCF schema-only + fewshot** — 96%+ accuracy em queries L1-L2 |
| Queries L3 (CTE, subquery) | qwen3:14b com M7 fewshot — 86% accuracy global |
| Queries com HAVING | Aplicar style hint `safe-sql-having` — recupera 15% para 85% |
| Screening rapido (muitos combos) | qwen2.5-coder:7b — ~4s/query para L1-L2 |
| Latencia minima com 14B | qwen3:14b ~6.4s/query; phi4 ~13.7s |

**Nao misture style hints** — combinacoes tendem a degradar (F-Q23);
selecao **per-question-type** e mais robusta que "turn everything on".

---

## Contribuindo

1. Fork o repositorio
2. Criar branch (`git checkout -b feature/minha-feature`)
3. Rodar testes (`python -m pytest tests/ -v`) — todos devem passar
4. Commit com mensagem descritiva
5. Abrir Pull Request

---

## License

MIT License. Livre para uso, modificacao e distribuicao, desde que mantendo
o aviso de copyright. Ver [LICENSE](LICENSE).

---

## Citacao

Se este projeto for util para seu trabalho, considere citar:

```bibtex
@software{souza2026tcf,
  author = {Souza, Leonardo Marques},
  title = {TCF: Textual Columnar Format for LLM Reasoning over Tabular Data},
  year = {2026},
  url = {https://github.com/<usuario>/tcf}
}
```

(URL sera atualizada apos publicacao do repo)

## Autor

Leonardo Marques Souza — 2026

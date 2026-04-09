# 3. TCF: Textual Columnar Format

## 3.1 Design e Motivacao

TCF e um formato de serializacao textual **orientado a colunas**, construido como
sublinguagem de Markdown. A escolha de Markdown como base se justifica pela
**familiaridade** — LLMs foram treinados em bilhoes de documentos Markdown
(READMEs, wikis, documentacao tecnica). Headers `##`, listas e notacao inline
sao padroes que modelos ja "sabem ler".

A compactacao usa tecnicas inspiradas em bancos de dados colunares:
- **Orientacao columnar:** todos os valores de um campo em uma unica linha
- **RLE (Run-Length Encoding):** repeticoes compactadas como `N:val`
- **Colunas sorted:** versao ordenada para revelar distribuicao
- **Modos FK:** diferentes formas de representar relacoes entre tabelas

## 3.2 Sintaxe

### Header global
```
# TCF v0.1
> N:val = val repeated N times consecutively. No prefix = single occurrence.
> Columns marked [sorted] are sorted.
> Columns marked [key] are primary keys.
```

### Bloco de tabela
```
## nome_tabela n=N
coluna[key]: val1 val2 val3 ...
coluna: val1 val2 val3 ...
coluna[sorted]: N1:val1 N2:val2 ...
```

### Notacao RLE
```
id_loja[sorted]: 7:1 3:2
```
Equivale a: `1 1 1 1 1 1 1 2 2 2` (10 valores em 2 tokens)

### Stats opcionais
```
# STATS vl n=41 sum=217.6 min=1 max=12.4 avg=5.306
# STATS nome n=30 distinct=30 mode=Ana(1)
```

## 3.3 Variantes de Encoding

### Numeric encoding

| Variante | Descricao | Exemplo | Reversivel |
|----------|-----------|---------|------------|
| `raw_float` | Floats compactos | `2.5 11 1 3.75` | Sim (lossless) |
| `int_scaled` | Multiplicar por scale, emitir inteiro | `250 1100 100 375` (scale=100) | Sim (lossless) |
| `bins_16` | Quantizar em N bins uniformes | `3 15 0 5` (indices de bin) | Nao (lossy) |

### FK representation

| Modo | Descricao | Exemplo |
|------|-----------|---------|
| `id_raw` | ID numerico original | `id_pessoa: 1 2 1 3` |
| `dict` | Bloco DICT antes da tabela | `## DICT pessoas: 1=Ana 2=Bruno` |
| `hint` | Comentario apos a coluna FK | `> id_pessoa: 1=Ana, 2=Bruno` |
| `inline` | Nomes resolvidos (JOIN) | `pessoa: Ana Bruno Ana Carla` |

### Sort mode

| Modo | Descricao | Overhead |
|------|-----------|----------|
| `sorted=True` | Emite coluna[sorted] com RLE | +5-15% (beneficio com repeticao) |
| `sorted=False` | Omite colunas sorted | Baseline |

### Supertable mode (planejado)

JOIN de todas as tabelas em uma unica supertabela desnormalizada.
IDs eliminados, nomes resolvidos, RLE sobre nomes repetidos.

```
## compras n=41 (from: pessoas=pessoa, produtos=produto)
pessoa: Ana Bruno Ana Carla ...
produto: Caneta Caderno Lapiz Caneta ...
vl: 2.5 11 1 3.75 ...
pessoa[sorted]: Alice 3:Ana Bianca 2:Bruno ...
produto[sorted]: 3:Apontador 4:Borracha 5:Caneta ...
```

## 3.4 Complexidade e Compressao

### Compressao teorica

Para uma coluna com N valores e K valores distintos:
- **CSV/JSONL:** O(N) tokens
- **TCF raw:** O(N) tokens (mesma cardinalidade)
- **TCF sorted+RLE:** O(K) tokens (compressao N/K)

RLE e eficiente quando K << N (muita repeticao):
- 1000 vendas, 30 clientes → pessoa[sorted]: O(30) vs O(1000) = **33x**
- 1000 vendas, 12 produtos → produto[sorted]: O(12) vs O(1000) = **83x**
- Dados unicos (K=N) → RLE nao ajuda (ratio 1.0x)

### Overhead do header

TCF tem overhead fixo por tabela (~200-300 bytes de header).
Isso faz TCF ser **maior que CSV** para tabelas pequenas (<200 linhas).
A partir de ~1000 linhas, o header e amortizado e TCF e ~3% menor que CSV.

### TCF vs JSONL

TCF e **sempre** menor que JSONL (17-83% menor em todos os cenarios testados).
JSONL repete nomes de campo em cada linha — overhead proporcional a N*K.
TCF emite nomes de campo uma vez — overhead fixo O(K).

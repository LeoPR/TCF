# 3. TCF: Textual Columnar Format

## 3.1 Design e Motivacao

TCF e um formato de serializacao textual **orientado a colunas**, construido como
sublinguagem de Markdown. LLMs foram treinadas em bilhoes de documentos Markdown
— headers `##`, listas e blocos de codigo sao padroes familiares.

A compactacao usa tecnicas de bancos colunares adaptadas para legibilidade textual:
- **Orientacao columnar:** todos os valores de uma coluna agrupados
- **RLE (Run-Length Encoding):** repeticoes consecutivas compactadas
- **Ordenacao por melhor coluna:** maximiza runs consecutivos para RLE
- **Dictionary encoding:** strings longas substituidas por indices curtos

## 3.2 Sintaxe v0.2

### Header
```
# TCF v0.2 level=2
# N*val = val repeated N times
```

### Bloco de tabela
```
## vendas n=41 sorted_by=produto
```

### Coluna de dados
```
pessoa:
3*Ana
2*Bruno
Carla
```
Cada valor (ou grupo RLE) em sua propria linha. `3*Ana` = Ana repetido 3 vezes.

### Stats (opcional)
```
# STATS total: n=41 sum=217.6 min=1 max=12.4 avg=5.31
```
Hints pre-computados para a LLM. Overhead < 5%.

### Dictionary (level 3)
```
# dict pessoa: Ana,Bruno,Carla
# dict produto: Caneta,Lapis,Borracha
```
No corpo, indices numericos referenciam o dicionario (0=primeiro, 1=segundo).

## 3.3 Niveis de Compressao

| Level | Descricao | RLE? | Sort? | Dict? | Reversivel |
|-------|-----------|------|-------|-------|------------|
| 0 | Expanded (1 valor/linha) | Nao | Nao | Nao | Sim |
| 1 | RLE em consecutivos | Sim | Nao | Nao | Sim |
| 2 | Ordena + RLE | Sim | Sim | Nao | Sim |
| 3 | Dict + ordena + RLE | Sim | Sim | Sim | Sim |

**Level 2 e recomendado para LLMs** — melhor tradeoff accuracy vs compressao.
**Level 3 e o mais compacto** mas indices numericos podem confundir modelos.

## 3.4 Exemplo Completo (Level 2)

Dados originais (3 tabelas CSV):
```
pessoas.csv: id,nome → 20 clientes
produtos.csv: id,nome,preco → 15 produtos
vendas.csv: id_cliente,id_produto,dt,qtd,total → 200 orders
```

TCF v0.2 Level 2 (saida):
```
# TCF v0.2 level=2
# N*val = val repeated N times

## vendas n=486 sorted_by=produto
# STATS total: n=486 sum=51234.5 min=0.95 max=423.1 avg=105.4
pessoa:
12*Ana
8*Bruno
6*Carla
...
produto:
45*Borracha
38*Caderno
52*Caneta
...
dt:
2024-01-03
2024-01-15
...
total:
12.5
3.0
28.9
...
```

**Nota:** Tabelas de referencia (pessoas, produtos) sao eliminadas.
FKs resolvidos para nomes. IDs descartados. Dados flat em 1 tabela.

## 3.5 Compressao: TCF vs Outros Formatos

Para detalhes completos de cada formato, ver apendice [D-format-comparison.md](appendices/D-format-comparison.md).

Resumo (retail_sales 200 orders, ~500 vendas):

| Formato | Tamanho | vs CSV | Tipo |
|---------|---------|--------|------|
| JSONL | ~62KB | 3.5x maior | Row, chaves repetidas |
| CSV | ~18KB | baseline | Row |
| TCF L0 | ~20KB | 1.1x | Column, expanded |
| TCF L2 | ~18KB | 1.0x | Column, sorted+RLE |
| **TCF L3** | **~12KB** | **0.68x** | Column, dict+sorted+RLE |

TCF L3 e **32% menor que CSV** e **81% menor que JSONL** com dados realistas.
Detalhes em [article/05-results-e1-e2.md](05-results-e1-e2.md).

## 3.6 Compressao Teorica

Para coluna com N valores e K valores unicos:
- **CSV/JSONL:** O(N) tokens por coluna
- **TCF L0:** O(N) tokens (columnar sem compressao)
- **TCF L2 sorted+RLE:** O(K) tokens (1 grupo RLE por valor unico)
- **TCF L3 dict+RLE:** O(K) tokens com strings curtas (indices)

RLE e eficiente quando K << N:
- 1000 vendas, 20 produtos → O(20) ao inves de O(1000) = **50x**
- 1000 vendas, 200 clientes → O(200) = 5x (menos repeticao)
- Dados unicos (K=N) → RLE nao ajuda (ratio 1.0x)

## 3.7 Notacao RLE: Escolha e Alternativas

Notacao escolhida: `N*val` ("N vezes val").

| Notacao | Exemplo | Familiaridade LLM | Status |
|---------|---------|-------------------|--------|
| `N*val` | `3*Ana` | Media (multiplicacao) | **Implementado** |
| `N:val` | `3:Ana` | Baixa (parece IP/hora) | Descartado |
| `(N)val` | `(3)Ana` | Media | Alternativa |

Investigacao em andamento (G37): testar se code fences, XML tags e
few-shot examples melhoram a compreensao. Ver [tickets/open/H-G37](../tickets/open/H-G37-notacao-decoracao.md).

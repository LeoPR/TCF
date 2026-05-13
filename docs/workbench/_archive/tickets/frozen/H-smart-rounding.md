---
title: Arredondamento matematicamente controlado (% erro aceitavel)
type: hypothesis
status: OPEN
priority: MEDIUM
created: 2026-04-10
origin: Ideia de arredondar valores com tolerancia controlada para compressao extra
---

# Arredondamento Matematicamente Controlado

## Hipotese

Se o usuario aceita um erro de X% em operacoes de agregacao, podemos
truncar precisao de forma inteligente para aumentar compressao.

Ex: soma de 1000 valores com erro total < 0.1%.
Arredondando cada valor para o decimal certo, a soma acumula erro controlado.

## Intuicao matematica

Para N valores somados com erro individual δ, o erro total no pior caso
e N*δ (se todos erros se somarem). Com distribuicao uniforme, erro esperado
cresce como sqrt(N)*δ (teorema central do limite).

Para aceitar erro total de 0.1% em soma de 1000 valores:
- Pior caso: δ_individual < 0.0001% = 1e-6 do valor medio
- Estatistico: δ_individual < 0.003% = 3e-5 do valor medio (sqrt(1000) ≈ 31)

Na pratica, **o usuario escolhe precision global (ex: 2 decimais)** e o
encoder arredonda. Nao ha magic — mas a interface pode ser:

```python
config = EncodeConfig(
    level=2,
    max_error_pct=0.001,   # 0.1% de erro aceitavel para aggregates
    aggregate_columns=["total"],  # colunas que serao agregadas
)
```

O encoder calcula a precisao minima necessaria para garantir a tolerancia
e arredonda. Valores mais "redondos" comprimem melhor via RLE
(10, 10, 10 vs 10.23, 10.27, 10.19).

## Alternativas

### 1. Precisao fixa (mais simples)
`precision=2` → arredonda tudo para 2 decimais. Ja suportado.

### 2. Precisao por coluna
`precision={"total": 2, "qtd": 0, "preco_unit": 3}` → granular.

### 3. Precisao derivada de tolerancia (inovacao)
`max_error_pct=0.1, ops=["sum"]` → encoder calcula precisao automaticamente.

### 4. Quantizacao por bucket
Valores proximos → mesmo bucket. Ex: `2.47, 2.51, 2.49` → `2.5` (bucket de 0.1).
Ideia ja testada em v0.1 (`bins_16`) e deu resultado ruim para LLMs.
Pode funcionar para compressao se for usada DEPOIS da leitura LLM (no transporte).

## Hipotese testavel

**H-round:** Arredondar `total` para 1 decimal (vs 2 decimais atual)
melhora compressao RLE em 5-15% com erro em sum < 1% e erro em avg < 0.5%.

**Teste:**
- Gerar retail_sales(500) com precisao padrao
- Gerar mesmo dataset com precision=1
- Comparar tamanhos de TCF L2 e L3
- Comparar ground truth (sum, avg) das duas versoes
- Medir accuracy LLM nas duas versoes

Se compressao melhorar significativamente sem degradar accuracy LLM,
adicionar como feature opcional.

## Perigos

1. **Compound error:** arredondamento propaga em calculos multi-step
2. **LLM nao sabe do arredondamento:** pode dar resposta "exata" quando
   pediu "aproximado"
3. **STATS inconsistentes:** se STATS sao computados antes do arredondamento,
   podem dar sum diferente da soma dos valores arredondados

## Relacao com outros tickets

- **P-data-types**: precisao e parte do sistema de tipos
- **E-qualitative-reasoning**: LLMs lidando com aproximacoes naturalmente
- **E-http-protocol**: compressao com precisao controlada para transporte

## Tarefas

- [ ] Implementar `precision` por coluna em EncodeConfig
- [ ] Implementar `max_error_pct` com calculo automatico
- [ ] Testar compression ratio vs precision trade-off
- [ ] Testar LLM accuracy com dados arredondados
- [ ] Documentar como feature opcional no spec

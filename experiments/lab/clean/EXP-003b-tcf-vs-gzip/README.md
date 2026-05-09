# EXP-003b — TCF vs gzip (HP-T1, decisor principal)

## Hipotese

**HP-T1**: TCF L0+sort+gzip eh competitivo com TCF smart+gzip,
reduzindo a necessidade de implementar Propostas E/H/I.

## Decisao em cascata

| Resultado | Caminho |
|-----------|---------|
| smart+gzip >> compact+gzip (>15% adicional) | A: vale implementar E/H/I no Sprint 1+2 |
| smart+gzip ≈ compact+gzip (±5%) | B: compact basta; E/H/I viram opt-in v0.4.x |
| smart+gzip < compact+gzip | bug — pausar e revisar |

## Metodo

5 datasets variados (mesma seed do EXP-003a) × 4 estrategias:

- **csv** — baseline puro
- **tcf raw** — colunar puro, sem sort, sem RLE, sem DICT
- **tcf compact** — RLE + sort_by automatico (heuristica)
- **tcf smart** — auto-tudo: cross-DICT (E) + DICT inline (D16) +
  affix (H) + key elimination (I) + auto-bypass

Cada um passa por `gzip -9` (level 9, standalone — equivalente a
HTTP body completo, ver `EXP-003a/verify-stream.py`).

---

# Resultados

## Mesa de testes — bytes brutos

| Dataset | rows | cols | csv | csv+gz | raw | raw+gz | compact | comp+gz | smart | smt+gz |
|---------|-----:|-----:|----:|-------:|----:|-------:|--------:|--------:|------:|-------:|
| tpch-supplier-100 | 100 | 7 | 13848 | 6343 | 13802 | 6188 | 13674 | 6141 | 11917 | **5906** |
| adult-1k | 1000 | 15 | 108226 | 13169 | 108746 | 12846 | 63749 | 11525 | 27268 | **10146** |
| categorical-heavy | 500 | 7 | 15243 | 4564 | 15295 | 4460 | 12374 | 4098 | 8145 | **2912** |
| time-series | 500 | 5 | 16829 | 5684 | 16873 | 5347 | 15567 | 5011 | 15565 | **5008** |
| mixed-relational | 800 | 8 | 37597 | 9913 | 37649 | 9336 | 28700 | 8363 | 15870 | **6229** |

## Mesa de testes — ganhos relativos (apos gzip)

| Dataset | smart+gz vs compact+gz | smart+gz vs csv+gz | classe |
|---------|------------------------:|-------------------:|--------|
| tpch-supplier-100 | -3.8% | -6.9% | margem fina |
| adult-1k | **-12.0%** | -23.0% | smart vale |
| categorical-heavy | **-28.9%** | **-36.2%** | smart **vence muito** |
| time-series | -0.1% | -11.9% | compact basta |
| mixed-relational | **-25.5%** | **-37.2%** | smart **vence muito** |
| **media** | **-14.06%** | **-23.02%** | — |

## Decisao em cascata — resultado

```
INTERMEDIARIO: smart+gz vence compact+gz por -14.1% em media.
→ NAO eh caminho A (>=15%) nem caminho B (<=5%).
→ Discussao caso a caso.
```

**Refino qualitativo**: existem **2 clusters claros** nos dados:

| Cluster | Datasets | Smart vs compact | Recomendacao |
|---------|----------|------------------|--------------|
| **Estrutural** | adult, categorical-heavy, mixed-relational | -12% a -29% | smart vale |
| **Numerico/unico** | tpch-supplier, time-series | -0.1% a -3.8% | compact basta |

Ou seja: **smart vale quando ha vocabularios compartilhados,
PKs auto-increment, ou afixos repetidos**. Em dados puramente
numericos ou strings unicas, gzip ja capturou tudo.

**Conclusao revisada**: caminho A para datasets relacionais/categoricos,
caminho B para numericos/aleatorios. Auto-bypass agressivo deve
fazer smart cair para compact em datasets do segundo cluster.

---

# Mesa de testes — exemplos visuais por dataset

## Exemplo 1: categorical-heavy (smart vence -28.9%)

Maior ganho relativo (-28.9% de smart vs compact apos gzip).

**Decisoes automaticas tomadas pelo encoder smart**:
- PK eliminada: `id` (auto-increment grau 2)
- Sort_by: `qtd` (cardinality 10/500 = 2%)
- DICT inline em `status`, `categoria`, `cidade` (cardinality < N/2)
- Sem cross-DICT detectado (vocabularios sao distintos: status ≠ categoria ≠ cidade)
- Sem affix (sem prefixos longos)

**Snippet do output `tcf-smart`** (primeiras 20 linhas):

```
# TCF v0.4 lv=smart
## categorical-heavy n=500 pk_eliminated=id sort_by=qtd
status: dict=cancelado,ok,pago,pendente
2*3
0
1
2*0
2
3
1
0
3
2
2*1
3
1
0
2*2
3
2*2
```

`status` declarado como dict + body com indices RLE-aplicados (`2*3` = `pendente,pendente`).

**Tamanhos**:
- CSV: 15243 B
- TCF smart: 8145 B (-46% vs CSV bruto)
- gzip(CSV): 4564 B
- gzip(TCF smart): **2912 B** (-36% vs gzip(CSV))

---

## Exemplo 2: time-series (compact basta, -0.1%)

Diff smart vs compact apos gzip: -0.1% (basicamente iguais).

**Decisoes automaticas**:
- Sem PK eliminavel (`data` eh string ISO, nao auto-increment)
- Sort_by: `temperatura` (escolhido por cardinality moderada)
- Nenhuma coluna teve DICT ativo (todas com cardinality alta — valores numericos floats)
- Sem affix (datas ISO 2026/2027 dao prefixo curto)
- Sem cross-DICT

**Snippet do output `tcf-smart`**:

```
# TCF v0.4 lv=smart
## time-series n=500 sort_by=temperatura
data:
2026-04-11
2026-07-24
2026-07-12
...
```

Sem `pk_eliminated`, sem `dict=`, sem `affix=` — basicamente igual a
compact (so o sort por temperatura ajuda RLE em outras cols numericas).

**Tamanhos**:
- CSV: 16829 B
- TCF smart: 15565 B (-7.5% vs CSV bruto)
- gzip(CSV): 5684 B
- gzip(TCF smart): **5008 B** (-11.9% vs gzip(CSV))

Nesse caso, gzip absorveu quase toda a vantagem possivel. Smart nao
agregou nada vs compact.

---

## Exemplo 3: mixed-relational (smart vence -25.5%)

Schema relacional simulado em uma tabela. Ganho expressivo.

**Decisoes automaticas**:
- PK eliminada: `pedido_id`
- Sort_by: `produto_nome`
- DICT inline em `cliente_nome`, `produto_nome`, `status` (low cardinality)
- Sem cross-DICT entre cliente_nome × produto_nome (vocabs disjuntos)
- Sem affix (nomes curtos)

**Snippet do output `tcf-smart`**:

```
# TCF v0.4 lv=smart
## mixed-relational n=800 pk_eliminated=pedido_id sort_by=produto_nome
cliente_id:
15
8
23
24
18
22
3
38
37
24
...
```

PK `pedido_id` (1..800) eliminada (economiza ~3KB), sort por `produto_nome`
agrupa pedidos similares, DICTs em colunas categoricas.

**Tamanhos**:
- CSV: 37597 B
- TCF smart: 15870 B (-58% vs CSV bruto)
- gzip(CSV): 9913 B
- gzip(TCF smart): **6229 B** (-37% vs gzip(CSV))

Aqui gzip nao conseguiu sozinho extrair todo o ganho — o schema
relacional tem padroes que gzip nao "ve" (PK eliminada como conceito
estrutural).

---

## Estatisticas globais

### Ganhos vs CSV+gzip apos pipeline completo

```
csv+gz  → raw+gz       :  -2.7% medio
csv+gz  → compact+gz   :  -9.1% medio
csv+gz  → smart+gz     : -23.0% medio  ← ganho final cumulativo
```

### Ganhos por etapa (em smart+gz)

| Etapa | Contribuicao tipica |
|-------|---------------------|
| Colunar (raw) | -3% (gzip aproveita melhor) |
| Sort + RLE (compact) | -6 a -10% adicional |
| DICT inline + affix + key-elim (smart) | -0 a -29% adicional |

### Onde smart faz diferenca

```
Forte (-25 a -29%):  schemas relacionais, categoricos densos
Moderada (-12%):     datasets com mistura categorica+livre
Marginal (≤-4%):     tabelas pequenas com strings unicas
Nula (-0.1%):        time-series, dados continuos numericos
```

---

# Arquivos produzidos

| Arquivo | Descricao |
|---------|-----------|
| `results/{dataset}-1-csv.txt` | CSV puro |
| `results/{dataset}-2-tcf-raw.txt` | TCF mode=raw |
| `results/{dataset}-3-tcf-compact.txt` | TCF mode=compact |
| `results/{dataset}-4-tcf-smart.txt` | TCF mode=smart |
| `results/{dataset}-{N}-{mode}.gz` | Versao gzip de cada |
| `results/results.json` | Dados estruturados reproduziveis |

5 datasets × 4 estrategias × 2 (texto + gz) = **40 arquivos**.

---

# Decisao final

**Caminho hibrido** — recomendado:

1. `mode=smart` como **default**, com **auto-bypass agressivo**:
   - Em time-series e dados numericos contiguos: smart cai para compact
     (sem ativar Propostas que nao agregam)
   - Em strings unicas curtas: smart cai para compact (sem ativar DICT)
   - Em schemas relacionais: smart ativa Propostas (E/H/I)
2. Auto-bypass NAO eh otimizacao — eh a forma correta. Tem que detectar
   quando Propostas pioram ou empatam apos gzip e desativar.
3. Implementar Propostas E + I no Sprint 1+2 (maior ganho mensurado).
   Proposta H entra com auto-bypass (so ganha com afixos longos).

**Pendencia de auto-bypass apos gzip**: o auto-bypass atual mede
bytes ANTES do gzip. Caminho ideal seria medir apos gzip — mas custo
computacional alto (rodar gzip antes de decidir). Aproximacao:
threshold mais conservador para ativar Propostas.

## Proximo passo sugerido

EXP-005 (HP-B1, type-preserving) ou EXP-006 (HP-F1, auto-sortedness).
Ambos independentes do resultado de HP-T1 e podem rodar em paralelo.

EXP-007 (HP-T2, chunks × batch) **bloqueado** ate M-chunks-v04 Bloco 1
ser implementado.

## Status

- [x] Hipotese formulada
- [x] Metodo executado
- [x] Resultado: intermediario com 2 clusters claros
- [x] Decisao: caminho hibrido com auto-bypass apos gzip
- [x] Arquivos produzidos: 40 arquivos em results/
- [x] Estatisticas registradas
- [ ] Validar auto-bypass apos gzip em datasets reais (lab futuro)

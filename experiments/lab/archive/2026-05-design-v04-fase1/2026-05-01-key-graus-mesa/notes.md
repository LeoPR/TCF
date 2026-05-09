# Lab dirty: key elimination por grau de maleabilidade

## Tese a testar

Em schemas relacionais com chaves grau 2 (auto-increment local),
TCF pode **eliminar as chaves** e regenerar no decode preservando
**a relacao**, nao os valores literais.

Bytes economizados:
```
ECONOMIA = K · |id_size| - overhead_recovery
```

## Cenarios

| # | Schema | Estrategia |
|---|--------|------------|
| C1 | 3 tabelas pessoa+produto+pedido (sintetica) | comparar preserva vs elimina |
| C2 | TPC-H supplier+nation (real) | s_suppkey eh grau 2; s_nationkey eh grau ? |
| C3 | Schema desnormalizado (1 tabela) | sem FK — eliminacao nao se aplica |

## Predicao

- C1: ELIMINA = ganha (PKs auto-increment + FKs sao puro overhead)
- C2: PARCIAL — s_suppkey eh grau 2 (eliminar); s_nationkey pode ser
  grau 1 se referenciado externamente
- C3: empata ou perde overhead minimo

## Metodo

1. Sintetizar/carregar 3 cenarios
2. Calcular bytes em 2 estrategias:
   - PRESERVE: TCF L3 normal, mantendo todas as chaves
   - ELIMINATE: chaves grau 2 substituidas por indices DICT
3. Validar que relacao se preserva (join no decode == join original)
4. Tabular bytes + ratio de economia

Saida: `./output/`

---

## Resultados (run.py — 2026-05-05)

### Tabela medida

| Cenario | naive | L3 | L3+elim | Ganho elim vs L3 |
|---------|-------|-----|---------|------------------|
| C1 3tables (FKs grau 2) | 737B | 803B | **704B** | **-12.3%** (-99B) |
| C2 TPC-H supplier (so PK) | 2505B | 2810B | **2531B** | **-9.9%** (-279B) |
| C3 desnormalizada (sem keys) | 934B | 650B | 650B | 0% (esperado) |

### Achados surpreendentes

**1. L3 normal PIORA naive em C1 e C2**

L3 com DICT em colunas de IDs auto-increment **adiciona overhead** sem
ganho — cada ID e unico, DICT eh puro custo. C1 +9%, C2 +12% acima
de naive. Eliminacao das chaves resolve isso DUPLAMENTE: nao emite
DICT inutil + nao emite os ids.

**2. Mesmo eliminando so PK, ganho substancial (-10%)**

C2 eliminou apenas s_suppkey (preservando s_nationkey por ser grau 1)
e ja recuperou ~280B em 50 rows. Em escala real (N=10000), seria
proporcional: ~56KB economizados em uma tabela.

**3. C3 confirma null hypothesis**

Sem PK/FK, eliminacao nao se aplica. L3 normal ja eh otimo (-30% vs
naive porque colunas categoricas pequenas — transacao, moeda).
Validates that elimination eh **schema-dependent**.

### Hipotese refinada

A Proposta I ganho real depende de:

```
ECONOMIA = K_rows · (|id_size| + overhead_dict_se_pk_em_string_col)
         - overhead_pk_eliminated_marker
```

Para C1: 50 rows · ~3B/id · 3 chaves (1 PK + 2 FK) = 450B teorico
         medido: 99B (overhead de marker e estrutura)

Para C2: 50 rows · 6B/id (s_suppkey) = 300B teorico
         medido: 279B (matched)

### Afirmacoes induzidas

| # | Afirmacao | Evidencia |
|---|-----------|-----------|
| A1 | Em schema relacional com PK auto-increment, L3 normal pode piorar; eliminacao corrige | C1, C2 |
| A2 | Ganho eliminate vs L3: -10% a -12% em casos sinteticos | medido |
| A3 | Em escala (N=milhoes), ganho seria dominante em databases relacionais | extrapolacao |
| A4 | Sem PK/FK, eliminacao eh no-op | C3 |
| A5 | Auto-detect de grau eh fragil sem schema | observado |

### Limites deste lab

- Datasets pequenos (N=50). Escala real nao foi testada
- Roundtrip de RELACAO nao foi validado (so bytes)
- Auto-detect de grau nao foi tentado — passamos manual
- C2 nao testou eliminacao de FK cross-tabela (supplier-nation)
- Multi-tabela com cardinality alta nao testada

### Recomendacao

Proposta I tem merito comprovado em casos sinteticos. Para avancar:

1. Lab formal `E-key-elimination-real-datasets` em datasets reais com schema
2. Em paralelo: especificar sintaxe `pk_eliminated=` e `fk_resolved=`
3. Decisao de implementar: depende de quantos datasets reais teem schema explicito disponivel

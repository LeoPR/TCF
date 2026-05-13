# Conclusões — comportamento observado em 16 cenários

## Tabela 1 — Estrutura e roundtrip

```
cenario                                  N_tot N_uniq N_int body_RLE rt_sep rt_inl
D1-baixa-card-sem-patricia/original         50      5     0       41     OK     OK
D1-baixa-card-sem-patricia/sorted           50      5     0        5     OK     OK
D1-baixa-card-sem-patricia/random           50      5     0       45     OK     OK
D1-baixa-card-sem-patricia/agrupado         50      5     0        5     OK     OK
D2-alta-card-sem-patricia/original         100     40     1       99     OK     OK
D2-alta-card-sem-patricia/sorted           100     40     1       40     OK     OK
D2-alta-card-sem-patricia/random           100     40     1       99     OK     OK
D2-alta-card-sem-patricia/agrupado         100     40     1       40     OK     OK
D3-baixa-card-com-patricia/original         50      5     1       41     OK     OK
D3-baixa-card-com-patricia/sorted           50      5     1        5     OK     OK
D3-baixa-card-com-patricia/random           50      5     1       45     OK     OK
D3-baixa-card-com-patricia/agrupado         50      5     1        5     OK     OK
D4-alta-card-com-patricia/original         100     25     4       99     OK     OK
D4-alta-card-com-patricia/sorted           100     25     4       25     OK     OK
D4-alta-card-com-patricia/random           100     25     4       95     OK     OK
D4-alta-card-com-patricia/agrupado         100     25     4       25     OK     OK
```

Observações:

- **Roundtrip 16/16 OK** em ambas serializações.
- **Patricia em D2** detectou 1 nó interno (raiz vazia) — comportamento
  esperado quando há diversidade total entre nomes mas algum LCP
  curto entre alguns deles. Para fins de fórmula, conta como
  `N_pat_int=1`.
- **body_RLE varia com ordenação** como esperado:
  - sorted/agrupado → 1 run por valor (body_RLE = N_unique)
  - random/original → quase 1 entry por linha (body_RLE ≈ N_total)

## Tabela 2 — Validação da fórmula

A previsão simbólica em `formula.prever_*` reproduz **exatamente** a
medição real em todos os 16 cenários:

```
                                            sep_med  sep_pred   inl_med  inl_pred  match
D1/original                                     574      574       496      496     OK
D1/sorted                                       213      213       135      135     OK
... (todos os 16 com match OK) ...
D4/agrupado                                    1228     1228       911      911     OK
```

Conclusão: o modelo de camadas em `formula.py` é consistente com o
encoder. Pode ser usado para previsão de tamanho sem rodar o encode
real.

## Tabela 3 — Decomposição por camada

```
cenario                       sep: macro / ref / dados   inl: macro / ref / dados
D1/original                     38 /  516 /   20             15 /  461 /   20
D1/sorted                       38 /  155 /   20             15 /  100 /   20
D1/random                       38 /  547 /   20             15 /  492 /   20
D1/agrupado                     38 /  155 /   20             15 /  100 /   20
D2/original                     38 / 1820 /  232             15 / 1352 /  232
D2/sorted                       38 / 1302 /  232             15 /  835 /  232
...
D4/original                     38 / 1867 /   39             15 / 1579 /   39
D4/sorted                       38 / 1151 /   39             15 /  862 /   39
D4/random                       38 / 1835 /   39             15 / 1547 /   39
D4/agrupado                     38 / 1151 /   39             15 /  857 /   39
```

Por camada:

- **macro**: separado = 38 bytes; inline = 15 bytes. Constante por
  cenário. Camada 3 — registrada como "escala pequena", não pesada
  para conclusão de comparação.
- **dados**: separado = inline em **todos os 16 cenários**. Mesma
  árvore Patricia → mesmos fragmentos → mesmos chars dentro de aspas.
  Diferença zero por construção.
- **ref**: aqui mora a diferença entre serializações.

## Tabela 4 — Camada 2: economia inline vs separado

```
cenario                                   sep_ref  inl_ref  delta    pct
D1/original                                   516     461    -55  -10.7%
D1/sorted                                     155     100    -55  -35.5%
D1/random                                     547     492    -55  -10.1%
D1/agrupado                                   155     100    -55  -35.5%
D2/original                                  1820    1352   -468  -25.7%
D2/sorted                                    1302     835   -467  -35.9%
D2/random                                    1819    1352   -467  -25.7%
D2/agrupado                                  1302     835   -467  -35.9%
D3/original                                   583     532    -51   -8.7%
D3/sorted                                     222     171    -51  -23.0%
D3/random                                     614     563    -51   -8.3%
D3/agrupado                                   222     171    -51  -23.0%
D4/original                                  1867    1579   -288  -15.4%
D4/sorted                                    1151     862   -289  -25.1%
D4/random                                    1835    1547   -288  -15.7%
D4/agrupado                                  1151     857   -294  -25.5%
```

### Observação 1 — delta absoluto é estável por dataset

A economia em bytes é praticamente constante para um dado dataset,
independente da ordenação:

| Dataset | min(delta) | max(delta) | spread |
|---|---:|---:|---:|
| D1 | -55 | -55 | 0 |
| D2 | -468 | -467 | 1 |
| D3 | -51 | -51 | 0 |
| D4 | -294 | -288 | 6 |

A pequena flutuação em D4 vem de counts variáveis na 1ª ocorrência
(detalhe em [algoritmo.md](algoritmo.md)).

### Observação 2 — percentual depende da ordenação

O delta absoluto é estável, mas o **percentual** muda entre
ordenações porque o denominador (`sep_ref`) muda:

- sorted/agrupado têm `sep_ref` pequeno (RLE comprime body) →
  mesmo delta vira % maior (~25–36%).
- original/random têm `sep_ref` grande (poucos runs) → mesmo delta
  vira % menor (~8–26%).

Em outras palavras: quando o body já é compacto por RLE, a economia
adicional do inline pesa relativamente mais. Quando o body é grande
(muitas refs), a economia adicional pesa relativamente menos.

### Observação 3 — economia escala com N_unique, não com N_total

Aplicando a fórmula simplificada `delta ≈ -11·N_unique + 5·N_pat_int`:

| Dataset | N_unique | N_pat_int | delta previsto | delta medido (média) |
|---|---:|---:|---:|---:|
| D1 | 5 | 0 | -55 | -55 |
| D2 | 40 | 1 | -435 | -467 |
| D3 | 5 | 1 | -50 | -51 |
| D4 | 25 | 4 | -255 | -290 |

Ordem de grandeza correta. Imprecisões de ~10–35 bytes vêm de:
- eids variáveis (1 a 2 chars conforme N_unique cresce);
- counts > 1 nas 1ªs ocorrências (depende de ordenação);
- mais sintaxe em decls de filhos Patricia.

A forma fechada exata exige varrer a árvore (que é o que `formula.py`
faz). A fórmula simplificada serve para intuição de grandeza.

### Observação 4 — `N_pat_int` reduz a economia

Comparando D1 (sem Patricia) com D3 (mesmo `N_unique=5`, mas com 1
nó interno Patricia):

- D1 delta: -55
- D3 delta: -51

D3 economiza 4 bytes a menos. Custo de uma decl tardia ≈ 5 chars,
consistente com a fórmula.

Para datasets com hierarquia Patricia profunda (muitos pais
intermediários), a economia inline cresce mais lentamente que
`N_unique`. Em casos extremos (`N_pat_int` ≈ `N_unique`), a economia
poderia se aproximar de zero — mas isso exigiria estrutura
hierárquica muito densa, não testada aqui.

## Pontos a registrar

1. **Roundtrip 16/16 OK** em ambas as serializações com formato
   normalizado.

2. **Fórmula em `formula.py` bate medição real em 16/16**. Modelo de
   camadas validado.

3. **Sinal definitivo da camada 2**: inline economiza em todos os
   cenários medidos. Magnitude proporcional a `N_unique`,
   parcialmente reduzida por `N_pat_int`.

4. **Ordenação é ortogonal à diferença**: muda o tamanho absoluto do
   body em ambas serializações na mesma proporção, deixando o delta
   praticamente intacto. Ordenação afeta % aparente, mas não a
   economia bruta.

5. **Camada 1 (dados efetivos) zerada como fonte de variação** entre
   as duas serializações — confirmação numérica do que dizia a
   convenção.

6. **Camada 3 (macros) é constante e pequena**: 23 bytes a menos no
   inline. Por convenção, não pesa na conclusão.

## O que este experimento NÃO mostra

- Comportamento em N_total >> 100. Para N grande, eids viram 3+
  chars; o overhead `len(str(eid))` em refs cresce, o que pode
  alterar a fórmula simplificada (mas não a forma exata).
- Comportamento com cardinalidade intermediária (ex: 10 ou 50 únicos
  em 200 linhas). Apenas testamos {5, 25, 40} em {50, 100}.
- Datasets com hierarquia Patricia profunda (3+ níveis, muitos pais
  internos). D4 tem 4 pais internos mas estrutura rasa.
- Comparação com formato compacto (sem marcadores verbosos).
- Tempo de encode/decode (não foi medido).
- Robustez de decoder contra inputs corrompidos.
- Outras serializações além das duas testadas. Ex: deferida (decls
  pós-ordem topológica), por slot (`?N` em vez de `noN`).
- Efeito de strings de fragmento mais longas (ex: nomes completos com
  60 chars). O custo `len(frag)` é igual nas duas serializações, mas
  poderia interagir com decisões de quebra de linha em formatos
  reais.

# 11 — padrões repetidos no encode (instrumentação)

## Princípio / motivação

Observação visual no D2 do exp 10: trechos como
`+ "g" + suf:no3` apareciam em várias linhas:

```
no1:  pref:no2 + "g" + suf:no3      ← maria.silva@gmail.com
no7:  pref:no8 + "g" + suf:no3      ← ana.lima@gmail.com
no9:  pref:no5 + "g" + suf:no3      ← joao.souza@gmail.com
no15: pref:no11 + "g" + suf:no3     ← pedro.alves@gmail.com
```

Cada `+ "g" + suf:no3` repete uma sub-expressão. Se fatorizássemos
em um nó composto `no99 = "g" + suf:no3` e reescrevêssemos as
linhas como `pref:no2 + no99`, economizaríamos bytes.

Conceitualmente é o algoritmo **Re-Pair** (Larsson & Moffat 2000)
aplicado sobre o output do encode — detecta digramas (ou
sub-expressões) frequentes e os substitui por não-terminais.

Este experimento é **B-light**: instrumentação simbólica que
**identifica e quantifica** padrões repetidos, sem fatorar. Estilo
exp 09. Se o ganho potencial justificar, exp 12 implementaria a
fatorização real.

## Propósito

Responde a uma pergunta:

1. **Qual o ganho potencial em bytes** se fatorássemos os padrões
   repetidos `(mid_text, suf_text)` e `(pref_text, mid_text)` no
   output do encode do exp 10?

Sem alterar algoritmo. Sem fatorar. Só medir potencial.

## Comparação

- **Compara com**: [10-decomposicao-com-avos](../2026-05-10-10-decomposicao-com-avos/)
  como baseline (composição com cadeia de ancestrais).
- **É comparável?** Não numericamente em bytes reais — gera só
  estimativa simbólica do ganho potencial.

## Cenários e valores possíveis

Mesmos 4 datasets do exp 10. Para cada:

1. Reaplica a decomposição do exp 10 (com cadeia de ancestrais).
2. Conta pares `(mid_text, suf_text)` que aparecem em ≥ 2 strings
   únicas. Idem para `(pref_text, mid_text)`.
3. Para cada par com count C, calcula:
   - economia por ocorrência (em chars/bytes da sintaxe do exp 10)
   - custo da decl extra do nó composto
   - ganho líquido = `C × economia − custo_decl`
4. Soma os ganhos positivos por tipo de padrão.

**Atenção**: ganhos não são aditivos exatos quando a mesma string
poderia ser fatorada por mais de um padrão. Aqui reportamos limite
superior, não previsão exata.

## Resultado observado

| Dataset | ref+dados (exp 10) | ganho (mid,suf) | ganho (pref,mid) | total | % vs exp 10 |
|---|---:|---:|---:|---:|---:|
| D1 | 494 | 0 | 0 | 0 | 0.0% |
| D2 | 655 | **81** | 0 | **81** | **12.4%** |
| D3 | 372 | 0 | 0 | 0 | 0.0% |
| D4 | 505 | 0 | 0 | 0 | 0.0% |

**Apenas D2 tem padrões repetidos significativos.** Os outros 3
datasets não exibem repetição de sub-expressões compostas — cada
folha tem combinação única de pref/mid/suf.

Detalhe dos padrões `(mid, suf)` em D2:

| count | mid | suf | econ/oc | custo_decl | ganho líquido |
|---:|---|---|---:|---:|---:|
| 4 | `"yahoo"` | `".com"` | 15 | 25 | **+35** |
| 4 | `"hot"` | `"mail.com"` | 12 | 22 | **+26** |
| 4 | `"g"` | `"mail.com"` | 10 | 20 | **+20** |

Padrões `(pref, mid)`: nenhum em D2. Razão: em D2, cada combinação
de `(nome.sobrenome@, dominio)` é única (4 nomes × 3 domínios = 12
únicos sem repetição). Padrão `(mid, suf)` repete porque captura
"a parte direita da string" — vários nomes diferentes têm o mesmo
"lado direito" (mesmo `mid + suf`).

### Cenário hipotético: B-médio implementado

Se o exp 12 implementasse a fatorização real desses 3 padrões em
D2:

| Versão | D2 ref+dados |
|---|---:|
| exp 08 (só pai imediato, 0 compostas) | 610 |
| exp 10 (com avós, 12 compostas) | 655 |
| **exp 12 hipotético (10 + fatorização) | **574** |
| Diferença vs exp 08 | -36 (-5.9%) |

Pela estimativa, exp 12 venceria tanto exp 08 quanto exp 10 em
D2. Composição + fatorização compensaria o overhead sintático
da composição.

## Limitações

- 4 datasets pequenos, todos com 20 linhas. Datasets maiores ou
  com mais repetições podem mostrar padrões diferentes.
- Custos calculados em chars baseados na sintaxe verbosa atual.
  Sintaxe diferente daria estimativas diferentes.
- Padrões `(pref, suf)` com mid variável não foram analisados.
  Capturá-los exigiria parameterização (`no99(X) = pref + X + suf`),
  conceitualmente diferente de fatorização simples.
- Ganhos potenciais **não são aditivos exatos** se a mesma string
  pudesse ser fatorada por dois padrões diferentes. Em D2 isso não
  acontece (cada string tem exatamente um par `(mid, suf)` e nenhum
  `(pref, mid)` qualifica), então a soma 81 é exata neste caso.
- Não considera Re-Pair recursivo (fatorizar sub-expressões que já
  foram fatoradas). Apenas 1 nível.
- Sem implementação ou validação de roundtrip. Apenas estimativa.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-11-padroes-no-encode
python run.py
```

Tabela consolidada no stdout. Detalhe por dataset em
`debug-output/<dataset>-padroes.txt`.

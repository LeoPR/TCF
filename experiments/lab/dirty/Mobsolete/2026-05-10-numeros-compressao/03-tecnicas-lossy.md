# Catálogo — técnicas com perda controlada

A perda é uma decisão **explícita** do encoder, justificada pela
tolerância da aplicação. TCF deve permitir, declarar e quantificar.

---

## Por que aceitar perda

A pergunta-chave não é "queremos perder informação?" mas sim:
**"se vamos somar/multiplicar/agregar esses valores, qual a precisão
realmente necessária no resultado final?"**

Se o resultado final é apresentado com 2 casas decimais, valores
intermediários com 5 são desperdício. **Reduzir precisão** vira
compressão sem custo prático.

---

## Categoria 1 — Quantização

### Q1.1 — Rounding uniforme

Arredondar para múltiplo fixo: round(v / step) * step.

- step = 0.01 (centavos)
- step = 0.1 (decimal de 1 dígito)
- step = 1 (inteiro)
- step = 100 (centena)

Codificação: armazenar os valores arredondados (menos chars).

Sintaxe TCF possível:
```
# ext: tensao=quant:0.1
tensao:
110.2
110.3       ← real era 110.27, arredondado pra 110.3
...
```

Decoder retorna os valores arredondados. Aplicação aceita por contrato.

### Q1.2 — Logarithmic / log-quantização

Útil para distribuições com cauda longa: quantiza em escala log.

- Preserva precisão relativa em todo o range
- Loss varia: pequeno na cauda, maior na origem (ou vice-versa)

→ Especializado. Não prioritário para TCF v0.5.

### Q1.3 — Quantização não-uniforme (k-means / clustering)

Encoder roda k-means, encontra k centros, mapeia cada valor ao centro
mais próximo. Resíduo opcional.

→ Complexidade alta no encoder. Reservado.

---

## Categoria 2 — Bit-truncation em float ✗

Truncar mantissa do float64 para float32 ou menos.

- float64 → 64 bits, ~15-17 dígitos significativos
- float32 → 32 bits, ~6-9 significativos
- float16 → 16 bits, ~3-4 significativos

Binário-only. Em TCF texto: equivale à quantização Q1.1 com step
escolhido para casar a precisão.

---

## Categoria 3 — Sum-preserving rounding (a inovação)

A ideia do usuário: arredondar mas preservar a soma. Técnicas conhecidas
da área de **apportionment** (alocação de assentos em eleições):

### S3.1 — Largest Remainder (Hare quota)

Algoritmo:
1. Define total a preservar T = Σ v_i (valor exato)
2. Define escala (grid) g — valor mínimo que se quer manter
3. Calcula `q_i = v_i / g` (quociente fracionário)
4. Cada v_i' = floor(q_i) * g (chão arredondado)
5. Resíduos r_i = q_i - floor(q_i)
6. Soma atual: T' = Σ v_i'. Diferença Δ = (T - T') / g (em unidades de g)
7. Aloca Δ unidades aos `r_i` maiores (top Δ resíduos)

Exemplo:
- Valores: [10.4, 20.3, 30.3], soma = 61.0
- Escala g = 1.0
- floor: [10, 20, 30], soma = 60. Falta 1 unidade.
- Resíduos: [0.4, 0.3, 0.3]. Maior = 10.4. Aloca +1 lá.
- Resultado: [11, 20, 30], soma = 61. ✓ preserva total.

Erro local: cada v_i tem erro ≤ g. Erro global (soma) = 0.

### S3.2 — Banker's rounding (round-half-to-even)

Aplica round-to-nearest-even em vez de round-half-up. Em sequências
grandes, erros se cancelam estatisticamente (em média 0). Não garante
sum-preservation por instância, mas não enviesa.

→ Útil quando contrato é "sem viés" mas não "sum-exato".

### S3.3 — Cumulative rounding

1. Mantém soma cumulativa S exata
2. Para cada v_i, escolhe v_i' tal que S' (soma cumulativa após v_i')
   esteja arredondada ao mesmo grid de S
3. v_i' = round(S_i, g) - round(S_{i-1}, g)

Garante que S' converja para S em cada ponto. Erro local pode flutuar,
mas erro acumulado é zero a cada arredondamento intermediário.

### Como TCF expressaria

Sintaxe possível:
```
# ext: valor=quant-sum:step=1
valor:
10
20
31              ← +1 aplicado aqui (antes era 30)
```

Encoder garante que Σ valores codificados = Σ valores originais (com
soma original armazenada implicitamente ou explicitamente).

Decoder retorna os valores codificados. Aplicação que somar obtém o
total original (a menos do erro de step se não houver garantia
explícita).

### Pergunta aberta

Se a aplicação NÃO sabe que houve sum-preserving, ela vê valores
ligeiramente diferentes. Quem garante que vê o "valor original"?

→ TCF precisa **declarar explicitamente** quando sum-preserving está
ativo, e talvez armazenar a soma original como metadado para
verificação.

---

## Categoria 4 — Erro armazenado (residual encoding)

Em vez de descartar a perda, **armazená-la em uma coluna separada** ou
de forma anexa.

### E4.1 — Coluna paralela de erro

Codificação:
- Coluna principal: valores arredondados
- Coluna paralela: erros de arredondamento

Pode parecer contraintuitivo (armazenar mais), mas:
- Erros têm distribuição compacta (pequenos, próximos de zero)
- Erros podem ter padrão (RLE/dict aplicável)
- Soma das colunas = valor original (lossless via lossy + erro)

```
valor_quant:           erro:
10                     +0.4
20                     +0.3
31                     -0.7         ← restou após sum-preserving
```

Aplicação que tolera erro: usa só a 1ª coluna.
Aplicação que precisa exato: usa 1ª + 2ª.

→ TCF pode oferecer "compressão estratificada": user escolhe quantos
níveis de erro reconstituir.

### E4.2 — Erro como dict

Se o erro tem cardinalidade baixa (apenas alguns valores possíveis pelo
método de quantização), dict captura:

```
erros: dict idx 1 = +0.4, idx 2 = -0.5, idx 3 = +0.1
1, 1, 2, 3, 1, 2, 3, 3, ...
```

Pergunta aberta: em datasets reais, o erro de quantização tem
cardinalidade baixa o suficiente para dict ser útil?

### E4.3 — Erro "perdoável" e erro "perdoável só após verificação"

Dois níveis de garantia:
- **Perda total**: erro é perdido (encoder rounded, decoder vê
  rounded, app aceita)
- **Perda recuperável**: erro armazenado, app pode pedir reconstituição

Flag separada para cada nível.

---

## Categoria 5 — Quantização tolerante a operações específicas

Elaborando a intuição do usuário:

> Resistente à multiplicações pequenas, etc.

### M5.1 — Sum-stable

Como S3. Preserva soma. Tolerância à multiplicação por escalar
(constantes): preservada se a constante for estritamente nz.

Não preserva multiplicação ENTRE valores quantizados (a*b ≠ a'*b' em
geral).

### M5.2 — Multiplication-stable (logarítmica)

Quantizar em log-space:
- Armazena log(v) arredondado
- Multiplicação no original = soma no log-space
- Preserva produtos exatamente quando log é exato no grid

Útil para probabilidades, taxas, fatores. Para somas, perde precisão.

### M5.3 — Operação-aware

Hipótese: TCF declara `op-target` por coluna:
```
# usage: valor=sum-stable, taxa=mult-stable
```

Encoder escolhe quantização por declaração. Decoder não muda; só
encoder.

→ **Pergunta aberta**: usuário deve declarar isso? É demais
infiltrar semântica de aplicação no formato?

→ **Alternativa**: TCF não declara, aplicação **escolhe a precisão**
e aceita o que TCF entrega.

---

## Categoria 6 — Compressão estatística (preserva distribuição)

### D6.1 — Histogram quantization

Encoder calcula histograma da coluna, mapeia valores aos buckets.
Loss = largura do bucket. Cada valor → idx do bucket.

Equivalente a quantização não-uniforme adaptada à distribuição.

### D6.2 — Top-K + outliers

Mantém K valores "típicos" exatos; resto é arredondado para o mais
próximo dos K. Outliers explícitos.

### D6.3 — PCA / SVD

Para matrizes (múltiplas colunas correlacionadas). Reservado para
datasets de alta dimensionalidade (não típico em TCF de 5-10 colunas).

---

## Categoria 7 — Combinações com a regra unificada

Após qualquer técnica lossy, os valores resultantes podem ser
**identicos entre si com mais frequência** que os originais. Aí
RLE/dict capturam:

- Quantização: valores arredondados ao mesmo step → muitas duplicatas →
  dict ou RLE eficiente
- Sum-preserving: idem
- Top-K: explicitamente reduz a K valores únicos → dict de K entradas

→ A regra unificada (RLE+dict) **se beneficia** das técnicas lossy.
Ordem natural: lossy primeiro, RLE/dict depois.

---

## Resumo das técnicas vs prioridade

| Técnica | Compatível TCF? | Prioridade v0.5 | Mesa futura |
|---|---|---|---|
| Quantização uniforme (Q1.1) | ✓ | **alta** | sim, com `# ext: <col>=quant:step` |
| Quantização logarítmica | ✓ | baixa | reservado |
| Bit-truncation | ✗ | — | TCF-binary |
| Sum-preserving (S3.1) | ✓ | **média-alta** | sim, pesquisa profunda |
| Banker's rounding | ✓ implicit | baixa | aplicação decide |
| Erro como coluna paralela | ✓ | **média** | mesa específica |
| Erro como dict | ✓ | média | depende dist do erro |
| Op-target declarado | ? | baixa | ticket de discussão |
| Histogram quant | ✓ | baixa | reservado |
| PCA/SVD | ✗ | — | reservado |

---

## Conclusão da seção

As técnicas mais úteis para TCF são:
1. **Quantização uniforme** com `step` declarado por coluna
2. **Sum-preserving rounding** (a inovação) — pesquisa profunda
   pendente
3. **Erro armazenado** opcional para recuperação

As demais são reservadas para datasets específicos (sci, IoT) ou para
um dialeto binário hipotético.

→ Próximo arquivo formaliza as **perguntas abertas** e propõe **ordem
das mesas** experimentais.

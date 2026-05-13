# Taxonomia dos padrões numéricos

Classificar antes de comprimir. Cada padrão pede técnicas diferentes.

---

## Eixo 1 — Espaço de valor

| Tipo | Espaço | Exemplo |
|---|---|---|
| Inteiro pequeno | ℤ ∩ [0, 2¹⁶] | quantidade em carrinho |
| Inteiro grande | ℤ | IDs, contagens populacionais |
| Decimal com precisão fixa | k casas decimais | dinheiro, R$ X,XX |
| Float arbitrário | ℝ aproximado | medições científicas |

---

## Eixo 2 — Distribuição estatística

| Padrão | Forma | Exploração |
|---|---|---|
| Uniforme | distribuição rectangular | range encoding com bordas |
| Concentrada (gaussiana, etc) | pico em torno de uma moda | delta de baseline + outliers |
| Bimodal/multimodal | múltiplos picos | dict por modo + delta dentro |
| Com cauda longa | poucos valores extremos | quantil-stripping + outliers |
| Discreta com poucos valores | cardinalidade baixa | dict |
| Discreta com muitos valores em range | cardinalidade média | bit-packing com offset |

---

## Eixo 3 — Padrão temporal/posicional

Como os valores se sucedem na coluna (após sort decidido).

| Padrão | Característica | Técnica natural |
|---|---|---|
| iid (random) | valores independentes | dict ou range encoding |
| Monotônico crescente | ordenação intrínseca | delta |
| Monotônico decrescente | ordenação reversa | delta negativo |
| Oscilante em torno de baseline | volta para média | delta de baseline |
| Trending com ruído | tendência linear + jitter | regressão + resíduos |
| Step changes | platôs com transições | RLE local + diff |
| Sequência cíclica | período conhecido | delta de período |

---

## Eixo 4 — Semântica do dado

Como a aplicação USA o número. Importa para escolha de lossy.

| Tipo | Operações comuns | Tolerância |
|---|---|---|
| Quantidade (cardinal) | soma, contagem | exata (lossless) |
| Identificador | igualdade | exata |
| Score / rating | comparação, média | pequena tolerância OK |
| Medição contínua | estatística, plotagem | tolerância proporcional |
| Moeda | soma exata, total deve fechar | exata, mas pode redistribuir erro |
| Probabilidade | multiplicação, soma=1 | proporcional, sum-preserving |
| Coordenada geográfica | distância | tolerância proporcional |

---

## Eixo 5 — Tolerância à perda

| Nível | Aceita perda? | Garantias necessárias |
|---|---|---|
| **Estrita** | ❌ | bit-perfect roundtrip |
| **Quantizada** | ✓ | erro absoluto ≤ ε |
| **Sum-preserving** | ✓ | Σ valores codificados = Σ originais |
| **Mean-preserving** | ✓ | média preservada (relacionada à anterior) |
| **Distributional** | ✓ | distribuição estatística mantida |
| **Best-effort** | ✓✓ | só quer "parecido" |

---

## Combinações específicas levantadas

### A — "Bounded counter" (carrinho ≤ 12)

Eixo 1: inteiro pequeno
Eixo 2: cardinalidade muito baixa
Eixo 3: iid
Eixo 4: quantidade
Eixo 5: estrita

→ Dict (regra unificada já cobre) ou bit-packing 4 bits/valor.

### B — "Oscilação em torno de baseline" (tensão IoT 110V)

Eixo 1: float
Eixo 2: gaussiana estreita
Eixo 3: oscilante
Eixo 4: medição
Eixo 5: quantizada (mV de tolerância OK)

→ Delta de baseline (`Δ` em mV) + quantização. Técnica bem documentada.

### C — "Números que são classificações" (códigos numéricos)

Eixo 1: inteiro
Eixo 2: cardinalidade variável
Eixo 3: iid
Eixo 4: identificador
Eixo 5: estrita

→ Dict puro. Não tem álgebra; tratá-los como string seria igual.

### D — "Faixa de idade" (range)

Eixo 1: inteiro
Eixo 2: discreto com bordas conhecidas
Eixo 3: iid
Eixo 4: faixa
Eixo 5: estrita

→ Dict (poucas faixas). Ou se as faixas são ranges contínuos, encoder
emite só o início ou identificador da faixa.

### E — "Preços com casas decimais variáveis"

Eixo 1: decimal
Eixo 2: bimodal (preços comuns + extremos)
Eixo 3: iid (após sort)
Eixo 4: moeda
Eixo 5: sum-preserving (rounding distribuído)

→ Aqui mora a inovação que o usuário mencionou. Pesquisa.

### F — "Float científico com tolerância" (medições)

Eixo 1: float
Eixo 2: gaussiana
Eixo 3: trending
Eixo 4: medição
Eixo 5: quantizada

→ ZFP, FPC, Gorilla — todos lidam. Mas são binários. Para texto,
quantização explícita + delta.

---

## Inventário do que já cobrimos vs o que falta

| Padrão | Mesa anterior cobre? | Lacuna |
|---|---|---|
| Bounded counter (A) | sim, dict | OK |
| Oscilação baseline (B) | parcialmente (delta de data, generaliza) | precisa formalizar para float |
| Números classificação (C) | sim, dict | OK |
| Faixa de idade (D) | sim, dict | OK se faixas pré-definidas |
| Sum-preserving (E) | **não** | pesquisa nova |
| Float quantizado (F) | parcialmente (delta) | precisa quantização |

---

## Eixos cruzados — exemplos não-óbvios

### Coluna `valor_unitario` do nosso dataset

Eixo 1: decimal
Eixo 2: bimodal (preços baixos 0.50-3.00 e altos 50.00)
Eixo 3: iid (sem ordem temporal)
Eixo 4: moeda
Eixo 5: estrita (preço unitário deve fechar com total)

→ Cobertura atual (RLE+dict pós-sort): boa. Lossy não se aplica para
preços individuais.

### Coluna hipotética "tensão_lida" de IoT

Valores 109.8, 110.2, 110.0, 109.7, 110.5, ...

Eixo 1: float
Eixo 2: gaussiana N(110, 0.5²)
Eixo 3: iid (ou autocorrelacionado)
Eixo 4: medição
Eixo 5: quantizada (0.1V de precisão)

→ Cobertura atual: dict puro. Cardinalidade alta, dict ineficiente.
Falta: delta de baseline (110V) + quantização para 1 casa decimal.

### Coluna hipotética "saldo_conta" — milhares de transações

Eixo 1: decimal
Eixo 4: moeda
Eixo 5: estrita (cada centavo conta)

→ Cobertura: delta entre saldos? Diferenças menores que valores
absolutos. Dict não funciona (cardinalidade ≈ N).

→ Falta: delta numérico generalizado (não só dates).

---

## Conclusão da seção

Há padrões claros e a maioria tem técnica conhecida. O TCF cobre bem os
casos simples (A, C, D). Os casos B, E, F precisam de extensões
específicas:

- **Delta numérico generalizado** (B, F): generalização do δ que já temos
  para dates. Próximo arquivo cataloga.
- **Quantização explícita** (B, F): encoder arredonda; flag declara
  precisão.
- **Sum-preserving rounding** (E): pesquisa nova, próximo arquivo
  detalha.

Próximas seções cobrem essas técnicas.

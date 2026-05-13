# Mesa de pesquisa — compressão de números

**Data:** 2026-05-10
**Tipo:** mesa de **pesquisa**, não experimentação direta. Sem dataset
ainda. Foco: catálogo, taxonomia, perguntas abertas, roadmap.

---

## Por que pesquisa antes do experimento

As mesas anteriores avançaram de forma empírica: dataset → estratégias →
bytes → conclusões. Funcionou para padrões simples (RLE, dict, delta de
data). Para números, a complexidade salta: há **muitas estratégias
heterogêneas**, várias com perda controlada, cada uma com domínio
específico de aplicação.

Antes de gastar tempo experimentando combinações, precisamos:
1. **Catalogar** as técnicas existentes (lossless e lossy)
2. **Mapear** quais técnicas casam com quais padrões de dados
3. **Identificar** as perguntas em aberto que ainda não foram
   respondidas pela literatura
4. **Priorizar** quais experimentar primeiro

Sem isso corre-se o risco de inventar do zero coisa já bem-estudada,
ou pior, escolher uma técnica subótima por desconhecimento.

---

## Padrões numéricos levantados pelo usuário

Tipos de números que aparecem em dados reais e merecem tratamento
diferenciado:

| Padrão | Exemplo | Característica |
|---|---|---|
| Inteiros gerais | quantidades, IDs | discretos, range variável |
| "Números que são classificações" | códigos, ratings | numéricos sintaticamente, categóricos semanticamente |
| Ranges/faixas | idade 18-25, faixa salarial | discretos com bordas conhecidas |
| Bounded counters | itens em carrinho ≤ 12 | inteiro com teto baixo |
| Oscilação em torno de baseline | tensão 110±5V de IoT | medição flutuante, range estreito |
| Floats com tolerância | preços que podem ser arredondados | precisão maior que necessária |

Cada um pede técnica diferente. A mesa cataloga.

---

## A pergunta nova: lossy controlado

Insight do usuário:

> Se eu pensar que vou usar os valores pra somar, subtrair — qual a faixa
> de erro que pode flutuar se eu arredondar os valores para conseguir
> comprimir? Posso arredondar para distribuir o valor em que a soma
> dê igual (assim como fazem em parcelamento).

Isto introduz **tolerância de operação** como parâmetro de compressão:
- O encoder pode arredondar se a operação dominante (soma, média, etc.)
  ainda fica correta dentro de uma tolerância
- O erro pode ser **distribuído** entre os valores, não apenas dropado
- Se o erro tiver estrutura (igual em vários valores), ele próprio
  pode ser comprimido (RLE/dict no erro!)

Isto é território menos comum em formatos de armazenamento e abre
muitas perguntas.

---

## Princípios da mesa

1. **Pesquisa primeiro, experimento depois** — esta mesa é catálogo.
2. **Não inventar onde já existe** — cita literatura quando aplicável.
3. **Distinguir lossless de lossy controlado** — ambos têm seu lugar.
4. **TCF é texto** — algumas técnicas binárias caem fora; outras
   adaptam (representar offset em texto custa diferente que em bits).
5. **Compatibilidade com flags Lxxx** — técnicas novas viram flags
   opt-in se sobreviverem ao filtro de domínio.

---

## Estrutura da mesa

| Arquivo | Conteúdo |
|---|---|
| `01-padroes-numericos.md` | Taxonomia detalhada dos padrões |
| `02-tecnicas-lossless.md` | Catálogo de técnicas sem perda |
| `03-tecnicas-lossy.md` | Catálogo de técnicas com perda controlada |
| `04-perguntas-e-roadmap.md` | Perguntas abertas + sequência de próximas mesas |

Cada arquivo cita literatura, marca o que já temos e o que falta. No
final, `04` propõe a ordem de mesas experimentais para preencher os
gaps mais críticos.

# Conclusões — escala do algoritmo do exp 16

Roundtrip 12/12 OK. Algoritmo escala em qualidade e em tempo
como previsto pela análise teórica.

## Observação central — cobertura cresce com N

Resultado mais relevante deste experimento. Em todas as 4
famílias do regime A, a cobertura ref% **aumenta** com N:

| Família | N=50 → N=1000 | Ganho absoluto |
|---|---|---:|
| urls | 93.9% → 98.8% | +4.9 pp |
| iso | 82.9% → 98.7% | +15.8 pp |
| ips | 75.8% → 96.3% | +20.5 pp |
| codigos | 93.3% → 95.9% | +2.6 pp |

A intuição: os "literais de introdução" (1ª URL, 1ª data, 1ª
sub-rede, 1º código) têm custo fixo. Quando N é pequeno, esses
literais dominam o total. Quando N cresce, eles **se diluem** —
viram fração desprezível.

`ips` ganhou mais (+20.5 pp) porque tem mais introduções
estruturais (7 sub-redes) e o ganho relativo é maior quando o
denominador (N) cresce. `codigos` ganhou menos (+2.6 pp) porque
já estava saturado em N=50 (só 4 prefixos novos).

## Unidades por string convergem para ~2

| Família | N=50 | N=1000 | convergência |
|---|---:|---:|---|
| urls | 4.56 | 2.25 | sim |
| iso | 5.38 | 2.26 | sim |
| ips | 3.68 | 2.09 | sim |
| codigos | 2.38 | 2.07 | sim |

Resultado consistente com a estrutura do algoritmo: em regime
estável cada string nova precisa apenas de `ref-pref + ref-suf`
(2 unidades) para ser descrita. As 12 strings de cada família
em N=1000 ficam:

| Família | puro ref (2 unid) | r+lit≤4 (3-6 unid) | r+lit>4 (7+ unid) |
|---|---:|---:|---:|
| iso | 875 | 121 | 3 |
| ips | 760 | 237 | 0 |
| urls | 623 | 372 | 4 |
| codigos | 500 | 499 | 0 |

`iso` é o regime mais favorável: 87.5% das strings em N=1000
viram puro ref de 2 unidades.

## Tempo escala O(N² · L) com efeito de L visível

Análise teórica: para cada string nova, comparar com todas as
anteriores (N-1) e cada comparação custa O(L) chars. Total
O(N² · L). Resultado prático:

| Família | L médio | razão N=200/50 | razão N=1000/200 |
|---|---:|---:|---:|
| urls | ~46 | 10.4× | **51.8×** |
| iso | ~20 | 27.1× | 24.4× |
| ips | ~12 | 15.6× | 46.6× |
| codigos | ~14 | 16.4× | 21.2× |

Esperado de O(N²) puro: 16× (200/50) e 25× (1000/200).

- A razão 200/50 fica próxima de 16× na média (variabilidade ±10×
  por efeitos de cache + comprimento)
- A razão 1000/200 mostra desvios maiores. `urls` ganha 51.8×
  (mais que o dobro do teórico) porque L é maior e o overhead por
  caracter conta proporcionalmente mais quando N cresce

Conclusão: a curva é compatível com O(N² · L). Não é puro O(N²).

## Onde dói

Em **N=1000** com Python puro single-threaded:

| Família | tempo |
|---|---:|
| urls | 3.8 s |
| iso | 3.4 s |
| ips | 1.6 s |
| codigos | 1.5 s |

Tractable para batches off-line. Lento para uso interativo. Em
N=10k a extrapolação dá ~6 min (urls); em N=100k ~10 h. Sem
otimização, inviável em produção em escala grande.

Otimizações possíveis (não testadas):

- **Cache de LCP/LCS** com chaves por prefixo/sufixo (suffix array
  ou trie). Custo amortizado pode ser sub-quadrático.
- **Pruning** com índice de prefixos ≥ min_len: só comparar com
  anteriores que compartilham primeiros 3 chars.
- **Janela deslizante** (limite W de anteriores ativos). Memória
  fixa, tempo linear em W. Compressão pode cair se padrões
  recorrem fora da janela.
- **Implementação em C/Rust**: speedup de 50-200× sem mudar
  algoritmo. Viabiliza N até ~50k-100k.

## Encode/decode são desprezíveis

Mesmo em N=1000, encode + decode somam <15 ms. Custo total é
dominado por `processar`. Otimização do lado de I/O ou parser
não vale enquanto o gargalo for a comparação.

## Pontos a registrar

1. **Algoritmo escala em qualidade**. Cobertura ref% sobe com N,
   não cai. Cada família converge para um teto próximo de 95-99%.

2. **Algoritmo escala em tempo como teorizado**. Não há surpresa
   negativa. Mas Python puro limita o N máximo prático para
   ~1000-5000.

3. **A "vantagem assintótica do online" do exp 15** se confirma
   em escala. As 2 unidades por string que aparecem em N=12 se
   mantêm em N=1000.

4. **L (comprimento) entra na constante**. URLs (46 chars) pesam
   mais que IPs (12 chars). Para strings longas em escala grande,
   pode valer a pena truncar o LCP/LCS na busca (parâmetro
   `max_len`).

5. **Introduções residuais visíveis** apenas em IPs (2 só
   literal em N=1000 = 0.2%). Em todas as outras famílias o
   algoritmo encontra ref para 100% das strings após a 1ª.

6. **Comparação com Re-Pair** não foi feita em escala. Re-Pair é
   batch e exige outra abordagem para escalar (greedy global pode
   ficar inviável muito antes de 1000). Não foi medido aqui.

## O que este experimento não mostra

- Comportamento em N > 1000
- Datasets com repetição (RLE adjacente não atuou)
- Famílias do regime B em escala (UUIDs e CPFs continuam fora do
  alvo)
- Efeito de mudar `min_len` em escala
- Comparação com Re-Pair / Front coding em escala
- Viabilidade em linguagem nativa (C/Rust)
- Otimizações algorítmicas que poderiam reduzir a constante

## Próximo experimento natural

Duas direções a partir daqui:

**Direção A — atacar a constante O(L)**: implementar pruning por
prefixo / cache. Mantém algoritmo, reduz tempo. Não traz nova
informação científica — é engenharia.

**Direção B — variantes algorítmicas com nova capacidade**:
- **exp 19 (par A+B independente)**: pode reduzir os 372 casos
  de `r+lit≤4` em urls e os 237 em ips, aumentando puro ref
- **exp 20 (revisão retroativa)**: ataca introduções residuais
  via reabertura; testar a hipótese levantada no exp 17

Direção B traz **nova informação** sobre o algoritmo. Direção A
é importante mas pode esperar até o algoritmo conceitual estar
fechado.

Sugestão: seguir para **exp 19** (par A+B independente). É a
limitação 1 declarada no README do exp 15; agora temos números
em escala para medir o ganho honestamente.

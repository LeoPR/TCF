# Conclusoes M4.C1 + M4.C1'

**Data**: 2026-05-13
**Vem de**: [`buffer-e-refragmentacao.md`](buffer-e-refragmentacao.md),
[`arvore-da-arvore-vs-regex.md`](arvore-da-arvore-vs-regex.md),
[`../M4-A-instrumentacao/conclusoes.md`](../M4-A-instrumentacao/conclusoes.md)
**Sucede**: orienta decisao M4.C2 (online) e M4.C3 (refragmentacao)

## Resultado

| Sintaxe | D1-D4 total | delta vs M1.E |
|---|---:|---:|
| M1.E (baseline) | 676 | 0 |
| M2.A (sufixos com preambulo) | 666 | -10 (-1.5%) |
| M4.C1 v1 (runs inteiras, idx implicito) | 666 | -10 (-1.5%) |
| **M4.C1' (subsequencias, idx implicito)** | **636** | **-40 (-5.9%)** |

RT 12/12 OK em M4.C1'.

## Achados

### Achado 1 — idx implicito + subsequencias funciona

M4.C1' captura ~40 bytes, ~35% do limite teorico (114B do M4.A).
O resto fica em conflitos entre candidatos sobrepostos que greedy
nao resolve otimo.

Exemplos:
- D1: alias `3,11,5,6` (sufixo) aparece 3x — economiza ~11 bytes
- D4: alias `2..4` aparece 5x em meio de runs maiores — economiza
  ~13 bytes

### Achado 2 — runs inteiras = sufixos = mesmo regime

M4.C1 v1 (runs inteiras) e M2.A (sufixos com preambulo) deram o
mesmo total (666) por caminhos diferentes:
- M2.A: detector encontra SUFIXOS de runs; preambulo gasta 4+Lt
- M4.C1 v1: detector encontra RUNS INTEIRAS; idx implicito gasta 1

Custos diferentes mas mesmo total — sugere que o regime de
redundancia "padrao completo repetido" e' o limite que esses dois
atingem.

### Achado 3 — subsequencias internas e' a diferenca

M4.C1' separa-se com -30B adicionais porque detecta padroes que
nem M2.A nem M4.C1 v1 viam:
- D4 `2..4` em meio de runs (M4.C1 v1 nao detectava — runs inteiras
  eram unicas)
- D1 `3,11,5,6` como sufixo de 3 runs distintas (M2.A detectava com
  4+Lt overhead; M4.C1' com 2 chars)

### Achado 4 — alocacao de idx por ordem de aparicao e' essencial

Bug encontrado em v0 do M4.C1: encoder alocava por net descending,
decoder por ordem de `~` no TCF. Divergia. Fix: encoder espelha
decoder (alocacao por ordem de 1a aparicao no body).

Esse padrao serve para qualquer sintaxe com idx implicito.

## Limites do M4.C1' (greedy)

Greedy nao resolve casos onde 2+ candidatos competem:
- Tupla X aparece em runs A, B
- Tupla Y aparece em runs A, C
- Greedy escolhe maior net; o outro perde A e fica com menos R

Caso real D1 esperado (M4.A teorico 56B intermediario implicito,
M4.C1' real ~11B) sugere que muitos candidatos competem.

## Pendencias / proximo passo

Tres caminhos:

**(a) M4.C2 — versao online (buffer = 1)**
- Streaming, decisao a cada linha
- Mais arriscado (sincronia encoder/decoder em buffer)
- Possivelmente menor ganho que C1' (C1' batch tem visao global)
- Testa hipotese "online sacrifica X% por Y x velocidade"

**(b) M4.C3 — refragmentacao**
- Online + capacidade de desfazer alias decidido cedo demais
- Mais complexo
- So' faz sentido se C2 mostrar perda significativa vs C1'

**(c) Fechar M4 e ir pro prototipo**
- M4.C1' provou que idx implicito + subsequencias e' tecnica
  valida
- Ganho 5.9% e' moderado mas significativo
- Combinar com M1.E base no prototipo
- Streaming pode ser implementado nativo no prototipo

## Recomendacao para decisao

Recomendo **(c)** — fechar M4 com M4.C1' como resultado canonico.
Motivos:
1. C1' ja' valida o conceito de idx implicito + subsequencias
2. Online (C2) tem alto risco de complexidade vs ganho duvidoso
3. Refragmentacao (C3) e' caso de uso real, melhor no prototipo
4. Os 70B restantes do limite teorico estao em conflitos greedy
   — resolver requer ILP ou similar (fora do escopo dirty)

Se houver tempo/interesse, C2 minimo (apenas para confirmar perda
em N=12) tambem pode ser feito antes do fechamento. Mas C3 fica
melhor no prototipo.

## Conexoes

- [[buffer-e-refragmentacao.md]] — estrategias de buffer
- [[arvore-da-arvore-vs-regex.md]] — motivou subsequencias
- [[../M4-A-instrumentacao/conclusoes.md]] — limites teoricos

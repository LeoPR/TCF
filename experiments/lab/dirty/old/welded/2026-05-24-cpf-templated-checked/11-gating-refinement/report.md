# Sub-exp 11 — Gating refinement (report) — HIPOTESE REFUTADA

**Data**: 2026-05-24
**Hipotese (do sub-exp 10)**: ADR-0010 gating (n>=100 ativa min_len=6)
prejudica D-IP-subnet (5.78% -> 68% entre n=50 e n=200).

## Estrategias testadas

| Estrategia | min_len |
|---|---|
| canonical | heur v3 (ADR-0010 padrao) |
| no_gating | 3 forcado |
| smart_gating | 3 se cadence_detected + variable_length, senao heur v3 |

## Resultados

| Dataset | n | canonical | no_gating | smart_gating |
|---|---:|---:|---:|---:|
| D-IP-subnet | 50 | 37 | 37 | 37 |
| D-IP-subnet | 100 | 37 | 37 | 37 |
| D-IP-subnet | 200 | 1827 | 1827 | 1827 |
| D-IP-subnet | 500 | 6897 | 6897 | 6897 |
| D-IP-subnet | 1000 | 15747 | 15747 | 15747 |
| D-CPF-uniform | 50 | 942 | 942 | 942 |
| D-CPF-uniform | 200 | 3800 | 3819 | 3800 |
| D-CPF-uniform | 1000 | 18936 | 19987 | 18936 |
| D-IP-uniform | 200 | 3671 | **3584** | 3671 |
| D-IP-uniform | 1000 | 18159 | 18903 | 18159 |

## Hipotese REFUTADA

**Bypass de gating (no_gating min_len=3) NAO muda nada em D-IP-subnet**:
- n=200 canonical 1827B == no_gating 1827B
- n=500 canonical 6897B == no_gating 6897B
- n=1000 canonical 15747B == no_gating 15747B

Smart_gating e canonical produzem IDENTICOS resultados em D-IP-subnet
porque min_len nao afeta este caso especifico.

## Investigacao do real culpado

O que muda entre n=50 (5.78%) e n=200 (68.17%)?

| n | Subnets | Comportamento |
|---:|---:|---|
| 50 | 1 (subnet1 IPs 0..49) | TODOS mesmo prefix — HCC seq-RLE captura |
| 100 | 1 (subnet1 IPs 0..99) | TODOS mesmo prefix — HCC captura todos |
| 200 | 2 (subnet1 + subnet2) | **PREFIXES diferentes entre subnets** |

**Achado real**: HCC seq-RLE captura cadence DENTRO de uma subnet
(prefix uniforme + cadence no ultimo octeto), mas NAO TRANSITA entre
subnets diferentes (prefix muda completamente).

ADR-0010 gating NAO eh o culpado. O problema eh estrutural no detector
de cadence/seq-RLE — opera localmente, nao reseta/reaplica quando
padroes mudam ao longo do dataset.

## Implicacao real

**ADR-0010 esta correto no que faz**. Smart_gating nao agrega.

**Direcao verdadeira (futuro)**: detector de cadence adaptativo que
reseta quando padroes mudam. Atualmente HCC seq-RLE processa body
sequencial mas decide based on first pairs near-identical. Pra
multi-subnet, precisa detectar "subnet boundary" e iniciar novo run.

Issue arquitetural, nao calibracao. Mais complexo de fixar.

## Validacao colateral: gating ajuda em CPF uniform alta-entropia

Em D-CPF-uniform (alta entropia, no cadence):
- n=1000 canonical (min_len=6): 18936B
- n=1000 no_gating (min_len=3): 19987B (5.5% pior)

Confirma que ADR-0010 gating ajuda em datasets sem cadence + high-
entropy + cardinality alta. Trade-off correto pro caso real-world.

## Conclusao

Hipotese ADR-0010 gating bug **REFUTADA empiricamente**. Sub-exp 10
me induziu a erro ao concluir "gating eh culpado" — coincidencia
entre min_len change e n>=100 threshold mascarava o problema real
(cross-subnet behavior).

ADR-0010 mantida. Direcao futura: detector cadence multi-segmento.

## Lesson methodological

Investigar mais profundamente antes de mudar parametros canonicos.
Sub-exp 11 bem-sucedido em REFUTAR antes que algo errado fosse
welded. Filosofia "viavel agora > otimo eventual" + "antes de declarar
confirmada empirica, RT em N=5 datasets" salvou de mudanca prematura.

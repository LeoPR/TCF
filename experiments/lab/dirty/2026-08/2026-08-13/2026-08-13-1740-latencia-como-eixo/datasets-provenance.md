# Proveniência dos dados

Todos **sintéticos**, gerados por `run.py` (seed fixa 20260813), materializados em
`inputs/<tipo>.entrada.json`. Nenhum dado externo, nenhum acesso a `Z:`.

Sintético é o correto aqui, e a razão importa: o lab compara **mecanismos de ganho**
(progressão global × afixo × dicionário × por-valor × nenhum), e cada tipo precisa isolar
um mecanismo. Corpus real misturaria os mecanismos e a régua ficaria ilegível. A
contrapartida honesta: os multiplicadores medidos **não** são previsão para dado real —
são a demonstração de que o multiplicador varia com o mecanismo, não com o tipo.

| rótulo | n | mecanismo de ganho isolado |
|---|---:|---|
| `data-diaria-spec` | 600 | progressão global (`*N+1\|`) + spec |
| `data-uteis-spec` | 600 | progressão global **cíclica** (período 5) + spec |
| `data-diaria-core` | 600 | a mesma coluna **sem** spec — o controle que separa tipo de mecanismo |
| `cpf-spec` | 600 | spec por-valor, sem progressão (CPFs com DV correto, gerados por fórmula) |
| `inteiro-sequencial` | 600 | progressão global **sem** spec e **sem** período — o controle do eixo "período" |
| `email-afixo` | 600 | afixo compartilhado (OBAT) |
| `categoria-k5` | 600 | dicionário (cardinalidade 5) |
| `texto-aleatorio` | 600 | nenhum — o controle de baixo |

**CONSTANTE na comparação**: n=600, os mesmos cortes, e cada fatia é um wire **independente**
(decodificável sozinha). Só o tipo/mecanismo varia.

Sobre os CPFs: gerados por fórmula com dígito verificador correto, sem qualquer origem em
pessoa real. Não são publicados fora de `inputs/cpf-spec.entrada.json`, que é dado sintético
de laboratório.

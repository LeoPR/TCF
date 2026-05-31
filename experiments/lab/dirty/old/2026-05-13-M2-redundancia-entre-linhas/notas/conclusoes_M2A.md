# Conclusoes M2.A — Alias de tupla de refs

## Resultados nos canonicos

| Dataset | M1.E (base) | M2.A | delta | proporcao |
|---|---:|---:|---:|---:|
| D1 | 149 | 141 | -8 | -5.4% |
| D2 | 180 | 178 | -2 | -1.1% |
| D3 | 206 | 206 | 0 | 0% |
| D4 | 141 | 141 | 0 | 0% |
| **TOTAL** | 676 | 666 | -10 | -1.5% |

RT 8/8 OK. Aliases detectados quando sufixos de runs-de-refs se
repetem >= 2 vezes E net positivo.

## Leitura matematica (escala)

**Funcao de eficiencia do alias:**

Para tupla de Lt chars (serializacao M1.E) substituida por `$N`
(1 + len(str(N)) chars) em R linhas:

```
Net = R · (Lt - 1 - len(N)) - (Lt + 2 + len(N) + 1)
```

Para N=1 (alias de 1 digit), simplificando:
```
Net(Lt, R) = R · (Lt - 2) - (Lt + 4)
```

**Pontos de equilibrio** (Net = 0 → R necessario):

| Lt | R minimo para ganho |
|---|---|
| 4 | (4+4)/(4-2) = 4 |
| 6 | (6+4)/(6-2) = 2.5 → R ≥ 3 |
| 8 | (8+4)/(8-2) = 2 |
| 10 | (10+4)/(10-2) = 1.75 → R ≥ 2 |
| 12+ | sempre R ≥ 2 |

**Implicacao escalavel**: para tuplas longas (Lt ≥ 8), basta 2
ocorrencias para ganho. Para tuplas curtas (Lt = 4), precisa 4
ocorrencias.

Em **datasets grandes com familias homogeneas** (regime esperado
em dados reais como URLs, paths, IDs), o numero de ocorrencias
R cresce com tamanho da familia, mas Lt e' fixo (depende da
estrutura). Ganho cresce **linearmente com R** — escala bem.

## Por que o ganho e' pequeno nos canonicos

Datasets D1-D4 tem 12 strings cada. Tuplas com R=3 dao ganho
marginal (1-3 bytes por tupla detectada). Em N=1000 com K=10
familias de 100 strings cada, ganho extrapolado:

- Tuplas com Lt=6, R=100: Net = 100·4 - 10 = +390 bytes por alias
- Multiplo aliases por dataset

Em **escala minuscula (4 datasets x 12 strings)**, o overhead
de declaracao (~10 chars por alias) come a economia. Em escala
grande, **declaracao e' custo fixo, economia cresce com R**.

## Bugs encontrados e corrigidos

### Bug 1: detector criava aliases sobrepostos

Primeiro detector criava `$1=3,11,5,6` E `$2=8,3,11,5,6` (um
contem o outro). Resultado: declaracoes duplicadas, custo extra
sem economia adicional.

**Fix**: detector greedy que remove ocorrencias usadas das runs
apos selecionar cada alias.

### Bug 2: aplicador quebrava range mesmo quando piora

Aplicador originalmente substituia qualquer sufixo matching por
alias, sem comparar com a serializacao com range completo. Em D3
linha 4, `web2..7` (7 chars, range completo) virava `web2..4,$1`
(10 chars), perdendo 3 bytes.

**Fix**: aplicador agora computa baseline (`emit_refs_range`) e
candidato com alias, escolhe o menor.

## Camada 2 confirmada como dimensao util

A redundancia entre linhas (Camada 2 identificada em
[../../2026-05-12-M1-marcacao-ambiguidade/notas/revisao-critica-M1E-output.md])
**existe e e' explorabel**. Em escala minuscula da' ganho marginal
(-1.5%), em escala maior espera-se 5-15% adicional sobre M1.E.

**Para o prototipo**, vale incorporar alias de tupla de refs sobre
a base M1.E. Custos:
- Encoder mais complexo (precisa scan + detector)
- Decoder ganha tabela de aliases (estrutura nova)
- Sintaxe usa novo char (`$`) que precisa escape em literais

## Limitacoes

- Detector greedy nao otimo. Pode haver combinacoes melhores.
- So' considera SUFIXOS de runs (nao prefixos nem trechos centrais).
- `$` reservado em literais (datasets D1-D4 nao tem `$`, OK por
  ora).
- Aliases limitados a 9 (ids de 1 digit). Em escala precisaria mais.

## Outras camadas de redundancia ainda nao testadas

Listadas na revisao critica M1.E:

1. **RLE nao-adjacente**: linhas inteiras identicas separadas.
   Verificado nos canonicos: D1-D4 tem 12 strings UNICAS cada.
   Nenhum dispara RLE nao-adjacente. **Sem caso real para testar.**
2. **Declaracao compacta do no fonte**: parcialmente atacado por
   M1.D (slice). Estrutralmente dominado por M1.E em regime
   exp 16.
3. **Template + slot estrutural**: requer extender algoritmo.
   Sai do escopo M2.

Conclusao: dentro do **regime do exp 16 + dados D1-D4**, M2.A
e' o unico micro M2 que **revela ganho proporcional**. Outros
micros M2 (B, C) ficam sem caso para testar.

## Decisao apos M2.A

**Fechar M2 com M2.A como dimensao mapeada.** Ganho marginal nos
canonicos, mas escala bem teoricamente. Vale incorporar ao
prototipo (M1.E base + aliases opcional).

**Proximo passo recomendado**: ir para o prototipo conforme
discussao anterior. Validar em N grande se ganho extrapolado se
materializa.

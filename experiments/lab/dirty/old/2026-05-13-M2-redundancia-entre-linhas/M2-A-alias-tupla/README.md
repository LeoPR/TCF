# M2.A — Alias de tupla de refs

## Tecnica

Identifica sufixos de runs-de-refs que se repetem entre linhas e
substitui por alias `$N` declarado em preambulo. Ataca **Camada
2 de redundancia** (entre linhas).

## Sintaxe

Preambulo (apos `[` body open):
```
$1=3,11,5,6
$2=3,12,6
```

Uso na linha: `$N` substitui o sufixo onde economiza:
```
7,8,$1     (em vez de 7,8,3,11,5,6)
```

## Algoritmo

Encoder:
1. Aplica logica de M1.E (range + escape escopo) como base
2. Coleta runs-de-refs por linha (sequencias consecutivas)
3. Detector greedy:
   - Sufixos (K>=3) de cada run viram candidatos
   - Net(R, Lt) = R · (Lt - 1 - len(N)) - (Lt + 2 + len(N) + 1)
   - Seleciona maior net; remove ocorrencias usadas
4. Aplicador: para cada run, compara serializacao baseline (range
   M1.E) vs com alias; escolhe menor

Decoder:
1. Le linhas que comecam com `$N=` no preambulo, monta tabela
2. Em ref-context, expande `$N` em refs (suportando ranges
   internos como `5..7`)

## Net teorico (escala)

```
Net(Lt, R, N=1) = R · (Lt - 2) - (Lt + 4)
```

Pontos de equilibrio (Net = 0):
- Lt = 4: R >= 4
- Lt = 6: R >= 3
- Lt = 8: R >= 2

**Ganho cresce linearmente com R.** Em escala (datasets grandes
com familias homogeneas), Net positivo cresce sem bound enquanto
declaracao continua custo fixo.

## Resultados nos canonicos

Ver [../notas/conclusoes_M2A.md](../notas/conclusoes_M2A.md).

| Dataset | M1.E | M2.A | delta |
|---|---:|---:|---:|
| D1 | 149 | 141 | -8 |
| D2 | 180 | 178 | -2 |
| D3 | 206 | 206 | 0 |
| D4 | 141 | 141 | 0 |
| **TOTAL** | 676 | **666** | **-10 (-1.5%)** |

Ganho marginal em escala minuscula. Funcao de eficiencia teorica
mostra escala favoravel.

## Limitacoes

- Detector greedy nao otimo (combinacoes melhores podem existir)
- So' considera SUFIXOS de runs, nao prefixos nem trechos
- `$` reservado em literais (datasets D1-D4 nao tem `$`)
- Maximo 9 aliases (ids 1-digit) — em escala precisaria mais
- Encoder mais complexo: scan + detector + aplicador caso-a-caso

## Como rodar

```bash
cd 2026-05-13-M2-redundancia-entre-linhas
python run_lote.py
```

# M3.A — No compartilhado simples (sem encadeamento)

## Tecnica

Detecta prefixos/sufixos de eids referenciados por R >= 2
descendentes e declara como no compartilhado `&N=texto` no preambulo.
Cada descendente usa `&N` em vez da serializacao M1.E dos refs.

## Sintaxe

Preambulo apos `[`:
```
&1=hotmail.com
&2=yahoo.com
```

Uso no body: `&N` no lugar da seq de refs.

## Resultado nos canonicos

| Dataset | M1.E (base) | M3.A | delta |
|---|---:|---:|---:|
| D1 | 149 | 149 | 0 |
| D2 | 180 | 180 | 0 |
| D3 | 206 | 206 | 0 |
| D4 | 141 | 141 | 0 |
| **TOTAL** | 676 | 676 | 0 |

**Net 0 em todos os 4 datasets.** Detector nao selecionou nenhum
alias — todos os candidatos tiveram net <= 0.

## Por que nao compensa nos canonicos

Em [conclusoes.md](conclusoes.md) — analise detalhada.

Resumo: M1.E ja' comprime refs sequenciais via range (`a..b`).
Substring de Lt chars geralmente vira Lr chars curtos em M1.E
(ex: "hotmail.com" 11 chars → `11,5,6` 6 chars). Custo de declarar
`&N=hotmail.com` (15 chars) nao se amortiza com R=3 usos
economizando 4 chars cada (12 chars).

**Pra ganho**: ou R >> 3 (datasets grandes), ou Lt curto + Lr longo
(substring com refs dispersas), ou **encadeamento profundo** (M3.B).

## Estrutura

```
M3-A-no-compartilhado/
  README.md       (este)
  syntax.py       implementacao
  conclusoes.md   analise detalhada
  output/         TCFs gerados
  decoded/        contra-prova
  debug/          detalhes
```

## RT
4/4 OK (TCFs identicos a M1.E porque detector nao selecionou
aliases). Validacao trivial.

## Limitacoes

- Apenas no compartilhado simples (sem encadeamento `&N=&P+ext`)
- Detector greedy
- `&` reservado em literais (datasets D1-D4 nao tem)
- Net nulo nos canonicos — proximo micro (M3.B) precisa atacar
  encadeamento

## Como rodar

```bash
cd 2026-05-13-M3-encadeamento-declaracoes
python run_lote.py
```

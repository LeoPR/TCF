# 2026-08-09-1710 — revisão dos tipos do ciclo (bool → date)

Pedido do owner: *"revise os tipos que fizemos até o momento, que vai desde bool e afins
até date (…) um pequeno lab de teste de ambos pra ver comportamento de cada um pra ver se
está tudo certo"*. Conclusões: [`result.md`](result.md).

## Como rodar

```
python run.py
```

Percorre a matriz de 32 casos (28 de comportamento + 4 fail-louds esperados), confere em
cada um: **rota** (header pinado por prefixo), **RT** (assert) e **teto de bytes** (pega
regressão grossa). Sai com código 1 se qualquer um falhar — a matriz é re-executável como
teste de conformidade.

## Guia de nomes

| onde | o quê |
|---|---|
| `inputs/<caso>--json-lib-like.json` | input após higiene `json.loads(json.dumps(...))` |
| `intermediates/<caso>--trilha.json` | rota escolhida + telemetria `seq_rle_runs` do caso |
| `outputs/<caso>.tcf` | wire real (vitrine) das famílias bool/num/data |
| `outputs/matriz.md` | a tabela completa esperado × observado |
| `outputs/medicoes.json` | matriz + interação do periódico, em máquina |

## O que a matriz cobre

- **bool** (ADR-0036..0039): b1 denso, b2 ternário, core-com-slots, lazytype com extras, null puro
- **numérica tipada** (T-BN-TIPADO): nB 1/2 bits, float, null, sequencial e **periódico** na rota tipada, grafia canônica
- **strings**: bN low-card, bool-em-string (caixa preservada), alta cardinalidade, vazia/whitespace
- **natures** (ADR-0015 + fixes): CPF×bN (FLOOR-vê-bN), CNPJ constante, IP×ADR-0016, CPF+null
- **data** (SPEC_DATA_ISO + ADR-0040): diária, úteis, feriado, mensal, ruído, null, grafia suja
- **fail-louds esperados**: `date`/`Decimal`/`datetime` nativos, int+str misto

`src/tcf` NÃO foi tocado.

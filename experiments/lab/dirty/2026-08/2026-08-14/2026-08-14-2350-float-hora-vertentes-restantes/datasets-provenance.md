# Procedência dos dados — e o viés declarado

## Sintéticos (4 colunas)

Gerados em `run.py`, **sem `random`** (módulo e LCG determinísticos). Todos com **k=97 ou
espalhado** e n=2000, para as réguas serem comparáveis:

| coluna | geração | para quê |
|---|---|---|
| `float-sint` | `1.0 + (i%97)·0.25` | k=97 → cai no bN; mede o custo de fatiar o bN |
| `hora-sint` | LCG em 08:00–18:00 | quase todos distintos → linha-a-linha, o caso caro |
| `int-regua` | `1000 + (i%97)` | a régua de CPU/memória |
| `str-regua` | `item-NNN` (97 distintos) | a régua de string |

**Viés declarado**: `float-sint` e `int-regua` têm o MESMO k e o mesmo padrão modular — de
propósito, para a comparação de perf ser entre **tipos**, não entre distribuições. `hora-sint`
é deliberadamente o caso caro (k alto). Nenhum estima o mundo.

## Reais (2 colunas)

`Z:/tcf-data/interim/`, passo espalhado, alvo 2000. **Não versionado**; o lab roda sem `Z:`.

- `float-real` = `wine.density` — a coluna de maior precisão do corpus.
- `hora-real` = a parte de hora do `online-retail.InvoiceDate` (segundo constante `00`).

## Vieses das medições

- **Vertente E (perf)**: dev-run, máquina não quiescente, 3 repetições. Razões, não absolutos.
- **Vertente F (transporte)**: gzip nível 9 como proxy de recompressor. O gate do bN usou
  brotli; a direção do achado coincide, os números não são comparáveis entre si.
- **Vertente C (latência)**: fatias por posição (`vals[i·tam:(i+1)·tam]`) — mede o custo de
  fatiar o **encode**; não mede o modelo "1 wire em p pedaços" (esse é o `T-PULSO-SINGLE-COL`).
- O gzip do JSON dos sintéticos é excepcionalmente pequeno (303 B) porque o JSON modular é
  quase periódico — é o **melhor caso do gzip**, e por isso o −175,9% é teto do efeito, não
  típico. As colunas reais (−18,8%, −5,7%) são a leitura honesta.

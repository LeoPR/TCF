# 2026-08-09-1853 — data: o alvo MENSAL (olhar pelo mês, não pelo dia)

Direção do owner sobre o `data-mensal` da revisão de tipos (lab `1710`): o ordinal conta
DIAS e paga a contabilidade do calendário; no eixo do MÊS o incremento vira `+1` uniforme.
Conclusões: [`result.md`](result.md).

## Como rodar

```
python run.py
```

8 regimes × 4-5 alvos, RT em DOIS níveis por célula (wire real via `decode()` + espelho
naive de cada alvo contra o input). `src/tcf` não é tocado — as colunas transformadas vão
pro `encode()` real (o core pós-ADR-0040 come sozinho).

## Guia de nomes

| onde | o quê |
|---|---|
| `inputs/<regime>--json-lib-like.json` | input após higiene json |
| `intermediates/<regime>--trilha.json` | todos os candidatos do regime + rotas + válvula (quantos válidos) |
| `outputs/mensal-dia1--A1-ordinal-atual.tcf` | o wire REAL de hoje (679 B) — decodável |
| `outputs/<regime>--<alvo>.wire.txt` | wires dos alvos hipotéticos (não são TCF válido: tag `:data-mes` não existe) |
| `outputs/medicoes.md` / `.json` | tabela completa + rotas |

## Os alvos

| | payload | convenção |
|---|---|---|
| A1 | ordinal-dia (o soldado) | — |
| A2 | `ano*12+(mês-1)` | dia==01 |
| A2f | idem | dia==último |
| A3 | `ano*100+mês` (YYYYMM) | dia==01 |
| A4 | `(ano*12+mês-1)*31+(dia-1)` | **nenhuma** (injetivo p/ toda data) |
| YM | mês-época com parser/grafia `YYYY-MM` | spec irmão |

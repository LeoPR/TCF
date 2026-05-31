# Mesa — δ (delta) para datas (compressão por repetição em valores derivados)

**Data:** 2026-05-09
**Status:** mesa nova; alfabeto/representação foi deferido (ver
`docs/workbench/tickets/open/S-representacao-de-indice.md`)

---

## Distinção conceitual fixada

A compressão tem dois eixos ortogonais. Decidimos focar:

| Eixo | Estratégias | Status atual |
|---|---|---|
| **Repetição** (padrões nos dados) | RLE, dict, **delta**, prefix elision, line-RLE | em mesa ativa |
| **Representação** (mais info/byte) | alfabeto denso, bit-packing | deferido (ticket S) |

Esta mesa explora **delta encoding** — uma transformação que cria
padrões repetitivos onde antes havia "valores únicos sequenciais"
(timestamps, IDs ordenados, contadores). É repetição sobre valores
**derivados**, não sobre valores **brutos**.

## Por que delta encoding precisa entrar

A regra unificada (RLE+dict) já cobre repetições óbvias. Mas falha em:

```
Datas:     2026-01-05, 2026-01-06, 2026-01-07, 2026-01-08
```

Cada valor único, sem repetição literal. RLE = 0, dict = 0 (todas
declarações). **Mas o padrão é trivial:** sequência aritmética de +1 dia.

O delta transforma:
```
Original:  2026-01-05, 2026-01-06, 2026-01-07, 2026-01-08
Delta:     2026-01-05, +1, +1, +1
RLE local: 2026-01-05, 3*+1
```

E aí a regra unificada **funciona normalmente** sobre os deltas.

→ Delta é **transformação pré-encoding**, não substitui a regra
unificada. Aplicada por coluna que tem padrão sequencial.

---

## O dataset extendido

Vou estender o dataset das mesas anteriores (30 linhas) com uma 5ª
coluna `data` que mostra **3 padrões diferentes** para forçar comparação
honesta:

1. **Sequencial denso** (rows 1-7): dias consecutivos, 1 venda/dia
2. **Mesmo dia** (rows 8-13): 6 vendas todas em 2026-01-15
3. **Mistura** (rows 14-22): alguns sequenciais, alguns mesmo dia, gaps
4. **Esparso/aleatório** (rows 23-30): datas espaçadas sem padrão claro

Isso permite estudar:
- Quando delta+RLE arrasa (padrão A — denso e sequencial)
- Quando delta+dict ajuda (padrão B — mesmo dia repetido)
- Quando delta perde valor (padrão D — esparso)
- Misturas reais (padrão C)

---

## Plano da mesa

| Arquivo | Conteúdo |
|---|---|
| `01-dataset.md` | Dataset estendido com coluna data (30 linhas, 4 padrões) |
| `02-formas-delta.md` | Variantes de codificação delta + sintaxe |
| `03-aplicado.md` | Aplicar a cada padrão e cada cenário de sort |
| `04-conclusoes.md` | Quando δ vence, integração na flag Lxxx |

---

## Hipóteses prévias

| ID | Hipótese | Predição |
|---|---|---|
| H-δ1 | Delta vence absoluto sempre que dataset tem ordem temporal | bytes muito menores |
| H-δ2 | Delta + RLE captura "mesmo dia" (delta=0) e "sequencial" (delta=+1) com ganhos massivos | ganho >50% no padrão A e B |
| H-δ3 | Delta sem sort (datas espalhadas) ainda ganha por **representação curta** (delta < absoluto) | ganho moderado mesmo sem RLE |
| H-δ4 | Sort por data antes de aplicar delta é a configuração ótima | confirma intuição |
| H-δ5 | Delta NÃO ajuda se cada data for única e não monotônica (extremo aleatório) | ganho zero, talvez negativo |

A mesa testa cada uma.

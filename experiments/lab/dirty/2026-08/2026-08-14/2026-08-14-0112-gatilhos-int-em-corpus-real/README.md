# Os gatilhos do int em corpus REAL

> Fecha a lacuna que os três labs sintéticos de inteiro declararam: *"falta medir a
> FREQUÊNCIA dos gatilhos em corpus real — o corpus dita o default"*. É a regra que valeu
> para data.

## Estado — era / foi / é / será

- **Era**: três labs sintéticos controlados (22h58, 23h26, 00h32) mediram **onde** cada
  mecanismo ajuda, isolando regimes. Nenhum dizia **com que frequência** os regimes aparecem.
- **Foi**: o desenho mudou em 2026-08-14 — o `OFFPAD` saiu (a base não viajava), o `min_len`
  entrou. Restaram 4 mecanismos: `PAD`, `B94`, `min_len`, `bN`.
- **É**: 39 colunas numéricas reais, descobertas **automaticamente** nos hubs de `Z:`, medidas
  nas duas ordens. Resultado em [`result.md`](result.md): agregado **11,2% menor**; o **PAD é
  o que vale** (mediana 1,72×, sem empates); o **B94 é marginal** (1,14×, 33 vitórias de ≤1 B);
  o **`min_len` não ganha em nenhuma** — e a razão é que este corpus não tem timestamps.
- **Será**: decidir se solda o PAD; e abrir a rota tipada, que hoje recusa **tanto** `nature=`
  **quanto** `min_len=`.

## Como rodar

```
python extrai.py    # só com Z: montado; regrava inputs/fontes/ (congelado no repo)
python run.py       # roda SEM Z:, a partir das fatias congeladas
```

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/fontes/_manifesto.json` | as 39 colunas: origem, n, k, faixa, exemplo |
| `intermediates/por-coluna.json` | a medição completa: gatilhos, bytes de cada mecanismo, vencedor |
| `outputs/<coluna>.<ordem>.tcf` | o wire do núcleo |
| `outputs/<coluna>.<ordem>.roundtrip.json` | contra-prova |

## Ressalvas

- **Viés declarado**: 25 das 39 colunas são TPC-H (gerador de benchmark, muitas chaves
  sequenciais) — favorece o PAD. Ver [`datasets-provenance.md`](datasets-provenance.md).
- Os mecanismos são medidos na rota **string** + 1 byte do discriminador `n`, porque a rota
  tipada os recusa. Não somar o byte seria comparar wires que não se emitem.
- Dirty: conclusão **orientativa**.

## Vínculo

`T-NUMERO-SPEC` · `T-MIN-LEN-CANDIDATO` · `T-NATURE-IGNORADA-CALADA` ·
`T-INT-CONFORMIDADE-DE-FLUXO`.
Nota que mudou o desenho: [`…-0210-offpad-detalhado-e-o-int-no-date.md`](../../notas/2026-08/2026-08-14-0210-offpad-detalhado-e-o-int-no-date.md).

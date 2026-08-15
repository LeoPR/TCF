# Float e hora nas vertentes restantes — a reavaliação

> **Owner (2026-08-14)**: *"o .8 preza tanto pela funcionalidade, fechar gaps e possibilidades
> extras de comprimir tipos (specs com especialidades), ver se o wire interno fecha tudo, desde
> o spec até após a saída de forma geral quando possível pra tudo. E particularmente agora, ver
> se o float e o time estão de acordo com essa dinâmica e se não faltou nada interessante ainda.
> Lembrando também da vertente de latência, memória, velocidade, compressão etc."*

**Uma pergunta**: os fechamentos de float e hora passaram a dinâmica **completa** do `.8`?

**Resposta curta**: os 5 eixos estruturais sim; **as vertentes de execução não tinham sido
passadas em nenhum fechamento de tipo** — nem int, nem data. Este lab as mede para float e
hora (com int e string de réguas) e acha **um gap real**: a ponta lazy não abre tipo nenhum.
Ver [`result.md`](result.md).

## Estado — era / foi / é / será

- **Era**: float e hora fechados nos 5 eixos (dispatch, candidatos, API, wire, RT).
- **Foi**: a cobrança do owner sobre latência/memória/velocidade/compressão e "o wire fecha
  tudo até após a saída".
- **É**: 6 vertentes medidas, 0 falhas de RT. Achados: `view` **não abre** single nem `.8H`
  (nenhuma coluna tipada tem caminho lazy); o custo de fatiar depende da **classe** do vencedor
  (bN 2,62×, literal 1,11×, polaridade **0,96×** — fica menor); hora custa **21× o int** em
  CPU e **126× a entrada** em pico de memória (dev-run); e no **transporte o sinal inverte**
  (gzip do JSON < gzip do wire nas 6 colunas).
- **Será**: o ritual de fechamento passa a ter 5 eixos + 4 vertentes; int e data completam
  as deles com este `run.py` de gabarito.

## As três correções da 1ª rodada (defeitos meus)

1. **Eu rotulava a tabela tipada de `.8M`.** O dispatch é *type-coherent*: dict só-strings →
   `.8M`; dict com qualquer tipo → `.8H`. O rótulo errado escondia o achado do view.
2. **O classificador de granularidade não casava o disc tipado** (`nB77d0` começava com `n`,
   não com `B`) e rotulava bN de "linha-a-linha".
3. **`vw.nrows()`** — na 1ª chamada usei a API errada do LazyTCF e reportei "não abre" para o
   `.8M` também; ele abre.

## Ressalva sobre a vertente E (velocidade/memória)

**Dev-run** em máquina não quiescente — o mesmo status que o `bench_perf` chama de
não-probatório. Valem as **razões entre tipos** (mesmo n, mesma máquina, mesmo instante), não
os absolutos. Nenhum número de E entra em baseline.

## Como rodar

```
python run.py     # sai 0 só se todos os RT fecharem
```

Roda **sem `Z:`** (as colunas reais são puladas). Não toca `src/tcf/` — o `.8M` interno é
consultado por import (`_encode_multi`), somente leitura.

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<col>.entrada.json` · `.fonte.json` | as 6 colunas e a procedência |
| `outputs/tabela-tipada.tcf` · `.roundtrip.json` | o `.8H` com float+hora+str, RT com tipo |
| `outputs/<col>.fatia8-exemplo.tcf` | a 1ª fatia de p=8 |
| `intermediates/vertentes.json` | as 6 vertentes, com avisos de dev-run |

## Vínculo

fechamentos: [`…-1616-fechamento-float`](../2026-08-14-1616-fechamento-float/) ·
[`…-2230-fechamento-hora`](../2026-08-14-2230-fechamento-hora/) ·
régua de fatias: lab `2026-08-13-1740-latencia-como-eixo` ·
leitura dupla: gate do bN (8,8% terminal / 1,7% pós-brotli) + `project_bn_3fluxos` ·
direção: *single-col é multi-col de UMA* (a 5ª divergência) · `T-BUDGET-DE-BUSCA` ·
consolidado: [`docs/theory/float-e-variantes-consolidado.md`](../../../../../docs/theory/float-e-variantes-consolidado.md)

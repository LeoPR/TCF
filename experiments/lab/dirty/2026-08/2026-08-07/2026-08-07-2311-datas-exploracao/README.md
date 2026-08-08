# DATA como tipo — exploração

**2026-08-07 · dirty · exploratório**

```
python run.py     # regenera inputs/, intermediates/, outputs/
```

## Por que

Data já apareceu em vários labs, mas sempre como **pretexto pra exercer o bN**. O EXP-016
tem um caso só (`dom-datas-incrementais`, 3 datas em ~20 B de domínio) e ele existe pra
mostrar o OBAT comprimindo *dentro* do domínio — não pra dizer nada sobre data.

Aqui data é o assunto, e o **bN fica em segundo plano**: uma rota possível entre outras.

## As quatro perguntas

| | |
|---|---|
| **era** | data é "string com estrutura", o core dá conta |
| **foi** | um caso no EXP-016, sem conclusão sobre o tipo |
| **é** | ver [`result.md`](result.md) — o core **não ganha em regime nenhum** |
| **será** | natureza de data como candidato do `min()`, alvo = `*N+M|` |

## Os eixos

| eixo | o que varia | casos |
|---|---|---|
| **formato** | a mesma sequência em 10 grafias (ISO, BR, US, compacto, epoch, extenso, ano, ano-mês…) | 10 |
| **precisão** | ano → ano-mês → data → +hora → +segundo → +ms → +tz | 8 |
| **regime** | como os valores se distribuem: diário, semanal, mensal, repetido, agrupado, espalhado, espalhado-ordenado, descendente | 8 |
| **regime-ts** | timestamp: log mesmo-dia, log esparso, vários dias, hora redonda | 4 |
| **escala** | n = 12 · 120 · 1200 | ×3 |

**90 medições**, RT conferido em todas (RT quebrado aborta o lab).

## As hipóteses naive

Três ideias óbvias, calculadas sobre os **mesmos dados**. Não são wire — são o **piso** que
um tratamento por natureza teria de bater:

- `H-split` — quebrar em campos (`YYYY`/`MM`/`DD`) e encodar cada um
- `H-delta` — 1ª data por extenso + diferenças em dias
- `H-epoch` — dias desde a época, como número

## O que sai daqui em uma linha

O TCF **já tem** o mecanismo que esmaga data (`*N+M|`, seq-RLE multi-delta): 120 datas
diárias em **22 B**. A grafia ISO é que não alcança ele — as mesmas 120 datas custam **97 B**,
e o buraco chega a **620×** no regime mensal com n=1200.

Mas **nenhuma representação ganha sempre**: `epoch` ganha no passo regular, `split` no
espalhado, `delta` no repetido. Data precisa de mais de um candidato, não de um substituto.

## Arquivos

- [`dados.py`](dados.py) — os geradores (sem RNG; o "espalhado" usa LCG de semente fixa)
- [`run.py`](run.py) — encoda, confere RT, mede, e calcula as hipóteses
- [`result.md`](result.md) — os achados
- [`outputs/medicoes.md`](outputs/medicoes.md) — as tabelas por eixo e escala
- `outputs/*.tcf` — 30 wires (n=120) · `inputs/*.json` — as colunas de regime
- [`intermediates/medicoes.json`](intermediates/medicoes.json) — cru

`src/tcf` **não é tocado**.

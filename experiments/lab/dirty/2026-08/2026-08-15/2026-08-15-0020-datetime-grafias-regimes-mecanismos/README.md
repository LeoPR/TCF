# Datetime — grafias × regimes × mecanismos

> **Owner (2026-08-15)**: *"gere uma variedade provável de datetimes, com os tipos e variações
> de formato para ver o comportamento do que se tem do TCF, e aí vemos como melhorar algum
> deles. **Foco no datetime agora, não misture tipos** pois dificulta minha análise. Também
> pode fazer variações de compressão para esse formato, e aí estudamos algo que seja uma
> mistura do datetime ou um mais específico ainda pra datetime."*

**Só datetime.** Nenhuma régua de int/float/string.

## O enquadramento que a sua direção fixou

> *"os tipos são comportados, já que têm origem em bancos de dados que já tratam esse tipo de
> dado como canônico; seria muito raro ter misturas, e mesmo nessas condições provavelmente
> seriam corrupções de transmissão."*

Então **a grafia é uniforme por coluna**, e o lab não testa robustez a lixo misturado — testa o
comportamento de cada grafia canônica. Os dois eixos ficam separados de propósito (cruzá-los
daria 104 colunas e esconderia qual explica o quê).

## Os três blocos

- **1 — 13 grafias**, regime fixo. SQLite/MySQL, ISO com `T`, RFC 3339 (`Z` e offset),
  PostgreSQL `.ffffff`, SQL Server `.fff`, sem segundo, compacta, ISO básica, pt-BR, US 12h,
  epoch em segundos e em milissegundos.
- **2 — 8 regimes**, grafia fixa. Comercial (o do corpus), log de alta cardinalidade, batimento
  de 5 min e de 1 s, esparso multi-ano, um dia só, constante, e **comercial embaralhado**.
- **3 — a contra-prova de ordem**, isolada.

## Os 9 mecanismos, medidos ISOLADOS

O `encode()` público devolve só o **vencedor**. Para ver o comportamento, cada candidato é
invocado à parte e o wire de cada um fica gravado: `core`, `raw`, `bN`, `dict`, `split`,
`multi(_best_of)` — mais três transformações que hoje o dev faria à mão: `epoch-s`, `separado`
(data com `:dt` + hora em segundos) e `campos-6`.

## Estado — era / foi / é / será

- **Era**: o datetime tinha 4 números numa nota (7,13× o mais citado) e **nenhum lab**.
- **Foi**: o pedido de ver o comportamento por grafia e por forma de compressão.
- **É**: 21 colunas × 9 mecanismos, 0 falhas. **O split vive da ordem** (embaralhado ele passa
  de 842 a 6331 B); a grafia compacta e a de 12h **não splitam**; e há um regime em que o
  núcleo **infla 9,9%**. Resultado em [`result.md`](result.md).
- **Será**: o desenho de um mecanismo específico para datetime, na nota irmã.

## Ressalva de comparação, declarada

O `campos-6` **descarta a grafia** (decodifica para um dict de 6 colunas, não para as strings).
Ele **não é competidor do split** — é o **piso** dele, e a diferença medida é constante:
**28 bytes**, o custo do template. Está tratado assim no `result.md`, não como vitória.

## Como rodar

```
python run.py     # sai 0 só se todo mecanismo com RT definido fechar
```

**Não precisa de `Z:`** — este lab é inteiramente sintético, por decisão sua (*"nem é
necessário nesse momento"*). Não toca `src/tcf/`: os candidatos são funções existentes,
chamadas por import.

## Onde olhar

| arquivo | o que é |
|---|---|
| `casos.py` | as 13 grafias e os 8 regimes, com a ideia de cada um |
| `mecanismos.py` | os 6 candidatos isolados + as 3 transformações |
| `inputs/<caso>.entrada.json` · `.fonte.json` | a coluna e a procedência |
| `outputs/<caso>.<mecanismo>.tcf` | **o wire de cada candidato**, não só do vencedor |
| `intermediates/bloco3-contraprova.json` | a tabela ordenado × embaralhado |

## Vínculo

`T-DATETIME-TIPO` · `T-SPLIT-SINGLE-COL` (a ressalva de ordem é para ele) ·
`T-UM-CAMINHO-SO` (o caso em que o single-col infla) · `T-DATA-GRAFIAS-IRMAS` ·
ADR-0026 (split `%`) · ADR-0041 (`dtm` reservado, sem dono)

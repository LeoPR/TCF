# Resultado — 09-auditoria-self-contained-D11a

**Conclusao**: `D11a.tcf` (42 bytes) e' **AUTO-CONTAINED**.

## Procedimento

1. Decoder recebeu APENAS `input/D11a.tcf` (42 bytes)
2. Decoder usou algoritmo padrao (TCF.decode) + logica pre-tx
3. Auto-detectou natureza: {'type': 'date', 'granularity': 'day'}
4. Reconstruiu 12 linhas
5. Comparou com D11a-datas-dia.csv original
   Resultado: **BYTE-CANONICAL OK**

Decoder **NAO** recebeu:
- D11a.csv original (nunca viu)
- Metadata externo (JSON, sidecar, ...)
- Hint sobre natureza ou granularidade
- Count de linhas esperadas

## Conteudo do .tcf (42 bytes — tudo que e' necessario)

```
\2026-\05-\15
*4|\1
\3
*2|^2
\5
^2
\2
\14
```

## Audit trail: tecnicas aplicadas a D11a (em ordem inversa do encode)

### Camada 2 — TCF decode (OBAT + HCC, algoritmo compartilhado)

TCF.decode aplica:
- Parse linhas tipo `*N|<conteudo>` (RLE adjacente — N copias da linha)
- Parse `^N` como referencia ao N-esimo node de declaracao anterior
- Parse `\<digits>` como literal escapado pra evitar conflito com IDs

Resultado intermediario apos TCF.decode:

```
[0] '2026-05-15'
[1] '1'
[2] '1'
[3] '1'
[4] '1'
[5] '3'
[6] '1'
[7] '1'
[8] '5'
[9] '1'
[10] '2'
[11] '14'
```

### Camada 1 — Pre-tx inverso (Stage A → C → B inversos)

**Stage A (identify)** — Auto-deducao da primeira linha:
- Pattern: `YYYY-MM-DD` (regex match)
- Validacao: `date.fromisoformat('2026-05-15')` → OK
- Meta inferido: `{'type': 'date', 'granularity': 'day'}`

**Stage C inverso** — parse das escalas:
- Para D11a, nenhuma escala (`Y`, `M`) presente
- Todas as linhas (apos a primeira) sao integers em dias

**Stage B inverso** — acumulacao dos deltas:
- `current = 2026-05-15`
- `current += 1 dia(s)` → `2026-05-16`
- `current += 1 dia(s)` → `2026-05-17`
- `current += 1 dia(s)` → `2026-05-18`
- `current += 1 dia(s)` → `2026-05-19`
- ... (segue ate' o fim)

## Resultado final

- Bytes do .tcf: **42**
- Linhas reconstruidas: **12**
- Linhas no original D11a.csv: **12**
- RT byte-canonical: **OK**

## Implicacao

O arquivo `.tcf` carrega **dados + estrutura de refs**. O resto
(natureza, granularidade, semântica do delta) e' **auto-deduzido
pela primeira linha**. Algoritmo de decoder e' conhecimento
compartilhado (como `gunzip`).

Se em iteracoes futuras for necessario um **cabecalho explicito**
(ex: pra disambiguar quando first line nao da pra deduzir tudo),
ele tera que estar **DENTRO do .tcf** — em principio numa linha
de meta antes do base. Hoje nao precisa porque a inferencia
automatica e' suficiente pra D11a-h.

## Conexoes

- [decode_standalone.py](decode_standalone.py) — decoder isolado
- [`../08-granularidades-finas/`](../08-granularidades-finas/) — fonte do tcf-C.tcf
- [TCF algoritmo](../../../../../../docs/algorithms/) — OBAT + HCC docs

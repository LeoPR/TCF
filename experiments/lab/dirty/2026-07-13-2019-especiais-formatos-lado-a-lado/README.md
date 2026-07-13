# Lab 2026-07-13-2019 — especiais: FORMATOS lado a lado (dados realistas)

**Status**: pesquisa/medido — **material de decisão, SEM veredito**. **Ticket**:
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md) ·
**Plano**: [dataseth-hierarquia-completa-plano.md](../notas/dataseth-hierarquia-completa-plano.md) (P5-material)

Refeito a pedido do owner (2026-07-13): os labs anteriores provaram a SEMÂNTICA com
fixtures pobres; este mostra **os formatos com dados realistas** para a decisão —
entrada visível → fluxo semântico → arquivo de saída real por formato → roundtrip
explícito de volta ao original. Inclui o caso **tabular SEM hierarquia**: o problema
null/NaN/Inf independe de hierarquia.

## Entradas (em `inputs/` — abra e leia)

| entrada | o que é | irregularidades reais |
|---|---|---|
| `01-clientes-api.json` | cadastro aninhado, **JSON padrão** | `ultima_compra: null`; Diego **sem** `endereco`; Fabio `endereco: {}`; Carla `geo: {}`; Eva sem `geo`; `telefones` ragged 0–3 |
| `02-telemetria-jsonlike.json` | export Python real (`json.dumps` emite `NaN`/`Infinity`) — gramática **declarada** JSON+constantes | sensor falho → `NaN`; divisão por zero na origem → `Infinity`; estufa-04 sem `umidade` |
| sensores (tabular, tipado) | colunas Python/driver — **sem hierarquia** | `nan` float; `inf`; `-0.0` vs `0.0`; `obs` linha3=`"None"` string (upstream já stringificou) vs linha4=`None` null; linha5=`"nan"` string |

## Formatos comparados (saídas em `artifacts/03*`)

| entrada | formato | arquivo |
|---|---|---|
| hierárquicas | **A** per-instance (tag por ocorrência) | `03a/03b-*-A-per-instance.txt` |
| hierárquicas | **RH** regular (stream def+kind por coluna + payload `tcf.encode` **real**) | `03a/03b-*-RH-regular.txt` |
| tabular | **HOJE** (stringify + `tcf.encode` real — comportamento atual; perda explícita) | `03c-sensores-HOJE-stringify.tcf.txt` |
| tabular | **FK** (kind-channel por coluna + payload `tcf.encode` real) | `03d-sensores-FK-kind-channel.txt` |

Alfabeto de marcas (1 char/ocorrência; candidato em estudo): `s i d t f` (string/int/
decimal/true/false) · `z q p m` (null/NaN/+Inf/−Inf) · `a` array-presente ·
`0..9` = cut@i (só hierárquico). **FK usa o MESMO alfabeto sem os cuts** — a prova de
que o contrato de especiais é ortogonal à hierarquia.

## Como ler a evidência

1. `artifacts/01-sensores-tabular-entrada.txt` — a tabela tipada de origem.
2. `artifacts/02-fluxo-semantico.txt` — o kind por valor (ex.: `endereco.rua sss0s1`
   = Diego cut@0, Fabio cut@1; `ultima_compra szszsz`; `temperatura.media dqdd`).
3. `artifacts/03*` — os arquivos de saída (payloads comprimidos pelo motor REAL:
   `an*a*@acme…`/`brun*o3`, `*2|Sao Paulo`, seq-RLE `*5+1|…`, refs `^1`).
4. `artifacts/04-roundtrip.txt` — original vs decodificado (JSON gerado e linha a
   linha tabular); as PERDAS do caminho HOJE listadas explicitamente.
5. `artifacts/05-bytes.txt` — tamanhos.

## Rodar

```powershell
python experiments/lab/dirty/2026-07-13-2019-especiais-formatos-lado-a-lado/run.py
```

Zero mudança em `src/tcf` (uso read-only de `encode`/`decode` para payloads).
Ver [result.md](result.md) — comparação, **decisão é do owner**.

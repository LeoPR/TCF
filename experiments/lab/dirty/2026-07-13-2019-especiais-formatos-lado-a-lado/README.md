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
| `inputs/01-clientes-api.json` | cadastro aninhado, **JSON padrão** | `ultima_compra: null`; Diego **sem** `endereco`; Fabio `endereco: {}`; Carla `geo: {}`; Eva sem `geo`; `telefones` ragged 0–3 |
| `inputs/02-telemetria-jsonlike.json` | export Python real (`json.dumps` emite `NaN`/`Infinity`) — gramática **declarada** JSON+constantes | sensor falho → `NaN`; divisão por zero na origem → `Infinity`; estufa-04 sem `umidade` |
| `inputs/03-sensores-tabular.csv` | export stringly do upstream (origem TIPADA em `run.py`, renderizada em `intermediates/01`) — **sem hierarquia** | no CSV, `None`-null e `"None"`-string viram o MESMO texto (linhas 4–5); `nan`/`inf` soletrados; `-0.0` vs `0.0` |

## Estrutura (convenção de labs: pastas por estágio + extensão real)

```
inputs/          entradas (.json / .csv)
intermediates/   fluxo semântico, origem tipada, canônicos p/ diff (.txt / .json)
outputs/         saídas por formato (.tcf), roundtrips (.json), contraprova, bytes
```

## Formatos comparados (saídas em `outputs/`)

| entrada | formato | arquivo |
|---|---|---|
| hierárquicas | **A** per-instance (tag por ocorrência) | `01-clientes.A.tcf`, `03-telemetria.A.tcf` |
| hierárquicas | **RH** regular (stream def+kind por coluna + payload `tcf.encode` **real**) | `02-clientes.RH.tcf`, `04-telemetria.RH.tcf` |
| tabular | **HOJE** (o CSV stringly + `tcf.encode` real — comportamento atual; perda explícita) | `05-sensores.HOJE.tcf` |
| tabular | **FK** (kind-channel por coluna + payload `tcf.encode` real) | `06-sensores.FK.tcf` |

**Roundtrip como arquivo**: `outputs/07-clientes.roundtrip.json` e
`08-telemetria.roundtrip.json` são **byte-idênticos** aos canônicos em
`intermediates/03-04` (asserted; dê `diff` você mesmo). Tabular linha a linha em
`outputs/09-sensores.FK.roundtrip.txt`.

Alfabeto de marcas (1 char/ocorrência; candidato em estudo): `s i d t f` (string/int/
decimal/true/false) · `z q p m` (null/NaN/+Inf/−Inf) · `a` array-presente ·
`0..9` = cut@i (só hierárquico). **FK usa o MESMO alfabeto sem os cuts** — a prova de
que o contrato de especiais é ortogonal à hierarquia.

## Como ler a evidência

1. `intermediates/01-sensores-origem-tipada.txt` — a origem tipada (o CSV de
   `inputs/03` é o `str()` dela, asserted).
2. `intermediates/02-fluxo-semantico.txt` — o kind por valor (ex.: `endereco.rua sss0s1`
   = Diego cut@0, Fabio cut@1; `ultima_compra szszsz`; `temperatura.media dqdd`).
3. `outputs/01..06-*.tcf` — os arquivos de saída (payloads comprimidos pelo motor REAL:
   `an*a*@acme…`/`brun*o3`, `*2|Sao Paulo`, seq-RLE `*5+1|…`, refs `^1`).
4. `outputs/07-08-*.roundtrip.json` — diffáveis contra `intermediates/03-04-*-canonico.json`
   (byte-idênticos); `outputs/10-roundtrip-contraprova.txt` — asserts + PERDAS do HOJE
   listadas uma a uma; `outputs/09` — tabular linha a linha.
5. `outputs/11-bytes.txt` — tamanhos.

## Rodar

```powershell
python experiments/lab/dirty/2026-07-13-2019-especiais-formatos-lado-a-lado/run.py
```

Zero mudança em `src/tcf` (uso read-only de `encode`/`decode` para payloads).
Ver [result.md](result.md) — comparação, **decisão é do owner**.

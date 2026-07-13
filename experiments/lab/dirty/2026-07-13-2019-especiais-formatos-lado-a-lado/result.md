# Resultado — formatos lado a lado (material de decisão; SEM veredito)

**[probatório]** `run.py` valida todos os roundtrips ANTES dos bytes. Contra-prova em
[`outputs/10-roundtrip-contraprova.txt`](outputs/10-roundtrip-contraprova.txt); roundtrips
como ARQUIVO diffável (`outputs/07-08-*.roundtrip.json` byte-idênticos aos canônicos de
`intermediates/`); proveniência e viés declarados em
[`datasets-provenance.md`](datasets-provenance.md) (material de forma, não medida de ganho).

## Bytes (após RT verde)

| entrada | original | A per-instance | RH regular | HOJE stringify | FK kind-channel |
|---|---:|---:|---:|---:|---:|
| clientes (JSON padrão, 6 registros aninhados) | 1599 | 1379 | **932** | — | — |
| telemetria (JSON-like, 4 registros, NaN/Inf) | 1031 | 923 | **715** | — | — |
| sensores (tabular tipado, 6 linhas) | — | — | — | 235 *(lossy)* | 342 *(lossless)* |

## O que cada arquivo mostra (abra-os)

- **RH** (`outputs/02-clientes.RH.tcf`, `04-telemetria.RH.tcf`): schema por coluna +
  1 char/ocorrência + payload comprimido pelo **motor real** (OBAT/HCC/dict/seq-RLE:
  `an*a*@acme…`, `*2|Sao Paulo`, `*5+1|…`, `^1`). A linha `C endereco.rua sss0s1`
  conta a história inteira: 3 strings, Diego sem endereço (`0` = cut@0), Eva string,
  Fabio endereço vazio (`1` = cut@1). Menor que o JSON original nos dois casos.
- **A** (`outputs/01-clientes.A.tcf`, `03-telemetria.A.tcf`): estrutura repetida por
  registro; maior que RH em dado regular, mas não exige schema comum — serve árvore
  irregular/doc único.
- **HOJE** (`outputs/05-sensores.HOJE.tcf`): o menor arquivo — e **lossy**: `'None'`
  (string) e `None`(null) colidem; `nan`(float) e `'nan'`(string) soletram igual;
  TODO número vira string. Perdas listadas uma a uma em `outputs/10`.
- **FK** (`outputs/06-sensores.FK.tcf`): +107 B sobre HOJE (nesta tabela minúscula,
  6 linhas) para fidelidade total de tipo: `-0.0` ≠ `0.0`, `nan`/`inf` de volta como
  floats, `'None'` string ≠ `None` null (`outputs/09` linha a linha). O canal de kind
  é 1 char/célula (empacotável b4 depois — território V2-L); o custo relativo CAI com
  volume (payload domina).

## Fatos que a comparação estabelece (para a decisão)

1. **O contrato de especiais é ortogonal à hierarquia** — FK usa o MESMO alfabeto do
   RH sem os chars de cut. Decidir o alfabeto UMA vez serve flat e hierárquico.
2. **O caminho de hoje já paga um custo escondido**: HOJE é menor porque **descarta
   tipo** — quem consome precisa re-adivinhar (`'87.5'` é número? `'None'` é null?).
   O kind-channel torna o custo explícito e pequeno (1 char/célula).
3. **RH < JSON original** nos dois documentos realistas, mantendo payloads no motor
   real — a forma regular amortiza o schema, como previsto pelo grupo `#TCF.8H`.
4. **A vs RH não é disputa**: A cobre o irregular (sem schema comum); RH cobre o
   regular. São candidatos de `min()` por REGIME, com a MESMA semântica de kinds.

## O que isto NÃO decide

- A grafia final (`#TCF.8H`/gramática, textual vs packed) — decisão do owner (P5),
  agora com os arquivos na mão.
- Repetition levels completos (objeto-em-array na forma regular) — peça seguinte.
- Ganho em dado real de produção — gate ecológico antes de `confirmada-empirica`
  (isto aqui é forma, não medida de ganho).

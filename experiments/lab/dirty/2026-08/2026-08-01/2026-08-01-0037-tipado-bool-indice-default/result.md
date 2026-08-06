# T-TIPADO-BOOL-INDICE — slots congelados DEFAULT da tag `b` (2026-08-01-0037)

O denso b2 (ADR-0037, weld 2026-07-31) fechou o ternário DENSO, mas o candidato CORE/RLE seguia emitindo `true`/`false` como NOMES. Este lab mede o render em slots congelados — o MESMO domínio do b2: `null=0` (já era a grafia core), `false=1`, `true=2` — emitidos como `\1`/`\2` pelo `_escape_lit` de sempre. Decode: slots canônicos; nomes decodáveis-não-emitidos (contrato do modo `C`, ADR-0036).

## A — hoje (nomes) × slot, por coluna

| coluna | n | modo hoje | modo slot | hoje | slot | Δ | RT |
|---|---:|:-:|:-:|---:|---:|---:|:--|
| `bool-constante` | 200 | core | core | 18 | 16 | **-2** | OK |
| `run-heavy-1` | 200 | core | core | 30 | 25 | **-5** | OK |
| `runs-4` | 200 | core | core | 41 | 34 | **-7** | OK |
| `runs-10` | 200 | b1 | b1 | 47 | 47 | **+0** | OK |
| `alternado` | 200 | b1 | b1 | 47 | 47 | **+0** | OK |
| `alternado-null` | 200 | b2 | b2 | 79 | 79 | **+0** | OK |
| `tiny-constante` | 3 | b1 | core | 14 | 14 | **+0** | OK |
| `tiny-ternario` | 3 | b2 | b2 | 14 | 14 | **+0** | OK |

**Caso run-heavy confirmado**: `[True]*100+[None]+[False]*99` — o CORE vence o b2 nos DOIS renders (modo `core` hoje, `core` com slot): o b2 pagaria 79 B fixos, o core paga ~3 linhas de run. O slot economiza **-5 B** exatamente onde o b2 não alcança.

## B — colunas REAIS (Adult, ordenadas por grupo = run-heavy realista)

| coluna | n | modo hoje | modo slot | hoje | slot | Δ | RT |
|---|---:|:-:|:-:|---:|---:|---:|:--|
| `real-adult-sex-ordenado` | 100 | core | core | 27 | 22 | **-5** | OK |
| `real-adult-sex-ord-null` | 100 | b2 | b2 | 47 | 47 | **+0** | OK |
| `real-adult-class-ordenado` | 100 | core | core | 27 | 22 | **-5** | OK |

## C — adversidades

### 1. polaridade sobre corpo de slots

Varredura direta de `polariza` sobre os corpos-slot de **todas as 11 colunas** do lab: sufixo disparado em **0**.

E o resultado é **estrutural**, não amostral: com o render em slots o corpo bool tem **no máximo 2 linhas literais** (`\1` e `\2`, na primeira ocorrência de cada valor — o null viaja como slot `0`, que não é literal escapado). A polaridade cobra 1 B por transição literal↔referência e só compensa quando há muitas; com ≤2 literais as transições são ≤4 e o sufixo **nunca compensa**. Logo ela não pode nem ser escolhida nem quebrar RT num corpo de slots — a adversidade é inerte por construção.

### 2. seq-RLE sobre `1,2,1,2…`

O alternado puro (sem null) vai pro **b1** nos dois renders (modo `b1`) — o padrão `\1,\2,\1,\2…` nem materializa corpo. O alternado COM null vai pro **b2** (modo `b2`). Seq-RLE no corpo de slots do alternado: **ausente** — delta não-uniforme (1↔2) não dispara o `*N+delta`; e se disparasse e encolhesse mantendo RT, seria o FLOOR trabalhando.

### 3. legado — nomes decodáveis-não-emitidos

`'#TCF.8b\ntrue\nfalse\n^1\n'` → `[True, False, True]` — **OK**. Mesmo contrato do modo `C` (ADR-0036): wires antigos por nomes seguem lendo.

### 4. fail-loud no cast de slots

Evidência em `outputs/fail-loud.txt`:

```
[OK] `\0` (literal '0' (colide com o slot do null)) → ValueError: #TCF.8b: valor fora do dominio bool (slots 1/2): '0'
[OK] `\3` (slot 3 (reservado, como no b2)) → ValueError: #TCF.8b: valor fora do dominio bool (slots 1/2): '3'
[OK] `\15` (slot 15 (fora do domínio)) → ValueError: #TCF.8b: valor fora do dominio bool (slots 1/2): '15'
```

## Resumo e round-trip

- Δ somado nas colunas medidas: **-24 B**; slot menor em **5 de 11** (`bool-constante`, `run-heavy-1`, `runs-4`, `real-adult-sex-ordenado`, `real-adult-class-ordenado`).
- Onde o slot NÃO muda nada: os modos densos (`b1`/`b2`) — o corpo core nem materializa, o FLOOR escolhe o denso nos dois renders (Δ = 0, modo idêntico).
- Observação de empate: `tiny-constante` (n=3) passa de `b1` para `core` — o slot empata o core com o denso (14 = 14) e o FLOOR fica no 1º candidato (core, mais inspecionável). Byte-neutro.
- RT estrito (valor, tipo, comprimento) + roundtrip ARQUIVO byte-idêntico em todas as colunas, com assert no `run.py`.
- `src/tcf` intocado; os `-slot.tcf` são proposta (o decode público ainda não conhece os slots `1`/`2` no corpo tipado).


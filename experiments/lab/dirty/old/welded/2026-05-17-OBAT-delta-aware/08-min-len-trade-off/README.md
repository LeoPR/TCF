# Sub-exp 08 — min_len trade-off study (H-DA-10)

**Data**: 2026-05-17
**Estado**: ativo
**Macro pai**: [`../README.md`](../README.md)
**Hipotese**: H-DA-10

## Hipotese a validar

**H-DA-10**: Existe trade-off entre OBAT criar refs longos (reduz
overhead inicial) vs nao criar refs (deixa HCC seq-RLE livre).
Pode ser controlado via parametro `min_len` do OBAT.

D16a (strings curtas) mostrou: SEM refs (min_len > LCP), HCC fork
seq-RLE compactou TUDO em 1 linha (-83% vs baseline).
D11d (strings longas) mostrou: COM refs + OBAT shape-preserve,
maior ganho (-45% vs baseline).

## Pergunta

Pra cada dataset, qual min_len da melhor compressao?

## Teste

Variar `min_len` ∈ {2, 3, 4, 5} em pipeline canonical OBAT + HCC
fork seq-RLE. Datasets selecionados:
- **D16a** (3-char IDs) — esperado: min_len>=3 ja' nao cria refs
- **D11d** (19-char datetime) — esperado: min_len=3 otimo
- **D9** (wrapper `@@@KEY=valueX@@@`) — caso onde hint H-DA-07
  ajudou muito (sub-exp 06); ver se min_len influencia

Reportar bytes por (dataset, min_len). RT obrigatorio.

## Aceite

- **Confirmada** se: pelo menos um dataset tem ganho >= 10 bytes com
  min_len != 3 (default)
- **Refutada** se: min_len=3 e' otimo ou empate em todos

## Caveats

- Mudar min_len pode quebrar canonical M9 baseline. Testar so' como
  parameter sweep, NAO altera default.
- min_len=2 pode causar refs muito pequenos (overhead alto).
- Maximo min_len = comprimento minimo das strings - 1.

## Estrutura

```
08-min-len-trade-off/
├── README.md
├── run.py        (sweep min_len em D16a, D11d, D9)
├── summary.md
└── result.md
```

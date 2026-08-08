# O custo da ambiguidade de data

**2026-08-08 · dirty · exploratório** · só **data** (sem hora)

```
python run.py     # 4 casos, n=480; exit ≠ 0 se algum RT quebrar
```

## A pergunta

> *"a ambiguidade só gera problema de compressão, não de encode/decode"* — é verdade? E
> **quanto** custa?

O lab constrói colunas **100% ambíguas por construção** (dia **e** mês ≤ 12, onde `DD/MM` e
`MM/DD` são leituras igualmente válidas) e encoda cada uma três vezes: **ignorando** (string
pura, o que o TCF faz hoje), com o spec **certo**, e com o spec **errado**.

| prova | o que decide |
|---|---|
| **integridade** | os três têm de fazer RT byte-exato. Se o errado falhar, a tese cai |
| **compressão** | a diferença certo × errado **é** o custo da ambiguidade |
| **FLOOR** | `min(errado, ignorar)` — o que sai se o spec for **candidato**, não substituto |

## Como achar pelo nome

```
inputs/        <caso>--<higiene>.input.json     o dado + se sobrevive a round-trip JSON
intermediates/ <caso>--<spec>.trilha.json       por onde passou no codec (SideOutputs REAL)
                                                → olhe `deltas_uniformes`: é ali que a
                                                  regularidade aparece ou some
outputs/       <caso>--ignorar.tcf              sem spec (hoje)
               <caso>--certo-br.tcf   + .roundtrip.json
               <caso>--errado-us.tcf  + .roundtrip.json
               medicoes.md                      as tabelas
```

`<caso>` ∈ `consecutivo-no-mes` · `consecutivo-no-mes-espelhado` · `ambiguo-sem-ordem` ·
`ambiguo-k12`

## Os achados

- **8 de 8 encodes com RT byte-exato**, incluindo todos os de spec errado. **A tese está
  certa: ambiguidade custa bytes, não integridade.**
- **O custo não é constante** — é proporcional à regularidade destruída: **+497%** onde havia
  sequência, **0,0%** onde não havia.
- **Com FLOOR o prejuízo é ZERO** — nunca pior que hoje em nenhum caso, e em 2 de 4 o palpite
  errado ainda ganha.
- O mecanismo está na telemetria: leitura certa = 40 corridas com delta `[1]`; errada = 239
  corridas com deltas `[-334,-333,20,28,29,30]`. A leitura errada **estilhaça a corrida**.

Análise completa das quatro formas (ignorar / orientar / multi-padrão / aceitar) em
[`result.md`](result.md).

`src/tcf` **não é tocado**.

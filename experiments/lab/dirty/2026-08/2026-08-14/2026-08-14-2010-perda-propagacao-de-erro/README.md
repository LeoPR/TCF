# A perda por cinco lentes — propagação de erro em dado real

> **Owner (2026-08-14)**: *"quanto ao loss, ainda precisa de estudo, talvez fazer ficar
> orientado à estatística de perdas e erros ajudaria. Por exemplo, se a perda significa algo
> como 1% numa soma ou multiplicação? não só pelo valor em si, mas se eu passar algo que seja
> financeiramente, ou fisicamente coerente arredondar dentro de alguma margem dentro da
> realidade, com justificativas em várias áreas."*

**Uma pergunta**: a mesma perda, medida por lentes diferentes, dá o mesmo número?

**Resposta curta: não, e a diferença é de ordens de grandeza.** Ver [`result.md`](result.md).

## Este lab tem um contrato diferente dos outros

Aqui o valor por linha **muda de propósito**. Então o RT contra a origem não se aplica, e no
lugar dele valem duas checagens:

1. **o contrato declarado** — a soma fica exata? o erro por linha cabe?
2. **o formato continua lossless sobre os valores já arredondados** — `decode(encode(x̂)) == x̂`.
   A perda tem de ser do *round*, nunca do TCF. **O PoC de junho não fez esta checagem**
   (importou `decode` e nunca chamou), e por isso seus bytes saíram sem §RT. Aqui: 10/10.

⚠️ Os `.tcf` deste lab contêm **valores arredondados de propósito**. O `roundtrip.json` prova
que o formato os preserva — **não** que são os originais. O original está em
`inputs/retail-preco.entrada.json`.

## GATE

Tudo aqui é **medição**, nunca proposta. O formato é lossless-puro por decisão do owner
(2026-06-15); qualquer perda exige gate real-world N≥5 e decisão explícita. `src/tcf` intocado.

## Estado — era / foi / é / será

- **Era**: o loss era declarado por **casas decimais** (`H-LOSS-03`, V2-C), e o PoC de junho
  media bytes e drift da soma — uma lente só, e sem §RT.
- **Foi**: o owner pediu que a perda fosse orientada ao que ela **significa**, por área.
- **É**: 5 lentes × 5 precisões × 2 métodos, 0 falhas. A soma dilui 640×, o produto **não
  dilui**, e a diferença de próximos **amplifica até 825%** com 40% de troca de sinal.
- **Será**: o vocabulário de 4 eixos + `mode` (nota irmã) precisa virar contrato declarável
  antes de qualquer weld — é o `H-LOSS-00`.

## Por que `online-retail` e não `wine`

Porque precisa de **duas** colunas para haver um produto derivado real: `UnitPrice × Quantity`
é receita, uma quantidade que alguém de fato lê. Medir propagação num produto sintético seria
medir a aritmética, não o dado.

## Como rodar

```
python run.py     # sai 0 só se o formato preservar os arredondados em todos os casos
```

Precisa de `Z:` (o lab é sobre dado real com duas colunas). Não toca `src/tcf/`.

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/retail-preco.entrada.json` · `retail-quantidade.entrada.json` | **os originais** |
| `inputs/d<N>-<método>.entrada.json` | os valores já arredondados |
| `outputs/d<N>-<método>.tcf` · `.roundtrip.json` · `.meta.json` | wire, prova, procedência |
| `outputs/margem-d<N>.derivada.json` | as margens derivadas — onde o sinal troca |
| `intermediates/cinco-lentes.json` · `cancelamento.json` | as medições, com `CONSTANTE_na_comparacao` |

## Vínculo

`H-LOSS-00` (vocabulário) · `H-LOSS-01` (maior resto) · `H-LOSS-03` (round, o PoC de junho) ·
`H-LOSS-02` (DERIVED-DROP — a consequência da subtração) ·
[`loss-taxonomia.md`](../../../notas/2026-06/loss-taxonomia.md) ·
nota [`…-2010`](../../../notas/2026-08/2026-08-14-2010-rle-intra-valor-e-perda-estatistica.md) ·
irmão: [`…-2010-rle-intra-valor-medida`](../2026-08-14-2010-rle-intra-valor-medida/)

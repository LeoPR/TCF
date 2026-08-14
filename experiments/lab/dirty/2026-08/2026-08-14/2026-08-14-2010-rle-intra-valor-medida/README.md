# RLE intra-valor — a primeira medição da H-INTRA

> **Owner (2026-08-14)**, reabrindo a própria ideia de 2026-06-16:
> *"itens repetidos no meio do texto… `0.30000000000000004` poderia ser `0.3(14x0)4`… ou ainda
> pra aproveitar o fluxo: `14x0` / `\0.3 <ref-01> 4` — um 'RLE fantasma' que descomprime só pra
> preencher dicionário, não coloca no conteúdo de fato. Veja se é simples ou arriscada."*

**Uma pergunta**: o núcleo já aproveita repetição de caractere **dentro** de um valor? Se não,
quanto sobra — e onde isso existe em dado real?

## Estado — era / foi / é / será

- **Era**: `H-INTRA-01/02/03` (Pacote 11) e `O-FMT-17` estavam **abertas desde 2026-06-16**, com
  o caso do owner (`111.111.111-11` tem `111.` 3×) — mas **nunca houve lab**. A única coisa
  medida era o inchaço por escape (14 → 18 chars).
- **Foi**: o owner reabriu com duas grafias concretas e pediu análise de risco.
- **É**: 4 blocos, 0 falhas. Resultado em [`result.md`](result.md). O núcleo captura **zero**
  run intra-valor; a curva é **1,000 B por char repetido**; e o **`*0|` já produz o "RLE
  fantasma" hoje, sem guarda**.
- **Será**: continua adiado — agora com número. O pré-requisito é `H-REF-03` (alfabeto por
  complemento), não a grafia. O `T-RLE-COUNT-ZERO` segue independente.

## Por que o Bloco 3 inverte o fluxo

Nos outros blocos o JSON é a entrada e o `.tcf` a saída. No Bloco 3 é o contrário: os wires são
**escritos à mão** em `inputs/*.wire-de-entrada.tcf`, porque a pergunta não é o que o encoder
produz — é **o que o decoder aceita**. A saída é o JSON decodificado.

Isso importa porque o achado é justamente que o encoder canônico **nunca emite** essas formas
(testado em 9 tipos de entrada) e mesmo assim o decoder as aceita.

## Dois defeitos, e de quem

| defeito | onde apareceu | correção |
|---|---|---|
| colapsar o run com `¤` (**2 bytes** em UTF-8) inflava o "teto de 5 chars" para 10 B | **meu**, 1ª rodada deste lab | char ASCII ausente da coluna, por complemento |
| a contra-prova do `o_clerk` (**−2,31%, custa**) **não reproduziu** — medido aqui ele ganha 1,70% | levantamento anterior ao lab | vale a tabela do `result.md`; a contra-prova real é o `c_name` |

## Como rodar

```
python run.py     # sai 0 só se todos os RT fecharem
```

Roda **sem `Z:`** (o Bloco 4 é pulado). Não toca `src/tcf/`.

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<caso>.entrada.json` · `.fonte.json` | o dado e a procedência |
| `inputs/f*.wire-de-entrada.tcf` | **os wires do fantasma, escritos à mão** |
| `outputs/<caso>.tcf` · `.roundtrip.json` · `.meta.json` | wire, contra-prova, procedência |
| `outputs/f*.decodificado.json` | o que o decoder devolveu para cada fantasma |
| `outputs/r*.teto-marcador{3,5}.tcf` | o wire do teto idealizado |
| `intermediates/medicoes.json` | as 4 medições com `CONSTANTE_na_comparacao` |

## Vínculo

`H-INTRA-01/02/03` · `O-FMT-17` · `H-REF-03` · **`T-RLE-COUNT-ZERO`** (aberto por este lab) ·
[`rle-familia-estudo.md`](../../../notas/2026-06/rle-familia-estudo.md) ·
nota [`…-2010`](../../../notas/2026-08/2026-08-14-2010-rle-intra-valor-e-perda-estatistica.md) ·
irmão: [`…-2010-perda-propagacao-de-erro`](../2026-08-14-2010-perda-propagacao-de-erro/)

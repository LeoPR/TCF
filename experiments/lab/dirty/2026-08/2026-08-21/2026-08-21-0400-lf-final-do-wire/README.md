# 2026-08-21-0400 — o `\n` final do wire: terminador, não convenção de arquivo

Pergunta do owner:

> *"lembrando que o tcf, em termos de arquivo, precisa do `\n` no final pois se não me engano é
> coisa da formatação para esse tipo de arquivo. só confirme. já um `\n` no final na transmissão
> pode ser verificado para dispensar, salvo se tiver algum valor vital na comunicação. eu acho
> que não."*

## Resposta curta

**Sim, ele é necessário — mas não pelo motivo que a intuição sugere.** Não é convenção POSIX de
arquivo de texto: é o **terminador do último valor**, num formato em que o LF **separa valores**.
E **não dá para dispensar na transmissão**: ele tem valor vital, sim.

A convenção documentada dizia o contrário, e estava errada. Corrigida.

## A prova, em uma linha

```
['a', 'b', '']   ->  '#TCF.8\na\nb\n\n'
['a', 'b']       ->  '#TCF.8\na\nb\n'
```

O wire da coluna que **termina em valor vazio** é exatamente o wire da coluna sem o vazio,
**mais um LF**. Logo, tratar o LF final como opcional obrigaria o decoder a **adivinhar** se o
último vazio é enchimento ou dado — **indecidível por construção**.

Uma coluna pode legitimamente terminar em `''`. Enquanto isso for verdade, o LF final é dado.

## O que o código faz, nas 10 rotas

A convenção prometia "decoder deve aceitar **com ou sem**". **Nenhuma das 10 rotas cumpre:**

| rota | emite LF? | decode **sem** ele | decode **com um a mais** |
|---|---|---|---|
| single-col flat / spec / n=1 | sim | tolera, **com warning** de grafia não-canônica | **ganha um valor vazio**, em silêncio |
| multi-col | **não** | ok | `ValueError` |
| multi-col n=1 | **não** | ok | ganha valor vazio |
| hierárquico (array e objeto) | sim | **`HierarchicalError`** (`size N excede o corpo … blob truncado?`) | erro |
| tipado bool | **não** | ok | `ValueError` |
| tipado int / misto | sim | tolera com warning | `ValueError` |

Duas leituras:

- **Dispensar o LF na transmissão quebra o `.8H`.** No hierárquico ele delimita o último bloco;
  sem ele o decode acusa blob truncado. No single-col é tolerado, mas perde a canonicidade.
  O ganho seria de **1 byte por wire** (3,5% neste conjunto de 10 wires minúsculos — mas eles
  são pequenos de propósito; num wire real é ruído).
- **Acrescentar um LF "por educação"** ao gravar é pior: em single-col e multi-col isso
  **acrescenta um valor vazio à coluna, sem erro e sem warning**. É a classe silenciosa.

**Regra prática**: grave e transmita **exatamente os bytes que o `encode` devolveu**.

## O que fica aberto (H-15-08)

**Quais rotas emitem o LF final não é uniforme** — 7 emitem, 3 não. Isso é assimetria de
implementação, não regra declarada em lugar nenhum. E o warning do single-col (*"corpo
single-col sem o LF terminador canônico… a forma canônica termina em `\n`"*) sugere que
existe uma noção de forma canônica que as outras rotas não seguem.

Não mexi nisso: uniformizar mudaria bytes de wire em 3 rotas, o que é decisão de formato.

## O que foi corrigido

`docs/algorithms/output-convention.md` §3 — o parágrafo que dizia *"o último byte PODE ser `\n`
[...] é opcional. Decoder deve aceitar com ou sem"*. O texto antigo fica citado no bloco de
correção, porque **portar o formato seguindo ele quebra o decode**.

## Não medido (declarado)

- O custo do LF em wire de tamanho realista (aqui os 10 wires somam 202 B de propósito).
- Se alguma rota do `.8M`/`.8H` mudaria de bytes ao uniformizar a emissão.
- CRLF: coberto pela §2 da mesma convenção, não retestado aqui.

## Evidência

[`run.py`](run.py) com G1–G5 e asserts (o G5 afirma `wa == wb + LF`). 30 arquivos em
[`inputs/`](inputs/)+[`outputs/`](outputs/) com roundtrip; portão anti-órfão.
[`resultado.json`](resultado.json) com a matriz das 10 rotas.

## Conexões

- Doc corrigida: [`output-convention.md`](../../../../../../docs/algorithms/output-convention.md) §3
- **H-15-08** no [registry](../../../notas/2026-05/roadmap-hipoteses.md) (a assimetria que fica aberta)
- Vizinho: [`0330-bordas-em-spec`](../2026-08-21-0330-bordas-em-spec/) — o LF **dentro** do valor
  (H-15-07), este lab é o LF **no fim do wire**

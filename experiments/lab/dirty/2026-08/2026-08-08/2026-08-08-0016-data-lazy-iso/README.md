# Data lazy (spec ISO) — a fatia mais barata

**2026-08-08 · dirty · exploratório**

```
python run.py     # 19 casos, n=500; exit ≠ 0 se algum RT quebrar
```

## Recorte

O owner pediu pra escolher: *"prefiro matar algo que dê mais retorno e seja mais fácil"*.
Escolhido: **só o spec ISO**, per-valor, no molde exato da nature do CPF. Os outros formatos
são o mesmo objeto com outro `fmt` — não precisam de decisão nova, precisam de medição.

## A filosofia, que é a do CPF

> *"converte, mas se tiver algo estranho, só finge que não viu e deixa em raw"*

É literalmente o que a `natures/templated_checked.py` faz:

```
classify_value(v)  ->  'compressible' | motivo
encode_value(v)    ->  não-compressível vira MARKER_LITERAL + v   (+1 byte)
decode_value(p)    ->  se começa com o marker, devolve o resto
```

O que muda pra data: não há dígito verificador. A validação é estrutural, e o alvo da
transformação é o **ordinal**, porque é ele que alcança o `*N+M|` do seq-RLE — medido no lab
[`2026-08-07-2311`](../../2026-08-07/2026-08-07-2311-datas-exploracao/): 120 datas diárias
saem de 97 B para 22 B.

## As três perguntas

| | resposta |
|---|---|
| **1. Quanto rende limpo?** | até **−99,5%** (`limpo-mensal`: 4856 → 23 B) |
| **2. A que ponto a sujeira mata o ganho?** | **não mata** — com 50% de lixo o lazy ainda ganha 3,1% |
| **3. O RT sobrevive a dado sujo, misturado e ambíguo?** | **19 de 19**, incluindo spec errando 100% |

A (3) é a que decide a viabilidade. As outras duas dizem se vale a pena.

## O achado de design

**A ambiguidade BR × US não precisa ser resolvida.** A transformação tem de ser
*inversível*, não *correta*: chute errado custa bytes (+4,9% no pior caso medido), nunca
dado. Isso rebaixa "olhar os primeiros valores" de requisito de correção para otimização de
bytes — uma heurística que pode errar à vontade.

Detalhe e a avaliação crítica completa da direção em [`result.md`](result.md).

## Os casos

| grupo | casos |
|---|---|
| limpo | diário · mensal · espalhado |
| sujeira crescente | 1% · 2% · 5% · 10% · 25% · 50% de valor que não parseia |
| sujeira real | null · string vazia · misto ISO+BR · tudo BR |
| ambiguidade | só dias 1..12 (BR e US indistinguíveis) |
| grafia | `2026-1-01` — parseia mas não é canônica |
| calendário | bissexto · 29/02 inexistente · virada de ano · ano 1 e 9999 |

## Arquivos

- [`spec_data.py`](spec_data.py) — o spec e a pré-tx (protótipo **fora** do `src/tcf`)
- [`run.py`](run.py) — os casos, as medições, o relatório
- [`result.md`](result.md) — achados + avaliação crítica da direção
- [`outputs/medicoes.md`](outputs/medicoes.md) — as tabelas
- `outputs/*--hoje.tcf` e `*--lazy.tcf` — os dois wires de cada caso, diffáveis

`src/tcf` **não é tocado**.

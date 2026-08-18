# 2026-08-17-1000 — o CEP decomposto

## O erro que este lab corrige

No levantamento anterior tratei o CEP como **8 dígitos opacos** e medi só empacotamento de
raiz. O owner apontou: *"o cep segue regras fora dele, ele tem uma lógica de construção…
existem regiões, estados, formatos para ele existir, ou seja, ele pode ser decomposto.
pelo que vi vc olhou o cep meramente como números."*

O erro tinha **duas metades**, e a segunda é pior que a primeira:

1. ignorei a **estrutura** — o CEP decompõe em partes de natureza diferente;
2. gerei o sintético com dígitos **uniformes**, o que **destrói justamente a localidade**
   que torna a decomposição lucrativa. Medir CEP aleatório é medir um número que não existe.

## A estrutura (Correios, verificado 2026-08-17)

```
N N N N N - N N N
│ │ │ │ │   └─┴─┴─ SUFIXO, com FAIXAS SEMÂNTICAS:
│ │ │ │ │            000-899 logradouros · 900-959 códigos especiais
│ │ │ │ │            960-969 promocionais · 970-989,999 unidades dos Correios
│ │ │ │ │            990-998 caixas postais comunitárias
│ │ │ │ └────────── divisor de subsetor
│ │ │ └──────────── subsetor
│ │ └────────────── setor
│ └──────────────── sub-região
└────────────────── REGIÃO postal (10, anti-horário a partir de SP)
```

Os 5 primeiros dígitos são uma **hierarquia encaixada** — cada nível subdivide o anterior
em 10. Numa base real os dígitos de alta ordem têm cardinalidade baixíssima; os de baixa
ordem aproximam-se do uniforme.

## Onde mora a entropia (medido, n=5000)

| | reg | sub | set | sse | div | sf1 | sf2 | sf3 | prefixo | sufixo |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **regional** (1 região) | **0,00** | 2,28 | 1,77 | 3,32 | 3,32 | 3,31 | 3,32 | 3,32 | 10,70 | 9,95 |
| **estadual** (3 regiões) | **1,39** | 2,94 | 2,83 | 3,32 | 3,32 | 3,31 | 3,32 | 3,32 | 13,80 | 9,95 |
| **nacional** (10 regiões) | 3,31 | 3,14 | 3,21 | 3,32 | 3,32 | 3,31 | 3,32 | 3,32 | 16,30 | 9,95 |

*(bits; máximo 3,32 = log₂10)*

**A hierarquia aparece exatamente onde a construção diz que deveria.** Os três primeiros
dígitos carregam a geografia e desabam quando a base é concentrada — `reg` vai a **zero**
numa base regional. Do `sse` em diante tudo satura em 3,32: é ruído uniforme, e nenhuma
decomposição vai extrair o que não há.

**O sufixo é 9,95 bits em todos os cenários** — não 9,97 (=3×3,32). A diferença é pequena
mas é real: as faixas semânticas (94% logradouro) tiram um pouquinho da uniformidade.

## As decomposições

Baseline **D1** = o que o TCF faz hoje (o `split` quebra no hífen).

| estratégia | regional | estadual | nacional |
|---|--:|--:|--:|
| D0 opaco (8 dígitos) | +54,3% | +25,4% | +0,1% |
| **D1 mascarado (hoje, `split`)** | **0,0%** | **0,0%** | **0,0%** |
| D2 prefixo+sufixo (2 colunas) | −0,1% | −0,1% | −0,1% |
| D3 hierárquico (6 colunas) | +20,1% | +11,7% | **−10,8%** |
| **D4a delta+sort** (ordem não-semântica) | **−56,5%** | **−54,8%** | **−51,8%** |
| D4b idem, pagando a permutação | −33,3% | −35,9% | −36,7% |

### O que cada linha ensina

- **D0 é o que eu media antes, e é o pior de todos.** Tratar o CEP como número opaco
  chega a custar **+54%** contra o que o TCF já faz. A medição anterior estava ancorada
  na estratégia errada.
- **D2 não acrescenta nada (−0,1%).** O `split` **já faz** a separação prefixo/sufixo — ele
  quebra na máscara. Uma "nature de decomposição posicional" seria redundante com o que
  existe. Resultado negativo, e é resultado.
- **D3 depende do cenário e inverte de sinal.** Separar em 6 colunas paga overhead por
  coluna: **piora 20%** quando a base é concentrada (o `split` já resolvia) e **ganha 10,8%**
  quando é nacional (aí há entropia real em cada nível para o `dict` explorar).
- **D4 é o achado.** O delta sobre a coluna ordenada ganha **~52–56%** — e não é acidente:
  a hierarquia do CEP **implica ordem**, então CEPs vizinhos geograficamente são vizinhos
  numericamente, e o delta fica minúsculo.

### A ressalva do D4 — que quase me escapou

Ordenar **uma** coluna quebra o alinhamento das linhas. Isso só vale se a **tabela inteira**
for reordenada junto, que é o que o `sort_by=` do `encode` faz — verificado:

```python
t = {'cep': ['30110-002','01310-100','20040-030'], 'nome': ['Ana','Bruno','Carla']}
decode(encode(t, sort_by='cep'))
# {'cep': ['01310-100','20040-030','30110-002'], 'nome': ['Bruno','Carla','Ana']}   <- o nome ACOMPANHA
```

É lossless como **conjunto de registros**, **não** como sequência: `decode(...) != t`.
Daí os dois números:

- **D4a** — a ordem das linhas **não** é semântica (cadastro, dump de tabela): o `sort_by` é
  de graça e o ganho é **−52 a −56%**.
- **D4b** — a ordem **é** semântica: paga a permutação, `log₂(n!)` = **6779 B** para n=5000.
  **Ainda ganha −33 a −37%** — e esse é o *piso* teórico da permutação; guardá-la de verdade
  custa mais.

## O contraste que denuncia o erro anterior

| | H total | H do prefixo | core |
|---|--:|--:|--:|
| uniforme (ruído com hífen) | 26,57 bits | 16,60 | 9,00 B/valor |
| realista (estadual) | 23,75 bits | **13,80** | 7,18 B/valor |

Gerar uniforme **apaga a hierarquia**: o prefixo fica tão caro quanto o sufixo, e a
decomposição não tem o que explorar. Era exatamente o que eu media.

## O que isto muda no encaminhamento

O levantamento anterior concluiu "nature de empacotamento de raiz, −24,1%, destino `.9`".
Com a estrutura na mesa:

1. **Empacotamento de raiz (D0) é a estratégia errada para o CEP.** Ele perde para o `split`
   que já existe. O −24,1% medido no telefone **não transfere** para o CEP.
2. **A decomposição posicional já está feita** — é o `split`. D2 = −0,1%.
3. **O que sobra é ordem**, não decomposição: o `sort_by` já existe na API e vale
   −52 a −56% quando a ordem não é semântica. **Isso não é nature nenhuma** — é um knob
   que já está lá e ninguém mediu para CEP.

## Não alcançado (declarado)

- **Todo dado é sintético.** Não há coluna de CEP em `Z:/tcf-data` (varredura do
  levantamento anterior: 6 hits de telefone, **0 de CEP**). O gerador respeita a construção,
  mas **a distribuição real de uma base brasileira não foi observada** — os pesos de região
  e as faixas de sufixo são plausíveis, não medidos.
- **As faixas oficiais por UF não foram obtidas** — as fontes consultadas põem a tabela
  atrás de formulário. O lab usa a **região** (que a fonte dos Correios confirma) e não
  afirma limite de UF.
- **A redundância cross-coluna não foi medida** (D5 no plano, não executado): se a tabela
  tem uma coluna UF, o prefixo do CEP é largamente **derivável** dela. Isso é um mecanismo
  diferente de tudo acima — dependência entre colunas, que o TCF não explora hoje.
- **Só bytes.** Nada de CPU, e o `sort_by` tem custo de ordenação não medido.

## Conexões

- Estrutura: [Correios — Tudo sobre CEP](https://www.correios.com.br/enviar/precisa-de-ajuda/imagens/tudo-sobre-cep)
- Levantamento que este lab corrige:
  [`notas/2026-08-17-0900`](../../../notas/2026-08/2026-08-17-0900-o-que-falta-pro-8-e-cep-telefone.md)
- `ROADMAP.md:87` (FILTROS-POPULARES, alvo `.9`) · `STATUS.md:482` (o "CEP → nenhuma ação" de 2026-06-16)

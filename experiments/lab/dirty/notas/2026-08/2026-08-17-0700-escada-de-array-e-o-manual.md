# 2026-08-17 — a escada de array (custo por nível) e o check do manual

**[probatório]** Dois checks pedidos pelo owner. Nenhum vira conserto agora: o primeiro é
**registro de custo conhecido**, o segundo é **verificação de viabilidade**.

---

## 1. A escada de array — o owner leu certo, e é caso sintético

> *"o bloco no tcf ficou fazendo referências de referenciar pra mostrar o nível… me dá a
> sensação de gastar muito só pra representar os níveis"*

### O que o wire realmente diz

`escada_array_d8.tcf` (94 B), lido:

```
[ 0] '#TCF.8Ha#:6[#:6[#:6[#:6[#:6[#:6[#:6[#:6['
[ 1] '*2|\1'      <- x8
[ 9] '*2|x'
```

Não é "referência de referência". `*2|` é **RLE** (2 linhas idênticas adjacentes — as duas
do dataset) e `\1` é o **dígito 1 escapado**: a *contagem* de itens daquele nível.

### O custo, decomposto

| | por nível |
|---|--:|
| header — o token `#:6[` | **+4 B** |
| corpo — a **coluna de contagem** (`*2|\1`) | **+6 B** |
| **total** | **+10,0 B/nível**, constante (medido d=1→32) |

**O ponto que fica**: num nível *singleton* a contagem é **sempre 1** — inteiramente
dedutível da estrutura — e mesmo assim é materializada. Isso contraria
[materialização-minimal] em princípio: *grava só o estritamente necessário, o resto deduz*.

### Por que não vale otimizar (o owner já suspeitava)

Comparado ao JSON compacto, nos dois eixos:

| profundo-e-estreito (a escada) | | | largo-e-raso (o caso real) | | |
|---|--:|--:|---|--:|--:|
| **d** | **tcf** | json | **n itens** | **tcf** | json |
| 1 | 24 | 25 | 2 | 33 | 37 |
| 2 | 34 | 29 | 8 | **52** | 97 |
| 8 | **94** | 53 | 32 | **160** | 381 |
| 32 | **334** | 149 | 128 | **586** | 1589 |

O TCF **perde** para o JSON a partir de d≈2 na escada, e **ganha 2,7×** no largo-e-raso.

A escada é uma forma que **não ocorre**: array singleton reaninhado 8 níveis não é dado,
é teste de resistência — foi construída exatamente para isso (lab `0600`, achar o teto de
128). Dado real aninha **largo**: uma lista de telefones, itens de pedido, tags. Aí o
mecanismo de contagem paga por si, porque a contagem varia e carrega informação.

**Decisão registrada**: não otimizar. Custo conhecido (10 B/nível), forma não-realista,
e o mecanismo que "desperdiça" aqui é o mesmo que ganha 2,7× no caso que importa. Se
algum dia aparecer corpus com singleton-nesting profundo, a saída natural seria **omitir a
coluna de contagem quando ela é constante-1** — mas isso é um candidato a mais no `min()`
da folha, e cai no mesmo balde do
[`0400`](../../2026-08/2026-08-17/2026-08-17-0400-o-candidato-unico-do-H/).

---

## 2. O manual — dá para ir montando? **Dá, e o material já está sendo produzido.**

> *"o manual é a superfície de uso e também das capacidades… apenas ver se a gente
> consegue ir montando"*

### O molde já existe

[`docs/reference/familia-bn-bits.md`](../../../../docs/reference/familia-bn-bits.md) é a
forma certa e está **verificada**: na varredura adversarial de 2026-08-17, os 14 wires e as
8 chamadas de `view` dele foram executados — **todos batem**. Ele é o doc mais confiável do
repo. O que o faz funcionar:

- cabeçalho **"Estado: preliminar"** honesto — descreve o soldado-e-medido, não promete
- links pras ADRs que decidiram, e pro EXP que contraprova
- exemplo com **wire real colado** logo na abertura
- seção explícita **"O que ainda não está aqui"**

### O buraco

O `.8H` **não tem página**. A gramática dele vive espalhada em 5 menções:

| onde | o que cobre |
|---|---|
| `api.md:34` | a linha de dispatch (`#D`/`#E`/`#O`/`#V`) |
| `api.md:97,152` | um exemplo de null-em-dict |
| `json-equivalence.md:68` | um exemplo de raiz-objeto |
| `TCF-format.*` (1 linha) | `#TCF.8H<tree-meta>` na tabela de discriminadores |

Nenhum lugar diz **como o meta se escreve**: `?:` máscara, `#:` contagem, `{` aninhado,
`\z` chave vazia, último campo sem size.

### O material já está pronto, nos labs

O que uma página `hierarquico-h.md` precisaria já foi produzido e **conferido**:

| seção da página | fonte pronta |
|---|---|
| gramática, produção por produção | [`0500`](../../2026-08/2026-08-17/2026-08-17-0500-header-do-H-sintetico/) — 15 casos mínimos, wire + RT em disco |
| limites (profundidade 128, largura, escapes) | [`0600`](../../2026-08/2026-08-17/2026-08-17-0600-limites-de-profundidade-do-H/) |
| o que roteia pro `.8H` (40 formas) | retrato do H, workflow `wf_091c3b09-c1d` |
| fronteira / o que recusa | [`json-equivalence.md`](../../../../docs/reference/json-equivalence.md) |
| "o que ainda não está aqui" | candidato único ([`0400`](../../2026-08/2026-08-17/2026-08-17-0400-o-candidato-unico-do-H/)) · folha tipada grava texto (`0500`) · custo da escada (esta nota) |

**Conclusão do check**: sim, dá para ir montando — e o modo de montar já está acontecendo.
Cada lab mínimo com wire + roundtrip em disco **é** a pré-anotação da página. O que falta é
só o passo de colher: quando o `.8H` fechar, a página se escreve a partir dos labs, sem
medição nova.

**Não é prioridade agora** (instrução do owner). Registrado para quando for.

## Conexões

- [`0400`](../../2026-08/2026-08-17/2026-08-17-0400-o-candidato-unico-do-H/) ·
  [`0500`](../../2026-08/2026-08-17/2026-08-17-0500-header-do-H-sintetico/) ·
  [`0600`](../../2026-08/2026-08-17/2026-08-17-0600-limites-de-profundidade-do-H/)
- Registro de limites: [`0630`](2026-08-17-0630-limites-de-hierarquia-registro.md)
- Molde do manual: [`familia-bn-bits.md`](../../../../docs/reference/familia-bn-bits.md)

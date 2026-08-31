---
title: "Onde a view ganha, e o quanto: o custo medido por operação"
type: explanation
parent: desempenho
subsystem: view
---

# Onde a `view` ganha, e o quanto

> Medições que estavam dentro da referência da `view` e não são contrato: elas descrevem o
> que foi medido, e o número muda quando o encoder muda. O contrato de cada chamada está em
> [`docs/reference/lazy-view.md`](../../reference/lazy-view.md); o princípio que explica por
> que a consulta é barata está em [`custo-da-consulta.md`](../conceitos/custo-da-consulta.md).

Não existe um "ganha / não ganha": existem graus, e o grau depende do modo em que a coluna
foi comprimida, de quão larga é a tabela, e de qual chamada você faz. A escala, do mais
barato ao mais caro:

| grau | o que faz | valores construídos |
|---|---|---|
| **header** | responde sem abrir o corpo | 0 |
| **estrutura compacta** | conta separadores, índices de largura fixa ou marcadores core sem reconstruir valores | 0 |
| **K únicos** | constrói só os valores distintos | K |
| **K + compacto** | constrói os K e percorre o stream de índices **sem expandir** | K |
| **uma coluna** | constrói as N linhas de uma coluna | N |
| **várias colunas** | uma coluna por chamada no encadeamento | N x tocadas |

A linha "K + compacto" é a que passa despercebida. Numa coluna dicionário um `where`
percorre as N posições do stream, mas cada posição é um índice de largura fixa, não um
valor: ele lê a forma compacta e nunca a expande. Ler tudo não é o mesmo que materializar
tudo.

### Por operação e modo

Medido em n=2000:

| operação | `@dict` | denso (`b`/`B`/`C`) | `%split` | core |
|---|---|---|---|---|
| `count`, `nrows` | **estrutura compacta** | **header** | uma coluna | **estrutura compacta** |
| `n_unique` | **K únicos** | uma coluna | uma coluna | uma coluna |
| `distinct` | **K únicos** | uma coluna | uma coluna | uma coluna |
| `where` | **K + compacto** | uma coluna | uma coluna | uma coluna |
| `group_count` | **K + compacto** | uma coluna | uma coluna | uma coluna |
| `sum`/`min`/`max`/`avg` | uma coluna | uma coluna | uma coluna | uma coluna |
| `group_sum` e família | duas colunas | duas colunas | duas colunas | duas colunas |
| `select(col)` | uma coluna | uma coluna | uma coluna | uma coluna |

O `count` numa rota densa sai direto do header: a contagem de linhas está escrita ali em
hex, então ele lê 11 ou 12 bytes e para. No modo core, soma os contadores e as linhas
soltas do corpo compacto; não reconstrói a coluna. Só uma tabela inteira em `split` não
tem contagem estrutural e decodifica a menor coluna.

A contagem estrutural inclui as linhas vazias. Um corpo core de uma única string vazia
conta como uma linha, e o `select()` a devolve.

Em que modo cada coluna cai é decisão do encoder, não sua, e ela é tomada só por bytes. O
`fallback=True` (o default do 0.8) é o que põe colunas de baixa cardinalidade em `@dict`, e
portanto o que habilita a coluna `@dict` inteira da tabela acima; ver
[encode-knobs.md](../../reference/encode-knobs.md). No `.8H` cada coluna usa o pipeline core sem essa
competição, então o blob fica 38,3% maior na mesma tabela de 2 000 linhas por 5 colunas e
nada cai em `@dict`.

### A largura da tabela muda a resposta

O `select` de uma coluna constrói sempre N valores, mas o que importa é a fração da tabela
que isso representa:

| colunas na tabela | `select("c")` | `select()` |
|---:|---:|---:|
| 2 | 50,1% | 100% |
| 5 | 20,0% | 100% |
| 10 | 10,0% | 100% |
| 20 | **5,0%** | 100% |

Então chamar o `select` de "materializa" é meia verdade. Ele materializa **uma** coluna, e
numa tabela larga é aí que está quase toda a economia.

### O encadeamento não reduz o que vem depois

Este é o limite honesto, e vale dizer com todas as letras porque a intuição diz o
contrário. Filtrar antes e agregar depois **não** deixa a agregação mais barata:

```
where(f, "sim").count()             2000 valores construídos
where(f, "sim").sum("v")            4000
where(f, "sim").group_count("g")    4000
where(f, "sim").group_sum("g", "v") 6000
```

Esses números são idênticos quer o filtro guarde 1% ou 100% das linhas. O filtro corta as
linhas **depois** de a coluna ter sido materializada, não antes. Fazer o filtro estreitar o
trabalho a jusante exige ler só as posições filtradas, coisa que o stream de largura fixa
do dicionário permitiria; está medido e registrado para o `.9` (`H-QUERY-04f`).

### A versão curta

Uma tabela com uma coluna de baixa cardinalidade e várias largas é o formato para o qual a
view foi feita: a coluna do filtro responde pela estrutura, e o resto nunca é tocado. Uma
tabela de uma coluna só, de alta cardinalidade, é o formato em que `view()` e `decode()`
custam quase o mesmo, e o honesto é dizer isso.

Este é o retrato do `.8`. Os protótipos que subiriam `group_*` e os agregadores na escala
estão medidos e registrados para o `.9`.

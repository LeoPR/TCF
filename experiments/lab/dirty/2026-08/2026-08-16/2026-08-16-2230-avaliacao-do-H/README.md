# Avaliação do `.8H` — gramática, header, estágios duplicados e o candidato único

> **Owner (2026-08-16)**: *"vamos avaliar o modo H, pois a estrutura de header dele é
> ligeiramente diferente. Faça o de sempre: primeiro estudo do que se tem das últimas
> atualizações das capacidades do H, e o foco de sempre do `.8` — ver pra simplificar o
> header, ver integração dos estágios internos que estejam repetidos ou que podem ser
> simplificados para generalizar, opções e tudo mais."*

## O veredito curto

**O header do `.8H` não é o problema — é 0,11% do wire.** O problema é o **candidato único**,
e ele vale **+23% do corpus**, agora confirmado em 23 tabelas (antes era uma só).

E o estudo prévio achou uma **defasagem documental**: o `tcf8h-header-checklist.md` (2026-07-06)
descreve o **protótipo pré-weld** e diz *"nada disto está weldado ainda"*. O weld (ADR-0033)
emitiu uma gramática com **cinco coisas a mais** — tags de tipo, máscara `?`, e os marcadores
de raiz `#O`/`#V`/`#E`.

## Os quatro achados

**1. A gramática real tem 10 glifos** — dois herdados do `.8M` (`:N`, `,`) e sete exclusivos
(`{}`, `[`, `#`, `?`, `#O`, `#V`, `#E`). Todas as 14 capacidades testadas fecham RT.

**2. O header é ruído**: 2.943 B de 2.777.913 B = **0,11%**. Mesma conclusão do `.8M`
(O-FMT-11, fechado). Os nomes são 61% dele — o único campo grande, e cortá-lo tem o preço de
sempre.

**3. O candidato único explica 99,99% do overhead, no corpus inteiro.** Residual de **69 B** em
520.044. Amplitude por tabela: 0% (`region`) a **+113%** (`wine-quality`).

**4. Os três estágios duplicados divergem — e a divergência é CORRETA.** `_esc_name`,
`_unesc_name` e `_parse_meta` existem nos dois módulos com o mesmo nome e código diferente;
o `hierarchical.py` **não importa nada do `multi`** e o comentário admite *"portado do `.8M`"*.
Mas cada rota escapa a **sua** gramática: só o `.8M` escapa `=`, só o `.8H` escapa `{}[]?#`.
RT fecha nas duas com 13 nomes hostis.

> **Unificar o alfabeto seria um bug.** O que cabe unificar é o **mecanismo** — um escapador
> parametrizado. É `.9` (legibilidade para o port), não ganho de byte.

## A reordenação que isto provoca

O `T-META-NAO-DECLARA-MODO` (B1) era tratado como gate de um item de **2,3%** (o Grupo A no
`.8M`). **Mas o `.8H` precisa exatamente da mesma coisa e ali vale +23%** — dez vezes mais.

E o `.8H` tem vantagem estrutural para isso: o meta dele **já declara por folha**
(`nome:size` + tag de tipo), então o slot onde o modo entraria **já existe na gramática** —
diferente do `.8M`, onde o marcador precisa vir antes do size e esbarra no alfabeto seguro.

## Como rodar

```
python run.py    # sai 0 só se os RTs fecharem e as medições de estrutura baterem
```

Precisa de `Z:/tcf-data/interim/` (somente leitura). `src/tcf` intocado.

## A ressalva mais importante

O `.8H` está sendo medido em dado **retangular**, que é onde ele é mais desfavorecido. Com
aninhamento real ele representa o que a tabela plana não representa e a comparação deixa de
existir. **Os +23% são o custo de usar o `.8H` onde o `.8M` daria conta** — não o custo do
`.8H` no domínio dele.

## Vínculo

`T-8H-UM-CANDIDATO-SO` (confirmado em corpus aqui) · `T-META-NAO-DECLARA-MODO` (reordenado) ·
`T-UM-CAMINHO-SO` · `T-8H-SEM-SPEC-OUT-OF-BAND` · ADR-0031 (disc `H`) · ADR-0033 (o weld) ·
`tcf8h-header-checklist.md` (**defasado** — descreve o protótipo) ·
[`2130`](../2026-08-16-2130-auditoria-do-M-no-corpus/) (a auditoria irmã, do `.8M`) ·
[síntese do mês](../../README.md)

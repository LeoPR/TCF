# ADR-0048 — A união bool+str é capacidade da família **single**, e a assimetria é deliberada

- **Status**: **aceito** (2026-08-31, decisão do owner ao fechar a cauda do `.8`). Ratifica o
  que já está soldado; **nenhuma mudança de wire**.
- **Ratifica**: a rota `#TCF.8bB` do [ADR-0039](0039-lazytype-bool-cabeca-congelada-extras.md),
  que une bool e string numa coluna do single-col.
- **Fecha**: a divergência #1 da auditoria das três famílias (2026-08-27), que a nota
  `2026-08-28-decisoes-de-dono-cauda-do-8.md` deixou aguardando decisão.

## O fato

Uma coluna que mistura `bool` e `str` **entra** no single-col e **é recusada** nas outras duas:

```python
encode([True, "texto", False, None, "outro"])   # '#TCF.8bB35\ntexto\noutro\n=TIg'
encode({"c": [True, "x"]})                      # HierarchicalError: tipos escalares MISTOS
encode([{"c": True}, {"c": "x"}])               # HierarchicalError: tipos escalares MISTOS
```

O round-trip do single é exato, e a `view` alcança os extras de string desde a 0.8.3.

## A decisão

**Manter a assimetria, e declará-la.** Ela não é acidente nem dívida: é uma capacidade que a
família single tem e as outras não, do mesmo jeito que o `.8H` tem hierarquia e o `.8M` não.

As duas alternativas foram medidas e **não** foram escolhidas:

- **proibir no single**, para uniformizar por baixo: quebra 12 testes e joga fora uma
  capacidade que funciona, para comprar simetria que ninguém pediu;
- **estender ao `.8M` e ao `.8H`**, para uniformizar por cima: exige wire de duas famílias
  dentro de uma coluna e uma tag de coluna nova. É mudança de formato, e o dado não a
  justifica: **união real medida é ~0 no hub, 1 coluna em 165**.

Fica registrada como **hipótese do `.9`/`2.0`, gatilhada por dado real**: se a união aparecer
em corpus de verdade, a extensão volta à mesa com evidência, e não por simetria estética.

## Por que isso importa mais do que parece

Sem esta decisão escrita, a assimetria **parece defeito**. Alguém que a encontra tem de
escolher entre dois erros: ou reporta como bug o que é escolha, ou uniformiza por conta
própria e paga um dos dois custos acima. Uma capacidade não declarada é indistinguível de uma
inconsistência, e é a declaração que faz a diferença.

## O que a mensagem de erro passa a fazer

O fail-loud do `.8M` e do `.8H` **ensina a rota que aceita**, em vez de só recusar. Isso já
entrou na 0.8.3: a mensagem descreve as duas saídas e o que cada uma perde (separar por tipo
preserva valor e tipo mas exige guardar a posição; converter tudo para string preserva a ordem
e faz round-trip da coluna convertida, não da original).

## Consequências

- o wire não muda, e nenhum baseline se move;
- a família single passa a ter uma capacidade **documentada** em vez de tolerada;
- a extensão às outras famílias fica bloqueada por falta de dado, e não por falta de decisão;
- quem precisa da união numa tabela tem a rota: a coluna vai como single-col própria.

## Ver também

- [ADR-0039](0039-lazytype-bool-cabeca-congelada-extras.md): a mecânica da rota `bB`
- [ADR-0027](0027-nature-mark-header-self-describing.md): o mesmo princípio noutro eixo, o de
  não inferir o que o dado não declara

# Inteiro: a matriz tipagem × spec

> **Owner (2026-08-13)**: *"porque os números estão como string em tudo? o json tem que
> colocar numeros como numeros, lembra da tipagem? […] se a fonte é inteiro (como era
> boleano) e por algum motivo entra como string no dataset antes de entrar no tcf, se colocar
> um spec inteiro, o tcf internamente trata como inteiro, mas se o dataset estava string,
> então realmente volta string. se o dado era int […] ele entra int, o spec é int, o tcf trata
> internamente como int, e devolve int. e assim por diante, fizemos isso com data, com bool, é
> a historia do semantico tipo."*
>
> E na correção seguinte: *"o caso de entrada string e spec int **também é válido**, mas o lab
> só tem isso."*

## Estado — era / foi / é / será

- **Era**: o lab das 22h58 mediu inteiro **só com fonte string**, e concluiu que um spec faz
  sentido em três regimes. A conclusão não está errada — está **incompleta**.
- **Foi**: a correção acima. Não há caso primário e secundário: são **dois eixos**, ambos
  legítimos, com contratos de round-trip **diferentes** (um devolve grafia, o outro devolve
  valor).
- **É**: este lab cobre a matriz — 14 regimes × 4 células, 0 falhas, round-trip conferido com
  **tipo**. Resultados em [`result.md`](result.md). Três achados: a tipagem custa **+1 byte
  em todos os 14 regimes e não entrega otimização**; a célula `int+spec` **não é expressável
  em nenhuma das três rotas**; e os dois eixos dão respostas **diferentes** (em ids
  aleatórios o eixo int ganha mais).
- **Será**: decidir se o spec de int vive nos dois eixos, e como encaixar spec na rota tipada
  — o desenho do **bool** é o modelo pronto (a tabela congelada de `tipos_internos.py` já é
  um spec semântico embutido na rota tipada).

## Como rodar

```
python run.py     # regenera inputs/, intermediates/, outputs/ e resultado.json
```

Sai 0 só se todos os round-trips fecharem. `src/tcf` **não é tocado**.

Os três alvos (PAD, B94, OFFPAD) são **importados** do lab das 22h58, não copiados — mesma
investigação, mesmo dia, uma fonte só para a definição.

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<r>.entrada-int.json` · `.entrada-str.json` | os **mesmos** valores nas duas fontes |
| `inputs/<r>.fonte.json` | procedência + o que ficou CONSTANTE na comparação |
| `intermediates/<r>.matriz.json` | as 4 células com bytes, header, RT — e as **recusas literais** de cada rota |
| `outputs/<r>.int-core.tcf` · `.str-core.tcf` · `.str-spec.tcf` | os wires |
| `outputs/<r>.int-core.roundtrip.json` | contra-prova da rota tipada |
| `outputs/INDEX.md` | a matriz em tabela |

## Ressalvas

- A coluna `int+spec` é **simulada** — a célula não existe na API. O número é o custo do
  corpo transformado + header tipado + tag, com round-trip verificado à mão. A simulação
  **não passa pelo FLOOR**, então reporta o custo cru, inclusive quando é pior; a coluna
  "com FLOOR" mostra o que o usuário veria.
- Dirty: conclusão **orientativa**. Sintético controlado isola o mecanismo; falta medir a
  frequência dos regimes em corpus real.

## Vínculo

`T-NUMERO-SPEC` · ADR-0015 (natures) · ADR-0036 (bN) · ADR-0037/0038/0039 (denso, índice
tipado, lazytype bool — o precedente do "semântico tipo").
Lab anterior (fonte string): [`…-2258-int-spec-faz-sentido`](../2026-08-13-2258-int-spec-faz-sentido/).

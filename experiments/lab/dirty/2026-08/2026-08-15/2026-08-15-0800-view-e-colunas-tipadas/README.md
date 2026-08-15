# O `view` e as colunas tipadas

> **Owner (2026-08-15)**: *"investigue o view agora, mas antes só veja se tem alguma pendência
> das tipagens e se todas estão organizadas e com fluxo consistente, ou seja, nada de conexões
> por fora demais."*

> ⚠️ **CORREÇÃO DE SEQUÊNCIA — owner, logo depois deste lab**: *"acho que a gente atravessou,
> pois o view só pode ser revisado com single column, a gente ainda tem que arrumar o M e o H.
> o lazy é por último."*
>
> **Este lab foi rodado fora de ordem.** A ordem é: tipos (fechados) → **arrumar o `.8M` e o
> `.8H`** → lazy/`view` por último. O que salva o lab é que **a medição já apontava para lá**:
> o §3 mostra que o custo é do **envelope `.8H`**, não do `view` nem da tipagem. Ou seja, ele
> não é um lab de `view` — **é um lab de `.8H` com título errado**, e o número que ele produz
> (+101,7% de envelope em tabela retangular) é insumo do trabalho de M/H, não do de `view`.
>
> **Não use o §7 como plano.** As duas saídas que ele lista são decisão de M/H, e a escolha
> pertence àquele trabalho, não a este.

O `view` estava adiado explicitamente até "fechar todos os tipos". Os tipos fecharam (date,
hora, float, datetime, int, bool). Este lab responde a pergunta que ficou — e descobre, no
caminho, que ela não era uma pergunta sobre o `view`.

## O gap que este lab fecha

O `T-LAZY-BYPASS-ARITMETICO` já mapeou — e prototipou — o lado **single-col** do `view`
(*"dispatch-only, ~20-25 linhas"*). O lado **`.8H`** nunca foi medido, e é exatamente lá que a
tabela tipada mora.

## Estado — era / foi / é / será

- **Era**: "falta o view para colunas tipadas", tratado como trabalho no `view`.
- **Foi**: medir onde a coluna tipada realmente vai parar, antes de propor qualquer coisa.
- **É**: o `view` abre **2 de 10** formas (só `.8M`); `_tabela_flat` exige `str` em todo valor,
  então **qualquer coluna tipada → `.8H` → `view` recusa**. O custo é **+101,7%** de bytes e
  **5,3×** de tempo — e a contra-prova mostra que **o custo é o ENVELOPE, não a tipagem**
  (envelope +78.134 B; tipagem **−416 B**). Resultado em [`result.md`](result.md).
- **Será**: decisão de design — dar gramática de tipo ao `.8M` (resolve acesso **e** bytes) ou
  ensinar o `view` a ler `.8H` (resolve só o acesso). É o `T-UM-CAMINHO-SO` outra vez.

## A predição declarada antes de rodar

1. o `view` abre `.8M` e recusa o resto — **confirmada** (2 de 10);
2. tipar UMA coluna muda a rota e fecha o `view` — **confirmada**;
3. o custo em bytes é do **envelope**, não da tipagem — **confirmada**, e é a que decide de
   quem é a culpa (se falhasse, o culpado seria a tipagem e a conclusão seria outra).

## Achado colateral que não esperava

`where(col, lambda ...)` **posicional** devolve **0 calado** (o lambda vira `value` e cai no
`v == value`); só `pred=` funciona. Resposta de consulta **errada, sem erro**. Eu caí nela
escrevendo este lab — o que é o argumento de que o usuário cai.

## Como rodar

```
python run.py     # sai 0 só se os RTs das 3 variantes fecharem e o where(pred=) bater com o decode
```

**Sem `Z:`** — tabela sintética determinística (`random.Random(11)`). `src/tcf` intocado.

## Onde olhar

| arquivo | o que é |
|---|---|
| `run.py` | 4 blocos, com a predição declarada no docstring |
| `inputs/tabela.entrada.json` · `.fonte.json` | a tabela e a procedência |
| `outputs/forma-*.tcf` | **o wire de cada uma das 10 formas testadas** |
| `outputs/tabela-{M-todo-string,H-todo-string,H-2-tipadas}.tcf` | as 3 variantes da contra-prova |
| `outputs/INDEX.md` | a tabela navegável |
| `resultado.json` | tudo, incluindo `falhas: []` |

## Vínculo

`T-LAZY-BYPASS-ARITMETICO` (o lado single-col, já prototipado) · `T-LAZYTYPE-OUTROS` ·
`T-UM-CAMINHO-SO` (a causa: dois caminhos internos; o `view` é 1 dos 4 sintomas nomeados) ·
`T-NATURE-IGNORADA-CALADA` (mesma família da armadilha do §5) · `T-DATA-TIPADA-NATIVA`
(o inventário da porta de entrada) · ADR-0029 (discriminadores) · ADR-0032 (legado cortado)

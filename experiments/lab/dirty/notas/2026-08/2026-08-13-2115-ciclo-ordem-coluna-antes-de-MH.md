# Ciclo de avaliação: a coluna primeiro, e M/H como consequência

**2026-08-13** · o owner rejeitou a mudança de ordem que propus, com dois argumentos:

> *"se mexer em M/H agora, e depois mexer nos números e algo alterar, pode ser que impacte em
> revisão do M/H novamente. por isso deixei o M/H pra depois. vc pensa muito em compressão, eu
> penso em fluxo que funciona. se atender apenas uma coluna, o resto é consequência não?"*

Avaliei os dois. **Os dois procedem, e o segundo é verificável — verifiquei.**

---

## 1. A tese "atender a coluna, o resto é consequência" — medida

Peguei um spec de inteiro sintético (12 linhas, zero-pad para largura fixa) e apliquei nas
três rotas **sem tocar em M nem em H**:

| rota | sem spec | com spec | |
|---|---:|---:|---|
| single-col | 36 B | **28 B** | 1,29× |
| multi `.8M` | 655 B | **644 B** | 1,02× — `#TCF.8Mf=n:xint,@x` |
| `.8H` | 733 B | — | **decode falhou** |

Para single e multi a tese se confirma **literalmente**: o tipo entra uma vez, e a rota
composta o carrega. O `.8H` falhou por um motivo já identificado na auditoria de streaming —
`decode_hierarchical(tcf_text)` não recebe spec, então spec **out-of-band** não é legível lá.
Specs **do registry** atravessam os três (o `data-iso` já faz isso: medido no lab de inspeção,
caso `d2-hierarquico`).

**Conclusão**: para o caminho real — spec soldado no registry — a tese vale nas três rotas.
O gap do `.8H` afeta só spec de terceiro, e vira ticket próprio.

## 2. Por que minha proposta estava errada (e era pior do que o owner apontou)

Eu ia propor "fazer a rota multi consultar o candidato denso". Olhando o código, os dois
conjuntos de candidatos são **quase disjuntos**:

| | candidatos |
|---|---|
| single-col (porta pública) | core polarizado · bN de domínio · tipado/denso (`#TCF.8b1`, `bB`) · nature |
| multi (`_best_of`, `multi/core.py:420`) | `_encode_column` cru · raw · dict `@` · split `%` · nature |

Cada um cobre o que o outro não cobre — e isso explica os números que medi:

| coluna | single | `_encode_column` cru | na tabela | leitura |
|---|---:|---:|---:|---:|
| bool nativo | 112 B | 1404 B | 1433 B | o gap é **100% candidato ausente** |
| categoria k=5 | 342 B | 1742 B | 639 B | o multi **ganha** do core cru (tem `dict`) |
| uf k=6 | 331 B | 1740 B | 628 B | idem |

Ou seja: **o multi não está "mal feito"** — ele tem candidatos próprios que o single não tem.
O problema é a duplicação da decisão em dois lugares. Minha proposta (levar o denso para o
multi) **aumentaria** a duplicação: o mesmo candidato mantido em dois lugares, e todo tipo
novo teria de ser registrado duas vezes. É exatamente o retrabalho que o owner quis evitar,
elevado ao quadrado.

É a mesma solda dupla que o `T-UM-CAMINHO-SO` já descreve — e que o owner já tinha posto
"depois dos tipos", pela razão certa.

## 3. Sobre "você pensa muito em compressão, eu penso em fluxo que funciona"

Procede, e o erro tem nome: eu ordenei a fila por **ganho de bytes por unidade de esforço**,
tratando ordem de construção como se fosse escolha livre. Não é — há dependência. Otimizar um
compositor (M/H) antes de fechar as peças que ele compõe convida à revisão dupla, e o custo
disso não aparece em nenhuma medição de bytes.

O critério certo para o `.8` já estava escrito no pedido do owner: *"funcionalidades, specs, e
que tudo ao menos construa corretamente e de forma minimalista"* — o `.9` é que é de
performance. Eu apliquei critério de `.9` numa decisão de `.8`.

## 4. Ordem revisada (volta a ser a do owner)

1. **Número** como spec — 1,9× a 3,0× medidos nos regimes de progressão e largura fixa; dois
   precedentes soldados para copiar (padding do IP, base94 do CPF). Entra uma vez, atravessa
   single e multi de graça.
2. **`T-DATA-GRAFIAS-IRMAS`** — `YYYYMMDD` e datetime, 2 das 10 colunas reais. Fecha data.
3. Demais tipos até o conjunto estar completo.
4. **`T-UM-CAMINHO-SO`** — unificar a decisão de candidatos. Feito **depois**, absorve todos os
   candidatos de uma vez e M/H herdam tudo junto. Feito **antes**, unificaria um conjunto
   incompleto.
5. **M e H** propriamente — com os tipos fechados e o caminho único, boa parte já terá vindo
   de graça; sobra o que for genuinamente estrutural (o gap de spec out-of-band no `.8H`, o
   layout colunar, os sizes do meta).

O `T-BAIXA-CARD-EM-TABELA` (5× a 12,8×) **continua real e grande** — só muda de lugar: não é
item de M/H, é sintoma da solda dupla, e some junto com o item 4.

## 5. Ticket novo

**`T-8H-SEM-SPEC-OUT-OF-BAND`**: `decode_hierarchical(tcf_text)` não recebe spec, então spec
fora do registry não é legível em `.8H` — enquanto single e multi aceitam `nature=` /
`nature_per_col=`. Medido acima. Pré-existente (a auditoria de streaming já verificou que é
idêntico no commit anterior). Só afeta spec de terceiro; specs welded atravessam.

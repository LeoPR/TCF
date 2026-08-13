# Single-col é convenção humana — no código, um multi-col de UMA coluna

**Data**: 2026-08-12
**Tipo**: direção arquitetural registrada (estudo; **não acionável agora** — vem depois
dos tipos, por decisão do owner)
**Origem**: owner, ao decidir o que fazer com o dispatch single-col no `view` —
*"eu vejo o single-col só como uma convenção humana; no código ele tem que ser algo perto
de um multi-column que tem apenas uma coluna, ou seja, o código é o mesmo pra um ou mais.
A gente até agora está apenas avaliando e fixando UMA coluna, mas depois que terminarmos
os tipos, vamos avançar pra ver as questões de multicolumn e hierarquia."*

---

## A tese

Uma coluna e N colunas não são casos diferentes — **é o mesmo caso com N=1**. O que hoje
separa "single-col" de "multi-col" é conveniência humana (uma lista é mais simples de
escrever e de ler que um dicionário de uma chave), não uma diferença estrutural do dado.

**Consequência de projeto**: o código deveria ser **um caminho só**, parametrizado por N.
Hoje são dois, e é por isso que eles divergem.

## A evidência — todas as divergências desta rodada são o mesmo sintoma

Não é especulação: as quatro coisas que esta sessão achou têm a mesma forma — *uma
capacidade existe num caminho e não no outro*.

| divergência | quem tem | quem não tem | ticket |
|---|---|---|---|
| **bN de domínio** no `min()` por coluna | single-col flat | `.8M` (**13,8%** na mesa no adult-census) | `T-BN-MULTICOL` |
| **split estrutural `%`** como candidato | `.8M` | single-col flat (**−35%/−63%** onde venceria) | `T-SPLIT-SINGLE-COL` |
| **`view` lazy** abre a rota | `.8M` (8 variantes) | **nenhuma** das 11 formas não-M | `T-LAZY-BYPASS-ARITMETICO` |
| **rota plena** (polaridade + bN) no candidato da nature | rota flat | rota da nature (~5,7% real) | `T-NATURE-CANDIDATO-BN` |

Quatro tickets abertos, quatro *classes* diferentes na aparência — **uma causa só**: um e
muitos são caminhos de código separados, então cada mecanismo novo precisa ser soldado
duas vezes, e na prática é soldado uma.

É a mesma classe que o projeto já nomeou cinco vezes como *"o candidato existe e a rota
não o consulta"*. A tese do owner explica **por que** ela reincide: enquanto houver dois
caminhos, a rota que não foi tocada fica para trás.

## O que isso NÃO quer dizer

- **Não** é unificar a API. `encode(["a","b"])` e `encode({"c": [...]})` continuam sendo
  as duas formas que o dev escreve — a conveniência humana é real e fica.
- **Não** é mudar o formato. O wire single-col (`#TCF.8`) e o `.8M` são grafias
  diferentes por bons motivos já registrados (ADR-0029/0030/0032/0034), e o single-col
  **congela no 1.0** (ADR-0030).
- A tese é sobre o **caminho interno**: o que decide candidatos, aplica camadas e escolhe
  o `min()` deveria ser um só, com N=1 como caso particular.

## O que fica para o estudo

1. **Onde exatamente os caminhos se separam hoje** — `encoder.py` (`_lista_flat` × o
   dispatch de dict) e `multi/core.py`. Mapear o ponto de bifurcação e o que cada lado
   ganhou desde então.
2. **O custo de N=1 pelo caminho multi**: hoje `.8M` paga meta por coluna; um `.8M` de
   uma coluna é maior que o single-col. Unificar o *código* não pode custar bytes no
   wire — o wire continua escolhendo a grafia melhor.
3. **A ordem certa**: unificar primeiro e depois soldar os 4 tickets (uma vez cada), ou
   soldar os 4 e unificar depois (duas vezes cada, mas sem bloqueio)?
4. **Hierarquia** (`#TCF.8H`) entra na mesma pergunta — é "multi-col de multi-col", e
   hoje é um terceiro caminho.

## Sequenciamento (decisão do owner)

**Depois dos tipos.** O ciclo atual está fixando **uma** coluna: os tipos, os specs, os
alvos. Só quando isso fechar é que se avança para multi-col e hierarquia — e é aí que
esta tese vira trabalho, não nota.

Até lá, os 4 tickets acima seguem como estão (cada um pagável isolado); esta nota existe
para que, quando forem atacados, se pergunte antes: **"isso é mais uma solda dupla?"**

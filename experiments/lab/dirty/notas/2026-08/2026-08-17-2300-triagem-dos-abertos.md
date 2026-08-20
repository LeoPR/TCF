# 2026-08-17 — triagem dos abertos: ganho × facilidade

Pedido do owner antes de revisar o H-13-03. **Aterrada em sondagem**, não em palpite — três
dos itens foram resolvidos ou medidos durante a própria triagem.

## Resolvidos DURANTE a triagem (custo zero)

### F5 — RESPONDIDO: o gate real é global por coluna

`split.py`, no `_struct_split_encode`:

```python
sig = tuple(toks0[::2])              # o template do 1o valor
for v in values[1:]:                 # varre TODOS os valores da coluna
    if len(t)//2 != nf or tuple(t[::2]) != sig:
        return None                  # template NAO-uniforme -> nao splita (gate 100%)
```

**É global por coluna, não por registro.** O mock dos labs 2100/2200 estava certo por
construção. **F5 pode ser fechado como não-risco** — vira registro, não trabalho.

### `drop_names` no sub-table — FUNCIONA, e estava disponível o tempo todo

A [nota 1400](2026-08-17-1400-split-teoria-e-o-magic-aninhado.md) deixou como pendência
*"não testei se o `_encode_multi` do split aceita esse flag hoje"*. Aceita:

```
como é hoje          100 B   meta='#TCF.8M@2b=c0,@c1'
com drop_names=True   95 B   meta='#TCF.8M@2b,@'        rt=True
```

**−5 B, sem tocar no decoder** — e o decode devolve chaves posicionais `'0','1'`, que é
exatamente o que o `split.py:83` já faz internamente (lê `ftable[f"c{k}"]` **por índice**).

É a mudança de **uma linha** (`_encode_multi(..., drop_names=True)`) que elimina metade da
redundância apontada na nota 1400, **sem re-pinar gramática nova** — só encolhe o meta do
sub-table.

### Telefone BR real — o dado está PRONTO

`receita-cnpj-enderecos`: **1999/2000** linhas com `ddd_1`+`telefone_1`, **69 DDDs distintos**.
Nada a coletar; é rodar a medição.

**Detalhe que interessa**: os comprimentos são `8 → 1983 · 1 → 15 · 7 → 1`. Dado **sujo** —
o gate do split vai recusar por template não-uniforme, e isso é justamente o caso realista
que os sintéticos não têm.

---

## A triagem

| item | ganho | facilidade | por quê |
|---|---|---|---|
| **`drop_names` no sub-table** | baixo em byte, **alto em redundância** | **trivial** (1 linha, medido) | já funciona; o decode já lê por índice; sem gramática nova |
| **Telefone BR real** | **alto** (fecha lacuna declarada 2×) | **trivial** (dado pronto) | é o único alvo do levantamento 0900 ainda não medido, e o dado sujo é caso realista |
| **F5** | — | **feito** | resolvido acima; vira registro |
| **6 tickets "já feitos"** | **alto** (limpa o board do `.8`) | **baixo esforço**, mas decisão de fechar é do owner | verificados por execução no levantamento 0900 |
| **`BUG-CHAVE-VAZIA-POSICIONAL`** | **alto** (único caso em que o TCF **altera** o dado) | médio (toca `src/tcf`) | reproduzido; o `.8H` já resolve com `\z` — a saída existe |
| **F6/DOC-03** (spec ensina 2 coisas falsas) | médio | trivial | registry tem 5 natures, não 3; id desconhecido é `ValueError`, não warning |
| Ganho do grupo em array com muitos itens | médio | médio | os labs 2100/2200 mediram composição, não byte |
| **H-13-04** (dica/spec de template) | médio | **médio-alto** | precisa de desenho de spec; conecta ADR-0041 |
| **H-13-03** (encode streaming) | **alto** (destrava o eixo stream) | **alto** | questão em aberto do prefixo já emitido; é pesquisa, não ajuste |
| 46 defasagens de doc | médio | alto (volume) | registradas em `2026-08-17-0300` |
| 69 reivindicações não-verificadas (`wf_4e9c88cb-b10`) | desconhecido | alto | dívida antiga, do sync de docs |

## Recomendação de ordem

1. **`drop_names`** — uma linha, medida, elimina redundância real. Menor custo do board.
2. **Telefone BR real** — fecha a lacuna que já declarei duas vezes; dado pronto; e o dado
   sujo testa o gate num caso que sintético não cobre.
3. **F6/DOC-03** — trivial e a spec está ensinando coisa falsa hoje.
4. **`BUG-CHAVE-VAZIA-POSICIONAL`** — o único caso em que o formato altera o dado. Precisa
   de aprovação para tocar `src/tcf`.
5. **H-13-03** por último dos técnicos: é o de maior ganho e **também o de maior custo** —
   é pesquisa aberta, não ajuste.

**H-13-03 não é "difícil de fechar" — é difícil de *definir*.** Por isso a revisão que o
owner pediu vem a seguir, separada.

## Conexões

- Levantamento das pendências: [`0900`](2026-08-17-0900-o-que-falta-pro-8-e-cep-telefone.md)
- Nota que deixou o `drop_names` pendente: [`1400`](2026-08-17-1400-split-teoria-e-o-magic-aninhado.md)
- [roadmap-hipoteses Pacote 13](../2026-05/roadmap-hipoteses.md)

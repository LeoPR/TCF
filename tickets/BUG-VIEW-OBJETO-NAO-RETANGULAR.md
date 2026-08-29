---
title: "BUG-VIEW-OBJETO-NAO-RETANGULAR: a view responde número sobre uma tabela que não existe, e depois acusa corrupção de um blob íntegro"
status: closed-fixed
priority: P2
severity: "R1 (resposta errada e silenciosa, seguida de diagnóstico falso)"
created: 2026-08-28
updated: 2026-08-28
gate: "correção em src/tcf só com aprovação explícita do owner (I5)"
blocked-by: []
related: [
      src/tcf/hierarchical.py,
      src/tcf/view.py,
      tickets/BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA.md,
      experiments/lab/dirty/notas/2026-08/2026-08-27-consistencia-tres-familias.md,
]
---

# BUG-VIEW-OBJETO-NAO-RETANGULAR

**[probatório → execução]** Um `dict` de colunas de **comprimentos diferentes** sai em
`#TCF.8H#O`, e o `decode` o lê exato. A `view` aceita esse blob, responde `columns` e
`nrows` sobre uma tabela retangular que não existe, e só quando alguém pede as linhas é
que levanta, **dizendo que o blob está corrompido**. Ele não está.

São dois defeitos num caso só, e o segundo é o pior: o diagnóstico culpa o dado.

Divergência #7 da [auditoria de consistência de
2026-08-27](../experiments/lab/dirty/notas/2026-08/2026-08-27-consistencia-tres-familias.md),
registrada aqui por não ter ticket próprio.

## Repro mínimo

```python
from tcf import decode, encode, view

w = encode({"a": [1, 2], "b": [3]})     # '#TCF.8H#Oa#:3[]:6n,b#:3[]:3n'

decode(w)          # {'a': [1, 2], 'b': [3]}    correto, e o blob está íntegro
view(w).columns    # ['a', 'b']                 aceitou
view(w).nrows      # 2                          só vale pra 'a'
view(w).select()   # ValueError: colunas com n_rows divergentes: 'b'=1 vs 'a'=2
                   #              — blob corrompido/truncado
```

## Causa

`_parse_hier` ([`view.py`](../src/tcf/view.py); o ticket dizia `hierarchical.py`, corrigido
ao fechar) abre o `#O` sem conferir que as colunas têm o mesmo comprimento: a coluna `count`
de cada campo era lida e jogada fora. As outras **sete** formas não tabulares do `.8H` são
recusadas na abertura, com mensagem limpa; esta passava.

O erro que aparece depois vem do cross-check de `n_rows` da `view`
([`view.py`](../src/tcf/view.py)), que existe para detectar **truncamento** e por isso
formula a mensagem em termos de corrupção. Quando o wire é legitimamente não retangular, a
mensagem está certa na aritmética e errada na acusação.

Com coluna de array vazio (`{"a": [], "b": [1, 2]}`) soma-se o fantasma `''` de
[`BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA`](BUG-VIEW-COLUNA-VAZIA-UNICO-FANTASMA.md), que é
outro ticket e não deve ser consertado aqui.

## Alcance

Entrada de borda: exige `dict` de listas de comprimentos diferentes, que já é uma forma que
o `.8M` recusa (o portão de retangularidade manda para o `.8H`). Nenhum gate byte-canônico
usa essa forma. O dano é de leitura, não de dado: o `decode` continua lossless.

## O certo

`_parse_hier` recusa o `#O` não retangular **na abertura**, com a mesma mensagem limpa que
as outras sete formas já usam, e a `view` nunca chega a ver o blob. Isso mata os dois
defeitos de uma vez, porque a acusação falsa só existia depois da aceitação indevida.

Alternativa considerada e descartada: fazer a `view` conferir o comprimento no `columns`.
Ela consertaria o número errado mas manteria a mensagem de corrupção, que é a metade mais
grave.

## Critérios de aceite

- [x] `view(encode({"a": [1, 2], "b": [3]}))` levanta na **abertura**, com a mensagem das
      formas não tabulares, e nenhuma menção a corrupção ou truncamento.
- [x] `decode` do mesmo blob continua lossless e sem mudança: o wire é íntegro e não é a
      camada que está errada.
- [x] A mensagem de `n_rows divergentes` continua existindo e continua dizendo corrupção
      **para truncamento de verdade** (contra-prova com blob cortado à mão).
- [x] `nrows`, `count` e `distinct` deixam de responder sobre a tabela que não existe.
- [x] As sete formas não tabulares que já eram recusadas continuam com a mesma mensagem.
- [x] Lab de evidência em disco (I2) com o antes e o depois, no padrão canônico.
- [x] Suíte completa e gates verdes; sem re-pin, porque nenhum wire emitido muda.

## Estado

**FECHADO em 2026-08-28 (onda 5).** O sítio ficou na `view` (`_parse_hier` vive em
`view.py`, não em `hierarchical.py`, e recusar dentro do `hierarchical.py` quebraria o
`decode` do ragged, que é lossless e tem de continuar). No laço dos corpos, a coluna
`count` de cada campo do `#O` deixou de ser descartada: é lida e comparada; counts
diferentes levantam na abertura com a frase das outras formas não tabulares, sem menção a
corrupção. O cross-check de `n_rows divergentes` continua existindo e continua acusando
corrupção **para truncamento de verdade** (contra-prova pinada).

Evidência: [`2026-08-28-0200-cauda-das-divergencias`](../experiments/lab/dirty/2026-08/2026-08-28/2026-08-28-0200-cauda-das-divergencias/), caso `nao-retangular-O`.
Testes: `TestViewObjetoNaoRetangular` (`test_tcf_lazy.py`), com o `#O` retangular à mão
abrindo e o truncamento real seguindo acusado.

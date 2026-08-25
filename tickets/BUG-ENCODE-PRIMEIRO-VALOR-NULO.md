---
title: "BUG-ENCODE-PRIMEIRO-VALOR-NULO: `None` na primeira linha estoura o encode multi-col"
status: closed
priority: P1
severity: R1 (erra alto, com excecao crua em vez de fail-loud; entrada comum em dado real)
created: 2026-08-24
updated: 2026-08-25
gate: `src/tcf` so' com aprovacao (I5). Nada soldado.
blocked-by: []
related:
  - src/tcf/multi/split.py
  - src/tcf/multi/core.py
  - experiments/lab/dirty/2026-08/2026-08-24/2026-08-24-0500-lazy-oportunista/
---

# BUG-ENCODE-PRIMEIRO-VALOR-NULO

## O que acontece

Numa tabela multi-coluna, se o **primeiro** valor de qualquer coluna for `None`, o
`encode` levanta `TypeError` cru, vindo de dentro do codec:

```python
encode({"uf": ["SP", "RJ"], "v": [None, 1]})
# TypeError: expected string or bytes-like object, got 'NoneType'
```

## CORRECAO DO PROPRIO TICKET (2026-08-25): o gatilho NAO e' a posicao

O que este ticket dizia abaixo esta' **errado**, e vale registrar porque a conclusao
apressada quase virou o desenho da correcao.

O gatilho nao e' "nulo na primeira linha". E' **nulo em qualquer posicao**, desde que o
primeiro valor forme um template com 2 ou mais campos de digito:

```python
_struct_split_encode(['a1b2', None, 'c3d4'])   # TypeError  (tem template)
_struct_split_encode(['abc',  None, 'def'])    # None       (sem template, retorna antes)
```

Quando o primeiro valor nao forma template, a funcao retorna antes de tocar os demais e o
nulo passa despercebido. Os testes originais deste ticket usavam valores sem template, e
foi isso que fez o defeito parecer posicional.

O texto abaixo fica como estava, porque e' o registro do que se sabia na hora.

## O gatilho parecia a POSICAO (leitura de 2026-08-24, incorreta)

Medido em 2026-08-24:

| entrada | resultado |
|---|---|
| `None` na posicao 0 | **TypeError** |
| `None` na posicao 1 | OK, 95 B |
| `None` na ultima posicao | OK, 92 B |
| coluna inteira `[None] * 60` | **TypeError** |
| single-col `[None] * 60` | OK, 13 B, round-trip fecha |

Nulo no meio da coluna funciona e faz round-trip. Só a primeira linha derruba.

## Causa

[`src/tcf/multi/split.py:32`](../src/tcf/multi/split.py):

```python
toks0 = _DIGITS.split(values[0])
```

O candidato `%split` inspeciona `values[0]` para deduzir o template, sem guarda de
`None`. Como `_best_of` avalia o split para **toda** coluna na competicao
`min(tcf, raw, dict, split)`, basta o primeiro valor ser nulo para a competicao inteira
morrer, mesmo que o split fosse perder para outro candidato.

Os outros candidatos ja' tem a guarda: `_fallback_safe` recusa coluna com `None`. O
split ficou de fora dessa protecao.

## Por que importa

Primeira linha com campo ausente e' entrada comum em dado real (CSV exportado, JSON de
API, planilha). O erro nao diz qual coluna nem qual linha, e nao vem do encoder: vem de
um `re.split` tres camadas abaixo.

## Criterio de aceite

- [ ] `encode` com `None` na primeira linha funciona, ou recusa com mensagem que nomeia
      a coluna e a razao. Escolher qual e' decisao do dono do projeto.
- [ ] O comportamento nao depende da POSICAO do nulo: mesma entrada, mesma resposta.
- [ ] Round-trip preservado onde hoje ja' funciona (nulo no meio), sem re-pin de gate.
- [ ] Teste cobrindo posicao 0, meio, fim, e coluna inteiramente nula.

## Descoberta

Achado por acaso em 2026-08-24, montando as bordas do lab
[`2026-08-24-0500-lazy-oportunista`](../experiments/lab/dirty/2026-08/2026-08-24/2026-08-24-0500-lazy-oportunista/):
o caso `tudo-nulo` derrubou o lab antes de chegar ao atalho que ele ia medir.

## Fechamento

`closed-done` em 2026-08-25. A correcao e' a guarda simetrica a que os outros candidatos
ja' tinham: coluna com nulo nao concorre no `%split`, porque o corpo dele e' template mais
campos de digito e nao tem onde representar nulo. O `_fallback_safe` recusa nulo no modo
raw pela mesma razao, e ja' explicava isso no comentario. Quem atende essa coluna e' o
candidato tcf, que tem slot proprio.

**MEDIDO ANTES DE SOLDAR**, porque guardar e' desistir de um candidato: 6 formas de
template forte (IP, data ISO, CPF, telefone, coordenada, versao) x 4 fracoes de nulo (1%,
5%, 20%, 50%). Em **24 de 24** combinacoes o modo que atende a coluna com nulo ja' e'
MENOR que o teto de um split tolerante a nulo (o split dos valores presentes mais a
mascara). A guarda nao custa byte nenhum.

Dois efeitos colaterais que a medicao expos, e que nao sao desta correcao:

- o split vence em 2 de 6 formas de template forte mesmo sem nulo (IP e telefone), entao
  ele nao e' um candidato marginal;
- **o nulo em si e' caro**: a coluna de telefone sai de 117 B sem nulo para 2944 B com 1%
  de nulo. Isso e' do formato, nao da guarda (o teto tolerante daria 2983 B, pior).

Gates byte-canonicos 33 verdes SEM re-pin: nenhuma coluna com nulo chegava a ter o split
como candidato, porque estourava antes de competir, entao a guarda troca ESTOURO por
NAO-CONCORRE e o wire de ninguem muda.

Suite 1497 -> 1507. Lab:
`experiments/lab/dirty/2026-08/2026-08-25/2026-08-25-0400-split-e-nulo/`

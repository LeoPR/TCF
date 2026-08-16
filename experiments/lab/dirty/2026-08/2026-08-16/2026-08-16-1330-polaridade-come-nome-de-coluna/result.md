# Resultado — o defeito, o alcance e a fronteira

**RT quebrado silenciosamente** em coluna única cujo nome termina em pontuação, no `.8M` **e**
no `.8H`. Reproduzido, mecanismo identificado, causa isolada por contra-prova.

## 1. O alcance

| rota | RT falso | modo de falha |
|---|---:|---|
| `.8M` (1 coluna, n≥5) | **48/64 = 75,0%** | 24 perdem a chave · 24 perdem chave **e** valores |
| `.8H` (1 campo) | **38/64 = 59,4%** | mesmo mecanismo |
| **warnings** | **0/64** | perda inteiramente silenciosa |

Os 16 que escapam terminam em `* , : = \ ^ | ~`.

## 2. A causa, isolada

A contra-prova é limpa: **a mesma coluna com uma segunda ao lado dá 64/64 RT ok**. Com 2+
colunas o meta ganha `,`/`=`, o nome deixa de ser o fim da linha 1, e a polaridade não o
alcança. **O defeito é da coluna única.**

## 3. A dependência de `n`, que é o motivo de não ter sido pego

O gatilho não é o nome — é o **modo** que vence o `min()`, porque o modo põe ou não um prefixo
antes do nome:

```
n=3   #TCF.8M!obs.   modo raw, prefixo '!'    RT ok
n=5   #TCF.8Mobs.    modo tcf, prefixo vazio  RT QUEBRA
```

Qualquer teste de round-trip escrito com uma coluna pequena passa. É a mesma classe do
`T-GRAFIA-CHECKLIST` (*"a frase no ADR não impediu — o teste é que impede"*), mas desta vez a
assimetria não está dentro de uma camada: está **entre duas** — a polaridade é camada de borda
(`decoder.py:150-153`: *"a PRIMEIRA coisa do decode"*) e por construção não conhece a gramática
do `.8M`.

## 4. Severidade

É a pior classe do projeto: **resposta errada sem erro**. Pior que o `T-NATURE-IGNORADA-CALADA`
(lá o wire sai certo e só a expectativa quebra) e pior que o `T-VIEW-PRED-POSICIONAL` (lá a
consulta erra mas o dado está íntegro). **Aqui o dado sai do round-trip diferente do que
entrou**, e em 24 dos 64 casos os valores — não só a chave.

Nomes plausíveis em dado real que caem: `obs.`, `qtd.`, `valor_r$`, `%`, `medida(m)`, `nome-`,
`id#`. Nomes com `.` final são comuns em export de planilha.

## 5. O que este lab NÃO fez

- **Não consertou.** `src/tcf` intocado; conserto exige aprovação e decisão de onde cortar
  (escapar o nome contra o alfabeto da polaridade no emissor, ou ensinar a polaridade a não
  agir quando o disc é `M`/`H` — são fronteiras diferentes com custos diferentes).
- **Não varreu Unicode** — só `string.punctuation` ASCII.
- **Não mediu multi-coluna com a ÚLTIMA coluna terminando em pontuação sob `drop_names`**, que
  é a outra forma em que o nome pode encostar no fim da linha 1.

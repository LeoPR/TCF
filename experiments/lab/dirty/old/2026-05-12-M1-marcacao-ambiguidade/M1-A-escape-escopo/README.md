# M1.A' — Escape com escopo (variante de M1.A)

## Tecnica

`\` antes de uma sequencia de digitos sinaliza "todos os digitos
contiguos seguintes sao literal". Em vez de escapar char a char
(M1.A original), agrupa a sequencia em **um unico marcador**.

Para `*` e `\` no literal: continua escape individual (esses
chars nao formam sequencias naturalmente).

## Custo

| Caso | M1.A | M1.A' |
|---|---|---|
| 1 digito isolado | `\X` (+1) | `\X` (+1) |
| K digitos contiguos | K escapes (+K) | 1 escape (+1) |
| `*` isolado | `\*` (+1) | `\*` (+1) |
| Antes de refs adjacentes | sep automatico | precisa `*` (+1) |

**Para K=1 ou K=2**: empate com M1.A.
**Para K=3+**: M1.A' ganha (K-1 bytes economizados, ate -1 por
separador necessario antes de refs).

## Roundtrip e bytes nos 4 datasets

| Dataset | M1.A | M1.B | **M1.A'** | M1.A' melhor que? |
|---|---:|---:|---:|---|
| D1-emails-simples | 162 | 162 | **162** | igual (sem ambig) |
| D2-emails-quote-id | 200 | 198 | **197** | -1 vs ambas |
| D3-stress-substring | 242 | 233 | **233** | empata com M1.B, -9 vs M1.A |
| D4-caos-mix | **152** | 160 | **152** | empata com M1.A, -8 vs M1.B |
| **TOTAL** | 756 | 753 | **744** | **-9 vs M1.B, -12 vs M1.A** |

**Roundtrip 4/4 OK.**

## M1.A' eh estritamente melhor ou igual

Em **todos os 4 datasets**, M1.A' tem bytes <= max(M1.A, M1.B).
Mais ainda: M1.A' <= M1.A em todos os casos E M1.A' <= M1.B em
todos os casos.

**M1.A' engole M1.A e M1.B simultaneamente.**

## Exemplos comparativos

### D2 eid=11 (`o'connor103`) — M1.A' ganha 2 bytes vs M1.A

```
M1.A : o'connor\1\0\3*@yahoo7
M1.A': o'connor\103*@yahoo7      (-2 chars)
```

Sequencia `103` escapada como um bloco. `*` separador necessario
antes de `@yahoo`.

### D3 eid=1 (`api/users/00042/profile.json`) — M1.A' ganha 3 vs M1.A

```
M1.A : api*/*users/\0\0*\0\4\2*/profile*.*json
M1.A': api*/*users/\00*\042*/profile*.*json    (-3 chars)
```

Sequencias `00` e `042` agrupadas.

### D2 eid=2 (`d'angelo42@gmail.com`) — empata com M1.A

```
M1.A : 1,2,3\4\25,6,7      (14 chars)
M1.A': 1,2,3\42*5,6,7      (14 chars) — precisou separador `*` antes refs
```

K=2, ganho de 1 byte no escape mas perde 1 byte no separador.
Empata.

### D4 eid=4 (`[b]*'foo'@42`) — empata com M1.A

```
M1.A : [b2,3,4,5            (mesmo de M1.A')
M1.A': [b2,3,4,5
```

K=1 em fragmentos isolados. Sem oportunidade de agrupamento.

## Propriedades para F2

| Eixo | M1.A | M1.B | M1.A' |
|---|---|---|---|
| Stateful encoder? | nao | nao | nao |
| Stateful decoder? | nao | sim (modo aspas) | sim (modo escape escopo) |
| Parse linear? | sim | nao | quase (lookahead 1 char apos `\`) |
| Latencia | linha a linha | linha a linha | linha a linha |
| Lookahead | nao | sim (busca aspa final) | sim (le dígitos apos `\`) |
| Bytes (total D1-D4) | 756 | 753 | **744** |

## Insight conceitual

M1.A' confirma a tese da nota
[`marcadores-redundantes-agrupamento`](../notas/marcadores-redundantes-agrupamento.md):

> "marcadores que aparecem em sequencia podem ser fundidos em
> uma forma mais compacta"

A "luta e' representar de forma barata". M1.A' encarna isso:
substitui K marcadores individuais por 1 marcador de escopo.
Ganho = K-1 (menos custo do eventual separador).

## Limitacoes

- **Limitado a sequencias de digitos.** `*` e `\` no literal nao
  agrupam (mas sao raros).
- **Separador antes de refs adjacentes**: anula parte do ganho
  quando literal-escape e' seguido de ref.
- **Decoder e' stateful** (modo escape escopo), igual M1.B —
  perde a propriedade "stateless puro" de M1.A.

## Aplicacao das ideias relacionadas

A mesma tecnica de agrupamento poderia ser aplicada a:
- **Refs contiguas** (range): `1,2,3,4,5` -> `[1-5]` (registrado
  na nota `range-de-indices.md`, ainda nao implementado)
- **Aspas adjacentes** (M1.B variante): `'X''Y'` -> `'X*Y'`
  (nao implementado)

Estes sao **independentes** de M1.A' e podem ser combinados.

## Como rodar

```bash
cd 2026-05-12-M1-marcacao-ambiguidade/M1-A-escape-escopo
python teste.py
```

Imprime TCFs + decode contra-prova nos 4 datasets.

## Implicacao para o macro M1

M1.A' venceu ou empatou em todos os 4 datasets. Isso permite:

1. **Fechar M1 mais cedo** — nao precisa implementar M1.C e M1.D
   se ja temos uma sintaxe que vence as outras 2.
2. **Ir direto para F2 e F3** com 3 sintaxes (A, A', B) ou ate
   apenas 1 (A').
3. **Considerar M1 fechado com M1.A' como vencedora textual**, e
   abrir M2 para outras direcoes (range de refs, marcadores
   binarios, etc.)

Decisao do user proxima.

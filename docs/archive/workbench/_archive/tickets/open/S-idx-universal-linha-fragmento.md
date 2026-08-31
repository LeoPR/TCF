---
title: Namespace unificado de índices (linha + fragmento) — estudo deferido
type: study
status: open
priority: low
created: 2026-05-10
defer-reason: depende de compressão de representação de índice (S-representacao-de-indice) para mitigar explosão
---

## Epifania (2026-05-10)

E se linha completa e fragmento `*` compartilhassem o **mesmo
namespace de índice**?

Hoje TCF v0.5 tem dois espaços disjuntos:
- `*<text>` declara fragmento → ganha idx fragmento (1, 2, 3, ...)
- linha completa repetida → `=N` (refere idx de linha)

Proposta: **toda linha tem `*` implícito**. Fragmentos declarados
com `*` e linhas inteiras concorrem ao mesmo contador. Eliminamos
o sinal `=` e unificamos as duas referências em uma só.

## Por que faz sentido (coerência com a teoria)

A tese de [DICT maleável unificado](../../research-notes/2026-05-12-dict-maleavel-unificado.md)
diz que **todas as técnicas são variações de uma única política
de dicionário**. O namespace duplo (`*` para parte, `=` para todo)
é o último vestígio de separação.

Unificar:
- 1 namespace em vez de 2
- Permite que uma linha seja referenciada como **fragmento** de
  outra linha mais longa (ex: `user001@gmail.com` é fragmento de
  `https://api.com/users/user001@gmail.com`)
- Aumenta densidade do dicionário gratuitamente — toda linha já é
  um candidato

## Trade-off honesto

**Ganho**:
- Sintaxe mais simples (1 marcador em vez de 2)
- Dicionário mais denso

**Perda**:
- Índices "explodem" — cada linha consome um slot
- Em N=1000, a maioria dos idx será 3 chars (decimal)
- Em N=100, idx=99 já tem 2 chars

**Onde dói**: cenário urls-1000 (linhas únicas, sem repetição). Cada
linha vira idx novo, sem nunca ser usado como ref. Idx até 1000
infla o dicionário sem retorno.

**Onde compensa**: cenários com repetição alta de linhas inteiras
(categóricas, dups), e cenários onde uma linha é prefixo/sufixo de
outras (hierarquia URL).

## Conexão com S-representacao-de-indice

A explosão de índices é **exatamente** o problema que o ticket
[S-representacao-de-indice](S-representacao-de-indice.md) endereça
no eixo 2 (compressão por representação). Letras a-z, base32,
base64 ASCII-safe reduzem 3 chars decimais para 1-2 chars.

Logo: **estudar os dois juntos**. Sem compressão de representação,
a unificação perde sempre em N alto. Com base32/64, idx até 1024
cabe em 2 chars — viabiliza unificação.

## Perguntas em aberto

1. **Idx implícito por ordem (sem declarar)**: se toda linha tem
   `*` implícito, o decoder pode contar linhas e gerar idx
   automaticamente. Custo de declaração = zero. É roundtrip-safe?
2. **Quando uma linha vale como ref?**: hoje `=N` é só linha
   inteira. Com unificação, posso ter `idx_de_linha + sufixo`
   formando outra linha? Decoder consegue desambiguar?
3. **Comparação com Re-Pair**: Re-Pair também unifica regras (cada
   par vira não-terminal). É o mesmo princípio teórico?
4. **Custo médio do idx em N=100, 500, 1000**: medir empiricamente
   bytes/ref decimal vs base32 vs base64.

## Quando revisitar

- Junto com [S-representacao-de-indice](S-representacao-de-indice.md)
  — fazem par (problema/remédio)
- Após validar curva de escala em datasets reais (TPC-H, logs)
- Quando otimização binária do dialeto TCF entrar em escopo

## Relacionado

- [DICT maleável unificado](../../research-notes/2026-05-12-dict-maleavel-unificado.md)
- [S-representacao-de-indice](S-representacao-de-indice.md)
- [lab 23 escala](../../../../experiments/lab/dirty/2026-05-23-escala/notes.md) —
  primeira evidência de que TCF+gz vence em escala (pano de fundo)

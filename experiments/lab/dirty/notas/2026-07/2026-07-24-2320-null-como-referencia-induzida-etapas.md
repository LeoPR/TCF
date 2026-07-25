---
title: null como referência induzida — análise em etapas (sem caso exclusivo de código)
type: analise
status: aberta
created: 2026-07-24
related:
  - experiments/lab/dirty/2026-07/2026-07-24/2026-07-24-2210-null-indice0-coluna-string/
  - experiments/lab/dirty/notas/2026-07/2026-07-24-2140-levantamento-null-e-tipos.md
  - experiments/lab/dirty/notas/2026-07/substituicao-indices-especiais-plano.md
  - experiments/lab/dirty/notas/2026-07/2026-07-24-0100-camada-explicita-vs-implicita-fecha-cicloA.md
---

# null como referência induzida — análise em etapas

Princípio firmado pelo owner (2026-07-24):

> *"Não podemos criar casos exclusivos de código de tratamento em si, mas um fluxo de trocas
> baratas como se fizesse parte do sistema de códigos existentes. Não gostaria de criar um
> super código só pra tratar o null com um código reservado."*

E a ordem, explicitamente **sem jumps**:

1. `^0` — referência a uma referência **pré-existente** (o passo normal do sistema atual)
2. otimização: `0` aponta para `^0`
3. talvez depois: `0` ligado direto ao null

---

## Resposta curta

**A etapa 1 não só é possível agora — ela SIMPLIFICA o código.** Não é caso especial: é
pré-semear a tabela que já existe. Medido, não argumentado (§2).

A etapa 2 é uma normalização de grafia de 1 linha, no mesmo lugar onde as outras
implícito→explícito já vivem. A etapa 3 é desnecessária: a 2 já entrega o byte.

---

## 1. Por que `^0` não é caso especial

O decode já tem a máquina inteira. Hoje:

```python
nos_decl = []                       # nós declarados, na ordem
...
s_no = nos_decl[idx - 1]            # `^N` é 1-based
```

O `- 1` existe **só** para compensar o fato de a lista começar vazia enquanto o wire conta
a partir de 1. Pré-semeando o slot reservado, essa compensação some:

```python
nos_decl = [NULO]                   # a tabela NASCE com o slot 0
...
s_no = nos_decl[idx]                # o -1 SUMIU
```

`^1` continua apontando para o primeiro nó declarado (agora `nos_decl[1]`), e `^0` passa a
ser o slot reservado. **Nenhum ramo novo, nenhum `if null`, nenhum handler.** O null entra
pela mesma porta que qualquer outra referência de linha — é exatamente o "fluxo de trocas
baratas dentro do sistema existente" que o owner pediu.

O lado do encode **não muda**: o `eid` já é 1-based (`unica_to_eid = {s: i+1 …}`), então
continua indexando corretamente na tabela pré-semeada.

## 2. Evidência (experimento aplicado e revertido)

Apliquei as 3 linhas no `src/tcf` real e rodei a suíte completa:

| | resultado |
|---|---|
| diff | **5 inserções, 3 remoções** — 1 arquivo |
| suíte | **915 passed**, 1 failed |
| gates byte-canônicos | **passam** (D1-D9, D17a, real-world) |
| a única falha | `test_ref_zero_nao_e_aceite_silencioso` — o teste que fixa "`^0` é inválido" |

A única falha é o teste que pina **exatamente a semântica sendo substituída**. Ou seja: a
mudança é compatível com tudo que existe, e o que "quebra" é a regra que ela vem trocar.

Comportamento verificado no experimento:

```
decode("ab\ncd\n^0\n")   -> ['ab', 'cd', None]
decode("^0\nab\n^0\n")   -> [None, 'ab', None]
decode("ab\ncd\n^1\n")   -> ['ab', 'cd', 'ab']     (inalterado)
decode("ab\n^9\n")       -> ValueError              (fora de faixa segue fail-loud)
```

**Experimento revertido**; a árvore está limpa e a suíte de volta em 916.

## 3. A etapa 2 (`0` → `^0`)

Uma linha na camada de normalização (o "pré-avaliador de apelidos" já formalizado em
`2026-07-24-0100`): linha cujo conteúdo **inteiro** é `0` expande para `^0`, e daí segue o
fluxo normal. Desambiguação **posicional**, mesma classe do char de modo no índice 7.

Isso mantém a hierarquia que o owner pediu — `0` → `^0` → referência pré-existente → null —
com cada degrau visível no código, em vez de um salto de `0` direto para null.

Custo medido no lab 2210 (17 casos, RT 51/51): a grafia `0` é **−479 B** contra a forma que
declarava nó e **−493 B** contra `^0` explícito, porque todo null passa a custar 1 char.

## 4. A etapa 3 é desnecessária

"Ligar o `0` direto ao null" não economiza byte nenhum sobre a etapa 2 — o wire já é `0`. Ela
só encurtaria o caminho **interno**, que é justamente o que o owner não quer colapsar agora
("precisamos do fluxo limpo em etapas"). Registrada como não-necessária, não como pendente.

## 5. O que esta análise NÃO cobre

- **Como o null CHEGA no `^0` pelo lado do encode.** O experimento provou o decode. O encode
  hoje nem recebe `None` na rota flat (`_lista_flat` exige todos `str`) — a coluna é desviada
  para o `.8H` antes. Abrir a rota flat para `str|None` é trabalho separado, e é ele que
  captura os 84% de ganho de envelope medidos no lab 2210.
- **Tipo de retorno.** `decode` de single-col passa a poder devolver `list[str | None]`. É
  mudança de contrato público — precisa de decisão e provavelmente ADR.
- **Multi-coluna, `.8M`, `.8H`.** Fora do escopo; a escala firmada é uma coluna de um tipo.
- **Os outros especiais** (NaN, ±Inf, ausência). O slot 0 é o null; a ordem canônica dos
  demais reservados continua **não fixada** (§6 do levantamento).

## 6. Recomendação

A etapa 1 está pronta para soldar sob demanda: 3 linhas, byte-neutra, gates verdes, e o único
teste afetado é o que ela vem substituir. Mas soldar só o decode **não entrega ganho** — o
ganho mora em abrir a rota flat no encode (§5). Sugiro tratar as duas como um weld só, ou
soldar a 1 declarando explicitamente que é preparação sem efeito no wire emitido.

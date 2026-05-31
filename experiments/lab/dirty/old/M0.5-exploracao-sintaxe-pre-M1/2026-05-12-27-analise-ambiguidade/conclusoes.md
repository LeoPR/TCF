# Conclusões — Etapa 1 mapeia o espaço de decisão

O analisador puro confirma 4 fatos centrais:

1. **A maior parte dos chars em literais não precisa marcação**
   (80% A em emails-quote-id)
2. **Toda ambiguidade real vem de dígitos** nesse dataset (categoria
   B é vazia)
3. **Escape e aspas custam o mesmo** no agregado (empate em +14B)
4. **Idx existentes** definem se um dígito é problema real ou
   pode ser sumido (próxima etapa)

## Por que isto é diferente das sintaxes anteriores

Os exps 21-26 implementaram **regras globais**:
- v3: nunca marca
- v4-escape: sempre `\X` por char ambíguo
- v4-quote-fixed: sempre `'X'` por fragmento ambíguo
- v4-mixed: regra por literal mas isolada do estado

Nenhuma considera **se o conflito é real**. v4-mixed e v4-q-fix
acabam empatando porque ambas marcam independente do contexto.

Esta análise mostra: **a marca podia ter sido omitida** em vários
casos, mas ninguém perguntou.

## Espaço de decisão por char

Para cada char no literal, há até 4 opções:

| Opção | Aplicabilidade | Custo |
|---|---|---|
| Sumir | char não-marcador OU contexto resolve OU idx-N não existe | 0 |
| Escape pontual | char-C isolado | +1 |
| Aspas em grupo | vários chars-C juntos | +2 |
| Aspas órfã | grupo seguido de fim-de-linha/transição | +1 |

A decisão **ótima** depende:
- Quantos chars-C tem o literal (K)
- Posição do literal na linha (início/meio/fim)
- Vizinhança (próximo é literal? ref? fim?)
- Estado do parser (idx-N existe?)

Hoje só implementamos 2 das 4 opções (escape e aspas) e fazemos
escolha global. As outras 2 (sumir, órfã) são potencial não
explorado.

## Estimativa de ganho possível

Hipótese para emails-quote-id (custos teóricos):

| Estratégia | Bytes extras |
|---|---:|
| v4-escape ou v4-q-fix (estado da arte) | +14 |
| Com sumida ideal (idx não existe) | +5 a +10 |
| Com órfã (1 byte de aspa em vez de 2) | -1 a -3 |
| Combinado (sumida + órfã + escolha local) | **+3 a +7** |

Ganho potencial sobre estado da arte: **40-80%** menos bytes de
marcação. Mas precisa medir.

## Achados estruturais

### Categoria B é vazia em emails-quote-id

Nenhum char `,`, `^`, `|`, `[`, `]` em literais. Significa que
o flow "char é marcador mas contexto resolve" não tem teste
nesse dataset.

Para a Etapa 4 (agrupamento) ter onde brilhar, precisaremos de
dataset com chars-B reais.

### Algoritmo do online.py concentra ambiguidade

11 dos 18 fragmentos têm K=0 (raw). A ambiguidade fica
concentrada em 7 fragmentos, todos contendo IDs numéricos.

Isso é **bom**: como há poucos fragmentos ambíguos, a estratégia
local pode ser sofisticada sem explosão de custo.

### Empate teórico aspas vs escape

A análise pura mostra +14 em ambos. Isso confirma o achado do
exp 26: não há razão para preferir uma sobre outra **apenas pelo
custo de marcação**.

A escolha vira por outras razões:
- **Escape**: mais simples, parser não precisa de modo aspas
- **Aspas**: mais natural visualmente, agrupa K=2+

## Pontos a registrar

1. **Análise é precondição** para todas as próximas etapas. Sem
   ela, decisões são cegas
2. **80% A** mostra que o algoritmo já produz fragmentos
   limpos. A pressão de otimização está em **20%** específicos
3. **Estado de idx** é peça-chave para sumida (Etapa 2)
4. **Vizinhança** é peça-chave para órfã e agrupamento (Etapas 3
   e 4)
5. **Categoria B vazia aqui** — precisa dataset com `,` ou
   similares para testar nuance contextual

## O que esta Etapa NÃO faz

- Não emite TCF (analisa apenas)
- Não considera estado de idx (deferido para Etapa 2)
- Não considera vizinhança (deferido para Etapa 3-4)
- Não testa em datasets sem dígitos (categoria B)

## Próximo passo

**Etapa 2 — sumida com parser stateful**. Exp 28.

Dataset alvo: emails-quote-id (continua, mesmo).

Pergunta: quantos dos 14 chars-C podem ser sumidos porque o idx
correspondente não existe?

Implementação prevista:
- Encoder analisa cada sequência de dígitos no literal
- Calcula valor N do número formado
- Verifica se idx N existe no momento da decodificação dessa
  linha
- Se NÃO existe: sumir (emitir literal sem marcador)
- Se EXISTE: precisa marcar (escape ou aspas)

Decoder fica stateful — mantém dict de idx → string, tenta cada
sequência de dígitos como ref, se idx não existe trata como
literal.

Atenção: **a ordem de leitura importa**. idx 256 não existe no
início, mas pode passar a existir depois. Se uma decl posterior
declara idx 256, o decoder antigo trataria como literal e o novo
como ref → bagunça. Solução: o encoder garante que dígitos no
literal **nunca formem N que seja idx existente quando a linha é
processada**.

A Etapa 2 vai testar essa premissa.

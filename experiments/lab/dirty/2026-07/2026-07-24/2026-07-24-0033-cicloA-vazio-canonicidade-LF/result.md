# Ciclo A — o VAZIO e a canonicidade do LF

Pergunta do owner: qual o mapeamento correto de `[]` / `['']` / `['','']`? Duas convenções para o LF do corpo: **(A) TERMINADOR** (cada elemento termina em LF — é o que o `encode` já produz) e **(B) SEPARADOR** (LF separa; `[]` = wire pelado `#TCF.8`, a proposta literal).

## 0. Hoje — o decode é TOLERANTE, e é isso que quebra a canonicidade

| corpo (órfão) | decode hoje |
|---|---|
| `''` | `['']` |
| `'\n'` | `['']` |
| `'\n\n'` | `['', '']` |
| `'a'` | `['a']` |
| `'a\n'` | `['a']` |
| `'a\n\n'` | `['a', '']` |
| `'a\nb'` | `['a', 'b']` |
| `'a\nb\n'` | `['a', 'b']` |

**3 colisões** (grafias distintas → mesmo dataset):
- `''` e `'\n'` → ambos `['']`
- `'a'` e `'a\n'` → ambos `['a']`
- `'a\nb'` e `'a\nb\n'` → ambos `['a', 'b']`

O `encode` usa LF como **terminador** (`['a']`→`'a\n'`); o `decode` aceita **com ou sem** o terminador final. Essa tolerância é a causa — e o efeito colateral é que `[]` **não tem representação** na forma flat (o mínimo é `['']`), obrigando a fuga pro `.8H#D0`.

## 1. As duas convenções — bijetividade

| dataset | (A) terminador | (B) separador |
|---|---|---|
| `[]` | `'#TCF.8\n'` | `'#TCF.8'` |
| `['']` | `'#TCF.8\n\n'` | `'#TCF.8\n'` |
| `['', '']` | `'#TCF.8\n\n\n'` | `'#TCF.8\n\n'` |
| `['a']` | `'#TCF.8\na\n'` | `'#TCF.8\na'` |
| `['a', '']` | `'#TCF.8\na\n\n'` | `'#TCF.8\na\n'` |
| `['', 'a']` | `'#TCF.8\n\na\n'` | `'#TCF.8\n\na'` |
| `['a', 'b']` | `'#TCF.8\na\nb\n'` | `'#TCF.8\na\nb'` |

- **(A)**: 0 colisões · RT 7/7
- **(B)**: 0 colisões · RT 7/7

Ambas são bijetivas. A diferença NÃO está aqui — está nos dois testes seguintes.

## 2. Compatibilidade — os wires que o `src/tcf` já emite continuam válidos?

> O corpo real pode conter marcadores (RLE `*N|`, refs `^N`). O teste abaixo NÃO reimplementa o codec do corpo: aplica só a **regra de moldura** de cada convenção e delega o corpo ao `decode` REAL. Assim mede compatibilidade de FRAMING, não de body.

| dataset | corpo REAL do encode | termina em LF? | (A) framing | (B) framing |
|---|---|:---:|---|---|
| `['']` | `'\n'` | sim | ✅ válido | `['', '']` ❌ |
| `['', '']` | `'*2|\n'` | sim | ✅ válido | `['', '', '']` ❌ |
| `['a']` | `'a\n'` | sim | ✅ válido | `['a', '']` ❌ |
| `['a', '']` | `'a\n\n'` | sim | ✅ válido | `['a', '', '']` ❌ |
| `['', 'a']` | `'\na\n'` | sim | ✅ válido | `['', 'a', '']` ❌ |
| `['a', 'b']` | `'a\nb\n'` | sim | ✅ válido | `['a', 'b', '']` ❌ |

- **(A) valida 6/6 wires reais** — porque o `encode` JÁ emite o terminador final em todos. Adotar (A) **não muda um único byte** do que é produzido hoje; só torna o *decode* estrito (rejeitar corpo sem terminador).
- **(B) valida 0** — sob separador, o LF final de todo wire existente passa a significar um **elemento vazio extra**. Todo wire de hoje decodificaria errado; adotar (B) exigiria reescrever o corpo (viola 'body congelado').

## 3. Robustez — normalização POSIX (ferramenta *garante* LF final)

> Um arquivo de texto POSIX **deve** terminar em LF. Editores, `git` e linters aplicam essa normalização: **acrescentam LF se e somente se faltar**. O teste é esse — não um LF arbitrário.

| conv. | wire de `[]` | já é POSIX-válido? | normalizador age? | resultado | corrompe? |
|---|---|:---:|:---:|---|:---:|
| (A) | `'#TCF.8\n'` | sim | não mexe | `[]` | ✅ não |
| (B) | `'#TCF.8'` | **NÃO** | **acrescenta LF** | `['']` | ❌ SIM |

**Este é o ponto decisivo.** Em (B) o wire de `[]` é `'#TCF.8'` — **não é um arquivo de texto POSIX válido** (não termina em LF). Qualquer normalizador acrescenta o LF, e `[]` vira `['']` **silenciosamente**. Em (A) o wire de `[]` já termina em LF: o normalizador **não tem o que fazer**, e o dado sobrevive.

⚠️ **Ressalva honesta**: (A) não é imune a um LF *espúrio* (dois LFs viram `['']`). A diferença é de **exposição**: (B) é corrompida pela operação PADRÃO das ferramentas; (A) só por uma edição anômala — que, sendo não-canônica, o decode estrito pode recusar.

## 4. O `????` do owner — `#TCF.8b\n\n`

Sob (A), com tag `b`:

| wire | corpo | elementos | valor | resultado |
|---|---|---|---|---|
| `#TCF.8b\n` | `''` | 0 | — | **`[]`** ✅ |
| `#TCF.8b\n\n` | `'\n'` | 1 | `''` | **FAIL-LOUD** — `''` não é `true`/`false` |

**Não existe `[,]`**: a lista de 1 elemento cujo texto é vazio só faz sentido para **string** (onde `""` é valor legítimo). Para `b`/`n`, linha vazia é **valor fora do domínio** ⇒ erro. Ou seja, a TAG também decide se linha vazia é dado ou defeito.

**E a tag é dispensável no vazio**: `[]` de bool e `[]` de int são o MESMO dataset (zero elementos, nenhum tipo a preservar). Logo a grafia canônica de `[]` é a **sem tag**: `#TCF.8\n`. `#TCF.8b\n` seria legal porém redundante — e admitir duas grafias para o mesmo dataset reabriria a não-canonicidade que estamos fechando.

## Veredito

O mapeamento que o owner propôs está **semanticamente certo** — `[]`, `['']`, `['','']` devem ser distintos e o vazio não precisa de tag. Mas a **convenção (B)** (LF separador, `[]` = wire pelado) tem dois custos que a medição expõe:
1. **quebra todos os wires existentes** (§2) — viola o 'body congelado';
2. **`[]` corrompe silenciosamente** ao ganhar um LF de qualquer editor (§3).

A **convenção (A)** entrega o MESMO mapeamento semântico com:
- `#TCF.8\n` → `[]` · `#TCF.8\n\n` → `['']` · `#TCF.8\n\n\n` → `['','']`
- **zero mudança** nos bytes que o `encode` já produz (só o decode fica estrito);
- `[]` expresso na forma flat (7 B) em vez de fugir pro `.8H#D0` (11 B);
- robustez a LF acrescentado.

A diferença entre o que o owner escreveu e (A) é de **um LF**: o owner contou o LF do header como parte do corpo. Semanticamente idênticos; (A) é a grafia que sobrevive às ferramentas e ao histórico.

> Não é decisão — é a tabela para decidir. Nada em `src/tcf`.
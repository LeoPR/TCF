# HCC — Hierarchical Compositional Coding

**Codnome de origem**: `M8.A` (variante A do macro M8 do dirty lab v0.6).

**Camada**: TCF camada 2 (compactação composicional).

## O que é

HCC é a camada de **compactação composicional** do TCF. Recebe os
tokens raiz produzidos pelo [OBAT](OBAT.md) e produz o texto TCF
final, comprimindo composições recorrentes em refs auto-nomeados
organizados hierarquicamente.

A inovação central de HCC é a distinção semântica entre dois
operadores de concatenação em texto:

- `,` (vírgula) — concat **efêmero**: junta dois refs em emissão, mas
  NÃO cria um novo ref nomeado.
- `~` (til) — concat **composicional**: junta dois refs E cria um
  novo ref auto-nomeado para reuso futuro.

Range `a..b` é caso particular de composição por sequência consecutiva.

## Estrutura

A saída de HCC é texto. Cada linha representa uma string original
(ou repetição via RLE).

### Sintaxe

| Construto | Significado |
|---|---|
| `1,2,3` | Refs 1, 2, 3 concatenados (sem criar ref novo) |
| `1~2~3` | Refs 1, 2, 3 concatenados E criam novos refs (pairwise) |
| `1..5` | Range: refs 1, 2, 3, 4, 5 (caso particular de composição) |
| `abc` | Literal `abc` |
| `\X` | Escape de char reservado (`*`, `\`, `~`, digit, etc.) |
| `*N\|linha` | RLE: linha repete N vezes |
| `*` | Separador entre lit-lit ou lit-ref boundary |
| `^N` | Repetição de string já decodificada (anti-RLE de string única) |

### Pipeline interno

1. **Fase A (tokenize)**: alg16 tokens + atomos provisionais → `pieces`
   por linha (`lit` ou `refs`)
2. **Fase B (detect)**: iterativo greedy — substitui sub-tuplas
   reusáveis por `alias_marker`
3. **Fase C (emit)**: single pass — atribui IDs decoder-style
   (interleaved atoms + composições), emite texto

## Funcionamento (sub-linguagem matemática)

### Estado interno

Seja `body = (T_1, ..., T_n)` o body, onde `T_i` é a linha do TCF da
i-ésima string única.

Seja `R` o conjunto de refs (atomic + virtual) e `M ⊂ R × R × ... × R`
o conjunto de sub-tuplas detectadas.

### Detector greedy

Para cada iteração `k = 1, 2, ...`:

```
contagem[sub] = | { posição em pieces[*]['refs'] onde sub aparece consecutivo } |

para cada sub ∈ pieces com contagem[sub] ≥ 2:
    Lr_inline = chars de _emit_refs_range(sub)
    len_N = chars de str(atom_count + composicoes_acumuladas + K - 1)
    net = (R - 1) * (Lr_inline - len_N)
    se net > 0:
        candidato

melhor = argmax(net) entre candidatos
se melhor existe:
    substituir todas ocorrências de melhor.sub por alias_marker novo
    aliases.append(melhor.sub)
senão:
    parar
```

### Constraint pra inline expansion correto (body-order check)

Quando um candidato `sub` contém um virtual `-Y` em posição `> 0`,
exigir:

```
alias_first_line[Y] < sub_first_line[sub]
```

Isto é, `Y` deve ter aparecido sozinho em uma linha **anterior** à
primeira aparição de `sub`. Garantia: ao emitir o def de `sub`,
`Y` já está resolvido — inline expansion via pairwise left-assoc
preserva o valor correto de `Y`.

### Emit (pairwise left-assoc)

Para um chain `a~b~c~...~z` de K refs, o decoder aloca `K - 1` IDs
seguindo a regra:

```
ID_1 = a + b
ID_2 = ID_1 + c
ID_3 = ID_2 + d
...
ID_{K-1} = ID_{K-2} + z
```

Onde `+` é concatenação de strings. O ID final (`ID_{K-1}`) é o
valor "exportado" do chain — pode ser referenciado por outras linhas.

IDs intermediários também são alocados (e podem ser referenciados se
um alias for definido para essa sub-composição em algum momento).

### Body-order de IDs

IDs são atribuídos pela ordem de aparição no body — interleaved entre
atoms (`'lit'` pieces) e composições (`'composition_def'`). Isso
permite decoder single-pass sem preâmbulo separado.

## Por que o nome

| Componente | Significado |
|---|---|
| **Hierarchical** | Composições podem conter refs que são elas próprias composições. Estrutura natural em árvore de níveis. |
| **Compositional** | A operação central é COMPOSIÇÃO (concat com nomeação). Distingue do mero concat. |
| **Coding** | Codifica em **texto** (não bytes binários). Output legível e inspecionável. |

## Diferencial vs literatura

### vs Re-Pair (Larsson & Moffat 1999)

Re-Pair substitui pares de **bytes/símbolos** mais frequentes
recursivamente até não haver par com freq ≥ 2. Constrói uma gramática
context-free.

HCC compartilha o espírito de "substituir o que repete" mas:
- Trabalha em **tokens** de OBAT (não bytes).
- Distingue `,` (efêmero) vs `~` (cria ref) — **semantica explícita**
  no output. Re-Pair não tem essa distinção (toda substituição cria
  regra de gramática).
- **Auto-naming implícito** (IDs sequenciais pela ordem). Re-Pair
  precisa dicionário explícito de regras.
- **Output textual** (não binário). Re-Pair tipicamente output binário.

### vs Sequitur (Nevill-Manning & Witten 1997)

Sequitur infere gramática online unindo digrams (pares de símbolos
adjacentes) que repetem, mantendo a gramática mínima.

HCC é **offline** (vê body completo antes de decidir, então itera
greedy). Mais simples de implementar. Sequitur mantém invariantes
fortes; HCC só requer net > 0.

### vs LZW (Lempel-Ziv-Welch 1984)

LZW cresce dicionário progressivamente conforme lê o stream. HCC
também cresce dicionário (composições) mas via **greedy global** com
heurística de net, não progressivamente.

### vs Templates / Macros em programação

O operador `~` lembra macro/template — define grupo nomeado para
reuso. HCC formaliza com algebra explícita de custo (net) e
constraints para garantir correção (body-order).

## Inovações próprias do HCC

1. **Marker semântico dual** (`~` vs `,`): única na literatura — texto
   compresso distingue "criar ref" de "concat só nesta vez".
2. **Auto-naming implícito**: IDs por ordem de aparição, sem preâmbulo.
   Permite decoder single-pass.
3. **Espaço unificado de refs**: detector vê atomic + virtual na mesma
   fila → captura pairs como `(atom_X, composição_anterior)` que
   detectores tradicionais perdem.
4. **Body-order constraint**: garantia algébrica de correção pra
   inline expansion com pairwise left-assoc.
5. **Range como caso particular**: `a..b` é açúcar para
   `a~a+1~...~b`. Sintaxe limpa para sequências consecutivas comuns.
6. **Output textual sem brackets**: arquivo é pura sequência de
   linhas, LF only. Inspecionável, processável por ferramentas
   line-oriented (grep, sed, etc.).

## Onde se encaixa

HCC é a **camada 2** do TCF. Pipeline:

```
Lista de strings (coluna de dados)
       ↓
   OBAT (camada 1)
       ↓ tokens raiz
   HCC (camada 2)
       ↓ texto TCF (com `~`/`,`, refs numéricos, escapes)
   Arquivo TCF
```

A implementação canônica está em
[`src/tcf/composicional/syntax.py`](../../src/tcf/composicional/syntax.py).
Origem experimental:
`experiments/lab/dirty/2026-05-16-M8-virtual-refs-clean-output/M8-A-detector-unificado/syntax.py`
(intocado desde 2026-05-16).

## Conexões

- [OBAT](OBAT.md) — camada que produz os tokens raiz consumidos por HCC
- [TCF-format](TCF-format.md) — posicionamento do formato
- `experiments/lab/dirty/notas/historia-dirty-lab.md` — narrativa do
  desenvolvimento (codnome M8.A)
- `experiments/lab/dirty/notas/no-funcional-marca-e-troca.md` —
  direção futura: extensão de HCC com slot variável

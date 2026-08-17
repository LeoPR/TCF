# Resultado — o `.8H`: o header não é o problema, o candidato único é

23 tabelas / 186 colunas do corpus + 14 capacidades sintéticas. **0 falhas.**

---

## 1. O estudo prévio achou uma DEFASAGEM documental

O documento canônico do header do `.8H` é o `tcf8h-header-checklist.md` (2026-07-06). Ele
descreve o **protótipo** e diz literalmente: *"nada disto está weldado em `src/tcf` ainda"*.
O weld veio depois (ADR-0033, 2026-07-14) e a gramática real tem **mais coisas**:

| | checklist 2026-07-06 | weld, medido hoje |
|---|---|---|
| espaço após o magic | `#TCF.8H ` | **sem espaço** — o checklist marcava como pendente, o weld resolveu ✓ |
| tag de TIPO por folha | não existe | **`n`/`b` após o size** (`n:6n`, `b:8b`) |
| máscara de nulo/ausente | citada, sem glifo | **`?` no nome** (`a?:5`) |
| raiz não-lista | não existe | **`#O`** objeto · **`#V`** escalar · **`#E`** vazio |
| contagem de array | `[` | **`#` + `[`** (`tel#:6[`) |

**O checklist precisa ser atualizado ou marcado como histórico** — hoje ele descreve algo que
não é o que o código emite.

## 2. A gramática real, capacidade por capacidade (todas com RT)

```
plano 1 campo         #TCF.8Hnome
plano 3 campos        #TCF.8Ha:6,b:6,c
TIPOS                 #TCF.8Hs:5,n:6n,f:9n,b:8b
objeto aninhado       #TCF.8Ho{rua:7,n
array de escalares    #TCF.8Htel#:6[
array de objetos      #TCF.8Ht#:6[n
NULL                  #TCF.8Ha?:5
ragged                #TCF.8Ha:4,b?:4
raiz objeto           #TCF.8H#Oa
raiz escalar          #TCF.8H#V\z
dict vazio            #TCF.8H#E
lista vazia           #TCF.8          (cai no flat)
```

**Dez glifos**, dos quais dois são herdados do `.8M` (`:N`, `,`) e sete são exclusivos
(`{}`, `[`, `#`, `?`, `#O`, `#V`, `#E`).

## 3. O header do `.8H` NÃO é o problema — 0,11% do wire

| | |
|---|---:|
| header, corpus inteiro | **2.943 B** |
| wire, corpus inteiro | 2.777.913 B |
| **header como % do wire** | **0,11%** |
| os nomes dentro do header | 1.796 B = **61% do header** |

Mesma conclusão a que o `.8M` chegou (O-FMT-11, fechado): **em payload de tamanho real o
header é ruído**. Simplificá-lo é otimização de terceira ordem — e, como no `.8M`, o único
campo grande é o dos **nomes** (61%), cujo corte tem o mesmo preço de sempre: a ordem vira
contrato.

## 4. O candidato único — agora CONFIRMADO NO CORPUS

| | bytes |
|---|---:|
| `.8M` (23 tabelas) | 2.257.869 |
| `.8H` (as mesmas) | 2.777.913 |
| `.8M` com `fallback=False` (sem candidatos) | 2.777.844 |
| **overhead do `.8H`** | **+520.044 B (+23,0%)** |
| **residual** (`.8H` − `.8M` sem candidatos) | **+69 B** |

**O conjunto de candidatos explica 99,99% do overhead, no corpus inteiro.** O residual de 69 B
em 520.044 é ruído de grafia do size.

Amplitude por tabela: de **0%** (`region`, 5 linhas) a **+113%** (`wine-quality`, 42.856 →
91.434 B). As grandes ficam entre +4% (`partsupp`) e +59% (`lineitem`).

Antes isto estava medido em **uma** tabela (adult-census, 99,986%). Agora são 23, e o número
segurou.

## 5. Os estágios duplicados — e por que unificar o alfabeto seria ERRADO

Três funções com o **mesmo nome** nos dois módulos, e as três **divergem**:

| função | `.8H` | `.8M` | |
|---|---:|---:|---|
| `_esc_name` | 31 L | 17 L | divergem |
| `_unesc_name` | 39 L | 13 L | divergem |
| `_parse_meta` | **165 L** | 58 L | divergem |

O `hierarchical.py` **não importa nada do `multi`** — e o comentário no código admite:
*"portado do `.8M`"*. É **cópia**, não compartilhamento.

**Mas a divergência é justificada**, e isso é o achado que muda a recomendação. Os dois
escapam alfabetos **diferentes**, e corretamente:

- só o `.8M` escapa **`=`** — é separador dele, o `.8H` não usa;
- só o `.8H` escapa **`{`, `}`, `[`, `]`, `?`, `#`** — são os glifos dele, o `.8M` não usa.

RT com 13 nomes hostis (`a,b`, `a=b`, `a{b`, `a#b`, `a?b`…) **fecha nas duas rotas**.

> **Unificar o ALFABETO seria um bug.** O que caberia unificar é o **MECANISMO**: um escapador
> parametrizado pelo alfabeto, usado pelos dois. É refactor de `.9` (legibilidade para o port),
> não ganho de byte — e vale principalmente pelo objetivo-linguagem, porque hoje a mesma ideia
> está escrita duas vezes de dois jeitos.

## 6. As opções, com tamanho

| opção | tamanho | bloqueio |
|---|---|---|
| **dar candidatos ao `.8H`** (`T-8H-UM-CANDIDATO-SO`) | **+23% do corpus** — o maior item aberto do formato | precisa de lugar no meta para declarar o modo |
| unificar o **mecanismo** de escape/parse (3 funções) | 0 bytes; ganho de manutenção e de port | nenhum — é refactor |
| simplificar o **header** | **0,11% do wire** | — não vale |
| cortar os **nomes** do header | 61% de 0,11% | a ordem vira contrato |

## 7. O que isto muda na fila — e é uma reordenação

O `T-META-NAO-DECLARA-MODO` (B1) era o gargalo do Grupo A, e o Grupo A vale **2,3%** no `.8M`.

**Mas o `.8H` precisa exatamente da mesma coisa** — um lugar no meta para declarar o modo de
cada coluna — e ali vale **+23%**, dez vezes mais.

**Então B1 não é o gate de um item de 2,3%: é o gate de um item de 23%.** E o `.8H` tem uma
vantagem estrutural para isso: o meta dele **já declara por folha** (`nome:size` + tag de tipo),
então o slot onde o modo entraria **já existe na gramática** — diferente do `.8M`, onde o
marcador tem de vir antes do size e esbarra no alfabeto seguro.

## 8. Ressalvas

- **Amostra de 2000 linhas por tabela**, janela contígua do meio (régua do lab `0530`).
- **`NULL` vira string vazia** — a comparação `.8M`×`.8H` usa os mesmos valores em ambos, então
  é justa, mas nenhuma das duas está exercitando nulo de verdade aqui.
- **O `.8H` está sendo medido em dado RETANGULAR**, que é o caso onde ele é mais desfavorecido.
  Com aninhamento real ele representa o que a tabela plana não representa, e a comparação
  deixa de existir. **Os +23% são o custo de usar o `.8H` onde o `.8M` daria conta** — não o
  custo do `.8H` no seu domínio.
- **O `tpch-sf001` é prefixo do `sf01`** e as duas entram: o TPC-H tem peso dobrado.

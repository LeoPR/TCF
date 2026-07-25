---
title: Levantamento — null e os outros tipos (estado medido + espaço em aberto)
type: levantamento
status: aberta
created: 2026-07-24
related:
  - experiments/lab/dirty/notas/2026-07/substituicao-indices-especiais-plano.md
  - experiments/lab/dirty/notas/2026-07/tipos-meta-grupo-fluxo.md
  - experiments/lab/dirty/2026-07/2026-07-13/2026-07-13-1921-dataseth-typed-header-domain/
  - experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md (H-SUBST-INDEX-01, H-HIER-SCALAR-01, H-PROFILE-01, H-TYPE-01/02)
  - docs/adr/0034-header-default-100-porcento-single-col.md
---

# Levantamento — null e os outros tipos

Pedido do owner (2026-07-24), antes de abrir o item 2 (referência implícita / índices
reservados). **Nada foi soldado.** Tudo abaixo é estado medido ou espaço de decisão.

---

## 1. O que já existe HOJE (medido contra o `src/tcf` real)

**null NÃO é um vazio no formato — já tem mecanismo.** É uma **máscara def-level de 3
estados** num canal `?` separado, dentro do `.8H`:

| estado | char | significado |
|---|---|---|
| presente | `.` | o valor está nas colunas de dado |
| ausente | `-` | a chave não existe naquele registro (P1) |
| null | `0` | a chave existe e vale null (P3a) |

Em array, há uma **element-mask** de 2 estados no mesmo esquema (P3b). O canal de máscara é
uma coluna como outra qualquer — passa pelo mesmo compressor L1.

**As 4 vias funcionam hoje** (verificado, RT exato nas 5 formas):

```
ausente  ≠  null  ≠  "null" (string)  ≠  "" (string vazia)
```

Wire: `#TCF.8Ha?:13:8,b\n.\n\0\n*2|^1\n-\nx\nnull\n\n*5|p\n` — a máscara `.`/`0`/`^1`/`-`
viaja separada dos literais `x`/`null`/`""`.

### Situação por tipo

| tipo | hoje | onde |
|---|---|---|
| `str` | flat `#TCF.8` | core |
| `bool` | `#TCF.8b` (core ou denso b1) | weld #4, 2026-07-24 |
| `int` / `float` | `.8H` com tag `n` | hierárquico |
| `None` | máscara `?` (3 estados) | hierárquico |
| ausência | máscara `?` (`-`) | hierárquico |
| `NaN` / `±Inf` | **fail-loud** (RFC 8259) | fronteira |
| tipos mistos numa coluna | **fail-loud** | fronteira |

## 2. Quanto custa o null hoje (medição nova)

Isolando o envelope: comparei `.8H` **com e sem** null na mesma forma (o envelope
flat→`.8H` custa só **+2 B**, não é ele que domina).

| n | 0% null | 1% | 10% | 50% | 90% |
|---:|---:|---:|---:|---:|---:|
| 10 | 27 | 39 | 39 | 39 | 36 |
| 100 | 297 | 310 | 316 | 199 | 90 |
| 1000 | 2997 | 3074 | 3098 | 1928 | 712 |
| 5000 | 14997 | 15355 | 15459 | 9609 | 3473 |

Três leituras:

1. **O custo é quase INSENSÍVEL à densidade** na faixa baixa: 1% e 10% de null custam
   praticamente o mesmo (3074 vs 3098 em n=1000). A máscara é um stream altamente repetitivo
   e o RLE do core a esmaga.
2. **Em densidade alta o total ENCOLHE** (50%/90%): null substitui dado, e o dado é mais caro
   que a marca.
3. **A dor é em n PEQUENO**: n=10 vai de 27 → 39 B (**+44%**); n=1000 vai de 2997 → 3098
   (**+3%**). Ou seja, o alvo do índice reservado é exatamente o regime de payload minúsculo
   — coerente com o foco declarado do owner.

**Sem null, não se paga nada**: `masked` só liga se a coluna tem ausência ou null. Pay-per-use
já é a regra.

## 3. O que o plano de índices reservados propõe

(De `substituicao-indices-especiais-plano.md`, owner 2026-07-15.)

A tabela de referências da coluna **nasce pré-semeada** com os especiais nos índices 0..k−1,
declarados por um **byte combinatório** no header (até 8 especiais). No corpo, um especial é
**uma referência como outra qualquer**.

**Por que não é o que já foi refutado**: o lab `2026-07-13-1921` refutou "null = índice"
porque **stringificava** null → token `"null"`, que **colidia** com a string real `"null"`. O
plano usa **sentinela não-string** e reserva **posicional na tabela** — strings reais
(inclusive `"null"` e `""`) continuam sendo descobertas e ganham índices ≥ k. Sem colisão.

**O maior ganho não é byte, é unificação**: null-em-campo (P3a) e null-em-elemento (P3b) caem
no MESMO mecanismo. Hoje são duas máscaras diferentes.

## 4. A pergunta do owner: null sempre no índice 0, ou declarado?

| | sempre no 0 | declarado no header |
|---|---|---|
| header | **limpo, zero declaração** | paga a dica quando ocorre |
| custo | desloca todo índice de dado em +1 | quem não tem null não paga nada |
| lógica | menos condicional | mais um ramo |

### Medição do deslocamento — e por que ela ainda NÃO está fechada

Teoricamente o deslocamento é **O(log n)**, não proporcional: mudar todo índice `i` para `i+1`
só muda o comprimento nas fronteiras de dígito (9→10, 99→100, 999→1000). Para 1500 refs
únicas, +3 B **se cada ref aparecesse uma vez**.

Mas refs **se repetem** no corpo, então o custo real é a **frequência** das refs que cruzam
fronteira, não a contagem de refs únicas.

Tentei medir com um proxy — prefixar um valor único empurra todo índice +1 — com controle
(append não desloca; prepend desloca; a diferença seria o shift puro). Resultado em D1-D9:

| dataset | shift puro |
|---|---:|
| D1, D4, D5, D8 | +0 B |
| D2, D6, D7 | +1 B |
| D3 | +2 B |
| **D9-frequencia-alta** | **+62 B** ⚠ |

**O proxy é INVÁLIDO** — e o D9 mostra por quê. Comparando os wires:

- base: 5 linhas, com `*7+1|` e `*9+1|` (seq-RLE colapsando 20 valores quase-idênticos)
- prepend: 14 linhas, seq-RLE desfeito, tokenização diferente (`value*-x*` → `value*-*x*`)

O **OBAT é um tokenizador ONLINE**: o primeiro valor semeia o vocabulário. Inserir um valor
não desloca índices — **re-semeia o tokenizador inteiro**, e a cascata (min_len, cadence,
seq-RLE) domina qualquer efeito de dígito.

> **Conclusão metodológica**: o custo do pré-semeio **não pode ser medido inserindo dado**. Só
> pode ser medido **pré-semeando a tabela de referências** — ou seja, exige o protótipo. Os
> +0..+2 B de D1-D8 são indicativos (e coerentes com a teoria de fronteira de dígito), mas não
> são prova, porque carregam a mesma contaminação em grau menor.

## 5. Tensão a reconciliar: bool

O weld #4 (2026-07-24) pôs bool em `#TCF.8b` com **domínio implícito fixo** (false=0/true=1)
vindo do FORMATO. O plano de índices reservados propõe que **bool migre para o framework de
índices** (índice 1=`True`, 2=`False`), argumentando que resolve `"true"`-string vs `True`-bool
"mais limpo que a tag".

**São dois desenhos diferentes para a mesma coisa** e ninguém reconciliou:

- a tag `b` resolve pelo **cabeçalho** (o tipo constrange o domínio da coluna inteira)
- o índice reservado resolve por **QUAL índice** (por valor, dentro de uma coluna misturada)

Não são incompatíveis — a tag é por-coluna, o índice é por-valor — mas **decidir qual é o
canônico antes de soldar o segundo** evita ter dois caminhos para o mesmo resultado. Isto não
estava registrado como conflito em lugar nenhum; anotado aqui.

## 6. Outros tipos — o que está aberto

- **NaN / ±Inf** (H-HIER-SCALAR-01): fail-loud hoje por RFC 8259. O owner já registrou que
  pertencem ao **domínio de folhas da estrutura**, não ao JSON. Três alternativas abertas: tag
  tipada explícita · domínio tipado + índices bN · string especial com escape reversível. O
  byte combinatório do plano já reserva espaço para eles.
- **Ausência**: hoje máscara `-`, declarada como "forma de TRABALHO". **Forma definitiva em
  aberto** — se índice ganhar, presença e null unificam no mesmo framework.
- **Número**: fica na **dedução** (cardinalidade infinita não cabe em índice reservado).
- **Ordem canônica dos reservados**: qual bit → qual índice. Precisa ser fixada para
  determinismo; ainda não foi.
- **H-PROFILE-01**: a escolha máscara × índice foi registrada como candidata a viver sob
  "perfil de uso" (API/transmissão × armazenamento), com **default por medição em massa
  depois**. O requisito é o código nascer preparado para os dois.

## 7. O que eu recomendaria como próximo passo

O gargalo é a medição do §4, e ela **exige o protótipo** — não dá para decidir "sempre 0 vs
declarado" no papel nem por proxy. Um protótipo de pré-semeio **no lab** (sem tocar `src/tcf`)
que:

1. pré-semeie a tabela de refs com null no 0 e meça o Δ real contra a máscara atual;
2. cubra os dois regimes que a §2 separou — **n pequeno** (onde a máscara dói, +44%) e **n
   grande** (onde ela já é barata, +3%);
3. varra densidade de null (1%/10%/50%/90%), já que a §2 mostrou que a densidade quase não
   muda o custo da máscara — se o índice tiver comportamento diferente, é aí que aparece;
4. teste as 4 vias (§1) sob o novo mecanismo, que é a assinatura de corretude do P3.

Só com isso a pergunta "null entra de graça sempre?" tem resposta medida em vez de intuída.

# BOOL vs BINÁRIO vs LOW-CARD — revisão pedida pelo owner (para decidir) [revisão]

**Data**: 2026-07-24 17:10. O owner pediu revisão de 3 pontos ao inspecionar os wires do `#4`:
(1) `n` em hex; (2) referência implícita do `false`; (3) **a confusão bool × binário × string low-card**.
Tudo abaixo é MEDIDO no código real (`src/tcf` pós-weld #4). Não decide — organiza pra decidir.

## 1. `n` em hex — DESCARTAR (ambiguidade + ganho ~zero)

`#TCF.8b164` = tag `b` + modo `1` + `n`=64. Pôr `n` em hex:

- **Ambiguidade real**: hex usa `a`–`f`, e **letras são o namespace reservado pros SUBTIPOS** do `<modo>`.
  Modo e `n` são colados ⇒ `#TCF.8b1b…` fica indecidível (dígito-hex do `n` ou outro campo?).
- **Ganho medido ~nulo**: `n=64` → `40`hex = **0 B** (2 chars nos dois). Só ganha 1 B em faixas
  estreitas (100–255, 1000–4095, …). E o `n` é **8,7%** do wire em n=64, **~0%** em n grande.

⇒ custo alto (colide com subtipos), ganho zero no caso real. **Não vale.**

## 2. Referência implícita do `false` — o ganho NÃO ESCALA (achado que muda a conclusão)

Eu havia proposto `T`/`F` medindo 352→314 B (−11%) num agregado. **Estava enganoso**: o
**mecanismo de referência do core já é NUMÉRICO** (`^N` = N-ésimo valor único por 1ª aparição —
a intuição do owner está certa). Então o literal aparece **1 ou 2 vezes no corpo inteiro**, nunca por
elemento:

| caso | literal aparece | corpo `true/false` | corpo `T/F` | ganho |
|---|---:|---:|---:|---:|
| alt n=8 | 2× | 29 B | 22 B | **7 B** |
| alt n=64 | 2× | 197 B | 190 B | **7 B** |
| alt n=512 | 2× | 1541 B | 1534 B | **7 B** |
| const n=512 | 1× | 10 B | 7 B | **3 B** |

**O ganho é CONSTANTE (3–7 B), não proporcional** — 0,45% em n=512. O `^N` já faz o trabalho de
"referência implícita" que o owner queria. ⇒ trocar `true/false` por `T/F` **compra quase nada** e
paga legibilidade. (E `0`/`1` é pior: dígito inicia REF no core ⇒ vira `\0`/`\1`, paga escape.)

## 3. Bool × binário × low-card — a distinção que o owner pediu

**Não há ambiguidade no WIRE** (medido): string real `['T','F',…]` vai pro **órfão** (sem header);
bool vai pra `#TCF.8b…`. O header separa. **Mas há custo de INSPEÇÃO**: `*64|false` é auto-evidente;
`*64|F` exige olhar o header pra saber se é bool ou string. Isso reforça o item 2.

### Os dois eixos (que o `bN` do registry conflaciona)

| eixo | o que é | exemplo |
|---|---|---|
| **TIPO (semântica)** | qual dataset volta | `bool` (True/False), `number`, `string` |
| **MODO (representação física)** | como o corpo carrega | core/RLE, denso bit-packed a `w` bits |

**São ORTOGONAIS.** O que o `b` do `#TCF.8b` significa hoje no código: **TIPO bool** (tag), e o char
seguinte (`1`) é a **LARGURA** do modo denso. **Isso já está separado corretamente** — quem conflacia
é o *nome* "bN" do registry (`b1/b2/b4`), que soa como "tipo b + largura N" mas foi cunhado como
"largura N".

### A diferença que REALMENTE importa: de onde vem o DOMÍNIO

| caso | símbolos | domínio | viaja no arquivo? |
|---|---|---|---|
| **bool** | 2 | `{false,true}` — **universal, do FORMATO** (dicionário da versão) | **NÃO** (implícito) |
| **low-card string** | k≤16 | os k valores — **específicos DAQUELE dado** | **SIM** (embutido) |

Os dois cabem em bit-packing (`w=1` pra 2 símbolos), mas **só o bool tem domínio implícito**. Uma
coluna de strings `['T','F',…]` também caberia em `w=1` — mas teria que **embutir** quais são as 2
strings. É por isso que o `#4b` implementou denso **só pra bool** e o `n`/`s` denso ficou de fora
("domínio embutido" é trabalho à parte, medido nos labs 1759/1857 como o candidato bN low-card).

⇒ Respondendo ao owner: **`b` remete ao TIPO bool, não a "binário"**. O "binário" é o *modo* (a
largura). E sim — **um grupo de strings que cabe binariamente é outro caso** (low-card com domínio
embutido), que hoje NÃO usa a tag `b`; usaria `s` + modo denso + domínio, quando/se for implementado.

## Recomendação (não é decisão)

1. **Hex no `n`: descartar** (ambiguidade com subtipos, ganho 0 B).
2. **Manter `true`/`false`** no corpo core — o `^N` já é a referência implícita; `T`/`F` compra 3–7 B
   constantes e custa legibilidade. **A economia real do bool já veio do modo denso** (bit-packing),
   que é onde o ganho escala.
3. **Nomenclatura**: separar no vocabulário `TIPO` (tag: `b`=bool) de `MODO/LARGURA` (`1/2/4/8`), e
   registrar que **low-card string ≠ bool** (domínio embutido vs implícito) — evita que o "bN" do
   registry siga sugerindo que são a mesma coisa.

Relaciona: [namespace do `<modo>`](2026-07-24-0322-modo-namespace-largura-e-subtipos.md) ·
[camada explícita↔implícita](2026-07-24-0100-camada-explicita-vs-implicita-fecha-cicloA.md) ·
[registry de chars](tcf8-header-char-registry.md) · labs `1759`/`1857` (bN low-card, domínio embutido).

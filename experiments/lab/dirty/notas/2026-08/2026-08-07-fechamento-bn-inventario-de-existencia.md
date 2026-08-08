# Fechamento do bN — inventário de EXISTÊNCIA das facetas de bits

**2026-08-07 · auditoria, não medição**

Critério desta nota, definido pelo owner: **`.8` = completude, `.9` = otimização.** A
pergunta aqui não é "qual é melhor" nem "quanto custa" — é **existe e funciona?**. Bench
entra só pra confirmar *existência* e *magnitude importante*, nunca como decisor de
precisão. Se para a mesma compressão houver formas diferentes, **registra as duas e escolhe
uma por compressão**.

---

## Inventário — todas as facetas de bits do `.8`

| faceta | wire | encoder emite? | decoder aceita? | ADR | conferido |
|---|---|:-:|:-:|---|---|
| **bN domínio, modo B** (domínio primeiro) | `#TCF.8B<w><n>` | ✅ rota flat | ✅ | 0036 | `#TCF.8B1c` |
| **bN domínio, modo C** (domínio por último) | `#TCF.8C<w><n>` | ❌ nunca | ✅ **RT ok** | 0036 | decodável-não-emitido |
| **denso b1** (bool, domínio implícito fixo) | `#TCF.8b1<n>` | ✅ rota tipada | ✅ | 0037/0038 | `#TCF.8b1c`, 47 B |
| **denso b2** (bool ternário com null) | `#TCF.8b2<n>` | ✅ rota tipada | ✅ | 0037 | `#TCF.8b2c`, 79 B |
| **denso b4 / b8** | `#TCF.8b4…` | ❌ | ⛔ **fail-loud** | — | `largura denso invalida w=4 p/ bool (esperado 1 ou 2)` |
| **lazy bool `bB`** (bool+str+null) | `#TCF.8bB<w><n>` | ✅ | ✅ | 0039 | `#TCF.8bB228\ntalvez\n=nJy…` |
| **tag `s`** (string tipada) | `#TCF.8s` | ❌ nunca | ✅ decodável | — | `decode('#TCF.8s\naa\nbb\n')` → `['aa','bb']` |
| **polaridade** (camada de borda) | sufixo de pontuação | ✅ | ✅ | 0035 | compõe com todas |
| **tipado `n` + bits** | `#TCF.8n<modo>` | ❌ | ❌ | — | **NÃO EXISTE** |

**Testes**: 252 passando em `test_dominio_bn.py` · `test_typed_singlecol.py` ·
`test_polaridade.py` · `test_null_slot0.py`. Classes cobrindo `TestBoolDensoFloor`,
`TestBoolDensoB2Ternario`, `TestDensoHexN`, `TestLazyBool`, `TestModoLote`,
`TestFronteirasDaLargura`, `TestFailLoud`.

Contraprova de comportamento: [EXP-016](../../clean/EXP-016-bn-familia-bits/), 72 casos,
11 famílias, 0 falhas.

---

## Veredito: o bN está fechado, **menos um buraco**

### ✅ O que está completo

- **A mecânica existe e funciona** em todas as facetas emitidas, com RT conferido.
- **b4/b8 falham alto** — reservado que recusa, não reservado que erra calado. É o
  comportamento certo pra um slot preparado.
- **Não há sobreposição perdida entre `b1/b2` e `bN`.** Para bool nativo o denso vence
  sempre (domínio implícito não gasta bytes): 47 B contra 57 B (sem null) e 79 B contra
  92 B (com null). Estarem em rotas que não competem **não perde nada** — conferido.
- **A polaridade compõe** com todas as facetas (camada de borda; encode polariza depois,
  decode despolariza antes).

### ❌ O buraco: coluna NUMÉRICA de baixa cardinalidade não tem faceta de bits

| coluna (n=200) | hoje | com bN sobre a grafia (+1 B de tag) |
|---|---:|---:|
| `int` 0/1 | **608 B** | **55 B** |
| `int` 0..3 | **604 B** | **93 B** |
| `float` | **612 B** | **59 B** |

É o `T-BN-TIPADO`. Pelo critério do owner — *existência* e *magnitude importante* — este é
o único item da família que **falta existir**, e a magnitude é da ordem de **−85 a −91%**.

**E a gramática que ele precisa já existe e está provada.** O bloqueio registrado na
ADR-0036 era "exige tag DENTRO do cabeçalho (`#TCF.8nB…`), que é grafia nova". Não é
grafia nova: o **`bB` faz exatamente isso hoje** — tag no índice 6, modo no índice 7,
depois `<w><n>`, bloco, `=`, b64:

```
#TCF.8bB228\ntalvez\n=nJycnJycnJycnA      ← lazy bool, EMITIDO hoje
#TCF.8nB<w><n>\n<domínio>\n=<b64>         ← o que falta: mesma forma, cast numérico
```

O que muda é só o **cast na volta** (string → `int`/`float`) e o gate de canonicidade da
grafia numérica. O corpo é o mesmo `candidatos()` de sempre.

---

## Duas formas para a mesma compressão — a regra do owner aplicada

### Caso 1 — modo B × modo C: **a escolha NÃO foi por compressão**

As duas formas estão registradas (o `C` é decodável). Mas o `C` é **1 byte menor** que o
`B` em todos os casos medidos, e escolhemos o `B`.

Pela regra ("escolhemos uma por compressão"), o `C` deveria ganhar. Escolhemos o `B` por
**streaming**, e agora isso tem número (lab `2026-08-07-2055`): pra emitir qualquer valor,
o `B` precisa de **2,1–7,0%** do fio e o `C` precisa de **100%** — o domínio dele vem
depois do payload.

> **Ponto de decisão do owner.** É a única exceção à regra na família. Confirmar (streaming
> vale 1 byte) ou reverter (compressão manda). Está registrado dos dois lados; nada
> bloqueia.

### Caso 2 — `b1/b2` × `bN`: escolha por compressão, ✅ certa

Domínio implícito vence domínio explícito por construção. Conferido acima. Nada a fazer.

### Caso 3 — polaridade: forma única, sem alternativa

Não há duas formas; há ligado/desligado, e o FLOOR decide por byte. O custo em CPU
(lab `2026-08-07-2055`) é assunto do `.9` (`T-FLOOR-MULTIVETOR`), **não** de completude.

---

## O que fica pro `.9`, explicitamente

Nenhum destes é buraco de completude — são otimização, e é onde eles devem ficar:

| ticket | por que é `.9` |
|---|---|
| `T-BN-LARGURA-VARIAVEL` | `w = ceil(log2(k))` arredonda pro inteiro; `k=5` gasta 3 bits onde a entropia pede 2,32 |
| `T-DENSO-PADDING` | 1–2 B de padding `=` dedutível de `n` e `w` |
| `T-B64-BITS-MORTOS` | trocar O(n) por O(1) na validação; custo atual é 0,17% |
| `T-FLOOR-MULTIVETOR` | o `min()` decide só por byte |
| `T-BN-LOTE` | opt-in de emissão do modo `C` |
| `T-BN-GZIP` | comportamento sob compressor externo |
| `T-BN-MULTICOL` | escopo `.8M`, outra rota |

---

## Detalhe não esgotado (owner apontou): domínio com estrutura interna

`EXP-016/outputs/dom-datas-incrementais.tcf`:

```
#TCF.8B2c8
\2026-\01-\0*\1
1\2
1\3
=GGGG…
```

Três datas (`2026-01-01/02/03`) cabendo em ~20 B de domínio — o **OBAT/afixo do core
comprimindo dentro do bloco de domínio do bN**, sem uma linha de código nova. A mecânica
existe e funciona (RT conferido no EXP-016).

**O que não foi detalhado**: quanto essa composição rende por *natureza* de domínio (data,
CPF, ID sequencial, enum textual). Isso é trabalho dos **tipos específicos**, não do
fechamento do bN — fica onde o owner colocou.

---

## Para finalizar o bN no `.8`

1. **Soldar o `T-BN-TIPADO`** — é o único buraco de existência. Gramática já provada pelo
   `bB`; o delta é cast + gate de canonicidade. **Precisa de aprovação explícita: mexe em
   `src/tcf/`.**
2. **Decidir o modo B × C** — confirmar streaming sobre 1 byte, ou reverter. Sem custo
   qualquer que seja a escolha; só precisa ficar registrado como decisão, não como inércia.
3. O resto da lista é `.9`.

Ligações: [manual da família](../../../../docs/reference/familia-bn-bits.md) ·
[EXP-016](../../clean/EXP-016-bn-familia-bits/) ·
[vetores ortogonais](../../2026-08/2026-08-07/2026-08-07-2055-vetores-ortogonais-por-mecanismo/) ·
[ADR-0035](../../../../docs/adr/0035-delimitador-de-polaridade-single-col.md) ·
[ADR-0036](../../../../docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md) ·
[ADR-0037](../../../../docs/adr/0037-denso-b2-ternario-dominio-implicito.md) ·
[ADR-0038](../../../../docs/adr/0038-indice-interno-default-core-tipado-bool.md) ·
[ADR-0039](../../../../docs/adr/0039-lazytype-bool-cabeca-congelada-extras.md)

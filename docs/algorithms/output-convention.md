# Convencao — output TCF oficial

**Data**: 2026-05-16
**Tipo**: nota transversal (convencao tecnica)
**Origem**: user em 2026-05-15/16 observou que brackets `[`/`]` e CRLF
nos outputs de M7 eram scaffolding/efeito-Windows, nao parte do
formato TCF.

## Regras

### 1. Sem delimitadores estruturais `[` e `]`

**Nao usar** `[` no inicio nem `]` no fim do output. O TCF e' uma
sequencia de linhas; o "envelope" e' o arquivo em si (e/ou metadados
externos como header), nao caracteres internos.

Antes (M5/M6/M7):
```
[
linha 1
linha 2
]
```

Agora (M8+):
```
linha 1
linha 2
```

**Por que**: brackets eram scaffolding de inspecao visual (print do
array para arquivo), nao informacao do formato. Adicionam 4 bytes
por arquivo sem ganho semantico.

### 2. Single LF (`\n`) line break

**Nao usar** CRLF (`\r\n`). Apenas LF (`\n`).

**Por que**: TCF e' formato textual independente de plataforma. CRLF
e' artefato de Windows text-mode write. Em Python:

```python
# ERRADO no Windows (gera CRLF):
path.write_text(content, encoding="utf-8")

# CORRETO (preserva LF):
path.write_text(content, encoding="utf-8", newline="")
# OU:
path.write_bytes(content.encode("utf-8"))
```

### 3. O LF final e' TERMINADOR, nao convencao POSIX

O LF final **não é** enchimento de arquivo: é o **terminador do último valor**, num formato em
que o LF **separa valores**. Prova de uma linha:

```
['a', 'b', '']   ->  '#TCF.8\na\nb\n\n'
['a', 'b']       ->  '#TCF.8\na\nb\n'
```

O wire da coluna que **termina em valor vazio** é exatamente o wire da coluna sem o vazio,
**mais um LF**.

**E o par que decide é mais simples ainda:**

```
[]     ->  '#TCF.8
'
['']   ->  '#TCF.8

'
```

**Coluna vazia** contra **coluna com um valor vazio** — os dois datasets diferem em exatamente
um LF. Se o LF fosse **separador** (n valores → n−1 LFs), ambas dariam corpo vazio e seriam
**indistinguíveis**. O terminador carrega **1 bit, e só nesse caso de borda**: pouco, e
suficiente para não ser removível.

> Executável em `tests/test_core_rt.py::test_o_LF_terminador_e_o_que_distingue_vazia_de_um_vazio`
> — é lá que este fato vive na altitude *exemplo* (Strata §5: como=código, exemplo=teste,
> porque=prosa). Esta seção é o *porque*.

**O que o código realmente faz** (medido nas 10 rotas; **nenhuma** aceita "com ou sem"):

| rota | emite LF final? | decode sem ele | decode com um a mais |
|---|---|---|---|
| single-col (flat/spec/n=1) | sim | tolera **com warning** de grafia não-canônica | **ganha um valor vazio**, em silêncio |
| multi-col | **não** | ok | `ValueError` |
| hierárquico | sim | **`HierarchicalError`** (`size N excede o corpo`) | erro |
| tipado bool | **não** | ok | `ValueError` |
| tipado int/misto | sim | tolera com warning | `ValueError` |

> **REFINADO 2026-08-21** (lab [`0500`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0500-lf-final-tem-funcao/)):
> dizer que o LF é "load-bearing" é impreciso. Ele **é 100% recuperável** — dropar o último byte
> e recolocá-lo na recepção devolve o objeto original em 55/55 wires testados. O que impede
> dropá-lo não é ele carregar informação; é que **o magic não determina a convenção** (`#TCF.8M`
> e `#TCF.8b` emitem em uns casos e não em outros), então o receptor não sabe quando recolocar —
> e dropar **sem** recolocar perde valor vazio final, em silêncio.
>
> Exceção real: no **`.8H`** o LF está **dentro do `size`** declarado do bloco. Ali ele não é
> trailing decorativo, é byte contado.

Duas consequências práticas:

- **Não dispense o LF final na transmissão** — hoje. No `.8H` ele está **dentro do `size`** e o
  decode falha; no single-col você perde o valor vazio final (silencioso) e a canonicidade
  (warning). O ganho seria de **1 byte por wire — 4 a 6% em payload minúsculo**, que é o alvo
  declarado do `.8`; por isso o LF segue registrado como **candidato a modo de transporte**
  (H-15-08), viável só se as duas pontas concordarem numa regra por rota.
- **Não acrescente um LF "por educação"** ao gravar em arquivo. Em single-col e multi-col isso
  **acrescenta um valor vazio à coluna, em silêncio**.

Ou seja: grave e transmita **exatamente os bytes que o `encode` devolveu**. Sobre gravar em
disco sem o CRLF do Windows, ver §2.

Quais rotas emitem e quais não **não é uniforme** — assimetria **conhecida e precificada**
(ADR-0045 §3): uniformizar faria o decoder rejeitar em 2 rotas, mudaria semântica numa terceira,
e quebraria o gate D17a (300 → 301 B).

### Sobre `file` / mimetype

Um mal-entendido comum: **o LF final não é necessário para identificação de tipo**. `file` e
libmagic identificam por *sniffing de conteúdo* (bytes iniciais) — e o TCF tem magic próprio e
forte (`#TCF.8…`), que é exatamente o que essas ferramentas usam.

O que **depende** do LF final é a definição POSIX de *linha* (toda linha termina em newline).
Isso afeta ferramentas orientadas a linha — `wc -l` subconta a última, `read` de shell perde a
última, git marca `\ No newline at end of file`. **Não afeta detecção de tipo.**

## Implicacao no byte count

Para D1-D4 (M7.A atual com brackets + CRLF):

| dataset | bytes reportados (LF inmem) | bytes em disco (CRLF) | brackets contam |
|---|---:|---:|---:|
| D1 | 128 | ~141 | 4 |
| D2 | 175 | ~190 | 4 |
| D3 | 194 | ~208 | 4 |
| D4 | 122 | ~133 | 4 |

Bytes reportados ja' contam brackets (4 bytes/dataset) mas NAO CRLF
(porque o tcf string e' LF). Remover brackets = -4 bytes/dataset.

## Decoder

O decoder **não faz nada** com a linha: nem skip, nem strip.

```python
for raw in raw_lines:
    linha = raw          # <- SEM .strip() e SEM skip
```

São **três** não-operações, e cada uma existe porque a operação correspondente causou perda de
dado silenciosa em produção:

| não-operação | o que a operação perdia | quando caiu |
|---|---|---|
| **não `.strip()`** | whitespace de ponta em literais (achado nos comments de `region`/`nation` do TPC-H, com espaço no fim) | 2026-05-18, EXP-012/013 |
| **não skipar linha vazia** | string vazia legítima — o encoder emite `body.append('')` quando o literal é `""` | 2026-05-18, ADR-0006 |
| **não skipar `[` / `]`** | a célula inteira, quando o valor **é** `"["` ou `"]"` | 2026-07-17, `BUG-BRACKET-CELL-LOSS` |

Verificável nos três: `decode(encode(["a ", " b", "c"]))` devolve `['a ', ' b', 'c']` ·
`decode(encode(["a", "", "b"]))` devolve `['a', '', 'b']` ·
`decode(encode(["a", "]", "b", "["]))` devolve `['a', ']', 'b', '[']`.
Implementação em `src/tcf/composicional/syntax.py:910-925`.

A decisão **principal** do [ADR-0006](../adr/0006-empty-string-decode-fix.md) — linha vazia
decoda como string vazia — **continua vigente**; o que caiu foi só a cláusula do skip de
brackets (`0006:39-40,:50`), registrada no índice de ADRs.

## Adotado em M8 e posteriores

Todas as sintaxes em M8 e protótipo seguem esta convencao.

## Conexoes

- [[2026-05-16-M8-*]] — primeira aplicacao
- [[../../experiments/lab/dirty/2026-05-15-M7-refactor/]] — ultimo macro com brackets/CRLF

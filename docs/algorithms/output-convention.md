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

> ⚠️ **CORRIGIDO 2026-08-21** (lab [`0400-lf-final-do-wire`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0400-lf-final-do-wire/)).
> Este parágrafo dizia: *"O último byte do arquivo PODE ser `\n` (separador da última linha,
> estilo POSIX), mas isso é **opcional**. Decoder deve aceitar com ou sem."* **Está errado, e
> seguir isso ao portar o formato quebra o decode.**

O LF final **não é** enchimento de arquivo: é o **terminador do último valor**, num formato em
que o LF **separa valores**. Ele é load-bearing, e a prova é de uma linha:

```
['a', 'b', '']   ->  '#TCF.8\na\nb\n\n'
['a', 'b']       ->  '#TCF.8\na\nb\n'
```

O wire da coluna que **termina em valor vazio** é exatamente o wire da coluna sem o vazio,
**mais um LF**. Tratar o LF final como opcional obrigaria o decoder a **adivinhar** se o
último vazio é enchimento ou dado — **indecidível por construção**.

**O que o código realmente faz** (medido nas 10 rotas; **nenhuma** aceita "com ou sem"):

| rota | emite LF final? | decode sem ele | decode com um a mais |
|---|---|---|---|
| single-col (flat/spec/n=1) | sim | tolera **com warning** de grafia não-canônica | **ganha um valor vazio**, em silêncio |
| multi-col | **não** | ok | `ValueError` |
| hierárquico | sim | **`HierarchicalError`** (`size N excede o corpo`) | erro |
| tipado bool | **não** | ok | `ValueError` |
| tipado int/misto | sim | tolera com warning | `ValueError` |

Duas consequências práticas:

- **Não dispense o LF final na transmissão.** No hierárquico ele delimita o último bloco e o
  decode falha sem ele; no single-col você perde a canonicidade (warning). O ganho seria de
  **1 byte por wire**.
- **Não acrescente um LF "por educação"** ao gravar em arquivo. Em single-col e multi-col isso
  **acrescenta um valor vazio à coluna, em silêncio**.

Ou seja: grave e transmita **exatamente os bytes que o `encode` devolveu**. Sobre gravar em
disco sem o CRLF do Windows, ver §2.

Quais rotas emitem e quais não **não é uniforme** — assimetria conhecida, não regra; registrada
como pendência no lab acima.

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

> ⚠️ **CORRIGIDO 2026-08-16** (auditoria de sincronização docs×código). O texto abaixo
> descrevia um skip que **foi REMOVIDO em 2026-07-17** (`BUG-BRACKET-CELL-LOSS`, aprovação do
> owner): ele **engolia célula calado** — uma coluna com o valor `"["` ou `"]"` perdia o dado
> no decode. Seguir a versão antiga ao portar o formato **reintroduz perda silenciosa de
> dado**, e por isso esta é a correção de maior severidade da auditoria.

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

> **CORRIGIDO 2026-08-17.** A revisão de 2026-08-16 tirou o skip de `[`/`]` deste bloco e
> **deixou o `linha = raw.strip()`** — reintroduzindo, na própria correção, a segunda das três
> perdas. Um port seguindo aquele bloco devolvia `['a', 'b', 'c']` para o wire `'#TCF.8\na \n b\nc\n'`,
> e transformava `"  "` (só espaços) em `""`. As três não-operações agora aparecem juntas
> justamente porque separá-las foi o que permitiu perder uma.

A decisão **principal** do [ADR-0006](../adr/0006-empty-string-decode-fix.md) — linha vazia
decoda como string vazia — **continua vigente**; o que caiu foi só a cláusula do skip de
brackets (`0006:39-40,:50`), registrada no índice de ADRs.

## Adotado em M8 e posteriores

Todas as sintaxes em M8 e protótipo seguem esta convencao.

## Conexoes

- [[2026-05-16-M8-*]] — primeira aplicacao
- [[../../experiments/lab/dirty/2026-05-15-M7-refactor/]] — ultimo macro com brackets/CRLF

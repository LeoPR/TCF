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

### 3. Sem trailing newline desnecessario

O ultimo byte do arquivo PODE ser `\n` (separador da ultima linha,
estilo POSIX), mas isso e' opcional. Decoder deve aceitar com ou sem.

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

**O decoder NÃO skipa `[` nem `]`.** Elas são células válidas como qualquer outra. O encoder
também não as emite como delimitador — o skip era back-compat de um formato *bracketed* (M7 e
anteriores) que não existe mais.

```python
for raw in tcf_text.splitlines():
    linha = raw.strip()
    ...            # sem skip: `[` e `]` sao VALORES, e linha vazia decoda como '' (ADR-0006)
```

Verificável: `decode(encode(["a", "]", "b", "["]))` devolve `['a', ']', 'b', '[']`.
Implementação em `src/tcf/composicional/syntax.py:918-923`.

A decisão **principal** do [ADR-0006](../adr/0006-empty-string-decode-fix.md) — linha vazia
decoda como string vazia — **continua vigente**; o que caiu foi só a cláusula do skip de
brackets (`0006:39-40,:50`), registrada no índice de ADRs.

## Adotado em M8 e posteriores

Todas as sintaxes em M8 e protótipo seguem esta convencao.

## Conexoes

- [[2026-05-16-M8-*]] — primeira aplicacao
- [[../../experiments/lab/dirty/2026-05-15-M7-refactor/]] — ultimo macro com brackets/CRLF

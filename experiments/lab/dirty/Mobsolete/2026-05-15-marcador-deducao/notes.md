# Marcadores deduzidos por recorrencia — gramatica sem ambiguidade

**Data**: 2026-05-15
**Origem**: insight do user — o marcador mais frequente pode virar
**implicito** (sem caractere especial); marcadores raros mantem
caractere. Cabecalho declara o modo default da coluna.

## Tese

Em vez de usar marcadores explicitos sempre (`=N`, `*N`, etc.), o
cabecalho declara o **modo dominante** e linhas no caso comum tem
**forma curta** (so o numero/texto). Excecoes mantem marcadores.

**Resultado**: bytes economizados nos casos comuns; nada perdido nas
excecoes.

## Tipos de marcador implicito por modo

### Modo `=` — line-rle dominante

Cabecalho: `col,=:`. Default = ref linha. Linha so com numero = ref.

```
col,=:
foo            ← literal (1a aparicao)
bar
1              ← ref linha 1 (default mode = line-rle, sem `=`)
baz
1              ← ref linha 1
```

Excecao em modo line-rle: idx de string deveria ter marcador
diferente, ex: `*1` se houvesse string-DICT misturado.

### Modo `>` — prefix-DICT dominante

Cabecalho: `col,>:`. Default = prefix + variavel.

```
col,>:
*user00 1@gmail.com    ← decl prefix idx 1, mid restante
2@gmail.com            ← (modo default) prefix idx 1 + mid
3@gmail.com
=2                     ← excecao: ref linha (com marcador `=`)
```

### Modo `<` — suffix-DICT dominante

```
col,<:
user001 *@gmail.com    ← decl suffix
user002                ← (modo default) var + suffix idx 1
user003
=2                     ← excecao: ref linha
```

### Modo `<>` — bidir dominante

```
col,<>:
*user00 1 *@gmail.com    ← decl prefix + middle + decl suffix
2 @gmail.com             ← Hmm — ambigua! Eh modo bidir mas onde esta o suffix?
```

Ambiguidade: bidir tem 3 partes; sem todas explicitas, decoder
nao sabe se o "2" eh prefix-idx ou middle. **Solucao**:

- Em modo bidir, linhas usam **2 partes** quando o suffix eh o
  mesmo do anterior (default)
- Se suffix muda, precisa explicitar
- Forma curta: `<p-spec> <middle>` reusa ultimo suffix declarado

```
col,<>:
*user00 1 *@gmail.com    ← decl ambos
2                          ← so middle; reusa prefix idx 1 + last suffix
3                          ← idem
=1                         ← excecao linha
```

Mas e quando middle aparece "2" e prefix idx eh "1"? Confuso.

**Resolucao via posicao**: em modo `<>`, sempre **3 tokens** ou
nenhum (so `=N`). Se ha 3 tokens, sao prefix-idx, middle, suffix-idx.

### Sumario das ambiguidades

| Modo | Linha "1" | Linha "1 foo" | Linha "1 foo 2" |
|------|-----------|---------------|------------------|
| `=` | ref linha 1 | impossivel (ambiguo) | impossivel |
| `>` | sem sentido | prefix idx 1 + mid "foo" | erro |
| `<` | sem sentido | mid "1" + suffix idx 1 ("foo" eh idx?) | erro |
| `<>` | sem sentido (raro) | prefix-mid only | prefix idx 1, mid "foo", suffix idx 2 |

**Regra de desambiguacao por contagem de tokens + modo**:

| Modo / Tokens | 1 token | 2 tokens | 3 tokens |
|--------------|---------|----------|----------|
| `=` | ref linha | impossivel | impossivel |
| `>` | impossivel (ou ref linha?) | prefix-idx + mid | erro |
| `<` | impossivel | mid + suffix-idx | erro |
| `<>` | ref linha (=N implicito?) | prefix-mid ou mid-suffix | full bidir |

Ainda ha casos ambiguos. **Solucao mais simples**: marcadores
explicitos para excecoes, default para o caso comum.

### Convencao final proposta

Sempre permitir excecao com marcador:
- `=N` para ref linha (sempre permitido)
- `\!<text>` para literal sem padrao
- `*<text>` para declaracao inline

**Modo do cabecalho** define o que **uma linha "comum"** significa:
- `=` → numero sozinho = ref linha
- `>` → 2 tokens = prefix-idx + mid
- `<` → 2 tokens = mid + suffix-idx
- `<>` → 3 tokens = full bidir

Linhas que nao se encaixam usam excecoes.

## Hipotese a validar empiricamente

A dedução por recorrencia economiza bytes:
1. Cabecalho mais longo (declara modo): ~5-10B
2. Linhas comuns: 2 chars a menos cada (sem `=` ou `*`)
3. Quando dominam: net win

**Net win** quando:
```
linhas_comuns × economia_por_linha > overhead_cabecalho
```

Ex: economia 2B/linha, overhead 5B, net win quando >= 3 linhas
comuns.

## 4 cenarios para teste

| # | Dataset | Modo dominante esperado |
|---|---------|------------------------|
| C1 | 80% linhas duplicadas | `=` (line-rle) |
| C2 | 80% linhas com prefix uniforme | `>` (prefix) |
| C3 | 80% linhas com suffix uniforme | `<` (suffix) |
| C4 | misto 50/50 | escolhe o mais frequente |

## Comparativo

Cada cenario codificado em 2 sintaxes:
- **Explicita**: marcadores em todas as linhas
- **Deduzida**: header declara modo, marcadores so para excecoes

Medir bytes economizados.

## Saida

`./output/<C>/`:
- `literal.txt`
- `explicit.txt`
- `deducao.txt`
- `bytes.json`

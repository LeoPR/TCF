---
title: BUG — decoder confunde texto livre terminado em ':' com header de coluna
type: bug
status: OPEN
priority: 28
discovered: 2026-04-13
discovered_in: test_encode_canonical.py (TPC-H customer.c_comment, lineitem.l_comment)
---

# Decoder Bug: freeform text with ':'

## Problema

O decoder (`src/tcf/decoder.py`) usa a heuristica "linha que termina com ':'
e nao comeca com digito = header de coluna" para detectar blocos de dados.

Quando uma coluna contem texto livre (como TPC-H `c_comment` ou `l_comment`),
valores que terminam com `:` sao interpretados erroneamente como headers.

Exemplo de dado real que quebra:
```
c_comment:
accounts use carefully along the foxes
pending requests:                          ← decoder pensa que e coluna "pending requests"
ly even packages alongside of the final
```

O decoder ve `pending requests:` e acha que e um header de coluna.

## Impacto

- **Dados afetados:** qualquer coluna de texto livre com `:` no final
- **TPC-H:** c_comment (customer), l_comment (lineitem), s_comment, etc.
- **Adult:** nao afetado (sem colunas de texto livre longo)
- **Dados sinteticos anteriores:** nao afetado (nomes curtos sem `:`)

## Causa raiz

`decoder.py` linha ~96:
```python
if line.endswith(":") and not line[0].isdigit():
    # Assume it's a column header
```

Isso e uma heuristica que funciona para dados estruturados mas falha
com texto livre.

## Pesquisa: como formatos consagrados resolvem isso (2026-04-13)

### CSV (RFC 4180) — padrao de ouro

Regra simples e universal (20+ anos):
- Se valor contem `,`, `"`, ou `\n` → envolve em aspas duplas
- Se valor contem `"` → duplica para `""`
- Caso contrario → valor cru

```
"pending requests:"              ← aspas protegem o ':'
"campo com ""aspas"" dentro"     ← aspas duplicadas
normal sem aspas                 ← valor seguro, sem aspas
```

### TSV — proibe caracteres especiais

TAB e newline sao **proibidos** dentro dos valores.
Escape: `\t`, `\n`, `\\`. Parsing trivial (`split('\t')`).

### JSON — backslash universal

`\"`, `\\`, `\n`, `\t`, `\uXXXX`. Robusto mas verboso.

### Parquet/Arrow — binario com length prefix

Nao aplicavel ao TCF (textual).

## Solucoes avaliadas para TCF

### A. Quoting estilo CSV ← RECOMENDADA

Se o valor contem `:` no final, newline, ou comeca com digito+`*`:
→ envolve em aspas duplas. Aspas internas duplicadas.

```
c_comment:
"accounts use carefully"
"pending requests:"              ← aspas protegem o ':'
"campo com ""aspas"" dentro"     ← aspas duplicadas
normal sem aspas
```

**Pros:** consagrado (RFC 4180), LLMs entendem (treinados em bilhoes de CSVs)
**Contras:** adiciona 2 chars por valor que precisa (+1% overhead estimado)

### B. Escape com backslash

`pending requests\:` — compacto mas nao e padrao CSV, confuso em Windows.

### C. Prefixo no header de coluna

`> c_comment` em vez de `c_comment:` — resolve 100% sem tocar nos valores.
Mas muda o formato (quebra v0.2).

### D. Length prefix

`c_comment[27]: ...` — zero ambiguidade, mas feio e verboso.

### E. Excluir colunas de texto livre (workaround atual)

Nao encodar colunas `_comment`. Workaround, nao solucao.

## Decisao

**Solucao A (quoting CSV)** sera implementada quando fizermos TCF v0.3.
Razoes:
1. Consagrada (RFC 4180, 20+ anos)
2. Minima mudanca no encoder (adicionar `_quote_if_needed()`)
3. Minima mudanca no decoder (detectar aspas no inicio)
4. Compativel com formato atual (aspas sao transparentes para valores simples)
5. LLMs entendem aspas (treinados em CSVs)

**Por agora:** workaround E nos testes. Os testes de roundtrip excluem
colunas `_comment` (que sao texto livre). Isso nao afeta testes de
compressao nem accuracy de LLM (texto livre nao e agregavel).

## Impacto estimado nos dados reais

| Dataset | Campos afetados | % valores que precisam de aspas |
|---------|----------------|-------------------------------|
| TPC-H customer | c_comment | ~13% (200 de 1500) |
| TPC-H lineitem | l_comment | ~5% (3000 de 60K) |
| TPC-H supplier | s_comment | ~10% |
| Adult | nenhum | 0% |

Overhead total estimado: <1% do tamanho do TCF.

## Referencias

- [RFC 4180 (CSV)](https://datatracker.ietf.org/doc/html/rfc4180)
- [Handling Special Characters in CSV](https://inventivehq.com/blog/handling-special-characters-in-csv-files)
- [TSV spec v2.0 (GitHub)](https://gist.github.com/rain-1/e6293ec0113c193ecc23d5529461d322)
- [Linear TSV — Open Knowledge Foundation](http://dataprotocols.org/linear-tsv/)

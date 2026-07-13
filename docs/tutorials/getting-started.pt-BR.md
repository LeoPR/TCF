---
title: Getting Started — TCF
type: tutorial
status: active
tags: [tutorial, beginner, compression]
created: 2026-05-27
updated: 2026-05-27
---
<!-- l10n: doc_id=getting-started · lang=pt-BR · source_lang=en · translation_of=getting-started.md · synced=2026-07-01 -->
[English](getting-started.md) · **Português**

> Tradução de [`getting-started.md`](getting-started.md). Se houver divergência, o original em inglês prevalece.
> A régua de atualização é o histórico do git.

# Getting Started — TCF

Neste tutorial, você vai construir uma experiência completa com TCF: codificar uma lista de strings, ver como o formato compacta os dados, decodificar de volta e confirmar que a transformação é lossless. Ao final, você entenderá como TCF funciona tanto em single-column quanto em multi-column.

## O que você vai construir

Você vai codificar um conjunto de dados simples (lista de strings com padrões repetitivos), examinar o texto TCF gerado, medir a economia de bytes, decodificar tudo de volta exatamente como era, e depois expandir o exemplo para tabelas multi-coluna. No total: 10 minutos.

## Pré-requisitos

- Python 3.10 ou superior
- Ter instalado TCF com dependências de desenvolvimento:

```bash
git clone https://github.com/LeoPR/TCF.git && cd TCF
pip install -e ".[dev]"
```

Você pode validar a instalação rapidamente:

```bash
python -c "from tcf import encode, decode; print('TCF OK')"
```

## Passo 1 — Codificar uma lista simples

Vamos começar com três strings que compartilham prefixos comuns. Abra um terminal Python ou crie um arquivo `hello_tcf.py`:

```python
from tcf import encode

data = ["abc", "abcd", "abcde"]
text = encode(data)

print("Dados originais:", data)
print("Texto TCF:")
print(text)
print("Repr:", repr(text))
```

Execute:

```bash
python hello_tcf.py
```

Saída esperada:

```
Dados originais: ['abc', 'abcd', 'abcde']
Texto TCF:
abc
1d
1,2e

Repr: 'abc\n1d\n1,2e\n'
```

O que aconteceu:

- **Primeira string (`abc`)**: gravada como literal, pois é a primeira.
- **Segunda string (`abcd`)**: representada como `1d`. Significa "reutilize 3 caracteres do prefixo da string 1 e adicione `d` ao final".
- **Terceira string (`abcde`)**: representada como `1,2e`. Significa "reutilize 4 caracteres (que cobrem todo `abcd` da string 2) e adicione `e` ao final".

TCF usa referências para strings anteriores, economizando caracteres sempre que há similaridade.

## Passo 2 — Decodificar e confirmar round-trip lossless

Agora vamos decodificar o texto TCF de volta aos dados originais e confirmar que nenhuma informação foi perdida:

```python
from tcf import encode, decode

data = ["abc", "abcd", "abcde"]
text = encode(data)

decoded = decode(text)

print("Original:", data)
print("Decoded: ", decoded)
print("Iguais?  ", decoded == data)
```

Saída esperada:

```
Original: ['abc', 'abcd', 'abcde']
Decoded:  ['abc', 'abcd', 'abcde']
Iguais?   True
```

A propriedade de **round-trip lossless** é garantida por TCF: qualquer dado codificado pode ser recuperado exatamente (ver [ADR-0024](../adr/0024-pre-1.0-versioning-git-as-compat.md) — projeto pré-1.0).

```python
assert decode(encode(x)) == x  # sempre verdade
```

## Passo 3 — Medir a compressão

Vamos quantificar o ganho. Comparamos o tamanho bruto (newline-delimited) com o tamanho TCF:

```python
from tcf import encode

data = ["abc", "abcd", "abcde"]
text = encode(data)

# Calcular tamanho bruto (newline-delimited)
raw_bytes = sum(len(s) + 1 for s in data)  # cada string + 1 newline
tcf_bytes = len(text.encode('utf-8'))

print(f"Raw (newline-delimited): {raw_bytes} bytes")
print(f"TCF encoded:              {tcf_bytes} bytes")
print(f"Taxa de compressão:       {tcf_bytes/raw_bytes*100:.1f}%")
print(f"Economia:                 {raw_bytes - tcf_bytes} bytes")
```

Saída esperada:

```
Raw (newline-delimited): 15 bytes
TCF encoded:              12 bytes
Taxa de compressão:       80.0%
Economia:                 3 bytes
```

Agora vamos ampliar o exemplo com mais dados reais (lista de emails com padrões repetitivos):

```python
from tcf import encode

emails = [
    "joao@gmail.com",
    "joao@hotmail.com",
    "maria@gmail.com",
    "maria@hotmail.com",
    "pedro@gmail.com",
    "pedro@hotmail.com",
]

encoded = encode(emails)

# Tamanho bruto
raw_bytes = sum(len(e) + 1 for e in emails)
tcf_bytes = len(encoded.encode('utf-8'))

print(f"Raw (newline-delimited): {raw_bytes} bytes")
print(f"TCF encoded:              {tcf_bytes} bytes")
print(f"Taxa de compressão:       {tcf_bytes/raw_bytes*100:.1f}%")
print(f"Economia:                 {raw_bytes - tcf_bytes} bytes ({(1 - tcf_bytes/raw_bytes)*100:.1f}%)")
```

Saída esperada:

```
Raw (newline-delimited): 100 bytes
TCF encoded:              64 bytes
Taxa de compressão:       64.0%
Economia:                 36 bytes (36.0%)
```

Com dados que compartilham prefixos e sufixos comuns, TCF reduz o tamanho. As duas camadas (OBAT + HCC) detectam e exploram esses padrões automaticamente.

## Passo 4 — Trabalhar com tabelas multi-coluna

Até aqui, usamos single-column (lista Python). TCF também suporta multi-column nativamente via dicts. Cada coluna é compactada independentemente, mas TCF preserva a estrutura da tabela:

```python
from tcf import encode, decode

table = {
    "id":   ["1", "2", "3"],
    "name": ["Alice", "Bob", "Charlie"],
}

encoded = encode(table)
decoded = decode(encoded)

print("Tabela original:")
print(table)
print()
print("Texto TCF:")
print(repr(encoded))
print()
print("Decodificado:")
print(decoded)
print()
print("Round-trip OK?", decoded == table)
```

Saída esperada:

```
Tabela original:
{'id': ['1', '2', '3'], 'name': ['Alice', 'Bob', 'Charlie']}

Texto TCF:
'#TCF.8M!5=id,!name\n1\n2\n3Alice\nBob\nCharlie'

Decodificado:
{'id': ['1', '2', '3'], 'name': ['Alice', 'Bob', 'Charlie']}

Round-trip OK? True
```

Observe a estrutura do texto TCF multi-coluna:

- **Linha 1**: `#TCF.8M!5=id,!name` — a assinatura e o meta inline. `M` significa multi-coluna;
    tamanhos estão em hexadecimal; `!` significa raw; a última coluna não leva tamanho e vai até o EOF.
- **Bytes seguintes**: os corpos são concatenados byte a byte; o decoder fatia o primeiro pelo tamanho
    declarado e atribui o restante à última coluna. Detalhe: [TCF-format.md](../algorithms/TCF-format.md).

TCF garante que a forma da tabela (nomes de colunas, ordem) é preservada exatamente.

## Passo 5 — Consultar a tabela sem materializar tudo

A API read-only `view()` oferece caminhos de consulta SQL-like como métodos Python. Ela não é um
parser SQL, mas filtra, agrega e projeta linhas alinhadas tocando apenas as colunas necessárias
quando o modo armazenado permite:

```python
from tcf import encode, view

table = {"cidade": ["SP", "SP", "RJ"], "valor": ["10", "20", "30"]}
v = view(encode(table))
assert v.where("cidade", "SP").sum("valor") == 30.0
print(v.report()["touched"])
```

O contrato e os limites da superfície query-like estão em
[`docs/reference/lazy-view.md`](../reference/lazy-view.md).

## Próximos passos

Você cobriu os fundamentos:

1. **encode(data)** transforma lista ou dict em texto TCF.
2. **decode(text)** recupera exatamente os dados originais.
3. TCF compacta explorando prefixos, sufixos e padrões composicionais.
4. Round-trip é garantido lossless.

### Explorar mais

- **[How-to guides](../how-to/)** — receitas práticas: [encodar um CSV](../how-to/encode-csv-file.md), [usar naturezas (CPF/CNPJ/IP)](../how-to/use-natures.md), [inspecionar a compressão](../how-to/inspect-compression.md).
- **[Formato TCF](../algorithms/TCF-format.md)** — especificação do formato, pipeline e API de referência.
- **[Algoritmos](../algorithms/)** — OBAT (Online Bidirectional Affix Tokenizer) e HCC (Hierarchical Compositional Coding).

### Benchmarks e validação

TCF foi validado em múltiplos datasets:

- **Sintético D1-D9**: 1523 bytes (53.2% ratio), round-trip 9/9.
- **Real-world Adult+TPC-H**: 57 colunas, -33% weighted vs raw, -31% vs single-column naive.
- **Benchmark vs csv/jsonl + gzip/brotli/zstd**: TCF vence 7/9 datasets.

Ver [`README.md`](../../README.md) e [`docs/algorithms/`](../algorithms/) para detalhes.

---

**Dúvidas?** Abra uma issue em [LeoPR/TCF](https://github.com/LeoPR/TCF/issues).

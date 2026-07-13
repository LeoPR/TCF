---
title: How to — Encodar um arquivo CSV
type: how-to
status: active
tags: [csv, compression, io, encode, decode, round-trip]
created: 2026-05-27
updated: 2026-05-27
---

# Encodar um arquivo CSV

Comprimir um arquivo CSV com TCF e recuperar os dados originais intactos. Fluxo: ler CSV → dict → encode → salvar .tcf → decodificar → verificar round-trip.

## Pré-requisitos

- TCF instalado: `pip install -e ".[dev]"` (Python ≥3.10)
- Arquivo CSV com cabeçalho (primeira linha = nomes de coluna)

## Passo 1 — Ler CSV em um dict

Usar `csv.DictReader` da stdlib para converter linhas CSV em dicionário `{coluna: [valor1, valor2, ...]}`:

```python
import csv

# Ler arquivo CSV
with open('dados.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    data_dict = {}
    for row in reader:
        for col, value in row.items():
            if col not in data_dict:
                data_dict[col] = []
            data_dict[col].append(value)
```

Estrutura esperada:
```python
data_dict = {
    'id': ['1', '2', '3'],
    'nome': ['Alice', 'Bob', 'Charlie'],
    'email': ['alice@example.com', 'bob@example.com', 'charlie@example.com']
}
```

## Passo 2 — Encodar e salvar como .tcf

Chamar `encode(dict)` e escrever resultado em arquivo `.tcf`:

```python
from tcf import encode

# Encode (retorna texto TCF)
tcf_text = encode(data_dict)

# Salvar em disco
with open('dados.tcf', 'w', encoding='utf-8') as f:
    f.write(tcf_text)
```

O arquivo `.tcf` contém:
- Assinatura de formato `#TCF.8M` (multi-coluna, default)
- Mapa de colunas (modo + tamanho + nome)
- Tokens comprimidos

Exemplo de saída (aproximado — detalhe do header em [TCF-format.md](../algorithms/TCF-format.md)):
```
#TCF.8M!5=id,!11=nome,email
1
2
3Alice
Bob
Charlie
alic*e*@example.com
bob3
charli2,3
```

## Passo 3 — Decodificar arquivo .tcf

Ler arquivo `.tcf` e chamar `decode(text)` para recuperar dict original:

```python
from tcf import decode

# Ler arquivo TCF
with open('dados.tcf', 'r', encoding='utf-8') as f:
    tcf_text = f.read()

# Decode (retorna dict ou list conforme tipo original)
recovered_data = decode(tcf_text)
```

## Passo 4 — Verificar round-trip

Validar que os dados decodificados são idênticos aos originais:

```python
# Verificar round-trip (lossless)
assert data_dict == recovered_data, "Round-trip falhou!"
```

TCF garante round-trip lossless: `decode(encode(x)) == x` sempre.

## Exemplo completo

```python
import csv
from tcf import encode, decode

# 1. Ler CSV
with open('vendas.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    data = {}
    for row in reader:
        for col, value in row.items():
            if col not in data:
                data[col] = []
            data[col].append(value)

print(f"Lidos: {len(data['id'])} linhas, {len(data)} colunas")

# 2. Encode e salvar
tcf_text = encode(data)
with open('vendas.tcf', 'w', encoding='utf-8') as f:
    f.write(tcf_text)

csv_size = len(open('vendas.csv', 'rb').read())
tcf_size = len(open('vendas.tcf', 'rb').read())
print(f"Compressão: {csv_size} → {tcf_size} bytes ({100*tcf_size/csv_size:.1f}%)")

# 3. Decodificar
with open('vendas.tcf', 'r', encoding='utf-8') as f:
    recovered = decode(f.read())

# 4. Verificar
assert data == recovered
print("Round-trip OK")
```

## Notas importantes

### NULL / valores vazios

CSV trata células em branco como `""` (string vazia), não `None`. TCF preserva strings vazias:

```python
# CSV com célula vazia:
# id,nome,telefone
# 1,Alice,11-9999-1111
# 2,Bob,
# 3,Charlie,21-3333-3333

data = {
    'id': ['1', '2', '3'],
    'nome': ['Alice', 'Bob', 'Charlie'],
    'telefone': ['11-9999-1111', '', '21-3333-3333']
}

tcf_text = encode(data)
recovered = decode(tcf_text)
assert data == recovered  # '' preservado
```

### Restrições em nomes de coluna

Nomes de coluna **não podem conter** os caracteres reservados:
- `,` (vírgula) — separador de colunas
- `=` (igual) — separador chave=valor

Válido:
```python
{
    'id': [...],
    'nome_completo': [...],
    'email_principal': [...]
}
```

Inválido:
```python
{
    'id,bad': [...],      # Erro: contém vírgula
    'email=principal': [...] # Erro: contém igual
}
```

Tentar encode com nome inválido levanta `ValueError`:

```python
try:
    encode({'id,bad': ['1', '2']})
except ValueError as e:
    print(f"Erro: {e}")
    # Erro: col name contem char reservado: 'id,bad'
```

### Encodings de arquivo

Sempre usar `encoding='utf-8'`:

```python
# Correto
with open('dados.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    ...

# Evitar (encoding padrao do SO pode variar)
with open('dados.csv', 'r') as f:
    reader = csv.DictReader(f)
    ...
```

## Ver também

- [Documentação de encode/decode](../algorithms/TCF-format.md) — especificação técnica
- [OBAT (Online Bidirectional Affix Tokenizer)](../algorithms/OBAT.md) — camada 1
- [HCC (Hierarchical Compositional Coding)](../algorithms/HCC.md) — camada 2
- [Exemplo: round-trip byte-canonical](../algorithms/output-convention.md)

---
title: "How to: Encodar um arquivo CSV"
type: how-to
status: active
tags: [csv, compression, io, encode, decode, round-trip]
created: 2026-05-27
updated: 2026-05-27
---

# Encodar um arquivo CSV

Comprimir um arquivo CSV com TCF e recuperar os dados originais intactos. Fluxo: ler CSV → dict → encode → salvar .tcf → decodificar → verificar round-trip.

## Pré-requisitos

- TCF instalado: `pip install tcf-format` (Python ≥3.10)
- Arquivo CSV com cabeçalho (primeira linha = nomes de coluna)

## Passo 1: Ler CSV em um dict

Esta página roda de ponta a ponta. Se você ainda não tem um CSV à mão, crie o dos exemplos:

```python
from pathlib import Path

Path('dados.csv').write_text(
    "\n".join([
        "id,nome,email",
        "1,Alice,alice@example.com",
        "2,Bob,bob@example.com",
        "3,Charlie,charlie@example.com",
    ]) + "\n",
    encoding='utf-8',
)
```

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

### O atalho: as linhas do `DictReader` entram como estão

O laço acima transpõe linhas em colunas, e desde a
[ADR-0049](../adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md) ele deixou de ser
obrigatório. Uma lista de dicionários retangular e plana é reconhecida como a tabela que ela
é, então a saída do `DictReader` entra direto no `encode`:

```python
import csv

with open('dados.csv', 'r', encoding='utf-8') as f:
    linhas = list(csv.DictReader(f))
```

O wire é o mesmo, byte por byte, salvo um caractere: o discriminador de família, que sai `R`
em vez de `M` para registrar a grafia da entrada.

```python
from tcf import encode

por_colunas = encode(data_dict)
por_linhas = encode(linhas)

print(len(por_colunas.encode('utf-8')), len(por_linhas.encode('utf-8')))
# 85 85

print(por_colunas.splitlines()[0])   # #TCF.8M!5=id,!11=nome,email
print(por_linhas.splitlines()[0])    # #TCF.8R!5=id,!11=nome,email

assert por_colunas.split('\n', 1)[1] == por_linhas.split('\n', 1)[1]   # corpo idêntico
```

Esse caractere decide a forma da volta. O `decode` de um `#TCF.8R` devolve as linhas como elas
entraram, uma lista de dicionários, e não um dicionário de colunas:

```python
from tcf import decode

assert decode(por_linhas) == linhas
assert decode(por_colunas) == data_dict
```

As duas rotas seguem válidas, e a escolha é de quem escreve o código. Quem já pensa em colunas
fica com o dicionário; quem lê o CSV linha a linha guarda as linhas.

## Passo 2: Encodar e salvar como .tcf

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

Exemplo de saída (aproximado, detalhe do header em [TCF-format.md](../algorithms/TCF-format.md)):
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

## Passo 3: Decodificar arquivo .tcf

Ler arquivo `.tcf` e chamar `decode(text)` para recuperar dict original:

```python
from tcf import decode

# Ler arquivo TCF
with open('dados.tcf', 'r', encoding='utf-8') as f:
    tcf_text = f.read()

# Decode (retorna dict ou list conforme tipo original)
recovered_data = decode(tcf_text)
```

## Passo 4: Verificar round-trip

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
with open('dados.csv', 'r', encoding='utf-8') as f:
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
with open('dados.tcf', 'w', encoding='utf-8') as f:
    f.write(tcf_text)

csv_size = len(open('dados.csv', 'rb').read())
tcf_size = len(open('dados.tcf', 'rb').read())
print(f"Compressão: {csv_size} → {tcf_size} bytes ({100*tcf_size/csv_size:.1f}%)")

# 3. Decodificar
with open('dados.tcf', 'r', encoding='utf-8') as f:
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

São **dois os caracteres proibidos**, `\n` e `\r`, e o motivo é o mesmo nos dois casos: o wire
é LF-only, o LF separa o meta, e não há como representar dentro do meta o caractere que o
delimita.

<!-- doctest: raises -->
```python
encode({'a\nb': ['1', '2']})
# ValueError: col name nao pode conter '\n' (o wire e' LF-only, e o LF separa o meta): 'a\nb'
```

<!-- doctest: raises -->
```python
encode({'a\rb': ['1', '2']})
# ValueError: col name nao pode conter '\r' (o wire e' LF-only, e o LF separa o meta): 'a\rb'
```

Todo o resto passa. Os caracteres que têm significado estrutural no meta, `,` (separador de
colunas), `=` (separador chave=valor), `\` (o próprio escape) e os marcadores de modo `!`, `@`,
`%` quando iniciam o nome, são **escapados com `\`** no wire e desescapados no decode:

```python
from tcf import encode, decode

tabela = {'id,bad': ['1', '2'], 'email=principal': ['3', '4']}
wire = encode(tabela)

print(wire.splitlines()[0])
# #TCF.8M!3=id\,bad,!email\=principal

assert decode(wire) == tabela   # o nome volta exatamente como entrou
```

Ou seja: o cabeçalho de um CSV do mundo real (`"Nome, Sobrenome"`, `"a=b"`, acentos, espaços)
entra sem tratamento. Verificável para todos eles com `decode(encode(t)) == t`.

**E o nome vazio (`''`)?** Também entra sem tratamento. Desde a
[ADR-0046](../adr/0046-nome-vazio-8m-porta-o-z-do-8h.md) ele viaja no meta como `\z` (a mesma
grafia que o `.8H` já usava) e volta `''` no decode:

```python
from tcf import encode, decode

decode(encode({'': ['1', '2']}))   # -> {'': ['1', '2']}
```

Isso cobre os CSVs em que o nome vazio nasce do **próprio formato** (RFC 4180: campo vazio é
campo legal): `a,b,` (vírgula sobrando), `a,,b` (coluna sem título no meio), `,a,b` (primeira sem
título), todos com `decode(encode(t)) == t`. Não precisa renomear nada antes.

Coluna **anônima** (nome posicional `'0'`, `'1'`, …) existe só quando você pede, com
`drop_names=True`: aí todos os nomes são dropados, o vazio inclusive.

> Até 2026-08-21 o nome vazio era tratado como anônimo (com `UserWarning`) e o decode devolvia
> `'0'`, o único caso em que o TCF alterava o dado
> ([`BUG-CHAVE-VAZIA-POSICIONAL`](../../tickets/BUG-CHAVE-VAZIA-POSICIONAL.md)). A causa era
> uma colisão de grafia com `drop_names`; a ADR-0046 portou o sentinela `\z` do `.8H`.

### Quebra de linha dentro de um valor

A proibição vale igual para o **valor**, com mensagem própria, e aqui ela pesa mais do que
parece: a RFC 4180 manda CRLF entre registros e permite CRLF **dentro** de um campo entre
aspas. O `csv.DictReader` resolve o terminador de registro sozinho, então o que chega ao
`encode` é o CRLF de dentro da célula.

<!-- doctest: raises -->
```python
encode({'obs': ['linha um\r\nlinha dois', 'ok']})
# ValueError: valor com quebra de linha (\n) nao e' representavel no TCF (LF delimita
# linhas): coluna 'obs', indice 0: 'linha um\r\nlinha dois'
```

A rota de registros não recusa esse dado. A quebra de linha tira a tabela do retangular
canônico, ela cai no `#TCF.8H`, que escapa nomes e folhas, e o round-trip continua exato:

```python
import csv, io

bruto = 'id,obs\r\n1,"linha um\r\nlinha dois"\r\n2,ok\r\n'
linhas_crlf = list(csv.DictReader(io.StringIO(bruto, newline='')))

wire = encode(linhas_crlf)
print(wire.splitlines()[0])          # #TCF.8Hid:6,obs

assert decode(wire) == linhas_crlf
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

- [Documentação de encode/decode](../algorithms/TCF-format.md): especificação técnica
- [OBAT (Online Bidirectional Affix Tokenizer)](../algorithms/OBAT.md): camada 1
- [HCC (Hierarchical Compositional Coding)](../algorithms/HCC.md): camada 2
- [Exemplo: round-trip byte-canonical](../algorithms/output-convention.md)

---
title: How to — Como usar naturezas (CPF/CNPJ/IP)
type: how-to
status: active
tags: [natures, pre-tx, compressão, cpf, cnpj, ip, adr-0015]
created: 2026-05-27
updated: 2026-05-27
---

# Como usar naturezas (CPF/CNPJ/IP)

Receita pra comprimir colunas com estrutura conhecida — CPF, CNPJ e
endereços IP — aproveitando dígitos verificadores e formatos templated
pra ganhar até 60% em ratio.

## Quando usar

Aplique naturezas quando seus dados satisfazem:

- **Estrutura conhecida**: o valor segue template fixo (ex: `NNN.NNN.NNN-DD`
  para CPF)
- **Padrão repetido**: muitos valores com mesma estrutura na coluna
- **Valores comprimíveis**: dígito verificador derivável (CPF, CNPJ) ou
  slots padronizáveis (IP com padding)

**Exemplo de ganho**: coluna com 1000 CPFs válidos comprime de 15 KB
→ 8.5 KB (43% ratio). Sem nature: 15 KB → 9 KB (60% ratio do M10
puro). Nature agrega 17 pontos percentuais.

**Não use naturezas quando**:

- Maioria dos valores quebra o padrão (ex: tabela heterogênea com CPFs
  + RG + passaporte)
- Você quer que o encode funcione sem fornecer spec no decode (decoder
  requer nature out-of-band por enquanto)

## Single-column: CPF

Coluna com CPFs formatados no padrão brasileiro `NNN.NNN.NNN-DD`.

```python
from tcf import encode, decode, SPEC_CPF

cpfs = [
    '111.444.777-35',
    '529.982.247-25',
    '111.444.777-35'  # repetição preservada
]

# Encode com nature
text = encode(cpfs, nature=SPEC_CPF)

# Decode requer MESMO spec
cpfs_back = decode(text, nature=SPEC_CPF)
assert cpfs_back == cpfs  # round-trip lossless
```

**Observacoes**:

- CPF valido requer digito verificador correto (mod-11 dupla). Se o
  digito for invalido, a natureza faz fallback pra literal: `_original`
  é armazenado. Round-trip preservado.
- Encoder automaticamente classifica cada valor:
  - `compressible`: CPF válido → codificado em base-94 (5 chars)
  - `check_invalid`: digito verificador errado → fallback literal
  - `format_mismatch`: formato diferente (ex: sem mascara) → fallback literal

Exemplos de classificacao:

```python
from tcf.natures import classify_value, SPEC_CPF

classify_value(SPEC_CPF, '111.444.777-35')   # 'compressible'
classify_value(SPEC_CPF, '111.444.777-99')   # 'check_invalid' (digito errado)
classify_value(SPEC_CPF, '11144477735')      # 'format_unmasked' (sem mascara)
classify_value(SPEC_CPF, '111-444-777-35')   # 'format_mismatch' (separadores errados)
```

### Comparacao com e sem nature

**Sem nature** (M10 puro):

```
Coluna original: ['111.444.777-35', '529.982.247-25', '111.444.777-35']
Bytes: 41
Texto TCF: '\\111.\\444.\\777-\\35\n\\529.\\982.\\247-\\25\n^1\n'
```

**Com nature**:

```
Coluna original: ['111.444.777-35', '529.982.247-25', '111.444.777-35']
Bytes: 17
Texto TCF: '%gc\\9g\n\\2y/h-\n^1\n'
Ratio: 41.5% (ganho de 58.5 pontos percentuais)
```

## Single-column: CNPJ

Coluna com CNPJ formatado `NN.NNN.NNN/NNNN-DD`.

```python
from tcf import encode, decode, SPEC_CNPJ

cnpjs = [
    '11.222.333/0001-81',
    '34.028.316/0001-00',
    '11.222.333/0001-81'
]

text = encode(cnpjs, nature=SPEC_CNPJ)
cnpjs_back = decode(text, nature=SPEC_CNPJ)
assert cnpjs_back == cnpjs
```

**Calculo de check digits**: CNPJ usa mod-11 dupla com pesos
diferentes de CPF (especificados em `_W1_CNPJ` e `_W2_CNPJ` via ADR-0015).

Ganho observado: CNPJ com 1000 valores uniforme/clustered comprime
**54-61%** vs M10 puro (similar ao CPF).

## Single-column: IP (IPv4)

Coluna com endereos IP `NNN.NNN.NNN.NNN` (canonico, sem zeros a esquerda
nos octetos).

```python
from tcf import encode, decode, SPEC_IP

ips = [
    '192.168.1.1',
    '192.168.1.2',
    '192.168.1.3'
]

text = encode(ips, nature=SPEC_IP)
ips_back = decode(text, nature=SPEC_IP)
assert ips_back == ips
```

**Mecanismo IP**: diferente de CPF/CNPJ, IP nao tem digito verificador.
A natureza padroniza slots via **padding zero-leading** (ex: `192.168.001.001`
= 12 digitos). Isso ativa detector HCC seq-RLE digit-centric, que aproveita
cadencia quando IPs estao em subnet.

**Ganho observado**: D-IP-subnet (1000 IPs em mesmo `/24`) comprime
**1.71% ratio** vs M10 puro — **speedup 68x**. Em IPs aleatorios
(D-IP-uniform), o ganho desaparece (102% ratio, ou seja, padrao nao
ajuda quando nao ha cadencia).

## Multi-column: nature_per_col

Use `nature_per_col` pra aplicar natureza diferente por coluna.

```python
from tcf import encode, decode, SPEC_CPF, SPEC_IP

table = {
    'id': ['001', '002', '003'],
    'cpf': ['111.444.777-35', '529.982.247-25', 'invalid-cpf'],
    'ip': ['192.168.1.1', '10.0.0.1', '10.0.0.2']
}

# Encode: aplica SPEC_CPF à coluna 'cpf', SPEC_IP à 'ip'
text = encode(table, nature_per_col={
    'cpf': SPEC_CPF,
    'ip': SPEC_IP
})

# Decode: reaplica specs
result = decode(text, nature_per_col={
    'cpf': SPEC_CPF,
    'ip': SPEC_IP
})

assert result == table
```

**Detalhes**:

- Colunas sem entrada em `nature_per_col` usam M10 puro (sem pre-tx)
- Cada coluna codifica/decodifica independentemente
- Round-trip lossless preservado mesmo com fallback em alguns valores

### Exemplo com fallback em multi-column

Valor invalido (`'invalid-cpf'`) na coluna CPF:

```python
table = {
    'cpf': ['111.444.777-35', 'invalid-cpf']
}

text = encode(table, nature_per_col={'cpf': SPEC_CPF})
result = decode(text, nature_per_col={'cpf': SPEC_CPF})

assert result == table  # 'invalid-cpf' preservado via fallback
```

## Fallback e round-trip

Quando um valor nao casa o padrao, natureza faz **fallback literal**:

```python
from tcf.natures import encode_value, decode_value, SPEC_CPF

# Valor com check digit invalido
invalid_cpf = '111.444.777-99'
encoded, status = encode_value(SPEC_CPF, invalid_cpf)

print(encoded)  # '_111.444.777-99' (prefixo '_' = fallback marker)
print(status)   # 'check_invalid'

# Decode remove marker e restaura original
decoded = decode_value(SPEC_CPF, encoded)
assert decoded == invalid_cpf
```

**Filosofia**: opt-in por valor. Cada valor que passa na validacao eh
comprimido; falhas caem pra literal. Nenhum valor eh perdido.

Taxa de compressao sobe quando **maioria** dos valores eh comprimível
(exemplo: dataset com 95% CPFs válidos e 5% invalidos ganha ainda 50%+
de compressao).

## Nota: Nature e byte-canonical

Sem `nature=` ou `nature_per_col=`, o encoder usa **byte-canonical
default** (M10 puro). Comportamento preservado sempre:

```python
# Sem nature — M10 puro (comportamento default)
text1 = encode(cpfs)

# Com nature — pre-tx + M10
text2 = encode(cpfs, nature=SPEC_CPF)

# text1 != text2, mas ambos preservam round-trip (com spec apropriado)
assert decode(text1) == cpfs
assert decode(text2, nature=SPEC_CPF) == cpfs
```

Nature eh **opt-in**: seu uso nao quebra compatibilidade com codigo
antigo.

## Validacao e diagnostico

Use `classify_value` pra inspecionar por que um valor nao comprimiu:

```python
from tcf.natures import classify_value, SPEC_CPF

values = [
    '111.444.777-35',    # OK
    '111.444.777-99',    # check invalido
    '111-444-777-35',    # formato errado
    '',                  # vazio
]

for v in values:
    status = classify_value(SPEC_CPF, v)
    print(f'{v:20} -> {status}')

# Output:
# 111.444.777-35       -> compressible
# 111.444.777-99       -> check_invalid
# 111-444-777-35       -> format_mismatch
#                       -> empty_value
```

**Categorias** (taxa Kim 2003):

- `compressible` — passou validacao, sera' codificado
- `check_invalid` — digito verificador errado
- `format_mismatch` — nao casa regex do template (ex: separadores errados)
- `format_unmasked` — digitos corretos mas sem mascara (ex: `11144477735`)
- `empty_value` — string vazia

> Os nomes exatos das categorias sao definidos por cada spec. Rode
> `classify_value(SPEC, valor)` pra ver o status real de um valor.

## Conexoes

- **ADR-0015**: [0015-natures-templated-checked-weld.md](../adr/0015-natures-templated-checked-weld.md) —
  decisao de welding e filosofia opt-in
- **API publica**: [`tcf/__init__.py`](../../src/tcf/__init__.py) —
  exports `SPEC_CPF`, `SPEC_CNPJ`, `SPEC_IP`
- **Implementacao**: [`tcf/natures/`](../../src/tcf/natures/) —
  `TemplatedCheckedSpec` e `TemplatedPaddedSpec`
- **Testes**: [`tests/test_natures_*.py`](../../tests/) —
  validacao de round-trip e fallback

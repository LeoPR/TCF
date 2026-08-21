---
title: How to — Como usar naturezas (CPF/CNPJ/IP)
type: how-to
status: active
tags: [natures, pre-tx, compressão, cpf, cnpj, cnpj-alfa, ip, adr-0015, adr-0042]
created: 2026-05-27
updated: 2026-05-27
---

# Como usar naturezas (CPF/CNPJ/IP)

Uma *nature* é um filtro opt-in para valores com formato conhecido, como CPF, CNPJ e IP. Ela pode
remover uma parte previsível do valor e reconstruir o original no `decode`.

## Contrato do formato 0.8

Cada filtro é apenas uma candidata: o TCF compara o **blob serializado completo**, incluindo
cabeçalho, tamanhos e o identificador do filtro. Se a versão filtrada ficar maior, a coluna original
permanece e o identificador não é emitido. Para `cpf`, `cnpj` e `ip`, o cabeçalho do `#TCF.8` registra
o filtro usado, e `decode(blob)` o reconhece sozinho. Um filtro customizado também pode ser usado,
mas o `decode` precisa receber um filtro com o mesmo nome registrado no cabeçalho.

Este guia mostra como comprimir colunas com estrutura conhecida — CPF, CNPJ e endereços IP —
aproveitando dígitos verificadores e formatos fixos.

## Quando usar

Aplique uma *nature* quando seus dados tiverem:

- **Estrutura conhecida**: o valor segue um formato fixo (ex.: `NNN.NNN.NNN-DD` para CPF)
- **Padrão repetido**: muitos valores com a mesma estrutura na coluna
- **Valores comprimíveis**: dígito verificador calculável (CPF, CNPJ) ou slots padronizáveis (IP)

**Exemplo medido**: uma coluna com 1000 CPFs válidos caiu de 15 KB para 8,5 KB com a *nature*.
Sem ela, caiu para 9 KB.

**Não use uma *nature* quando**:

- A maioria dos valores quebra o padrão (ex.: tabela heterogênea com CPFs, RG e passaporte)
- Você precisa de autodetecção: naturezas são opt-in; o `encode` só aplica o filtro que você fornece

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

# Para os filtros oficiais, o cabeçalho #TCF.8 permite decodificar sem argumento
cpfs_back = decode(text)
assert cpfs_back == cpfs  # round-trip sem perdas
```

**Observações**:

- CPF válido requer dígito verificador correto (duplo módulo 11). Se o dígito for inválido, o filtro
  guarda o valor como literal: `_original`. O round-trip continua preservado.
- O encoder classifica cada valor:
  - `compressible`: CPF válido, codificado no alfabeto seguro atual (5 caracteres)
  - `check_invalid`: dígito verificador errado, guardado como literal
  - `format_mismatch`: formato diferente (ex.: sem máscara), guardado como literal

Exemplos de classificação:

```python
from tcf.natures import classify_value, SPEC_CPF

classify_value(SPEC_CPF, '111.444.777-35')   # 'compressible'
classify_value(SPEC_CPF, '111.444.777-99')   # 'check_invalid' (dígito errado)
classify_value(SPEC_CPF, '11144477735')      # 'format_unmasked' (sem máscara)
classify_value(SPEC_CPF, '111-444-777-35')   # 'format_mismatch' (separadores errados)
```

### Comparação com e sem *nature*

**Sem filtro** (codificação comum):

```
Coluna original: ['111.444.777-35', '529.982.247-25', '111.444.777-35']
Bytes: 42
Texto TCF: '#TCF.8!!\n111.444.777-35\n529.982.247-25\n^1\n'
```

**Com filtro**:

```
Coluna original: ['111.444.777-35', '529.982.247-25', '111.444.777-35']
Bytes: 29
Texto TCF: '#TCF.8 :cpf\n%gc\\9g\n\\2y/h-\n^1\n'
Ratio: 69,0% da codificação comum; o custo do cabeçalho já está incluído na comparação
```

> **CORRIGIDO 2026-08-16** (auditoria de sincronização docs×código). O bloco "sem filtro" estava
> na grafia **pré-polaridade**: mostrava 41 B e um wire órfão com `\` de escape em cada slot. Hoje
> o carimbo `#TCF.8` é default ([ADR-0034](../adr/0034-header-default-100-porcento-single-col.md))
> e o sufixo de polaridade `!!` (2026-07-26) dispensa aqueles escapes — daí 42 B. O bloco "com
> filtro" não mudou; só a razão entre os dois (70,7% → 69,0%).

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
cnpjs_back = decode(text)
assert cnpjs_back == cnpjs
```

**Cálculo dos dígitos verificadores**: CNPJ usa duas etapas de cálculo por módulo 11, com pesos
 diferentes dos usados no CPF. A regra está registrada em [ADR-0015](../adr/0015-natures-templated-checked-weld.md).

O ganho não é garantido: em dados pequenos ou ordenados, a versão com filtro pode perder para a
codificação comum e não emitir `:cnpj`. Em uma tabela real ordenada, o teste mediu aumento de tamanho;
por isso não há uma porcentagem geral prometida.

## Single-column: CNPJ alfanumérico (`SPEC_CNPJ_ALFA`)

Desde **julho de 2026** (IN RFB nº 2.229/2024), CNPJ novo tem as **12 primeiras posições
alfanuméricas** (`0-9` e `A-Z`); os **2 dígitos verificadores continuam decimais**. Os CNPJ
numéricos existentes **não mudam** e continuam válidos.

```python
from tcf import encode, decode
from tcf.natures import SPEC_CNPJ_ALFA

cnpjs = [
    '12.ABC.345/01DE-35',      # alfanumérico
    '11.222.333/0001-81',      # numérico — também casa no spec alfa
]

text = encode(cnpjs, nature=SPEC_CNPJ_ALFA)
assert text.startswith('#TCF.8 :cnpja')
assert decode(text) == cnpjs   # o header resolve sozinho, sem spec out-of-band
```

**É UM CNPJ só** ([ADR-0043](../adr/0043-cnpj-um-so-compacto-por-valor.md)): o
`SPEC_CNPJ_ALFA` cobre os dois domínios pagando o preço certo **em cada valor** — corpo
100% numérico grava em **7 chars** (payload byte-idêntico ao do spec legado), corpo com
letra grava em **10**; o decode distingue pelo comprimento. Não há heurística de coluna:

| valor na coluna | payload | observação |
|---|---:|---|
| numérico (`11.222.333/0001-81`) | **7 chars** | byte-idêntico ao `SPEC_CNPJ` legado |
| alfanumérico (`12.ABC.345/01DE-35`) | **10 chars** | base 36 densa |

O `SPEC_CNPJ` (`:cnpj`) permanece para **ler wire legado** e como emissão explícita
byte-compat. Numa coluna 100% numérica ele economiza exatamente **1 byte** (o header);
em qualquer coluna com um alfanumérico sequer, o unificado vence.

### O helper `cnpj_spec_para`

Resolve só o empate: coluna 100% numérica → `SPEC_CNPJ` (1 B menor, byte-compat); qualquer
valor alfanumérico compressível → `SPEC_CNPJ_ALFA`. Medido contra a verdade (3 sementes ×
17 frações × 2 000 CNPJ reais): **51/51** — com o caso compacto por valor, a escolha que o
desenho anterior podia errar deixou de existir.

```python
from tcf import encode, decode
from tcf.natures import cnpj_spec_para

coluna = ['12.ABC.345/01DE-35', '11.222.333/0001-81', '34.028.316/0001-00']

text = encode(coluna, nature=cnpj_spec_para(coluna))
assert decode(text) == coluna
```

### Maiúscula/minúscula

O domínio oficial é **maiúscula-only** (NT Conjunta 2025.001: `[0-9A-Z]{12}[0-9]{2}`).
Minúscula é variante de representação e hoje cai em **literal** — não ganha, nunca
corrompe, e o roundtrip devolve exatamente o que entrou. Aceitar minúscula devolvendo
maiúscula canonizaria a saída (perderia o roundtrip byte a byte), então é da classe
CONTRATO e está registrado como pendência (H-15-06) — mediria −35,6% numa coluna
minúscula.

**O dígito verificador não mudou de regra**: é o mesmo módulo 11 com os mesmos pesos. O que
mudou é a conversão de caractere para valor — `ASCII(c) - 48`, então `'A'`=17 … `'Z'`=42. Como
`'0'` é ASCII 48, dígito converte para ele mesmo, e é por isso que CNPJ numérico gera
exatamente o mesmo DV nas duas regras. Detalhes e o que **não** foi resolvido (o `split`
estrutural continua recusando coluna com letra) em
[ADR-0042](../adr/0042-cnpj-alfanumerico-dois-specs.md).

## Single-column: IP (IPv4)

Coluna com endereços IP no formato `N.N.N.N`, sem zeros à esquerda nos octetos.

```python
from tcf import encode, decode, SPEC_IP

ips = [
    '192.168.1.1',
    '192.168.1.2',
    '192.168.1.3'
]

text = encode(ips, nature=SPEC_IP)
ips_back = decode(text)
assert ips_back == ips
```

**Mecanismo IP**: diferente de CPF/CNPJ, IP não tem dígito verificador. O filtro padroniza cada
parte com zeros à esquerda (por exemplo, `192.168.001.001` = 12 dígitos). Isso ajuda o compressor a
reconhecer a cadência quando os IPs estão na mesma subnet.

**Ganho observado em laboratório**: 1000 IPs na mesma `/24` chegaram a **1,71% do tamanho** da
codificação comum. Em amostras pequenas ou IPs aleatórios, o filtro não ajudou (102% do tamanho,
ou seja, ficou ligeiramente maior).

## Multi-column: `nature_per_col`

Use `nature_per_col` para aplicar filtros diferentes por coluna.

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

# Decode: o cabeçalho reaplica os filtros escolhidos
result = decode(text)

assert result == table
```

**Detalhes**:

- Colunas sem entrada em `nature_per_col` usam a codificação comum (sem filtro)
- Cada coluna codifica e decodifica independentemente
- O round-trip sem perdas é preservado mesmo com fallback em alguns valores

### Exemplo com fallback em multi-column

Valor inválido (`'invalid-cpf'`) na coluna CPF:

```python
table = {
    'cpf': ['111.444.777-35', 'invalid-cpf']
}

text = encode(table, nature_per_col={'cpf': SPEC_CPF})
result = decode(text)

assert result == table  # 'invalid-cpf' preservado via fallback
```

## Fallback e round-trip

Quando um valor não segue o padrão, o filtro o guarda como **literal**:

```python
from tcf.natures import encode_value, decode_value, SPEC_CPF

# Valor com dígito verificador inválido
invalid_cpf = '111.444.777-99'
encoded, status = encode_value(SPEC_CPF, invalid_cpf)

print(encoded)  # '_111.444.777-99' (prefixo '_' = marcador de fallback)
print(status)   # 'check_invalid'

# Decode remove o marcador e restaura o original
decoded = decode_value(SPEC_CPF, encoded)
assert decoded == invalid_cpf
```

**Regra**: o filtro é opt-in por valor. Cada valor que passa na validação é comprimido; os demais
caem para literal. Nenhum valor é perdido.

A taxa de compressão sobe quando a **maioria** dos valores é comprimível (por exemplo, um conjunto
com 95% de CPFs válidos e 5% inválidos ainda pode ganhar mais de 50%).

## Nota: escolha da menor representação

Sem `nature=` ou `nature_per_col=`, o encoder usa a representação padrão. Com uma *nature*, ele
compara a versão filtrada com a codificação comum e mantém a menor:

```python
# Sem nature — comportamento padrão
text1 = encode(cpfs)

# Com nature — filtro + pipeline padrão
# O filtro só permanece se o blob completo diminuir
text2 = encode(cpfs, nature=SPEC_CPF)

# text1 pode ser diferente de text2, mas ambos preservam o round-trip
assert decode(text1) == cpfs
assert decode(text2) == cpfs
```

O uso de uma *nature* é **opt-in**: ele não quebra a compatibilidade com código antigo.

## Validação e diagnóstico

Use `classify_value` para inspecionar por que um valor não foi comprimido:

```python
from tcf.natures import classify_value, SPEC_CPF

values = [
    '111.444.777-35',    # OK
    '111.444.777-99',    # dígito inválido
    '111-444-777-35',    # formato errado
    '',                  # vazio
]

for value in values:
    status = classify_value(SPEC_CPF, value)
    print(f'{value:20} -> {status}')

# Output:
# 111.444.777-35       -> compressible
# 111.444.777-99       -> check_invalid
# 111-444-777-35       -> format_mismatch
#                       -> empty_value
```

**Categorias de classificação**:

- `compressible` — passou na validação e será codificado
- `check_invalid` — dígito verificador errado
- `format_mismatch` — não corresponde ao formato (ex.: separadores errados)
- `format_unmasked` — dígitos corretos, mas sem máscara (ex.: `11144477735`)
- `empty_value` — string vazia

> Os nomes exatos das categorias são definidos por cada filtro. Rode
> `classify_value(SPEC, valor)` para ver o status real de um valor.

## Campos cadastrais ainda em exploração

O laboratório [`specs-cadastrais-v1`](../../experiments/lab/dirty/2026-07/2026-07-12/2026-07-12-specs-cadastrais-v1/)
mediu protótipos fora do core, sempre com round-trip e comparação do blob completo:

- **Data ISO**: ganho forte em single-column, mas tabelas em que o split já vence podem empatar.
  Uma futura `DateSpec` precisa validar o calendário e só entra com testes em dados reais.
- **CEP**: exige preservar zeros à esquerda (`01001-000`); o `TemplatedPaddedSpec` atual não deve
  ser usado sem essa garantia. Sem fonte real no hub, fica fora da lista de filtros do `.8`.
- **RG**: não tem formato nacional único; uma nature única seria enganosa. Tratar por UF ou deixar
  para uma extensão futura com dados autorizados.
- **CNH/RENAVAM/PIS/título**: alguns podem caber em uma máquina de dígitos verificadores, mas a regra
  e o dado precisam ser confirmados antes de batizar um filtro.
- **Telefone**: largura, DDD e máscara variam; não é um filtro nacional único.
- **Códigos sem inferência semântica**: codificar em uma base numérica só ajuda quando o alfabeto e a
  largura são declarados. O alfabeto seguro atual tem 80 caracteres; base64 não melhora os domínios
  medidos e base96 exigiria escaping ou quebraria a promessa ASCII.

Por isso, o `.8` mantém CPF/CNPJ/IP. Os demais candidatos ficam no `.9`, salvo aprovação separada
para uma `DateSpec` com validação de calendário e dois testes em dados reais.

## Conexões

- **ADR-0015**: [0015-natures-templated-checked-weld.md](../adr/0015-natures-templated-checked-weld.md) —
  decisão de integração dos filtros e filosofia opt-in
- **API pública**: [`tcf/__init__.py`](../../src/tcf/__init__.py) —
  exports `SPEC_CPF`, `SPEC_CNPJ`, `SPEC_IP`
- **Implementação**: [`tcf/natures/`](../../src/tcf/natures/) —
  `TemplatedCheckedSpec` e `TemplatedPaddedSpec`
- **Testes**: [`tests/test_natures_*.py`](../../tests/) —
  validação de round-trip e fallback

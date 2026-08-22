# TCF · Tabular Compact Format

![Version](https://img.shields.io/badge/version-0.8.0%20(pre--1.0)-orange)
![Format](https://img.shields.io/badge/format-%23TCF.8%20default-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Transmita a mesma tabela com bem menos bytes, sem virar um blob binário que ninguém
mais abre e lê.**

TCF comprime dados tabulares e aninhados para **texto ASCII inspecionável**: o que se
repete vira referência, o que é único fica cru (sem inflar). Sem dependências de runtime.

```bash
pip install tcf-format        # ou: uv pip install tcf-format
```

> Distribuição: `tcf-format` · pacote importável: `tcf`

## Um minuto

```python
from tcf import encode, decode

# Single-column: lista de strings
blob = encode(["ana@acme.com.br", "bruno@acme.com.br", "carla@acme.com.br"])
assert decode(blob) == ["ana@acme.com.br", "bruno@acme.com.br", "carla@acme.com.br"]

# Multi-column: dict de colunas
tabela = {
    "nome":   ["Ana Souza", "Bruno Lima", "Carla Nunes"],
    "cidade": ["Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plano":  ["Premium",   "Premium",   "Basic"],
}
blob = encode(tabela)
assert decode(blob) == tabela        # round-trip sempre exato

# Aninhado (o JSON que sua API manda): roteia para #TCF.8H pela mesma porta
pedidos = [{"cliente": "Ana", "itens": [{"sku": "A1", "qtd": 2}], "ativo": True}]
assert decode(encode(pedidos)) == pedidos
```

Uma porta só: `encode()` roteia pelo **tipo da entrada**, `decode()` pela assinatura do
formato. Round-trip é sempre lossless — ou preserva, ou falha alto.

## Como o wire se parece

Quatro registros de cadastro, saída real do `encode`:

```
#TCF.8M!2c=nome,2a=email,1c=cidade,14=plano,!cpf
Ana Souza
Bruno Lima
Carla Nunes
Diego Rochaan*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
111.111.111-11
...
```

`*3|Sao Paulo` = *"Sao Paulo, 3×"*. `^1` = *"igual à linha 1"*. Na coluna de e-mail o
prefixo único fica e o domínio comum vira referência — é onde mais se ganha, e onde o
texto fica mais denso. **Legível não quer dizer óbvio à primeira vista.**

## Números

Nos 15 datasets sintéticos, **sem compressor nenhum**, TCF é o texto mais compacto do
conjunto: **3131 B** contra CSV 4872 · JSON 5409 · JSONL 7001 (~36% menor que CSV).
Em multi-column real (9 tabelas Adult + TPC-H, 136 mil linhas): **−33% ponderado** vs CSV cru.

Contra `gzip`/`brotli`/`zstd` a comparação é de outra categoria — eles são **opacos**: para
responder qualquer pergunta é preciso inflar tudo primeiro. TCF compõe com eles e, com
volume, `tcf+brotli` bate `csv+brotli` (Adult 3k: **21,8 KB** vs 30,4 KB).

## Consultar sem descomprimir

```python
from tcf import encode, view

vendas = {
    "cliente": ["Ana", "Bruno", "Carla", "Diego", "Eva", "Ana"],
    "cidade":  ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio", "Sao Paulo", "Rio"],
    "valor":   ["120", "100", "170", "200", "80", "80"],
}
v = view(encode(vendas))                       # conecta, não descomprime nada
assert v.count() == 6                          # toca a coluna mais barata
assert v.sum("valor") == 750
assert v.where("cidade", "Sao Paulo").sum("valor") == 470   # só cidade + valor
```

Numa tabela real (online-retail, 5000×8), responder *"quanto o usuário X comprou"* toca
**7,9% do blob**; `count()` toca 0,2% — contra 100% de um `decode()`. Um compressor opaco
não faz isso.

## Specs: tipo semântico, resultado string

O TCF é um formato **de texto**: tudo volta como veio. Mas *saber a natureza* de uma
coluna permite comprimir muito além do que a estrutura sozinha entrega — e é aí que
entram os **specs**:

```python
from tcf import encode, decode

cpfs = ["111.111.111-11", "222.222.222-22", "333.333.333-33", "444.444.444-44"]
blob = encode(cpfs, schema="cpf")     # 69 B -> 39 B
assert decode(blob) == cpfs           # o header diz qual spec inverter
```

Um spec **não é um tipo forte** — a diferença importa:

| | tipo forte (int, date…) | spec semântico do TCF |
|---|---|---|
| o que afirma | *"este valor **é** um inteiro"* | *"este valor **tem a forma** de um CPF"* |
| o que devolve | o objeto nativo | **a string original, byte a byte** |
| se o valor não casa | erro de tipo / coerção | cai para literal, **sem falhar e sem perder** |
| o que ganha | semântica no seu programa | bytes no fio |

O spec explora **redundância que a forma garante**: um CPF tem 11 dígitos, máscara fixa e
dois dígitos verificadores *deriváveis* — então a máscara não viaja, o DV não viaja, e o
corpo vai numa base densa. O resultado continua sendo a string `"111.111.111-11"`.

É **opt-in por valor e nunca-pior**: o spec compete com o pipeline comum e só vence se
encolher; valor que não casa a forma vira literal na mesma coluna. E é **auto-descritivo** —
quando vence, o header carrega o id (`:cpf`) e o `decode` reverte sozinho, sem receber nada.

O registry traz `cpf`, `cnpj` (alfanumérico, IN RFB 2.229/2024), `ip`, `data-iso` e
`int-pad`; `schema` é **incremental** — sem ele, toda coluna é string semântica e o
pipeline decide sozinho:

```python
from tcf import encode, decode

clientes = {
    "cnpj":      ["11.222.333/0001-81", "12.ABC.345/01DE-35"],
    "criado_em": ["2026-01-15", "2026-02-20"],
    "obs":       ["-", "-"],
}
blob = encode(clientes, schema={"cnpj": "cnpj", "criado_em": "data-iso"})  # por nome
assert encode(clientes, schema={0: "cnpj"}) == encode(clientes, schema={"cnpj": "cnpj"})
assert decode(blob) == clientes            # `obs` nem foi mencionada — segue string
```

## O que ele não é

Não é banco, não é serialização de objetos, não é compressor binário de propósito geral.
Não valida semântica (não checa se um CPF *existe*). Round-trip lossless é o contrato;
compressão é a consequência.

## Estado: pré-1.0

Formato `#TCF.8`. Os minors pré-1.0 são **iterações de desenvolvimento** rumo a um 1.0
sólido: **não há compatibilidade rígida entre eles** — versões antigas se recuperam pelo
git. O congelamento definitivo é ato do 1.0.

## Documentação

Tudo vive no repositório:

- **[Repositório e README completo](https://github.com/LeoPR/TCF)** — exemplos com bytes
  medidos, comparativos e a leitura do wire linha a linha
- **[CHANGELOG](https://github.com/LeoPR/TCF/blob/main/CHANGELOG.md)**
- **[Referência da API](https://github.com/LeoPR/TCF/blob/main/docs/reference/api.md)** ·
  [knobs do encode](https://github.com/LeoPR/TCF/blob/main/docs/reference/encode-knobs.md) ·
  [view() lazy](https://github.com/LeoPR/TCF/blob/main/docs/reference/lazy-view.md)
- **[Como usar specs](https://github.com/LeoPR/TCF/blob/main/docs/how-to/use-natures.md)** ·
  [equivalência com JSON](https://github.com/LeoPR/TCF/blob/main/docs/reference/json-equivalence.md)
- **[Especificação do formato](https://github.com/LeoPR/TCF/blob/main/docs/algorithms/TCF-format.en.md)** ·
  [decisões de arquitetura (ADR)](https://github.com/LeoPR/TCF/blob/main/docs/adr/README.md)
- **[Versão em português](https://github.com/LeoPR/TCF/blob/main/README.pt-BR.md)**

## Licença

MIT — [LICENSE](https://github.com/LeoPR/TCF/blob/main/LICENSE).
Para citar: [CITATION.cff](https://github.com/LeoPR/TCF/blob/main/CITATION.cff).

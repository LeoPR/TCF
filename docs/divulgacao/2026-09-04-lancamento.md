**Português** · [English](2026-09-04-release.en.md)

# TCF 0.8.4: referência para divulgação

Documento datado que serve de fonte para os textos de canal desta pasta. Regra: nenhum texto
de canal muda sem esta fonte mudar antes.

Este documento reúne afirmações, exemplos e limites para adaptar aos canais. A evidência
permanece nas fontes: [baselines canônicos](../../tests/test_regression_v1_baseline.py),
[relatório do EXP-019](../../experiments/lab/clean/EXP-019-consistencia-0-8-4/report.md)
e [instrumentos de desempenho](../../scripts/bench_perf/). Um resultado só deve ser
reutilizado com sua base de comparação e seu escopo.

Os blocos Python desta página são executados pelo
[teste de exemplos](../../tests/test_docs_snippets.py). Asserções verificam o que está
explicitamente codificado; números em tabelas e prosa exigem conferência nas fontes.

## O que a biblioteca é

O TCF codifica dados tabulares e aninhados suportados em texto inspecionável, sem perdas.
`encode()` produz uma string; `decode()` reconstrói os dados. A representação usa
referências e agrupamentos, cuja leitura exige conhecer os marcadores. Não é banco de
dados, ferramenta de ETL nem serializador de objetos Python arbitrários.

`pip install tcf-format` · MIT · pré-1.0 · Python 3.10 ou mais novo · zero dependências.

A superfície pública está documentada na [referência da API](../reference/api.md).

## Afirmações e evidências

### 1. Representação e compressão são escolhas combináveis

JSON, CSV e TCF representam dados; gzip, brotli e zstd comprimem os bytes dessa
representação. São escolhas combináveis, não alternativas mutuamente exclusivas.
Em HTTP, a compressão pode ser indicada por `Content-Encoding`, e muitas bibliotecas
descomprimem o corpo antes de entregá-lo à aplicação. A pergunta inclui, portanto,
**qual representação o processo recebe e interpreta depois da descompressão do canal**.

O custo dessa descompressão integra a avaliação de CPU e memória da aplicação, mesmo
quando é administrado pela biblioteca HTTP.

### 2. Estrutura inspecionável e consultas seletivas

Um arquivo gzip não expõe os campos e valores como texto diretamente inspecionável.
É preciso descomprimir para interpretá-los, mas isso pode ser feito em fluxo, sem manter
o conteúdo inteiro descomprimido na memória. O gzip, por si só, não oferece acesso por
coluna nem operações sobre os registros da tabela.

Sem uma camada externa de compressão, a representação TCF expõe estrutura que `view()`
pode aproveitar. O exemplo abaixo verifica o round-trip e consultas sobre um cadastro:

```python
from tcf import decode, encode, view

tabela = {
    "nome":   ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha"],
    "email":  ["ana@acme.com.br", "bruno@acme.com.br",
               "carla@acme.com.br", "diego@acme.com.br"],
    "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plano":  ["Premium", "Premium", "Basic", "Premium"],
    "cpf":    ["111.111.111-11", "222.222.222-22",
               "333.333.333-33", "444.444.444-44"],
}

wire = encode(tabela)
assert decode(wire) == tabela              # §RT: o roundtrip vem antes do número
assert len(wire.encode("utf-8")) == 242

v = view(wire)                             # nada foi decodificado ainda
assert list(v.columns) == ["nome", "email", "cidade", "plano", "cpf"]
assert v.nrows == 4
assert sorted(v.distinct("cidade")) == ["Rio de Janeiro", "Sao Paulo"]
assert dict(v.group_count("plano")) == {"Premium": 3, "Basic": 1}
assert v.where("plano", "Premium").nrows == 3
assert v.column_bytes("cpf") == 59         # dá para saber o custo por coluna
```

As consultas acima não exigem reconstruir a tabela inteira. O teste verifica suas
respostas e o tamanho da representação; o custo depende da operação e do modo da coluna.

### 3. Comparação de tamanho e escopo das amostras

O cadastro tem quatro registros e cinco colunas. Os tamanhos estão em bytes, com
JSON/JSONL compactos e compressores externos no nível máximo:

| formato | cru | gzip | br | zstd |
|---|---:|---:|---:|---:|
| JSON | 451 | 206 | 195 | 197 |
| JSONL | 449 | 205 | 194 | 194 |
| CSV | 277 | 177 | **162** | **165** |
| **TCF** | **242** | 206 | 185 | 193 |

Neste exemplo, o TCF é o menor sem compressor externo. Sob gzip, JSON, JSONL e TCF ficam
a até um byte de distância; o CSV comprimido é menor que os três. O resultado não
estabelece uma ordem de desempenho para outros dados ou níveis de compressão.

O [EXP-019](../../experiments/lab/clean/EXP-019-consistencia-0-8-4/) compara duas
representações do próprio TCF: a hierárquica (`.8H`) e a de registros tabulares (`.8R`).
Nas oito amostras de 800 linhas, o total passou de 390.863 B para 290.949 B, ou **−25,6%**,
com reduções de 4,1% a 46,6% por amostra e round-trips verificados. Não é uma comparação
contra CSV, JSON ou gzip, nem um teste de escala; o corpus inclui dados reais e gerados.

### 4. Dados aninhados preservam estrutura e valores

O TCF lê a **estrutura de dados** que a linguagem monta a partir do JSON, e não o texto
do JSON. O round-trip preserva os valores e a estrutura suportada, incluindo objetos
aninhados, listas, `null` e booleanos; não preserva a formatação do documento JSON original.

Dois registros com uma lista dentro: JSON compacto dá 184 B, o TCF dá 166 B, e com o filtro
opcional de CPF dá **144 B**.

O codificador decompõe o objeto em colunas por campo. O nome de cada campo aparece
uma vez no cabeçalho. Um exemplo de cabeçalho hierárquico é:

```
#TCF.8Hnome:21,cpf:38,ativo:11b,fones#:6[
```

### 5. A escolha de candidatos tem um limite definido

> Para cada coluna, o codificador gera as candidatas e grava a **menor**:
> `min(tcf, cru, dicionário, split)`.

Essa escolha limita o custo do corpo de cada coluna às alternativas avaliadas pelo
codificador, incluindo a representação crua. Não garante que o arquivo completo seja
menor que qualquer CSV ou JSON: cabeçalhos e metadados também ocupam espaço.

Com `sort_by`, a ordenação também é uma candidata: o codificador compara as versões e
mantém a menor. A opção autoriza mudar a ordem das linhas, que deixa de fazer parte do
contrato de reconstrução. Use-a somente quando essa ordem não importar. O
[EXP-019](../../experiments/lab/clean/EXP-019-consistencia-0-8-4/report.md) registra as
verificações dessa escolha nas amostras.

### 6. Como o contrato é verificado

As verificações têm funções distintas:

A **regra §RT**, que é de processo e não de código. Ela está escrita como invariante no guia do
projeto, e diz que `decode(encode(x)) == x` vem antes de qualquer número: sem roundtrip, o
número não entra em prosa, nem em tabela, nem em commit. Os tamanhos desta página passaram por
ela, e o script que os reproduz sai com erro se um roundtrip falhar.

Os **gates byte-canônicos**, que fixam a saída esperada de conjuntos conhecidos e falham
vermelho se um byte mudar. É o que impede uma otimização de mudar o wire sem ninguém notar.

E o **baseline de performance pinado**, com a matriz de casos travada por hash. Ele recusa
comparar duas rodadas se a matriz ou o plano diferirem, em vez de casar o que não casa.

### 7. O custo depende de como os dados são reutilizados

O `encode` busca padrões; o `decode` reconstrói a representação escolhida sem repetir
essa busca. A `view` pode evitar materialização desnecessária, mas também pode precisar
decodificar colunas inteiras. Não há uma razão fixa de tempo entre essas operações.

Dados preparados uma vez para muitas leituras amortizam o custo de codificação. Dados
personalizados a cada requisição repetem esse custo. Medições de desempenho devem
identificar carga, versão, ambiente e instrumento, não apenas uma razão de velocidade.

### 8. Marcadores descrevem diferentes padrões

`*N|` representa valores idênticos consecutivos. `*N+delta|` representa uma sequência
com passo constante; `*N~d1,d2,...|`, uma sequência com passos periódicos. O marcador
`*12+5|\100`, por exemplo, descreve doze valores a partir de 100, com passo 5.

Esses marcadores expõem contagens e progressões, mas isso não garante que toda consulta
opere sem expansão. Os caminhos implementados dependem do modo de coluna e estão
documentados na [referência de consultas](../reference/lazy-view.md).

## Limites a preservar nas adaptações

- Os resultados de tamanho pertencem aos dados e configurações medidos. O cadastro pequeno
    não demonstra desempenho em escala nem vantagem universal sobre compressores externos.
- Codificação e consulta têm custos distintos; ambas precisam ser medidas no uso pretendido.
- O pacote é pré-1.0, sem garantia rígida de compatibilidade entre versões menores.
- As comparações desta página não avaliam Parquet, ORC ou outros formatos de armazenamento.
- O trabalho em curso e as prioridades são mantidos em [STATUS.md](../../STATUS.md) e
    [ROADMAP.md](../../ROADMAP.md), não inferidos a partir deste anúncio.

## Reprodução

Para instalar a biblioteca: `python -m pip install tcf-format`.
Para executar os testes abaixo, use um checkout com o ambiente de desenvolvimento
preparado conforme [CONTRIBUTING.pt-BR.md](../../CONTRIBUTING.pt-BR.md):

```sh
python -m pytest -q tests/test_docs_snippets.py       # os blocos desta página
python -m pytest -q tests/test_regression_v1_baseline.py   # os bytes canônicos + §RT
```

## Ligações

- Repositório: https://github.com/LeoPR/TCF
- Pacote: https://pypi.org/project/tcf-format/
- A assimetria entre escrever e ler: [`docs/theory/conceitos/a-assimetria-encode-decode.md`](../theory/conceitos/a-assimetria-encode-decode.md)
- O wire em uma página: [`docs/theory/conceitos/o-wire-em-uma-pagina.md`](../theory/conceitos/o-wire-em-uma-pagina.md)
- O custo da consulta: [`docs/theory/conceitos/custo-da-consulta.md`](../theory/conceitos/custo-da-consulta.md)
- A comparação interna nas amostras: [EXP-019](../../experiments/lab/clean/EXP-019-consistencia-0-8-4/)

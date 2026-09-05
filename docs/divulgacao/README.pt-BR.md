**Português** · [English](README.md)

# `docs/divulgacao/`: material para apresentar o TCF

Esta pasta reúne textos e figuras para apresentar o projeto fora do repositório. A
documentação de uso fica nas pastas irmãs. As peças adaptam evidências existentes:
cada medição deve conservar sua fonte, base de comparação e escopo.

## Público e finalidade

Os textos compartilham fatos, não uma redação única. A organização deve responder à
pergunta que traz o leitor a cada lugar:

| superfície | necessidade do leitor | prioridade editorial |
|---|---|---|
| [README do GitHub](../../README.pt-BR.md) | entender, avaliar ou contribuir para o projeto | proposta, início rápido, formato, evidências, limites e navegação técnica |
| [página do PyPI](../../README.pypi.md) | instalar a biblioteca e usá-la em Python | versão mínima, nome de instalação/importação, exemplos completos, contratos e compatibilidade; links absolutos |
| artigo do LinkedIn | compreender uma ideia sem conhecer o projeto | contexto, exemplo, explicação, utilidade e conclusão; introduzir termos antes de depender deles |
| post do LinkedIn | decidir se vale abrir o artigo | uma ideia central, exemplo curto, ressalva relevante e convite à leitura |
| fonte de divulgação | verificar o que pode ser afirmado | fatos, proveniência, exemplos testáveis e limites; sem linguagem de chamada |

O artigo pode desenvolver um argumento; o README deve facilitar a consulta e a avaliação.
O post não precisa reproduzir o catálogo de funcionalidades, e a página do PyPI não precisa
repetir a explicação interna do algoritmo.

## Como está organizado

A **raiz** guarda a **fonte de notícia** datada: um arquivo por anúncio, com o estado, as
manchetes e os limites ditos por inteiro. As **subpastas** são os **canais**, e cada uma dá
àquela fonte o formato que o meio aceita.

A regra que mantém os dois alinhados: nenhum texto de canal muda sem a fonte datada mudar antes.

| Caminho | O que é |
|---|---|
| [`2026-09-04-lancamento.md`](2026-09-04-lancamento.md) / [`2026-09-04-release.en.md`](2026-09-04-release.en.md) | a fonte de notícia atual (PT / EN) |
| [`linkedin/post.*`](linkedin/) | a peça curta do feed, uma por língua |
| [`linkedin/artigo.*`](linkedin/) | o artigo, um por língua, com notas de publicação separadas |
| [`linkedin/figuras/<língua>/`](linkedin/figuras/) | as figuras, uma pasta por língua |

Há dois textos por língua: chamada para o feed e artigo longo. As notas no início de cada
arquivo são instruções para publicação e não fazem parte do texto destinado ao leitor.

Fica sob `docs/` porque **documento de divulgação é documento**. Uma segunda hierarquia na raiz
faria o leitor escolher entre dois lugares para procurar a mesma coisa.

O artigo usa figuras para as comparações tabulares e blocos de código curtos para facilitar
a leitura em coluna estreita. Ao publicar, aplique títulos, links e blocos no editor,
insira as imagens indicadas e confira a prévia. Colar Markdown não dispensa essa conferência.

As figuras ficam em `linkedin/figuras/<língua>/`, uma subpasta por língua para o diretório do
canal não misturar texto com binário. O `scripts/make_divulgacao_figuras.py` gera todas, e
rodá-lo regenera tudo. Elas obedecem à mesma regra dos números do texto: existe um comando que
as reproduz.

Saem em **SVG e PNG** lado a lado. O SVG é texto, o repositório versiona e o GitHub renderiza;
o PNG é o que se sobe, porque **o LinkedIn não aceita SVG**.

A conversão usa o Chrome ou o Edge da própria máquina, em modo headless, e por isso não instala
nada. Sai em 2× de propósito: o LinkedIn reamostra a imagem para baixo, e texto fino em 1×
fica sujo depois disso. Sem navegador, o script avisa quais figuras ficaram sem PNG em vez de
falhar.

As figuras de resultados usam evidência executável: as barras representam bytes medidos
após round-trip, o texto codificado vem de `encode` e a figura de consultas usa
`view.report()`. Isso não elimina a necessidade de revisar legendas e conclusões.

São seis SVGs por língua: `0-capa` é a capa 1.91:1; `1-formatos` compara os formatos;
`2-wire` anota a saída; `3-view` mostra as colunas consultadas; `4-tabela` compara a
compressão externa; `5-pipeline` apresenta as etapas de codificação. Use apenas as figuras
citadas na peça, não necessariamente todo o conjunto.

Aqui o português é a língua canônica, ao contrário do resto do projeto, porque o público a que
estes textos se dirigem lê português primeiro. O inglês é a tradução.

## Limites de cada canal

- **Post do LinkedIn** (`linkedin/post.*`): orçamento de até 3.000 caracteres no corpo,
  incluindo links e hashtags. Reserve margem para o URL definitivo. A abertura deve fazer
  sentido isoladamente na prévia, cujo corte varia com a interface. Use texto simples,
  contexto antes do jargão e hashtags ao final; as grafias sem acento são uma convenção editorial.
- **Artigo do LinkedIn** (`linkedin/artigo.*`): texto longo, com desenvolvimento do argumento
  e transições entre seções. Use figuras em vez de tabelas largas e explique os exemplos
  antes de extrair conclusões. Termine com os limites e o caminho para experimentar o projeto.

## Antes de publicar

Verifique cada número na fonte indicada. Os
[baselines](../../tests/test_regression_v1_baseline.py) protegem saídas canônicas; o
[EXP-019](../../experiments/lab/clean/EXP-019-consistencia-0-8-4/report.md) compara duas
representações internas do TCF, não TCF contra CSV; os
[instrumentos de desempenho](../../scripts/bench_perf/) tratam de tempo e memória.

A fonte vigente e os artigos participam dos
[testes de exemplos](../../tests/test_docs_snippets.py). Eles executam os blocos Python
e suas asserções, mas não verificam automaticamente todos os números da prosa, as
imagens ou a apresentação no LinkedIn. Confira também links, legendas, orçamento do post
e a substituição do marcador pelo URL publicado.

**O que estes textos evitam de propósito:**

- superlativo. O gancho é o problema do leitor, não a vantagem do projeto;
- dizer "menor" sem dizer contra o quê, medido de que jeito, e em que dado;
- histórico de desenvolvimento. Estes textos dizem o que a biblioteca faz hoje. O caminho até
  aqui fica no `CHANGELOG.md`, nas ADR e nos labs datados, que é onde alguém procura de
  propósito. A razão é do leitor: quem chega agora nunca viu a versão antiga.

**Preserve as ressalvas junto das afirmações.** O empate sob gzip e a vantagem do CSV
comprimido pertencem ao cadastro pequeno, não a todos os dados. Custos de codificação,
compatibilidade pré-1.0 e ausência de comparação com formatos de armazenamento não devem
sumir ao encurtar a peça. Consulte o [estado vigente](../../STATUS.md) para descrever o
trabalho em curso.
